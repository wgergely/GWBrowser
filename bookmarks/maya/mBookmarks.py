# -*- coding: utf-8 -*-
"""Maya plugin."""

import sys
import re

from shiboken2 import wrapInstance
from PySide2 import QtWidgets, QtCore

from maya.app.general.mayaMixin import mixinWorkspaceControls
import maya.api.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI

import maya.cmds as cmds

__version__ = u'0.3.0'


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.

    """
    pass


def initializePlugin(plugin):
    """Loads the Bookmarks plugin.

    Python libraries are found in the `%BOOKMARKS_ROOT%/shared` folder and the
    binaries are in `%BOOKMARKS_ROOT%/bin`.

    The environment is set by the installer normally and should point to the
    folder where bookmarks.exe resides.

    """
    import sys
    import os

    k = 'BOOKMARKS_ROOT'
    if k not in os.environ:
        raise EnvironmentError(
            u'Is Bookmarks installed?\n(Environment variable `{}` is not set)'.format(k))

    shared = u'{}{}{}'.format(os.environ[k], os.path.sep, u'shared')
    bin = u'{}{}{}'.format(os.environ[k], os.path.sep, u'bin')
    sys.path.insert(0, os.path.abspath(os.path.normpath(shared)))
    path = u'{};{}'.format(
        os.path.abspath(os.path.normpath(bin)),
        os.environ['PATH'])
    os.environ['PATH'] = path

    import bookmarks

    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor=u'Gergely Wootsch', version=bookmarks.__version__)

    try:

        import bookmarks.maya.widget as widget
        widget.maya_button = widget.MayaBrowserButton()
        cmds.evalDeferred(widget.maya_button.initialize)

    except ImportError as e:
        raise ImportError(e)

    except Exception as e:
        raise Exception(e)


def uninitializePlugin(plugin):
    """Method is called by Maya when unloading the plug-in."""
    import bookmarks
    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor=u'Gergely Wootsch', version=bookmarks.__version__)

    import bookmarks.maya as maya
    widget = maya.widget.instance()

    def p():
        print 'Plugin uninitialised.'

    widget.terminated.connect(p)
    widget.browserwidget.shutdown.emit()
