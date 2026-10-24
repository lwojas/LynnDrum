// SPDX-License-Identifier: GPL-3.0-only
// LynnDrum - runs one lxr_core engine inside an audio callback of arbitrary rate/block size.
#pragma once
#include <array>
#include <cstdint>
#include "Resampler.h"
#include "lxr/lxr_engine.h"
#include "lxr/lxr_seq.h"

namespace lynn
{
// A note/parameter event with a sample offset inside the current host block. Offsets must be ascending.
struct HostEvent
{
    enum class Type : std::uint8_t { NoteOn, Param, ModTarget, SeqRun, SeqStop, SeqLocate };
    int offset = 0;
    Type type = Type::NoteOn;
    std::uint8_t a = 0;     // NoteOn: voice          Param: parameter index (PAR_*)     ModTarget: kind (0 velocity, 1 LFO)
    std::uint8_t b = 0;     // NoteOn: note           Param: value 0..127                ModTarget: modulator/voice 0..5
    std::uint8_t c = 0;     // NoteOn: velocity       ModTarget: index into the mod-target list
    double ppq = 0.0;       // SeqRun / SeqLocate: host position in quarter notes (the sequencer grid is 4 steps per quarter)
};

class EngineHost
{
public:
    EngineHost();
    ~EngineHost();
    EngineHost (const EngineHost&) = delete;
    EngineHost& operator= (const EngineHost&) = delete;

    // Not real-time safe. maxBlock is informational (no allocation happens in process()).
    void prepare (double hostSampleRate);
    void reset();                                           // silence + restart (keeps kit)
    void loadKit (const std::uint8_t kit[LXR_KIT_BYTES]);   // not real-time safe? it is: pure computation, no allocation
    void setSeed (std::uint32_t seed);
    // Host tempo (float). The sequencer core only knows integer BPM, so it runs on a time axis scaled by
    // hostBpm / round(hostBpm): steps then land exactly on the host's grid (deviation S8).
    void setTempo (double hostBpm);
    void setFader (unsigned voice, float gain) { lxr_set_fader (engine, voice, gain); }
    void setMasterGain (float g) noexcept { master = g; }

    // Render n host frames (mono-compatible stereo, float, summed DAC1+DAC2). events: ascending offsets in [0,n).
    void process (float* left, float* right, int n, const HostEvent* events, int numEvents) noexcept;

    // Output latency in host samples (resampler look-ahead + at most one engine block of event quantisation)
    int latencySamples() const noexcept { return latency; }
    LxrEngine* raw() noexcept { return engine; }
    LxrSeq* sequencer() noexcept { return seq; }
    void loadDemoPattern();                                 // authored 1-bar beat in pattern 0

private:
    void renderTo (float* l, float* r, int n) noexcept;
    void apply (const HostEvent&) noexcept;

    LxrEngine* engine = nullptr;
    LxrSeq* seq = nullptr;
    double seqTicks = 0.0;                                  // injected 0.25 ms clock of the sequencer core
    double tickScale = 1.0;                                 // hostBpm / round(hostBpm)
    unsigned seqBpm = 120;
    static void sinkTrigger (void*, unsigned, unsigned, unsigned);
    static void sinkCc (void*, std::uint8_t, std::uint8_t, std::uint8_t, std::uint8_t);
    static void sinkKit (void*, unsigned);
    static void sinkTempo (void*, unsigned);
    Resampler resampler;
    double hostRate = 44100.0;
    float master = 1.0f;
    int latency = 0;
};
} // namespace lynn
