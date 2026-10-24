include(FetchContent)
set(FETCHCONTENT_QUIET OFF)
FetchContent_Declare(JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG 8.0.9
    GIT_SHALLOW TRUE)
FetchContent_MakeAvailable(JUCE)

juce_add_plugin(LynnDrum
    COMPANY_NAME "LynnDrum"
    PLUGIN_MANUFACTURER_CODE Lnnd
    PLUGIN_CODE Lnd1
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    NEEDS_WEB_BROWSER TRUE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD FALSE
    FORMATS VST3 Standalone
    PRODUCT_NAME "LynnDrum"
    VST3_CATEGORIES Instrument Drum Synth)

# the React UI (Source/UI/web) is built to one self-contained index.html (Tools/ui/build.sh) and embedded
file(GLOB LYNN_FACTORY_PRESETS CONFIGURE_DEPENDS "${CMAKE_SOURCE_DIR}/Presets/factory/*.lynnpreset")
juce_add_binary_data(LynnDrumUI SOURCES "${CMAKE_SOURCE_DIR}/Source/UI/web/dist/index.html" ${LYNN_FACTORY_PRESETS})
target_sources(LynnDrum PRIVATE PluginProcessor.cpp PluginEditor.cpp PresetManager.cpp)
target_compile_definitions(LynnDrum PUBLIC
    JUCE_WEB_BROWSER=1 JUCE_USE_CURL=0 JUCE_VST3_CAN_REPLACE_VST2=0 JUCE_DISPLAY_SPLASH_SCREEN=0)
target_link_libraries(LynnDrum PRIVATE lynn_host lxr_seq LynnDrumUI
    juce::juce_audio_utils juce::juce_audio_processors juce::juce_gui_extra
    juce::juce_recommended_config_flags juce::juce_recommended_warning_flags)

add_subdirectory("${CMAKE_SOURCE_DIR}/Tools/plugin_tests" plugin_tests)
