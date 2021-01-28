# -*- coding: utf-8 -*-
"""This module defines Bookmarks's ``MayaMainWidget``, a dockable `mayaMixin`
widget that wraps MainWidget.

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
import gc
import imp

import shiboken2
from PySide2 import QtWidgets, QtGui, QtCore

import maya.app.general.mayaMixin as mayaMixin
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as OpenMaya
import maya.cmds as cmds

from .. import log
from .. import common
from .. import common_ui
from .. import settings
from .. import images
from .. import contextmenu
from .. import main
from .. import addfile
from .. import bookmark_db
from .. import rv
from .. import actions
from .. import __path__ as package_path



object_name = 'm{}MainButton'.format(__name__.split('.')[0])


maya_button = None
"""The bookmarks shortcut icon button. Set by the ``mBookmarks.py`` when the plugin is initializing."""


_instance = None
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
    u'29.97fps': 29.976,
    u'29.97df': 29.976,
    u'47.952fps': 47.952,
    u'59.94fps': 59.94,
    u'44100fps': 44100.0,
    u'48000fps': 48000.0,
}

SUFFIX_LABEL = u'Select a suffix for this import.\n\n\
Suffixes are always unique and help differentiate imports when the same file \
is imported mutiple times.'


def _get_available_suffixes(basename):
    """Checks for already used suffixes in the current scene and returns a list
    of available ones.

    """
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


def _add_suffix_attribute(rfn, suffix, reference=True):
    """Adds a custom attribute to the imported scene.

    """
    id = string.ascii_uppercase.index(suffix)

    if reference:
        nodes = cmds.referenceQuery(rfn, nodes=True)
    else:
        nodes = cmds.namespaceInfo(rfn, listNamespace=True)

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


def is_scene_modified():
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


def open_scene(path):
    """Opens the given path using ``cmds.file``.

    Returns:
        unicode: The name of the input scene if the load was successfull.

    Raises:
        RuntimeError: When and invalid scene file is passed.

    """
    p = common.get_sequence_endpath(path)
    file_info = QtCore.QFileInfo(p)

    _s = file_info.suffix().lower()
    if _s not in (u'ma', u'mb', u'abc'):
        s = u'{} is not a valid scene.'.format(p)
        common_ui.ErrorBox(u'Error.', s).open()
        log.error(s)
        raise RuntimeError(s)

    if _s == 'abc':
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcImport.mll", quiet=True)
        if not cmds.pluginInfo("AbcExport.mll", loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)

    if not file_info.exists():
        s = u'{} does not exist.'.format(p)
        common_ui.ErrorBox(u'Could not import scene', s).open()
        log.error(s)
        raise RuntimeError(s)

    try:
        if is_scene_modified() == QtWidgets.QMessageBox.Cancel:
            return
        cmds.file(file_info.filePath(), open=True, force=True)

        s = u'Scene opened {}\n'.format(file_info.filePath())
        log.success(s)
        return file_info.filePath()
    except Exception as e:
        s = u'Could not open the scene.'
        common_ui.ErrorBox(s, u'{}'.format(e)).open()
        log.error(s)
        raise


def import_scene(path, reference=False):
    """Imports a Maya or alembic file to the current Maya scene.

    Args:
        path (unicode): Path to a Maya scene file.
        reference (bool): When `true` the import will be a reference.

    """
    p = common.get_sequence_endpath(path)
    file_info = QtCore.QFileInfo(p)
    _s = file_info.suffix().lower()
    if _s not in (u'ma', u'mb', u'abc'):
        s = u'{} is not a valid scene.'.format(p)
        common_ui.ErrorBox(u'Error.', s).open()
        log.error(s)
        raise RuntimeError(s)

    # Load the alembic plugin
    if _s == 'abc':
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcImport.mll", quiet=True)
        if not cmds.pluginInfo("AbcExport.mll", loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)

    if not file_info.exists():
        s = u'{} does not exist.'.format(p)
        common_ui.ErrorBox(u'Could not reference scene', s).open()
        log.error(s)
        raise RuntimeError(s)

    if cmds.file(q=True, sn=True).lower() == file_info.filePath().lower() and reference:
        raise RuntimeError('Can\'t reference self.')

    try:
        match = common.get_sequence(file_info.fileName())
        basename = match.group(1) if match else file_info.baseName()
        basename = re.sub(ur'_v$', u'', basename, flags=re.IGNORECASE)

        alphabet = _get_available_suffixes(basename)
        if not alphabet:  # no more suffixes to assign
            return None

        w = QtWidgets.QInputDialog()
        w.setWindowTitle(u'Assign suffix')
        w.setLabelText(SUFFIX_LABEL)
        w.setComboBoxItems(alphabet)
        w.setCancelButtonText(u'Cancel')
        w.setOkButtonText(u'Import')
        res = w.exec_()
        if not res:
            return None
        suffix = w.textValue()

        id = u'{}'.format(uuid.uuid1()).replace(u'-', u'_')
        # This should always be a unique name in the maya scene
        ns = u'{}_{}'.format(basename, suffix)
        rfn = u'{}_RN_{}'.format(ns, id)

        if reference:
            cmds.file(
                file_info.filePath(),
                reference=True,
                ns=ns,
                rfn=rfn,
            )
            _add_suffix_attribute(rfn, suffix, reference=reference)

            # The reference node is locked by default
            cmds.lockNode(rfn, lock=False)
            rfn = cmds.rename(rfn, u'{}_RN'.format(ns))
            cmds.lockNode(rfn, lock=True)
        else:
            cmds.file(
                file_info.filePath(),
                i=True,
                ns=ns
            )
            _add_suffix_attribute(ns, suffix, reference=reference)

        s = u'{} was imported.'.format(file_info.filePath())
        log.success(s)
        return file_info.filePath()
    except Exception as e:
        s = u'Could not reference the scene.'
        common_ui.ErrorBox(s, u'{}'.format(e)).open()
        log.error(s)
        raise


def find_project_folder(key):
    """Return the relative path of a project folder.

    Args:
        key (unicode): The name of a Maya project folder name, eg. 'sourceImages'.

    Return:
        unicode: The name of the folder that corresponds with `key`.

    """
    if not key:
        raise ValueError('Key must be specified.')

    _file_rules = cmds.workspace(
        fr=True,
        query=True,
    )

    file_rules = {}
    for n, _ in enumerate(_file_rules):
        m = n % 2
        k = _file_rules[n - m].lower()
        if m == 0:
            file_rules[k] = None
        if m == 1:
            file_rules[k] = _file_rules[n]

    key = key.lower()
    if key in file_rules:
        return file_rules[key]
    return key


def set_framerate(fps):
    for k, v in MAYA_FPS.iteritems():
        if fps == v:
            cmds.currentUnit(time=k)
            return k
    raise ValueError(u'Invalid fps provided')


def get_framerate():
    return MAYA_FPS[cmds.currentUnit(query=True, time=True)]


def get_preference(k):
    return settings.local_settings.value(
        settings.SettingsSection,
        k
    )


def instance():
    return _instance


@QtCore.Slot()
def show():
    """Main function to show ``MayaMainWidget`` inside Maya as a dockable
    widget.

    The function will create ``MayaMainWidget`` if it doesn't yet exist and
    dock it to the _AttributeEditor_. If it exists it will get the existing
    instance and show it if not currently visible, hide it if visible.

    Usage

        Run the following python code inside maya:

        .. code-block:: python

            import bookmarks.maya.widget as widget
            widget.show()

    """
    app = QtWidgets.QApplication.instance()

    # We will check if there's already a _MayaMainWidget_ instance
    for widget in app.allWidgets():
        # Skipping workspaceControls objects, just in case there's a name conflict
        # between what the parent().objectName() and this method yields
        if re.match(ur'{}.*WorkspaceControl'.format(common.PRODUCT), widget.objectName()):
            continue

        match = re.match(ur'{}.*'.format(common.PRODUCT), widget.objectName())
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

    # Initializing MayaMainWidget
    try:
        widget = MayaMainWidget()
        common.set_custom_stylesheet(widget)
        widget.show()

        sys.stdout.write(
            u'# {}: Initialized successfully\n'.format(common.PRODUCT))

        # We will defer the execution, otherwise the widget does not dock properly
        for widget in app.allWidgets():
            match = re.match(
                ur'{}.*WorkspaceControl'.format(common.PRODUCT), widget.objectName())
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
        log.error(u'Could not open {} window.'.format(common.PRODUCT))
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
    """Main alembic export definition.

    Only shapes, normals and uvs are exported by this implementation. The list
    of shapes contained in the `outliner_set` will be rebuilt in the root of
    the scene to avoid parenting issues.

    Args:
        destination_path (unicode): Path to the output file.
        outliner_set (tuple): A list of transforms contained in a geometry set.

    """
    # ======================================================
    # ERROR CHECKING
    # Check destination before proceeding
    if not isinstance(outliner_set, (tuple, list)):
        raise TypeError(
            u'Expected <type \'list\'>, got {}'.format(type(outliner_set)))

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
        log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    if not _destination_dir_info.isReadable():
        s = u'Unable to save the alembic file, {} is not readable.'.format(
            _destination_dir_info.filePath())
        common_ui.ErrorBox(
            u'Alembic export failed.',
            s
        ).open()
        log.error('Unable to save the alembic file, {} does not exists.')
        raise OSError(s)

    if not _destination_dir_info.isWritable():
        s = u'Unable to save the alembic file, {} is not writable.'.format(
            _destination_dir_info.filePath())
        common_ui.ErrorBox(
            u'Alembic export failed.',
            s
        ).open()
        log.error('Unable to save the alembic file, {} does not exists.')
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
                # This was suggested on a forum - listing the relatives for a
                # an object without a unique name should raise a ValueError
                cmds.listRelatives(basename)
            except ValueError as err:
                s = u'"{shape}" does not have a unique name. This is not usually allowed for alembic exports and might cause the export to fail.\nError: {err}'.format(
                    shape=shape, err=err)
                log.error(s)

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
    # the meshes. We will delete this namespace, and it's contents after the export
    if cmds.namespace(exists=u'mayaExport'):
        cmds.namespace(removeNamespace=u'mayaExport',
                       deleteNamespaceContent=True)
    ns = cmds.namespace(add=u'mayaExport')

    world_transforms = []

    try:
        # For meshes, we will create an empty mesh node and connect the outMesh and
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

        # Our custom progress callback
        perframecallback = u'"import {}.maya.widget as w;w.report_export_progress({}, #FRAME#, {}, {})"'.format(
            common.PRODUCT.lower(), startframe, endframe, time.time())

        # Let's build the export command
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
        s = u'# jobArg: `{}`'.format(jobArg)

        cmds.AbcExport(jobArg=jobArg)
        log.success(s)

    except Exception as err:
        common_ui.ErrorBox(
            u'An error occured exporting Alembic cache',
            u'{}'.format(err)
        ).open()
        log.error(u'Could not open the plugin window.')
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
    imagedir = find_project_folder(u'images')
    capturedir = imagedir + u'/captures' if imagedir else u'render/captures'

    workspace = cmds.workspace(q=True, rootDirectory=True).rstrip(u'/')
    scene_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))
    dest = u'{workspace}/{capturedir}/{scene}/{scene}'.format(
        workspace=workspace,
        capturedir=capturedir,
        scene=scene_info.baseName()
    )
    return capturedir, workspace, dest


@QtCore.Slot()
def capture_viewport(size=1.0):
    """Saves a versioned capture to the ``capture_folder`` defined in the preferences.

    The script will output to the an image sequence and if FFmpeg is present converts it to a h264 movie file.
    It will also try to create a ``latest`` folder with a copy of the last exported image sequence.

    Usage:

        .. code-block:: python

        MayaMainWidget.capture_viewport()


    """
    from . import mCapture

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

    picker = PanelPicker()
    picker.exec_()
    panel = picker.panel
    if not panel:
        return

    # Not all panels are modelEditors
    if panel is None or cmds.objectTypeUI(panel) != u'modelEditor':
        s = u'Activate a viewport before starting a capture.'
        common_ui.MessageBox(
            u'The active window is not a viewport.',
            s
        ).open()
        log.error(s)
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
            panel_widget = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)
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
                panel_widget = shiboken2.wrapInstance(
                    long(ptr), QtWidgets.QWidget)
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

    val = get_preference(settings.PushCaptureToRVKey)
    val = val if val is not None else False
    if not val:
        rv.push(rv_seq_path)

    val = get_preference(settings.RevealCaptureKey)
    val = val if val is not None else False
    if not val:
        actions.reveal(rv_seq_path)

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
            log.error(s)
            raise OSError(s)

    if not QtCore.QFileInfo(latest_dir).isWritable():
        s = 'Publish folder is not writable.'
        common_ui.ErrorBox(
            u'Could not publish the capture',
            s
        ).open()
        log.error(s)
        raise OSError(s)

    import _scandir as _scandir
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


class PanelPicker(QtWidgets.QDialog):
    """Modal dialog used to select a visible modelPanel in Maya.

    """

    def __init__(self, parent=None):
        super(PanelPicker, self).__init__(parent=parent)

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_in = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(0.5)
        self.fade_in.setDuration(500)
        self.fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self._mouse_pos = None
        self._click_pos = None
        self._offset_pos = None

        self._capture_rect = QtCore.QRect()

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.setMouseTracking(True)
        self.installEventFilter(self)

        self.panels = {}
        self.panel = None

        panels = cmds.lsUI(panels=True)
        if not panels:
            return

        for panel in panels:
            if not cmds.modelPanel(panel, exists=True):
                continue
            ptr = OpenMayaUI.MQtUtil.findControl(panel)
            if not ptr:
                continue
            widget = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)
            if not widget:
                continue
            if not widget.isVisible():
                continue
            self.panels[panel] = widget

    def _fit_screen_geometry(self):
        """Compute the union of all screen geometries, and resize to fit.

        """
        app = QtWidgets.QApplication.instance()
        geo = app.primaryScreen().geometry()
        x = []
        y = []
        w = 0
        h = 0

        try:
            for screen in app.screens():
                g = screen.geometry()
                x.append(g.topLeft().x())
                y.append(g.topLeft().y())
                w += g.width()
                h += g.height()
            topleft = QtCore.QPoint(
                min(x),
                min(y)
            )
            size = QtCore.QSize(w - min(x), h - min(y))
            geo = QtCore.QRect(topleft, size)
        except:
            pass

        self.setGeometry(geo)

    def paintEvent(self, event):
        """Paint the capture window."""
        # Convert click and current mouse positions to local space.
        mouse_pos = self.mapFromGlobal(common.cursor.pos())
        painter = QtGui.QPainter()
        painter.begin(self)

        # Draw background. Aside from aesthetics, this makes the full
        # tool region accept mouse events.
        painter.setBrush(QtGui.QColor(0, 0, 0, 255))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())

        for panel in self.panels.values():
            _mouse_pos = panel.mapFromGlobal(common.cursor.pos())

            if not panel.rect().contains(_mouse_pos):
                self.setCursor(QtCore.Qt.ArrowCursor)
                continue

            self.setCursor(QtCore.Qt.PointingHandCursor)
            topleft = panel.mapToGlobal(panel.rect().topLeft())
            topleft = self.mapFromGlobal(topleft)
            bottomright = panel.mapToGlobal(panel.rect().bottomRight())
            bottomright = self.mapFromGlobal(bottomright)

            capture_rect = QtCore.QRect(topleft, bottomright)
            pen = QtGui.QPen(common.ADD)
            pen.setWidth(common.ROW_SEPARATOR() * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(capture_rect)

            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(common.ADD)
            painter.setOpacity(0.3)
            painter.drawRect(capture_rect)

        painter.end()

    def keyPressEvent(self, event):
        """Cancel the capture on keypress."""
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()

    def mouseReleaseEvent(self, event):
        """Finalise the caputre"""
        if not isinstance(event, QtGui.QMouseEvent):
            return

        for panel, widget in self.panels.iteritems():
            mouse_pos = widget.mapFromGlobal(common.cursor.pos())
            if widget.rect().contains(mouse_pos):
                self.panel = panel
                self.done(QtWidgets.QDialog.Accepted)
                self.panel = panel
                return

        self.done(QtWidgets.QDialog.Rejected)

    def mouseMoveEvent(self, event):
        """Constrain and resize the capture window."""
        self.update()

    def showEvent(self, event):
        self._fit_screen_geometry()
        self.fade_in.start()


class BrowserButtonContextMenu(contextmenu.BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(BrowserButtonContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)

    def setup(self):
        self.maya_actions_menu()
        self.separator()
        self.show_menu()


    def maya_actions_menu(self):
        self.menu[u'save'] = {
            u'icon': images.ImageCache.get_rsc_pixmap(u'add_file', common.TEXT_SELECTED, common.MARGIN()),
            u'text': u'Save version...',
            u'action': self.parent().saveRequested.emit
        }
        self.menu[u'save_increment'] = {
            u'icon': images.ImageCache.get_rsc_pixmap(u'add_file', common.SECONDARY_TEXT, common.MARGIN()),
            u'text': u'Save quick increment...',
            u'action': self.parent().incrementRequested.emit
        }
        return


    def export_alembic_menu(self):
        objectset_pixmap = images.ImageCache.get_rsc_pixmap(
            u'set', None, common.MARGIN())

        outliner_set_members = outliner_sets()

        key = u'alembic_animation'
        self.menu[key] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(key)] = objectset_pixmap
        self.menu[u'{}:text'.format(key)] = u'Export timeline to alembic'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            self.menu[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(self.parent().alembicExportRequested.emit, k, v, False)
            }

        key = u'alembic_frame'
        self.menu[key] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(key)] = objectset_pixmap
        self.menu[u'{}:text'.format(key)] = u'Export current frame to alembic'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            self.menu[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(self.parent().alembicExportRequested.emit, k, v, True)
            }

        return


    def show_menu(self):
        if not hasattr(self.parent(), 'clicked'):
            return
        self.menu[u'show'] = {
            u'icon': images.ImageCache.get_rsc_pixmap(u'icon_bw', None, common.MARGIN()),
            u'text': u'Toggle {}'.format(common.PRODUCT),
            u'action': self.parent().clicked.emit
        }
        return


    def capture_menu(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'capture', None, common.MARGIN())
        k = 'Capture viewport'
        self.menu[k] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(k)] = pixmap

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")

        def size(n): return (int(int(width) * n), int(int(height) * n))

        for n in (1.0, 0.5, 0.25, 1.5, 2.0):
            self.menu[k][u'capture{}'.format(n)] = {
                u'text': u'Capture  |  @{}  |  {}x{}px'.format(n, *size(n)),
                u'action': functools.partial(capture_viewport, size=n)
            }
        return


class MayaBrowserButton(common_ui.ClickableIconButton):
    """Small widget to embed into the context to toggle the MainWidget's visibility.

    """
    saveRequested = QtCore.Signal()
    incrementRequested = QtCore.Signal()
    alembicExportRequested = QtCore.Signal(unicode, dict, bool)

    ContextMenu = BrowserButtonContextMenu

    def __init__(self, parent=None):
        super(MayaBrowserButton, self).__init__(
            u'icon_maya',
            (None, None),
            common.ASSET_ROW_HEIGHT(),
            description=u'Click to toggle {}.\nRight-click to see addittional options.'.format(common.PRODUCT),
            parent=parent
        )
        self.setObjectName(object_name)
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
            widget = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)
            widget.layout().addWidget(self)
            self.setFixedWidth(widget.width())
            self.setFixedHeight(widget.width())
            self.adjustSize()
            self.update()
        else:
            s = 'Could not find "ToolBox" - ``MayaBrowserButton`` not embedded.'
            log.error(s)
            print s

        # Unlocking showing widget
        currentval = cmds.optionVar(q='workspacesLockDocking')
        cmds.optionVar(intValue=(u'workspacesLockDocking', False))
        cmds.evalDeferred(show)
        cmds.evalDeferred(functools.partial(
            cmds.optionVar, intValue=(u'workspacesLockDocking', currentval)))

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 10))

        if hover:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'icon', None, self.width())
            painter.setOpacity(1.0)
        else:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'icon_bw', None, self.width())
            painter.setOpacity(0.80)

        rect = self.rect()
        center = rect.center()
        o = common.INDICATOR_WIDTH() * 2
        rect = rect.adjusted(0, 0, -o, -o)
        rect.moveCenter(center)

        painter.drawRoundRect(rect, o, o)

        painter.drawPixmap(rect, pixmap, pixmap.rect())
        painter.end()

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
        widget.move(self.mapToGlobal(self.rect().bottomLeft()))
        common.move_widget_to_available_geo(widget)
        widget.exec_()


class MayaMainWidgetContextMenu(contextmenu.BaseContextMenu):
    def setup(self):
        self.apply_bookmark_settings_menu()
        self.separator()
        self.save_actions_menu()
        self.separator()
        if index.isValid():
            self.scenes_menu()
        self.separator()
        self.export_alembic_menu()
        self.separator()
        self.capture_menu()

    def apply_bookmark_settings_menu(self):
        parent = self.parent().parent().parent().parent()
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'check', common.ADD, common.MARGIN())

        self.menu[u'apply_settings'] = {
            u'text': u'Apply scene settings...',
            u'icon': pixmap,
            u'action': parent.apply_settings
        }

    def save_actions_menu(self):
        """Save actions.

        """
        parent = self.parent().parent().parent().parent()
        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'add_file', common.TEXT_SELECTED, common.MARGIN())
        pixmap2 = images.ImageCache.get_rsc_pixmap(
            u'add_file', common.TEXT_DISABLED, common.MARGIN())
        self.menu[u'new'] = {
            u'text': u'Save version...',
            u'icon': pixmap,
            u'action': lambda: parent.save_scene(increment=False)
        }
        if common.get_sequence(scene.fileName()):
            self.menu[u'increment'] = {
                u'text': u'Save quick increment...',
                u'icon': pixmap2,
                u'action': lambda: parent.save_scene(increment=True)
            }

    def scenes_menu(self):
        """Maya & alembic import/open actions.

        """
        parent = self.parent().parent().parent().parent()
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        _s = file_info.suffix().lower()
        if _s not in (u'ma', u'mb', u'abc'):
            return

        maya_pixmap = images.ImageCache.get_rsc_pixmap(
            u'maya', None, common.MARGIN())
        maya_reference_pixmap = images.ImageCache.get_rsc_pixmap(
            u'maya_reference', None, common.MARGIN())

        self.menu[u'open_scene'] = {
            u'text': u'Open',
            u'icon': maya_pixmap,
            u'action': lambda: open_scene(file_info.filePath())
        }
        self.menu[u'import_local_scene'] = {
            u'text': u'Import',
            u'icon': maya_pixmap,
            u'action': lambda: import_scene(file_info.filePath(), reference=False)
        }
        self.menu[u'import_scene'] = {
            u'text': u'Import as reference',
            u'icon': maya_reference_pixmap,
            u'action': lambda: import_scene(file_info.filePath(), reference=True)
        }

    def export_alembic_menu(self):
        parent = self.parent().parent().parent().parent()
        objectset_pixmap = images.ImageCache.get_rsc_pixmap(
            u'set', None, common.MARGIN())

        outliner_set_members = outliner_sets()

        key = u'alembic_animation'
        self.menu[key] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(key)] = objectset_pixmap
        self.menu[u'{}:text'.format(key)] = u'Export timeline to Alembic'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            self.menu[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(parent.export_set_to_alembic, k, v, frame=False)
            }

        key = u'alembic_frame'
        self.menu[key] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(key)] = objectset_pixmap
        self.menu[u'{}:text'.format(key)] = u'Export current frame to Alembic'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            self.menu[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(parent.export_set_to_alembic, k, v, frame=True)
            }

        key = u'obj'
        self.menu[key] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(key)] = objectset_pixmap
        self.menu[u'{}:text'.format(key)] = u'Export set to *.obj'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            self.menu[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(parent.export_set_to_obj, k, v)
            }

        key = u'ass'
        self.menu[key] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(key)] = objectset_pixmap
        self.menu[u'{}:text'.format(key)] = u'Export set to Arnold *.ass'
        for k in sorted(list(outliner_set_members)):
            v = outliner_set_members[k]
            _k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            self.menu[key][_k] = {
                u'text': u'{} ({})'.format(_k.upper(), len(v)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(parent.export_set_to_ass, k, v)
            }

    def capture_menu(self):
        parent = self.parent().parent().parent().parent()
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'capture', None, common.MARGIN())
        k = 'Capture viewport'
        self.menu[k] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(k)] = pixmap

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")

        def size(n): return (int(int(width) * n), int(int(height) * n))

        for n in (1.0, 0.5, 0.25, 1.5, 2.0):
            self.menu[k][u'capture{}'.format(n)] = {
                u'text': u'Capture  |  @{}  |  {}x{}px'.format(n, *size(n)),
                u'action': functools.partial(capture_viewport, size=n)
            }



class MayaMainWidget(mayaMixin.MayaQWidgetDockableMixin, QtWidgets.QWidget):
    """The main wrapper-widget to be used inside maya."""
    terminated = QtCore.Signal()

    def __init__(self, parent=None):
        global _instance
        _instance = self
        super(MayaMainWidget, self).__init__(parent=parent)

        self._workspacecontrol = None
        self._callbacks = []  # Maya api callbacks
        self.mainwidget = None

        self.setWindowTitle(common.PRODUCT)

        # Rename object
        _object_name = self.objectName().replace(
            self.__class__.__name__, common.PRODUCT)
        self.setObjectName(_object_name)

        self._create_UI()
        self.setFocusProxy(self.mainwidget.stackedwidget)

        self.workspace_timer = QtCore.QTimer(parent=self)
        self.workspace_timer.setSingleShot(False)
        self.workspace_timer.setInterval(5000)
        self.workspace_timer.timeout.connect(self.set_workspace)

        self.mainwidget.sizeHint = self.sizeHint

        self.mainwidget.initialized.connect(
            lambda: self.mainwidget.layout().setContentsMargins(0, 0, 0, 0))
        self.mainwidget.initialized.connect(self._connect_signals)
        self.mainwidget.initialized.connect(self.context_callbacks)
        self.mainwidget.initialized.connect(self.set_workspace)
        self.mainwidget.initialized.connect(self.workspace_timer.start)

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
        assets_model = self.mainwidget.assetswidget.model().sourceModel()
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

        self.mainwidget = main.MainWidget(parent=self)
        self.layout().addWidget(self.mainwidget)
        self.mainwidget.terminated.connect(self.terminate)

    @QtCore.Slot()
    def terminate(self):
        @QtCore.Slot()
        def delete_module_import_cache():
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
                    imp.find_module(p[0], package_path)
                    del sys.modules[pkg]
                except ImportError:
                    continue
                except RuntimeError as e:
                    print e
                except ValueError as e:
                    print e

            gc.collect()

        @QtCore.Slot()
        def remove_button():
            """Removes the workspaceControl, and workspaceControlState objects."""
            ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
            if not ptr:
                widgets = QtWidgets.QApplication.instance().allWidgets()
                widget = [f for f in widgets if f.objectName() == object_name]
                if not widget:
                    return
                widget = widget[0]

            else:
                widget = shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)
                if not widget:
                    return

                widget = widget.findChild(MayaBrowserButton)

            widget.hide()
            widget.deleteLater()

        def remove_workspace_control(workspace_control):
            if cmds.workspaceControl(workspace_control, q=True, exists=True):
                cmds.deleteUI(workspace_control)
                if cmds.workspaceControlState(workspace_control, ex=True):
                    cmds.workspaceControlState(workspace_control, remove=True)
            try:
                for k in mayaMixin.mixinWorkspaceControls.items():
                    if u'MayaMainWidget' in k:
                        del mayaMixin.mixinWorkspaceControls[k]
            except:
                pass

            sys.stdout.write(
                u'# {}: UI deleted.\n'.format(common.PRODUCT))

        for widget in QtWidgets.QApplication.instance().allWidgets():
            if re.match(ur'MayaMainWidget.*WorkspaceControl', widget.objectName()):
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
                u'If you didn\'t expect this message, is it possible the project was changed by {} from another instance of Maya?'.format(common.PRODUCT)
            ).open()

    @QtCore.Slot()
    def unmark_active(self, *args):
        """Callback responsible for keeping the active-file in the list updated."""
        f = self.mainwidget.fileswidget
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
        f = self.mainwidget.fileswidget
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

    def context_callbacks(self):
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
        sys.stdout.write('# {}: Removing callbacks...\n'.format(common.PRODUCT))
        for callback in self._callbacks:
            res = OpenMaya.MMessage.removeCallback(callback)
            sys.stdout.write(u'# Callback status {}\n'.format(res))
        self._callbacks = []

    @QtCore.Slot()
    def _connect_signals(self):
        self.mainwidget.headerwidget.hide()

        bookmarkswidget = self.mainwidget.bookmarkswidget
        assetswidget = self.mainwidget.assetswidget
        fileswidget = self.mainwidget.fileswidget
        favouriteswidget = self.mainwidget.favouriteswidget

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
                open_scene(file_info.filePath())
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
        width = (width * 0.5) if width > common.WIDTH() else width
        width = width - common.INDICATOR_WIDTH()

        widget = MayaMainWidgetContextMenu(index, parent=parent)
        if index.isValid():
            rect = parent.visualRect(index)
            widget.move(
                parent.viewport().mapToGlobal(rect.bottomLeft()).x(),
                parent.viewport().mapToGlobal(rect.bottomLeft()).y(),
            )
        else:
            widget.move(common.cursor.pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH(), widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    @QtCore.Slot()
    def set_workspace(self):
        """Slot responsible for updating the Maya workspace."""
        try:
            # When active sync is disabled we won't set workspaces
            if get_preference(u'disable_workspace_sync') is True:
                return
            index = self.mainwidget.assetswidget.model().sourceModel().active_index()
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
            path = os.path.normpath(
                os.path.abspath(file_info.absoluteFilePath()))
            cmds.workspace(path, openWorkspace=True)
        except Exception as e:
            s = u'Could not set the workspace'
            common_ui.ErrorBox(
                s,
                u'This might have happened because {} is not a valid Maya Workspace?'.format(
                    file_info.fileName())
            ).open()
            log.error(s)
            raise

    @QtCore.Slot()
    def apply_settings(self):
        """Apply current Bookmark Properties to the current scene.

        """
        def _set_start_frame(frame):
            frame = round(frame, 0)
            currentFrame = round(cmds.currentTime(query=True))

            cmds.playbackOptions(animationStartTime=int(frame))
            cmds.playbackOptions(minTime=int(frame))
            cmds.setAttr('defaultRenderGlobals.startFrame', int(frame))
            if currentFrame < frame:
                cmds.currentTime(frame, edit=True)
            else:
                cmds.currentTime(currentFrame, edit=True)

        def _set_end_frame(frame):
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
            animationStartTime = cmds.playbackOptions(
                query=True, animationStartTime=True)
            minTime = cmds.playbackOptions(query=True, minTime=True)
            animationEndTime = cmds.playbackOptions(
                query=True, animationEndTime=True)
            maxTime = cmds.playbackOptions(query=True, maxTime=True)
            set_framerate(fps)
            cmds.playbackOptions(animationStartTime=animationStartTime)
            cmds.playbackOptions(minTime=minTime)
            cmds.playbackOptions(animationEndTime=animationEndTime)
            cmds.playbackOptions(maxTime=maxTime)

        def _get_cut_value(bookmark_k, asset_k, db, v):
            """ We will check if the asset has valid cut information set.

            If not, we will use the bookmark's default duration, or otherwise,
            we will not do anything.

            """
            val = None
            if db.value(asset, asset_k):
                try:
                    # Stored value might be `string`, whereas we need an `int`
                    val = int(db.value(asset, asset_k))
                except:
                    pass
            if not val and v[bookmark_k]:
                try:
                    # Stored value might be `string`, whereas we need an `int`
                    val = int(v[bookmark_k])
                except:
                    pass
            return val


        server = settings.active(settings.ServerKey)
        job = settings.active(settings.JobKey)
        root = settings.active(settings.RootKey)
        asset = settings.active(settings.AssetKey)
        if not all((server, job, root, asset)):
            return

        try:
            v = {}
            with bookmark_db.transactions(server, root, job) as db:
                source = db.source(asset)
                for _k in bookmark_db.TABLES[bookmark_db.BookmarkTable]:
                    v[_k] = db.value(db.source(), _k, table=bookmark_db.BookmarkTable)
                startframe = _get_cut_value('startframe', 'cut_in', db, v)
                duration = _get_cut_value('duration', 'cut_duration', db, v)
        except Exception as e:
            log.error(e)
            raise

        if (v['width'] and v['height']):
            try:
                cmds.setAttr('defaultResolution.width', v['width'])
                cmds.setAttr('defaultResolution.height', v['height'])
            except:
                log.error('Could not set resolution')

        if v['framerate']:
            try:
                _set_framerate(v['framerate'])
            except:
                log.error(u'Could not set frame rate')

        if startframe:
            try:
                _set_start_frame(startframe)
            except:
                log.error(u'Could not set start frame')

        if duration:
            try:
                _set_end_frame(startframe + duration)
            except:
                log.error(u'Could not set end frame')

        cmds.setAttr('defaultRenderGlobals.extensionPadding', 4)
        cmds.setAttr('defaultRenderGlobals.animation', 1)
        cmds.setAttr('defaultRenderGlobals.putFrameBeforeExt', 1)
        cmds.setAttr('defaultRenderGlobals.periodInExt', 2)
        cmds.setAttr('defaultRenderGlobals.useFrameExt', 0)
        cmds.setAttr('defaultRenderGlobals.outFormatControl', 0)
        cmds.setAttr('defaultRenderGlobals.imageFormat', 8)

        info = u'{w}{h}{fps}{pre}{start}{duration}'.format(
            w=u'{}'.format(int(v['width'])) if (
                v['width'] and v['height']) else u'',
            h=u'x{}px'.format(int(v['height'])) if (
                v['width'] and v['height']) else u'',
            fps=u'  |  {}fps'.format(
                v['framerate']) if v['framerate'] else u'',
            pre=u'  |  {}'.format(v['prefix']) if v['prefix'] else u'',
            start=u'  |  {}'.format(
                int(startframe)) if startframe else u'',
            duration=u'-{} ({} frames)'.format(
                int(startframe) + int(duration),
                int(duration) if duration else u'') if duration else u''
        )

        s = u'Successfully applied the default scene settings: {}'.format(info)
        log.success(s)
        common_ui.OkBox(
            u'Successfully applied the default scene settings.',
            info,
        ).open()

        except Exception as e:
            s = u'Could apply properties'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            log.error(s)
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

        widget = addfile.AddFileWidget(ext, file=file)
        if modal:
            if widget.exec_() == QtWidgets.QDialog.Rejected:
                return
        if not modal and not increment:
            raise RuntimeError(
                'Flags `increment` and `modal` together is undefined behaviour')
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
            log.error(s)
            raise RuntimeError(s)

        try:
            cmds.file(rename=file_path)
            cmds.file(force=True, save=True, type=u'mayaAscii')
            fileswidget = self.mainwidget.stackedwidget.widget(2)
            fileswidget.new_file_added(file_path)
            return file_path

        except Exception as e:
            s = u'Could not save the scene.'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            log.error(s)
            raise

    @QtCore.Slot(unicode)
    @QtCore.Slot(dict)
    @QtCore.Slot(bool)
    def export_set_to_ass(self, set_name, set_members, frame=False):
        """Main method to initiate an Arnold ASS export using Bookmarks's
        saver to generate the filename.

        Args:
            key (str):   The name of the object set to export.
            value (tuple): A list of object names inside the set.

        """
        # Ensure the plugin is loaded
        try:
            if not cmds.pluginInfo(u'mtoa.mll', loaded=True, q=True):
                cmds.loadPlugin(u'mtoa.mll', quiet=True)
        except Exception as e:
            s = u'Could not load the `mtoa` plugin'
            log.error(s)
            common_ui.ErrorBox(u'Could not export the set', s).open()
            raise

        # We want to handle the exact name of the file
        # We'll remove the namespace, strip underscores
        set_name = set_name.replace(u':', u'_').strip(u'_')
        set_name = re.sub(ur'[0-9]*$', u'', set_name)
        ext = u'ass'

        exportdir = find_project_folder(u'ass export')
        exportdir = exportdir if exportdir else u'export/ass'
        layer = cmds.editRenderLayerGlobals(
            query=True, currentRenderLayer=True)
        file_path = u'{workspace}/{exportdir}/{set}/{set}_{layer}_v001.{ext}'.format(
            workspace=cmds.workspace(q=True, fn=True),
            exportdir=exportdir,
            set=set_name,
            layer=layer,
            ext=ext
        )

        fileswidget = self.mainwidget.stackedwidget.widget(2)

        # Let's make sure destination folder exists
        file_info = QtCore.QFileInfo(file_path)
        _dir = file_info.dir()
        if not _dir.exists():
            if not _dir.mkpath(u'.'):
                s = u'Could not create {}'.format(_dir.path())
                log.error(s)
                common_ui.ErrorBox(u'Could not export the set', s).open()
                raise OSError(s)

        sel = cmds.ls(selection=True)
        try:
            import arnold

            # Let's get the first renderable camera
            cams = cmds.ls(cameras=True)
            cam = None
            for cam in cams:
                if cmds.getAttr('{}.renderable'.format(cam)):
                    break

            cmds.select(clear=True)
            cmds.select(set_members, replace=True)
            cmds.arnoldExportAss(
                f=file_path,
                cam=cam,
                s=True,  # selected
                mask=arnold.AI_NODE_CAMERA |
                arnold.AI_NODE_SHAPE |
                arnold.AI_NODE_SHADER |
                arnold.AI_NODE_OVERRIDE |
                arnold.AI_NODE_LIGHT
            )
            fileswidget.new_file_added(file_path)
            return file_path
        except Exception as e:
            s = u'Could not export the set'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            log.error(s)
            raise
        finally:
            cmds.select(clear=True)
            cmds.select(sel, replace=True)

    @QtCore.Slot(unicode)
    @QtCore.Slot(dict)
    @QtCore.Slot(bool)
    def export_set_to_alembic(self, set_name, set_members, frame=False):
        """Main method to initiate an alembic export using Bookmarks's
        saver to generate the filename.

        Args:
            key (str):   The name of the object set to export.
            value (tuple): A list of object names inside the set.

        """
        # Ensure the plugin is loaded
        try:
            if not cmds.pluginInfo('AbcExport.mll', loaded=True, q=True):
                cmds.loadPlugin("AbcExport.mll", quiet=True)
                cmds.loadPlugin("AbcImport.mll", quiet=True)
        except Exception as e:
            s = u'Could not load the `AbcExport` plugin'
            log.error(s)
            common_ui.ErrorBox(u'Could not export the set', s).open()
            raise

        # We want to handle the exact name of the file
        # We'll remove the namespace, strip underscores
        set_name = set_name.replace(u':', u'_').strip(u'_')
        set_name = re.sub(ur'[0-9]*$', u'', set_name)
        ext = u'abc'

        exportdir = find_project_folder(u'alembic export')
        exportdir = exportdir if exportdir else u'export/abc'
        file_path = u'{workspace}/{exportdir}/{set}/{set}_v001.{ext}'.format(
            workspace=cmds.workspace(q=True, fn=True),
            exportdir=exportdir,
            set=set_name,
            ext=ext
        )

        # Let's make sure destination folder exists
        file_info = QtCore.QFileInfo(file_path)
        _dir = file_info.dir()
        if not _dir.exists():
            if not _dir.mkpath(u'.'):
                s = u'Could not create {}'.format(_dir.path())
                log.error(s)
                common_ui.ErrorBox(u'Could not export the set', s).open()
                raise OSError(s)

        widget = addfile.AddFileWidget(ext, file=file_path)
        if widget.exec_() == QtWidgets.QDialog.Rejected:
            return None

        fileswidget = self.mainwidget.stackedwidget.widget(2)
        file_path = widget.filePath()
        file_info = QtCore.QFileInfo(file_path)

        # Last-ditch check to make sure we're not overwriting anything...
        if file_info.exists():
            s = u'Unable to save alembic: {} already exists.'.format(file_path)
            common_ui.ErrorBox(u'Could not export the set', s).open()
            log.error(s)
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
            fileswidget.new_file_added(file_path)
            return file_path
        except Exception as e:
            s = u'Could not export the set'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            log.error(s)
            raise
        finally:
            if not state:
                cmds.ogs(pause=True)

    @QtCore.Slot(unicode)
    @QtCore.Slot(dict)
    @QtCore.Slot(bool)
    def export_set_to_obj(self, set_name, set_members):
        """Main method to initiate an alembic export using Bookmarks's
        saver to generate the filename.

        Args:
            key (str):   The name of the object set to export.
            value (tuple): A list of object names inside the set.

        """
        # Ensure the plugin is loaded
        try:
            if not cmds.pluginInfo(u'objExport.mll', loaded=True, q=True):
                cmds.loadPlugin(u'objExport.mll', quiet=True)
        except Exception as e:
            s = u'Could not load the `objExport` plugin'
            log.error(s)
            common_ui.ErrorBox(u'Could not export the set', s).open()
            raise

        # We want to handle the exact name of the file
        # We'll remove the namespace, strip underscores
        set_name = set_name.replace(u':', u'_').strip(u'_')
        set_name = re.sub(ur'[0-9]*$', u'', set_name)
        ext = u'obj'

        exportdir = find_project_folder(u'objexport')
        exportdir = exportdir if exportdir else u'export/obj'
        file_path = u'{workspace}/{exportdir}/{set}/{set}_v001.{ext}'.format(
            workspace=cmds.workspace(q=True, fn=True),
            exportdir=exportdir,
            set=set_name,
            ext=ext
        )

        # Let's make sure destination folder exists
        file_info = QtCore.QFileInfo(file_path)
        _dir = file_info.dir()
        if not _dir.exists():
            if not _dir.mkpath(u'.'):
                s = u'Could not create {}'.format(_dir.path())
                log.error(s)
                common_ui.ErrorBox(u'Could not export the set', s).open()
                raise OSError(s)

        widget = addfile.AddFileWidget(ext, file=file_path)
        if widget.exec_() == QtWidgets.QDialog.Rejected:
            return None

        fileswidget = self.mainwidget.stackedwidget.widget(2)
        file_path = widget.filePath()
        file_info = QtCore.QFileInfo(file_path)

        # Last-ditch check to make sure we're not overwriting anything...
        if file_info.exists():
            s = u'Unable to save set: {} already exists.'.format(file_path)
            common_ui.ErrorBox(u'Could not export the set', s).open()
            log.error(s)
            raise RuntimeError(s)

        sel = cmds.ls(selection=True)
        try:
            cmds.select(clear=True)
            cmds.select(set_members, replace=True)

            cmds.file(
                file_info.filePath(),
                preserveReferences=True,
                type='OBJexport',
                exportSelected=True,
                options='groups=1;ptgroups=1;materials=1;smoothing=1; normals=1'
            )
            fileswidget.new_file_added(file_path)
            return file_path
        except Exception as e:
            s = u'Could not export the set'
            common_ui.ErrorBox(s, u'{}'.format(e)).open()
            log.error(s)
            raise
        finally:
            cmds.select(clear=True)
            cmds.select(sel, replace=True)

    def show(self, dockable=True):
        """Initializes the Maya workspace control on show."""
        kwargs = {
            u'dockable': True,
            u'allowedArea': None,
            u'retain': True,
            u'width': common.WIDTH() * 0.5,
            u'height': common.HEIGHT() * 0.5
        }
        super(MayaMainWidget, self).show(**kwargs)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 0.5, common.HEIGHT() * 0.5)
