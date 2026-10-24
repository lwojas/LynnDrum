// SPDX-License-Identifier: GPL-3.0-only
// Host-transport behaviour of the processor with a scripted AudioPlayHead: start at an arbitrary position, locate, loop wrap.
#include <juce_audio_processors/juce_audio_processors.h>
#include <cmath>
#include <cstdio>
#include <vector>
#include <initializer_list>
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
        for (int pt = 0; pt < 64; ++pt) b.applyUiCommand ({ (double) pt }, "clearPattern");                                              // empty bank (a fresh instance holds the Tight 4/4 preset)
        b.applyUiCommand ({ 0, 0, 0, 1 }, "step"); b.applyUiCommand ({ 0, 0, 0, 127 }, "stepVol");                                       // kick on step 1 of 16 only
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
    {   // pattern 2 has its kick on step 9 only; selecting it while playing takes effect at the end of the bar
        Run r; auto& b = r.p.bridge();
        b.applyUiCommand ({ 1, 0, 8, 1 }, "step"); b.applyUiCommand ({ 1, 0, 8, 127 }, "stepVol"); r.step (false);
        r.host.ppq = 0.0; r.host.playing = true; r.run (0.3);
        b.applyUiCommand ({ 1 }, "selectPattern"); r.run (5.0);
        std::printf ("pattern switch: kicks at"); for (double o : r.onsets) std::printf (" %.3f", o); std::printf ("\n");
        CHECK (r.onsets.size() >= 3 && std::fabs (r.onsets[0]) < 0.02, "first bar plays pattern 1");
        CHECK (r.onsets.size() >= 2 && std::fabs (r.onsets[1] - 3.0) < 0.03, "queued pattern starts at the bar end (kick on its step 9 at 3.0 s): %.3f", r.onsets.size() > 1 ? r.onsets[1] : -1.0);
        CHECK (r.onsets.size() >= 3 && std::fabs (r.onsets[2] - 5.0) < 0.03, "and keeps playing it: %.3f", r.onsets.size() > 2 ? r.onsets[2] : -1.0);
    }
    {   // song mode: patterns 1, 2, then loop
        Run r; auto& b = r.p.bridge();
        b.applyUiCommand ({ 1, 0, 8, 1 }, "step"); b.applyUiCommand ({ 1, 0, 8, 127 }, "stepVol");
        b.applyUiCommand ({ 0, 0 }, "songSet"); b.applyUiCommand ({ 1, 1 }, "songSet"); b.applyUiCommand ({ 2, 65 }, "songSet"); b.applyUiCommand ({ 1 }, "songMode");
        r.step (false);
        r.host.ppq = 0.0; r.host.playing = true; r.run (6.5);
        std::printf ("song 1,2,loop: kicks at"); for (double o : r.onsets) std::printf (" %.3f", o); std::printf ("\n");
        const double want[] = { 0.0, 3.0, 4.0, 7.0 };
        CHECK (r.onsets.size() >= 3, "song produced %zu kicks", r.onsets.size());
        for (size_t i = 0; i < 3 && i < r.onsets.size(); ++i) CHECK (std::fabs (r.onsets[i] - want[i]) < 0.04, "song kick %zu at %.3f, expected %.3f", i, r.onsets[i], want[i]);
    }
    {   // solo reaches the audio: soloing another (empty) track silences the kick, soloing the kick track or clearing the solo restores it
        auto kicks = [&] (std::initializer_list<std::pair<const char*, std::vector<double>>> cmds) {
            Run r; auto& b = r.p.bridge();
            for (auto& c : cmds) b.applyUiCommand (c.second, c.first);
            for (int i = 0; i < 4; ++i) r.step (false);                                           // apply the commands on the audio thread
            r.onsets.clear(); r.t = 0; r.host.ppq = 0.0; r.host.playing = true; r.run (3.0);
            return r.onsets.size(); };
        CHECK (kicks ({}) >= 1, "baseline plays");
        CHECK (kicks ({ { "solo", { 1, 1 } } }) == 0, "soloing another track must silence the kick");
        CHECK (kicks ({ { "solo", { 0, 1 } } }) >= 1, "soloing the kick track keeps it");
        CHECK (kicks ({ { "solo", { 1, 1 } }, { "solo", { 1, 0 } } }) >= 1, "clearing the solo restores the kick");
        CHECK (kicks ({ { "solo", { 0, 1 } }, { "mute", { 0, 1 } } }) == 0, "mute wins over solo");
    }
    std::printf (failures ? "%d FAILURE(S)\n" : "transport tests passed\n", failures);
    return failures ? 1 : 0;
}
