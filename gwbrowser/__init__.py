# -*- coding: utf-8 -*-
"""
GWBrowser - a PySide2 based asset-manager for digital production - was designed to run as a standalone PySide2 application, or
to be embedded in a PySide2 context. Maya, Houdini, Nuke are all capable of embedding
but thus far only Maya has a dedicated plug-in.

"""

import sys
import importlib
import traceback
import platform

__name__ = u'gwbrowser'
__author__ = 'Gergely Wootsch'
__website__ = 'https://gergely-wootsch.com'
__email__ = 'hello@gergely-wootsch.com'
__dependencies__ = (
    u'OpenImageIO.OpenImageIO',
    u'gwalembic.alembic',
    u'numpy',
    u'PySide2.QtCore'
)
__version__ = u'0.1.50'


# Making sure the PyImath library is loaded as well
import gwalembic
import gwalembic.alembic as alembic


def _ensure_dependencies():
    """Check the dependencies for **GWBrowser** and raises an exception if
    anything seems out of

    Raises:        ImportError: When importlib fails to import the module.

    """
    try:
        for dependency in __dependencies__:
            # sys.stdout.write(u'GWBrowser: Found "{}"\n'.format(dependency))
            importlib.import_module(dependency)
    except ImportError as err:
        raise ImportError(
            '# Missing dependency: Unable to find the necessary module:\n# {}\n'.format(err))


def get_info():
    """Returns an array of technical information."""
    return (
        u'Author:   {}'.format(__author__),
        u'Email:    {}'.format(__email__),
        u'Website:  {}'.format(__website__),
        u'Version:  {}'.format(__version__),
        u'\n',
        u'Python {} {}'.format(
            platform.python_version(), platform.python_compiler()),
        u'OpenImageIO {}'.format(importlib.import_module(
            __dependencies__[0]).__version__),
        u'{}'.format(importlib.import_module(
            __dependencies__[1]).Abc.GetLibraryVersion()),
        u'Numpy {}'.format(importlib.import_module(
            __dependencies__[2]).__version__),
        u'PySide2 {}'.format(importlib.import_module(
            __dependencies__[3]).__version__),
    )


def exec_():
    """The main method to start GWBrowser as a standalone PySide2 application.

    GWBrowser will not run without ``OpenImageIO``,
    ``Numpy``, ``Alembic`` (will look for *gwalembic* but it really is just the
    regular alembic module renamed to avoid name-clashes) and ``PySide2``. Make
    sure these packages are available for the Python interpreter.

    Example:
        .. code-block:: python

            import gwbrowser
            gwbrowser.exec_()

    """
    _ensure_dependencies()

    # Some basic debugging information
    for info in get_info():
        sys.stdout.write(u'{}\n'.format(info))

    try:
        gwbrowser = importlib.import_module(
            u'{}.standalonewidgets'.format(__name__))

        app = gwbrowser.StandaloneApp([])
        widget = gwbrowser.StandaloneBrowserWidget()
        widget.show()

        app.exec_()
        exit_code = 0
    except:
        sys.stderr.write(u'{}\n'.format(traceback.format_exc()))
        exit_code = 1
    finally:
        raise SystemExit(exit_code)
