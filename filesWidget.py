# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the assets and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

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


class FilesModel(BaseModel):
    def __init__(self, asset, parent=None):
        self.asset = asset
        self.mode = None
        self.collapsed_data = {}

        super(FilesModel, self).__init__(parent=parent)

    def __initdata__(self):
        """To get the files, we will have to decide what extensions to take
        into consideration and what location to get the files from.

        Each asset should be made up of an `scenes`, `renders`, `textures` and
        `exports` folder. See the ``common`` module for definitions.

        """
        self.internal_data = {}  # reset
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
            file_info = QtCore.QFileInfo(it.next())
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
            if file_info.completeBaseName() == local_settings.value('activepath/file'):
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

            tooltip = u'{}\n'.format(file_info.completeBaseName().upper())
            tooltip += u'{}\n'.format(server.upper())
            tooltip += u'{}\n'.format(job.upper())
            tooltip += u'{}'.format(file_info.filePath())

            # Modes
            mode = file_info.path()  # parent folder
            mode = mode.replace('/'.join((server, job, root, asset, location)), '')
            mode = mode.strip('/')

            # File info
            info_string = '{day}/{month}/{year} {hour}:{minute}  {size}'.format(
                day=file_info.lastModified().toString('dd'),
                month=file_info.lastModified().toString('MM'),
                year=file_info.lastModified().toString('yyyy'),
                hour=file_info.lastModified().toString('hh'),
                minute=file_info.lastModified().toString('mm'),
                size=common.byte_to_string(file_info.size())
            )

            self.internal_data[idx] = {
                QtCore.Qt.DisplayRole: file_info.completeBaseName(),
                QtCore.Qt.EditRole: file_info.completeBaseName(),
                QtCore.Qt.StatusTipRole: file_info.filePath(),
                QtCore.Qt.ToolTipRole: tooltip,
                QtCore.Qt.SizeHintRole: QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT),
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
        self.asset = asset  # tuple(server,job,root,asset)

        self.setWindowTitle('Files')
        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self._context_menu_cls = FilesWidgetContextMenu

    def inline_icons_count(self):
        return 3

    def set_asset(self, asset):
        self.asset = asset
        self.refresh()

    def refresh(self):
        """Refreshes the list if files."""
        super(FilesWidget, self).refresh()

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
