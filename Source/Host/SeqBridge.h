// SPDX-License-Identifier: GPL-3.0-only
// LynnDrum - sequencer edit bridge: UI thread <-> audio thread, without sharing mutable pattern memory.
//
//  * The UI side owns a *mirror* of the pattern (what the editor shows and what is saved in the plugin state).
//  * Every edit updates the mirror and enqueues a small command; the audio thread drains the queue at the start
//    of a block and applies it to the real sequencer. Single producer / single consumer, no locks, no allocation.
//  * Playhead telemetry flows back through one atomic word.
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
constexpr int kShiftNone = 7;

struct UiTrack
{
    std::array<std::uint8_t, kSteps> on {}, vol {}, prob {}, note {}, flam {}, shift {};
    std::uint8_t length = 16;
    bool muted = false;
    UiTrack() { vol.fill (100); prob.fill (100); note.fill (60); shift.fill (kShiftNone); }
};
struct UiPattern
{
    std::array<UiTrack, kTracks> tracks;
    std::uint8_t shuffle = 0;
};

struct SeqCommand
{
    enum Type : std::uint8_t { Step, Length, Mute, Shuffle, Audition };
    Type type = Step;
    std::uint8_t track = 0, idx = 0, on = 0, vol = 100, prob = 100, note = 60, flam = 0, shift = kShiftNone;
    std::uint16_t value = 0;       // Length / Mute / Shuffle payload
};

class SeqBridge
{
public:
    SeqBridge();

    // ---- message thread -------------------------------------------------------------------------------------------
    UiPattern& pattern() noexcept { return mirror; }
    const UiPattern& pattern() const noexcept { return mirror; }
    void loadDemo();                                         // authored default beat
    void editStep (int track, int idx);                      // enqueue the full state of one step (after mirror edit)
    void editLength (int track);
    void editMute (int track);
    void editShuffle();
    void audition (int track, int velocity);                 // trigger a voice now (UI preview); thread-safe for the message thread only
    void setPattern (const UiPattern&);                       // replace the whole pattern (preset load) and push it to the sequencer
    std::uint32_t editCount() const noexcept { return edits.load (std::memory_order_relaxed); }
    void resyncAll();                                        // enqueue everything (state restore)
    void flush();                                            // retry commands that did not fit into the queue

    // JSON command from the editor: ["step",track,idx,on] ... (see Source/UI/web/src/model.ts). Returns false if malformed.
    bool applyUiCommand (const std::vector<double>& args, const std::string& name);

    std::string serialize() const;                           // compact binary (schema 1), raw bytes
    bool deserialize (const std::uint8_t* data, size_t n);

    // ---- audio thread ---------------------------------------------------------------------------------------------
    void drain (EngineHost& host) noexcept;
    void publishPlayhead (EngineHost& host, double bpm, float peakL = 0.f, float peakR = 0.f) noexcept;
    struct Level { float l, r; };
    Level readLevel() noexcept;                              // peak since the last call (message thread)

    // ---- message thread: telemetry ---------------------------------------------------------------------------------
    struct Playhead { bool running; std::array<int, kTracks> steps; double bpm; };
    Playhead readPlayhead() const noexcept;

private:
    void push (const SeqCommand&);
    static constexpr size_t kQueue = 8192;                   // power of two
    std::array<SeqCommand, kQueue> ring {};
    std::atomic<size_t> head { 0 }, tail { 0 };              // producer / consumer
    std::deque<SeqCommand> pending;                          // message thread only
    UiPattern mirror;
    std::atomic<std::uint32_t> edits { 0 };                  // bumped by every UI edit (preset dirty tracking)
    std::atomic<std::uint64_t> playheadWord { 0 };           // 7 x 8 bit step index, bit 56 running
    std::atomic<float> bpmShown { 120.f };
    std::atomic<float> peakL { 0.f }, peakR { 0.f };         // running peaks, reset by readLevel()
};
} // namespace lynn
