# -*- coding: utf-8 -*-
"""mGWBrowser.py is the main Maya plugin of GWBrowser.
This file should be loaded a plugin using the Maya plugin manager.

"""

import sys
import re

from shiboken2 import wrapInstance
from PySide2 import QtWidgets

from maya.app.general.mayaMixin import mixinWorkspaceControls
import maya.api.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI

import maya.cmds as cmds

__version__ = '0.1.11'


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
        import gwbrowser.context.mayabrowserwidget as mayabrowserwidget
        mayabrowserwidget.maya_button = mayabrowserwidget.MayaBrowserButton()
        cmds.evalDeferred(mayabrowserwidget.maya_button.initialize)
    except ImportError as err:
        raise ImportError(err)
    except Exception as err:
        raise Exception(err)


def uninitializePlugin(plugin):
    """Method is called by Maya when unloading the plug-in."""
    import gwbrowser

    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor=u'Gergely Wootsch', version=gwbrowser.__version__)

    # First we will delete the embedded button
    try:
        from gwbrowser.context.mayabrowserwidget import MayaBrowserButton
        ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
        widget = wrapInstance(long(ptr), QtWidgets.QWidget)
        widget = widget.findChild(MayaBrowserButton)
        widget.deleteLater()
    except Exception as err:
        raise Exception(err)

    # Then we try and delete the main widget itself
    app = QtWidgets.QApplication.instance()
    try:
        for widget in app.allWidgets():
            match = re.match(
                ur'MayaBrowserWidget.*WorkspaceControl', widget.objectName())
            if match:
                widget.deleteLater()
                continue
            match = re.match(ur'MayaBrowserWidget.*', widget.objectName())
            if match:
                widget.remove_context_callbacks()
                widget.browserwidget.shutdown_timer.timeout.connect(widget.browserwidget.terminate)
                widget.browserwidget.shutdown_timer.start()
    except Exception as err:
        raise Exception(err)

    try:
        for k in mixinWorkspaceControls.items():
            if u'MayaBrowserWidget' in k:
                del mixinWorkspaceControls[k]
    except Exception as err:
        sys.stdout.write(
            '# GWBrowser: Failed to delete the workspace control.\n')
