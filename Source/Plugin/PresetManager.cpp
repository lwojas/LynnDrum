// SPDX-License-Identifier: GPL-3.0-only
#include "PresetManager.h"
#include "PluginProcessor.h"
#include "BinaryData.h"
#include "GeneratedParams.h"

namespace
{
juce::var stepVar (int i, const lynn::UiTrack& t)
{
    auto* o = new juce::DynamicObject();
    const size_t k = (size_t) i;
    o->setProperty ("i", i); o->setProperty ("vol", (int) t.vol[k]);
    if (t.prob[k] != 100) o->setProperty ("prob", (int) t.prob[k]);
    if (t.note[k] != 60) o->setProperty ("note", (int) t.note[k]);
    if (t.flam[k] != 0) o->setProperty ("flam", (int) t.flam[k]);
    if (t.shift[k] != lynn::kShiftNone) o->setProperty ("shift", (int) t.shift[k]);
    return juce::var (o);
}
int clampi (const juce::var& v, int lo, int hi, int def) { return v.isVoid() ? def : juce::jlimit (lo, hi, (int) v); }
}

PresetManager::PresetManager (LynnDrumProcessor& p) : proc (p)
{
    for (const auto& d : lynn::params::kSound) proc.apvts.addParameterListener (d.id, this);
    rescan();
}
PresetManager::~PresetManager()
{
    for (const auto& d : lynn::params::kSound) proc.apvts.removeParameterListener (d.id, this);
}

namespace { juce::File userDirOverride; }
void PresetManager::overrideUserDirectory (const juce::File& f) { userDirOverride = f; }

juce::File PresetManager::userDirectory()
{
    if (userDirOverride != juce::File()) return userDirOverride;
    return juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory).getChildFile ("LynnDrum").getChildFile ("Presets");
}

void PresetManager::rescan()
{
    list.clear();
    for (int i = 0; i < BinaryData::namedResourceListSize; ++i)
    {
        const juce::String orig (BinaryData::originalFilenames[i]);
        if (!orig.endsWithIgnoreCase (".lynnpreset")) continue;
        int size = 0; const char* data = BinaryData::getNamedResource (BinaryData::namedResourceList[i], size);
        const auto doc = juce::JSON::parse (juce::String::fromUTF8 (data, size));
        if (!doc.isObject()) continue;
        Entry e; e.name = doc["name"].toString(); e.factory = true; e.resource = BinaryData::namedResourceList[i];
        if (e.name.isNotEmpty()) list.push_back (e);
    }
    std::stable_sort (list.begin(), list.end(), [] (const Entry& a, const Entry& b) { return a.name == "Init" ? b.name != "Init" : (b.name != "Init" && a.name.compareIgnoreCase (b.name) < 0); });
    auto dir = userDirectory();
    if (dir.isDirectory())
    {
        juce::Array<juce::File> files = dir.findChildFiles (juce::File::findFiles, false, "*.lynnpreset");
        files.sort();
        for (auto& f : files)
        {
            const auto doc = juce::JSON::parse (f);
            if (!doc.isObject()) continue;
            Entry e; e.name = doc["name"].toString(); e.file = f;
            if (e.name.isNotEmpty()) list.push_back (e);
        }
    }
}

juce::var PresetManager::document (const juce::String& name) const
{
    auto* root = new juce::DynamicObject();
    root->setProperty ("schema", 1); root->setProperty ("name", name);
    auto* kit = new juce::DynamicObject();
    for (const auto& d : lynn::params::kSound) kit->setProperty (d.id, (int) (proc.apvts.getRawParameterValue (d.id)->load() + 0.5f));
    root->setProperty ("kit", juce::var (kit));
    auto* pat = new juce::DynamicObject();
    pat->setProperty ("shuffle", (int) proc.bridge().pattern().shuffle);
    juce::Array<juce::var> tracks;
    for (const auto& t : proc.bridge().pattern().tracks)
    {
        auto* to = new juce::DynamicObject();
        to->setProperty ("length", (int) t.length); to->setProperty ("mute", t.muted);
        juce::Array<juce::var> steps;
        for (int i = 0; i < lynn::kSteps; ++i) if (t.on[(size_t) i]) steps.add (stepVar (i, t));
        to->setProperty ("steps", steps);
        tracks.add (juce::var (to));
    }
    pat->setProperty ("tracks", tracks);
    root->setProperty ("pattern", juce::var (pat));
    return juce::var (root);
}

bool PresetManager::apply (const juce::var& doc)
{
    if (!doc.isObject() || (int) doc["schema"] != 1) return false;
    const auto kit = doc["kit"];
    loading = true;
    for (const auto& d : lynn::params::kSound)
    {
        const int v = clampi (kit.isObject() ? kit[juce::Identifier (d.id)] : juce::var(), d.min, d.max, d.def);
        if (auto* p = proc.apvts.getParameter (d.id)) p->setValueNotifyingHost (p->convertTo0to1 ((float) v));
    }
    loading = false;

    lynn::UiPattern up;                                       // no "pattern" key = empty pattern
    const auto pat = doc["pattern"];
    if (pat.isObject())
    {
        up.shuffle = (std::uint8_t) clampi (pat["shuffle"], 0, 127, 0);
        if (auto* ts = pat["tracks"].getArray())
            for (int t = 0; t < juce::jmin (ts->size(), lynn::kTracks); ++t)
            {
                const auto& tv = (*ts)[t]; auto& tr = up.tracks[(size_t) t];
                tr.length = (std::uint8_t) clampi (tv["length"], 1, 64, 16); tr.muted = (bool) tv["mute"];
                if (auto* ss = tv["steps"].getArray())
                    for (const auto& sv : *ss)
                    {
                        if (sv["i"].isVoid() || (int) sv["i"] < 0 || (int) sv["i"] >= lynn::kSteps) continue;       // not clamped: a wrong index would silently move a step
                        const int i = (int) sv["i"];
                        const size_t k = (size_t) i;
                        tr.on[k] = 1; tr.vol[k] = (std::uint8_t) clampi (sv["vol"], 1, 127, 100); tr.prob[k] = (std::uint8_t) clampi (sv["prob"], 1, 100, 100);
                        tr.note[k] = (std::uint8_t) clampi (sv["note"], 0, 127, 60); tr.flam[k] = (std::uint8_t) clampi (sv["flam"], 0, 5, 0);
                        tr.shift[k] = (std::uint8_t) clampi (sv["shift"], 0, 14, lynn::kShiftNone);
                    }
            }
    }
    proc.bridge().setPattern (up);
    return true;
}

bool PresetManager::load (const juce::String& name, bool factory)
{
    for (const auto& e : list)
    {
        if (e.name != name || e.factory != factory) continue;
        juce::var doc;
        if (e.factory) { int size = 0; const char* d = BinaryData::getNamedResource (e.resource.toRawUTF8(), size); doc = juce::JSON::parse (juce::String::fromUTF8 (d, size)); }
        else doc = juce::JSON::parse (e.file);
        if (!apply (doc)) return false;
        current = e.name; currentFactory = e.factory; paramDirty = false; editsAtLoad = proc.bridge().editCount();
        return true;
    }
    return false;
}

bool PresetManager::save (const juce::String& rawName)
{
    const auto name = rawName.trim();
    if (name.isEmpty() || name.length() > 64) return false;
    for (const auto& e : list) if (e.factory && e.name.equalsIgnoreCase (name)) return false;       // factory names are reserved
    auto dir = userDirectory();
    if (!dir.createDirectory().wasOk()) return false;
    const auto file = dir.getChildFile (juce::File::createLegalFileName (name) + ".lynnpreset");
    if (!file.replaceWithText (juce::JSON::toString (document (name), false))) return false;
    rescan();
    current = name; currentFactory = false; paramDirty = false; editsAtLoad = proc.bridge().editCount();
    return true;
}

bool PresetManager::remove (const juce::String& name)
{
    for (const auto& e : list)
        if (!e.factory && e.name == name && e.file.deleteFile()) { rescan(); return true; }
    return false;
}

bool PresetManager::isDirty() const { return paramDirty.load() || proc.bridge().editCount() != editsAtLoad; }

void PresetManager::setState (const juce::String& name, bool factory, bool dirty)
{
    current = name; currentFactory = factory; paramDirty = dirty; editsAtLoad = proc.bridge().editCount();
}

void PresetManager::parameterChanged (const juce::String&, float) { if (!loading) paramDirty = true; }
