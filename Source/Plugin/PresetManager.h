// SPDX-License-Identifier: GPL-3.0-only
// LynnDrum - presets: a kit (sound parameters, by stable id) plus an optional step pattern, as a small JSON document.
//   factory presets: embedded (Presets/factory/*.lynnpreset, via BinaryData)
//   user presets:    ~/Library/Application Support/LynnDrum/Presets/*.lynnpreset (platform equivalent elsewhere)
// Message-thread only. Loading sets host parameters through the normal parameter path (so the host sees the change)
// and replaces the pattern through the sequencer bridge.
#pragma once
#include <juce_audio_processors/juce_audio_processors.h>
#include "SeqBridge.h"

class LynnDrumProcessor;

class PresetManager final : private juce::AudioProcessorValueTreeState::Listener
{
public:
    // `meta` is the optional documentation object of a preset document (category, level, what it demonstrates, ...): never used for sound, only shown by the browser.
    // `order` is meta.order; presets without it (the starters) sort first, then the library in the order its author gave.
    struct Entry { juce::String name; bool factory = false; juce::File file; juce::String resource; juce::var meta; int order = 50; };

    explicit PresetManager (LynnDrumProcessor&);
    ~PresetManager() override;

    void rescan();
    const std::vector<Entry>& entries() const noexcept { return list; }

    bool load (const juce::String& name, bool factory);
    bool save (const juce::String& name);                     // always a user preset
    bool remove (const juce::String& name);                   // user presets only

    juce::String currentName() const { return current; }
    bool currentIsFactory() const { return currentFactory; }
    bool isDirty() const;
    void setState (const juce::String& name, bool factory, bool dirty);   // plugin state restore

    juce::var document (const juce::String& name) const;       // snapshot of the current kit + pattern
    bool apply (const juce::var& doc);                         // used by load(); public for tests
    static juce::File userDirectory();
    static void overrideUserDirectory (const juce::File&);     // tests

private:
    void parameterChanged (const juce::String&, float) override;
    LynnDrumProcessor& proc;
    std::vector<Entry> list;
    juce::String current { "Init" };
    bool currentFactory = true;
    bool loading = false;
    std::atomic<bool> paramDirty { false };
    std::uint32_t editsAtLoad = 0;
};
