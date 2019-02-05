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
from browser.settings import local_settings, Active
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
    """Model with the file-data associated with asset `locations` and
    groupping modes.

    The model stores information in the private `_model_data` dictionary. The items
    returned by the model are read from the `model_data`.

    Example:
        self.model_data = self._model_data[location][grouppingMode]

    """

    def __init__(self, asset, parent=None):
        self.asset = asset
        self.mode = None
        self._isgrouped = None

        super(FilesModel, self).__init__(parent=parent)
        self.switch_location_data()

        self.grouppingChanged.connect(self.switch_location_data)
        self.activeLocationChanged.connect(self.switch_location_data)
        self.modelDataResetRequested.connect(self.__resetdata__)

    @longprocess
    def __initdata__(self, spinner=None):
        """To get the files, we will have to decide what extensions to take
        into consideration and what location to get the files from.

        Each asset should be made up of an `scenes`, `renders`, `textures` and
        `exports` folder. See the ``common`` module for definitions.

        """
        location = self.get_location()
        active_paths = Active.get_active_paths()
        self._model_data[location] = {True: {}, False: {}}
        server, job, root, asset = self.asset

        if not all(self.asset):
            return

        self.modes = self.get_modes(self.asset, location)
        # Iterator
        dir_ = QtCore.QDir(u'{asset}/{location}'.format(
            asset=u'/'.join(self.asset),
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
                self._model_data[location][False][idx] = {
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
            fileroot = u'/'.join((server, job, root, asset, location))
            fileroot = it.fileInfo().path().replace(fileroot, u'')
            fileroot = fileroot.strip(u'/')

            activefilepath = u'{}/{}'.format(fileroot, it.fileName())
            if activefilepath == active_paths[u'file']:
                flags = flags | MarkedAsActive

            # Archived
            settings = AssetSettings((server, job, root, it.filePath()))
            if settings.value(u'config/archived'):
                flags = flags | MarkedAsArchived

            # Favourite
            favourites = local_settings.value(u'favourites')
            favourites = favourites if favourites else []
            if it.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            # Todos
            count = 0

            tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
            tooltip += u'{}'.format(it.filePath())

            # File info
            info_string = u'{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                day=it.fileInfo().lastModified().toString(u'dd'),
                month=it.fileInfo().lastModified().toString(u'MM'),
                year=it.fileInfo().lastModified().toString(u'yyyy'),
                hour=it.fileInfo().lastModified().toString(u'hh'),
                minute=it.fileInfo().lastModified().toString(u'mm'),
                size=common.byte_to_string(it.fileInfo().size())
            )

            self._model_data[location][False][idx] = {
                QtCore.Qt.DisplayRole: it.fileName(),
                QtCore.Qt.EditRole: it.fileName(),
                QtCore.Qt.StatusTipRole: it.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, fileroot),
                common.DescriptionRole: settings.value(u'config/description'),
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
        for k in self._model_data[location][False]:
            path = self._model_data[location][False][k][QtCore.Qt.StatusTipRole]

            match = common.get_sequence(path)
            if not match:  # Non-sequence items
                # Previously skipped all this, have to re-add the data here.
                if location == common.RendersFolder:
                    file_info = QtCore.QFileInfo(
                        self._model_data[location][False][k][QtCore.Qt.StatusTipRole])

                    # Active
                    fileroot = u'/'.join((server, job, root, asset, location))
                    fileroot = file_info.path().replace(fileroot, u'')
                    fileroot = fileroot.strip(u'/')

                    # Flags
                    flags = (
                        QtCore.Qt.ItemNeverHasChildren |
                        QtCore.Qt.ItemIsSelectable |
                        QtCore.Qt.ItemIsEnabled |
                        QtCore.Qt.ItemIsEditable |
                        QtCore.Qt.ItemIsDragEnabled
                    )

                    activefilepath = u'{}/{}'.format(fileroot,
                                                    file_info.fileName())
                    if activefilepath == active_paths[u'file']:
                        flags = flags | MarkedAsActive

                    # Archived
                    settings = AssetSettings(
                        (server, job, root, file_info.filePath()))
                    if settings.value(u'config/archived'):
                        flags = flags | MarkedAsArchived

                    # Favourite
                    favourites = local_settings.value(u'favourites')
                    favourites = favourites if favourites else []
                    if file_info.filePath() in favourites:
                        flags = flags | MarkedAsFavourite

                    # Todos
                    count = 0

                    tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
                    tooltip += u'{}'.format(file_info.filePath())

                    # File info
                    info_string = u'{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                        day=file_info.lastModified().toString(u'dd'),
                        month=file_info.lastModified().toString(u'MM'),
                        year=file_info.lastModified().toString(u'yyyy'),
                        hour=file_info.lastModified().toString(u'hh'),
                        minute=file_info.lastModified().toString(u'mm'),
                        size=common.byte_to_string(file_info.size())
                    )
                    self._model_data[location][True][idx] = {
                        QtCore.Qt.DisplayRole: file_info.fileName(),
                        QtCore.Qt.EditRole: file_info.fileName(),
                        QtCore.Qt.StatusTipRole: file_info.filePath(),
                        QtCore.Qt.ToolTipRole: u'Non-sequence item.',
                        QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                        common.FlagsRole: flags,
                        common.ParentRole: (server, job, root, asset, location, fileroot),
                        common.DescriptionRole: settings.value(u'config/description'),
                        common.TodoCountRole: count,
                        common.FileDetailsRole: info_string,
                    }
                    common.cache_image(
                        settings.thumbnail_path(),
                        common.ROW_HEIGHT - 2
                    )
                else:
                    # We can just use the previously collected data
                    self._model_data[location][True][idx] = self._model_data[location][False][k]
                idx += 1
                continue

            k = u'{}|{}.{}'.format(match.group(1), match.group(3), match.group(4))
            if k not in groups:
                file_info = QtCore.QFileInfo(path)
                groups[k] = {
                    u'path': path,
                    u'frames': [],
                    u'size': file_info.size(),
                    u'padding': len(match.group(2)),
                    u'modified': file_info.lastModified(),
                }
            groups[k][u'frames'].append(int(match.group(2)))

        # Adding the collapsed sequence items
        for k in groups:
            frames = groups[k][u'frames']
            frames = sorted(list(set(frames)))
            sk = k.split(u'|')
            path = u'{}[{}]{}'.format(
                sk[0],
                common.get_ranges(frames, groups[k][u'padding']),
                sk[1]
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
            fileroot = u'/'.join((server, job, root, asset, location))
            fileroot = file_info.path().replace(fileroot, u'')
            fileroot = fileroot.strip(u'/')
            activefilepath = u'{}/{}'.format(fileroot, file_info.fileName())
            if activefilepath == active_paths[u'file']:
                flags = flags | MarkedAsActive

            # Archived
            if settings.value(u'config/archived'):
                flags = flags | MarkedAsArchived

            # Favourite
            favourites = local_settings.value(u'favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            # Modes
            fileroot = u'/'.join((server, job, root, asset, location))
            fileroot = file_info.path().replace(fileroot, u'')
            fileroot = fileroot.strip(u'/')

            tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
            tooltip += u'{}'.format(file_info.filePath())

            # File info
            info_string = u'Sequence of {} files'.format(len(frames))

            tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
            tooltip += u'{}  (sequence)'.format(file_info.filePath())

            self._model_data[location][True][idx] = {
                QtCore.Qt.DisplayRole: file_info.fileName(),
                QtCore.Qt.EditRole: file_info.fileName(),
                QtCore.Qt.StatusTipRole: file_info.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, fileroot),
                common.DescriptionRole: settings.value(u'config/description'),
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
            u'application/x-qt-windows-mime;value="FileName"',
            QtCore.QDir.toNativeSeparators(filepath))

        mime.setData(
            u'application/x-qt-windows-mime;value="FileNameW"',
            QtCore.QDir.toNativeSeparators(filepath))
        return mime

    def switch_location_data(self):
        """Sets the location data stored in the private
        ``_model_data`` dictionary as the active model_data.

        """
        # When the dataset is empty, calling __initdata__
        if not self._model_data[self.get_location()][self.is_grouped()]:
            self.beginResetModel()
            self.__initdata__()
            self.endResetModel()

        self.model_data = self._model_data[self.get_location(
        )][self.is_grouped()]

    def set_asset(self, asset):
        """Sets a new asset for the model."""
        self.asset = asset

    def is_grouped(self):
        """Gathers sequences into a single file."""
        location = self.get_location()
        if location == common.RendersFolder:
            return True

        if self._isgrouped is None:
            cls = self.__class__.__name__
            key = u'widget/{}/{}/isgroupped'.format(cls, location)
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
        key = u'widget/{}/{}/isgroupped'.format(cls, location)
        cval = local_settings.value(key)

        if cval == val:
            return

        self.modelDataAboutToChange.emit()
        self._isgrouped = val
        local_settings.setValue(key, val)
        self.grouppingChanged.emit()

    def get_modes(self, asset, location):
        file_info = QtCore.QFileInfo(u'{asset}/{location}'.format(
            asset=u'/'.join(asset),
            location=location))
        if not file_info.exists():
            return []

        d = QtCore.QDir(file_info.filePath())
        d = d.entryList(
            filters=QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot,
        )
        d.append(u'')
        return sorted(d)

    def get_location(self):
        """Get's the current ``location``."""
        val = local_settings.value(u'activepath/location')
        if not val:
            local_settings.setValue(u'activepath/location', common.ScenesFolder)

        return val if val else common.ScenesFolder

    def set_location(self, val):
        """Sets the location and emits the ``activeLocationChanged`` signal."""
        key = u'activepath/location'
        cval = local_settings.value(key)

        if cval == val:
            return

        local_settings.setValue(key, val)
        self.activeLocationChanged.emit(val)

        # Updating the groupping
        cval = self.is_grouped()
        cls = self.__class__.__name__
        key = u'widget/{}/{}/isgroupped'.format(cls, val)
        val = local_settings.value(key)

        if cval == val:
            return

        self.modelDataAboutToChange.emit()
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

        self.setWindowTitle(u'Files')
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
        activefilepath = u'{}/{}'.format(fileroot, file_info.fileName())
        local_settings.setValue(u'activepath/file', activefilepath)

        activefilepath = list(index.data(common.ParentRole)
                              ) + [file_info.fileName(), ]
        activefilepath = u'/'.join(activefilepath)
        activefilepath = common.get_sequence_endpath(activefilepath)
        self.model().sourceModel().activeFileChanged.emit(activefilepath)

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
    active_paths = Active.get_active_paths()
    asset = (active_paths[u'server'],
             active_paths[u'job'],
             active_paths[u'root'],
             active_paths[u'asset'],
             )
    widget = FilesWidget(asset)
    widget.show()
    app.exec_()
