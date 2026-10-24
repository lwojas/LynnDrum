// SPDX-License-Identifier: GPL-3.0-only
// LynnDrum - sequencer edit bridge: UI thread <-> audio thread, without sharing mutable pattern memory.
//
//  * The UI side owns a *mirror* of the whole bank (64 patterns, the song, the mutes): what the editor shows and what is
//    saved in the plugin state.
//  * Every edit updates the mirror and enqueues a small command; the audio thread drains the queue at the start of a block
//    and applies it to the real sequencer. Single producer / single consumer, no locks, no allocation.
//  * Telemetry (playhead, playing/pending pattern, meter) flows back through a few atomic words.
#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <deque>
#include <string>
#include <vector>
#include "EngineHost.h"

namespace lynn
{
constexpr int kTracks = LXRSEQ_TRACKS;
constexpr int kSteps = LXRSEQ_STEPS;
constexpr int kPatterns = LXRSEQ_PATTERNS;
constexpr int kSongLength = 64;
constexpr int kSongEnd = 64, kSongLoop = 65;
constexpr int kShiftNone = 7;

struct UiTrack
{
    std::array<std::uint8_t, kSteps> on {}, vol {}, prob {}, note {}, flam {}, shift {};
    std::uint8_t length = 16;
    UiTrack() { vol.fill (100); prob.fill (100); note.fill (60); shift.fill (kShiftNone); }
    bool operator== (const UiTrack& o) const { return on == o.on && vol == o.vol && prob == o.prob && note == o.note && flam == o.flam && shift == o.shift && length == o.length; }
};
struct UiPattern
{
    std::array<UiTrack, kTracks> tracks;
    std::uint8_t shuffle = 0;
    bool operator== (const UiPattern& o) const { return tracks == o.tracks && shuffle == o.shuffle; }
    bool isEmpty() const { return *this == UiPattern(); }
};
struct UiSong
{
    std::array<std::uint8_t, kSongLength> entries {};          // pattern numbers; kSongEnd / kSongLoop terminate
    bool enabled = false;
    UiSong() { entries.fill (kSongEnd); entries[0] = 0; }
    bool operator== (const UiSong& o) const { return entries == o.entries && enabled == o.enabled; }
};

struct SeqCommand
{
    enum Type : std::uint8_t { Step, Length, Mute, Shuffle, Audition, SelectPattern, SongMode, SongEntry };
    Type type = Step;
    std::uint8_t pat = 0, track = 0, idx = 0, on = 0, vol = 100, prob = 100, note = 60, flam = 0, shift = kShiftNone;
    std::uint16_t value = 0;       // Length / Mute / Shuffle / SongMode / SongEntry payload
};

class SeqBridge
{
public:
    SeqBridge();

    // ---- message thread -------------------------------------------------------------------------------------------
    const UiPattern& pattern (int p) const noexcept { return bank[(size_t) p]; }
    bool muted (int track) const noexcept { return ((mutes >> track) & 1) != 0; }
    const UiSong& songState() const noexcept { return song; }
    bool used (int p) const noexcept { return !bank[(size_t) p].isEmpty(); }

    void loadDemo();                                         // authored default beat in pattern 0
    // JSON command from the editor (see Source/UI/web/src/model.ts). Returns false if malformed.
    bool applyUiCommand (const std::vector<double>& args, const std::string& name);

    void audition (int track, int velocity);                 // trigger a voice now (UI preview)
    void setBank (const std::array<UiPattern, kPatterns>&, const UiSong&, std::uint8_t mutesMask);   // preset / state load
    void setPattern (int p, const UiPattern&);               // replace one pattern
    void flush();                                            // retry commands that did not fit into the queue
    std::uint32_t editCount() const noexcept { return edits.load (std::memory_order_relaxed); }

    std::string serialize() const;                           // compact binary (schema 2); reads schema 1 too
    bool deserialize (const std::uint8_t* data, size_t n);

    // ---- audio thread ---------------------------------------------------------------------------------------------
    void drain (EngineHost& host) noexcept;
    void publishPlayhead (EngineHost& host, double bpm, float peakL = 0.f, float peakR = 0.f) noexcept;

    // ---- message thread: telemetry ---------------------------------------------------------------------------------
    struct Playhead { bool running; std::array<int, kTracks> steps; double bpm; int activePattern, pendingPattern, songPosition; };
    Playhead readPlayhead() const noexcept;
    struct Level { float l, r; };
    Level readLevel() noexcept;                              // peak since the last call

private:
    void push (const SeqCommand&);
    void editStep (int pat, int t, int i);
    void editLength (int pat, int t);
    void editMute (int t);
    void editShuffle (int pat);
    void sendPattern (int pat, const UiPattern* previous);   // all steps that differ from `previous` (nullptr = everything)
    void sendSong();
    static constexpr size_t kQueue = 8192;                   // power of two
    std::array<SeqCommand, kQueue> ring {};
    std::atomic<size_t> head { 0 }, tail { 0 };              // producer / consumer
    std::deque<SeqCommand> pending;                          // message thread only
    std::array<UiPattern, kPatterns> bank;
    UiSong song;
    std::uint8_t mutes = 0;
    std::atomic<std::uint32_t> edits { 0 };                  // bumped by every UI edit (preset dirty tracking)
    std::atomic<std::uint64_t> playheadWord { 0 };           // 7 x 8 bit step index, bit 56 running
    std::atomic<std::uint32_t> patternWord { 0 };            // active | pending << 8 | songPosition << 16
    std::atomic<float> bpmShown { 120.f };
    std::atomic<float> peakL { 0.f }, peakR { 0.f };
};
} // namespace lynn
