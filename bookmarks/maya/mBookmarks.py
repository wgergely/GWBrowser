# -*- coding: utf-8 -*-
"""Bookmarks Maya plugin.

Make sure Bookmark is installed before trying to load the plugin.
The `*_ROOT` environment is set by the installer and is
required to find and load all the necessary Python modules.

"""
import sys
import os

from maya.app.general.mayaMixin import mixinWorkspaceControls
import maya.api.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds


INSTALL_ROOT = 'BOOKMARKS_ROOT'
pkg_name = INSTALL_ROOT.lower().replace('_root', '').strip()


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.

    """
    pass


def initializePlugin(plugin):
    """Loads the Bookmarks plugin.

    Python libraries are found in the `%*_ROOT%/shared` folder and the
    binaries in `%*_ROOT%/bin`.

    The environment is set by the installer and should point to the
    folder where bookmarks.exe resides.

    """
    if INSTALL_ROOT not in os.environ:
        raise EnvironmentError(
            u'Is Bookmarks installed?\n(Environment variable `{}` is not set.)'.format(INSTALL_ROOT))

    # Add the `shared` folder to the python path
    shared = u'{}{}{}'.format(os.environ[INSTALL_ROOT], os.path.sep, u'shared')
    sys.path.insert(0, os.path.abspath(os.path.normpath(shared)))

    # Add the `bin` folder to the current path envrionment
    bin = u'{}{}{}'.format(os.environ[INSTALL_ROOT], os.path.sep, u'bin')
    path = u'{};{}'.format(
        os.path.abspath(os.path.normpath(bin)),
        os.environ['PATH'])
    os.environ['PATH'] = path

    try:
        package = __import__(pkg_name)
        common = __import__('{}.common'.format(pkg_name))
        widget = __import__('{}.maya.widget'.format(pkg_name))
    except:
        raise


    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor=u'Gergely Wootsch', version=package.__version__)

    try:
        # Initiate the font_db. This will load the used custom fonts to Maya.
        common.font_db = common.FontDatabase()

        # Let Bookmarks know we're not launching it in standalone mode
        common.STANDALONE = False

        # If Maya has any UI scaling set scale Bookmark's interface accordingly
        common.UI_SCALE = cmds.mayaDpiSetting(scaleValue=True, query=True)

        # Load Bookmarks
        widget.maya_button = widget.MayaBrowserButton()
        cmds.evalDeferred(widget.maya_button.initialize)
    except Exception as e:
        raise Exception(e)


def uninitializePlugin(plugin):
    """Method is called by Maya when unloading the plug-in."""
    try:
        package = __import__(pkg_name)
        widget = __import__('{}.maya.widget'.format(pkg_name))
    except ImportError as e:
        raise 'Could not import \'{}\''.format(pkg_name)

    pluginFn = OpenMaya.MFnPlugin(
        plugin, vendor=u'Gergely Wootsch', version=package.__version__)

    def done():
        print '{} uninitialised.'.format(pkg_name)

    widget.instance().terminated.connect(done)
    widget.instance().main.shutdown.emit()
