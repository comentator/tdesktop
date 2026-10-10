set(PROTOTYPE_SHERPA_PACKAGE
    ""
    CACHE PATH "Read-only installed sherpa native package")
set(PROTOTYPE_SHERPA_LIB "${PROTOTYPE_SHERPA_PACKAGE}/lib")
add_executable(sherpa_helper "${CMAKE_CURRENT_LIST_DIR}/sherpa_helper.cpp")
target_compile_features(sherpa_helper PRIVATE cxx_std_17)
target_include_directories(sherpa_helper PRIVATE "${PROTOTYPE_SHERPA_PACKAGE}/include")
target_link_libraries(sherpa_helper PRIVATE
    "${PROTOTYPE_SHERPA_LIB}/libsherpa-onnx-c-api.dylib"
    "${PROTOTYPE_SHERPA_LIB}/libonnxruntime.dylib"
    "-framework CoreML" "-framework Foundation" "-framework CoreFoundation")
set_target_properties(sherpa_helper PROPERTIES
    BUILD_RPATH "${PROTOTYPE_SHERPA_LIB}"
    INSTALL_RPATH "${PROTOTYPE_SHERPA_LIB}")
target_compile_options(sherpa_helper PRIVATE "-mmacosx-version-min=26.4")
target_link_options(sherpa_helper PRIVATE "-mmacosx-version-min=26.4")
