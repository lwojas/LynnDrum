cmake_minimum_required(VERSION 3.20)
project(lxr_ref_harness C)

# Reference harness: builds the UNMODIFIED upstream DSP + parameter handler on the
# host (plus the small patches in patches/) and renders audio from a script.
# Upstream is the read-only submodule in Reference/; it is never written to.

set(UPSTREAM "${CMAKE_CURRENT_SOURCE_DIR}/../../Reference/lxr-desktop-app/Core"
    CACHE PATH "Upstream Core/ directory")
if(NOT EXISTS "${UPSTREAM}/Src/Soundengine/DSPAudio/mixer.c")
  message(FATAL_ERROR "Upstream not found at ${UPSTREAM} (git submodule update --init)")
endif()

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_EXTENSIONS ON)
set(CMAKE_C_FLAGS_RELEASE "-O2")           # no -ffast-math, no FMA contraction (see below)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# ---- patched overlay -------------------------------------------------------
# Upstream files that need a documented edit are copied into the build tree and
# patched there. Each patch is registered in docs/ref-harness.md (H-series).
find_program(PATCH_EXE patch REQUIRED)
set(OVERLAY "${CMAKE_BINARY_DIR}/overlay")
set(PATCHED_FILES
    Src/Soundengine/DSPAudio/Oscillator.c
    Src/Soundengine/DSPAudio/DrumVoice.c
    Src/Soundengine/DSPAudio/lfo.c
    Src/Soundengine/DSPAudio/wavetable.c
    Src/Soundengine/MIDI/MidiParser.c
    Src/Soundengine/Sequencer/EuklidGenerator.c
    Inc/Soundengine/DSPAudio/wavetable.h)
file(REMOVE_RECURSE "${OVERLAY}")
foreach(f IN LISTS PATCHED_FILES)
  get_filename_component(d "${f}" DIRECTORY)
  file(MAKE_DIRECTORY "${OVERLAY}/${d}")
  file(COPY "${UPSTREAM}/${f}" DESTINATION "${OVERLAY}/${d}")
endforeach()
file(GLOB PATCH_FILES "${CMAKE_CURRENT_SOURCE_DIR}/patches/*.patch")
list(SORT PATCH_FILES)
foreach(p IN LISTS PATCH_FILES)
  execute_process(COMMAND "${PATCH_EXE}" -p1 -i "${p}" WORKING_DIRECTORY "${OVERLAY}"
                  RESULT_VARIABLE rc OUTPUT_VARIABLE out ERROR_VARIABLE err)
  if(NOT rc EQUAL 0)
    message(FATAL_ERROR "patch ${p} failed:\n${out}${err}")
  endif()
endforeach()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${PATCH_FILES})

# ---- upstream sources (mirrors the lxr_dsp / midi / FX-bus parts of Core/CMakeLists.txt)
set(DSP_DIR Src/Soundengine/DSPAudio)
set(UP_SOURCES
    1PoleLp automationNode BufferTools CymbalVoice Decay distortion dither DrumVoice HiHat
    lfo mixer modulationNode Oscillator random ResonantFilter Samples SlopeEg2 snapEg Snare
    squareRootLut TiltEq transientGenerator transientTables wavetable
    FX/Compressor FX/Delay FX/Distortion FX/FxRamBuffer FX/Reverb FX/Ringmod
    FX/VerbTools/AllpassDelay FX/VerbTools/sinCos FX/VerbTools/VerbDelay FX/VerbTools/VerbModDelay)
set(SRC_LIST)
foreach(s IN LISTS UP_SOURCES)
  set(rel "${DSP_DIR}/${s}.c")
  if(rel IN_LIST PATCHED_FILES)
    list(APPEND SRC_LIST "${OVERLAY}/${rel}")
  else()
    list(APPEND SRC_LIST "${UPSTREAM}/${rel}")
  endif()
endforeach()
foreach(rel Src/Soundengine/FxBus.c Src/Soundengine/MIDI/MidiParser.c
            Src/Soundengine/MIDI/MidiVoiceControl.c Src/Soundengine/MIDI/ParameterArray.c
            Src/Soundengine/MIDI/MidiMessages.c
            Src/menu/Cc2Text.c Src/Preset/initKit.c)
  if(rel IN_LIST PATCHED_FILES)
    list(APPEND SRC_LIST "${OVERLAY}/${rel}")
  else()
    list(APPEND SRC_LIST "${UPSTREAM}/${rel}")
  endif()
endforeach()

add_library(lxr_upstream OBJECT ${SRC_LIST})
target_include_directories(lxr_upstream PUBLIC
    "${OVERLAY}/Inc"                       # patched headers first
    "${CMAKE_CURRENT_SOURCE_DIR}/shim"     # host HAL/CMSIS shims
    "${UPSTREAM}/Inc")
target_compile_definitions(lxr_upstream PUBLIC STM32F765xx)
target_compile_options(lxr_upstream PUBLIC
    -include "${CMAKE_CURRENT_SOURCE_DIR}/shim/lxr_host_prelude.h"
    -ffp-contract=off -fno-fast-math -funsigned-char
    -Wno-everything)

add_library(lxr_stubs OBJECT src/stubs_common.c src/stubs_noseq.c)
target_link_libraries(lxr_stubs PUBLIC lxr_upstream)
target_include_directories(lxr_stubs PRIVATE src)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(PAR_NAMES "${CMAKE_BINARY_DIR}/gen/par_names.inc")
add_custom_command(OUTPUT "${PAR_NAMES}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${CMAKE_BINARY_DIR}/gen"
    COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/gen_par_names.py"
            "${UPSTREAM}/Inc/Parameters.h" "${PAR_NAMES}"
    DEPENDS "${UPSTREAM}/Inc/Parameters.h" "${CMAKE_CURRENT_SOURCE_DIR}/gen_par_names.py")
add_custom_target(par_names DEPENDS "${PAR_NAMES}")

add_executable(lxr_ref_render src/render_main.c $<TARGET_OBJECTS:lxr_upstream> $<TARGET_OBJECTS:lxr_stubs>)
target_include_directories(lxr_ref_render PRIVATE
    "${OVERLAY}/Inc" "${CMAKE_CURRENT_SOURCE_DIR}/shim" "${UPSTREAM}/Inc" src)
target_compile_definitions(lxr_ref_render PRIVATE STM32F765xx)
target_compile_options(lxr_ref_render PRIVATE -include "${CMAKE_CURRENT_SOURCE_DIR}/shim/lxr_host_prelude.h")
target_link_libraries(lxr_ref_render PRIVATE m)
add_dependencies(lxr_ref_render par_names)
target_include_directories(lxr_ref_render PRIVATE "${CMAKE_BINARY_DIR}/gen")

# ---- Stage S0: sequencer oracle (real sequencer.c / clockSync.c / EuklidGenerator.c) ----
set(SEQ_SRC_LIST)
foreach(rel Src/Soundengine/Sequencer/sequencer.c Src/Soundengine/Sequencer/clockSync.c
            Src/Soundengine/Sequencer/EuklidGenerator.c)
  if(rel IN_LIST PATCHED_FILES)
    list(APPEND SEQ_SRC_LIST "${OVERLAY}/${rel}")
  else()
    list(APPEND SEQ_SRC_LIST "${UPSTREAM}/${rel}")
  endif()
endforeach()
add_library(lxr_seq_upstream OBJECT ${SEQ_SRC_LIST})
target_include_directories(lxr_seq_upstream PUBLIC "${OVERLAY}/Inc" "${CMAKE_CURRENT_SOURCE_DIR}/shim" "${UPSTREAM}/Inc")
target_compile_definitions(lxr_seq_upstream PUBLIC STM32F765xx)
target_compile_options(lxr_seq_upstream PUBLIC -include "${CMAKE_CURRENT_SOURCE_DIR}/shim/lxr_host_prelude.h"
    -ffp-contract=off -fno-fast-math -funsigned-char -Wno-everything)
add_library(lxr_stubs_common OBJECT src/stubs_common.c)
target_link_libraries(lxr_stubs_common PUBLIC lxr_upstream)
target_include_directories(lxr_stubs_common PRIVATE src)
add_library(lxr_stubs_seq OBJECT src/stubs_seq.c)
target_link_libraries(lxr_stubs_seq PUBLIC lxr_upstream)
target_include_directories(lxr_stubs_seq PRIVATE src)
add_executable(lxr_ref_seq src/render_main.c $<TARGET_OBJECTS:lxr_upstream> $<TARGET_OBJECTS:lxr_seq_upstream>
    $<TARGET_OBJECTS:lxr_stubs_common> $<TARGET_OBJECTS:lxr_stubs_seq>)
target_include_directories(lxr_ref_seq PRIVATE "${OVERLAY}/Inc" "${CMAKE_CURRENT_SOURCE_DIR}/shim" "${UPSTREAM}/Inc" src "${CMAKE_BINARY_DIR}/gen")
target_compile_definitions(lxr_ref_seq PRIVATE STM32F765xx LXR_WITH_SEQ)
target_compile_options(lxr_ref_seq PRIVATE -include "${CMAKE_CURRENT_SOURCE_DIR}/shim/lxr_host_prelude.h")
target_link_libraries(lxr_ref_seq PRIVATE m)
add_dependencies(lxr_ref_seq par_names)

# Hooks: record what the sequencer does to the engine, then forward to the real function.
set_source_files_properties("${UPSTREAM}/Src/Soundengine/Sequencer/sequencer.c" PROPERTIES
    COMPILE_DEFINITIONS "voiceControl_noteOn=lxr_hook_noteOn;midiParser_ccHandler=lxr_hook_cc")
set_source_files_properties("${UPSTREAM}/Src/Soundengine/DSPAudio/automationNode.c" PROPERTIES
    COMPILE_DEFINITIONS "midiParser_ccHandler=lxr_hook_cc")
