# -*- coding: utf-8 -*-
"""
"""
import sys
import os
import importlib
import traceback
import platform

name = u'bookmarks'
author = 'Gergely Wootsch'
website = 'https://gergely-wootsch.com'
email = 'hello@gergely-wootsch.com'
__version__ = u'0.3.8'


def get_info():
    return (
        u'Copyright (C) 2020  {}'.format(author),
        u'Email:    {}'.format(email),
        u'Website:  {}'.format(website),
        u'Version:  {}'.format(__version__),
        u'\n',
        u'Python {} {}'.format(
            platform.python_version(), platform.python_compiler()),
        u'OpenImageIO {}'.format(
            importlib.import_module('OpenImageIO').__version__),
        u'{}'.format(
            importlib.import_module('alembic').Abc.GetLibraryVersion()),
        u'PySide2 {}'.format(
            importlib.import_module('PySide2.QtCore').__version__),
    )


def exec_():
    """Start Bookmarks as a standalone PySide2 application.

    .. code-block:: python

        import bookmarks
        bookmarks.exec_()

    """
    # Some basic debugging information
    for info in get_info():
        sys.stdout.write(u'{}\n'.format(info))

    from PySide2 import QtWidgets
    import bookmarks.settings as settings
    import bookmarks.common as common

    if not settings.local_settings:
        settings.local_settings = settings.LocalSettings()
    ui_scale = settings.local_settings.value(u'preferences/ui_scale')
    ui_scale = ui_scale if ui_scale else common.UI_SCALE

    common.UI_SCALE = float(ui_scale)
    common.STANDALONE = True

    import bookmarks.standalone as standalone
    if QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication.instance()
    else:
        app = standalone.StandaloneApp([])

    import bookmarks.mainwidget as mainwidget
    standalone.StandaloneMainWidget()
    mainwidget.show_window()

    app.exec_()
