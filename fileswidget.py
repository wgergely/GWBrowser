# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

from PySide2 import QtWidgets, QtCore, QtGui

from browser.baselistwidget import BaseContextMenu
from browser.baselistwidget import BaseInlineIconWidget
from browser.baselistwidget import BaseModel

import browser.common as common
from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from browser.settings import AssetSettings
from browser.settings import local_settings, path_monitor
from browser.delegate import FilesWidgetDelegate
import browser.editors as editors
from browser.spinner import longprocess


class FilesWidgetContextMenu(BaseContextMenu):
    """Context menu associated with FilesWidget."""

    def __init__(self, index, parent=None):
        super(FilesWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions
        self.add_sort_menu()
        self.add_display_toggles_menu()
        if index.isValid():
            self.add_reveal_folder_menu()
            self.add_copy_menu()
            self.add_mode_toggles_menu()
            self.add_thumbnail_menu()
        self.add_location_toggles_menu()
        self.add_collapse_sequence_menu()
        self.add_refresh_menu()


class FilesModel(BaseModel):
    """The model to collect files."""

    activeLocationChanged = QtCore.Signal(str)

    def __init__(self, asset, parent=None):

        self.asset = asset
        self.mode = None
        self._isgrouped = None

        super(FilesModel, self).__init__(parent=parent)
        self.switch_dataset()

        self.grouppingChanged.connect(self.switch_dataset)
        self.activeLocationChanged.connect(self.switch_dataset)

    @longprocess
    def __initdata__(self, spinner=None):
        """To get the files, we will have to decide what extensions to take
        into consideration and what location to get the files from.

        Each asset should be made up of an `scenes`, `renders`, `textures` and
        `exports` folder. See the ``common`` module for definitions.

        """
        location = self.get_location()
        active_paths = path_monitor.get_active_paths()
        self._internal_data[location] = {True: {}, False: {}}
        server, job, root, asset = self.asset

        if not all(self.asset):
            return

        self.modes = self.get_modes(self.asset, location)
        # Iterator
        dir_ = QtCore.QDir('{asset}/{location}'.format(
            asset='/'.join(self.asset),
            location=location
        ))
        if not dir_.exists():
            return
        dir_.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dir_.setSorting(QtCore.QDir.Unsorted)
        dir_.setNameFilters(common.NameFilters[location])
        it = QtCore.QDirIterator(
            dir_, flags=QtCore.QDirIterator.Subdirectories)

        idx = 0
        __count = 0
        __nth = 300
        while it.hasNext():
            path = it.next()

            # Collecting files can take a long time. We're triggering ui updates inside loop here.
            __count += 1
            if ((__count % __nth) + 1) == __nth:
                spinner.setText(it.fileName())
                QtCore.QCoreApplication.instance().processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents)

            # We're not going to set more data when looking inside the ``renders`` location.
            # Things can slow down when querrying 10000+ files.
            if location == common.RendersFolder:
                self._internal_data[location][False][idx] = {
                    int(QtCore.Qt.StatusTipRole): path,
                    int(common.FlagsRole): QtCore.Qt.NoItemFlags
                }
                idx += 1
                continue

            # Flags
            flags = (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable |
                QtCore.Qt.ItemIsDragEnabled
            )

            # Active
            fileroot = '/'.join((server, job, root, asset, location))
            fileroot = it.fileInfo().path().replace(fileroot, '')
            fileroot = fileroot.strip('/')

            activefilepath = '{}/{}'.format(fileroot, it.fileName())
            if activefilepath == active_paths['file']:
                flags = flags | MarkedAsActive

            # Archived
            settings = AssetSettings((server, job, root, it.filePath()))
            if settings.value('config/archived'):
                flags = flags | MarkedAsArchived

            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if it.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            # Todos
            count = 0

            tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
            tooltip += u'{}'.format(it.filePath())

            # File info
            info_string = '{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                day=it.fileInfo().lastModified().toString('dd'),
                month=it.fileInfo().lastModified().toString('MM'),
                year=it.fileInfo().lastModified().toString('yyyy'),
                hour=it.fileInfo().lastModified().toString('hh'),
                minute=it.fileInfo().lastModified().toString('mm'),
                size=common.byte_to_string(it.fileInfo().size())
            )

            self._internal_data[location][False][idx] = {
                QtCore.Qt.DisplayRole: it.fileName(),
                QtCore.Qt.EditRole: it.fileName(),
                QtCore.Qt.StatusTipRole: it.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, fileroot),
                common.DescriptionRole: settings.value('config/description'),
                common.TodoCountRole: count,
                common.FileDetailsRole: info_string,
            }

            common.cache_image(
                settings.thumbnail_path(),
                common.ROW_HEIGHT - 2
            )

            idx += 1

        # Getting unique sequence groups
        groups = {}
        idx = 0
        for k in self._internal_data[location][False]:
            path = self._internal_data[location][False][k][QtCore.Qt.StatusTipRole]
            match = common.get_sequence(path)
            if not match:  # Non-sequence items

                # Previously skipped all this, have to re-add the data here.
                if location == common.RendersFolder:
                    file_info = QtCore.QFileInfo(
                        self._internal_data[location][False][k][QtCore.Qt.StatusTipRole])

                    # Active
                    fileroot = '/'.join((server, job, root, asset, location))
                    fileroot = file_info.path().replace(fileroot, '')
                    fileroot = fileroot.strip('/')

                    # Flags
                    flags = (
                        QtCore.Qt.ItemNeverHasChildren |
                        QtCore.Qt.ItemIsSelectable |
                        QtCore.Qt.ItemIsEnabled |
                        QtCore.Qt.ItemIsEditable |
                        QtCore.Qt.ItemIsDragEnabled
                    )

                    activefilepath = '{}/{}'.format(fileroot,
                                                    file_info.fileName())
                    if activefilepath == active_paths['file']:
                        flags = flags | MarkedAsActive

                    # Archived
                    settings = AssetSettings(
                        (server, job, root, file_info.filePath()))
                    if settings.value('config/archived'):
                        flags = flags | MarkedAsArchived

                    # Favourite
                    favourites = local_settings.value('favourites')
                    favourites = favourites if favourites else []
                    if file_info.filePath() in favourites:
                        flags = flags | MarkedAsFavourite

                    # Todos
                    count = 0

                    tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
                    tooltip += u'{}'.format(file_info.filePath())

                    # File info
                    info_string = '{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                        day=file_info.lastModified().toString('dd'),
                        month=file_info.lastModified().toString('MM'),
                        year=file_info.lastModified().toString('yyyy'),
                        hour=file_info.lastModified().toString('hh'),
                        minute=file_info.lastModified().toString('mm'),
                        size=common.byte_to_string(file_info.size())
                    )
                    self._internal_data[location][True][idx] = {
                        QtCore.Qt.DisplayRole: file_info.fileName(),
                        QtCore.Qt.EditRole: file_info.fileName(),
                        QtCore.Qt.StatusTipRole: file_info.filePath(),
                        QtCore.Qt.ToolTipRole: 'Non-sequence item.',
                        QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                        common.FlagsRole: flags,
                        common.ParentRole: (server, job, root, asset, location, fileroot),
                        common.DescriptionRole: settings.value('config/description'),
                        common.TodoCountRole: count,
                        common.FileDetailsRole: info_string,
                    }
                    common.cache_image(
                        settings.thumbnail_path(),
                        common.ROW_HEIGHT - 2
                    )
                else:
                    # We can just use the previously collected data
                    self._internal_data[location][True][idx] = self._internal_data[location][False][k]
                idx += 1
                continue

            k = '{}|{}'.format(match.group(1), match.group(3))
            if k not in groups:
                file_info = QtCore.QFileInfo(path)
                groups[k] = {
                    'path': path,
                    'frames': [],
                    'size': file_info.size(),
                    'padding': len(match.group(2)),
                    'modified': file_info.lastModified(),
                    'ext': match.group(3)
                }
            groups[k]['frames'].append(int(match.group(2)))

        # Adding the collapsed sequence items
        for k in groups:
            frames = groups[k]['frames']
            frames = sorted(list(set(frames)))
            path = '{}[{}].{}'.format(
                k.split('|')[0],
                common.get_ranges(frames, groups[k]['padding']),
                groups[k]['ext']
            )

            file_info = QtCore.QFileInfo(path)
            settings = AssetSettings((server, job, root, file_info.filePath()))

            # Flags
            flags = (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable |
                QtCore.Qt.ItemIsDragEnabled
            )

            # Active
            fileroot = '/'.join((server, job, root, asset, location))
            fileroot = file_info.path().replace(fileroot, '')
            fileroot = fileroot.strip('/')
            activefilepath = '{}/{}'.format(fileroot, file_info.fileName())
            if activefilepath == active_paths['file']:
                flags = flags | MarkedAsActive

            # Archived
            if settings.value('config/archived'):
                flags = flags | MarkedAsArchived

            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            # Modes
            fileroot = '/'.join((server, job, root, asset, location))
            fileroot = file_info.path().replace(fileroot, '')
            fileroot = fileroot.strip('/')

            tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
            tooltip += u'{}'.format(file_info.filePath())

            # File info
            info_string = 'Sequence of {} files'.format(len(frames))

            tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
            tooltip += u'{}  (sequence)'.format(file_info.filePath())

            self._internal_data[location][True][idx] = {
                QtCore.Qt.DisplayRole: file_info.fileName(),
                QtCore.Qt.EditRole: file_info.fileName(),
                QtCore.Qt.StatusTipRole: file_info.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, fileroot),
                common.DescriptionRole: settings.value('config/description'),
                common.TodoCountRole: 0,
                common.FileDetailsRole: info_string,
            }

            common.cache_image(
                settings.thumbnail_path(),
                common.ROW_HEIGHT - 2
            )

            idx += 1

    def canDropMimeData(self, data, action, row, column):
        return False

    def supportedDropActions(self):
        return QtCore.Qt.IgnoreAction

    def supportedDragActions(self):
        return QtCore.Qt.CopyAction

    def mimeData(self, indexes):
        index = next((f for f in indexes), None)
        mime = QtCore.QMimeData()
        location = self.get_location()
        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))

        if location == common.RendersFolder:  # first file
            filepath = common.get_sequence_startpath(file_info.filePath())
        elif location == common.ScenesFolder:  # last file
            filepath = common.get_sequence_endpath(file_info.filePath())
        elif location == common.TexturesFolder:
            filepath = common.get_sequence_endpath(file_info.filePath())
        elif location == common.ExportsFolder:
            filepath = common.get_sequence_endpath(file_info.filePath())

        url = QtCore.QUrl.fromLocalFile(filepath)
        mime.setUrls((url,))
        mime.setData(
            'application/x-qt-windows-mime;value="FileName"',
            QtCore.QDir.toNativeSeparators(filepath))

        mime.setData(
            'application/x-qt-windows-mime;value="FileNameW"',
            QtCore.QDir.toNativeSeparators(filepath))
        return mime

    def switch_dataset(self):
        """Swaps the dataset."""
        if not self._internal_data[self.get_location()][self.is_grouped()]:
            self.beginResetModel()
            self.__initdata__()
            self.endResetModel()
        self.internal_data = self._internal_data[self.get_location(
        )][self.is_grouped()]

    def set_asset(self, asset):
        if asset == self.asset:
            return
        self.asset = asset
        self.beginResetModel()
        self.__initdata__()
        self.switch_dataset()
        self.endResetModel()

    def is_grouped(self):
        """Gathers sequences into a single file."""
        location = self.get_location()
        if location == common.RendersFolder:
            return True

        if self._isgrouped is None:
            cls = self.__class__.__name__
            key = 'widget/{}/{}/isgroupped'.format(cls, location)
            val = local_settings.value(key)
            if val is None:
                self._isgrouped = False
            else:
                self._isgrouped = val
        return self._isgrouped

    def set_grouped(self, val):
        """Sets the groupping mode."""
        location = self.get_location()
        cls = self.__class__.__name__
        key = 'widget/{}/{}/isgroupped'.format(cls, location)
        cval = local_settings.value(key)

        if cval == val:
            return

        self.aboutToChange.emit()
        self._isgrouped = val
        local_settings.setValue(key, val)
        self.grouppingChanged.emit()

    def get_modes(self, asset, location):
        file_info = QtCore.QFileInfo('{asset}/{location}'.format(
            asset='/'.join(asset),
            location=location))
        if not file_info.exists():
            return []

        d = QtCore.QDir(file_info.filePath())
        d = d.entryList(
            filters=QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot,
        )
        d.append('')
        return sorted(d)

    def get_location(self):
        """Get's the current ``location``."""
        val = local_settings.value('activepath/location')
        if not val:
            local_settings.setValue('activepath/location', common.ScenesFolder)

        return val if val else common.ScenesFolder

    def set_location(self, val):
        """Sets the location and emits the ``activeLocationChanged`` signal."""
        key = 'activepath/location'
        cval = local_settings.value(key)

        if cval == val:
            return

        local_settings.setValue(key, val)
        self.activeLocationChanged.emit(val)

        # Updating the groupping
        cval = self.is_grouped()
        cls = self.__class__.__name__
        key = 'widget/{}/{}/isgroupped'.format(cls, val)
        val = local_settings.value(key)

        if cval == val:
            return

        self.aboutToChange.emit()
        self._isgrouped = val
        self.grouppingChanged.emit()


class FilesWidget(BaseInlineIconWidget):
    """Files widget is responsible for listing scene and project files of an asset.

    It relies on a custom collector class to gether the files requested.
    The scene files live in their respective root folder, usually ``scenes``.
    The first subfolder inside this folder will refer to the ``mode`` of the
    asset file.

    """

    def __init__(self, asset, parent=None):
        super(FilesWidget, self).__init__(FilesModel(asset), parent=parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self.setAcceptDrops(False)

        self.model().sourceModel().grouppingChanged.connect(self.model().invalidate)
        self.model().sourceModel().activeLocationChanged.connect(self.model().invalidate)

        self.setWindowTitle('Files')
        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self.context_menu_cls = FilesWidgetContextMenu

    def inline_icons_count(self):
        return 3

    def activate_current_index(self):
        """Sets the current item item as ``active`` and
        emits the ``activeLocationChanged`` and ``activeFileChanged`` signals.

        """
        if not super(FilesWidget, self).activate_current_index():
            return

        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        fileroot = index.data(common.ParentRole)[5]
        activefilepath = '{}/{}'.format(fileroot, file_info.fileName())
        local_settings.setValue('activepath/file', activefilepath)

        activefilepath = list(index.data(common.ParentRole)
                              ) + [file_info.fileName(), ]
        activefilepath = '/'.join(activefilepath)
        activefilepath = common.get_sequence_endpath(activefilepath)
        print activefilepath
        self.activeFileChanged.emit(activefilepath)

    def mouseDoubleClickEvent(self, event):
        """Custom double-click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double-click location before deciding what action to take.

        """
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)

        thumbnail_rect = QtCore.QRect(rect)
        thumbnail_rect.setWidth(rect.height())
        thumbnail_rect.moveLeft(common.INDICATOR_WIDTH)

        name_rect, _, metrics = self.itemDelegate().get_text_area(
            rect, common.PRIMARY_FONT)
        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))

        description_rect, _, metrics = self.itemDelegate().get_text_area(
            rect, common.SECONDARY_FONT)
        description_rect.moveTop(
            description_rect.top() + (description_rect.height() / 2.0))
        description_rect.setHeight(metrics.height())
        description_rect.moveTop(description_rect.top(
        ) - (description_rect.height() / 2.0) + metrics.lineSpacing())

        if description_rect.contains(event.pos()):
            widget = editors.DescriptionEditorWidget(index, parent=self)
            widget.show()
            return
        elif thumbnail_rect.contains(event.pos()):
            editors.ThumbnailEditor(index, parent=self)
            return

        self.activate_current_index()
        return


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    active_paths = path_monitor.get_active_paths()
    asset = (active_paths['server'],
             active_paths['job'],
             active_paths['root'],
             active_paths['asset'],
             )
    widget = FilesWidget(asset)
    widget.show()
    app.exec_()
