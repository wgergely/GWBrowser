# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Browser - Maya plug-in.

Installation:
    Place 'mayaBrowserPlugin.py' into one of the plug-in directories read by maya.
    The list of plug-in directories can be retrieved by running the following in
    the script editor:

        import os
        for path in os.environ['MAYA_PLUG_IN_PATH'].split(';'):
            print path

    By default, on windows, the default user plug-in paths are:
        C:/Users/[user name]/Documents/maya/[version]/plug-ins
        C:/Users/[user name]/Documents/maya/plug-ins

    In Maya load the plug-in via the Plug-in Manager.

Important:
    Before loading the plug-in make sure the main 'gwbrowser' module is placed in
    one of the python script directories. You can get them by running:

    import sys
    for path in sys.path:
        print path

    By default, on windows, the default user script paths are:
        C:/Users/[user name]/Documents/maya/[version]/scripts
        C:/Users/[user name]/Documents/maya/scripts

    After copying, you can test by your setup by trying to import 'gwbrowser'
    by running in the script editor:

        import gwbrowser

    If you get any error messages something went south.

Credits:
    Gergely Wootsch, 2019, April.
    hello@gergely-wootsch.com
    http://gergely-wootsch.com

"""

import sys


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.

    """
    pass


def initializePlugin(plugin):
    """Method is called by Maya when initializing the plug-in."""
    from PySide2 import QtWidgets
    import maya.api.OpenMaya as OpenMaya
    import maya.cmds as cmds

    sys.path.append(r'\\sloth\3d_share\GWBrowser\python\Lib\site-packages')

    import gwbrowser
    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor='Gergely Wootsch', version=gwbrowser.__version__)

    try:
        from gwbrowser.context.mayabrowserwidget import MayaBrowserButton
        btn = MayaBrowserButton()
        cmds.evalDeferred(btn.initialize)
        sys.stdout.write('\n\n# GWBrowser: Plugin loaded.\n\n')
    except ImportError as err:
        sys.stderr.write(err)
        errStr = '# GWBrowser: Unable to import the "MayaBrowserButton" from the "gwbrowser" module.\n'
        errStr += '# GWBrowser: Make sure the "gwbrowser" python module has been added to Maya\'s python path.\n'
        errStr += '# GWBrowser: {}'.format(err)
        raise ImportError(errStr)
    except Exception as err:
        errStr = '# Borwser plug-in load error:\n\n{}\n'.format(err)
        sys.stderr.write(errStr)
        errStr += '# GWBrowser: {}\n'.format(err)
        raise Exception(err)


def uninitializePlugin(plugin):
    """Method is called by Maya when unloading the plug-in."""
    import maya.OpenMayaUI as OpenMayaUI
    import maya.api.OpenMaya as OpenMaya
    from maya.app.general.mayaMixin import mixinWorkspaceControls
    import re
    from PySide2 import QtWidgets
    from shiboken2 import wrapInstance


    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor='Gergely Wootsch', version=__version__)

    try:
        from gwbrowser.context.mayabrowserwidget import MayaBrowserButton
        ptr = OpenMayaUI.MQtUtil.findControl('ToolBox')
        widget = wrapInstance(long(ptr), QtWidgets.QWidget)
        widget = widget.findChild(MayaBrowserButton)
        widget.deleteLater()
    except Exception as err:
        sys.stdout.write('# GWBrowser: Failed to delete the tool button.\n')

    app = QtWidgets.QApplication.instance()
    try:
        for widget in app.allWidgets():
            match = re.match(r'MayaBrowserWidget.*WorkspaceControl', widget.objectName())
            if match:
                widget.deleteLater()
                continue
            match = re.match(r'MayaBrowserWidget.*', widget.objectName())
            if match:
                widget.remove_context_callbacks()
                widget.deleteLater()
                continue
    except Exception as err:
        sys.stdout.write('# GWBrowser: Failed to delete the Browser window.\n')

    try:
        for k in mixinWorkspaceControls.items():
            if u'MayaBrowserWidget' in k:
                del mixinWorkspaceControls[k]
    except Exception as err:
        sys.stdout.write('# GWBrowser: Failed to delete the workspace control.\n')

    try:
        del sys.modules['gwbrowser']
        for k in sys.modules.items():
            if 'gwbrowser.' in k:
                del sys.modules[k]
    except Exception as err:
        sys.stdout.write('# GWBrowser: Failed unload the python modules.\n')
