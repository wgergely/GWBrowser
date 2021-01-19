# -*- coding: utf-8 -*-
"""
"""
import sys
import os
import importlib
import traceback
import platform

author = 'Gergely Wootsch'
website = 'https://gergely-wootsch.com'
email = 'hello@gergely-wootsch.com'
__version__ = u'0.4.0'

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
    """Starts Bookmarks as a standalone PySide2 application.

    .. code-block:: python

        import bookmarks
        bookmarks.exec_()

    """
    # Some basic debugging information
    for info in get_info():
        sys.stdout.write(u'{}\n'.format(info))

    from PySide2 import QtWidgets
    from . import settings
    from . import common

    # Load and apply Global UI Scale
    v = settings.local_settings.value(settings.SettingsSection, settings.UIScaleKey)
    v = 1.0 if not isinstance(v, float) else v
    common.UI_SCALE = v

    # Indicate we're running Bookmarks in standalone mode
    common.STANDALONE = True

    from . import standalone
    if QtWidgets.QApplication.instance():
        standalone.show()
        return

    app = standalone.StandaloneApp([])
    standalone.show()
    app.exec_()
