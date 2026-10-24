// SPDX-License-Identifier: GPL-3.0-only
// Loads the built VST3 bundle through JUCE's hosting code and exercises it the way a host would
// (a small subset of what pluginval does): instantiate, rates x block sizes, MIDI, state round-trip,
// several instances, NaN/Inf/level checks.
#include <juce_audio_processors/juce_audio_processors.h>
#include <cmath>
#include <cstdio>
#include <functional>

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { ++failures; std::printf ("FAIL: "); std::printf (__VA_ARGS__); std::printf ("\n"); } } while (0)

static std::unique_ptr<juce::AudioPluginInstance> load (juce::AudioPluginFormatManager& fm, const juce::PluginDescription& d, double sr, int bs)
{
    juce::String err;
    auto p = fm.createPluginInstance (d, sr, bs, err);
    CHECK (p != nullptr, "instantiate failed: %s", err.toRawUTF8());
    return p;
}

int main (int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI init;
    if (argc < 2) { std::puts ("usage: plugin_smoke <path/to/LynnDrum.vst3>"); return 2; }

    juce::AudioPluginFormatManager fm;
    fm.addFormat (new juce::VST3PluginFormat());
    juce::OwnedArray<juce::PluginDescription> found;
    juce::VST3PluginFormat vst3;
    vst3.findAllTypesForFile (found, argv[1]);
    CHECK (found.size() == 1, "expected exactly one plugin type in the bundle, got %d", found.size());
    if (found.isEmpty()) return 1;
    const auto& desc = *found[0];
    std::printf ("found: %s (%s) synth=%d\n", desc.name.toRawUTF8(), desc.manufacturerName.toRawUTF8(), (int) desc.isInstrument);
    CHECK (desc.isInstrument, "not flagged as instrument");

    for (double sr : { 44100.0, 48000.0, 96000.0 })
        for (int bs : { 1, 37, 64, 480, 1024, 4096 })
        {
            auto p = load (fm, desc, sr, bs);
            if (!p) continue;
            p->setPlayConfigDetails (0, 2, sr, bs);
            p->prepareToPlay (sr, bs);
            CHECK (p->getLatencySamples() > 0, "latency not reported");
            juce::AudioBuffer<float> buf (2, bs);
            double peak = 0; bool bad = false; int silentAfter = 0;
            const int total = (int) sr;                       // 1 second
            for (int pos = 0; pos < total; pos += bs)
            {
                juce::MidiBuffer midi;
                // kick at t=0.05 s, snare at 0.3 s, closed hat at 0.5 s (note map 36/38/42), absolute times
                const int hits[3][2] = { { (int) (0.05 * sr), 36 }, { (int) (0.3 * sr), 38 }, { (int) (0.5 * sr), 42 } };
                for (auto& h : hits) if (h[0] >= pos && h[0] < pos + bs) midi.addEvent (juce::MidiMessage::noteOn (1, h[1], (juce::uint8) 100), h[0] - pos);
                buf.clear();
                p->processBlock (buf, midi);
                for (int c = 0; c < 2; ++c)
                    for (int i = 0; i < bs; ++i)
                    {
                        const float v = buf.getSample (c, i);
                        if (!std::isfinite (v)) bad = true;
                        peak = std::max (peak, (double) std::fabs (v));
                    }
                (void) silentAfter;
            }
            CHECK (!bad, "NaN/Inf at %g/%d", sr, bs);
            CHECK (peak > 0.05 && peak < 8.0, "peak %g out of range at %g/%d", peak, sr, bs);
            p->releaseResources();
        }
    std::puts ("rates x block sizes done");

    // state round trip
    {
        auto a = load (fm, desc, 48000, 256), b = load (fm, desc, 48000, 256);
        if (a && b)
        {
            a->prepareToPlay (48000, 256); b->prepareToPlay (48000, 256);
            auto& params = a->getParameters();
            CHECK (params.size() >= 8, "expected >= 8 parameters, got %d", params.size());
            auto find = [] (juce::AudioPluginInstance& p, const char* name) -> juce::AudioProcessorParameter* {
                for (auto* q : p.getParameters()) if (q->getName (64) == name) return q;
                return nullptr; };
            auto* ma = find (*a, "Master"); auto* sa = find (*a, "Snare Level");
            CHECK (ma && sa, "parameters Master / Snare Level not found");
            if (!ma || !sa) return 1;
            ma->setValueNotifyingHost (0.25f);
            sa->setValueNotifyingHost (0.5f);
            juce::MemoryBlock mb; a->getStateInformation (mb);
            b->setStateInformation (mb.getData(), (int) mb.getSize());
            CHECK (std::fabs (find (*b, "Master")->getValue() - 0.25f) < 3e-3f, "Master not restored");
            CHECK (std::fabs (find (*b, "Snare Level")->getValue() - 0.5f) < 1e-4f, "Snare Level not restored");
            std::puts ("state round-trip ok");
        }
    }

    // multiple instances in one process, interleaved, must not disturb each other
    {
        std::unique_ptr<juce::AudioPluginInstance> inst[3];
        for (auto& i : inst) { i = load (fm, desc, 48000, 128); if (i) i->prepareToPlay (48000, 128); }
        juce::AudioBuffer<float> out[3] = { { 2, 128 }, { 2, 128 }, { 2, 128 } };
        double peaks[3] = { 0, 0, 0 };
        for (int blk = 0; blk < 200; ++blk)
            for (int k = 0; k < 3; ++k)
            {
                if (!inst[k]) continue;
                juce::MidiBuffer m; if (blk == 3 + k * 10) m.addEvent (juce::MidiMessage::noteOn (1, k == 0 ? 36 : k == 1 ? 38 : 42, (juce::uint8) 110), 5);
                out[k].clear(); inst[k]->processBlock (out[k], m);
                for (int i = 0; i < 128; ++i) peaks[k] = std::max (peaks[k], (double) std::fabs (out[k].getSample (0, i)));
            }
        for (int k = 0; k < 3; ++k) CHECK (peaks[k] > 0.02, "instance %d silent", k);
        std::puts ("three instances ok");
    }

    // a sound parameter must change the sound: Drum 1 / Volume to zero silences the kick (note 36)
    {
        auto run = [&] (bool silence) {
            auto p = load (fm, desc, 48000, 256); double peak = 0;
            if (!p) return peak;
            std::function<juce::AudioProcessorParameter*(const juce::AudioProcessorParameterGroup&)> findVol = [&] (const juce::AudioProcessorParameterGroup& g) -> juce::AudioProcessorParameter* {
                for (auto* n : g) { if (auto* sub = n->getGroup()) { if (auto* r = findVol (*sub)) return r; }
                                    else if (g.getName() == "Drum 1" && n->getParameter()->getName (64) == "Volume") return n->getParameter(); }
                return nullptr; };
            auto* vol = findVol (p->getParameterTree());
            CHECK (vol != nullptr, "Drum 1 / Volume not found in the parameter tree");
            if (vol && silence) vol->setValueNotifyingHost (0.0f);
            p->prepareToPlay (48000, 256);
            juce::AudioBuffer<float> buf (2, 256);
            for (int b = 0; b < 40; ++b)
            {
                juce::MidiBuffer m; if (b == 1) m.addEvent (juce::MidiMessage::noteOn (1, 36, (juce::uint8) 120), 3);
                buf.clear(); p->processBlock (buf, m);
                for (int k = 0; k < 256; ++k) peak = std::max (peak, (double) std::fabs (buf.getSample (0, k)));
            }
            return peak;
        };
        const double loud = run (false), quiet = run (true);
        std::printf ("kick peak %.3f, with Drum 1 volume = 0: %.4f\n", loud, quiet);
        CHECK (loud > 0.05 && quiet < loud * 0.05, "volume parameter has no effect");
    }

    // free-run sequencer must play the demo pattern without any MIDI input
    {
        auto p = load (fm, desc, 48000, 256);
        if (p)
        {
            for (auto* q : p->getParameters())
            {
                if (q->getName (64) == "Seq Sync") q->setValueNotifyingHost (1.0f);
                if (q->getName (64) == "Seq Run (Free)") q->setValueNotifyingHost (1.0f);
            }
            p->prepareToPlay (48000, 256);
            juce::AudioBuffer<float> buf (2, 256); double peak = 0;
            for (int i = 0; i < 48000 / 256; ++i)
            {
                juce::MidiBuffer m; buf.clear(); p->processBlock (buf, m);
                for (int k = 0; k < 256; ++k) peak = std::max (peak, (double) std::fabs (buf.getSample (0, k)));
            }
            CHECK (peak > 0.1, "free-run sequencer is silent (peak %g)", peak);
            std::puts ("free-run sequencer ok");
        }
    }

    std::printf (failures ? "%d FAILURE(S)\n" : "plugin smoke test passed\n", failures);
    return failures ? 1 : 0;
}
