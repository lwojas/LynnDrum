// SPDX-License-Identifier: GPL-3.0-only
#include "EngineHost.h"
#include <cmath>

namespace lynn
{
EngineHost::EngineHost()
{
    engine = lxr_create (0x1234ABCDu);
    LxrSeqSink sink {};
    sink.ctx = this;
    sink.trigger = &EngineHost::sinkTrigger;
    sink.cc = &EngineHost::sinkCc;
    sink.originalCc = lxr_original_cc_table (engine);
    sink.kit_change = &EngineHost::sinkKit;
    sink.tempo = &EngineHost::sinkTempo;
    seq = lxrseq_create (&sink, 0x1234ABCDu);
}
EngineHost::~EngineHost() { lxrseq_destroy (seq); lxr_destroy (engine); }

void EngineHost::sinkTrigger (void* c, unsigned t, unsigned n, unsigned v) { lxr_trigger (static_cast<EngineHost*> (c)->engine, t, n, v); }
void EngineHost::sinkCc (void* c, std::uint8_t st, std::uint8_t d1, std::uint8_t d2, std::uint8_t u) { lxr_cc (static_cast<EngineHost*> (c)->engine, st, d1, d2, u); }
void EngineHost::sinkKit (void*, unsigned) {}                       // kit-per-pattern arrives with phase S3
void EngineHost::sinkTempo (void* c, unsigned bpm) { lxr_set_tempo (static_cast<EngineHost*> (c)->engine, bpm); }

void EngineHost::prepare (double hostSampleRate)
{
    hostRate = hostSampleRate;
    resampler.prepare (LXR_ENGINE_RATE, hostSampleRate);
    latency = static_cast<int> (std::ceil ((resampler.latencySourceSamples() + 64.0) / resampler.ratio()));
}

void EngineHost::reset() { resampler.reset(); lxrseq_set_run (seq, 0); }
void EngineHost::loadKit (const std::uint8_t kit[LXR_KIT_BYTES]) { lxr_load_kit (engine, kit); }
void EngineHost::setSeed (std::uint32_t seed) { lxr_set_seed (engine, seed); }
void EngineHost::setTempo (double hostBpm)
{
    if (!(hostBpm >= 20.0 && hostBpm <= 400.0)) return;
    const unsigned b = static_cast<unsigned> (hostBpm + 0.5);
    // seq_calcDeltaT() uses the *integer* quotient (1000*60)/bpm [ms]: the real speed of the core at integer b is
    // 60000/floor(60000/b) BPM (e.g. 87 -> 87.1), not b. Scale the injected clock to hit the host tempo exactly.
    const double effectiveBpm = 60000.0 / std::floor (60000.0 / static_cast<double> (b));
    tickScale = hostBpm / effectiveBpm;
    if (b != seqBpm) { seqBpm = b; lxrseq_set_tempo (seq, b); }
}

void EngineHost::apply (const HostEvent& e) noexcept
{
    switch (e.type)
    {
        case HostEvent::Type::NoteOn:  lxr_trigger (engine, e.a, e.b, e.c); break;
        case HostEvent::Type::Param:   lxr_param (engine, e.a, e.b); lxrseq_set_param (seq, e.a, e.b); break;
        case HostEvent::Type::ModTarget: lxr_set_mod_target (engine, e.a, e.b, e.c); break;
        case HostEvent::Type::SeqRun:
        case HostEvent::Type::SeqLocate:
        {
            // position on the 16th-note / 24-sub-tick grid; the next sub-tick to fire is ceil(u)
            const double steps = e.ppq < 0 ? 0.0 : e.ppq * 4.0;
            double n = std::floor (steps);
            const double u = (steps - n) * 24.0;
            double k = std::ceil (u - 1e-9);
            double remaining = k - u;
            if (k >= 24.0) { n += 1.0; remaining = 24.0 - u; k = 0.0; }
            lxrseq_start_at (seq, static_cast<std::uint32_t> (n), static_cast<unsigned> (k), remaining < 0 ? 0 : remaining);
            break;
        }
        case HostEvent::Type::SeqStop: lxrseq_set_run (seq, 0); break;
    }
}

void EngineHost::renderTo (float* l, float* r, int n) noexcept
{
    LxrEngine* e = engine;
    LxrSeq* sq = seq;
    constexpr double ticksPerBlock = LXR_BLOCK_FRAMES / double (LXR_ENGINE_RATE) / 0.00025;   // 5.8 systicks
    resampler.process (l, r, n, [this, e, sq, ticksPerBlock] (float* dl, float* dr, int frames)
    {
        // firmware main loop: seq_tick(); calcNextSampleBlock()  - one sequencer poll per engine block
        seqTicks += ticksPerBlock * tickScale;
        lxrseq_tick (sq, static_cast<std::uint32_t> (seqTicks));
        // frames == LXR_BLOCK_FRAMES by construction of the resampler
        int16_t st1[LXR_BLOCK_FRAMES * 2], st2[LXR_BLOCK_FRAMES * 2];
        lxr_render_block (e, st1, st2);
        constexpr float k = 1.0f / 32768.0f;
        for (int i = 0; i < frames; ++i)
        {
            dl[i] = (static_cast<float> (st1[2 * i])     + static_cast<float> (st2[2 * i]))     * k;
            dr[i] = (static_cast<float> (st1[2 * i + 1]) + static_cast<float> (st2[2 * i + 1])) * k;
        }
    });
    if (master != 1.0f)
        for (int i = 0; i < n; ++i) { l[i] *= master; r[i] *= master; }
}

void EngineHost::process (float* left, float* right, int n, const HostEvent* events, int numEvents) noexcept
{
    int pos = 0;
    for (int i = 0; i < numEvents; ++i)
    {
        const int off = events[i].offset < pos ? pos : (events[i].offset > n ? n : events[i].offset);
        if (off > pos) { renderTo (left + pos, right + pos, off - pos); pos = off; }
        apply (events[i]);
    }
    if (pos < n) renderTo (left + pos, right + pos, n - pos);
}
} // namespace lynn

void lynn::EngineHost::loadDemoPattern()
{
    // An authored 4/4 beat (pattern 0): kick on the quarter notes, snare on 2 and 4, closed hats on the 8ths,
    // open hat on the last off-beat. Written for LynnDrum; not taken from the LXR.
    LxrSeq* q = seq;
    auto on = [q] (int track, int step, int vol, int note = 60)
    {
        lxrseq_set_main_step (q, 0, track, step, 1);
        lxrseq_set_step (q, 0, track, step, vol, 100, note);
        lxrseq_set_step_timing (q, 0, track, step, 0, 7);
    };
    for (int s : { 0, 4, 8, 12 }) on (0, s, 110);
    for (int s : { 4, 12 })        on (3, s, 105);
    for (int s = 0; s < 16; s += 2) on (5, s, s % 4 ? 70 : 95);
    on (6, 14, 90);
}
