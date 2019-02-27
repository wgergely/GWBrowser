built_modules = list(name for name in
    "Core;Gui;Widgets;PrintSupport;Sql;Network;Test;Concurrent;WinExtras;Xml;XmlPatterns;Help;Multimedia;MultimediaWidgets;OpenGL;Qml;Quick;QuickWidgets;Svg;UiTools;WebChannel;WebEngineWidgets;WebSockets"
    .split(";"))

shiboken_library_soversion = str(5.6)
pyside_library_soversion = str(5.6)

version = "5.6.0a1.dev1528216830"
version_info = (5, 6, 0, "a", 1)

__build_date__ = '2018-06-05T16:42:42+00:00'




# Timestamp used for snapshot build, which is part of snapshot package version.
__setup_py_package_timestamp__ = '1528216830'
