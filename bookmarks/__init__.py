# -*- coding: utf-8 -*-
"""**Bookmarks is a simple asset browser used to create and navigate
the files and folders of animation or film productions.**

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
__version__ = u'0.3.5'


def get_info():
    """Returns an array of string with the dependent library versions and information
    about the author.

    """
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
    """Starts the product as a standalone PySide2 application.

    .. code-block:: python

        import bookmarks
        bookmarks.exec_()

    """
    # Some basic debugging information
    for info in get_info():
        sys.stdout.write(u'{}\n'.format(info))

    from PySide2 import QtWidgets
    import bookmarks.common as common
    import bookmarks.settings as settings

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
