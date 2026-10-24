# lxr_core: the GPL-derived engine (DSP + parameter handler) as a static library with a C API.
# Everything under src/ and inc/ is derived from the LXR firmware (see Tools/port/make_core.py
# for the exact edits); platform/ and src/lxr_engine.c are ours.
file(GLOB_RECURSE LXR_CORE_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_LIST_DIR}/src/*.c" "${CMAKE_CURRENT_LIST_DIR}/engine/*.c")
add_library(lxr_core STATIC ${LXR_CORE_SOURCES})
target_include_directories(lxr_core
    PUBLIC  "${CMAKE_CURRENT_LIST_DIR}/include"
    PRIVATE "${CMAKE_CURRENT_LIST_DIR}/platform" "${CMAKE_CURRENT_LIST_DIR}/inc")
set_target_properties(lxr_core PROPERTIES C_STANDARD 11 C_EXTENSIONS ON)
target_compile_options(lxr_core PRIVATE
    -include "${CMAKE_CURRENT_LIST_DIR}/platform/lxr_prelude.h"
    -ffp-contract=off -fno-fast-math -funsigned-char -Wno-everything)
# prelude must see platform headers first
target_include_directories(lxr_core PRIVATE BEFORE "${CMAKE_CURRENT_LIST_DIR}/platform")
