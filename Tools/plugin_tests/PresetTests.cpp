// SPDX-License-Identifier: GPL-3.0-only
// Preset / state tests: the processor class driven directly (message-thread API), no host involved.
#include <juce_audio_processors/juce_audio_processors.h>
#include <cstdio>
#include "PluginProcessor.h"

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { ++failures; std::printf ("FAIL: "); std::printf (__VA_ARGS__); std::printf ("\n"); } } while (0)

static int paramValue (LynnDrumProcessor& p, const lynn::params::Def& d) { return (int) (p.apvts.getRawParameterValue (d.id)->load() + 0.5f); }

static int countSteps (const lynn::UiPattern& p) { int n = 0; for (auto& t : p.tracks) for (auto v : t.on) n += v; return n; }
static int countAll (LynnDrumProcessor& p) { int n = 0; for (int i = 0; i < lynn::kPatterns; ++i) n += countSteps (p.bridge().pattern (i)); return n; }

static const lynn::params::Def& def (const char* id) { for (auto& d : lynn::params::kSound) if (juce::String (d.id) == id) return d; jassertfalse; return lynn::params::kSound[0]; }

int main()
{
    juce::ScopedJuceInitialiser_GUI init;
    auto tmp = juce::File::getSpecialLocation (juce::File::tempDirectory).getChildFile ("lynndrum_preset_test_" + juce::String (juce::Random::getSystemRandom().nextInt (1000000)));
    PresetManager::overrideUserDirectory (tmp);
    {
        LynnDrumProcessor p;
        auto& pm = p.presetManager();

        // ---- factory presets ---------------------------------------------------------------------------------------
        juce::StringArray names; for (auto& e : pm.entries()) if (e.factory) names.add (e.name);
        std::printf ("factory presets: %s\n", names.joinIntoString (", ").toRawUTF8());
        CHECK (names.contains ("Init") && names.contains ("Tight 4/4") && names.contains ("Deep Backbeat") && names.contains ("Metal Broken"), "factory preset list");
        CHECK (names[0] == "Init", "Init must come first");
        CHECK (pm.currentName() == "Tight 4/4" && !pm.isDirty(), "a fresh instance starts with the Tight 4/4 preset, clean (%s)", pm.currentName().toRawUTF8());

        // each factory preset: loads, sets every parameter from its kit, clean afterwards
        for (auto& n : names)
        {
            CHECK (pm.load (n, true), "load %s", n.toRawUTF8());
            CHECK (!pm.isDirty(), "%s dirty right after load", n.toRawUTF8());
            const auto doc = pm.document (n);                              // snapshot of what is now loaded...
            for (auto& d : lynn::params::kSound) CHECK (doc["kit"][juce::Identifier (d.id)].operator int() == paramValue (p, d), "%s: %s", n.toRawUTF8(), d.id);
        }
        pm.load ("Init", true);
        CHECK (countAll (p) == 0, "Init has an empty bank");
        pm.load ("Metal Broken", true);
        CHECK (countSteps (p.bridge().pattern (0)) == 30 && countSteps (p.bridge().pattern (1)) == 13 && countAll (p) == 43 && p.bridge().pattern (0).tracks[4].length == 32 && p.bridge().pattern (0).shuffle == 40, "Metal Broken bank content");
        {   // the p-locks of the factory pattern arrived
            const auto& k0 = p.bridge().pattern (0).tracks[0]; const auto& k3 = p.bridge().pattern (0).tracks[3];
            CHECK (k0.lockPar1[10] == def ("fmamnt1").par && k0.lockVal1[10] == 110 && k0.lockPar2[10] == lynn::kNoLock && k3.lockPar1[12] == def ("filter_freq_4").par && k3.lockPar2[12] == def ("reso_4").par && k3.lockVal2[12] == 70, "factory p-locks");
        }
        CHECK (p.bridge().songState().entries[0] == 0 && p.bridge().songState().entries[1] == 1 && p.bridge().songState().entries[2] == lynn::kSongLoop && !p.bridge().songState().enabled, "Metal Broken song");
        
        // ---- the demo library (Tools/kits/library, documentation in each preset's "meta") ------------------------------------
        {
            int library = 0; bool complete = true;
            for (auto& e : pm.entries())
                if (e.factory && e.meta.isObject())
                {
                    ++library;
                    for (const char* k : { "category", "level", "character", "technique", "voices", "key", "bpm", "demonstrates", "patterns", "order" })
                        if (e.meta[juce::Identifier (k)].isVoid()) { complete = false; std::printf ("FAIL: %s has no meta.%s\n", e.name.toRawUTF8(), k); ++failures; }
                    if (e.meta["demonstrates"].toString().length() < 40) { complete = false; std::printf ("FAIL: %s: 'demonstrates' is too short\n", e.name.toRawUTF8()); ++failures; }
                }
            CHECK (library >= 35 && complete, "demo library: %d presets with documentation", library);
            int iTight = names.indexOf ("Tight 4/4"), iWare = names.indexOf ("Warehouse Pulse"), iLast = names.indexOf ("Ring Mod Throws");
            CHECK (iTight > 0 && iWare > iTight && iLast > iWare, "starters sort before the library, the library keeps its authored order (%d %d %d)", iTight, iWare, iLast);

            pm.load ("Warehouse Pulse", true);
            CHECK (pm.currentName() == "Warehouse Pulse" && countSteps (p.bridge().pattern (0)) > 0 && countSteps (p.bridge().pattern (1)) > 0, "library preset loads with two patterns");
            {   // pattern 2 carries the phrase-ending locks on the last kick and the last snare
                const auto& k = p.bridge().pattern (1).tracks[0]; const auto& s3 = p.bridge().pattern (1).tracks[3];
                CHECK (k.length == 32 && k.lockPar1[28] == def ("velod1").par && k.lockVal1[28] == 11 && k.note[28] == 63, "library kick lock: decay 11, note +3 on the phrase-ending kick");
                CHECK (s3.lockPar1[28] == def ("filter_freq_4").par && s3.lockPar2[28] == def ("velod4").par, "library snare locks");
                CHECK (p.bridge().pattern (0).tracks[0].lockPar1[28] == lynn::kNoLock, "pattern 1 is the plain version (no locks)");
            }
            pm.load ("Concrete Roller", true);
            CHECK (p.bridge().pattern (0).tracks[5].length == 12 && p.bridge().pattern (1).tracks[1].length == 10, "polymeter: track lengths 12 and 10 arrive");
            pm.load ("Foggy Dub", true);
            CHECK (paramValue (p, def ("fx_type")) == 4 && paramValue (p, def ("audio_out2")) == 6, "Foggy Dub: delay FX and drum 2 routed to the FX bus");
            pm.load ("Swing Lab", true);
            CHECK (p.bridge().pattern (0).shuffle == 0 && p.bridge().pattern (4).shuffle > 55 && p.bridge().pattern (4).shuffle < 70, "Swing Lab: five patterns, straight to triplet shuffle");
            pm.load ("Probability Garden", true);
            { int low = 0; for (auto& t : p.bridge().pattern (0).tracks) for (int i = 0; i < lynn::kSteps; ++i) if (t.on[(size_t) i] && t.prob[(size_t) i] < 100) ++low; CHECK (low > 10, "Probability Garden has optional steps (%d)", low); }
            pm.load ("Tight 4/4", true);
        }

        // ---- dirty tracking ------------------------------------------------------------------------------------------
        auto* kickDecay = p.apvts.getParameter ("velod1");
        kickDecay->setValueNotifyingHost (kickDecay->convertTo0to1 (3.0f));
        CHECK (pm.isDirty(), "parameter edit must mark the preset dirty");
        pm.load ("Metal Broken", true); CHECK (!pm.isDirty(), "reload cleans");
        p.bridge().applyUiCommand ({ 0, 0, 5, 1 }, "step");
        CHECK (pm.isDirty(), "pattern edit must mark the preset dirty");

        // ---- save / reload / delete user presets -----------------------------------------------------------------------
        CHECK (!pm.save ("Init"), "factory names are reserved");
        CHECK (!pm.save ("   "), "empty name rejected");
        CHECK (pm.save ("My Test: kit/1"), "save user preset");
        CHECK (pm.currentName() == "My Test: kit/1" && !pm.currentIsFactory() && !pm.isDirty(), "state after save");
        const auto before = pm.document ("x");
        pm.load ("Init", true);
        CHECK (pm.load ("My Test: kit/1", false), "load user preset");
        CHECK (juce::JSON::toString (pm.document ("x"), true) == juce::JSON::toString (before, true), "save -> load must reproduce kit and pattern exactly");
        CHECK (tmp.getChildFile ("My Test_ kit_1.lynnpreset").existsAsFile() || tmp.findChildFiles (juce::File::findFiles, false, "*.lynnpreset").size() == 1, "file written");
        CHECK (pm.remove ("My Test: kit/1"), "delete user preset");
        CHECK (!pm.load ("My Test: kit/1", false), "deleted preset is gone");
        CHECK (!pm.remove ("Init"), "factory presets cannot be deleted");

        // ---- robustness of the document parser ------------------------------------------------------------------------------
        CHECK (!pm.apply (juce::JSON::parse ("{\"schema\":99}")), "unknown schema must be rejected");
        CHECK (!pm.apply (juce::JSON::parse ("[1,2,3]")), "non-object rejected");
        CHECK (pm.apply (juce::JSON::parse ("{\"schema\":1,\"name\":\"x\",\"kit\":{\"coarse1\":9999,\"waveform_nonexistent\":3,\"pan1\":-5},\"pattern\":{\"tracks\":[{\"length\":500,\"steps\":[{\"i\":99,\"vol\":0},{\"i\":3,\"vol\":999,\"flam\":77}]}]}}")),
              "a sloppy but valid document loads");
        CHECK (paramValue (p, def ("coarse1")) == 127 && paramValue (p, def ("pan1")) == 0, "out-of-range kit values are clamped");
        CHECK (p.bridge().pattern (0).tracks[0].length == 64 && p.bridge().pattern (0).tracks[0].vol[3] == 127 && p.bridge().pattern (0).tracks[0].flam[3] == 5, "out-of-range pattern values are clamped");
        CHECK (countAll (p) == 1, "step index out of range ignored");
        CHECK (paramValue (p, def ("velod1")) == def ("velod1").def, "missing kit entries fall back to the Init defaults");

        CHECK (pm.apply (juce::JSON::parse ("{\"schema\":1,\"name\":\"old\",\"kit\":{},\"pattern\":{\"shuffle\":10,\"tracks\":[{\"length\":8,\"mute\":true,\"steps\":[{\"i\":2,\"vol\":90}]}]}}")), "first-format document loads");
        CHECK (p.bridge().pattern (0).shuffle == 10 && p.bridge().pattern (0).tracks[0].length == 8 && p.bridge().muted (0) && countAll (p) == 1, "first-format document content (mute moved to the bank)");
        CHECK (pm.apply (juce::JSON::parse ("{\"schema\":1,\"name\":\"multi\",\"patterns\":[{\"index\":7,\"tracks\":[{\"steps\":[{\"i\":1}]}]},{\"index\":99,\"tracks\":[]}],\"song\":{\"enabled\":true,\"entries\":[7,7,65]}}")), "multi-pattern document loads");
        CHECK (countSteps (p.bridge().pattern (7)) == 1 && countAll (p) == 1 && p.bridge().songState().enabled && p.bridge().songState().entries[2] == lynn::kSongLoop, "multi-pattern content; index 99 ignored");

        // ---- plugin state ------------------------------------------------------------------------------------------------------
        pm.load ("Deep Backbeat", true);
        p.apvts.getParameter ("velod2")->setValueNotifyingHost (0.9f);          // -> dirty
        juce::MemoryBlock blob; p.getStateInformation (blob);
        const auto pat = p.bridge().serialize(); const int v2 = paramValue (p, def ("velod2"));
        {
            LynnDrumProcessor q;
            q.setStateInformation (blob.getData(), (int) blob.getSize());
            CHECK (q.presetManager().currentName() == "Deep Backbeat" && q.presetManager().currentIsFactory() && q.presetManager().isDirty(), "preset info restored (%s)", q.presetManager().currentName().toRawUTF8());
            CHECK (q.bridge().serialize() == pat && paramValue (q, def ("velod2")) == v2, "pattern and parameters restored");
        }
        {   // a schema-1 state (before presets existed): parameters + pattern only
            auto xml = juce::parseXML (juce::String::fromUTF8 ((const char*) blob.getData() + 8, (int) blob.getSize() - 8));   // header skipped below if it is not plain xml
            juce::XmlDocument::parse (juce::String ("<STATE/>"));
            std::unique_ptr<juce::XmlElement> x = juce::AudioProcessor::getXmlFromBinary (blob.getData(), (int) blob.getSize());
            CHECK (x != nullptr, "state is xml");
            if (x)
            {
                for (auto* n : { "preset", "presetFactory", "presetDirty" }) x->removeAttribute (n);
                x->setAttribute ("schema", 1);
                juce::MemoryBlock old; juce::AudioProcessor::copyXmlToBinary (*x, old);
                LynnDrumProcessor q;
                q.setStateInformation (old.getData(), (int) old.getSize());
                CHECK (paramValue (q, def ("velod2")) == v2 && q.bridge().serialize() == pat, "schema-1 state loads");
                CHECK (q.presetManager().currentName() == "Init" && !q.presetManager().isDirty(), "schema-1 state: preset defaults");
            }
        }
        int garbage[4] = { 1, 2, 3, 4 };
        p.setStateInformation (garbage, sizeof garbage);                        // must not crash or change anything
        CHECK (p.presetManager().currentName() == "Deep Backbeat", "garbage state ignored");
    }
    tmp.deleteRecursively();
    std::printf (failures ? "%d FAILURE(S)\n" : "preset tests passed\n", failures);
    return failures ? 1 : 0;
}
