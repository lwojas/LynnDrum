add_executable(host_tests host_tests.cpp)
target_link_libraries(host_tests PRIVATE lynn_host)
add_test(NAME host_tests COMMAND host_tests)
