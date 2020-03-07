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
    except ImportError as err:
        raise ImportError(err)
    except Exception as err:
        raise Exception(err)


@QtCore.Slot()
def delete_module_import_cache():
    name = 'gwbrowser'
    name_ext = '{}.'.format(name)

    def compare(loaded):
        return (loaded == name) or loaded.startswith(name_ext)

    # prevent changing iterable while iterating over it
    all_mods = tuple(sys.modules)
    sub_mods = filter(compare, all_mods)
    for pkg in sub_mods:
        # remove sub modules and packages from import cache
        del sys.modules[pkg]

    sys.stdout.write(
        u'# GWBrowser: Import cache deleted.\n')


@QtCore.Slot()
def remove_button():
    """Removes the workspaceControl, and workspaceControlState objects."""
    from gwbrowser.maya.widget import MayaBrowserButton
    ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
    widget = wrapInstance(long(ptr), QtWidgets.QWidget)
    widget = widget.findChild(MayaBrowserButton)

    if not widget:
        return

    widget.deleteLater()


def remove_workspace_control(workspace_control):
    if cmds.workspaceControl(workspace_control, q=True, exists=True):
        cmds.deleteUI(workspace_control)
        if cmds.workspaceControlState(workspace_control, ex=True):
            cmds.workspaceControlState(workspace_control, remove=True)

    try:
        for k in mixinWorkspaceControls.items():
            if u'MayaBrowserWidget' in k:
                del mixinWorkspaceControls[k]
    except:
        pass

    sys.stdout.write(
        u'# GWBrowser: UI deleted.\n')

    mbox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.NoIcon,
                                 'Plugin unloaded', u'GWBrowser unloaded successfully.').exec_()


def uninitializePlugin(plugin):
    """Method is called by Maya when unloading the plug-in."""
    import gwbrowser
    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor=u'Gergely Wootsch', version=gwbrowser.__version__)

    app = QtWidgets.QApplication.instance()
    widget = None

    for widget in app.allWidgets():
        # Skipping workspaceControls objects, just in case there's a name conflict
        # between what the parent().objectName() and this method yields
        if re.match(ur'MayaBrowserWidget.*WorkspaceControl', widget.objectName()):
            continue
        match = re.match(ur'MayaBrowserWidget.*', widget.objectName())
        if not match:
            continue
        break

    if not widget:
        sys.stderr.write(
            u'# GWBrowser: MayaBrowserWidget not found.\n')
        return
    if not hasattr(widget, 'browserwidget'):
        sys.stderr.write(
            u'# GWBrowser: MayaBrowserWidget not found.\n')
        return

    widget.workspace_timer.stop()
    widget.remove_context_callbacks()
    remove_button()
    widget.browserwidget.terminate()
    for widget in app.allWidgets():
        try:
            if re.match(ur'MayaBrowserWidget.*WorkspaceControl', widget.objectName()):
                remove_workspace_control(widget.objectName())
        except:
            pass
    delete_module_import_cache()
