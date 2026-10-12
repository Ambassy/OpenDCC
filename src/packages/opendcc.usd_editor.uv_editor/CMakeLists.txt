set(PLUGIN_DIR ${CMAKE_INSTALL_PREFIX}/packages/opendcc.usd_editor.uv_editor/)

set(OPENDCC_CURRENT_PACKAGE_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/lib)
set(_src_dir lib/opendcc/usd_editor/uv_editor)

opendcc_make_library(
    opendcc.usd_editor.uv_editor
    QT_AUTOMOC
    TYPE
    PLUGIN
    INCLUDE_DIRS
    ${OPENDCC_CURRENT_PACKAGE_INCLUDE_DIR}
    PRIVATE_HEADERS
    ${_src_dir}/prim_info.h
    ${_src_dir}/utils.h
    ${_src_dir}/uv_editor_entry_point.h
    ${_src_dir}/uv_editor_gl_widget.h
    ${_src_dir}/uv_editor.cpp
    ${_src_dir}/uv_editor.h
    ${_src_dir}/uv_rotate_command.h
    ${_src_dir}/uv_rotate_tool.h
    ${_src_dir}/uv_rotate_manipulator.h
    ${_src_dir}/uv_move_command.h
    ${_src_dir}/uv_move_manipulator.h
    ${_src_dir}/uv_move_tool.h
    ${_src_dir}/uv_scale_command.h
    ${_src_dir}/uv_scale_manipulator.h
    ${_src_dir}/uv_scale_tool.h
    ${_src_dir}/uv_scene_delegate.h
    ${_src_dir}/uv_select_tool.h
    ${_src_dir}/uv_tool.h
    CPPFILES
    ${_src_dir}/prim_info.cpp
    ${_src_dir}/utils.cpp
    ${_src_dir}/uv_editor_entry_point.cpp
    ${_src_dir}/uv_editor_gl_widget.cpp
    ${_src_dir}/uv_editor.cpp
    ${_src_dir}/uv_rotate_command.cpp
    ${_src_dir}/uv_rotate_tool.cpp
    ${_src_dir}/uv_rotate_manipulator.cpp
    ${_src_dir}/uv_move_command.cpp
    ${_src_dir}/uv_move_manipulator.cpp
    ${_src_dir}/uv_move_tool.cpp
    ${_src_dir}/uv_scale_command.cpp
    ${_src_dir}/uv_scale_manipulator.cpp
    ${_src_dir}/uv_scale_tool.cpp
    ${_src_dir}/uv_scene_delegate.cpp
    ${_src_dir}/uv_select_tool.cpp
    ${_src_dir}/uv_tool.cpp
    LIBRARY_DEPENDENCIES
    opendcc_lib
    RESOURCES
    ${_src_dir}/plugInfo.json
    RESOURCES_DIR
    packages/opendcc.usd_editor.uv_editor/pxr_plugins/opendcc.usd_editor.uv_editor/resources
    VS_FOLDER
    usd/dcc
    PACKAGE_DIR
    opendcc.usd_editor.uv_editor/lib)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/pxr_plugins/plugInfo.json DESTINATION ${PLUGIN_DIR}/pxr_plugins)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/package.toml DESTINATION ${PLUGIN_DIR})
