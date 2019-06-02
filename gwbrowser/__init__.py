# -*- coding: utf-8 -*-
"""
#################################################################
GWBrowser - A PySide2 based asset-manager for digital production.
#################################################################


Written by `Gergely Wootsch`_ at `Glassworks Barcelona`_, 2019.

.. _Gergely Wootsch: https://gergely-wootsch.com/
.. _Glassworks Barcelona: https://www.glassworksvfx.com/

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
    u'gwalembic',
    u'numpy',
    u'PySide2'
)
__version__ = u'0.1.49'


def _ensure_dependencies():
    """Check the dependencies for **GWBrowser** and raises an exception if
    anything seems out of

    Raises:        ImportError: When importlib fails to import the module.

    """
    try:
        for dependency in __dependencies__:
            importlib.import_module(dependency)
    except ImportError as err:
        raise ImportError(
            '# Missing dependency: Unable to find the necessary module:\n# {}\n'.format(err))


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
    sys.stdout.write(u'\nGWBrowser: All dependencies found. Starting...\n')
    sys.stdout.write(u'Author:   {}\n'.format(__author__))
    sys.stdout.write(u'Email:    {}\n'.format(__email__))
    sys.stdout.write(u'Website:  {}\n'.format(__website__))
    sys.stdout.write('\n')
    sys.stdout.write(u'Python {}\n'.format(platform.python_version()))
    sys.stdout.write(u'{}\n'.format(platform.python_compiler()))

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
