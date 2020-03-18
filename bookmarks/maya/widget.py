# -*- coding: utf-8 -*-
"""This module defines Bookmarks's ``MayaBrowserWidget``, a dockable `mayaMixin`
widget that wraps BrowserWidget.

Usage:

    .. code-block:: python

        import bookmarks.maya.widget as mb
        mb.show()

"""
import os
import re
import string
import uuid
import time
import sys
import functools
import collections

from PySide2 import QtWidgets, QtGui, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import mixinWorkspaceControls
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as OpenMaya
from shiboken2 import wrapInstance
import maya.cmds as cmds

import bookmarks.settings as settings
import bookmarks.common as common
import bookmarks.images as images
from bookmarks.basecontextmenu import BaseContextMenu, contextmenu
from bookmarks.browserwidget import BrowserWidget
import bookmarks.common_ui as common_ui
import bookmarks.addfilewidget as addfilewidget


ALEMBIC_EXPORT_PATH = u'{workspace}/{exports}/abc/{set}/{set}_v001.abc'
CAPTURE_PATH = u'viewport_captures'


maya_button = None
"""The bookmarks shortcut icon button. Set by the ``mBookmarks.py`` when the plugin is initializing."""

__instance__ = None
"""The bookmarks widget instance."""


MAYA_FPS = {
    u'hour': 2.777777777777778e-4,
    u'min': 0.0166667,
    u'sec': 1.0,
    u'millisec': 1000.0,
    u'game': 15.0,
    u'film': 24.0,
    u'pal': 25.0,
    u'ntsc': 30.0,
    u'show': 48.0,
    u'palf': 50.0,
    u'ntscf': 60.0,
    u'2fps': 2.0,
    u'3fps': 3.0,
    u'4fps': 4.0,
    u'5fps': 5.0,
    u'6fps': 6.0,
    u'8fps': 8.0,
    u'10fps': 10.0,
    u'12fps': 12.0,
    u'16fps': 16.0,
    u'20fps': 20.0,
    u'40fps': 40.0,
    u'75fps': 75.0,
    u'100fps': 100.0,
    u'120fps': 120.0,
    u'200fps': 200.0,
    u'240fps': 240.0,
    u'250fps': 250.0,
    u'300fps': 300.0,
    u'400fps': 400.0,
    u'500fps': 500.0,
    u'600fps': 600.0,
    u'750fps': 750.0,
    u'1200fps': 1200.0,
    u'1500fps': 1500.0,
    u'2000fps': 2000.0,
    u'3000fps': 3000.0,
    u'6000fps': 6000.0,
    u'23.976fps': 23.976,
    u'29.97fps': 29.97,
    u'29.97df': 29.97,
    u'47.952fps': 47.952,
    u'59.94fps': 59.94,
    u'44100fps': 44100.0,
    u'48000fps': 48000.0,
}

def set_framerate(fps):
    for k, v in MAYA_FPS.iteritems():
        if fps == v:
            cmds.currentUnit(time=k)
            return k
    raise ValueError(u'Invalid fps provided')

def get_framerate():
    return MAYA_FPS[cmds.currentUnit(query=True, time=True)]


def get_preference(k):
    return settings.local_settings.value(u'preferences/{}'.format(k))


def instance():
    return __instance__


@QtCore.Slot()
def show():
    """Main function to show ``MayaBrowserWidget`` inside Maya as a dockable
    widget.

    The function will create ``MayaBrowserWidget`` if it doesn't yet exist and
    dock it to the _AttributeEditor_. If it exists it will get the existing
    instance and show it if not currently visible, hide it if visible.

    Usage

        Run the following python code inside maya:

        .. code-block:: python

            import bookmarks.maya.widget as widget
            widget.show()

    """
    app = QtWidgets.QApplication.instance()

    # We will check if there's already a _MayaBrowserWidget_ instance
    for widget in app.allWidgets():
        # Skipping workspaceControls objects, just in case there's a name conflict
        # between what the parent().objectName() and this method yields
        if re.match(ur'MayaBrowserWidget.*WorkspaceControl', widget.objectName()):
            continue

        match = re.match(ur'MayaBrowserWidget.*', widget.objectName())
        if not match:
            continue

        if not widget.parent():
            state = widget.isVisible()
            widget.setVisible(not state)
            return

        workspace_control = widget.parent().objectName()
        if cmds.workspaceControl(workspace_control, q=True, exists=True):
            visible = cmds.workspaceControl(
                workspace_control, q=True, visible=True)
            if cmds.workspaceControl(workspace_control, q=True, floating=True):
                cmds.workspaceControl(
                    workspace_control, e=True, visible=not visible)
                return
            state = cmds.workspaceControl(
                workspace_control, q=True, collapse=True)
            if state is None:
                cmds.workspaceControl(
                    workspace_control, e=True, tabToControl=(u'AttributeEditor', -1))
                cmds.workspaceControl(workspace_control, e=True, visible=True)
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=False)
                return
            if not widget.parent().isVisible():
                cmds.workspaceControl(workspace_control, e=True, visible=True)
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=False)
                return
            if state is False:
                cmds.workspaceControl('AttributeEditor', e=True, visible=True)
                cmds.workspaceControl(
                    'AttributeEditor', e=True, collapse=False)
                return
            if state is True:
                cmds.workspaceControl(
                    workspace_control, e=True, collapse=True)
            return
        else:
            state = widget.parent().isVisible()
            widget.setVisible(not state)
        return

    # Initializing MayaBrowserWidget...
    try:
        widget = MayaBrowserWidget()
        widget.show()

        sys.stdout.write(
            u'# Bookmarks: Initialized successfully\n')

        # We will defer the execution, otherwise the widget does not dock properly
        for widget in app.allWidgets():
            match = re.match(
                ur'MayaBrowserWidget.*WorkspaceControl', widget.objectName())
            if match:
                func = functools.partial(
                    cmds.workspaceControl,
                    widget.objectName(),
                    e=True,
                    tabToControl=(u'AttributeEditor', -1)
                )
                cmds.evalDeferred(func)
                cmds.evalDeferred(widget.raise_)
                return
    except Exception as err:
        common_ui.ErrorBox(
            u'Could not show {}'.format(common.PRODUCT),
            u'{}'.format(err)
        ).open()
        common.Log.error(u'Could not open the plugin window.')
        raise


def report_export_progress(start, current, end, start_time):
    """A litle progress report get some export feedback."""
    elapsed = time.time() - start_time
    elapsed = time.strftime('%H:%M.%Ssecs', time.localtime(elapsed))

    start = int(start)
    current = int(current)
    end = int(end)

    _current = current - start
    _end = end - start

    if _end < 1:
        progress = float(_current) * 100
    else:
        progress = float(_current) / float(_end) * 100

    progress = u'[{}{}] {}%'.format(
        u'#' * int(progress),
        u' ' * (100 - int(progress)),
        int(progress)
    )

    msg = u'# Exporting frame {current} of {end}\n# {progress}\n# Elapsed: {elapsed}\n'.format(
        current=current,
        end=end,
        progress=progress,
        elapsed=elapsed
    )
    sys.stdout.write(msg)


def outliner_sets():
    """The main function responsible for returning the user created object sets
    from the current Maya scene. There's an extra caveat: the set has to contain
    the word 'geo' to be considered valid.

    Returns:
        dict: key is the set's name, the value is the contained meshes.

    """
    def _is_set_created_by_user(name):
        """From the good folks at cgsociety - filters the in-scene sets to return
        the user-created items only.

        https://forums.cgsociety.org/t/maya-mel-python-list-object-sets-visible-in-the-dag/1586067/2

        Returns:
            bool: True if the user created the set, otherwise False.

        """
        try:
            # We first test for plug-in object sets.
            apiNodeType = cmds.nodeType(name, api=True)
        except RuntimeError:
            return False

        if apiNodeType == "kPluginObjectSet":
            return True

        # We do not need to test is the object is a set, since that test
        # has already been done by the outliner
        try:
            nodeType = cmds.nodeType(name)
        except RuntimeError:
            return False

        # We do not want any rendering sets
        if nodeType == "shadingEngine":
            return False

        # if the object is not a set, return false
        if not (nodeType == "objectSet" or
                nodeType == "textureBakeSet" or
                nodeType == "vertexBakeSet" or
                nodeType == "character"):
            return False

        # We also do not want any sets with restrictions
        restrictionAttrs = ["verticesOnlySet", "edgesOnlySet",
                            "facetsOnlySet", "editPointsOnlySet", "renderableOnlySet"]
        if any(cmds.getAttr("{0}.{1}".format(name, attr)) for attr in restrictionAttrs):
            return False

        # Do not show layers
        if cmds.getAttr("{0}.isLayer".format(name)):
            return False

        # Do not show bookmarks
        annotation = cmds.getAttr("{0}.annotation".format(name))
        if annotation == "bookmarkAnimCurves":
            return False

        return True


    sets_data = {}
    for s in sorted([k for k in cmds.ls(sets=True) if _is_set_created_by_user(k)]):
        # I added this because of the plethora of sets in complex animation scenes
        if u'geo' not in s:
            continue

        dag_set_members = cmds.listConnections(u'{}.dagSetMembers'.format(s))
        if not dag_set_members:
            continue

        # We can ignore this group is it does not contain any shapes
        members = [
            cmds.ls(f, long=True)[-1] for f in dag_set_members if cmds.listRelatives(f, shapes=True, fullPath=True)]
        if not members:
            continue

        sets_data[s] = members

    return sets_data


def export_alembic(destination_path, outliner_set, startframe, endframe, step=1.0):
    """Main Alembic export function.

    Exporting is based on outliner sets and their contents. For each member of
    the this set, Bookmarks will try to find the valid shape nodes to duplicate
    their geometry in the  world-space.

    Only the normals, geometry and uvs will be exported. No addittional user or
    scene data will is picked up by default.

    """
    # ======================================================
    # ERROR CHECKING
    # Check destination before proceeding
    if not isinstance(outliner_set, (tuple, list)):
        raise TypeError('Expected <type \'list\'>, got {}'.format(type(outliner_set)))

    destination_info = QtCore.QFileInfo(destination_path)
    destination_dir = destination_info.dir()
    _destination_dir_info = QtCore.QFileInfo(destination_dir.path())

    if not _destination_dir_info.exists():
        s = u'Unable to save the alembic file, {} does not exists.'.format(
            _destination_dir_info.filePath())
        common_ui.ErrorBox(
            u'Alembic export failed.',
            s
        ).open()
        common.Log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    if not _destination_dir_info.isReadable():
        s = u'Unable to save the alembic file, {} is not readable.'.format(
            _destination_dir_info.filePath())
        common_ui.ErrorBox(
            u'Alembic export failed.',
            s
        ).open()
        common.Log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    if not _destination_dir_info.isWritable():
        s = u'Unable to save the alembic file, {} is not writable.'.format(
            _destination_dir_info.filePath())
        common_ui.ErrorBox(
            u'Alembic export failed.',
            s
        ).open()
        common.Log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    # ======================================================

    destination_path = QtCore.QFileInfo(destination_path).filePath()

    # If the extension is missing, we'll add it here
    if not destination_path.lower().endswith('.abc'):
        destination_path = destination_path + u'.abc'

    def is_intermediate(s): return cmds.getAttr(
        u'{}.intermediateObject'.format(s))

    # We'll need to use the DecomposeMatrix Nodes, let's check if the plugin
    # is loaded and ready to use
    if not cmds.pluginInfo(u'matrixNodes.mll', loaded=True, q=True):
        cmds.loadPlugin(u'matrixNodes.mll', quiet=True)

    world_shapes = []
    valid_shapes = []

    # First, we will collect the available shapes from the given set
    for item in outliner_set:
        shapes = cmds.listRelatives(item, fullPath=True)
        for shape in shapes:
            if is_intermediate(shape):
                continue

            basename = shape.split(u'|').pop()
            try:
                # AbcExport will fail if a transform or a shape node's name is not unique
                # We will try and see if this passes...
                cmds.listRelatives(basename)
            except ValueError as err:
                print u'"{shape}" does not have a unique name. This is not usually allowed for alembic exports and might cause the export to fail.\nError: {err}'.format(
                    shape=shape, err=err)

            # Camera's don't have mesh nodes but we still want to export them!
            if cmds.nodeType(shape) != u'camera':
                if not cmds.attributeQuery(u'outMesh', node=shape, exists=True):
                    continue
            valid_shapes.append(shape)

    if not valid_shapes:
        raise RuntimeError(
            u'# No valid shapes found in "{}" to export! Aborting...'.format(outliner_set))

    cmds.select(clear=True)

    # Creating a temporary namespace to avoid name-clashes later when we duplicate
    # the meshes. We will delete this namespace after the export...
    if cmds.namespace(exists=u'mayaExport'):
        cmds.namespace(removeNamespace=u'mayaExport',
                       deleteNamespaceContent=True)
    ns = cmds.namespace(add=u'mayaExport')

    world_transforms = []

    try:
        # For meshes, we will create an empty mesh and connect the outMesh and
        # UV attributes from our source.
        # We will also apply the source mesh's transform matrix to the newly created mesh
        for shape in valid_shapes:
            basename = shape.split(u'|').pop()
            if cmds.nodeType(shape) != u'camera':
                # Create new empty shape node
                world_shape = cmds.createNode(
                    u'mesh', name=u'{}:{}'.format(ns, basename))

                # outMesh -> inMesh
                cmds.connectAttr(u'{}.outMesh'.format(
                    shape), u'{}.inMesh'.format(world_shape), force=True)
                # uvSet -> uvSet
                cmds.connectAttr(u'{}.uvSet'.format(shape),
                                 u'{}.uvSet'.format(world_shape), force=True)

                # worldMatrix -> transform
                decompose_matrix = cmds.createNode(
                    u'decomposeMatrix', name=u'{}:decomposeMatrix#'.format(ns))
                cmds.connectAttr(
                    u'{}.worldMatrix[0]'.format(shape), u'{}.inputMatrix'.format(decompose_matrix), force=True)
                #
                transform = cmds.listRelatives(
                    world_shape, fullPath=True, type='transform', parent=True)[0]
                world_transforms.append(transform)
                #
                cmds.connectAttr(
                    u'{}.outputTranslate'.format(decompose_matrix), u'{}.translate'.format(transform), force=True)
                cmds.connectAttr(
                    u'{}.outputRotate'.format(decompose_matrix), u'{}.rotate'.format(transform), force=True)
                cmds.connectAttr(
                    u'{}.outputScale'.format(decompose_matrix), u'{}.scale'.format(transform), force=True)
            else:
                world_shape = shape
                world_transforms.append(cmds.listRelatives(
                    world_shape, fullPath=True, type='transform', parent=True)[0])
            world_shapes.append(world_shape)

        perframecallback = u'"import bookmarks.maya.widget as w;w.report_export_progress({}, #FRAME#, {}, {})"'.format(startframe, endframe, time.time())

        jobArg = u'{f} {fr} {s} {uv} {ws} {wv} {wuvs} {sn} {rt} {df} {pfc} {ro}'.format(
            f=u'-file "{}"'.format(destination_path),
            fr=u'-framerange {} {}'.format(startframe, endframe),
            s=u'-step {}'.format(step),
            uv=u'-uvWrite',
            ws=u'-worldSpace',
            wv=u'-writeVisibility',
            # eu='-eulerFilter',
            wuvs=u'-writeuvsets',
            sn=u'-stripNamespaces',
            rt=u'-root {}'.format(u' -root '.join(world_transforms)),
            df=u'-dataFormat {}'.format(u'ogawa'),
            pfc=u'-pythonperframecallback {}'.format(perframecallback),
            ro='-renderableOnly'
        )
        print '# jobArg: `{}`'.format(jobArg)
        cmds.AbcExport(jobArg=jobArg)

    except Exception as err:
        common_ui.ErrorBox(
            u'An error occured exporting Alembic cache',
            u'{}'.format(err)
        ).open()
        common.Log.error(u'Could not open the plugin window.')
        raise

    finally:
        # Finally, we will delete the previously created namespace and the object
        # contained inside. I wrapped the call into an evalDeferred to let maya
        # recover after the export and delete the objects more safely.

        def teardown():
            cmds.namespace(
                removeNamespace=u'mayaExport', deleteNamespaceContent=True)
        cmds.evalDeferred(teardown)


def _capture_viewport_destination():
    capture_folder = get_preference(u'capture_path')
    capture_folder = capture_folder if capture_folder else CAPTURE_PATH

    workspace = cmds.workspace(q=True, rootDirectory=True).rstrip(u'/')
    scene_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))
    dest = u'{workspace}/{capture_folder}/{scene}/{scene}'.format(
        workspace=workspace,
        capture_folder=capture_folder,
        scene=scene_info.baseName()
    )
    return capture_folder, workspace, dest

@QtCore.Slot()
def capture_viewport(size=1.0):
    """Saves a versioned capture to the ``capture_folder`` defined in the preferences.

    The script will output to the an image sequence and if FFmpeg is present converts it to a h264 movie file.
    It will also try to create a ``latest`` folder with a copy of the last exported image sequence.

    Usage:

        .. code-block:: python

        MayaBrowserWidget.capture_viewport()


    """
    import bookmarks.maya._mCapture as mCapture
    ext = u'png'

    DisplayOptions = {
        "displayGradient": True,
        "background": (0.5, 0.5, 0.5),
        "backgroundTop": (0.6, 0.6, 0.6),
        "backgroundBottom": (0.4, 0.4, 0.4),
    }
    CameraOptions = {
        "displayGateMask": False,
        "displayResolution": False,
        "displayFilmGate": False,
        "displayFieldChart": False,
        "displaySafeAction": False,
        "displaySafeTitle": False,
        "displayFilmPivot": False,
        "displayFilmOrigin": False,
        "overscan": 1.0,
        "depthOfField": False,
    }

    scene_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))
    capture_folder, workspace, complete_filename = _capture_viewport_destination()

    _dir = QtCore.QFileInfo(complete_filename).dir()
    if not _dir.exists():
        _dir.mkpath(u'.')

    panel = cmds.getPanel(withFocus=True)
    # Not all panels are modelEditors
    if panel is None or cmds.objectTypeUI(panel) != u'modelEditor':
        s = u'Activate a viewport before starting a capture.'
        common_ui.MessageBox(
            'The active window is not a viewport.',
            s
        ).open()
        common.Log.error(s)
        raise RuntimeError(s)

    camera = cmds.modelPanel(panel, query=True, camera=True)

    options = mCapture.parse_view(panel)
    options['viewport_options'].update({
        "wireframeOnShaded": False,
        "displayAppearance": 'smoothShaded',
        "selectionHiliteDisplay": False,
        "headsUpDisplay": False,
        "imagePlane": False,
        "nurbsCurves": False,
        "nurbsSurfaces": False,
        "polymeshes": True,
        "subdivSurfaces": True,
        "planes": True,
        "cameras": False,
        "controlVertices": False,
        "lights": False,
        "grid": False,
        "hulls": False,
        "joints": False,
        "ikHandles": False,
        "deformers": False,
        "dynamics": False,
        "fluids": False,
        "hairSystems": False,
        "follicles": False,
        "nCloths": False,
        "nParticles": False,
        "nRigids": False,
        "dynamicConstraints": False,
        "locators": False,
        "manipulators": False,
        "dimensions": False,
        "handles": False,
        "pivots": False,
        "strokes": False,
        "motionTrails": False
    })

    # Hide existing panels
    current_state = {}
    for panel in cmds.getPanel(type=u'modelPanel'):
        if not cmds.modelPanel(panel, exists=True):
            continue

        try:
            ptr = OpenMayaUI.MQtUtil.findControl(panel)
            if not ptr:
                continue
            panel_widget = wrapInstance(long(ptr), QtWidgets.QWidget)
            current_state[panel] = panel_widget.isVisible()
            if panel_widget:
                panel_widget.hide()
        except:
            print '# An error occured hiding {}'.format(panel)

    width = int(cmds.getAttr('defaultResolution.width') * size)
    height = int(cmds.getAttr('defaultResolution.height') * size)

    error = False
    try:
        mCapture.capture(
            camera=camera,
            width=width,
            height=height,
            display_options=DisplayOptions,
            camera_options=CameraOptions,
            viewport2_options=options['viewport2_options'],
            viewport_options=options['viewport_options'],
            format=u'image',
            compression=ext,
            filename=complete_filename,
            overwrite=True,
            viewer=False
        )
    except Exception as err:
        print u'# And error occured capturing the viewport: {}'.format(err)
        error = True
    finally:
        cmds.ogs(reset=True)
        # Show hidden panels
        for panel in cmds.getPanel(type=u'modelPanel'):
            if not cmds.modelPanel(panel, exists=True):
                continue
            try:
                ptr = OpenMayaUI.MQtUtil.findControl(panel)
                if not ptr:
                    continue
                panel_widget = wrapInstance(long(ptr), QtWidgets.QWidget)
                if panel_widget:
                    if panel in current_state:
                        panel_widget.setVisible(current_state[panel])
                    else:
                        panel_widget.setVisible(True)
            except:
                print '# Could not restore {} after capture'.format(panel)

        print u'# Capture saved to:\n{}'.format(complete_filename)

    if error:
        return

    rv_seq_path = u'{workspace}/{capture_folder}/{scene}/{scene}.{frame}.{ext}'.format(
        workspace=workspace,
        capture_folder=capture_folder,
        scene=scene_info.baseName(),
        frame=u'{}'.format(
            int(cmds.playbackOptions(q=True, minTime=True))).zfill(4),
        ext=ext
    )

    val = get_preference(u'push_to_rv')
    val = val if val is not None else True
    if val:
        common.push_to_rv(rv_seq_path)

    val = get_preference(u'reveal_capture')
    val = val if val is not None else False
    if val:
        common.reveal(rv_seq_path)

    publish_capture(workspace, capture_folder, scene_info, ext)


def publish_capture(workspace, capture_folder, scene_info, ext):
    """Copies the latest capture sequence as a version agnostic copy."""
    asset = workspace.split(u'/').pop()
    start = int(cmds.playbackOptions(q=True, minTime=True))
    end = int(cmds.playbackOptions(q=True, maxTime=True))
    duration = (end - start) + 1

    latest_dir = u'{workspace}/{capture_folder}/latest'.format(
        workspace=workspace,
        capture_folder=capture_folder,
        asset=asset,
    )
    _dir = QtCore.QDir(latest_dir)
    if not _dir.exists():
        if not _dir.mkpath('.'):
            s = 'Could not create folder published capture.'
            common_ui.ErrorBox(
                u'Could not publish the capture',
                s
            ).open()
            common.Log.error(s)
            raise OSError(s)

    if not QtCore.QFileInfo(latest_dir).isWritable():
        s = 'Publish folder is not writable.'
        common_ui.ErrorBox(
            u'Could not publish the capture',
            s
        ).open()
        common.Log.error(s)
        raise OSError(s)

    import bookmarks._scandir as _scandir
    for entry in _scandir.scandir(latest_dir):
        os.remove(entry.path)


    idx = 0
    for n in xrange(int(duration)):
        source = u'{workspace}/{capture_folder}/{scene}/{scene}.{n}.{ext}'.format(
            workspace=workspace,
            capture_folder=capture_folder,
            scene=scene_info.baseName(),
            n=str(n + int(start)).zfill(4),
            ext=ext
        )
        dest = u'{workspace}/{capture_folder}/latest/{asset}_capture_{n}.{ext}'.format(
            workspace=workspace,
            capture_folder=capture_folder,
            asset=asset,
            n=str(n + int(start)).zfill(4),
            ext=ext
        )
        master_file = QtCore.QFile(dest)
        if idx == 0 and not QtCore.QFileInfo(source).exists():
            raise RuntimeError('Could not find {}'.format(source))
            return

        # Remove the
        QtCore.QFile.copy(source, dest)
        idx += 1


def contextmenu_browserwidget(func):
    """Decorator to create a menu set."""
    @functools.wraps(func)
    def func_wrapper(self, menu_set):
        widget = self.parent().parent().parent().parent()
        menu_set = func(
            self,
            menu_set,
            browserwidget=widget
        )
        return menu_set
    return func_wrapper


class BrowserButtonContextMenu(BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(BrowserButtonContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)

        self.add_separator()
        #
        self.add_maya_actions_menu()
        #
        self.add_separator()
        #
        self.add_export_alembic_menu()
        #
        self.add_separator()
        #
        self.add_capture_menu()
        #
        self.add_separator()
        #
        self.add_show_menu()
        #
        self.add_separator()

    @contextmenu
    def add_maya_actions_menu(self, menu_set):
        menu_set[u'save'] = {
            u'icon': images.ImageCache.get_rsc_pixmap(u'add_file', common.TEXT_SELECTED, common.INLINE_ICON_SIZE),
            u'text': u'Save version...',
            u'action': self.parent().saveRequested.emit
        }
        menu_set[u'save_increment'] = {
            u'icon': images.ImageCache.get_rsc_pixmap(u'add_file', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE),
            u'text': u'Save quick increment...',
            u'action': self.parent().incrementRequested.emit
        }
        return menu_set

    @contextmenu
    def add_export_alembic_menu(self, menu_set):
        objectset_pixmap = images.ImageCache.get_rsc_pixmap(
            u'set', None, common.INLINE_ICON_SIZE)

        outliner_set_members = outliner_sets()

        key = u'alembic_animation'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = u'Export timeline to alembic'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            menu_set[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(self.parent().alembicExportRequested.emit, k, v, False)
            }

        key = u'alembic_frame'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = u'Export current frame to alembic'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            menu_set[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(self.parent().alembicExportRequested.emit, k, v, True)
            }

        return menu_set

    @contextmenu
    def add_show_menu(self, menu_set):
        if not hasattr(self.parent(), 'clicked'):
            return menu_set
        menu_set[u'show'] = {
            u'icon': images.ImageCache.get_rsc_pixmap(u'icon_bw', None, common.INLINE_ICON_SIZE),
            u'text': u'Toggle {}'.format(common.PRODUCT),
            u'action': self.parent().clicked.emit
        }
        return menu_set

    @contextmenu
    def add_capture_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(u'capture', None, common.INLINE_ICON_SIZE)
        k = 'Capture viewport'
        menu_set[k] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(k)] = pixmap

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")

        size = lambda n: (int(int(width) * n), int(int(height) * n))

        for n in (1.0, 0.5, 0.25, 1.5, 2.0):
            menu_set[k][u'capture{}'.format(n)] = {
                u'text': u'Capture  |  @{}  |  {}x{}px'.format(n, *size(n)),
                u'action': functools.partial(capture_viewport, size=n)
            }
        return menu_set


class MayaBrowserButton(common_ui.ClickableIconButton):
    """Small widget to embed into the context to toggle the BrowserWidget's visibility.

    """
    saveRequested = QtCore.Signal()
    incrementRequested = QtCore.Signal()
    alembicExportRequested = QtCore.Signal(unicode, dict, bool)

    ContextMenu = BrowserButtonContextMenu

    def __init__(self, parent=None):
        super(MayaBrowserButton, self).__init__(
            u'icon_maya',
            (None, None),
            common.ASSET_ROW_HEIGHT,
            description=u'Click to toggle Bookmarks.\nRight-click to see addittional options.',
            parent=parent
        )
        self.setObjectName('MayaBrowserMainButton')
        self.setAttribute(QtCore.Qt.WA_NoBackground, False)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+Alt+Shift+S'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(self.saveRequested)
        #
        shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence(u'Ctrl+Alt+Shift+B'), self)
        shortcut.setAutoRepeat(False)
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(show)

        self.clicked.connect(show)

    def initialize(self):
        """Finds the built-in Toolbox menu and embeds a custom control-button
        for the Browser ``MayaBrowserButton``.

        """
        # Get the tool box and embed
        ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
        if ptr is not None:
            widget = wrapInstance(long(ptr), QtWidgets.QWidget)
            widget.layout().addWidget(self)
            self.setFixedWidth(widget.width())
            self.setFixedHeight(widget.width())
            self.adjustSize()
            self.update()
        else:
            s ='Could not find "ToolBox" - ``MayaBrowserButton`` not embedded.'
            common.Log.error(s)
            print s

        # Unlocking showing widget
        currentval = cmds.optionVar(q='workspacesLockDocking')
        cmds.optionVar(intValue=(u'workspacesLockDocking', False))
        cmds.evalDeferred(show)
        cmds.evalDeferred(functools.partial(
            cmds.optionVar, intValue=(u'workspacesLockDocking', currentval)))

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SECONDARY_BACKGROUND)
        painter.drawRoundRect(self.rect(), 6, 6)
        painter.end()

        super(MayaBrowserButton, self).paintEvent(event)

    def enterEvent(self, event):
        self.message.emit(self.statusTip)
        self.update()

    def leaveEvent(self, event):
        self.update()

    def contextMenuEvent(self, event):
        """Context menu event."""
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier
        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit(event.pos())
            return

        widget = self.ContextMenu(parent=self)
        common.set_custom_stylesheet(widget)
        widget.move(self.mapToGlobal(self.rect().bottomLeft()))
        widget.setFixedWidth(300)
        common.move_widget_to_available_geo(widget)
        widget.exec_()


class MayaBrowserWidgetContextMenu(BaseContextMenu):
    """The context menu for all Maya specific actions."""

    def __init__(self, index, parent=None):
        super(MayaBrowserWidgetContextMenu, self).__init__(
            index, parent=parent)

        self.add_apply_bookmark_settings_menu()
        self.add_separator()

        self.add_save_actions_menu()
        self.add_separator()

        if index.isValid():
            self.add_scenes_menu()
        self.add_separator()

        # Caches
        if index.isValid():
            self.add_alembic_actions_menu()

        self.add_separator()

        self.add_export_alembic_menu()

        self.add_separator()

        self.add_capture_menu()

    @contextmenu
    @contextmenu_browserwidget
    def add_apply_bookmark_settings_menu(self, menu_set, browserwidget=None):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'check', common.ADD, common.INLINE_ICON_SIZE)

        menu_set[u'apply_settings'] = {
            u'text': u'Apply scene settings...',
            u'icon': pixmap,
            u'action': browserwidget.apply_settings
        }

        return menu_set

    @contextmenu
    @contextmenu_browserwidget
    def add_save_actions_menu(self, menu_set, browserwidget=None):
        """Save actions.

        """
        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'add_file', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        pixmap2 = images.ImageCache.get_rsc_pixmap(
            u'add_file', common.TEXT_DISABLED, common.INLINE_ICON_SIZE)
        menu_set[u'new'] = {
            u'text': u'Save version...',
            u'icon': pixmap,
            u'action': lambda: browserwidget.save_scene(increment=False)
        }
        if common.get_sequence(scene.fileName()):
            menu_set[u'increment'] = {
                u'text': u'Save quick increment...',
                u'icon': pixmap2,
                u'action': lambda: browserwidget.save_scene(increment=True)
            }

        return menu_set

    @contextmenu
    @contextmenu_browserwidget
    def add_scenes_menu(self, menu_set, browserwidget=None):
        """Maya scene actions."""
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        if file_info.suffix().lower() not in (u'ma', u'mb'):
            return menu_set

        maya_pixmap = images.ImageCache.get_rsc_pixmap(
            u'maya', None, common.INLINE_ICON_SIZE)
        maya_reference_pixmap = images.ImageCache.get_rsc_pixmap(
            u'maya_reference', None, common.INLINE_ICON_SIZE)

        menu_set[u'open_scene'] = {
            u'text': u'Open  "{}"'.format(file_info.fileName()),
            u'icon': maya_pixmap,
            u'action': lambda: browserwidget.open_scene(file_info.filePath())
        }
        menu_set[u'import_local_scene'] = {
            u'text': u'Import  "{}"'.format(file_info.fileName()),
            u'icon': maya_pixmap,
            u'action': lambda: browserwidget.import_scene(file_info.filePath())
        }
        menu_set[u'import_scene'] = {
            u'text': u'Reference  "{}"'.format(file_info.fileName()),
            u'icon': maya_reference_pixmap,
            u'action': lambda: browserwidget.import_referenced_scene(file_info.filePath())
        }
        return menu_set

    @contextmenu
    @contextmenu_browserwidget
    def add_alembic_actions_menu(self, menu_set, browserwidget=None):
        """Actions associated with ``alembic`` cache operations."""
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        alembic_pixmap = images.ImageCache.get_rsc_pixmap(
            u'abc', None, common.INLINE_ICON_SIZE)
        maya_reference_pixmap = images.ImageCache.get_rsc_pixmap(
            u'maya_reference', None, common.INLINE_ICON_SIZE)

        menu_set[u'open_alembic'] = {
            u'text': u'Open  "{}"'.format(file_info.fileName()),
            u'icon': alembic_pixmap,
            u'action': lambda: browserwidget.open_alembic(file_info.filePath())
        }
        menu_set[u'import_local_alembic'] = {
            u'text': u'Import alembic "{}"'.format(file_info.fileName()),
            u'icon': alembic_pixmap,
            u'action': lambda: browserwidget.import_alembic(file_info.filePath())
        }
        menu_set[u'import_ref_alembic'] = {
            u'text': u'Import alembic as reference...',
            u'icon': maya_reference_pixmap,
            u'action': lambda: browserwidget.import_referenced_alembic(file_info.filePath())
        }
        return menu_set

    @contextmenu
    @contextmenu_browserwidget
    def add_export_alembic_menu(self, menu_set, browserwidget=None):
        objectset_pixmap = images.ImageCache.get_rsc_pixmap(
            u'set', None, common.INLINE_ICON_SIZE)

        outliner_set_members = outliner_sets()

        key = u'alembic_animation'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = u'Export timeline to alembic'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            menu_set[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(browserwidget.export_set_to_alembic, k, v, frame=False)
            }

        key = u'alembic_frame'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = u'Export current frame to alembic'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            menu_set[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(browserwidget.export_set_to_alembic, k, v, frame=True)
            }

        return menu_set

    @contextmenu
    @contextmenu_browserwidget
    def add_capture_menu(self, menu_set, browserwidget=None):
        pixmap = images.ImageCache.get_rsc_pixmap(u'capture', None, common.INLINE_ICON_SIZE)
        k = 'Capture viewport'
        menu_set[k] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(k)] = pixmap

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")

        size = lambda n: (int(int(width) * n), int(int(height) * n))

        for n in (1.0, 0.5, 0.25, 1.5, 2.0):
            menu_set[k][u'capture{}'.format(n)] = {
                u'text': u'Capture  |  @{}  |  {}x{}px'.format(n, *size(n)),
                u'action': functools.partial(capture_viewport, size=n)
            }
        return menu_set


class MayaBrowserWidget(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    """The main wrapper-widget to be used inside maya."""
    terminated = QtCore.Signal()

    def __init__(self, parent=None):
        global __instance__
        __instance__ = self
        super(MayaBrowserWidget, self).__init__(parent=parent)
        self._workspacecontrol = None
        self._callbacks = []  # Maya api callbacks
        self.browserwidget = None

        self.setWindowTitle(common.PRODUCT)

        self._create_UI()
        self.setFocusProxy(self.browserwidget.stackedwidget)

        self.workspace_timer = QtCore.QTimer(parent=self)
        self.workspace_timer.setSingleShot(False)
        self.workspace_timer.setInterval(5000)
        self.workspace_timer.timeout.connect(self.set_workspace)

        self.browserwidget.sizeHint = self.sizeHint

        self.browserwidget.initialized.connect(
            lambda: self.browserwidget.layout().setContentsMargins(0, 0, 0, 0))
        self.browserwidget.initialized.connect(self._connect_signals)
        self.browserwidget.initialized.connect(self.add_context_callbacks)
        self.browserwidget.initialized.connect(self.set_workspace)
        self.browserwidget.initialized.connect(self.workspace_timer.start)
        # self.browserwidget.active_monitor.activeAssetChanged.connect(
        #     self.active_changed)

        if maya_button is not None:
            maya_button.saveRequested.connect(self.save_scene)
            maya_button.incrementRequested.connect(
                lambda: self.save_scene(increment=True))

    @QtCore.Slot()
    def active_changed(self):
        """Slot called when an active asset changes."""
        if get_preference(u'disable_workspace_warnings') is True:
            return

        # We will get a warning when we change to a new bookmark and Bookmarks
        # unsets the current workspace. Whilst technically correct, it is
        # counterintuitive to be warned of a direct action just performed
        assets_model = self.browserwidget.assetswidget.model().sourceModel()
        if not assets_model.active_index().isValid():
            return

        workspace_info = QtCore.QFileInfo(
            cmds.workspace(q=True, expandName=True))

        common_ui.MessageBox(
            u'Workspace changed\n The new workspace is {}'.format(
                workspace_info.path()),
            u'If you didn\'t expect this message, it is possible your current project was changed by Bookmarks, perhaps in another instance of Maya.'
        ).open()

    def _add_shortcuts(self):
        """Global maya shortcut to do a save as"""

    def _create_UI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        common.set_custom_stylesheet(self)

        self.browserwidget = BrowserWidget(parent=self)
        self.layout().addWidget(self.browserwidget)
        self.browserwidget.terminated.connect(self.terminate)

    @QtCore.Slot()
    def terminate(self):
        @QtCore.Slot()
        def delete_module_import_cache():
            import gc
            import imp
            import bookmarks

            name = common.PRODUCT.lower()
            name_ext = '{}.'.format(name)

            # prevent changing iterable while iterating over it
            def compare(loaded):
                return (loaded == name) or loaded.startswith(name_ext)

            all_mods = tuple(sys.modules)
            sub_mods = filter(compare, all_mods)

            for pkg in sub_mods:
                p = pkg.split('.')
                p.pop(0)
                if not p:
                    continue

                # remove sub modules and packages from import cache
                # but only if submodules of bookmarks`
                try:
                    imp.find_module(p[0], bookmarks.__path__)
                    del sys.modules[pkg]
                except ImportError:
                    continue
                except RuntimeError as e:
                    print e
                except ValueError as e:
                    print e

            # del bookmarks
            # del sys.modules['bookmarks']
            gc.collect()

        @QtCore.Slot()
        def remove_button():
            """Removes the workspaceControl, and workspaceControlState objects."""
            ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
            if not ptr:
                widgets = QtWidgets.QApplication.instance().allWidgets()
                widget = [f for f in widgets if f.objectName() ==
                          u'MayaBrowserMainButton']
                if not widget:
                    return
                widget = widget[0]

            else:
                widget = wrapInstance(long(ptr), QtWidgets.QWidget)
                if not widget:
                    return

                from bookmarks.maya.widget import MayaBrowserButton
                widget = widget.findChild(MayaBrowserButton)

            widget.hide()
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
                u'# Bookmarks: UI deleted.\n')

        for widget in QtWidgets.QApplication.instance().allWidgets():
            if re.match(ur'MayaBrowserWidget.*WorkspaceControl', widget.objectName()):
                try:
                    remove_workspace_control(widget.objectName())
                except:
                    pass

        self.workspace_timer.stop()
        self.remove_context_callbacks()
        remove_button()

        self.hide()
        self.deleteLater()
        self.terminated.emit()

        delete_module_import_cache()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.SEPARATOR)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())
        painter.end()

    @QtCore.Slot()
    def save_warning(self, *args):
        """Will give the user a warning when their workspace does not match
        with their file save destination.

        """
        val = get_preference(u'disable_save_warnings')
        if val is True:
            return

        workspace_info = QtCore.QFileInfo(
            cmds.workspace(q=True, expandName=True))
        scene_file = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        if scene_file.baseName().lower() == u'untitled':
            return

        if workspace_info.path().lower() not in scene_file.filePath().lower():
            common_ui.MessageBox(
                u'Looks like you are saving "{}" outside the current project\nThe current project is "{}"'.format(
                    scene_file.fileName(),
                    workspace_info.path()),
                u'If you didn\'t expect this message, is it possible the project was changed by Bookmarks from another instance of Maya?'
            ).open()

    @QtCore.Slot()
    def unmark_active(self, *args):
        """Callback responsible for keeping the active-file in the list updated."""
        f = self.browserwidget.fileswidget
        if not f:
            return
        if not f.model().sourceModel().active_index().isValid():
            return
        f.deactivate(f.model().sourceModel().active_index())

    @QtCore.Slot()
    def update_active_item(self, *args):
        """Callback responsible for keeping the active-file in the list updated."""
        scene = common.get_sequence_endpath(
            cmds.file(query=True, expandName=True))
        f = self.browserwidget.fileswidget
        if not f:
            return

        if f.model().sourceModel().active_index().isValid():
            f.deactivate(f.model().sourceModel().active_index())

        for n in xrange(f.model().rowCount()):
            index = f.model().index(n, 0, parent=QtCore.QModelIndex())
            data = common.get_sequence_endpath(
                index.data(QtCore.Qt.StatusTipRole))

            if data.lower() == scene.lower():
                f.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                f.scrollTo(index)
                source_index = index.model().mapToSource(index)
                flags = source_index.flags() | common.MarkedAsActive
                source_index.model().setData(source_index, flags, role=common.FlagsRole)
                break

    def add_context_callbacks(self):
        """This method is called by the Maya plug-in when initializing."""

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterOpen, self.update_active_item)
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeOpen, self.unmark_active)
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeNew, self.unmark_active)
        self._callbacks.append(callback)

        # callback = OpenMaya.MSceneMessage.addCallback(
        #     OpenMaya.MSceneMessage.kBeforeSave, self.save_warning)
        # self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterSave, self.save_warning)
        self._callbacks.append(callback)

    def remove_context_callbacks(self):
        """This method is called by the Maya plug-in when unloading."""
        sys.stdout.write('# Bookmarks: Removing callbacks...\n')
        for callback in self._callbacks:
            res = OpenMaya.MMessage.removeCallback(callback)
            sys.stdout.write(u'# Callback status {}\n'.format(res))
        self._callbacks = []

    @QtCore.Slot()
    def _connect_signals(self):
        self.browserwidget.headerwidget.hide()

        bookmarkswidget = self.browserwidget.bookmarkswidget
        assetswidget = self.browserwidget.assetswidget
        fileswidget = self.browserwidget.fileswidget
        favouriteswidget = self.browserwidget.favouriteswidget

        # Asset/project
        assetswidget.model().sourceModel().activeChanged.connect(self.set_workspace)

        # Context menu
        bookmarkswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)
        assetswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)
        fileswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)
        favouriteswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)

        @QtCore.Slot()
        def execute(index):
            file_path = common.get_sequence_endpath(
                index.data(QtCore.Qt.StatusTipRole))
            file_info = QtCore.QFileInfo(file_path)
            if file_info.suffix().lower() in (u'ma', u'mb', u'abc'):
                self.open_scene(file_info.filePath())
                return
            common.execute(index)

        fileswidget.activated.connect(execute)
        favouriteswidget.activated.connect(execute)
        fileswidget.model().sourceModel().modelReset.connect(self.unmark_active)
        fileswidget.model().sourceModel().modelReset.connect(self.update_active_item)

    @QtCore.Slot(QtCore.QModelIndex)
    @QtCore.Slot(QtCore.QObject)
    def customFilesContextMenuEvent(self, index, parent):
        """Shows the custom context menu."""
        width = parent.viewport().geometry().width()
        width = (width * 0.5) if width > 400 else width
        width = width - common.INDICATOR_WIDTH

        widget = MayaBrowserWidgetContextMenu(index, parent=parent)
        if index.isValid():
            rect = parent.visualRect(index)
            widget.move(
                parent.viewport().mapToGlobal(rect.bottomLeft()).x(),
                parent.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
            )
        else:
            widget.move(QtGui.QCursor().pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH, widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    @QtCore.Slot()
    def set_workspace(self):
        """Slot responsible for updating the Maya workspace."""
        try:
            # When active sync is disabled we won't set workspaces
            if get_preference(u'disable_workspace_sync') is True:
                return
            index = self.browserwidget.assetswidget.model().sourceModel().active_index()
            if not index.isValid():
                return
            parent = index.data(common.ParentPathRole)
            if not parent:
                return
            if not all(parent):
                return
            file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
            if file_info.filePath().lower() == cmds.workspace(q=True, sn=True).lower():
                return
            cmds.workspace(file_info.filePath(), openWorkspace=True)
        except Exception as e:
            s = u'Could not set the workspace'
            common_ui.ErrorBox(
                s,
                u'This might have happened because {} is not a valid Maya Workspace?'.format(
                    file_info.fileName())
            ).open()
            common.Log.error(s)
            raise

    @QtCore.Slot()
    def apply_settings(self):
        """Apply the Bookmark Properties to the current scene.

        """
        import bookmarks.bookmark_db as bookmark_db

        def set_start_frame(frame):
            frame = round(frame, 0)
            currentFrame = round(cmds.currentTime(query=True))

            cmds.playbackOptions(animationStartTime=int(frame))
            cmds.playbackOptions(minTime=int(frame))
            cmds.setAttr('defaultRenderGlobals.startFrame', int(frame))
            if currentFrame < frame:
                cmds.currentTime(frame, edit=True)
            else:
                cmds.currentTime(currentFrame, edit=True)


        def set_end_frame(frame):
            frame = round(frame, 0)
            currentFrame = round(cmds.currentTime(query=True))

            cmds.playbackOptions(animationEndTime=int(frame))
            cmds.playbackOptions(maxTime=int(frame))
            cmds.setAttr('defaultRenderGlobals.endFrame', int(frame))

            if currentFrame > frame:
                cmds.currentTime(frame, edit=True)
            else:
                cmds.currentTime(currentFrame, edit=True)


        def _set_framerate(fps):
            animationStartTime = cmds.playbackOptions(query=True, animationStartTime=True)
            minTime = cmds.playbackOptions(query=True, minTime=True)
            animationEndTime = cmds.playbackOptions(query=True, animationEndTime=True)
            maxTime = cmds.playbackOptions(query=True, maxTime=True)
            set_framerate(fps)
            cmds.playbackOptions(animationStartTime=animationStartTime)
            cmds.playbackOptions(minTime=minTime)
            cmds.playbackOptions(animationEndTime=animationEndTime)
            cmds.playbackOptions(maxTime=maxTime)


        try:
            widget = self.browserwidget.stackedwidget.widget(0)
            model = widget.model().sourceModel()
            if not model.active_index().isValid():
                return

            t = u'properties'
            v = {}
            db = None
            n = 0

            while db is None:
                db = bookmark_db.get_db(model.active_index())
                if db is None:
                    n += 1
                    time.sleep(0.1)
                if n > 10:
                    break

            if not db:
                s = u'Could not get the Bookmark Database'
                common.Log.error(s)
                raise RuntimeError(s)

            with db.transactions():
                for _k in bookmark_db.KEYS[t]:
                    v[_k] = db.value(0, _k, table=t)


            if (v['width'] and v['height']):
                cmds.setAttr('defaultResolution.width', v['width'])
                cmds.setAttr('defaultResolution.height', v['height'])
            if v['framerate']:
                _set_framerate(v['framerate'])
            if v['startframe']:
                set_start_frame(v['startframe'])
            if v['duration']:
                set_end_frame(v['startframe'] + v['duration'])

            cmds.setAttr('defaultRenderGlobals.extensionPadding', 4)
            cmds.setAttr('defaultRenderGlobals.animation', 1)
            cmds.setAttr('defaultRenderGlobals.putFrameBeforeExt', 1)
            cmds.setAttr('defaultRenderGlobals.periodInExt', 2)
            cmds.setAttr('defaultRenderGlobals.useFrameExt', 0)
            cmds.setAttr('defaultRenderGlobals.outFormatControl', 0)
            cmds.setAttr('defaultRenderGlobals.imageFormat', 8)


            info = u'{w}{h}{fps}{pre}{start}{duration}'.format(
                w=u'{}'.format(int(v['width'])) if (v['width'] and v['height']) else u'',
                h=u'x{}px'.format(int(v['height'])) if (v['width'] and v['height']) else u'',
                fps=u'  |  {}fps'.format(v['framerate']) if v['framerate'] else u'',
                pre=u'  |  {}'.format(v['prefix']) if v['prefix'] else u'',
                start=u'  |  {}'.format(int(v['startframe'])) if v['startframe'] else u'',
                duration=u'-{} ({} frames)'.format(
                    int(v['startframe']) + int(v['duration']),
                    int(v['duration']) if v['duration'] else u'') if v['duration'] else u''
            )

            common_ui.OkBox(
                u'Successfully applied the default scene settings:',
                info,
                parent=self
            ).open()

        except Exception as e:
            s = u'Could apply properties'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise



    @QtCore.Slot()
    def save_scene(self, increment=False, modal=True):
        """Initializes Bookmarks' custom file saver dialog.

        Then increment=True, Bookmarks will try to increment any version number
        +1 before saving the file.

        The saving is done using `AddFileWidget`, a modal QDialog.

        Returns:
            unicode: Path to the saved scene file.

        """
        ext = u'ma'
        file = cmds.file(query=True, expandName=True) if increment else None
        if file:
            if not file.lower().endswith(u'.ma'):
                file = file + '.ma'

        widget = addfilewidget.AddFileWidget(ext, file=file)
        if modal:
            if widget.exec_() == QtWidgets.QDialog.Rejected:
                return
        if not modal and not increment:
            raise RuntimeError('Flags `increment` and `modal` together is undefined behaviour')
        if increment and modal:
            widget.open()

        file_path = widget.filePath()
        if not file_path:
            raise RuntimeError('Could not retrieve the destination path.')

        file_info = QtCore.QFileInfo(file_path)

        # Last-ditch check to make sure we're not overwriting anything
        if file_info.exists():
            s = u'Unable to save file: {} already exists.'.format(file_path)
            common.ErrorBox(u'Error.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        try:
            cmds.file(rename=file_path)
            cmds.file(force=True, save=True, type=u'mayaAscii')
            fileswidget = self.browserwidget.stackedwidget.widget(2)
            fileswidget.new_file_added(widget.data_key(), file_path)
            return file_path

        except Exception as e:
            s = u'Could not save the scene.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise

    def open_scene(self, path):
        """Maya Command: Opens the given path in Maya using ``cmds.file``.

        Returns:
            unicode: The name of the input scene if the load was successfull.

        Raises:
            RuntimeError: When and invalid scene file is passed.


        """
        p = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(p)

        if file_info.suffix().lower() not in (u'ma', u'mb', u'abc'):
            s = u'{} is not a valid scene.'.format(p)
            common_ui.ErrorBox(u'Error.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        if not file_info.exists():
            s = u'{} does not exist.'.format(p)
            common_ui.ErrorBox(u'Could not import scene', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        try:
            if self.is_scene_modified() == QtWidgets.QMessageBox.Cancel:
                return
            cmds.file(file_info.filePath(), open=True, force=True)

            common.Log.success(
                u'# Bookmarks: Scene opened {}\n'.format(file_info.filePath()))
            common_ui.OkBox(
                u'Success.',
                u'{} opened successfully.'.format(file_info.filePath())
            ).open()
            return file_info.filePath()
        except Exception as e:
            s = u'Could not open the scene.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise

    def import_scene(self, path):
        """Imports the given scene locally."""
        p = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(p)

        if file_info.suffix().lower() not in (u'ma', u'mb'):
            s = u'{} is not a valid scene.'.format(p)
            common_ui.ErrorBox(u'Error.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        if not file_info.exists():
            s = u'{} does not exist.'.format(p)
            common_ui.ErrorBox(u'Could not import scene', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        try:
            if self.is_scene_modified() == QtWidgets.QMessageBox.Cancel:
                return
            match = common.get_sequence(file_info.fileName())
            ns = match.group(1) if match else file_info.baseName()
            ns = u'{}#'.format(ns)
            cmds.file(
                file_info.filePath(),
                i=True,
                ns=ns
            )
            common_ui.OkBox(
                u'Done.',
                u'{} imported successfully.'.format(file_info.filePath())
            ).open()
            return file_info.filePath()

        except Exception as e:
            s = u'Could not open the scene.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise

    def import_referenced_scene(self, path):
        """Imports the given scene as a reference."""

        def get_alphabet(basename):
            """Checks the scene against the already used suffixes and returs a modified alphabet"""
            alphabet = unicode(string.ascii_uppercase)
            transforms = cmds.ls(transforms=True)
            for s in transforms:
                if basename not in s:
                    continue
                if not cmds.attributeQuery('instance_suffix', node=s, exists=True):
                    continue
                suffix = cmds.getAttr('{}.instance_suffix'.format(s))
                alphabet = alphabet.replace(string.ascii_uppercase[suffix], '')
            return alphabet

        def add_attribute(rfn, suffix):
            id = string.ascii_uppercase.index(suffix)
            nodes = cmds.referenceQuery(rfn, nodes=True)
            for node in nodes:

                # Conflict of duplicate name would prefent import... this is a hackish, yikes, workaround!
                _node = cmds.ls(node, long=True)[0]
                if cmds.nodeType(_node) != 'transform':
                    continue
                if cmds.listRelatives(_node, parent=True) is None:
                    if cmds.attributeQuery('instance_suffix', node=node, exists=True):
                        continue
                    cmds.addAttr(_node, ln='instance_suffix', at='enum',
                                 en=u':'.join(string.ascii_uppercase))
                    cmds.setAttr('{}.instance_suffix'.format(_node), id)

        p = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(p)
        if file_info.suffix().lower() not in (u'ma', u'mb'):
            s = u'{} is not a valid scene.'.format(p)
            common_ui.ErrorBox(u'Error.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        if not file_info.exists():
            s = u'{} does not exist.'.format(p)
            common_ui.ErrorBox(u'Could not reference scene', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        try:
            match = common.get_sequence(file_info.fileName())
            basename = match.group(1) if match else file_info.baseName()
            basename = re.sub(ur'_v$', u'', basename, flags=re.IGNORECASE)

            alphabet = get_alphabet(basename)
            if not alphabet:
                return

            w = QtWidgets.QInputDialog(parent=self)
            w.setWindowTitle(u'Assign suffix')
            w.setLabelText(
                u'Select the suffix of this referece.\n\nSuffixes are unique and help differentiate animation and cache data\nwhen the same asset is referenced mutiple times.')
            w.setComboBoxItems(alphabet)
            w.setCancelButtonText(u'Cancel')
            w.setOkButtonText(u'Import reference')
            res = w.exec_()
            if not res:
                return
            suffix = w.textValue()

            id = u'{}'.format(uuid.uuid1()).replace(u'-', u'_')
            # This should always be a unique name in the maya scene
            ns = u'{}_{}'.format(basename, suffix)
            rfn = u'{}_RN_{}'.format(ns, id)

            cmds.file(
                file_info.filePath(),
                reference=True,
                ns=ns,
                rfn=rfn,
            )
            add_attribute(rfn, suffix)

            cmds.lockNode(rfn, lock=False)
            rfn = cmds.rename(rfn, u'{}_RN'.format(ns))
            cmds.lockNode(rfn, lock=True)

            common_ui.OkBox(
                u'Success.',
                u'{} referenced successfully.'.format(file_info.filePath())
            ).open()

            return file_info.filePath()
        except Exception as e:
            s = u'Could not reference the scene.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise

    def open_alembic(self, path):
        """Opens the given scene."""
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)
            cmds.loadPlugin("AbcImport.mll", quiet=True)

        p = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(p)
        if file_info.suffix().lower() not in (u'abc',):
            s = u'{} is not a valid alembic.'.format(p)
            common_ui.ErrorBox(u'Error.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        if not file_info.exists():
            s = u'{} does not exist.'.format(p)
            common_ui.ErrorBox(u'Could not open alembic.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        try:
            if self.is_scene_modified() == QtWidgets.QMessageBox.Cancel:
                return
            cmds.AbcImport(file_info.filePath(), mode=u'open')
            common_ui.OkBox(
                u'Success.',
                u'{} opened successfully.'.format(file_info.filePath())
            ).open()
            return file_info.filePath()
        except Exception as e:
            s = u'Could not reference the scene.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise

    def import_alembic(self, path):
        """Imports the given scene locally."""
        if not cmds.pluginInfo(u'AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin('AbcExport.mll', quiet=True)
            cmds.loadPlugin('AbcImport.mll', quiet=True)

        p = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(p)
        if file_info.suffix().lower() not in (u'abc',):
            s = u'{} is not a valid alembic.'.format(p)
            common_ui.ErrorBox(u'Error.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        if not file_info.exists():
            s = u'{} does not exist.'.format(p)
            common_ui.ErrorBox(u'Could not import alembic.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        try:
            seq = common.get_sequence(file_info.fileName())
            if seq:
                prefix, _, _, _ = seq.groups()
                prefix = re.sub(ur'_v$', '', prefix).rstrip(u'_')
            else:
                prefix = file_info.baseName().rstrip(u'_')

            # Create namespace
            n = 1
            ns = u'abc_{}{}'.format(prefix, n)
            while True:
                if cmds.namespace(exists=ns):
                    n += 1
                    ns = u'abc_{}{}'.format(prefix, n)
                    continue
                break
            cmds.namespace(add=ns)
            root_node = u'{}:{}'.format(ns, prefix)
            cmds.createNode(u'transform', name=root_node)

            cmds.AbcImport(
                p,
                mode='import',
                reparent=root_node,
                filterObjects=u'.*Shape.*'
            )

            for s in cmds.listRelatives(root_node, children=True):
                cmds.rename(s, u'{}:{}'.format(ns, s))

            common_ui.OkBox(
                u'Success.',
                u'{} imported successfully.'.format(file_info.filePath())
            ).open()
            return file_info.filePath()
        except Exception as e:
            s = u'Could not import alembic.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise

    def import_referenced_alembic(self, path):
        """Imports the given scene as a reference."""
        if not cmds.pluginInfo(u'AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin('AbcExport.mll', quiet=True)
            cmds.loadPlugin('AbcImport.mll', quiet=True)

        p = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(p)
        if file_info.suffix().lower() not in (u'abc',):
            s = u'{} is not a valid alembic.'.format(p)
            common_ui.ErrorBox(u'Error.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        if not file_info.exists():
            s = u'{} does not exist.'.format(p)
            common_ui.ErrorBox(u'Could not reference alembic.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        try:
            seq = common.get_sequence(file_info.fileName())
            if seq:
                prefix, _, _, _ = seq.groups()
                prefix = re.sub(ur'_v$', '', prefix).rstrip(u'_')
            else:
                prefix = file_info.baseName().rstrip(u'_')

            # Create namespace
            n = 1
            ns = u'abc_{}{}'.format(prefix, n)
            while True:
                if cmds.namespace(exists=ns):
                    n += 1
                    ns = u'abc_{}{}'.format(prefix, n)
                    continue
                break

            # The namespace will be created by the cmds.file() command
            rfn = u'{}_RN'.format(ns)

            cmds.file(
                file_info.filePath(),
                reference=True,
                ns=ns,
                rfn=rfn,
            )
            members = cmds.namespaceInfo(ns, listNamespace=True, fullName=True)
            root_node = u'{}:{}'.format(ns, prefix)
            cmds.createNode(u'transform', name=root_node)
            for member in members:
                if cmds.objectType(member) != u'transform':
                    continue
                cmds.parent(member, root_node)

            common_ui.OkBox(
                u'Success.',
                u'{} referenced successfully.'.format(file_info.filePath())
            ).open()
            return file_info.filePath()
        except Exception as e:
            s = u'Could not reference alembic.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise

    @QtCore.Slot(unicode)
    @QtCore.Slot(dict)
    @QtCore.Slot(bool)
    def export_set_to_alembic(self, set_name, set_members, frame=False):
        """Main method to initiate an alembic export using Browser's
        saver to generate the filename.

        Args:
            key (str):   The name of the object set to export.
            value (tuple): A list of object names inside the set.

        """
        if not cmds.pluginInfo('AbcExport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)
            cmds.loadPlugin("AbcImport.mll", quiet=True)

        ext = u'abc'

        # We want to handle the exact name of the file
        # We'll remove the namespace, strip underscores
        set_name = set_name.replace(u':', u'_').strip(u'_')
        set_name = re.sub(ur'[0-9]*$', u'', set_name)

        template = get_preference(u'alembic_export_path')
        template = template if template else ALEMBIC_EXPORT_PATH
        file_path = unicode(template).format(
            workspace=cmds.workspace(q=True, sn=True),
            exports=common.ExportsFolder,
            set=set_name
        )

        # Let's make sure destination folder exists
        file_info = QtCore.QFileInfo(file_path)
        _dir = file_info.dir()
        if not _dir.exists():
            _dir.mkpath(u'.')

        widget = addfilewidget.AddFileWidget(ext, file=file_path)
        fileswidget = self.browserwidget.stackedwidget.widget(2)

        if widget.exec_() == QtWidgets.QDialog.Rejected:
            return

        file_path = widget.filePath()
        file_info = QtCore.QFileInfo(file_path)

        # Last-ditch check to make sure we're not overwriting anything...
        if file_info.exists():
            s = u'Unable to save alembic: {} already exists.'.format(file_path)
            common_ui.ErrorBox('Error.', s).open()
            common.Log.error(s)
            raise RuntimeError(s)

        if frame:
            start = cmds.currentTime(query=True)
            end = cmds.currentTime(query=True)
        else:
            start = cmds.playbackOptions(query=True, animationStartTime=True)
            end = cmds.playbackOptions(query=True, animationEndTime=True)

        state = cmds.ogs(pause=True, query=True)
        if not state:
            cmds.ogs(pause=True)

        try:
            export_alembic(
                file_info.filePath(),
                set_members,
                start,
                end
            )
            fileswidget.new_file_added(widget.data_key(), file_path)
            return file_path
        except Exception as e:
            s = u'Could not export alembic.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            common.Log.error(s)
            raise
        finally:
            if not state:
                cmds.ogs(pause=True)

    def is_scene_modified(self):
        """If the current scene was modified since the last save, the user will be
        prompted to save the scene.

        """
        if not cmds.file(q=True, modified=True):
            return

        mbox = QtWidgets.QMessageBox()
        mbox.setText(
            u'Current scene has unsaved changes.'
        )
        mbox.setInformativeText(u'Do you want to save before continuing?')
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Save
            | QtWidgets.QMessageBox.No
            | QtWidgets.QMessageBox.Cancel
        )
        mbox.setDefaultButton(QtWidgets.QMessageBox.Save)
        result = mbox.exec_()

        if result == QtWidgets.QMessageBox.Cancel:
            return result
        elif result == QtWidgets.QMessageBox.Save:
            cmds.SaveScene()
            return result

        return result

    def show(self, dockable=True):
        """Initializes the Maya workspace control on show."""
        kwargs = {
            u'dockable': True,
            u'allowedArea': None,
            u'retain': True,
            u'width': 240,
            u'height': 360
        }
        super(MayaBrowserWidget, self).show(**kwargs)

    def sizeHint(self):
        return QtCore.QSize(240, 360)
