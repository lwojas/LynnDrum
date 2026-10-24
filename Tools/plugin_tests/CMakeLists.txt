juce_add_console_app(plugin_smoke PRODUCT_NAME "plugin_smoke")
target_sources(plugin_smoke PRIVATE PluginSmoke.cpp)
target_compile_definitions(plugin_smoke PRIVATE JUCE_PLUGINHOST_VST3=1 JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_MODAL_LOOPS_PERMITTED=1)
target_link_libraries(plugin_smoke PRIVATE juce::juce_audio_processors juce::juce_audio_utils juce::juce_recommended_config_flags)

# preset / state tests drive the processor class directly (no host), with the same sources as the plugin
juce_add_console_app(preset_tests PRODUCT_NAME "preset_tests")
target_sources(preset_tests PRIVATE PresetTests.cpp ../../Source/Plugin/PluginProcessor.cpp ../../Source/Plugin/PluginEditor.cpp ../../Source/Plugin/PresetManager.cpp)
target_include_directories(preset_tests PRIVATE ../../Source/Plugin)
target_compile_definitions(preset_tests PRIVATE JUCE_WEB_BROWSER=1 JUCE_USE_CURL=0 JUCE_MODAL_LOOPS_PERMITTED=1)
target_link_libraries(preset_tests PRIVATE lynn_host lxr_seq LynnDrumUI juce::juce_audio_processors juce::juce_audio_utils juce::juce_gui_extra juce::juce_recommended_config_flags)

juce_add_console_app(transport_tests PRODUCT_NAME "transport_tests")
target_sources(transport_tests PRIVATE TransportTests.cpp ../../Source/Plugin/PluginProcessor.cpp ../../Source/Plugin/PluginEditor.cpp ../../Source/Plugin/PresetManager.cpp)
target_include_directories(transport_tests PRIVATE ../../Source/Plugin)
target_compile_definitions(transport_tests PRIVATE JUCE_WEB_BROWSER=1 JUCE_USE_CURL=0 JUCE_MODAL_LOOPS_PERMITTED=1)
target_link_libraries(transport_tests PRIVATE lynn_host lxr_seq LynnDrumUI juce::juce_audio_processors juce::juce_audio_utils juce::juce_gui_extra juce::juce_recommended_config_flags)
