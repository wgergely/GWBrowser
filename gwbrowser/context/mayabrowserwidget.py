# -*- coding: utf-8 -*-
"""Maya wrapper for the BrowserWidget."""


import re
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

try: # No need to use our bundled alembic module if one is already present in our environment
    from alembic import Abc
except ImportError:
    from gwalembic.alembic import Abc

from gwbrowser.settings import Active
import gwbrowser.common as common
from gwbrowser.imagecache import ImageCache
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.browserwidget import BrowserWidget
from gwbrowser.editors import ClickableLabel
from gwbrowser.bookmarkswidget import BookmarksModel
from gwbrowser.assetswidget import AssetModel

from gwbrowser.addfilewidget import AddFileWidget, SaverFileInfo, Custom
from gwbrowser.context.mayaexporter import BaseExporter, AlembicExport
from gwbrowser.settings import AssetSettings


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
            continue # Skipping workspaceControls objects, just in case

        match = re.match(ur'MayaBrowserWidget.*', widget.objectName())
        if not match:
            continue

        if widget.isFloating():
            common.move_widget_to_available_geo(widget.window())
            widget.window().raise_()
            return

        workspace_control = widget.parent().objectName()
        if cmds.workspaceControl(workspace_control, q=True, exists=True):
            state = cmds.workspaceControl(workspace_control, q=True, collapse=True)
            cmds.workspaceControl(workspace_control, e=True, collapse=not state)
        else:
            widget.setVisible(not widget.isVisible())
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


def contextmenu(func):
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
        self.add_toolbar_menu()

    @contextmenu
    def add_show_menu(self, menu_set):
        if not hasattr(self.parent(), 'clicked'):
            return menu_set
        menu_set[u'show'] = {
            u'icon': ImageCache.get_rsc_pixmap(u'custom', None, common.INLINE_ICON_SIZE),
            u'text': u'Open...',
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


class MayaBrowserButton(ClickableLabel):
    """Small widget to embed into the context to toggle the BrowserWidget's visibility.

    """
    message = QtCore.Signal(unicode)

    def __init__(self, height=common.ROW_HEIGHT, parent=None):
        super(MayaBrowserButton, self).__init__(parent=parent)
        self.context_menu_cls = BrowserButtonContextMenu
        self.setFixedWidth(height)
        self.setFixedHeight(height)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setWindowFlags(
            QtCore.Qt.Widget
            | QtCore.Qt.FramelessWindowHint
        )
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom_bw', common.SECONDARY_TEXT, height)
        self.setPixmap(pixmap)

        description = u'Show GWBrowser'
        self.setStatusTip(description)
        self.setToolTip(description)

        self.clicked.connect(
            show, type=QtCore.Qt.QueuedConnection)

    def set_size(self, size):
        self.setFixedWidth(int(size))
        self.setFixedHeight(int(size))
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom_bw', common.SECONDARY_TEXT, int(size))
        self.setPixmap(pixmap)

    def enterEvent(self, event):
        self.message.emit(self.statusTip())
        self.repaint()

    def leaveEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        """Browser button's custom paint event."""
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        painter = QtGui.QPainter()
        painter.begin(self)
        brush = self.pixmap().toImage()

        painter.setBrush(brush)
        painter.setPen(QtCore.Qt.NoPen)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        painter.setOpacity(0.8)
        if option.state & QtWidgets.QStyle.State_MouseOver:
            painter.setOpacity(1)

        painter.drawRoundedRect(self.rect(), 2, 2)
        painter.end()

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

    def initialize(self):
        """Finds the built-in Toolbox menu and embeds a custom control-button
        for the Browser ``MayaBrowserButton``.

        """
        # Get the tool box and embed
        ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
        if ptr is not None:
            widget = wrapInstance(long(ptr), QtWidgets.QWidget)
            widget.layout().addWidget(self)
            self.set_size(widget.width())
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


class MayaBrowserWidgetContextMenu(BaseContextMenu):
    """The context menu for all Maya specific actions."""

    def __init__(self, index, parent=None):
        super(MayaBrowserWidgetContextMenu, self).__init__(
            index, parent=parent)

        # Scenes
        if index.isValid():
            self.add_scenes_menu()
        self.add_save_as_menu()

        self.add_separator()

        # Caches
        if index.isValid():
            self.add_readalembic_menu()

        self.add_writealembic_menu()
        self.add_writeobj_menu()

    @contextmenu
    def add_readalembic_menu(self, menu_set, browserwidget=None):
        """Actions associated with ``alembic`` cache operations."""
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        menu_set[u'open'] = {
            u'text': u'Open alembic...',
            u'icon': QtGui.QPixmap(':importAlembic.png'),
            u'action': functools.partial(browserwidget.open_alembic, file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import alembic...',
            u'icon': QtGui.QPixmap(':importAlembic.png'),
            u'action': functools.partial(browserwidget.import_scene, file_info.filePath())
        }
        menu_set[u'import'] = {
            u'text': u'Import alembic as reference...',
            u'icon': QtGui.QPixmap(':importAlembic.png'),
            u'action': functools.partial(browserwidget.import_referenced_scene, file_info.filePath())
        }
        return menu_set

    @contextmenu
    def add_writealembic_menu(self, menu_set, browserwidget=None):
        objectset_pixmap = QtGui.QPixmap(u':objectSet.svg')
        exporter = AlembicExport()

        key = u'alembic'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = u'Export alembic...'

        outliner_set_members = exporter.get_outliner_set_members()
        for k in sorted(list(outliner_set_members)):
            value = outliner_set_members[k]
            k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            menu_set[key][k] = {
                u'text': u'{} ({})'.format(k.upper(), len(value)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(browserwidget.init_alembic_export, k, value, exporter)
            }

        return menu_set

    @contextmenu
    def add_writeobj_menu(self, menu_set, browserwidget=None):
        objectset_pixmap = QtGui.QPixmap(u':objectSet.svg')
        exporter = BaseExporter()

        key = u'obj'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = u'Export obj...'

        outliner_set_members = exporter.get_outliner_set_members()
        for k in sorted(list(outliner_set_members)):
            value = outliner_set_members[k]
            k = k.replace(u':', u' - ')  # Namespace and speudo conflict
            menu_set[key][k] = {
                u'text': u'{} ({})'.format(k.upper(), len(value)),
                u'icon': objectset_pixmap,
                u'action': functools.partial(browserwidget.init_obj_export, k, value)
            }

        return menu_set

    @contextmenu
    def add_save_as_menu(self, menu_set, browserwidget=None):
        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        if common.get_sequence(scene.fileName()):
            menu_set[u'increment'] = {
                u'text': u'Save as increment...',
                u'icon': QtGui.QPixmap(u':mayaIcon.png'),
                u'action': lambda: browserwidget.save_scene(increment=True)
            }
        menu_set[u'new'] = {
            u'text': u'Save as new...',
            u'icon': QtGui.QPixmap(u':mayaIcon.png'),
            u'action': lambda: browserwidget.save_scene(increment=False)
        }
        return menu_set

    @contextmenu
    def add_scenes_menu(self, menu_set, browserwidget=None):
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        menu_set[u'open'] = {
            u'text': u'Open scene',
            u'icon': QtGui.QPixmap(u':mayaIcon.png'),
            u'action': functools.partial(browserwidget.open_scene, file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import scene',
            u'icon': QtGui.QPixmap(u':mayaIcon.png'),
            u'action': functools.partial(browserwidget.import_scene, file_info.filePath())
        }
        menu_set[u'import'] = {
            u'text': u'Import scene as reference',
            u'icon': QtGui.QPixmap(u':mayaIcon.png'),
            u'action': functools.partial(browserwidget.import_referenced_scene, file_info.filePath())
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

        self.workspace_timer = QtCore.QTimer()
        self.workspace_timer.setSingleShot(False)
        self.workspace_timer.setInterval(5000)
        self.workspace_timer.timeout.connect(self.set_workspace)

        self.browserwidget.initialized.connect(self.connectSignals)
        self.browserwidget.initialized.connect(self.add_context_callbacks)
        self.browserwidget.initialized.connect(self.set_workspace)
        self.browserwidget.initialized.connect(self.workspace_timer.start)

        self.browserwidget.initialize()

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

            if data == scene:
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

    @QtCore.Slot(tuple)
    def fileThumbnailAdded(self, args):
        """Slot called by the Saver when finished."""
        server, job, root, filepath, image = args
        settings = AssetSettings(QtCore.QModelIndex(),
                                 args=(server, job, root, filepath))
        if not image.isNull():
            image.save(settings.thumbnail_path())

        fileswidget = self.browserwidget.fileswidget
        sizehint = fileswidget.itemDelegate().sizeHint(None, None)
        height = sizehint.height() - 2
        ImageCache.get(settings.thumbnail_path(), height, overwrite=True)

    def _get_saver_for_objectset(self, ext, key, subfolder):
        """Returns a saver instance after checked for existing versions."""
        # Creating the saver with no current file set will generate a new filename
        # we can use to query the exports folder
        saver = AddFileWidget(
            BookmarksModel(),
            AssetModel(),
            ext,
            currentfile=None,
            parent=self.browserwidget
        )
        saver.findChild(Custom).setText(key)  # Setting the group name

        # Proposed filename - we're going to check in a bit if newer versions
        # are present
        file_info = SaverFileInfo(saver).fileInfo()

        dir_ = QtCore.QFileInfo(file_info.filePath()).dir()
        dir_.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dir_.setNameFilters((u'*.{}'.format(ext),))
        if not dir_.exists():
            raise RuntimeError(
                u'The export destination path {} does not exist.'.format(dir_.path()))

        # Let's check if the current name is a sequence
        current_filename_match = common.get_sequence(file_info.fileName())
        path = file_info.fileName()

        if current_filename_match:  # sequence
            versions = []

            # We're going to look for existing files and match it against the
            # proposed filename
            for entry in dir_.entryInfoList():
                # Checking if the entry is a sequence
                existing_file_match = common.get_sequence(entry.fileName())
                if not existing_file_match:
                    continue
                # Comparing against the new version and if they're the same
                # thread saving it
                if existing_file_match.group(1) == current_filename_match.group(1):
                    versions.append(existing_file_match.group(2))

            if versions:
                # finding the largest version
                version = unicode(max([int(f) for f in versions])).zfill(
                    len(versions[-1]))
                # Making a new filename
                path = current_filename_match.expand(
                    ur'{}/\1{}\3.\4').format(file_info.path(), version)
            else:
                v = int(current_filename_match.group(2)) - 1
                pad = len(current_filename_match.group(2))
                path = current_filename_match.expand(
                    ur'{}/\1{}\3.\4').format(file_info.path(), u'{}'.format(v).zfill(pad))

        saver = AddFileWidget(
            BookmarksModel(),
            AssetModel(),
            ext,
            currentfile=path,
            parent=self.browserwidget
        )
        return saver

    def init_obj_export(self, key, value):
        """Main method to initiate an alembic export using Browser's
        saver to generate the filename.

        Args:
            key (str):   The name of the object set to export.
            value (tuple): A list of object names inside the set.

        """
        def fileSaveRequested(filepath):
            """Slot called by the Saver when finished."""
            cmds.select(value, replace=True)
            filepath = cmds.file(
                filepath,
                force=True,
                type='OBJexport',
                options='groups=1;ptgroups=1;materials=1;smoothing=1;normals=1',
                preserveReferences=True,
                exportSelected=True)

            # Refresh the view and select the added path
            fileswidget = self.browserwidget.fileswidget
            fileswidget.model().sourceModel().dataKeyChanged.emit(common.ExportsFolder)
            fileswidget.model().sourceModel().modelDataResetRequested.emit()

        def fileDescriptionAdded(args):
            """Slot called by the Saver when finished."""
            server, job, root, filepath, description = args
            settings = AssetSettings(
                QtCore.QModelIndex(), args=(server, job, root, filepath))
            settings.setValue(u'config/description', description)

        # Start save
        saver = self._get_saver_for_objectset(
            u'obj', key, common.ExportsFolder)
        saver.fileSaveRequested.connect(fileSaveRequested)
        saver.fileDescriptionAdded.connect(fileDescriptionAdded)
        saver.fileThumbnailAdded.connect(self.fileThumbnailAdded)
        saver.exec_()

    def init_alembic_export(self, key, value, exporter):
        """Main method to initiate an alembic export using Browser's
        saver to generate the filename.

        Args:
            key (str):   The name of the object set to export.
            value (tuple): A list of object names inside the set.

        """
        def fileSaveRequested(filepath):
            """Slot called by the Saver when finished."""
            exporter.export(
                filepath,
                value,
                cmds.playbackOptions(query=True, animationStartTime=True),
                cmds.playbackOptions(query=True, animationEndTime=True)
            )

            # Refresh the view and select the added path
            fileswidget = self.browserwidget.fileswidget
            fileswidget.model().sourceModel().dataKeyChanged.emit(common.ExportsFolder)
            fileswidget.model().sourceModel().modelDataResetRequested.emit()
            sys.stdout.write(
                '# GWBrowser: Finished.Result: \n{}\n'.format(filepath))

        def fileDescriptionAdded(args):
            """Slot called by the Saver when finished."""
            server, job, root, filepath, description = args
            # WARNING: The IArchive / Boost code can't accept unicode input.
            # It needs to be a simple srt string. I do wonder why this is...
            abc = Abc.IArchive('{}'.format(filepath))
            if not abc.valid():
                annotation = 'invalid cache'
            else:
                annotation = Abc.GetArchiveInfo(abc)['userDescription']

            settings = AssetSettings(
                QtCore.QModelIndex(), args=(server, job, root, filepath))
            description = '{} - {}'.format(description, annotation)
            settings.setValue(u'config/description', description)

        # Start save
        saver = self._get_saver_for_objectset(
            u'abc', key, common.ExportsFolder)
        saver.fileSaveRequested.connect(fileSaveRequested)
        saver.fileDescriptionAdded.connect(fileDescriptionAdded)
        saver.fileThumbnailAdded.connect(self.fileThumbnailAdded)
        saver.exec_()

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
        """Slot responsible for updating the maya workspace."""
        index = self.browserwidget.assetswidget.model().sourceModel().active_index()
        if not index.isValid():
            return
        parent = index.data(common.ParentRole)
        if not parent:
            return
        if not all(parent):
            return

        file_info = QtCore.QFileInfo(u'/'.join(parent))
        if file_info.filePath().lower() == cmds.workspace(q=True, sn=True).lower():
            return

        cmds.workspace(file_info.filePath(), openWorkspace=True)
        print '# GWBrowser: Maya Workspace set to {}'.format(file_info.filePath())

    def show(self, dockable=True):
        """Initializes the Maya workspace control on show."""
        kwargs = {
            u'dockable': True,
            u'allowedArea': None,
            u'retain': True,
        }
        super(MayaBrowserWidget, self).show(**kwargs)

    def save_scene(self, increment=True):
        """Saves the current scene either as a new file or as an increment of
        the current scene.

        The filename and the location will be returned by the ``Saver``.

        """
        fileswidget = self.browserwidget.fileswidget

        def fileSaveRequested(filepath):
            """Slot responsible for saving the scene-file."""
            cmds.file(rename=filepath)
            filepath = cmds.file(force=True, save=True, type='mayaAscii')

            # Refresh the view and select the added path
            # Switching to the scenes folder
            fileswidget.model().sourceModel().dataKeyChanged.emit(common.ScenesFolder)
            # Refreshing the model
            fileswidget.model().sourceModel().modelDataResetRequested.emit()

        def fileDescriptionAdded(args):
            """Slot responsible for saving the description."""
            server, job, root, filepath, description = args
            settings = AssetSettings(
                QtCore.QModelIndex(), args=(server, job, root, filepath))
            settings.setValue(u'config/description', description)

        bookmark_model = BookmarksModel()
        asset_model = AssetModel()
        extension = u'ma'  # This is a generic extension that can be overriden

        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))
        currentfile = scene.filePath() if scene.exists() and increment else None

        saver = AddFileWidget(
            bookmark_model,
            asset_model,
            extension,
            currentfile=currentfile,
            parent=self.browserwidget
        )

        saver.fileSaveRequested.connect(fileSaveRequested)
        saver.fileDescriptionAdded.connect(fileDescriptionAdded)
        saver.fileThumbnailAdded.connect(self.fileThumbnailAdded)

        saver.exec_()

    def open_scene(self, path):
        """Maya Command: Opens the given path in Maya using ``cmds.file``.

        """
        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.file(file_info.filePath(), open=True, force=True)

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

    def open_alembic(self, path):
        """Opens the given scene."""
        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.AbcImport(file_info.filePath(), mode=u'open')

    def import_alembic(self, path):
        """Imports the given scene locally."""
        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.AbcImport(
            (file_info.filePath(),),
            mode=u'import',
            filterObjects=".*Shape.*"
        )

    def import_referenced_alembic(self, path):
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
            type=u'Alembic',
            reference=True,
            ns=u'{}#'.format(match.group(
                1) if match else file_info.baseName()),
            rfn=u'{}RN#'.format(match.group(
                1) if match else file_info.baseName()),
        )

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
