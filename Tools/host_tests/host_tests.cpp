// SPDX-License-Identifier: GPL-3.0-only
// JUCE-free tests of the host layer: resampler quality, block-size independence, event timing.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>
#include <algorithm>
#include "EngineHost.h"
#include "Resampler.h"
#include "SeqBridge.h"
#include "../../Source/Plugin/GeneratedParams.h"

using namespace lynn;

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { ++failures; std::printf ("FAIL: "); std::printf (__VA_ARGS__); std::printf ("\n"); } } while (0)

// --- resampler: a sine of known level must come out at the same level, with the alias/image floor low
static void resamplerQuality (double dstRate)
{
    Resampler r; r.prepare (44140.0, dstRate);
    const double f = 5000.0; double ph = 0;
    auto fill = [&] (float* l, float* rr, int n) { for (int i = 0; i < n; ++i) { l[i] = rr[i] = static_cast<float> (0.5 * std::sin (ph)); ph += 2 * M_PI * f / 44140.0; } };
    const int N = 1 << 16; std::vector<float> L (N), R (N);
    r.process (L.data(), R.data(), N, fill);
    // measure amplitude and residual of a best-fit sine at f (in the destination domain)
    double sc = 0, ss = 0, cc = 0, sg = 0, cg = 0;
    const int a = 4096; const int b = N;
    double w = 2 * M_PI * f / dstRate;
    for (int i = a; i < b; ++i) { double s = std::sin (w * i), c = std::cos (w * i); sc += L[i] * s; cc += L[i] * c; ss += s * s; sg += c * c; cg += s * c; }
    const double as = sc / ss, ac = cc / sg;                    // quadrature fit (orthogonal enough over many cycles)
    double err = 0, sig = 0;
    for (int i = a; i < b; ++i) { double m = as * std::sin (w * i) + ac * std::cos (w * i); err += (L[i] - m) * (L[i] - m); sig += m * m; }
    const double amp = std::sqrt (as * as + ac * ac);
    const double snr = 10 * std::log10 (sig / std::max (err, 1e-30));
    std::printf ("resampler 44140 -> %6.0f: gain %.5f, residual %.1f dB\n", dstRate, amp / 0.5, -snr);
    CHECK (std::fabs (amp / 0.5 - 1.0) < 0.002, "gain error at %g", dstRate);
    CHECK (snr > 90.0, "residual only %.1f dB at %g", snr, dstRate);
}

// --- block size independence: the host block size must not change the audio (events at fixed absolute times)
static std::vector<float> renderWithBlocks (double rate, int block, int totalFrames)
{
    EngineHost h; h.prepare (rate);
    std::uint8_t kit[LXR_KIT_BYTES] = {0};
    lynn::params::fillDefaultKit (kit);
    h.loadKit (kit);
    struct Abs { int t; HostEvent e; };
    std::vector<Abs> evs { { 100, { 0, HostEvent::Type::NoteOn, 0, 60, 100 } }, { 5000, { 0, HostEvent::Type::NoteOn, 3, 60, 100 } },
                           { 9000, { 0, HostEvent::Type::NoteOn, 5, 60, 100 } } };
    std::vector<float> out (static_cast<size_t> (totalFrames));
    std::vector<float> l (static_cast<size_t> (block)), r (static_cast<size_t> (block));
    for (int pos = 0; pos < totalFrames; pos += block)
    {
        const int n = std::min (block, totalFrames - pos);
        std::vector<HostEvent> here;
        for (auto& a : evs) if (a.t >= pos && a.t < pos + n) { HostEvent e = a.e; e.offset = a.t - pos; here.push_back (e); }
        h.process (l.data(), r.data(), n, here.data(), static_cast<int> (here.size()));
        std::copy (l.begin(), l.begin() + n, out.begin() + pos);
    }
    return out;
}

static void blockSizeIndependence()
{
    const int total = 20000;
    const auto ref = renderWithBlocks (48000.0, 64, total);
    float peak = 0; for (float v : ref) peak = std::max (peak, std::fabs (v));
    CHECK (peak > 0.05f, "reference is silent (peak %g)", peak);
    for (int b : { 1, 7, 32, 65, 128, 480, 1024, 4096 })
    {
        const auto o = renderWithBlocks (48000.0, b, total);
        double maxd = 0; for (int i = 0; i < total; ++i) maxd = std::max (maxd, (double) std::fabs (o[i] - ref[i]));
        std::printf ("block %5d: max |diff| vs block 64 = %g\n", b, maxd);
        CHECK (maxd == 0.0, "block size %d changes the audio", b);
    }
}

// --- event timing: a trigger at host offset s must become audible within one engine block + filter delay
static void eventLatency (double rate)
{
    const auto o = renderWithBlocks (rate, 256, 6000);
    int first = -1; for (int i = 0; i < 6000; ++i) if (std::fabs (o[i]) > 1e-4f) { first = i; break; }
    EngineHost h; h.prepare (rate);
    const int lat = h.latencySamples();
    std::printf ("rate %6.0f: first sound %d samples after the note at 100 (reported latency %d)\n", rate, first - 100, lat);
    CHECK (first >= 100 && first - 100 <= lat + 4, "event latency %d exceeds reported %d", first - 100, lat);
}

// --- sequencer in host time: onsets of a quarter-note kick must stay on the host grid (no drift), any tempo/block size
static void sequencerGrid (double rate, double bpm, int block)
{
    EngineHost h; h.prepare (rate);
    std::uint8_t kit[LXR_KIT_BYTES] = {0};
    lynn::params::fillDefaultKit (kit);
    h.loadKit (kit);
    {   // a short, loud kick so that onsets are unambiguous (the factory kick rings for ~0.5 s)
        HostEvent e; e.offset = 0; e.type = HostEvent::Type::Param; e.a = 50 /* PAR_VELOD1 */; e.b = 5; float a[64], b[64]; h.process (a, b, 64, &e, 1);
    }
    h.setTempo (bpm);
    for (int st : { 0, 4, 8, 12 })
    {
        lxrseq_set_main_step (h.sequencer(), 0, 0, st, 1);
        lxrseq_set_step (h.sequencer(), 0, 0, st, 127, 100, 60);
        lxrseq_set_step_timing (h.sequencer(), 0, 0, st, 0, 7);
    }
    const double beat = 60.0 / bpm * rate;
    const int total = static_cast<int> (beat * 4 * 16);                // 16 bars
    std::vector<float> out (static_cast<size_t> (total)), l (static_cast<size_t> (block)), r (static_cast<size_t> (block));
    for (int pos = 0; pos < total; pos += block)
    {
        const int n = std::min (block, total - pos);
        HostEvent run; run.type = HostEvent::Type::SeqRun; run.offset = 0;
        h.process (l.data(), r.data(), n, pos == 0 ? &run : nullptr, pos == 0 ? 1 : 0);
        std::copy (l.begin(), l.begin() + n, out.begin() + pos);
    }
    // onsets: |x| crosses 0.05 after at least 60 ms below 0.01
    std::vector<int> on; int quiet = 1 << 20;
    for (int i = 0; i < total; ++i)
    {
        const float a = std::fabs (out[static_cast<size_t> (i)]);
        if (a > 0.05f && quiet > static_cast<int> (0.06 * rate)) on.push_back (i);
        if (a < 0.01f) ++quiet; else if (a > 0.05f) quiet = 0;
    }
    CHECK (on.size() >= 60, "only %zu onsets at %g bpm", on.size(), bpm);
    if (on.size() < 3) return;
    double worst = 0;
    for (size_t k = 1; k < on.size(); ++k)
    {
        const double ideal = on[0] + static_cast<double> (k) * beat;
        worst = std::max (worst, std::fabs (on[k] - ideal));
    }
    const double tol = 64.0 / LXR_ENGINE_RATE * rate * 2.0;           // two engine blocks (offsets are measured against the first onset, each is quantised to a block)
    std::printf ("sequencer %6.0f Hz %6.2f bpm block %4d: %zu onsets, max deviation from the host grid %.1f samples (tol %.0f)\n",
                 rate, bpm, block, on.size(), worst, tol);
    CHECK (worst <= tol, "grid deviation %.1f > %.1f", worst, tol);
}

// --- sequencer bridge: UI commands reach the real sequencer (all 64 patterns), state round-trips, queue overflow loses nothing
static void bridgeTests()
{
    EngineHost h; h.prepare (48000.0); SeqBridge b;
    auto mask = [&] (int pat, int track) { std::uint16_t m[4]; unsigned len; lxrseq_get_main_steps (h.sequencer(), pat, track, m, &len); return m[0]; };
    auto length = [&] (int pat, int track) { std::uint16_t m[4]; unsigned len = 0; lxrseq_get_main_steps (h.sequencer(), pat, track, m, &len); return len; };
    CHECK (b.applyUiCommand ({ 0, 2, 3, 1 }, "step"), "step command rejected");
    CHECK (b.applyUiCommand ({ 0, 2, 3, 90 }, "stepVol"), "stepVol rejected");
    CHECK (!b.applyUiCommand ({ 0, 9, 3, 1 }, "step"), "bad track accepted");
    CHECK (!b.applyUiCommand ({ 64, 0, 3, 1 }, "step"), "bad pattern accepted");
    CHECK (!b.applyUiCommand ({}, "nonsense"), "unknown command accepted");
    b.drain (h);
    CHECK ((mask (0, 2) & (1u << 3)) != 0, "step 3 of track 2 not set in the sequencer");
    b.applyUiCommand ({ 0, 2 }, "clearTrack"); b.drain (h);
    CHECK (mask (0, 2) == 0, "clearTrack did not clear");
    b.applyUiCommand ({ 0, 1, 21 }, "trackLength"); b.drain (h);
    CHECK (length (0, 1) == 21, "length %u", length (0, 1));

    // the whole bank: edits address their own pattern and do not leak into others
    b.applyUiCommand ({ 5, 0, 7, 1 }, "step"); b.applyUiCommand ({ 63, 6, 0, 1 }, "step"); b.applyUiCommand ({ 5, 3, 24 }, "trackLength"); b.applyUiCommand ({ 5, 40 }, "shuffle");
    b.drain (h);
    CHECK ((mask (5, 0) & (1u << 7)) && (mask (63, 6) & 1u) && mask (0, 0) == 0 && length (5, 3) == 24 && length (0, 3) == 16, "pattern addressing");
    b.applyUiCommand ({ 5, 9 }, "copyPattern"); b.drain (h);
    CHECK ((mask (9, 0) & (1u << 7)) && length (9, 3) == 24, "copyPattern");
    b.applyUiCommand ({ 9 }, "clearPattern"); b.drain (h);
    CHECK (mask (9, 0) == 0 && length (9, 3) == 16, "clearPattern");
    b.applyUiCommand ({ 5, 1, 2, 1 }, "copyTrack"); b.drain (h);
    b.applyUiCommand ({ 3, 1 }, "mute"); b.drain (h);
    CHECK (b.muted (3) && !b.muted (2), "mute mirror");

    // pattern select while stopped is immediate; song entries/mode reach the sequencer
    b.applyUiCommand ({ 5 }, "selectPattern"); b.drain (h);
    CHECK (lxrseq_active_pattern (h.sequencer()) == 5, "select pattern while stopped must switch at once (%u)", lxrseq_active_pattern (h.sequencer()));
    b.applyUiCommand ({ 0, 5 }, "songSet"); b.applyUiCommand ({ 1, 2 }, "songSet"); b.applyUiCommand ({ 1 }, "songMode"); b.drain (h);
    CHECK (lxrseq_song_mode (h.sequencer()) == 1 && b.songState().entries[1] == 2, "song state");

    // audition: a UI trigger sounds without any sequencer or MIDI, and reports a level
    {
        EngineHost ha; ha.prepare (48000.0); SeqBridge ba;
        std::uint8_t k[LXR_KIT_BYTES]; lynn::params::fillDefaultKit (k); ha.loadKit (k);
        std::vector<float> l (512), r (512);
        ba.audition (0, 110); ba.drain (ha);
        float pk = 0; for (int i = 0; i < 20; ++i) { ha.process (l.data(), r.data(), 512, nullptr, 0); for (float v : l) pk = std::max (pk, std::fabs (v)); }
        ba.publishPlayhead (ha, 120.0, pk, pk);
        const auto lv = ba.readLevel();
        CHECK (pk > 0.05f && lv.l == pk, "audition silent or level not reported (peak %g, meter %g)", pk, lv.l);
        CHECK (ba.readLevel().l == 0.f, "meter peak must reset after reading");
    }

    // Euclid: the firmware's generator (golden values taken from the oracle: Tools/ref-harness/golden/seq/euclid_*.ev)
    {
        auto bits = [&] (int len, int st, int rot) { SeqBridge e; const auto a = e.euclidPreview (len, st, rot); unsigned long long m = 0; for (int i = 0; i < 64; ++i) if (a[(size_t) i]) m |= 1ull << i; return m; };
        CHECK (bits (16, 5, 0) == 0x1249ull, "euclid 16/5: %llx", bits (16, 5, 0));
        CHECK (bits (16, 7, 3) == 0xa54aull, "euclid 16/7 rot 3: %llx", bits (16, 7, 3));
        CHECK (bits (13, 5, 0) == 0x0529ull, "euclid 13/5: %llx", bits (13, 5, 0));
        CHECK (bits (32, 9, 0) == 0x12244891ull, "euclid 32/9: %llx", bits (32, 9, 0));
        const auto m64 = bits (64, 17, 5); int pop = 0; for (int i = 0; i < 64; ++i) pop += (m64 >> i) & 1;
        CHECK (pop == 17, "euclid 64/17 rot 5 has %d steps (the unguarded upstream shift erased it)", pop);
        SeqBridge e; EngineHost he; he.prepare (48000.0);
        e.applyUiCommand ({ 2, 1, 16, 5, 0 }, "euclid"); e.drain (he);
        std::uint16_t m[4]; unsigned len = 0; lxrseq_get_main_steps (he.sequencer(), 2, 1, m, &len);
        CHECK (m[0] == 0x1249 && len == 16, "euclid command reached the sequencer (mask %04x, length %u; upstream would store 0 for 16)", m[0], len);
        CHECK (e.pattern (2).tracks[1].length == 16 && e.pattern (2).tracks[1].on[3] && !e.pattern (2).tracks[1].on[4], "euclid mirror");
        CHECK (!e.applyUiCommand ({ 2, 1, 16, 0, 0 }, "euclid") && !e.applyUiCommand ({ 99, 1, 16, 5, 0 }, "euclid"), "bad euclid arguments accepted");
    }

    // roll: while held the voice retriggers at the roll rate (every step at rate 5 = 1/16), one-shot (rate 0) fires once
    {
        auto rollOnsets = [&] (int rate)
        {
            EngineHost hr; hr.prepare (48000.0); SeqBridge br;
            std::uint8_t k[LXR_KIT_BYTES]; lynn::params::fillDefaultKit (k); hr.loadKit (k);
            HostEvent sp; sp.type = HostEvent::Type::Param; sp.a = 50; sp.b = 5; float a_[64], b_[64]; hr.process (a_, b_, 64, &sp, 1);
            hr.setTempo (120.0);
            br.applyUiCommand ({ (double) rate }, "rollRate"); br.drain (hr);
            std::vector<float> l (48000 * 3), r (l.size());
            HostEvent run; run.type = HostEvent::Type::SeqRun; bool on = false, off = false;
            for (size_t pos = 0; pos < l.size(); pos += 256)
            {
                if (pos >= 256 * 10 && !on) { on = true; br.applyUiCommand ({ 0, 1 }, "roll"); }
                if (pos >= 256 * 10 + 48000 && !off) { off = true; br.applyUiCommand ({ 0, 0 }, "roll"); }
                br.drain (hr);
                hr.process (l.data() + pos, r.data() + pos, 256, pos == 0 ? &run : nullptr, pos == 0 ? 1 : 0);
            }
            int n = 0, quiet = 1 << 20;
            for (float v : l) { const float a = std::fabs (v); if (a > 0.05f && quiet > 2400) ++n; if (a < 0.01f) ++quiet; else if (a > 0.05f) quiet = 0; }
            return n;
        };
        const int every16 = rollOnsets (5), every8 = rollOnsets (4), oneShot = rollOnsets (0);
        std::printf ("roll for 1 s at 120 bpm: 1/16 -> %d hits, 1/8 -> %d, one-shot -> %d\n", every16, every8, oneShot);
        CHECK (every16 >= 7 && every16 <= 10, "1/16 roll hits: %d", every16);
        CHECK (every8 >= 3 && every8 <= 6, "1/8 roll hits: %d", every8);
        CHECK (oneShot == 1, "one-shot roll must fire once, not %d times", oneShot);
    }

    // p-locks: command -> sequencer data (cortex destination numbering), clearing, and the audible effect (restore on the next trigger)
    {
        SeqBridge bl; EngineHost hl; hl.prepare (48000.0);
        CHECK (bl.applyUiCommand ({ 3, 1, 9, 1, 88, 77 }, "stepLock"), "stepLock rejected");
        CHECK (bl.applyUiCommand ({ 3, 1, 9, 2, 200, 5 }, "stepLock"), "stepLock rejected (CC2 range)");
        CHECK (!bl.applyUiCommand ({ 3, 1, 9, 3, 88, 1 }, "stepLock") && !bl.applyUiCommand ({ 3, 1, 9, 1, 300, 1 }, "stepLock"), "bad slot / parameter accepted");
        bl.drain (hl);
        unsigned d = 0, v = 0;
        lxrseq_get_plock (hl.sequencer(), 3, 1, 9, 1, &d, &v); CHECK (d == 89 && v == 77, "slot 1 stored as PAR+1 (%u,%u)", d, v);
        lxrseq_get_plock (hl.sequencer(), 3, 1, 9, 2, &d, &v); CHECK (d == 200 && v == 5, "slot 2 (CC2 range) stored raw (%u,%u)", d, v);
        bl.applyUiCommand ({ 3, 1, 9, 1, -1, 0 }, "stepLock"); bl.drain (hl);
        lxrseq_get_plock (hl.sequencer(), 3, 1, 9, 1, &d, &v); CHECK (d == 0xff, "lock cleared (%u)", d);

        // kick with Drum 1 "Pitch Mod" locked to 0 on step 1, none on step 9: the first hit has no pitch sweep (low start frequency), the
        // second one is restored to the unlocked sound (voice volume is unsuitable here: the engine smooths it over ~100 ms)
        auto run = [&] (bool locked, double& first, double& second)
        {
            EngineHost he; he.prepare (48000.0); SeqBridge be;
            std::uint8_t k[LXR_KIT_BYTES]; lynn::params::fillDefaultKit (k); he.loadKit (k);
            HostEvent sp; sp.type = HostEvent::Type::Param; sp.a = 50; sp.b = 5; float a_[64], b_[64]; he.process (a_, b_, 64, &sp, 1);     // short decay
            for (int st : { 0, 8 }) { be.applyUiCommand ({ 0, 0, (double) st, 1 }, "step"); be.applyUiCommand ({ 0, 0, (double) st, 127 }, "stepVol"); }
            if (locked) be.applyUiCommand ({ 0, 0, 0, 1, 74, 0 }, "stepLock");
            be.drain (he); he.setTempo (120.0);
            std::vector<float> o (48000 * 2), o2 (o.size());
            HostEvent run; run.type = HostEvent::Type::SeqRun;
            for (size_t pos = 0; pos < o.size(); pos += 256) he.process (o.data() + pos, o2.data() + pos, 256, pos == 0 ? &run : nullptr, pos == 0 ? 1 : 0);
            auto zc = [&] (double t0, double t1) { int n = 0; size_t a = (size_t) (t0 * 48000), b = (size_t) (t1 * 48000), z0 = 0, z1 = 0; for (size_t i = a + 1; i < b; ++i) if (o[i - 1] < 0 && o[i] >= 0) { if (!n) z0 = i; z1 = i; ++n; } return n > 1 ? (n - 1) * 48000.0 / (double) (z1 - z0) : 0.0; };
            first = zc (0.006, 0.020); second = zc (1.006, 1.020);                  // start frequency of each hit
        };
        double f0, s0, f1, s1; run (false, f0, s0); run (true, f1, s1);
        std::printf ("p-lock: start frequency of the two hits unlocked %.0f / %.0f Hz, with the pitch-mod lock %.0f / %.0f Hz\n", f0, s0, f1, s1);
        CHECK (f0 > 120 && std::fabs (f0 - s0) < 0.1 * f0 && f1 < 0.5 * f0 && std::fabs (s1 - s0) < 0.1 * s0, "p-lock must remove the sweep of the locked hit only and be restored for the next hit");
    }

    // state round-trip: several patterns, a song, mutes
    b.applyUiCommand ({ 12, 4, 10, 1 }, "step"); b.applyUiCommand ({ 12, 4, 10, 3 }, "stepFlam"); b.applyUiCommand ({ 12, 4, 10, 11 }, "stepShift");
    b.applyUiCommand ({ 12, 64 }, "shuffle"); b.applyUiCommand ({ 12, 4, 10, 2, 114, 33 }, "stepLock");
    const std::string blob = b.serialize();
    SeqBridge c; CHECK (c.deserialize (reinterpret_cast<const std::uint8_t*> (blob.data()), blob.size()), "deserialize failed");
    CHECK (c.serialize() == blob, "state not stable through a round-trip");
    CHECK (c.pattern (12).tracks[4].lockPar2[10] == 114 && c.pattern (12).tracks[4].lockVal2[10] == 33 && c.pattern (12).tracks[4].lockPar1[10] == lynn::kNoLock && c.pattern (12).tracks[4].flam[10] == 3 && c.pattern (12).tracks[4].shift[10] == 11 && c.pattern (12).shuffle == 64 && c.pattern (5).tracks[3].length == 24 && c.pattern (63).tracks[6].on[0], "state content");
    CHECK (c.muted (3) && c.songState().enabled && c.songState().entries[1] == 2, "mutes and song in the state");
    CHECK (!c.deserialize (reinterpret_cast<const std::uint8_t*> (blob.data()), blob.size() - 1), "truncated state accepted");
    {   // restoring into a bridge whose engine already holds other data must make the engine match exactly (diff against the mirror)
        EngineHost h3; h3.prepare (48000.0); SeqBridge d;
        d.applyUiCommand ({ 12, 0, 1, 1 }, "step"); d.drain (h3);
        d.deserialize (reinterpret_cast<const std::uint8_t*> (blob.data()), blob.size()); d.drain (h3);
        std::uint16_t m[4]; unsigned len; lxrseq_get_main_steps (h3.sequencer(), 12, 0, m, &len);
        CHECK (m[0] == 0, "stale step survived a state restore");
        lxrseq_get_main_steps (h3.sequencer(), 12, 4, m, &len); CHECK ((m[0] & (1u << 10)) != 0, "restored step missing");
    }

    // overflow: more commands than the queue holds, applied in order once the audio side drains
    SeqBridge o; EngineHost h2; h2.prepare (48000.0);
    for (int rep = 0; rep < 40; ++rep) for (int t = 0; t < 7; ++t) for (int i = 0; i < 64; ++i)
        o.applyUiCommand ({ 0, (double) t, (double) i, (double) ((rep + i) & 1) }, "step");        // last rep (39): on where (39+i) odd
    for (int k = 0; k < 8; ++k) { o.drain (h2); o.flush(); }
    std::uint16_t m[4]; unsigned len; lxrseq_get_main_steps (h2.sequencer(), 0, 6, m, &len);
    CHECK (m[0] == 0x5555 && m[3] == 0x5555, "overflowed commands lost or reordered: %04x", m[0]);
    std::printf ("bridge tests done\n");
}

static void writeDemo (const char* path)
{
    const double rate = 48000.0, bpm = 120.0; const int total = static_cast<int> (rate * 60.0 / bpm * 4 * 4);   // 4 bars
    EngineHost h; h.prepare (rate);
    std::uint8_t kit[LXR_KIT_BYTES] = {0};
    lynn::params::fillDefaultKit (kit);
    h.loadKit (kit); h.setTempo (bpm); h.loadDemoPattern();
    std::vector<float> l (static_cast<size_t> (total)), r (static_cast<size_t> (total));
    HostEvent run; run.type = HostEvent::Type::SeqRun; run.offset = 0;
    for (int pos = 0; pos < total; pos += 256)
    {
        const int n = std::min (256, total - pos);
        h.process (l.data() + pos, r.data() + pos, n, pos == 0 ? &run : nullptr, pos == 0 ? 1 : 0);
    }
    FILE* f = std::fopen (path, "wb"); if (!f) return;
    auto w32 = [&] (std::uint32_t v) { std::fwrite (&v, 4, 1, f); }; auto w16 = [&] (std::uint16_t v) { std::fwrite (&v, 2, 1, f); };
    std::fwrite ("RIFF", 1, 4, f); w32 (36 + total * 4); std::fwrite ("WAVEfmt ", 1, 8, f); w32 (16); w16 (1); w16 (2); w32 (48000); w32 (48000 * 4); w16 (4); w16 (16);
    std::fwrite ("data", 1, 4, f); w32 (total * 4);
    for (int i = 0; i < total; ++i) for (float v : { l[static_cast<size_t> (i)], r[static_cast<size_t> (i)] }) { float c = std::max (-1.f, std::min (1.f, v)); w16 (static_cast<std::uint16_t> (static_cast<std::int16_t> (c * 32767.f))); }
    std::fclose (f);
    std::printf ("demo written to %s\n", path);
}

// the generated parameter table must agree with the engine it was generated for
static void paramTableTests()
{
    CHECK (lxr_num_mod_targets() == sizeof (lynn::params::kModTargetPar) / sizeof (lynn::params::kModTargetPar[0]),
           "mod target count: engine %u, table %zu", lxr_num_mod_targets(), sizeof (lynn::params::kModTargetPar) / sizeof (lynn::params::kModTargetPar[0]));
    for (const auto& d : lynn::params::kSound)
    {
        CHECK (d.par < LXR_KIT_BYTES, "parameter %s outside the kit", d.id);
        CHECK (d.min <= d.def && d.def <= d.max, "default of %s outside its range", d.id);
    }
    // driving every parameter to both ends of its domain must stay finite and bounded (UB for out-of-domain values is why ranges matter)
    EngineHost h; h.prepare (48000.0);
    std::uint8_t kit[LXR_KIT_BYTES] = {0}; lynn::params::fillDefaultKit (kit);
    h.loadKit (kit);
    std::vector<float> l (256), r (256);
    for (int pass = 0; pass < 2; ++pass)
    {
        for (const auto& d : lynn::params::kSound)
        {
            HostEvent e; e.offset = 0;
            if (d.kind == lynn::params::Kind::Target) { e.type = HostEvent::Type::ModTarget; e.a = (std::uint8_t) d.targetKind; e.b = (std::uint8_t) d.targetIndex; e.c = pass ? d.max : d.min; }
            else { e.type = HostEvent::Type::Param; e.a = (std::uint8_t) d.par; e.b = pass ? d.max : d.min; }
            h.process (l.data(), r.data(), 32, &e, 1);
        }
        for (int v = 0; v < 7; ++v) { HostEvent n; n.type = HostEvent::Type::NoteOn; n.a = (std::uint8_t) v; n.b = 60; n.c = 120; h.process (l.data(), r.data(), 256, &n, 1); }
        for (int b = 0; b < 100; ++b)
        {
            h.process (l.data(), r.data(), 256, nullptr, 0);
            for (int i = 0; i < 256; ++i) { CHECK (std::isfinite (l[i]) && std::isfinite (r[i]) && std::fabs (l[i]) < 16.f, "non-finite/huge output (pass %d)", pass); if (failures) return; }
        }
    }
    std::printf ("param table tests done (%d parameters)\n", lynn::params::kNumSound);
}

int main (int argc, char** argv)
{
    if (argc > 2 && !std::strcmp (argv[1], "--demo")) { writeDemo (argv[2]); return 0; }
    bridgeTests();
    paramTableTests();
    for (double r : { 44100.0, 48000.0, 88200.0, 96000.0, 192000.0 }) resamplerQuality (r);
    blockSizeIndependence();
    for (double r : { 44100.0, 48000.0, 96000.0 }) eventLatency (r);
    for (double bpm : { 120.0, 120.5, 133.37, 87.0 }) for (int b : { 64, 480 }) sequencerGrid (48000.0, bpm, b);
    sequencerGrid (44100.0, 140.0, 1024); sequencerGrid (96000.0, 99.9, 77);
    std::printf (failures ? "%d FAILURE(S)\n" : "all host tests passed\n", failures);
    return failures ? 1 : 0;
}
