cmake_minimum_required(VERSION 3.20)
project(lxr_compare C)

# lxr_render: the same script CLI as the reference harness, driving lxr_core instead of the
# upstream build. Its output must be bit-identical (T0) to lxr_ref_render's.
add_subdirectory(../../Source/Engine/lxr_core lxr_core)
add_subdirectory(../../Source/Sequencer/lxr_seq lxr_seq)

set(HARNESS "${CMAKE_CURRENT_LIST_DIR}/../ref-harness")
set(UPSTREAM "${CMAKE_CURRENT_LIST_DIR}/../../Reference/lxr-desktop-app/Core")
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(PAR_NAMES "${CMAKE_BINARY_DIR}/gen/par_names.inc")
add_custom_command(OUTPUT "${PAR_NAMES}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${CMAKE_BINARY_DIR}/gen"
    COMMAND Python3::Interpreter "${HARNESS}/gen_par_names.py"
            "${CMAKE_CURRENT_LIST_DIR}/../../Source/Engine/lxr_core/inc/Parameters.h" "${PAR_NAMES}"
    DEPENDS "${HARNESS}/gen_par_names.py")
add_custom_target(par_names DEPENDS "${PAR_NAMES}")

add_executable(lxr_render "${HARNESS}/src/render_main.c" "${UPSTREAM}/Src/Preset/initKit.c")
add_dependencies(lxr_render par_names)
target_link_libraries(lxr_render PRIVATE lxr_core m)
target_compile_definitions(lxr_render PRIVATE LXR_BACKEND_CORE)
target_include_directories(lxr_render PRIVATE
    "${CMAKE_BINARY_DIR}/gen"
    "${CMAKE_CURRENT_LIST_DIR}/../../Source/Engine/lxr_core/platform"
    "${CMAKE_CURRENT_LIST_DIR}/../../Source/Engine/lxr_core/inc"
    "${UPSTREAM}/Inc")

add_executable(lxr_render_seq "${HARNESS}/src/render_main.c" "${UPSTREAM}/Src/Preset/initKit.c")
add_dependencies(lxr_render_seq par_names)
target_link_libraries(lxr_render_seq PRIVATE lxr_core lxr_seq m)
target_compile_definitions(lxr_render_seq PRIVATE LXR_BACKEND_CORE LXR_WITH_LXRSEQ)
target_include_directories(lxr_render_seq PRIVATE
    "${CMAKE_BINARY_DIR}/gen"
    "${CMAKE_CURRENT_LIST_DIR}/../../Source/Engine/lxr_core/platform"
    "${CMAKE_CURRENT_LIST_DIR}/../../Source/Engine/lxr_core/inc" "${UPSTREAM}/Inc")

add_executable(test_instances test_instances.c "${UPSTREAM}/Src/Preset/initKit.c")
target_link_libraries(test_instances PRIVATE lxr_core m pthread)
target_include_directories(test_instances PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../../Source/Engine/lxr_core/platform"
    "${CMAKE_CURRENT_LIST_DIR}/../../Source/Engine/lxr_core/inc" "${UPSTREAM}/Inc")
add_executable(test_seq_instances test_seq_instances.c)
target_link_libraries(test_seq_instances PRIVATE lxr_seq m pthread)
enable_testing()
add_test(NAME instances COMMAND test_instances)
add_test(NAME seq_instances COMMAND test_seq_instances)
