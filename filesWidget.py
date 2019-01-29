# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import re
import collections
import functools
from PySide2 import QtWidgets, QtCore

from mayabrowser.baselistwidget import BaseContextMenu
from mayabrowser.baselistwidget import BaseInlineIconWidget
from mayabrowser.baselistwidget import BaseModel

import mayabrowser.common as common
from mayabrowser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from mayabrowser.settings import AssetSettings
from mayabrowser.settings import local_settings, path_monitor
from mayabrowser.delegate import FilesWidgetDelegate
import mayabrowser.editors as editors


class FilesWidgetContextMenu(BaseContextMenu):
    """Context menu associated with FilesWidget."""

    def __init__(self, index, parent=None):
        super(FilesWidgetContextMenu, self).__init__(index, parent=parent)
        self.add_location_toggles_menu()
        self.add_collapse_sequence_menu()
        if index.isValid():
            self.add_thumbnail_menu()
        self.add_refresh_menu()

    def add_collapse_sequence_menu(self):
        """Adds the menu needed to change context"""
        if self.parent().model().sourceModel().get_location() == common.RendersFolder:
            return  # Render sequences are always collapsed

        expand_pixmap = common.get_rsc_pixmap(
            'expand', common.SECONDARY_TEXT, 18.0)
        collapse_pixmap = common.get_rsc_pixmap(
            'collapse', common.FAVOURITE, 18.0)

        collapsed = self.parent().model().sourceModel().is_grouped()

        menu_set = collections.OrderedDict()
        menu_set['separator'] = {}
        menu_set['collapse'] = {
            'text': 'Show individual files' if collapsed else 'Group sequences together',
            'icon': expand_pixmap if collapsed else collapse_pixmap,
            'checkable': True,
            'checked': collapsed,
            'action': (functools.partial(
                self.parent().model().sourceModel().set_grouped,
                not collapsed),
                self.parent().model().sort,
            )
        }

        self.create_menu(menu_set)

    def add_location_toggles_menu(self):
        """Adds the menu needed to change context"""
        locations_icon_pixmap = common.get_rsc_pixmap(
            'location', common.TEXT_SELECTED, 18.0)
        item_on_pixmap = common.get_rsc_pixmap(
            'item_on', common.TEXT_SELECTED, 18.0)
        item_off_pixmap = common.get_rsc_pixmap(
            'item_off', common.TEXT_SELECTED, 18.0)

        menu_set = collections.OrderedDict()
        menu_set['separator'] = {}

        key = 'Locations'

        menu_set[key] = collections.OrderedDict()
        menu_set['{}:icon'.format(key)] = locations_icon_pixmap

        for k in sorted(list(common.NameFilters)):
            checked = self.parent().get_location() == k
            menu_set[key][k] = {
                'text': 'Switch to  > {} <'.format(k.upper()),
                'checkable': True,
                'checked': checked,
                'icon': item_on_pixmap if checked else item_off_pixmap,
                'action': functools.partial(self.parent().set_location, k)
            }

        self.create_menu(menu_set)


class FilesModel(BaseModel):
    def __init__(self, asset, parent=None):
        self.asset = asset
        self.mode = None
        super(FilesModel, self).__init__(parent=parent)
        self.switch_dataset()

    def __initdata__(self):
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
            dir_,
            flags=QtCore.QDirIterator.Subdirectories,
        )

        idx = 0
        config_dir_paths = {}

        while it.hasNext():
            path = it.next()
            mode = it.fileInfo().path().replace(
                '/'.join((server, job, root, asset, location)), '')
            mode = mode.strip('/')

            # Flags
            flags = (
                QtCore.Qt.ItemNeverHasChildren |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable |
                QtCore.Qt.ItemIsDragEnabled
            )
            # We're not going to set more data if looking inside the renders
            # folder as the number of files querried can be huge.
            if location == common.RendersFolder:
                self._internal_data[location][False][idx] = {
                    int(QtCore.Qt.StatusTipRole): path
                }
                idx += 1
                continue

            settings = AssetSettings((server, job, root, it.filePath()))
            if it.path() not in config_dir_paths:
                config_dir_paths[it.path()] = QtCore.QFileInfo(
                    settings.conf_path()).path()

            # Active
            if it.fileName() == active_paths['file']:
                flags = flags | MarkedAsActive

            # Archived
            if settings.value('config/archived'):
                flags = flags | MarkedAsArchived

            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if it.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            # Todos
            count = 0

            tooltip = u'{} | {} | {}\n'.format(job, root, mode)
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
                common.ParentRole: (server, job, root, asset, location, mode),
                common.DescriptionRole: settings.value('config/description'),
                common.TodoCountRole: count,
                common.FileDetailsRole: info_string,
            }

            common.cache_image(
                settings.thumbnail_path(),
                common.ROW_HEIGHT - 2
            )

            idx += 1

        # Creating directories for the settings
        for k in config_dir_paths:
            if QtCore.QFileInfo(config_dir_paths[k]).exists():
                continue
            QtCore.QDir().mkpath(config_dir_paths[k])


        # Regex responsible for identifying sequences
        r = re.compile(r'^(.*?)([0-9]+)\.(.{2,5})$')

        # Getting unique sequence groups
        groups = {}
        idx = 0
        for k in self._internal_data[location][False]:
            path = self._internal_data[location][False][k][QtCore.Qt.StatusTipRole]
            match = r.search(path)
            if not match:
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
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable
            )

            # Active
            if file_info.fileName() == active_paths['file']:
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
            mode = file_info.path()  # parent folder
            mode = mode.replace(
                '/'.join((server, job, root, asset, location)), '')
            mode = mode.strip('/')

            tooltip = u'{} | {} | {}\n'.format(job, root, mode)
            tooltip += u'{}'.format(file_info.filePath())

            # File info
            info_string = 'Sequence of {} files'.format(len(frames))

            tooltip = u'{} | {} | {}\n'.format(job, root, mode)
            tooltip += u'{}  (sequence)'.format(file_info.filePath())

            self._internal_data[location][True][idx] = {
                QtCore.Qt.DisplayRole: file_info.fileName(),
                QtCore.Qt.EditRole: file_info.fileName(),
                QtCore.Qt.StatusTipRole: file_info.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ROW_HEIGHT),
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, mode),
                common.DescriptionRole: settings.value('config/description'),
                common.TodoCountRole: 0,
                common.FileDetailsRole: info_string,
            }

            common.cache_image(
                settings.thumbnail_path(),
                common.ROW_HEIGHT - 2
            )

            idx += 1


    def switch_dataset(self):
        """Swaps the dataset."""
        self.beginResetModel()
        self.internal_data = self._internal_data[self.get_location()][self.is_grouped()]
        self.endResetModel()

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
        if self.get_location() == common.RendersFolder:
            return True

        cls = self.__class__.__name__
        key = 'widget/{}/groupfiles'.format(cls)
        val = local_settings.value(key)
        return val if val else False

    def set_grouped(self, val):
        cls = self.__class__.__name__
        key = 'widget/{}/groupfiles'.format(cls)
        local_settings.setValue(key, val)
        self.switch_dataset()

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
        return val if val else common.ScenesFolder

    def set_location(self, val):
        """Sets the location and emits the ``activeLocationChanged`` signal."""
        key = 'activepath/location'
        cval = local_settings.value(key)

        if cval == val:
            return

        local_settings.setValue(key, val)
        self.activeLocationChanged.emit(val)

        self.beginResetModel()
        self.__initdata__()
        self.endResetModel()


class FilesWidget(BaseInlineIconWidget):
    """Files widget is responsible for listing scene and project files of an asset.

    It relies on a custom collector class to gether the files requested.
    The scene files live in their respective root folder, usually ``scenes``.
    The first subfolder inside this folder will refer to the ``mode`` of the
    asset file.

    Signals:

    """
    # Signals
    fileOpened = QtCore.Signal(str)
    fileSaved = QtCore.Signal(str)
    fileImported = QtCore.Signal(str)
    fileReferenced = QtCore.Signal(str)

    def __init__(self, asset, parent=None):
        super(FilesWidget, self).__init__(FilesModel(asset), parent=parent)
        self.setWindowTitle('Files')
        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self._context_menu_cls = FilesWidgetContextMenu

    def inline_icons_count(self):
        return 3

    def get_location(self):
        """Get's the current file ``location``.

        See the ``common`` module forpossible values but generally this refers
        to either to `scenes`, `textures`, `renders` or `exports folder.`

        """
        val = local_settings.value('activepath/location')
        return val if val else common.ScenesFolder

    def set_location(self, val):
        """Sets the location and emits the ``activeLocationChanged`` signal."""
        key = 'activepath/location'
        cval = local_settings.value(key)

        if cval == val:
            return

        local_settings.setValue(key, val)
        self.activeLocationChanged.emit(val)

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
