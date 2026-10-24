// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <juce_gui_extra/juce_gui_extra.h>
#include "PluginProcessor.h"

// The editor is a WebView hosting the React UI (Source/UI/web). Host-automatable parameters are bound with JUCE's
// web relays; pattern edits and the playhead use the sequencer bridge (own JSON protocol, see Source/UI/web/src/model.ts).
class LynnDrumEditor final : public juce::AudioProcessorEditor, private juce::Timer
{
public:
    explicit LynnDrumEditor (LynnDrumProcessor&);
    ~LynnDrumEditor() override;
    void resized() override;
    void paint (juce::Graphics&) override {}

private:
    void timerCallback() override;
    std::optional<juce::WebBrowserComponent::Resource> resource (const juce::String& url);
    juce::var stateJson() const;
    juce::var patternJson (int p) const;
    juce::var presetsJson (bool withItems) const;

    LynnDrumProcessor& proc;

    // relays must exist before the browser component that registers them
    juce::WebSliderRelay masterRelay { "master" }, tempoRelay { "tempo" };
    std::array<std::unique_ptr<juce::WebSliderRelay>, LynnDrumProcessor::kVoices> faderRelay;
    juce::WebToggleButtonRelay runRelay { "seqRun" };
    juce::WebComboBoxRelay syncRelay { "seqSync" };

    // one relay per generated sound parameter (kind decides the type)
    std::vector<std::unique_ptr<juce::WebSliderRelay>> soundSliders;
    std::vector<std::unique_ptr<juce::WebComboBoxRelay>> soundCombos;
    std::vector<std::unique_ptr<juce::WebToggleButtonRelay>> soundToggles;
    std::vector<std::unique_ptr<juce::WebComboBoxParameterAttachment>> comboAtt;
    std::vector<std::unique_ptr<juce::WebToggleButtonParameterAttachment>> toggleAtt;

    std::unique_ptr<juce::WebBrowserComponent> web;
    std::vector<std::unique_ptr<juce::WebSliderParameterAttachment>> sliderAtt;
    std::unique_ptr<juce::WebToggleButtonParameterAttachment> runAtt;
    std::unique_ptr<juce::WebComboBoxParameterAttachment> syncAtt;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (LynnDrumEditor)
};
