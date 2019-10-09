# -*- coding: utf-8 -*-
"""mGWBrowser.py is the main Maya plugin of GWBrowser.
This file should be loaded a plugin using the Maya plugin manager.

"""

import sys
import re

from shiboken2 import wrapInstance
from PySide2 import QtWidgets, QtCore

from maya.app.general.mayaMixin import mixinWorkspaceControls
import maya.api.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI

import maya.cmds as cmds

__version__ = '0.2.1'


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


def find_widget():
    """Returns the first ``MayaBrowserWidget`` widget instance found."""
    app = QtWidgets.QApplication.instance()
    for widget in app.allWidgets():
        # Skipping workspaceControls objects, just in case there's a name conflict
        # between what the parent().objectName() and this method yields
        if re.match(ur'MayaBrowserWidget.*WorkspaceControl', widget.objectName()):
            continue
        match = re.match(ur'MayaBrowserWidget.*', widget.objectName())
        if not match:
            continue
        return widget
    return None


@QtCore.Slot()
def remove_widgets():
    """Removes the workspaceControl, and workspaceControlState objects."""
    from gwbrowser.context.mayabrowserwidget import MayaBrowserButton
    ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
    widget = wrapInstance(long(ptr), QtWidgets.QWidget)
    widget = widget.findChild(MayaBrowserButton)
    if widget:
        widget.deleteLater()

    widget = find_widget()
    if not widget:
        return

    if not widget.parent():
        widget.close()
        widget.deleteLater()
        return

    workspace_control = widget.parent().objectName()
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

    widget = find_widget()
    if not widget:
        sys.stderr.write(
            u'# GWBrowser: MayaBrowserWidget not found.\n')
        return
    if not hasattr(widget, 'browserwidget'):
        sys.stderr.write(
            u'# GWBrowser: MayaBrowserWidget not found.\n')
        return

    widget.browserwidget.shutdown_timer.timeout.connect(
        widget.browserwidget.terminate)
    widget.browserwidget.terminated.connect(remove_widgets)
    widget.browserwidget.terminated.connect(delete_module_import_cache)

    widget.workspace_timer.stop()
    widget.remove_context_callbacks()
    widget.browserwidget.shutdown_timer.start()
