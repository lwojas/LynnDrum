// SPDX-License-Identifier: GPL-3.0-only
#include "PluginEditor.h"
#include "BinaryData.h"
#include "GeneratedParams.h"

namespace
{
juce::var trackJson (const lynn::UiTrack& t)
{
    auto* o = new juce::DynamicObject();
    juce::Array<juce::var> on, vol, prob, note, flam, shift;
    for (int i = 0; i < lynn::kSteps; ++i)
    {
        const size_t k = (size_t) i;
        on.add (t.on[k] != 0); vol.add ((int) t.vol[k]); prob.add ((int) t.prob[k]);
        note.add ((int) t.note[k]); flam.add ((int) t.flam[k]); shift.add ((int) t.shift[k]);
    }
    o->setProperty ("on", on); o->setProperty ("vol", vol); o->setProperty ("prob", prob);
    o->setProperty ("note", note); o->setProperty ("flam", flam); o->setProperty ("shift", shift);
    o->setProperty ("length", (int) t.length); o->setProperty ("muted", t.muted);
    return juce::var (o);
}
}

LynnDrumEditor::LynnDrumEditor (LynnDrumProcessor& p) : juce::AudioProcessorEditor (p), proc (p)
{
    using Options = juce::WebBrowserComponent::Options;
    // sound-parameter relays first (they must outlive, and be registered with, the browser component)
    for (const auto& d : lynn::params::kSound)
    {
        switch (d.kind)
        {
            case lynn::params::Kind::Int:    soundSliders.push_back (std::make_unique<juce::WebSliderRelay> (d.id)); break;
            case lynn::params::Kind::Bool:   soundToggles.push_back (std::make_unique<juce::WebToggleButtonRelay> (d.id)); break;
            default:                         soundCombos.push_back (std::make_unique<juce::WebComboBoxRelay> (d.id)); break;
        }
    }
    auto options = Options {}
        .withNativeIntegrationEnabled()
        .withKeepPageLoadedWhenBrowserIsHidden()
        .withResourceProvider ([this] (const juce::String& url) { return resource (url); })
        .withNativeFunction ("lynn_getState", [this] (const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done)
                             { done (juce::JSON::toString (stateJson(), true)); })
        .withNativeFunction ("lynn_cmd", [this] (const juce::Array<juce::var>& args, juce::WebBrowserComponent::NativeFunctionCompletion done)
        {
            bool ok = false;
            if (args.size() > 0)
            {
                const auto parsed = juce::JSON::parse (args[0].toString());
                if (auto* arr = parsed.getArray(); arr != nullptr && arr->size() > 0)
                {
                    std::vector<double> nums;
                    for (int i = 1; i < arr->size(); ++i) nums.push_back ((double) (*arr)[i]);
                    ok = proc.bridge().applyUiCommand (nums, (*arr)[0].toString().toStdString());
                }
            }
            done (ok);
        })
        .withNativeFunction ("lynn_audition", [this] (const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done)
        {
            if (a.size() > 1) proc.bridge().audition ((int) a[0], (int) a[1]);
            done (true);
        })
        .withNativeFunction ("lynn_presets", [this] (const juce::Array<juce::var>&, juce::WebBrowserComponent::NativeFunctionCompletion done)
                             { done (juce::JSON::toString (presetsJson (true), true)); })
        .withNativeFunction ("lynn_loadPreset", [this] (const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done)
        {
            const bool ok = a.size() > 1 && proc.presetManager().load (a[0].toString(), (bool) a[1]);
            if (ok && web) web->emitEventIfBrowserIsVisible ("presetLoaded", juce::var());
            done (ok);
        })
        .withNativeFunction ("lynn_savePreset", [this] (const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done)
                             { done (a.size() > 0 && proc.presetManager().save (a[0].toString())); })
        .withNativeFunction ("lynn_deletePreset", [this] (const juce::Array<juce::var>& a, juce::WebBrowserComponent::NativeFunctionCompletion done)
                             { done (a.size() > 0 && proc.presetManager().remove (a[0].toString())); })
        .withOptionsFrom (masterRelay).withOptionsFrom (tempoRelay).withOptionsFrom (runRelay).withOptionsFrom (syncRelay);
    for (int v = 0; v < LynnDrumProcessor::kVoices; ++v)
    {
        faderRelay[(size_t) v] = std::make_unique<juce::WebSliderRelay> ("fader" + juce::String (v + 1));
        options = std::move (options).withOptionsFrom (*faderRelay[(size_t) v]);
    }
    for (auto& r : soundSliders) options = std::move (options).withOptionsFrom (*r);
    for (auto& r : soundCombos)  options = std::move (options).withOptionsFrom (*r);
    for (auto& r : soundToggles) options = std::move (options).withOptionsFrom (*r);
    web = std::make_unique<juce::WebBrowserComponent> (std::move (options));
    addAndMakeVisible (*web);

    auto& ap = proc.apvts;
    auto slider = [&] (const char* id, juce::WebSliderRelay& relay)
    { sliderAtt.push_back (std::make_unique<juce::WebSliderParameterAttachment> (*ap.getParameter (id), relay, nullptr)); };
    slider ("master", masterRelay); slider ("tempo", tempoRelay);
    for (int v = 0; v < LynnDrumProcessor::kVoices; ++v) slider (("fader" + juce::String (v + 1)).toRawUTF8(), *faderRelay[(size_t) v]);
    runAtt = std::make_unique<juce::WebToggleButtonParameterAttachment> (*ap.getParameter ("seqRun"), runRelay, nullptr);
    syncAtt = std::make_unique<juce::WebComboBoxParameterAttachment> (*ap.getParameter ("seqSync"), syncRelay, nullptr);

    {
        size_t si = 0, ci = 0, ti = 0;
        for (const auto& d : lynn::params::kSound)
        {
            auto* par = ap.getParameter (d.id);
            switch (d.kind)
            {
                case lynn::params::Kind::Int:  sliderAtt.push_back (std::make_unique<juce::WebSliderParameterAttachment> (*par, *soundSliders[si++], nullptr)); break;
                case lynn::params::Kind::Bool: toggleAtt.push_back (std::make_unique<juce::WebToggleButtonParameterAttachment> (*par, *soundToggles[ti++], nullptr)); break;
                default:                       comboAtt.push_back (std::make_unique<juce::WebComboBoxParameterAttachment> (*par, *soundCombos[ci++], nullptr)); break;
            }
        }
    }

    web->goToURL (juce::WebBrowserComponent::getResourceProviderRoot());

    setResizeLimits (900, 600, 2400, 1600);
    setResizable (true, true);
    setSize (1300, 860);
    startTimerHz (30);
}

LynnDrumEditor::~LynnDrumEditor() { stopTimer(); }

void LynnDrumEditor::resized() { if (web) web->setBounds (getLocalBounds()); }

std::optional<juce::WebBrowserComponent::Resource> LynnDrumEditor::resource (const juce::String& url)
{
    if (url == "/" || url == "/index.html")
    {
        const auto* d = reinterpret_cast<const std::byte*> (BinaryData::index_html);
        return juce::WebBrowserComponent::Resource { std::vector<std::byte> (d, d + BinaryData::index_htmlSize), juce::String ("text/html") };
    }
    return std::nullopt;
}

juce::var LynnDrumEditor::presetsJson (bool withItems) const
{
    auto* root = new juce::DynamicObject();
    juce::Array<juce::var> items;
    for (const auto& e : proc.presetManager().entries())
    {
        auto* o = new juce::DynamicObject(); o->setProperty ("name", e.name); o->setProperty ("factory", e.factory); items.add (juce::var (o));
    }
    if (withItems) root->setProperty ("items", items);
    root->setProperty ("current", proc.presetManager().currentName());
    root->setProperty ("factory", proc.presetManager().currentIsFactory());
    root->setProperty ("dirty", proc.presetManager().isDirty());
    return juce::var (root);
}

juce::var LynnDrumEditor::stateJson() const
{
    auto* root = new juce::DynamicObject();
    auto* pat = new juce::DynamicObject();
    juce::Array<juce::var> tracks;
    for (const auto& t : proc.bridge().pattern().tracks) tracks.add (trackJson (t));
    pat->setProperty ("tracks", tracks);
    pat->setProperty ("shuffle", (int) proc.bridge().pattern().shuffle);
    root->setProperty ("pattern", juce::var (pat));
    root->setProperty ("bpm", proc.shownBpm());
    root->setProperty ("running", proc.bridge().readPlayhead().running);
    return juce::var (root);
}

void LynnDrumEditor::timerCallback()
{
    proc.bridge().flush();
    const auto ph = proc.bridge().readPlayhead();
    auto* o = new juce::DynamicObject();
    juce::Array<juce::var> steps;
    for (int s : ph.steps) steps.add (s);
    const auto lv = proc.bridge().readLevel();
    o->setProperty ("running", ph.running); o->setProperty ("steps", steps); o->setProperty ("bpm", ph.bpm); o->setProperty ("peakL", (double) lv.l); o->setProperty ("peakR", (double) lv.r);
    if (web) web->emitEventIfBrowserIsVisible ("playhead", juce::var (o));
    if (web) web->emitEventIfBrowserIsVisible ("preset", presetsJson (false));
}
