// SPDX-License-Identifier: GPL-3.0-only
// Host-transport behaviour of the processor with a scripted AudioPlayHead: start at an arbitrary position, locate, loop wrap.
#include <juce_audio_processors/juce_audio_processors.h>
#include <cmath>
#include <cstdio>
#include "PluginProcessor.h"

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { ++failures; std::printf ("FAIL: "); std::printf (__VA_ARGS__); std::printf ("\n"); } } while (0)

struct FakeHost : juce::AudioPlayHead
{
    bool playing = false, looping = false; double ppq = 0, bpm = 120, loopA = 0, loopB = 0;
    juce::Optional<PositionInfo> getPosition() const override
    {
        PositionInfo p; p.setIsPlaying (playing); p.setBpm (bpm); p.setPpqPosition (ppq); p.setIsLooping (looping);
        p.setLoopPoints (juce::AudioPlayHead::LoopPoints { loopA, loopB });
        return p;
    }
};

// Renders the processor with the host script and returns the times (seconds from the start) of kick onsets.
struct Run
{
    LynnDrumProcessor p; FakeHost host; double sr = 48000; int block = 256; std::vector<double> onsets; double t = 0; float quiet = 1e9;
    Run()
    {
        p.setPlayHead (&host);
        p.prepareToPlay (sr, block);
        auto& b = p.bridge();
        for (int s = 0; s < 64; ++s) for (int tr = 0; tr < 7; ++tr) b.applyUiCommand ({ (double) tr, (double) s, 0 }, "step");   // empty pattern
        b.applyUiCommand ({ 0, 0, 1 }, "step"); b.applyUiCommand ({ 0, 0, 127 }, "stepVol");                                       // kick on step 1 of 16 only
        p.apvts.getParameter ("velod1")->setValueNotifyingHost (p.apvts.getParameter ("velod1")->convertTo0to1 (5.f));
        p.apvts.getParameter ("pan1")->setValueNotifyingHost (0.5f);
        for (int i = 0; i < 4; ++i) step (false);                                                                                  // apply the edits
        onsets.clear(); t = 0;
    }
    void step (bool advance)
    {
        juce::AudioBuffer<float> buf (2, block); juce::MidiBuffer m;
        p.processBlock (buf, m);
        for (int i = 0; i < block; ++i)
        {
            const float a = std::fabs (buf.getSample (0, i));
            if (a > 0.04f && quiet > 0.06 * sr) onsets.push_back (t + i / sr);
            if (a < 0.008f) quiet += 1.f; else if (a > 0.04f) quiet = 0.f;
        }
        t += block / sr;
        if (advance && host.playing) { host.ppq += block / sr * host.bpm / 60.0; if (host.looping && host.ppq >= host.loopB) host.ppq = host.loopA + (host.ppq - host.loopB); }
    }
    void run (double seconds) { for (int i = 0; i < (int) (seconds * sr / block); ++i) step (true); }
};

int main()
{
    juce::ScopedJuceInitialiser_GUI init;
    const double stepSec = 0.125;                                   // one 16th at 120 bpm
    {   // start at 0.75 beats (= step 3): the first kick (step 0 of the next bar) comes 13 steps later
        Run r; r.host.ppq = 0.75; r.host.playing = true; r.run (4.0);
        std::printf ("start at ppq 0.75: onsets %zu, first at %.3f s (ideal %.3f)\n", r.onsets.size(), r.onsets.empty() ? -1.0 : r.onsets[0], 13 * stepSec);
        CHECK (!r.onsets.empty() && std::fabs (r.onsets[0] - 13 * stepSec) < 0.02, "start position not anchored to the host grid");
        CHECK (r.onsets.size() >= 2 && std::fabs ((r.onsets[1] - r.onsets[0]) - 2.0) < 0.01, "bar period");
    }
    {   // start exactly on a bar: kick immediately
        Run r; r.host.ppq = 8.0; r.host.playing = true; r.run (1.0);
        CHECK (!r.onsets.empty() && r.onsets[0] < 0.02, "start on the bar did not fire immediately (%.3f)", r.onsets.empty() ? -1.0 : r.onsets[0]);
    }
    {   // start between two sub-ticks: 0.76 beats = step 3.04
        Run r; r.host.ppq = 0.76; r.host.playing = true; r.run (3.0);
        CHECK (!r.onsets.empty() && std::fabs (r.onsets[0] - (16 - 3.04) * stepSec) < 0.02, "fractional start: first onset %.3f", r.onsets.empty() ? -1.0 : r.onsets[0]);
    }
    {   // locate while playing: from 1.0 to 6.25 beats (absolute step 25 -> 7 steps to the next bar)
        Run r; r.host.ppq = 0.0; r.host.playing = true; r.run (1.0);
        const size_t before = r.onsets.size(); const double tj = r.t; r.host.ppq = 6.25; r.run (2.0);
        CHECK (r.onsets.size() > before, "no kick after the locate");
        if (r.onsets.size() > before) { const double d = r.onsets[before] - tj; std::printf ("locate: next kick %.3f s after the jump (ideal %.3f)\n", d, 7 * stepSec); CHECK (std::fabs (d - 7 * stepSec) < 0.02, "locate not re-anchored"); }
    }
    {   // loop 0..2 beats: the pattern restarts with the loop, so the kick falls on every loop start (1 s), not every 2 s
        Run r; r.host.playing = true; r.host.looping = true; r.host.loopA = 0; r.host.loopB = 2.0; r.host.ppq = 0.0; r.run (6.0);
        std::printf ("loop 0..2 beats: %zu kicks in 6 s\n", r.onsets.size());
        CHECK (r.onsets.size() >= 6, "loop wrap not re-anchored (%zu kicks, expected 6)", r.onsets.size());
        for (size_t i = 1; i < r.onsets.size(); ++i) CHECK (std::fabs ((r.onsets[i] - r.onsets[i - 1]) - 1.0) < 0.02, "loop period %.3f", r.onsets[i] - r.onsets[i - 1]);
    }
    {   // stop then start elsewhere
        Run r; r.host.ppq = 0.0; r.host.playing = true; r.run (0.5); r.host.playing = false; r.run (0.3); r.host.ppq = 2.5; r.host.playing = true; r.run (2.5);
        CHECK (r.onsets.size() >= 2, "restart after stop");
    }
    std::printf (failures ? "%d FAILURE(S)\n" : "transport tests passed\n", failures);
    return failures ? 1 : 0;
}
