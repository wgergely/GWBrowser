# -*- coding: utf-8 -*-
"""The base-context menu associated with the BaseListWidget subclasses."""

import functools
import collections

from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.common as common
import bookmarks.images as images


def contextmenu(func):
    """Decorator to create a menu set."""
    @functools.wraps(func)
    def func_wrapper(self, *args, **kwargs):
        """Wrapper for function."""
        menu_set = collections.OrderedDict()
        menu_set = func(self, menu_set, *args, **kwargs)
        if not isinstance(menu_set, collections.OrderedDict):
            raise ValueError(
                u'Invalid return type from context menu function, expected an OrderedDict, got {}'.format(type(menu_set)))
        self.create_menu(menu_set)
        return menu_set
    return func_wrapper


class BaseContextMenu(QtWidgets.QMenu):
    """Custom context menu associated with the BaseListWidget.
    The menu and the actions are always associated with a ``QModelIndex``
    from the list widget.

    The menu structure is defined by key/value pares stored in an OrderedDict.

    Properties:
        index (QModelIndex): The index the context menu is associated with.

    Methods:
        create_menu():  Populates the menu with actions based on the ``menu_set`` given.

    """

    def __init__(self, index, parent=None):
        super(BaseContextMenu, self).__init__(parent=parent)
        common.set_custom_stylesheet(self)
        self.index = index
        self.setToolTipsVisible(False)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    @contextmenu
    def add_separator(self, menu_set):
        menu_set[u'separator'] = None
        return menu_set

    def create_menu(self, menu_set, parent=None):
        """This action populates the menu using the action-set dictionaries,
        and it automatically connects the action with a corresponding method based
        on the key/method-name.

        Args:
            menu_set (OrderedDict):    The set of menu items. See keys below.
            parent (QMenu):

        Implemented keys:
            action_set[k][u'action'] (bool): The action to execute when the item is clicked.
            action_set[k][u'text'] (str): The action's text
            action_set[k][u'data'] (object): User data stored in the action
            action_set[k][u'disabled'] (bool): Sets wheter the item is disabled.
            action_set[k][u'tool_tip'] (str):The description of the action.
            action_set[k][u'status_tip'] (str): The description of the action.
            action_set[k][u'icon'] (QPixmap): The action's icon.
            action_set[k][u'shortcut'] (QKeySequence): The action's icon.
            action_set[k][u'checkable'] (bool): Sets wheter the item is checkable.
            action_set[k][u'checked'] (bool): The state of the checkbox.
            action_set[k][u'visible'] (bool): The visibility of the action.

        """
        if not parent:
            parent = self

        for k in menu_set:
            if u':' in k:  # Skipping `speudo` keys
                continue

            # Recursive menu creation
            if isinstance(menu_set[k], collections.OrderedDict):
                parent = QtWidgets.QMenu(k, parent=self)
                if u'{}:icon'.format(k) in menu_set:
                    icon = QtGui.QIcon(menu_set[u'{}:icon'.format(k)])
                    parent.setIcon(icon)
                if u'{}:text'.format(k) in menu_set:
                    parent.setTitle(menu_set[u'{}:text'.format(k)])
                if u'{}:action'.format(k) in menu_set:
                    name = menu_set[u'{}:text'.format(k)] if u'{}:text'.format(
                        k) in menu_set else k
                    icon = menu_set[u'{}:icon'.format(k)] if u'{}:icon'.format(
                        k) in menu_set else QtGui.QPixmap()
                    action = parent.addAction(name)
                    action.setIconVisibleInMenu(True)
                    action.setIcon(icon)

                    if isinstance(menu_set[u'{}:action'.format(k)], collections.Iterable):
                        for func in menu_set[u'{}:action'.format(k)]:
                            action.triggered.connect(func)
                    else:
                        action.triggered.connect(
                            menu_set[u'{}:action'.format(k)])
                    parent.addAction(action)
                    parent.addSeparator()

                self.addMenu(parent)
                self.create_menu(menu_set[k], parent=parent)
                continue

            if u'separator' in k:
                parent.addSeparator()
                continue

            action = parent.addAction(k)

            if u'data' in menu_set[k]:  # Skipping disabled items
                action.setData(menu_set[k][u'data'])
            if u'disabled' in menu_set[k]:  # Skipping disabled items
                action.setDisabled(menu_set[k][u'disabled'])
            if u'action' in menu_set[k]:
                if isinstance(menu_set[k][u'action'], collections.Iterable):
                    for func in menu_set[k][u'action']:
                        action.triggered.connect(func)
                else:
                    action.triggered.connect(menu_set[k][u'action'])
            if u'text' in menu_set[k]:
                action.setText(menu_set[k][u'text'])
            else:
                action.setText(k)
            if u'status_tip' in menu_set[k]:
                action.setStatusTip(menu_set[k][u'status_tip'])
            if u'tool_tip' in menu_set[k]:
                action.setToolTip(menu_set[k][u'tool_tip'])
            if u'checkable' in menu_set[k]:
                action.setCheckable(menu_set[k][u'checkable'])
            if u'checked' in menu_set[k]:
                action.setChecked(menu_set[k][u'checked'])
            if u'icon' in menu_set[k]:
                action.setIconVisibleInMenu(True)
                action.setIcon(menu_set[k][u'icon'])
            if u'shortcut' in menu_set[k]:
                action.setShortcut(menu_set[k][u'shortcut'])
            if u'visible' in menu_set[k]:
                action.setVisible(menu_set[k][u'visible'])
            else:
                action.setVisible(True)

    def showEvent(self, event):
        """Elides the action text to fit the size of the widget upon showing."""
        for action in self.actions():
            if not action.text():
                continue

            metrics = QtGui.QFontMetricsF(self.font())
            text = metrics.elidedText(
                action.text(),
                QtCore.Qt.ElideMiddle,
                self.width()  # padding set in the stylesheet
            )
            action.setText(text)

    @contextmenu
    def add_sort_menu(self, menu_set):
        """Creates the menu needed to set the sort-order of the list."""
        sort_menu_icon = images.ImageCache.get_rsc_pixmap(
            u'sort', common.SECONDARY_TEXT, common.MARGIN)
        arrow_up_icon = images.ImageCache.get_rsc_pixmap(
            u'arrow_up', common.SECONDARY_TEXT, common.MARGIN)
        arrow_down_icon = images.ImageCache.get_rsc_pixmap(
            u'arrow_down', common.SECONDARY_TEXT, common.MARGIN)

        item_on_icon = images.ImageCache.get_rsc_pixmap(
            u'check', common.ADD, common.MARGIN)

        m = self.parent().model().sourceModel()
        sortorder = m.sort_order()
        sortrole = m.sort_role()

        sort_by_name = sortrole == common.SortByName
        sort_modified = sortrole == common.SortByLastModified
        sort_size = sortrole == common.SortBySize

        menu_set[u'Sort'] = collections.OrderedDict()

        menu_set[u'Sort:icon'] = sort_menu_icon
        menu_set[u'Sort'][u'Order'] = {
            u'text': u'Ascending' if not sortorder else u'Descending',
            u'checkable': False,
            # u'checked': not sortorder,
            u'icon': arrow_down_icon if not sortorder else arrow_up_icon,
            u'action': lambda: m.sortingChanged.emit(sortrole, not sortorder)
        }

        menu_set[u'Sort'][u'separator'] = {}

        menu_set[u'Sort'][u'Name'] = {
            u'icon': item_on_icon if sort_by_name else QtGui.QPixmap(),
            # u'ckeckable': True,
            # u'checked': True if sort_by_name else False,
            u'action': lambda: m.sortingChanged.emit(common.SortByName, sortorder)
        }
        menu_set[u'Sort'][u'Date modified'] = {
            u'icon': item_on_icon if sort_modified else QtGui.QPixmap(),
            # u'ckeckable': True,
            # u'checked': True if sort_modified else False,
            u'action': lambda: m.sortingChanged.emit(common.SortByLastModified, sortorder)
        }
        menu_set[u'Sort'][u'Size'] = {
            u'icon': item_on_icon if sort_size else QtGui.QPixmap(),
            # u'ckeckable': True,
            # u'checked': True if sort_size else False,
            u'action': lambda: m.sortingChanged.emit(common.SortBySize, sortorder)
        }
        return menu_set

    @contextmenu
    def add_reveal_item_menu(self, menu_set):
        """Creates a menu containing"""
        if not self.index.isValid():
            return menu_set

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN)

        path = common.get_sequence_startpath(
            self.index.data(QtCore.Qt.StatusTipRole))
        menu_set['Show in file manager'] = {
            u'icon': pixmap,
            u'action': functools.partial(common.reveal, path)
        }
        return menu_set

    @contextmenu
    def add_rv_menu(self, menu_set):
        """Creates a menu containing"""
        if not self.index.isValid():
            return menu_set
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', common.SECONDARY_TEXT, common.MARGIN)

        path = common.get_sequence_startpath(
            self.index.data(QtCore.Qt.StatusTipRole))
        menu_set['Push to RV'] = {
            u'icon': pixmap,
            u'action': lambda: common.push_to_rv(path)
        }
        return menu_set

    @contextmenu
    def add_copy_menu(self, menu_set):
        """Menu containing the subfolders of the selected item."""

        if not self.index.isValid():
            return menu_set

        copy_icon = images.ImageCache.get_rsc_pixmap(
            u'copy', common.SECONDARY_TEXT, common.MARGIN)
        copy_icon2 = images.ImageCache.get_rsc_pixmap(
            u'copy', common.SECONDARY_TEXT, common.MARGIN)

        key = u'Copy path'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = copy_icon

        path = self.index.data(QtCore.Qt.StatusTipRole)
        menu_set[key][u'windows1'] = {
            u'text': u'Windows:  {}'.format(
                common.copy_path(path, mode=common.WindowsPath, copy=False)),
            u'icon': copy_icon2,
            u'action': functools.partial(
                common.copy_path,
                path,
                mode=common.WindowsPath)
        }
        menu_set[key][u'unix'] = {
            u'text': u'Unix:  {}'.format(
                common.copy_path(path, mode=common.UnixPath, copy=False)),
            u'icon': copy_icon2,
            u'action': functools.partial(
                common.copy_path,
                path,
                mode=common.UnixPath
            )
        }
        menu_set[key][u'slack'] = {
            u'text': u'URL:  {}'.format(
                common.copy_path(path, mode=common.SlackPath, copy=False)),
            u'icon': copy_icon2,
            u'action': functools.partial(
                common.copy_path,
                path,
                mode=common.SlackPath
            )
        }
        menu_set[key][u'macos'] = {
            u'text': u'SMB:  {}'.format(
                common.copy_path(path, mode=common.MacOSPath, copy=False)),
            u'icon': copy_icon2,
            u'action': functools.partial(
                common.copy_path,
                path,
                mode=common.MacOSPath
            )
        }

        menu_set[key][u'separator+'] = {}

        path = QtCore.QFileInfo(path).dir().path()
        menu_set[key][u'parent_windows1'] = {
            u'text': u'Windows:  {}'.format(
                common.copy_path(path, mode=common.WindowsPath, copy=False)),
            u'icon': copy_icon2,
            u'action': functools.partial(
                common.copy_path,
                path,
                mode=common.WindowsPath)
        }
        menu_set[key][u'parent_unix'] = {
            u'text': u'Unix:  {}'.format(
                common.copy_path(path, mode=common.UnixPath, copy=False)),
            u'icon': copy_icon2,
            u'action': functools.partial(
                common.copy_path,
                path,
                mode=common.UnixPath
            )
        }
        menu_set[key][u'parent_slack'] = {
            u'text': u'URL:  {}'.format(
                common.copy_path(path, mode=common.SlackPath, copy=False)),
            u'icon': copy_icon2,
            u'action': functools.partial(
                common.copy_path,
                path,
                mode=common.SlackPath
            )
        }
        menu_set[key][u'parent_macos'] = {
            u'text': u'SMB:  {}'.format(
                common.copy_path(path, mode=common.MacOSPath, copy=False)),
            u'icon': copy_icon2,
            u'action': functools.partial(
                common.copy_path,
                path,
                mode=common.MacOSPath
            )
        }
        return menu_set

    @contextmenu
    def add_mode_toggles_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        favourite_on_icon = images.ImageCache.get_rsc_pixmap(
            u'favourite', common.SECONDARY_TEXT, common.MARGIN)
        favourite_off_icon = images.ImageCache.get_rsc_pixmap(
            u'favourite', common.SECONDARY_TEXT, common.MARGIN)
        archived_on_icon = images.ImageCache.get_rsc_pixmap(
            u'archived', common.SECONDARY_TEXT, common.MARGIN)
        archived_off_icon = images.ImageCache.get_rsc_pixmap(
            u'archived', common.SECONDARY_TEXT, common.MARGIN)

        favourite = self.index.flags() & common.MarkedAsFavourite
        archived = self.index.flags() & common.MarkedAsArchived

        pixmap = archived_off_icon if archived else archived_on_icon
        if self.__class__.__name__ == u'BookmarksWidgetContextMenu':
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'remove', common.REMOVE, common.MARGIN)
            text = u'Remove'
        else:
            text = u'Restore' if archived else u'Archive'
        menu_set[u'archived'] = {
            u'text': text,
            u'icon': pixmap,
            u'checkable': False,
            u'action': functools.partial(
                self.parent().toggle_item_flag,
                self.index,
                common.MarkedAsArchived,
                state=not archived
            )
        }
        menu_set[u'favourite'] = {
            u'text': u'Remove favourite' if favourite else u'Favourite',
            u'icon': favourite_off_icon if favourite else favourite_on_icon,
            u'checkable': False,
            u'action': functools.partial(
                self.parent().toggle_item_flag,
                self.index,
                common.MarkedAsFavourite,
                state=not favourite
            )
        }
        return menu_set

    @contextmenu
    def add_display_toggles_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        item_on = images.ImageCache.get_rsc_pixmap(
            u'check', common.ADD, common.MARGIN)
        item_off = images.ImageCache.get_rsc_pixmap(
            u'active', common.SECONDARY_TEXT, common.MARGIN)

        proxy = self.parent().model()
        favourite = proxy.filter_flag(common.MarkedAsFavourite)
        archived = proxy.filter_flag(common.MarkedAsArchived)
        active = proxy.filter_flag(common.MarkedAsActive)

        s = (favourite, archived, active)
        all_off = all([not f for f in s])

        if active or all_off:
            menu_set[u'active'] = {
                u'text': 'Show active only',
                u'icon': item_on if active else item_off,
                u'disabled': favourite,
                u'action': lambda: proxy.filterFlagChanged.emit(common.MarkedAsActive, not active),
            }
        if favourite or all_off:
            menu_set[u'favourite'] = {
                u'text': 'Show favourites',
                u'icon': item_on if favourite else item_off,
                u'disabled': active,
                u'action': lambda: proxy.filterFlagChanged.emit(common.MarkedAsFavourite, not favourite),
            }
        if archived or all_off:
            menu_set[u'archived'] = {
                u'text': 'Show archived',
                u'icon': item_on if archived else item_off,
                u'disabled': active if active else favourite,
                u'action': lambda: proxy.filterFlagChanged.emit(common.MarkedAsArchived, not archived),
            }
        return menu_set

    @contextmenu
    def add_row_size_menu(self, menu_set):
        menu_set['increase_row_size'] = {
            'text': u'Increase row height',
            'action': self.parent().increase_row_size,
        }
        menu_set['decrease_row_size'] = {
            'text': u'Decrease row height',
            'action': self.parent().decrease_row_size,
        }
        return menu_set

    @contextmenu
    def add_refresh_menu(self, menu_set):
        parent = self.parent()
        refresh_pixmap = images.ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.MARGIN)
        preferences_pixmap = images.ImageCache.get_rsc_pixmap(
            u'settings', common.SECONDARY_TEXT, common.MARGIN)
        quit_pixmap = images.ImageCache.get_rsc_pixmap(
            u'close', common.SEPARATOR, common.MARGIN)

        menu_set[u'Refresh'] = {
            u'action': parent.model().sourceModel().modelDataResetRequested.emit,
            u'icon': refresh_pixmap
        }

        menu_set[u'separator'] = None
        menu_set[u'Preferences...'] = {
            u'action': parent.show_preferences,
            u'icon': preferences_pixmap,
        }

        try:
            menu_set[u'separator'] = None
            menu_set[u'Quit...'] = {
                u'action': parent.parent().parent().shutdown.emit,
                u'icon': quit_pixmap,
            }
        except:
            common.Log.error('Quit menu not added')

        return menu_set

    @contextmenu
    def add_set_generate_thumbnails_menu(self, menu_set):
        item_on_icon = images.ImageCache.get_rsc_pixmap(
            u'check', common.ADD, common.MARGIN)
        item_off_icon = images.ImageCache.get_rsc_pixmap(
            u'spinner_btn', common.SECONDARY_TEXT, common.MARGIN)

        model = self.parent().model().sourceModel()

        enabled = model.generate_thumbnails_enabled()
        menu_set['generate'] = {
            'text': 'Generate thumbnails',
            'icon': item_on_icon if enabled else item_off_icon,
            'action': lambda: model.set_generate_thumbnails_enabled(not enabled)
        }
        return menu_set

    @contextmenu
    def add_thumbnail_menu(self, menu_set):
        """Menu item resposible for general thumbnail operations."""
        index = self.index
        if not index.isValid() or not index.data(common.FileInfoLoaded):
            menu_set['off'] = {
                'text': 'File not loaded',
                'disabled': True
            }
            return menu_set

        capture_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'capture_thumbnail', common.SECONDARY_TEXT, common.MARGIN)
        pick_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.MARGIN)
        pick_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.MARGIN)
        remove_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, common.MARGIN)
        refresh_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'refresh', common.ADD, common.MARGIN)
        show_thumbnail = images.ImageCache.get_rsc_pixmap(
            u'active', common.SECONDARY_TEXT, common.MARGIN)

        import bookmarks.editors as editors

        source_index = index.model().mapToSource(index)
        thumbnail_path = index.data(common.ThumbnailPathRole)
        thumbnail_info = QtCore.QFileInfo(thumbnail_path)
        exists = thumbnail_info.exists()

        menu_set[u'header'] = {
            u'text': 'Thumbnails',
            u'disabled': True,
        }
        menu_set[u'separator'] = {}

        if exists:
            menu_set[u'Show'] = {
                u'icon': show_thumbnail,
                u'action': self.parent().key_space
            }
            menu_set[u'separator'] = {}

        menu_set[u'capture'] = {
            u'text': 'Capture',
            u'icon': capture_thumbnail_pixmap,
            u'action': functools.partial(images.ImageCache.capture, source_index)}

        def show_thumbnail_picker():
            widget = editors.ThumbnailsWidget(parent=self.parent())

            @QtCore.Slot(unicode)
            def add_thumbnail_from_library(path):
                images.ImageCache.pick(source_index, source=path)
                widget.thumbnailSelected.disconnect()
                widget.close()
                widget.deleteLater()

            widget.thumbnailSelected.connect(add_thumbnail_from_library)
            self.parent().resized.connect(widget.setGeometry)
            p = self.parent().viewport()
            widget.show()
            widget.setGeometry(p.geometry())
            widget.move(p.geometry().topLeft())

        menu_set[u'library'] = {
            u'text': u'Pick from library...',
            u'icon': pick_thumbnail_pixmap,
            u'action': show_thumbnail_picker
        }

        menu_set[u'file'] = {
            u'text': u'Pick',
            u'icon': pick_thumbnail_pixmap,
            u'action': functools.partial(images.ImageCache.pick, source_index)
        }

        menu_set[u'separator.'] = {}
        ext = QtCore.QFileInfo(source_index.data(
            QtCore.Qt.StatusTipRole)).suffix().lower()
        valid = ext in [f.lower() for f in common.get_oiio_extensions()]

        model = self.parent().model().sourceModel()
        if exists and model.generate_thumbnails_enabled() and valid:
            menu_set[u'remove'] = {
                u'text': u'Update thumbnail',
                u'action': lambda: images.ImageCache.remove(source_index),
                u'icon': refresh_thumbnail_pixmap
            }
        elif exists:
            menu_set[u'remove'] = {
                u'text': u'Remove',
                u'action': lambda: images.ImageCache.remove(source_index),
                u'icon': remove_thumbnail_pixmap
            }
        menu_set[u'separator_'] = {}
        menu_set[u'reveal'] = {
            u'text': u'Show cache...',
            u'action': functools.partial(
                common.reveal,
                thumbnail_path,
            )
        }
        return menu_set

    @contextmenu
    def add_manage_bookmarks_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'bookmark2', common.ADD, common.MARGIN)
        menu_set[u'Manage bookmarks'] = {
            u'text': u'Manage bookmarks',
            u'icon': pixmap,
            u'action': self.parent().manage_bookmarks.show
        }
        return menu_set

    @contextmenu
    def add_collapse_sequence_menu(self, menu_set):
        """Adds the menu needed to change context"""
        expand_pixmap = images.ImageCache.get_rsc_pixmap(
            u'expand', common.SECONDARY_TEXT, common.MARGIN)
        collapse_pixmap = images.ImageCache.get_rsc_pixmap(
            u'collapse', common.ADD, common.MARGIN)

        currenttype = self.parent().model().sourceModel().data_type()
        newtype = common.SequenceItem if currenttype == common.FileItem else common.FileItem
        groupped = currenttype == common.SequenceItem

        menu_set[u'collapse'] = {
            u'text': 'Show all files' if groupped else 'Group into sequence',
            u'icon': expand_pixmap if groupped else collapse_pixmap,
            u'checkable': False,
            # u'checked': groupped,
            u'action': functools.partial(
                self.parent().model().sourceModel().dataTypeChanged.emit, newtype)
        }
        return menu_set

    @contextmenu
    def add_location_toggles_menu(self, menu_set):
        """Adds the menu needed to change context"""
        taskfolder_pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN)
        item_on_pixmap = images.ImageCache.get_rsc_pixmap(
            u'check', common.SECONDARY_TEXT, common.MARGIN)
        item_off_pixmap = QtGui.QPixmap()

        key = u'Change task folder'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = taskfolder_pixmap

        model = self.parent().model().sourceModel()
        parent_item = model.parent_path
        if not parent_item:
            return menu_set
        if not all(parent_item):
            return menu_set

        dir_ = QtCore.QDir(u'/'.join(parent_item))
        dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        for entry in sorted(dir_.entryList()):
            if model.data_key():
                checked = model.data_key().lower() == entry.lower()
            else:
                checked = False
            menu_set[key][entry] = {
                u'text': entry.title(),
                u'icon': item_on_pixmap if checked else item_off_pixmap,
                u'action': functools.partial(model.dataKeyChanged.emit, entry)
            }
        return menu_set

    @contextmenu
    def add_remove_favourite_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        remove_icon = images.ImageCache.get_rsc_pixmap(
            u'favourite', common.REMOVE, common.MARGIN)

        favourite = self.index.flags() & common.MarkedAsFavourite

        toggle = functools.partial(
            self.parent().toggle_item_flag,
            self.index,
            common.MarkedAsFavourite,
            state=not favourite
        )
        menu_set[u'favourite'] = {
            u'text': u'Remove favourite',
            u'icon': remove_icon,
            u'checkable': False,
            u'action': (toggle, self.parent().favouritesChanged.emit)
        }
        return menu_set

    @contextmenu
    def add_control_favourites_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        add_icon = images.ImageCache.get_rsc_pixmap(
            u'favourite', common.TEXT, common.MARGIN)
        save_icon = images.ImageCache.get_rsc_pixmap(
            u'favourite', common.ADD, common.MARGIN)
        remove_icon = images.ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, common.MARGIN)

        menu_set[u'export_favourites'] = {
            u'text': u'Save favourites...',
            u'icon': save_icon,
            u'checkable': False,
            u'action': common.export_favourites
        }
        menu_set[u'import_favourites'] = {
            u'text': u'Import favourites...',
            u'icon': add_icon,
            u'checkable': False,
            u'action': (common.import_favourites, self.parent().favouritesChanged.emit)
        }
        menu_set['_separator_'] = {}
        menu_set[u'remove'] = {
            u'text': u'Remove all favourites',
            u'icon': remove_icon,
            u'checkable': False,
            u'action': (common.clear_favourites, self.parent().favouritesChanged.emit)
        }

        return menu_set
