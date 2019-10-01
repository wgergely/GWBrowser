# -*- coding: utf-8 -*-
"""This module defines GWBrowser's ``Maya`` module.

``MayaBrowserWidget`` is a dockable mayaMixin widget that wraps BrowserWidget.

Usage: To show the widget in maya you can use the ``mayabrowserwidget.show()``
command:

    .. code-block:: python

    import gwbrowser.context.mayabrowserwidget as mGWBrowser mGWBrowser.show()


"""
import re
import time
import sys
import functools
import traceback
from functools import wraps
import collections

from PySide2 import QtWidgets, QtGui, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import mixinWorkspaceControls
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as OpenMaya
from shiboken2 import wrapInstance
import maya.cmds as cmds


try:  # No need to use our bundled alembic module if one is already present in our environment
    from alembic import Abc
except ImportError:
    from gwalembic.alembic import Abc

from gwbrowser.settings import Active
import gwbrowser.settings as Settings
import gwbrowser.common as common
from gwbrowser.imagecache import ImageCache
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.browserwidget import BrowserWidget
from gwbrowser.common_ui import ClickableIconButton

from gwbrowser.addfilewidget import AddFileWidget




@QtCore.Slot()
def show():
    """Main function to show ``MayaBrowserWidget`` inside Maya as a dockable widget.

    The function will create ``MayaBrowserWidget`` if it doesn't yet exist and dock it
    to the _AttributeEditor_. If it exists it will get the existing instance and show
    it if not currently visible, hide it if visible.

    Usage

        Run the following python code inside maya:

        .. code-block:: python

            import gwbrowser.context.mayabrowserwidget as mayabrowserwidget
            mayabrowserwidget.show()

    """
    app = QtWidgets.QApplication.instance()

    # We will check if there's already a _MayaBrowserWidget_ instance
    for widget in app.allWidgets():
        if re.match(ur'MayaBrowserWidget.*WorkspaceControl', widget.objectName()):
            continue  # Skipping workspaceControls objects, just in case

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
                cmds.workspaceControl(workspace_control, e=True, visible=True)
            cmds.workspaceControl(
                workspace_control, e=True, collapse=not state)
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
            u'# GWBrowser: Initialized.\n{}\n'.format(traceback.print_exc()))

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
    except Exception:
        sys.stdout.write(
            u'# GWBrowser: Could not show widget:\n{}\n'.format(traceback.print_exc()))


def _is_set_created_by_user(name):
    """From the good folks at cgsociety - filters the in-scene sets to return
    the user-created items only.
    https://forums.cgsociety.org/t/maya-mel-python-list-object-sets-visible-in-the-dag/1586067/2

    """
    # We first test for plug-in object sets.
    try:
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


def report_export_progress(start, current, end, start_time):
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


def get_outliner_sets_members():
    """Returns the available outliner sets and the objects inside."""
    sets_data = {}
    for s in sorted([k for k in cmds.ls(sets=True) if _is_set_created_by_user(k)]):
        dag_set_members = cmds.listConnections(u'{}.dagSetMembers'.format(s))
        # Filters
        if not dag_set_members:
            continue
        members = [
            cmds.ls(f)[-1] for f in dag_set_members if cmds.listRelatives(f, shapes=True)]
        if not members:
            continue
        sets_data[s] = members
    return sets_data


def export_alembic(destination_path, outliner_set, startframe, endframe, step=1.0):
    """Main Alembic export function.

    Exporting is based on outliner sets and their contents. For each member of
    the this set, GWBrowser will try to find the valid shape nodes to duplicate
    their geometry in the world-space.

    Only the normals, geomtery and uvs will be exported.

    """
    is_intermediate = lambda s: cmds.getAttr(u'{}.intermediateObject'.format(s))
    is_template = lambda s: cmds.getAttr(u'{}.template'.format(s))

    world_shapes = []
    valid_shapes = []

    for item in outliner_set:
        shapes = cmds.listRelatives(item, shapes=True)
        for shape in shapes:
            if is_intermediate(shape):
                continue
            if is_template(shape):
                continue
            if not cmds.attributeQuery(u'worldMesh', node=shape, exists=True):
                continue
            valid_shapes.append(shape)

    cmds.select(clear=True)
    if cmds.namespace(exists=u'mayaExport'):
        cmds.namespace(removeNamespace=u'mayaExport',
                       deleteNamespaceContent=True)
    ns = cmds.namespace(add=u'mayaExport')

    if not valid_shapes:
        return

    for shape in valid_shapes:
        world_shape = cmds.createNode(u'mesh', name=u'{}:{}'.format(ns, shape))
        world_shapes.append(world_shape)

        cmds.connectAttr(u'{}.worldMesh[0]'.format(
            shape), u'{}.inMesh'.format(world_shape), force=True)
        cmds.connectAttr(u'{}.uvSet'.format(shape),
                         u'{}.uvSet'.format(world_shape), force=True)

    world_transforms = []
    for shape in valid_shapes:
        transform = cmds.listRelatives(shape, type=u'transform', p=True)
        if transform:
            for t in transform:
                world_transforms.append(t)

    perframecallback = u'"import gwbrowser.context.mayabrowserwidget as w;w.report_export_progress({}, #FRAME#, {}, {})"'.format(
        startframe, endframe, time.time())

    kwargs = {
        # 'jobArg': u'{f} {fr} {s} {uv} {ws} {wv} {wuvs} {rt} {ef} {df} {pfc} {ppc}'.format(
        'jobArg': u'{f} {fr} {s} {uv} {ws} {wv} {wuvs} {rt} {ef} {df} {pfc} {ppc} {ro}'.format(
            f=u'-file {}'.format(destination_path),
            fr=u'-framerange {} {}'.format(startframe, endframe),
            # frs='-framerelativesample {}'.format(1.0),
            # no='-nonormals',
            # uvo='-uvsonly',
            # pr='-preroll {}'.format(bool(preroll)),
            ro='-renderableonly',
            s=u'-step {}'.format(step),
            # sl='-selection {}'.format(False),
            # sn='-stripnamespaces',
            uv=u'-uvwrite',
            # wcs='-writecolorsets',
            # wfs='-writefacesets',
            # wfg='-wholeframegeo',
            ws=u'-worldspace',
            wv=u'-writevisibility',
            wuvs=u'-writeuvsets',
            # as_='-autosubd',
            # mfc='-melperframecallback {}'.format(''),
            pfc=u'-pythonperframecallback {}'.format(perframecallback),
            # mpc='-melpostjobcallback {}'.format(''),
            ppc=u'-pythonpostjobcallback {}'.format(
                '"\'# GWBrowser: Finished alembic export.\'"'),
            # atp='-attrprefix {}'.format(''),
            # uatp='-userattrprefix {}'.format(''),
            # u='-userattr {}'.format(''),
            rt=u'-root {}'.format(u' -root '.join(world_transforms)),
            ef=u'-eulerfilter',
            df=u'-dataformat {}'.format(u'ogawa'),
        ),
        # u'preRollStartFrame': float(int(startframe - preroll)),
        # u'dontSkipUnwrittenFrames': True,
    }

    cmds.AbcExport(**kwargs)

    # Teardown
    def teardown():
        cmds.namespace(removeNamespace=u'mayaExport',
                       deleteNamespaceContent=True)

    cmds.evalDeferred(teardown)


def contextmenu2(func):
    """Decorator to create a menu set."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        menu_set = collections.OrderedDict()
        parent = self.parent().parent().parent().parent()
        menu_set = func(self, menu_set, *args, browserwidget=parent, **kwargs)
        if not isinstance(menu_set, collections.OrderedDict):
            raise ValueError(
                'Invalid return type from context menu function, expected an OrderedDict, got {}'.format(type(menu_set)))
        self.create_menu(menu_set)
        return menu_set
    return func_wrapper


class BrowserButtonContextMenu(BaseContextMenu):
    """The context-menu associated with the BrowserButton."""

    def __init__(self, parent=None):
        super(BrowserButtonContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)

        self.add_show_menu()
        #
        self.add_separator()
        #
        self.add_toolbar_menu()

    @contextmenu
    def add_show_menu(self, menu_set):
        if not hasattr(self.parent(), 'clicked'):
            return menu_set
        menu_set[u'show'] = {
            u'icon': ImageCache.get_rsc_pixmap(u'custom', None, common.INLINE_ICON_SIZE),
            u'text': u'Toggle GWBrowser',
            u'action': self.parent().clicked.emit
        }
        return menu_set

    @contextmenu
    def add_toolbar_menu(self, menu_set):
        active_paths = Active.paths()
        bookmark = (active_paths[u'server'],
                    active_paths[u'job'], active_paths[u'root'])
        asset = bookmark + (active_paths[u'asset'],)
        location = asset + (active_paths[u'location'],)

        if all(bookmark):
            menu_set[u'bookmark'] = {
                u'icon': ImageCache.get_rsc_pixmap('bookmark', common.TEXT, common.INLINE_ICON_SIZE),
                u'disabled': not all(bookmark),
                u'text': u'Show active bookmark in the file manager...',
                u'action': functools.partial(common.reveal, u'/'.join(bookmark))
            }
            if all(asset):
                menu_set[u'asset'] = {
                    u'icon': ImageCache.get_rsc_pixmap(u'assets', common.TEXT, common.INLINE_ICON_SIZE),
                    u'disabled': not all(asset),
                    u'text': u'Show active asset in the file manager...',
                    u'action': functools.partial(common.reveal, '/'.join(asset))
                }
                if all(location):
                    menu_set[u'location'] = {
                        u'icon': ImageCache.get_rsc_pixmap(u'location', common.TEXT, common.INLINE_ICON_SIZE),
                        u'disabled': not all(location),
                        u'text': u'Show current task folder in the file manager...',
                        u'action': functools.partial(common.reveal, '/'.join(location))
                    }

        return menu_set


class MayaBrowserButton(ClickableIconButton):
    """Small widget to embed into the context to toggle the BrowserWidget's visibility.

    """
    context_menu_cls = BrowserButtonContextMenu

    def __init__(self, parent=None):
        super(MayaBrowserButton, self).__init__(
            u'custom_bw',
            (common.TEXT, common.TEXT),
            common.ASSET_ROW_HEIGHT,
            description=u'Click to toggle GWBrowser.\nRight-click to see addittional options.',
            parent=parent
        )
        self.setFocusPolicy(QtCore.Qt.NoFocus)
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
            self.repaint()
        else:
            sys.stderr.write(
                '# GWBrowser: Could not find "ToolBox" - ``MayaBrowserButton`` not embedded.\n')

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
        painter.drawRoundRect(self.rect(), 4, 4)

        pixmap = ImageCache.get_rsc_pixmap('custom_bw', common.TEXT, self.width())
        painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
        painter.end()

    def enterEvent(self, event):
        self.message.emit(self.statusTip)
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def contextMenuEvent(self, event):
        """Context menu event."""
        # Custom context menu
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier
        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit()
            return

        widget = self.context_menu_cls(parent=self)
        widget.move(self.mapToGlobal(self.rect().bottomLeft()))
        widget.setFixedWidth(300)
        common.move_widget_to_available_geo(widget)
        widget.exec_()


class MayaBrowserWidgetContextMenu(BaseContextMenu):
    """The context menu for all Maya specific actions."""

    def __init__(self, index, parent=None):
        super(MayaBrowserWidgetContextMenu, self).__init__(
            index, parent=parent)

        self.add_scene_actions_menu()

        self.add_separator()

        if index.isValid():
            self.add_scenes_menu()

        self.add_separator()

        # Caches
        if index.isValid():
            self.add_alembic_actions_menu()

        self.add_separator()

        self.add_export_alembic_menu()
        # self.add_writeobj_menu()

    @contextmenu2
    def add_scene_actions_menu(self, menu_set, browserwidget=None):
        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))
        pixmap = ImageCache.get_rsc_pixmap(
            u'add_file', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        pixmap2 = ImageCache.get_rsc_pixmap(
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

    @contextmenu2
    def add_scenes_menu(self, menu_set, browserwidget=None):
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        maya_pixmap = ImageCache.get_rsc_pixmap(
            u'maya', None, common.INLINE_ICON_SIZE)
        maya_reference_pixmap = ImageCache.get_rsc_pixmap(
            u'maya_reference', None, common.INLINE_ICON_SIZE)

        menu_set[u'open'] = {
            u'text': u'Open  "{}"'.format(file_info.fileName()),
            u'icon': maya_pixmap,
            u'action': lambda: browserwidget.open_scene(file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import  "{}"'.format(file_info.fileName()),
            u'icon': maya_pixmap,
            u'action': lambda: browserwidget.import_scene(file_info.filePath())
        }
        menu_set[u'import'] = {
            u'text': u'Reference  "{}"'.format(file_info.fileName()),
            u'icon': maya_reference_pixmap,
            u'action': functools.partial(browserwidget.import_referenced_scene, file_info.filePath())
        }
        return menu_set

    @contextmenu2
    def add_alembic_actions_menu(self, menu_set, browserwidget=None):
        """Actions associated with ``alembic`` cache operations."""
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        alembic_pixmap = ImageCache.get_rsc_pixmap(
            u'abc', None, common.INLINE_ICON_SIZE)

        menu_set[u'open'] = {
            u'text': u'Open  "{}"'.format(file_info.fileName()),
            u'icon': alembic_pixmap,
            u'action': lambda: browserwidget.open_alembic(file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import "{}"'.format(file_info.fileName()),
            u'icon': alembic_pixmap,
            u'action': lambda: browserwidget.import_scene(file_info.filePath())
        }
        menu_set[u'import'] = {
            u'text': u'Import alembic as reference...',
            u'icon': alembic_pixmap,
            u'action': lambda: browserwidget.import_referenced_scene(file_info.filePath())
        }
        return menu_set

    @contextmenu2
    def add_export_alembic_menu(self, menu_set, browserwidget=None):
        objectset_pixmap = ImageCache.get_rsc_pixmap(
            u'set', None, common.INLINE_ICON_SIZE)

        outliner_set_members = get_outliner_sets_members()

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


class MayaBrowserWidget(MayaQWidgetDockableMixin, QtWidgets.QWidget):  # pylint: disable=E1139
    """The main wrapper-widget to be used inside maya."""

    def __init__(self, parent=None):
        super(MayaBrowserWidget, self).__init__(parent=parent)
        self._workspacecontrol = None
        self._callbacks = []  # Maya api callbacks
        self.browserwidget = None

        self.setAutoFillBackground(True)
        self.setWindowTitle(u'GWBrowser')

        self._createUI()
        self.setFocusProxy(self.browserwidget)

        self.workspace_timer = QtCore.QTimer()
        self.workspace_timer.setSingleShot(False)
        self.workspace_timer.setInterval(5000)
        self.workspace_timer.timeout.connect(self.set_workspace)


        self.browserwidget.initialized.connect(self.connectSignals)
        self.browserwidget.initialized.connect(self.add_context_callbacks)
        self.browserwidget.initialized.connect(self.set_workspace)
        self.browserwidget.initialized.connect(self.workspace_timer.start)
        self.browserwidget.active_monitor.activeAssetChanged.connect(self.active_changed)

        self.browserwidget.initialize()
        self._add_shortcuts()

    @QtCore.Slot()
    def active_changed(self):
        workspace_info = QtCore.QFileInfo(cmds.workspace(q=True, expandName=True))
        
        mbox = QtWidgets.QMessageBox()
        mbox.setIcon(QtWidgets.QMessageBox.Information)
        mbox.setWindowTitle(u'GWBrowser - Workspace changed')
        mbox.setText(
            u'The current workspace changed. The new workspace is:\n{}'.format(
            workspace_info.path())
        )
        mbox.setInformativeText(u'If you didn\'t expect this message, it is possible your current project was changed by GWBrowser, perhaps in another instance of Maya.')
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
        mbox.setWindowFlags(QtCore.Qt.Window)
        res = mbox.exec_()

    def _add_shortcuts(self):
        """Global maya shortcut to do a save as"""
        self.browserwidget.add_shortcut(
            u'Ctrl+Alt+Shift+S', (self.save_scene, ), context=QtCore.Qt.ApplicationShortcut)

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        common.set_custom_stylesheet(self)

        self.browserwidget = BrowserWidget()
        self.layout().addWidget(self.browserwidget)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(common.SEPARATOR)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(self.rect())
        painter.end()

    @QtCore.Slot()
    def workspace_warning(self, *args):
        """Will give the user a warning when their workspace does not match
        with their current file.

        """
        workspace_info = QtCore.QFileInfo(cmds.workspace(q=True, expandName=True))
        scene_file = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        if scene_file.baseName().lower() == u'untitled':
            return

        if workspace_info.path().lower() not in scene_file.filePath():
            mbox = QtWidgets.QMessageBox()
            mbox.setIcon(QtWidgets.QMessageBox.Information)
            mbox.setWindowTitle(u'GWBrowser - Workspace mismatch')
            mbox.setText(
                u'Looks like you are saving "{}" outside your current project!\nYour current project is "{}"'.format(
                scene_file.fileName(),
                workspace_info.path())
            )
            mbox.setInformativeText(u'If you didn\'t expect this message, it is possible your current project was changed by GWBrowser another instance of Maya.\nOtherwise, you all is good!')
            mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            res = mbox.exec_()
            # if res == QtWidgets.QMessageBox.Cancel:
            #     return False


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
        #     OpenMaya.MSceneMessage.kBeforeSave, self.workspace_warning)
        # self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterSave, self.workspace_warning)
        self._callbacks.append(callback)



    def remove_context_callbacks(self):
        """This method is called by the Maya plug-in when unloading."""
        sys.stdout.write('\n# GWBrowser: Removing callbacks...\n\n')
        for callback in self._callbacks:
            res = OpenMaya.MMessage.removeCallback(callback)
            sys.stdout.write(u'# Callback status {}\n'.format(res))
        self._callbacks = []

    @QtCore.Slot()
    def connectSignals(self):
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

        fileswidget.activated.connect(lambda x: self.open_scene(
            common.get_sequence_endpath(x.data(QtCore.Qt.StatusTipRole))))
        favouriteswidget.activated.connect(lambda x: self.open_scene(
            common.get_sequence_endpath(x.data(QtCore.Qt.StatusTipRole))))
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
        index = self.browserwidget.assetswidget.model().sourceModel().active_index()
        if not index.isValid():
            return
        parent = index.data(common.ParentRole)
        if not parent:
            return
        if not all(parent):
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        if file_info.filePath().lower() == cmds.workspace(q=True, sn=True).lower():
            return

        cmds.workspace(file_info.filePath(), openWorkspace=True)
        print u'# GWBrowser: Maya Workspace set to {}'.format(
            file_info.filePath())

    def save_scene(self, increment=False):
        """Our custom scene saver command.
        This method will try to save a version aware file based on the
        current context.

        """
        ext = u'ma'
        file = None
        if increment:
            file = cmds.file(query=True, expandName=True)
        fileswidget = self.browserwidget.stackedwidget.widget(2)

        widget = AddFileWidget(ext, file=file)
        overlay = self.browserwidget.stackedwidget.currentWidget().disabled_overlay_widget
        overlay.show()

        if widget.exec_() == QtWidgets.QDialog.Rejected:
            overlay.hide()
            return

        file_path = widget.filePath()
        file_info = QtCore.QFileInfo(file_path)

        # Last-minute double-check to make sure we're not overwriting anything...
        if file_info.exists():
            raise RuntimeError('# Unable to save file: File already exists.')

        cmds.file(rename=file_path)
        cmds.file(force=True, save=True, type=u'mayaAscii')
        sys.stdout.write(u'# GWBrowser: Scene saved as {}\n'.format(file_path))

        fileswidget.new_file_added(widget.data_key(), file_path)
        overlay.hide()

    def open_scene(self, path):
        """Maya Command: Opens the given path in Maya using ``cmds.file``.

        """
        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.file(file_info.filePath(), open=True, force=True)
        sys.stdout.write(
            u'# GWBrowser: Scene opened {}\n'.format(file_info.filePath()))

    def import_scene(self, path):
        """Imports the given scene locally."""
        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        match = common.get_sequence(file_info.fileName())
        cmds.file(
            file_info.filePath(),
            i=True,
            ns=u'{}#'.format(match.group(1) if match else file_info.baseName())
        )

        sys.stdout.write(
            u'# GWBrowser: Scene imported locally: {}\n'.format(file_info.filePath()))

    def import_referenced_scene(self, path):
        """Imports the given scene as a reference."""
        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        match = common.get_sequence(file_info.fileName())
        cmds.file(
            file_info.filePath(),
            reference=True,
            ns=u'{}#'.format(match.group(
                1) if match else file_info.baseName()),
            rfn=u'{}RN#'.format(match.group(
                1) if match else file_info.baseName()),
        )
        sys.stdout.write(
            u'# GWBrowser: Scene imported as reference: {}\n'.format(file_info.filePath()))

    def open_alembic(self, path):
        """Opens the given scene."""
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)
            cmds.loadPlugin("AbcImport.mll", quiet=True)

        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        if not file_info.exists():
            return
        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.AbcImport(file_info.filePath(), mode=u'open')

        sys.stdout.write(
            u'# GWBrowser: Alembic opened: {}\n'.format(file_info.filePath()))

    def import_alembic(path):
        """Imports the given scene locally."""
        if not cmds.pluginInfo(u'AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)
            cmds.loadPlugin("AbcImport.mll", quiet=True)

        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        if not file_info.exists():
            return

        match = common.get_sequence(file_info.fileName())
        ns = u'{}#'.format(match.group(1) if match else file_info.baseName())
        ns = cmds.namespace(addNamespace=ns)

        parent_grp = u'{}_loc'.format(match.group(
            1) if match else file_info.baseName())
        parent_grp = cmds.createNode(
            u'transform', name=u'{}:{}'.format(ns, parent_grp))

        cmds.AbcImport(
            (file_info.filePath(),),
            reparent=parent_grp,
            mode=u'import',
            filterObjects=u'.*Shape.*'
        )

        for s in cmds.listRelatives(parent_grp, children=True):
            cmds.rename(s, u'{}:{}'.format(ns, s))

        sys.stdout.write(
            u'# GWBrowser: Alembic imported: {}\n'.format(file_info.filePath()))

    def import_referenced_alembic(path):
        """Imports the given scene as a reference."""
        if not cmds.pluginInfo('AbcImport.mll', loaded=True, q=True):
            cmds.loadPlugin("AbcExport.mll", quiet=True)
            cmds.loadPlugin("AbcImport.mll", quiet=True)

        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        if not file_info.exists():
            return

        match = common.get_sequence(file_info.fileName())
        ns = u'{}#'.format(match.group(1) if match else file_info.baseName())

        rfn = u'{}RN#'.format(match.group(
            1) if match else file_info.baseName())
        parent_grp = u'{}_loc#'.format(match.group(
            1) if match else file_info.baseName())

        cmds.file(
            file_info.filePath(),
            type=u'Alembic',
            reference=True,
            groupReference=True,
            groupName=parent_grp,
            ns=ns,
            rfn=rfn,
        )

        sys.stdout.write(
            u'# GWBrowser: Alembic referenced: {}\n'.format(file_info.filePath()))

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
        file_path = u'{workspace}/{exports}/abc/{set}_v0001.abc'.format(
            workspace=cmds.workspace(q=True, sn=True),
            exports=common.ExportsFolder,
            set=set_name.split(u':').pop()
        )

        # Let's make sure destination folder exists
        file_info = QtCore.QFileInfo(file_path)
        _dir = file_info.dir()
        if not _dir.exists():
            _dir.mkpath(u'.')

        widget = AddFileWidget(ext, file=file_path)
        fileswidget = self.browserwidget.stackedwidget.widget(2)
        overlay = self.browserwidget.stackedwidget.currentWidget().disabled_overlay_widget
        overlay.show()

        if widget.exec_() == QtWidgets.QDialog.Rejected:
            overlay.hide()
            return

        file_path = widget.filePath()
        file_info = QtCore.QFileInfo(file_path)

        # Last-minute double-check to make sure we're not overwriting anything...
        if file_info.exists():
            raise RuntimeError('# Unable to save file: File already exists.')

        if frame:
            start = cmds.currentTime(query=True)
            end = cmds.currentTime(query=True)
        else:
            start = cmds.playbackOptions(query=True, animationStartTime=True)
            end = cmds.playbackOptions(query=True, animationEndTime=True)

        # Time to start the export...
        export_alembic(
            file_info.filePath(),
            set_members,
            start,
            end
        )

        # Let's try to select the newly added alembic file
        fileswidget.new_file_added(widget.data_key(), file_path)
        overlay.hide()

    def is_scene_modified(self):
        """If the current scene was modified since the last save, the user will be
        prompted to save the scene.

        """
        if not cmds.file(q=True, modified=True):
            return

        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setText(
            u'Current scene has unsaved changes.'
        )
        mbox.setInformativeText(u'Do you want to save it before continuing?')
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
        }
        super(MayaBrowserWidget, self).show(**kwargs)
