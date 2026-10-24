// SPDX-License-Identifier: GPL-3.0-only
#include "PluginProcessor.h"
#include "PluginEditor.h"
#include <map>


namespace
{
const char* kVoiceNames[LynnDrumProcessor::kVoices] = { "Drum 1", "Drum 2", "Drum 3", "Snare", "Cymbal", "Closed Hat", "Open Hat" };
// General-MIDI-flavoured default note map
const int kNoteMap[LynnDrumProcessor::kVoices] = { 36, 41, 43, 38, 49, 42, 46 };
}

juce::AudioProcessorValueTreeState::ParameterLayout LynnDrumProcessor::createLayout()
{
    using namespace juce;
    AudioProcessorValueTreeState::ParameterLayout l;
    l.add (std::make_unique<AudioParameterFloat> (ParameterID { "master", 1 }, "Master",
                                                  NormalisableRange<float> (0.f, 2.f, 0.001f, 0.6f), 1.0f));
    for (int v = 0; v < kVoices; ++v)
        l.add (std::make_unique<AudioParameterFloat> (ParameterID { "fader" + String (v + 1), 1 },
                                                      String (kVoiceNames[v]) + " Level",
                                                      NormalisableRange<float> (0.f, 1.f, 0.001f), 1.0f));
    // ---- the sound parameters (generated from the firmware's own datatype table: Tools/params/gen_params.py) ----
    std::map<juce::String, std::unique_ptr<juce::AudioProcessorParameterGroup>> groups;
    for (const auto& d : lynn::params::kSound)
    {
        const juce::String g (d.group);
        if (groups.find (g) == groups.end()) groups[g] = std::make_unique<juce::AudioProcessorParameterGroup> (g.replaceCharacter (' ', '_').toLowerCase(), g, " | ");
        const ParameterID pid { d.id, 1 };
        std::unique_ptr<juce::RangedAudioParameter> p;
        switch (d.kind)
        {
            case lynn::params::Kind::Int:
            {
                AudioParameterIntAttributes a;
                if (d.bipolar) a = a.withStringFromValueFunction ([] (int v, int) { return (v - 63 > 0 ? "+" : "") + String (v - 63); });
                p = std::make_unique<AudioParameterInt> (pid, d.name, d.min, d.max, d.def, a);
                break;
            }
            case lynn::params::Kind::Bool:
                p = std::make_unique<AudioParameterBool> (pid, d.name, d.def != 0);
                break;
            case lynn::params::Kind::Choice:
                p = std::make_unique<AudioParameterChoice> (pid, d.name, StringArray::fromTokens (d.choices, "|", ""), d.def);
                break;
            case lynn::params::Kind::Target:
            {
                StringArray names; for (const char* t : lynn::params::kModTargets) names.add (t);
                p = std::make_unique<AudioParameterChoice> (pid, d.name, names, d.def);
                break;
            }
        }
        groups[g]->addChild (std::move (p));
    }
    for (auto& kv : groups) l.add (std::move (kv.second));

    l.add (std::make_unique<AudioParameterChoice> (ParameterID { "seqSync", 1 }, "Seq Sync", StringArray { "Host", "Free" }, 0));
    l.add (std::make_unique<AudioParameterBool> (ParameterID { "seqRun", 1 }, "Seq Run (Free)", false));
    l.add (std::make_unique<AudioParameterFloat> (ParameterID { "tempo", 1 }, "Tempo (Free)",
                                                  NormalisableRange<float> (30.f, 300.f, 0.01f), 120.0f));
    return l;
}

LynnDrumProcessor::LynnDrumProcessor()
    : AudioProcessor (BusesProperties().withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "STATE", createLayout())
{
    master = apvts.getRawParameterValue ("master");
    seqSync = apvts.getRawParameterValue ("seqSync");
    seqRun = apvts.getRawParameterValue ("seqRun");
    freeTempo = apvts.getRawParameterValue ("tempo");
    for (int v = 0; v < kVoices; ++v) fader[(size_t) v] = apvts.getRawParameterValue ("fader" + juce::String (v + 1));
    lastFader.fill (-1.f);
    for (int i = 0; i < lynn::params::kNumSound; ++i)
    {
        soundParam[(size_t) i] = apvts.getRawParameterValue (lynn::params::kSound[i].id);
        soundSent[(size_t) i] = lynn::params::kSound[i].def;
    }
    events.reserve (4096);
    loadDefaultKit();
    presets.load ("Tight 4/4", true);                        // a fresh instance starts with a playable kit + beat
}

void LynnDrumProcessor::loadDefaultKit()
{
    std::uint8_t kit[LXR_KIT_BYTES] = {};
    lynn::params::fillDefaultKit (kit);                                  // clean-room Init kit (Presets/factory/init.lynnpreset)
    engine.loadKit (kit);
}

bool LynnDrumProcessor::isBusesLayoutSupported (const BusesLayout& l) const
{
    return l.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
}

void LynnDrumProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    juce::ignoreUnused (samplesPerBlock);
    currentRate = sampleRate;
    engine.prepare (sampleRate);
    setLatencySamples (engine.latencySamples());
    lastFader.fill (-1.f);
    lastMaster = -1.f;
    seqWasRunning = false;
    engine.reset();
}

int LynnDrumProcessor::voiceForNote (int note) const noexcept
{
    for (int v = 0; v < kVoices; ++v) if (kNoteMap[v] == note) return v;
    return -1;
}

void LynnDrumProcessor::sendSoundParams() noexcept
{
    for (int i = 0; i < lynn::params::kNumSound; ++i)
    {
        const int v = (int) (soundParam[(size_t) i]->load() + 0.5f);
        if (v == soundSent[(size_t) i] || events.size() >= events.capacity()) continue;
        soundSent[(size_t) i] = v;
        const auto& d = lynn::params::kSound[i];
        lynn::HostEvent e; e.offset = 0;
        if (d.kind == lynn::params::Kind::Target)
        {
            e.type = lynn::HostEvent::Type::ModTarget; e.a = (std::uint8_t) d.targetKind; e.b = (std::uint8_t) d.targetIndex; e.c = (std::uint8_t) v;
        }
        else { e.type = lynn::HostEvent::Type::Param; e.a = (std::uint8_t) d.par; e.b = (std::uint8_t) v; }
        events.push_back (e);
    }
}

void LynnDrumProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)
{
    juce::ScopedNoDenormals noDenormals;
    const int n = buffer.getNumSamples();
    buffer.clear();

    // smoothed-free parameter hand-over once per block
    for (int v = 0; v < kVoices; ++v)
    {
        const float f = fader[(size_t) v]->load();
        if (f != lastFader[(size_t) v]) { engine.setFader ((unsigned) v, f); lastFader[(size_t) v] = f; }
    }
    const float m = master->load();
    if (m != lastMaster) { engine.setMasterGain (m); lastMaster = m; }

    events.clear();
    sendSoundParams();

    // --- transport / tempo -> sequencer -------------------------------------------------------------------
    // Host mode keeps the sequencer on the host's 16th-note grid: a start, a locate, a jump or a loop wrap re-anchors the step
    // counters to the host position (every track plays step  absolute_step % track_length). Free mode just runs from step 0.
    double bpm = freeTempo->load();
    bool running = false, haveHost = false;
    double ppq = 0.0;
    bool looping = false; double loopStart = 0.0, loopEnd = 0.0;
    if (seqSync->load() < 0.5f)
    {
        if (auto* ph = getPlayHead())
            if (auto pos = ph->getPosition())
            {
                running = pos->getIsPlaying();
                if (auto b = pos->getBpm()) bpm = *b;
                if (auto q = pos->getPpqPosition()) { ppq = *q; haveHost = true; }
                if (auto lp = pos->getLoopPoints(); lp && pos->getIsLooping()) { looping = true; loopStart = lp->ppqStart; loopEnd = lp->ppqEnd; }
            }
    }
    else
        running = seqRun->load() > 0.5f;
    engine.setTempo (bpm);
    lastBpm.store (bpm);
    seqBridge.drain (engine);

    auto transportEvent = [this] (lynn::HostEvent::Type t, int offset, double at)
    {
        lynn::HostEvent e; e.offset = offset; e.type = t; e.ppq = at;
        if (events.size() < events.capacity()) events.push_back (e);
    };
    const double ppqPerSample = bpm / 60.0 / currentRate;
    if (running && !seqWasRunning)       { transportEvent (lynn::HostEvent::Type::SeqRun, 0, haveHost ? ppq : 0.0); haveExpectedPpq = false; }
    else if (!running && seqWasRunning)  { transportEvent (lynn::HostEvent::Type::SeqStop, 0, 0.0); }
    else if (running && haveHost)
    {
        if (haveExpectedPpq && std::abs (ppq - expectedPpq) > 0.03)      // locate / jump while playing
            transportEvent (lynn::HostEvent::Type::SeqLocate, 0, ppq);
    }
    if (running && haveHost)
    {
        double next = ppq + n * ppqPerSample;
        if (looping && loopEnd > loopStart && ppq < loopEnd && next >= loopEnd - 1e-9)         // the loop wraps inside this block
        {
            const int off = juce::jlimit (0, n - 1, (int) std::lround ((loopEnd - ppq) / ppqPerSample));
            transportEvent (lynn::HostEvent::Type::SeqLocate, off, loopStart);
            next = loopStart + (n - off) * ppqPerSample;
        }
        expectedPpq = next; haveExpectedPpq = true;
    }
    else haveExpectedPpq = false;
    seqWasRunning = running;

    for (const auto meta : midi)
    {
        const auto msg = meta.getMessage();
        if (msg.isNoteOn() && events.size() < events.capacity())
        {
            const int voice = voiceForNote (msg.getNoteNumber());
            if (voice >= 0)
            {
                lynn::HostEvent e;
                e.offset = juce::jlimit (0, n - 1, meta.samplePosition);
                e.type = lynn::HostEvent::Type::NoteOn;
                e.a = (std::uint8_t) voice; e.b = 60;                       // pitched voices play their written note
                e.c = (std::uint8_t) juce::jlimit (1, 127, (int) msg.getVelocity());
                events.push_back (e);
            }
        }
    }

    for (size_t i = 1; i < events.size(); ++i)            // stable insertion sort by sample offset (tiny list, no allocation)
    {
        const auto e = events[i]; size_t j = i;
        while (j > 0 && events[j - 1].offset > e.offset) { events[j] = events[j - 1]; --j; }
        events[j] = e;
    }

    float* l = buffer.getWritePointer (0);
    float* r = buffer.getNumChannels() > 1 ? buffer.getWritePointer (1) : l;
    engine.process (l, r, n, events.data(), (int) events.size());
    float pl = 0.f, pr = 0.f;
    for (int i = 0; i < n; ++i) { pl = juce::jmax (pl, std::abs (l[i])); pr = juce::jmax (pr, std::abs (r[i])); }
    seqBridge.publishPlayhead (engine, bpm, pl, pr);
    midi.clear();
}

void LynnDrumProcessor::getStateInformation (juce::MemoryBlock& dest)
{
    auto state = apvts.copyState();
    state.setProperty ("schema", 2, nullptr);
    state.setProperty ("preset", presets.currentName(), nullptr);
    state.setProperty ("presetFactory", presets.currentIsFactory(), nullptr);
    state.setProperty ("presetDirty", presets.isDirty(), nullptr);
    const auto blob = seqBridge.serialize();
    state.setProperty ("pattern", juce::Base64::toBase64 (blob.data(), blob.size()), nullptr);
    if (auto xml = state.createXml()) copyXmlToBinary (*xml, dest);
}

void LynnDrumProcessor::setStateInformation (const void* data, int size)
{
    if (auto xml = getXmlFromBinary (data, size))
        if (xml->hasTagName (apvts.state.getType()))
        {
            auto vt = juce::ValueTree::fromXml (*xml);
            const auto b64 = vt.getProperty ("pattern").toString();
            if (b64.isNotEmpty())
            {
                juce::MemoryOutputStream mo;
                if (juce::Base64::convertFromBase64 (mo, b64))
                    seqBridge.deserialize (static_cast<const std::uint8_t*> (mo.getData()), mo.getDataSize());     // diffs against the mirror, which tracks the engine
            }
            const auto pname = vt.getProperty ("preset", "Init").toString();      // schema 1 states have no preset info
            const bool pfac = (bool) vt.getProperty ("presetFactory", true), pdirty = (bool) vt.getProperty ("presetDirty", false);
            for (auto prop : { "pattern", "preset", "presetFactory", "presetDirty", "schema" }) vt.removeProperty (prop, nullptr);
            apvts.replaceState (vt);
            presets.setState (pname, pfac, pdirty);
        }
}

juce::AudioProcessorEditor* LynnDrumProcessor::createEditor() { return new LynnDrumEditor (*this); }

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new LynnDrumProcessor(); }
