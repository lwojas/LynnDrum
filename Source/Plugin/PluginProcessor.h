// SPDX-License-Identifier: GPL-3.0-only
#pragma once
#include <juce_audio_processors/juce_audio_processors.h>
#include <array>
#include "EngineHost.h"
#include "SeqBridge.h"
#include "GeneratedParams.h"
#include "PresetManager.h"

class LynnDrumProcessor final : public juce::AudioProcessor
{
public:
    LynnDrumProcessor();
    ~LynnDrumProcessor() override = default;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override {}
    bool isBusesLayoutSupported (const BusesLayout&) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    using juce::AudioProcessor::processBlock;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return "LynnDrum"; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 4.0; }

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int) override {}
    const juce::String getProgramName (int) override { return "Init"; }
    void changeProgramName (int, const juce::String&) override {}

    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    juce::AudioProcessorValueTreeState apvts;

    lynn::SeqBridge& bridge() noexcept { return seqBridge; }
    PresetManager& presetManager() noexcept { return presets; }
    double shownBpm() const noexcept { return lastBpm.load(); }

    static constexpr int kVoices = 7;                       // 0..2 drums, 3 snare, 4 cymbal, 5 closed hat, 6 open hat

private:
    static juce::AudioProcessorValueTreeState::ParameterLayout createLayout();
    void loadDefaultKit();
    int voiceForNote (int note) const noexcept;

    lynn::EngineHost engine;
    lynn::SeqBridge seqBridge;
    PresetManager presets { *this };                        // after apvts and the bridge
    std::atomic<double> lastBpm { 120.0 };
    std::atomic<float>* master = nullptr;
    std::atomic<float>* seqSync = nullptr;                  // 0 = follow host transport, 1 = free-run
    std::atomic<float>* seqRun = nullptr;                   // free-run start/stop
    std::atomic<float>* freeTempo = nullptr;
    bool seqWasRunning = false;
    double expectedPpq = 0.0;                               // where the host should be at the start of the next block (discontinuity detection)
    bool haveExpectedPpq = false;
    double currentRate = 44100.0;
    std::array<std::atomic<float>*, kVoices> fader {};
    std::array<float, kVoices> lastFader {};
    float lastMaster = -1.f;
    std::array<std::atomic<float>*, lynn::params::kNumSound> soundParam {};   // raw parameter values (index / int)
    std::array<int, lynn::params::kNumSound> soundSent {};                     // last value handed to the engine
    void sendSoundParams() noexcept;
    std::vector<lynn::HostEvent> events;                    // reserved in prepareToPlay, never grown on the audio thread

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (LynnDrumProcessor)
};
