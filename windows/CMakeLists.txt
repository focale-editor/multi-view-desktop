cmake_minimum_required(VERSION 3.15)
set(PROJECT_NAME "multi_view_desktop")
project(${PROJECT_NAME} LANGUAGES CXX)

# This value is used when generating builds using this plugin, so it must
# not be changed
set(PLUGIN_NAME "multiview_desktop_plugin")

add_library(${PLUGIN_NAME} SHARED
  "multi_view_desktop.cpp"
  "multi_view_desktop.h"
  "multi_view_desktop_plugin.cpp"
  "mvd_ffi_bridge.cpp"
  "mvd_windows_screen.cpp"
  "mvd_windows_screen.h"
  "mvd_windows_taskbar_menu.cpp"
  "mvd_windows_taskbar_menu.h"
  "mvd_windows_view_creation.cpp"
  "mvd_windows_view_creation.h"
)
apply_standard_settings(${PLUGIN_NAME})
set_target_properties(${PLUGIN_NAME} PROPERTIES
  CXX_VISIBILITY_PRESET hidden)
target_compile_definitions(${PLUGIN_NAME} PRIVATE FLUTTER_PLUGIN_IMPL)
target_compile_definitions(${PLUGIN_NAME} PRIVATE NOMINMAX)
target_compile_definitions(${PLUGIN_NAME} PRIVATE _CRT_SECURE_NO_WARNINGS)
target_compile_definitions(${PLUGIN_NAME} PRIVATE _SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING)
target_include_directories(${PLUGIN_NAME} INTERFACE
  "${CMAKE_CURRENT_SOURCE_DIR}/include")
target_link_libraries(${PLUGIN_NAME} PRIVATE flutter flutter_wrapper_plugin comctl32)

# List of absolute paths to libraries that should be bundled with the plugin
set(multiview_desktop_bundled_libraries
  ""
  PARENT_SCOPE
)

# Native initialization regressions are built by the example only.
if(include_multiview_desktop_tests)
  enable_testing()
  add_executable(multiview_desktop_test
    "test/mvd_windows_view_creation_test.cpp"
    "mvd_windows_view_creation.cpp"
  )
  apply_standard_settings(multiview_desktop_test)
  target_link_libraries(multiview_desktop_test PRIVATE comctl32)
  target_include_directories(multiview_desktop_test PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}")
  add_test(NAME multiview_desktop_view_creation
    COMMAND multiview_desktop_test)
endif()
