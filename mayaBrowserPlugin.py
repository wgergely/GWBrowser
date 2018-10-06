# -*- coding: utf-8 -*-
"""Browser - Maya plug-in.

This plug-in is a Maya front-end to 'Browser', a custom PyQt pipeline package.
Please note, this is a development release, and I can take no warranty for any
of the functionality.

Description:
    The plug-in is responsible for setting Maya projects and importing, opening and
    referencing maya scenes.
    Once installed and loaded, the browser window can be found in Maya's 'File'
    menu. The application-wide shortcut to show the panel is 'Ctrl+Shift+O'.

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

    Then, in Maya you have to load the plug-in via the Plug-in Manager.

Important:
    Before loading the plug-in make sure the main 'Browser' module is placed in
    one of the python script directories. You can get them by running:

    import sys
    for path in sys.path:
        print path

    By default, on windows, the default user script paths are:
        C:/Users/[user name]/Documents/maya/[version]/scripts
        C:/Users/[user name]/Documents/maya/scripts

    After copying, you can test by your setup by trying to import 'browser'
    by running in the script editor:

    import browser

    If you get any error messages something went south...

Credits:
    Gergely Wootsch, 2018, September.
    hello@gergely-wootsch.com
    http://gergely-wootsch.com

"""
# pylint: disable=E1101, C0103, R0913, I1101

import sys
from PySide2 import QtGui, QtWidgets, QtCore
import maya.api.OpenMaya as OpenMaya


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.

    """
    pass


class ShowBrowserCmd(OpenMaya.MPxCommand):
    """Custom maya command."""
    kPluginCmdName = 'showBrowser'

    def __init__(self):
        """Init method."""
        super(ShowBrowserCmd, self).__init__()

    @staticmethod
    def cmdCreator():
        """Creates an instance of the command."""
        return ShowBrowserCmd()

    def doIt(self, args):
        """This is the main method called by maya when running the command."""
        from mayabrowser.toolbar import MayaBrowserWidget
        MayaBrowserWidget().show()


def initializePlugin(plugin):
    """Method is called by Maya when initializing the plug-in."""
    pluginFn = OpenMaya.MFnPlugin(plugin, vendor='Gergely Wootsch', version='0.1.0')

    try:
        from mayabrowser.toolbar import MayaBrowserWidget
        app = QtCore.QCoreApplication.instance()
        browser = MayaBrowserWidget() # Initializing our singleton
        browser.add_maya_callbacks()
        browser.add_global_app_actions()

        pluginFn.registerCommand(
            ShowBrowserCmd.kPluginCmdName, ShowBrowserCmd.cmdCreator
        )

    except ImportError as err:
        sys.stderr.write(err)
        errStr = '# Browser:  Unable to import the "mayabrowser" from the "browser" module.\n'
        errStr = '# Browser:  Make sure the "browser" python module has been added to Maya\'s python path.'
        raise ImportError(errStr)
    except:
        sys.stderr.write(
            'Failed to register command: {}\n'.format(ShowBrowserCmd.kPluginCmdName)
        )
        raise


def uninitializePlugin(plugin):
    """Method is called by Maya when unloading the plug-in."""
    pluginFn = OpenMaya.MFnPlugin(plugin, vendor='Gergely Wootsch', version='0.1.0')

    try:
        from mayabrowser.toolbar import MayaBrowserWidget
        from mayabrowser.toolbar import Singleton

        browser = MayaBrowserWidget()
        browser.remove_maya_callbacks()
        browser.remove_global_app_actions()
        browser.uninitialize()

        # Delete instances
        for k, _ in Singleton._instances.items():
            Singleton._instances[k].deleteLater()
            del Singleton._instances[k]

        del Singleton
        del browser
        del MayaBrowserWidget

        # Deleting the python modules
        for k, _ in sys.modules.items():
            if 'browser' in k:
                del sys.modules[k]

        pluginFn.deregisterCommand(ShowBrowserCmd.kPluginCmdName)
    except Exception as err:
        sys.stderr.write(err)
        sys.stderr.write(
            'Failed to unregister command: {}\n'.format(ShowBrowserCmd.kPluginCmdName)
        )
        raise
