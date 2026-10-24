cmake_minimum_required(VERSION 3.22)
project(LynnDrum VERSION 0.1.0 LANGUAGES C CXX)

# LynnDrum - experimental drum synthesizer plugin derived from the LXR firmware (GPL-3.0-only, see NOTICE.md)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_OSX_DEPLOYMENT_TARGET "11.0" CACHE STRING "")
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release)
endif()

option(LYNN_BUILD_PLUGIN "Build the JUCE plugin (downloads JUCE)" ON)
option(LYNN_BUILD_TESTS  "Build host-layer tests" ON)

add_subdirectory(Source/Engine/lxr_core)
add_subdirectory(Source/Sequencer/lxr_seq)
add_subdirectory(Source/Host)

if(LYNN_BUILD_TESTS)
  enable_testing()
  add_subdirectory(Tools/host_tests)
endif()
if(LYNN_BUILD_PLUGIN)
  add_subdirectory(Source/Plugin)
endif()
