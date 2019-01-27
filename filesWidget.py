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
from mayabrowser.settings import local_settings
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
        self._internal_data = {}
        self.collapsed_data = {}
        super(FilesModel, self).__init__(parent=parent)
        self.switch_dataset()

    def __initdata__(self):
        """To get the files, we will have to decide what extensions to take
        into consideration and what location to get the files from.

        Each asset should be made up of an `scenes`, `renders`, `textures` and
        `exports` folder. See the ``common`` module for definitions.

        """
        self.internal_data = {}
        self._internal_data = {}  # reset
        self.collapsed_data = {}  # reset
        self.modes = None

        server, job, root, asset = self.asset
        if not all(self.asset):
            return

        location = self.get_location()
        file_info = QtCore.QFileInfo('{asset}/{location}'.format(
            asset='/'.join(self.asset),
            location=location
        ))

        if not file_info.exists():
            return

        self.modes = self.get_modes(self.asset, location)

        it = QtCore.QDirIterator(
            file_info.filePath(),
            common.NameFilters[location],
            flags=QtCore.QDirIterator.Subdirectories,
            filters=QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Files |
            QtCore.QDir.NoSymLinks
        )

        idx = 0
        config_dir_paths = {}
        while it.hasNext():
            path = it.next()
            if location == common.RendersFolder:
                self._internal_data[idx] = {
                    QtCore.Qt.StatusTipRole: path
                }
                idx += 1
                continue

            file_info = QtCore.QFileInfo(path)
            settings = AssetSettings((server, job, root, file_info.filePath()))
            if file_info.path() not in config_dir_paths:
                config_dir_paths[file_info.path()] = QtCore.QFileInfo(
                    settings.conf_path()).path()

            # Flags
            flags = (
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable
            )

            # Active
            if file_info.fileName() == local_settings.value('activepath/file'):
                flags = flags | MarkedAsActive

            # Archived
            if settings.value('config/archived'):
                flags = flags | MarkedAsArchived

            # Favourite
            favourites = local_settings.value('favourites')
            favourites = favourites if favourites else []
            if file_info.filePath() in favourites:
                flags = flags | MarkedAsFavourite

            # Todos
            count = 0

            # Modes
            mode = file_info.path()  # parent folder
            mode = mode.replace(
                '/'.join((server, job, root, asset, location)), '')
            mode = mode.strip('/')

            tooltip = u'{} | {} | {}\n'.format(job, root, mode)
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

            self._internal_data[idx] = {
                QtCore.Qt.DisplayRole: file_info.fileName(),
                QtCore.Qt.EditRole: file_info.fileName(),
                QtCore.Qt.StatusTipRole: file_info.filePath(),
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

        self.__init_collapseddata__()

    def __init_collapseddata__(self):
        self.collapsed_data = {}
        r = re.compile(r'^(.*?)([0-9]+)\.(.{2,5})$')

        server, job, root, asset = self.asset
        location = self.get_location()

        # Getting unique sequence groups
        groups = {}
        idx = 0
        for k in self._internal_data:
            path = self._internal_data[k][QtCore.Qt.StatusTipRole]
            match = r.search(path)
            if not match:
                self.collapsed_data[idx] = self._internal_data[k]
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
            # print settings.conf_path()

            # Flags
            flags = (
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsEditable
            )

            # Active
            if file_info.fileName() == local_settings.value('activepath/file'):
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

            self.collapsed_data[idx] = {
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
        if self.is_grouped():
            self.internal_data = self.collapsed_data
        else:
            self.internal_data = self._internal_data
        self.endResetModel()


    def set_asset(self, asset):
        self.asset = asset
        self.beginResetModel()
        self.__initdata__()
        self.endResetModel()
        self.switch_dataset()

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
        self.switch_dataset()


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

    def refresh(self):
        super(FilesWidget, self).refresh()
        self.model().sourceModel().switch_dataset()

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
        else:
            self.activate_current_index()
            return


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    path = (local_settings.value('activepath/server'),
            local_settings.value('activepath/job'),
            local_settings.value('activepath/root'),
            local_settings.value('activepath/asset'))

    widget = FilesWidget(path)

    widget.show()
    app.exec_()
