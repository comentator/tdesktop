set(CT2_SOURCE ""
    CACHE PATH "Sparse matching CTranslate2 v4.4.0 source/header checkout")
set(CT2_LIBRARY ""
    CACHE FILEPATH "Read-only existing CTranslate2 4.4.0 native dylib")
if(NOT APPLE OR NOT EXISTS "${CT2_LIBRARY}" OR
   NOT EXISTS "${CT2_SOURCE}/include/ctranslate2/models/whisper.h" OR
   NOT EXISTS "${CT2_SOURCE}/include/half_float/half.hpp" OR
   NOT EXISTS "${CT2_SOURCE}/include/nlohmann/json.hpp")
    message(FATAL_ERROR "CT2 helper requires macOS and exact existing v4.4.0 dylib/header dependencies")
endif()
find_library(CT2_ACCELERATE Accelerate REQUIRED)
get_filename_component(CT2_LIBRARY_DIRECTORY "${CT2_LIBRARY}" DIRECTORY)
add_executable(ct2_helper ct2_helper.cpp)
target_compile_features(ct2_helper PRIVATE cxx_std_17)
target_include_directories(ct2_helper PRIVATE "${CT2_SOURCE}/include")
target_compile_options(ct2_helper PRIVATE "-mmacosx-version-min=11.0")
target_link_options(ct2_helper PRIVATE "-mmacosx-version-min=11.0")
target_link_libraries(ct2_helper PRIVATE "${CT2_LIBRARY}" "${CT2_ACCELERATE}")
set_target_properties(ct2_helper PROPERTIES
    BUILD_RPATH "${CT2_LIBRARY_DIRECTORY}"
    INSTALL_RPATH "${CT2_LIBRARY_DIRECTORY}")
add_custom_command(TARGET ct2_helper POST_BUILD
    COMMAND /usr/bin/install_name_tool -change
        "/DLC/ctranslate2/.dylibs/libctranslate2.4.4.0.dylib"
        "${CT2_LIBRARY}" "$<TARGET_FILE:ct2_helper>"
    COMMAND /usr/bin/codesign --force --sign - "$<TARGET_FILE:ct2_helper>"
    VERBATIM)
