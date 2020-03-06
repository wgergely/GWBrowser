# -*- coding: utf-8 -*-
"""**GWBrowser is a simple asset browser used to create and navigate
the files and folders of animation or film productions.**

Predominantly intended to be run as a standalone PySide2 application, GWBrowser
can, however, be embedded in PySide2 contexts. This should include (at the time
of writing) Maya, Houdini and Nuke.

``mGWBrowser.py`` is the plug-in for launching GWBrowser from inside Maya.

Info:
    GWBrowser requires ``OpenImageIO``, ``Numpy``, ``GWAlembic`` and ``PySide2``
    to function.

    The standalone version is built against Python 2.7 MSCV1900 and includes the
    above libraries. The library versions are mindful of the *VFX Reference
    Platform* specifications.

"""

import sys
import os
import importlib
import traceback
import platform

name = u'gwbrowser'
author = 'Gergely Wootsch'
website = 'https://gergely-wootsch.com'
email = 'hello@gergely-wootsch.com'
__version__ = u'0.3.0'


def get_info():
    """Returns an array of string with the dependent library versions and information
    about the author.

    """
    return (
        u'Author:   {}'.format(author),
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

        import gwbrowser
        gwbrowser.exec_()

    """
    # Some basic debugging information
    for info in get_info():
        sys.stdout.write(u'{}\n'.format(info))

    gwbrowser = importlib.import_module(
        u'{}.standalonewidgets'.format(name))

    from PySide2 import QtWidgets, QtCore
    if QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication.instance()
    else:
        # High-dpi scaling support
        # os.putenv('QT_SCALE_FACTOR', '1.2')
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        app = gwbrowser.StandaloneApp([])
    widget = gwbrowser.StandaloneBrowserWidget()
    widget.show()

    app.exec_()
