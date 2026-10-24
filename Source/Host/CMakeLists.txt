add_library(lynn_host STATIC EngineHost.cpp Resampler.cpp SeqBridge.cpp)
target_include_directories(lynn_host PUBLIC "${CMAKE_CURRENT_LIST_DIR}")
target_link_libraries(lynn_host PUBLIC lxr_core lxr_seq)
target_compile_features(lynn_host PUBLIC cxx_std_17)
