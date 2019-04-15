# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, E0401

"""Maya wrapper for the BrowserWidget."""


import re
import os
import sys
import functools
from functools import wraps
import collections

from PySide2 import QtWidgets, QtGui, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import mixinWorkspaceControls
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as OpenMaya
from shiboken2 import wrapInstance
import maya.cmds as cmds

import gwbrowser.common as common
from gwbrowser.imagecache import ImageCache
from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.browserwidget import BrowserWidget, ListControlWidget
from gwbrowser.listcontrolwidget import BrowserButton

from gwbrowser.bookmarkswidget import BookmarksModel
from gwbrowser.assetwidget import AssetModel

from gwbrowser.assetwidget import AssetWidget
from gwbrowser.fileswidget import FilesWidget

from gwbrowser.settings import local_settings
from gwbrowser.saver import SaverWidget, SaverFileInfo, Custom
from gwbrowser.context.mayaexporter import BaseExporter, AlembicExport
from gwbrowser.settings import AssetSettings
import gwbrowser.settings as Settings


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


class MayaBrowserWidgetContextMenu(BaseContextMenu):
    """The context holding the Maya specific actions."""

    def __init__(self, index, parent=None):
        super(MayaBrowserWidgetContextMenu, self).__init__(
            index, parent=parent)
        # Scenes
        if index.isValid():
            if self.parent().model().sourceModel().data_key() == common.ScenesFolder:
                self.add_scenes_menu()
        self.add_save_as_menu()

        self.add_separator()

        # Caches
        if index.isValid():
            if self.parent().model().sourceModel().data_key() == common.ExportsFolder:
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
        objectset_pixmap = QtGui.QPixmap(':objectSet.svg')
        exporter = AlembicExport()

        key = 'alembic'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = 'Export alembic...'

        outliner_set_members = exporter.get_outliner_set_members()
        for k in sorted(list(outliner_set_members)):
            value = outliner_set_members[k]
            k = k.replace(':', ' - ')  # Namespace and speudo conflict
            menu_set[key][k] = {
                'text': '{} ({})'.format(k.upper(), len(value)),
                'icon': objectset_pixmap,
                'action': functools.partial(browserwidget.init_alembic_export, k, value, exporter)
            }

        return menu_set


    @contextmenu
    def add_writeobj_menu(self, menu_set, browserwidget=None):
        objectset_pixmap = QtGui.QPixmap(':objectSet.svg')
        exporter = BaseExporter()

        key = 'obj'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = 'Export obj...'

        outliner_set_members = exporter.get_outliner_set_members()
        for k in sorted(list(outliner_set_members)):
            value = outliner_set_members[k]
            k = k.replace(':', ' - ')  # Namespace and speudo conflict
            menu_set[key][k] = {
                'text': '{} ({})'.format(k.upper(), len(value)),
                'icon': objectset_pixmap,
                'action': functools.partial(browserwidget.init_obj_export, k, value)
            }

        return menu_set

    @contextmenu
    def add_save_as_menu(self, menu_set, browserwidget=None):
        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        if common.get_sequence(scene.fileName()):
            menu_set[u'increment'] = {
                u'text': u'Save as increment...',
                u'icon': QtGui.QPixmap(':mayaIcon.png'),
                u'action': lambda: browserwidget.save_scene(increment=True)
            }
        menu_set[u'new'] = {
            u'text': u'Save as new...',
            u'icon': QtGui.QPixmap(':mayaIcon.png'),
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
            u'icon': QtGui.QPixmap(':mayaIcon.png'),
            u'action': functools.partial(browserwidget.open_scene, file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import scene',
            u'icon': QtGui.QPixmap(':mayaIcon.png'),
            u'action': functools.partial(browserwidget.import_scene, file_info.filePath())
        }
        menu_set[u'import'] = {
            u'text': u'Import scene as reference',
            u'icon': QtGui.QPixmap(':mayaIcon.png'),
            u'action': functools.partial(browserwidget.import_referenced_scene, file_info.filePath())
        }
        return menu_set


class MayaBrowserWidget(MayaQWidgetDockableMixin, QtWidgets.QWidget):  # pylint: disable=E1139
    """The main wrapper-widget to be used inside maya."""

    # Signals for signalling show/hide status changes
    showEventTriggered = QtCore.Signal()
    hideEventTriggered = QtCore.Signal()

    def __init__(self, parent=None):
        super(MayaBrowserWidget, self).__init__(parent=parent)
        # Overriding the default name-filters
        common.NameFilters[common.ScenesFolder] = (
            u'ma',  # Maya ASCII
            u'mb',  # Maya Binary
        )

        self._workspacecontrol = None
        self._callbacks = []  # Maya api callbacks

        self.setAutoFillBackground(True)
        self.setWindowTitle(u'Browser')

        self._createUI()

        self.findChild(BrowserWidget).initialized.connect(self.connectSignals)
        self.findChild(BrowserWidget).initialized.connect(self.add_context_callbacks)
        self.findChild(BrowserWidget).initialize()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        common.set_custom_stylesheet(self)

        widget = BrowserWidget()
        self.layout().addWidget(widget)

    def unmark_active(self, *args):
        """Callback responsible for keeping the active-file in the list updated."""
        f = self.findChild(FilesWidget)
        if not f:
            return
        if not f.active_index().isValid():
            return
        f.deactivate(f.active_index())

    @QtCore.Slot()
    def update_active_item(self, *args):
        """Callback responsible for keeping the active-file in the list updated."""

        scene = common.get_sequence_endpath(
            cmds.file(query=True, expandName=True))
        f = self.findChild(FilesWidget)
        if not f:
            return

        if f.active_index().isValid():
            f.deactivate(f.active_index())

        for n in xrange(f.model().rowCount()):
            index = f.model().index(n, 0, parent=QtCore.QModelIndex())
            data = common.get_sequence_endpath(
                index.data(QtCore.Qt.StatusTipRole))

            if data == scene:
                f.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                f.scrollTo(index)
                source_index = index.model().mapToSource(index)
                flags = source_index.flags() | Settings.MarkedAsActive
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
        sys.stdout.write('\n# Browser: Removing callbacks...\n\n')
        for callback in self._callbacks:
            res = OpenMaya.MMessage.removeCallback(callback)
            sys.stdout.write('# Callback status {}\n'.format(res))
        self._callbacks = []

    @QtCore.Slot()
    def connectSignals(self):
        browserwidget = self.findChild(BrowserWidget)
        assetswidget = self.findChild(AssetWidget)
        fileswidget = self.findChild(FilesWidget)

        # Asset/project
        assetswidget.model().sourceModel().activeChanged.connect(self.set_workspace)

        # Context menu
        fileswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)

        fileswidget.activated.connect(lambda x: self.open_scene(common.get_sequence_endpath(x.data(QtCore.Qt.StatusTipRole))))
        fileswidget.model().sourceModel().modelReset.connect(self.unmark_active)
        fileswidget.model().sourceModel().modelReset.connect(self.update_active_item)

    @QtCore.Slot(tuple)
    def fileThumbnailAdded(self, args):
        """Slot called by the Saver when finished."""
        server, job, root, filepath, image = args
        settings = AssetSettings(QtCore.QModelIndex(), args=(server, job, root, filepath))
        if not image.isNull():
            image.save(settings.thumbnail_path())

        fileswidget = self.findChild(FilesWidget)
        sizehint = fileswidget.itemDelegate().sizeHint(None, None)
        height = sizehint.height() - 2
        ImageCache.get(settings.thumbnail_path(), height, overwrite=True)

    def _get_saver_for_objectset(self, ext, key, subfolder):
        """Returns a saver instance after checked for existing versions."""
        # Creating the saver with no current file set will generate a new filename
        # we can use to query the exports folder
        saver = SaverWidget(
            BookmarksModel(),
            AssetModel(),
            ext,
            subfolder,
            currentfile=None
        )
        saver.findChild(Custom).setText(key)  # Setting the group name

        # Proposed filename - we're going to check in a bit if newer versions
        # are present
        file_info = SaverFileInfo(saver).fileInfo()

        dir_ = QtCore.QFileInfo(file_info.filePath()).dir()
        dir_.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dir_.setNameFilters(('*.{}'.format(ext),))
        if not dir_.exists():
            raise RuntimeError(
                'The export destination path {} does not exist.'.format(dir_.path()))

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
                    r'{}/\1{}\3.\4').format(file_info.path(), version)
            else:
                v = int(current_filename_match.group(2)) - 1
                pad = len(current_filename_match.group(2))
                path = current_filename_match.expand(
                    r'{}/\1{}\3.\4').format(file_info.path(), u'{}'.format(v).zfill(pad))

        saver = SaverWidget(
            BookmarksModel(),
            AssetModel(),
            ext,
            location,
            currentfile=path
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
            fileswidget = self.findChild(FilesWidget)
            fileswidget.model().sourceModel().dataKeyChanged.emit(common.ExportsFolder)
            fileswidget.model().sourceModel().modelDataResetRequested.emit()

            sys.stdout.write('# Browser: Finished.Result: \n{}\n'.format(path))

        def fileDescriptionAdded(args):
            """Slot called by the Saver when finished."""
            server, job, root, filepath, description = args
            settings = AssetSettings(QtCore.QModelIndex(), args=(server, job, root, filepath))
            settings.setValue(u'config/description', description)

        # Start save
        saver = self._get_saver_for_objectset(u'obj', key, common.ExportsFolder)
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
            fileswidget = self.findChild(FilesWidget)
            fileswidget.model().sourceModel().dataKeyChanged.emit(common.ExportsFolder)
            fileswidget.model().sourceModel().modelDataResetRequested.emit()
            sys.stdout.write('# Browser: Finished.Result: \n{}\n'.format(path))

        def fileDescriptionAdded(args):
            """Slot called by the Saver when finished."""
            server, job, root, filepath, description = args
            from alembic.Abc import IArchive, GetArchiveInfo
            # WARNING: The IArchive / Boost code can't accept unicode input.
            # It needs to be a simple srt string. I do wonder why this is...
            abc = IArchive('{}'.format(filepath))
            if not abc.valid():
                annotation = 'invalid cache'
            else:
                annotation = GetArchiveInfo(abc)['userDescription']

            settings = AssetSettings(QtCore.QModelIndex(), args=(server, job, root, filepath))
            description = '{} - {}'.format(description, annotation)
            settings.setValue(u'config/description', description)

        # Start save
        saver = self._get_saver_for_objectset(u'abc', key, common.ExportsFolder)
        saver.fileSaveRequested.connect(fileSaveRequested)
        saver.fileDescriptionAdded.connect(fileDescriptionAdded)
        saver.fileThumbnailAdded.connect(self.fileThumbnailAdded)
        saver.exec_()


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
        widget.show()

    @QtCore.Slot(QtCore.QModelIndex)
    def set_workspace(self, index):
        """Slot responsible for updating the maya worspace."""
        parent = index.data(common.ParentRole)
        if not all(parent):
            return
        file_info = QtCore.QFileInfo(u'/'.join(parent))
        cmds.workspace(file_info.filePath(), openWorkspace=True)

    def floatingChanged(self, isFloating):
        """Triggered when QDockWidget.topLevelChanged() signal is triggered.
        Stub function.  Override to perform actions when this happens.
        """
        cls = self.__class__.__name__
        key = u'widget/{}/isFloating'.format(cls)
        local_settings.setValue(key, isFloating)

        wpcs = (f for f in mixinWorkspaceControls if u'MayaBrowserWidget' in f)
        if isFloating == u'0':  # why'o'why, is this a unicode value
            pass  # I can't implement this shit.

    def dockCloseEventTriggered(self):
        """riggered when QDockWidget.closeEventTriggered() signal is triggered.
        Stub function.  Override to perform actions when this happens.
        """
        cls = self.__class__.__name__
        if self.isFloating():
            x = u'widget/{}/x'.format(cls)
            y = u'widget/{}/y'.format(cls)
            local_settings.setValue(x, self.geometry().x())
            local_settings.setValue(y, self.geometry().y())

    def show(self, *args, **kwargs):
        """Initializes the Maya workspace control on show."""
        cls = self.__class__.__name__
        kwargs = {
            u'dockable': True,
            u'allowedArea': None,
            u'retain': True,
        }
        super(MayaBrowserWidget, self).show(**kwargs)


    def save_scene(self, increment=True):
        """Saves the current scene either as a new file or as an increment of
        the current scene.

        The filename and the location will be returned by the ``Saver``."""
        def fileSaveRequested(filepath):
            """Slot responsible for saving the scene-file."""
            cmds.file(rename=filepath)
            filepath = cmds.file(force=True, save=True, type='mayaAscii')

            # Refresh the view and select the added path
            fileswidget = self.findChild(FilesWidget)
            fileswidget.model().sourceModel().dataKeyChanged.emit(common.ScenesFolder)
            fileswidget.model().sourceModel().modelDataResetRequested.emit()

            sys.stdout.write('# Browser: Finished.Result: \n{}\n'.format(filepath))

        def fileDescriptionAdded(args):
            """Slot responsible for saving the description"""
            server, job, root, filepath, description = args
            settings = AssetSettings(QtCore.QModelIndex(), args=(server, job, root, filepath))
            settings.setValue(u'config/description', description)

        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))
        currentfile = scene.filePath() if scene.exists() and increment else None
        data_key = self.findChild(BrowserWidget).fileswidget.model().sourceModel().data_key()
        subfolder = data_key if data_key else common.ScenesFolder

        if currentfile:
            index = self.findChild(BrowserWidget).assetswidget.model().sourceModel().active_index()
            if index.isValid():
                if index.data(QtCore.Qt.StatusTipRole) in currentfile:
                    subfolder = currentfile.replace(index.data(QtCore.Qt.StatusTipRole), u'')
                    subfolder = subfolder.split(u'/')
                    subfolder.pop()
                    subfolder = u'/'.join(subfolder).strip('/')

        saver = SaverWidget(
            BookmarksModel(),
            AssetModel(),
            u'ma',
            subfolder,
            currentfile=currentfile
        )

        saver.fileSaveRequested.connect(fileSaveRequested)
        saver.fileDescriptionAdded.connect(fileDescriptionAdded)
        saver.fileThumbnailAdded.connect(self.fileThumbnailAdded)
        saver.exec_()
        self.findChild(BrowserWidget).fileswidget.model().sourceModel().modelDataResetRequested.emit()

    def open_scene(self, path):
        """Opens the given scene."""
        file_info = QtCore.QFileInfo(common.get_sequence_endpath(path))
        if not file_info.exists():
            sys.stderr.write('# Browser: File {} does not exist.\n'.format(path))
            return
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
        if cmds.file(q=True, modified=True):
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setText(
                u'Current scene has unsaved changes.'
            )
            mbox.setInformativeText(u'Save the scene now?')
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Save
                | QtWidgets.QMessageBox.Discard
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


class MayaBrowserButton(BrowserButton):
    """A dockable tool bar for showing/hiding the browser window."""

    def __init__(self, parent=None):
        super(MayaBrowserButton, self).__init__(parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setToolTip(u'Browser')
        self.clicked.connect(self.show_browser)

    def initialize(self):
        # Embeds this widget to the maya toolbox
        ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
        widget = wrapInstance(long(ptr), QtWidgets.QWidget)
        widget.layout().addWidget(self)
        self.set_size(widget.width())
        self.update()

        # Unlocking showing widget
        currentval = cmds.optionVar(q='workspacesLockDocking')
        cmds.optionVar(intValue=(u'workspacesLockDocking', False))
        cmds.evalDeferred(self.show_browser)
        cmds.evalDeferred(functools.partial(
            cmds.optionVar, intValue=(u'workspacesLockDocking', currentval)))

    @QtCore.Slot()
    def show_browser(self):
        """Slot responsible showing the maya browser widget."""
        app = QtWidgets.QApplication.instance()
        try:
            for widget in app.allWidgets():
                match = re.match(
                    r'MayaBrowserWidget.*WorkspaceControl', widget.objectName())
                if match:
                    continue
                match = re.match(r'MayaBrowserWidget.*', widget.objectName())
                if match:
                    if widget.isFloating():
                        widget.raise_()
                    else:
                        widget.show()
                    return
        except Exception as err:
            sys.stdout.write(
                '# Browser: Could not show widget:\n{}\n'.format(err))

        try:
            widget = MayaBrowserWidget()
            widget.show()

            for widget in app.allWidgets():
                match = re.match(
                    r'MayaBrowserWidget.*WorkspaceControl', widget.objectName())
                if match:
                    cmds.evalDeferred(
                        lambda *args: cmds.workspaceControl(widget.objectName(), e=True, tabToControl=(u'AttributeEditor', -1)))
                    cmds.evalDeferred(lambda: widget.raise_())
                    return
        except Exception as err:
            sys.stdout.write(
                '# Browser: Could not show widget:\n{}\n'.format(err))
