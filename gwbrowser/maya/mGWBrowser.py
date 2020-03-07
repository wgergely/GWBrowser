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
    """Method is called by Maya when initializing the plug-in."""
    import gwbrowser
    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor=u'Gergely Wootsch', version=gwbrowser.__version__)

    try:

        import gwbrowser.maya.widget as widget
        widget.maya_button = widget.MayaBrowserButton()
        cmds.evalDeferred(widget.maya_button.initialize)

    except ImportError as e:
        raise ImportError(e)

    except Exception as e:
        raise Exception(e)


def uninitializePlugin(plugin):
    """Method is called by Maya when unloading the plug-in."""
    import gwbrowser
    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor=u'Gergely Wootsch', version=gwbrowser.__version__)

    import gwbrowser.maya as maya
    widget = maya.widget.instance()

    def p():
        print 'Plugin uninitialised.'

    widget.terminated.connect(p)
    widget.browserwidget.shutdown.emit()
