# lxr_seq: the GPL-derived step sequencer as a static library with a C API (see README).
file(GLOB_RECURSE LXR_SEQ_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_LIST_DIR}/src/*.c" "${CMAKE_CURRENT_LIST_DIR}/engine/*.c")
add_library(lxr_seq STATIC ${LXR_SEQ_SOURCES})
target_include_directories(lxr_seq
    PUBLIC  "${CMAKE_CURRENT_LIST_DIR}/include"
    PRIVATE BEFORE "${CMAKE_CURRENT_LIST_DIR}/platform" "${CMAKE_CURRENT_LIST_DIR}/inc")
set_target_properties(lxr_seq PROPERTIES C_STANDARD 11 C_EXTENSIONS ON)
target_compile_options(lxr_seq PRIVATE -ffp-contract=off -fno-fast-math -funsigned-char -Wno-everything)
# the derived sources see the upstream identifiers through macros; our own engine/ sources do not
file(GLOB LXR_SEQ_DERIVED CONFIGURE_DEPENDS "${CMAKE_CURRENT_LIST_DIR}/src/*.c")
set_source_files_properties(${LXR_SEQ_DERIVED} PROPERTIES
    COMPILE_OPTIONS "-include;${CMAKE_CURRENT_LIST_DIR}/platform/lxrseq_prelude.h")
