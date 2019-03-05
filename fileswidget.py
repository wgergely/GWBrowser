# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101
import time

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
from browser.imagecache import ImageCache


class ModelWorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    update = QtCore.Signal(unicode)


class ModelWorker(QtCore.QRunnable):
    """Generic QRunnable, taking an index as it's first argument."""

    def __init__(self, chunk):
        super(ModelWorker, self).__init__()
        self.chunk = chunk
        self.signals = ModelWorkerSignals()

    @QtCore.Slot()
    def run(self):
        """The main work method run in a secondary thread."""
        for index in self.chunk:
            filename = QtCore.QFileInfo(index.data(
                QtCore.Qt.StatusTipRole)).fileName()
            self.signals.update.emit(u'Processing {}'.format(filename.encode('utf-8')))
            ImageCache.generate(index)
        self.signals.finished.emit()


class FilesWidgetContextMenu(BaseContextMenu):
    """Context menu associated with FilesWidget."""

    def __init__(self, index, parent=None):
        super(FilesWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions
        self.add_location_toggles_menu()

        self.add_separator()

        if index.isValid():
            self.add_mode_toggles_menu()
            self.add_thumbnail_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_folder_menu()
            self.add_copy_menu()

        self.add_separator()

        self.add_sort_menu()
        self.add_collapse_sequence_menu()
        self.add_display_toggles_menu()

        self.add_separator()

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

        # This will add the asset to the file monitor
        self.set_asset(asset)

    def __initdata__(self):
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

        # File monitor
        self._file_monitor.addPath('{}/{}/{}/{}/{}'.format(
            server, job, root, asset, location))

        # Iterator
        dir_ = QtCore.QDir(u'{asset}/{location}'.format(
            asset=u'/'.join(self.asset),
            location=location
        ))
        if not dir_.exists():
            return
        dir_.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dir_.setSorting(QtCore.QDir.Unsorted)

        if location in common.NameFilters:
            dir_.setNameFilters(common.NameFilters[location])
        else:
            dir_.setNameFilters((u'*.*',))

        it = QtCore.QDirIterator(
            dir_, flags=QtCore.QDirIterator.Subdirectories)

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        idx = 0
        __count = 0
        __nth = 300

        while it.hasNext():
            path = it.next()
            # Collecting files can take a long time. We're triggering ui updates inside loop here.
            __count += 1
            if ((__count % __nth) + 1) == __nth:
                common.ProgressMessage.instance().set_message(path)

            # We're not going to set more data when looking inside the ``renders`` location.
            # Things can slow down when querrying 10000s of files.
            if location == common.RendersFolder:
                self._model_data[location][False][idx] = {
                    int(QtCore.Qt.StatusTipRole): path,
                    int(common.FlagsRole): QtCore.Qt.NoItemFlags
                }
                idx += 1
                continue

            file_info = it.fileInfo()
            filename = file_info.fileName()
            filepath = file_info.filePath()
            last_modified = file_info.lastModified()
            size = file_info.size()

            # Flags
            flags, settings, fileroot = self.__flags(favourites,
                active_paths,
                server, job, root, asset, location,
                file_info.path(), filepath, filename
            )

            # Todos
            count = 0

            # Tooltip
            tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
            tooltip += u'{}'.format(filepath)

            # File info
            info_string = u'{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                day=last_modified.toString(u'dd'),
                month=last_modified.toString(u'MM'),
                year=last_modified.toString(u'yyyy'),
                hour=last_modified.toString(u'hh'),
                minute=last_modified.toString(u'mm'),
                size=common.byte_to_string(size)
            )

            self._model_data[location][False][idx] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, fileroot),
                common.DescriptionRole: settings.value(u'config/description'),
                common.TodoCountRole: 0,
                common.FileDetailsRole: info_string,
            }
            idx += 1
            ImageCache.instance().get(settings.thumbnail_path(), common.ROW_HEIGHT - 2)

        self.__collapseddata(favourites, active_paths, server, job, root, asset, location)

    def __collapseddata(self, favourites, active_paths, server, job, root, asset, location):
        """Populates the model data with the information needed to display file
        sequences.

        """
        groups = {}
        idx = 0
        for k in self._model_data[location][False]:
            path = self._model_data[location][False][k][QtCore.Qt.StatusTipRole]
            match = common.get_sequence(path)
            if not match:  # Non-sequence items
                # Previously skipped getting information for render-files
                if location == common.RendersFolder:
                    file_info = QtCore.QFileInfo(path)
                    filename = file_info.fileName()
                    filepath = file_info.filePath()
                    last_modified = file_info.lastModified()
                    size = file_info.size()

                    # Flags
                    flags, settings, fileroot = self.__flags(favourites,
                        active_paths,
                        server, job, root, asset, location,
                        file_info.path(), filepath, filename
                    )

                    # Todos
                    count = 0

                    # Tooltip
                    tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
                    tooltip += u'{}'.format(filepath)

                    # File description
                    info_string = u'{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                        day=last_modified.toString(u'dd'),
                        month=last_modified.toString(u'MM'),
                        year=last_modified.toString(u'yyyy'),
                        hour=last_modified.toString(u'hh'),
                        minute=last_modified.toString(u'mm'),
                        size=common.byte_to_string(size)
                    )
                    self._model_data[location][True][idx] = {
                        QtCore.Qt.DisplayRole: filename,
                        QtCore.Qt.EditRole: filename,
                        QtCore.Qt.StatusTipRole: filepath,
                        QtCore.Qt.ToolTipRole: u'Non-sequence item.',
                        QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                        common.FlagsRole: flags,
                        common.ParentRole: (server, job, root, asset, location, fileroot),
                        common.DescriptionRole: settings.value(u'config/description'),
                        common.TodoCountRole: count,
                        common.FileDetailsRole: info_string,
                    }
                    ImageCache.instance().get(settings.thumbnail_path(), common.ROW_HEIGHT - 2)
                else:
                    # If the item is not a sequence we can just use the previously
                    # collected item
                    self._model_data[location][True][idx] = self._model_data[location][False][k]

                idx += 1
                continue

            k = u'{}|{}.{}'.format(match.group(
                1), match.group(3), match.group(4))
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
            __path = u'{}{}{}'.format(
                sk[0],
                u'{}'.format(frames[0]).zfill(groups[k][u'padding']),
                sk[1]
            )

            file_info = QtCore.QFileInfo(path)
            filename = file_info.fileName()
            filepath = file_info.filePath()

            # Flags
            flags, settings, fileroot = self.__flags(favourites, 
                active_paths,
                server, job, root, asset, location,
                file_info.path(), filepath, filename
            )

            # File info string
            info_string = u'Sequence of {} files'.format(len(frames))

            tooltip = u'{} | {} | {}\n'.format(job, root, fileroot)
            tooltip += u'{}  (sequence)'.format(filepath)

            self._model_data[location][True][idx] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, fileroot),
                common.DescriptionRole: settings.value(u'config/description'),
                common.TodoCountRole: 0,
                common.FileDetailsRole: info_string,
            }
            idx += 1
            ImageCache.instance().get(settings.thumbnail_path(), common.ROW_HEIGHT - 2)
            #
            if file_info.path() not in self._file_monitor.directories():
                self._file_monitor.addPath(file_info.path())

        # file-monitor timestamp
        self._last_refreshed[self.get_location()] = time.time()

    @staticmethod
    def __flags(favourites, active_paths, server, job, root, asset, location, path, filepath, filename):
        """Private convenicen function for getting the flag values of a file."""
        settings = AssetSettings((server, job, root, filepath))
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
        fileroot = path.replace(fileroot, u'')
        fileroot = fileroot.strip(u'/')

        activefilepath = u'{}/{}'.format(fileroot, filename)
        if activefilepath == active_paths[u'file']:
            flags = flags | MarkedAsActive

        # Archived
        if settings.value(u'config/archived'):
            flags = flags | MarkedAsArchived

        # Favourite
        if filepath in favourites:
            flags = flags | MarkedAsFavourite

        return flags, settings, fileroot

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
        else:
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
        location = self.get_location()
        if not location in self._model_data:
            self._model_data[location] = {True: {}, False: {}, }
        if not self._model_data[location][self.is_grouped()]:
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

    def get_location(self):
        """Get's the current ``location``."""
        val = local_settings.value(u'activepath/location')
        if not val:
            local_settings.setValue(
                u'activepath/location', common.ScenesFolder)

        return val if val else common.ScenesFolder

    def set_location(self, val):
        """Sets the location and emits the ``activeLocationChanged`` signal."""
        key = u'activepath/location'
        cval = local_settings.value(key)

        if cval == val:
            return

        local_settings.setValue(key, val)
        self.activeLocationChanged.emit(val)

        # Updating the groupping of the files
        cls = self.__class__.__name__
        key = u'widget/{}/{}/isgroupped'.format(cls, val)
        groupped = True if local_settings.value(key) else False

        if self.is_grouped() == groupped:
            return

        self.modelDataAboutToChange.emit()
        self._isgrouped = groupped
        self.grouppingChanged.emit()


class FilesWidget(BaseInlineIconWidget):
    """Files widget is responsible for listing scene and project files of an asset.

    It relies on a custom collector class to gether the files requested.
    The scene files live in their respective root folder, usually ``scenes``.
    The first subfolder inside this folder will refer to the ``mode`` of the
    asset file.

    """

    itemDoubleClicked = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, asset, parent=None):
        super(FilesWidget, self).__init__(parent=parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self.setAcceptDrops(False)

        self.setWindowTitle(u'Files')
        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self.context_menu_cls = FilesWidgetContextMenu
        self.set_model(FilesModel(asset))

    def eventFilter(self, widget, event):
        super(FilesWidget, self).eventFilter(widget, event)
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            # Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                'files', QtGui.QColor(0, 0, 0, 10), 200)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True
        return False

    def inline_icons_count(self):
        return 3

    def action_on_enter_key(self):
        index = self.selectionModel().currentIndex()
        self.itemDoubleClicked.emit(index)

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

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        name_rect = QtCore.QRect(rect)
        name_rect.setLeft(
            common.INDICATOR_WIDTH +
            name_rect.height() +
            common.MARGIN
        )
        name_rect.setRight(name_rect.right() - common.MARGIN)
        #
        description_rect = QtCore.QRect(name_rect)
        #
        name_rect.moveTop(name_rect.top() + (name_rect.height() / 2.0))
        name_rect.setHeight(metrics.height())
        name_rect.moveTop(name_rect.top() - (name_rect.height() / 2.0))
        #
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
            ImageCache.instance().pick(index)
            return

        # self.activate_current_index()
        self.itemDoubleClicked.emit(index)


# if __name__ == '__main__':
#     app = QtWidgets.QApplication([])
#     active_paths = Active.get_active_paths()
#     asset = (active_paths[u'server'],
#              active_paths[u'job'],
#              active_paths[u'root'],
#              active_paths[u'asset'],
#              )
#     widget = FilesWidget(asset)
#     widget.show()
#     app.exec_()
