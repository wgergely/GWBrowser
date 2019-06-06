# -*- coding: utf-8 -*-
"""GWBrowser is a PySide2 based asset-manager used in a digital production
environment.

The tool was designed to create and navigate folder-structures, aiding an
organized workflow. Projects, assets and files can be annotated with comments,
descriptions and thumbnails making navigating digital life a little
less cumbersome.

Predominantly intended to be run as a standalone PySide2 application, GWBrowser
can, however, be embedded in PySide2 contexts. This should include (at the time
of writing) Maya, Houdini and Nuke.

``mGWBrowser.py`` is the plug-in for launching GWBrowser from inside Maya.

Warning:
    GWBrowser requires ``OpenImageIO``, ``Numpy``, ``GWAlembic`` and ``PySide2``
    to function.

    The standalone version is built against Python 2.7 MSCV1900 and includes the
    above libraries. The library versions are mindful of the *VFX Reference
    Platform* specifications.

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
    """Returns an array of string with the dependent library versions and information
    about the author.

    """
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
