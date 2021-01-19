# -*- coding: utf-8 -*-
"""All context-menus derive from the `BaseContextMenu` defined below.

"""
import functools
import uuid
import collections

from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common
from . import bookmark_db
from . import images
from . import settings
from . import ffmpeg
from . import rv
from . import shortcuts


def key():
    return uuid.uuid1().get_hex()


def show_event(widget, event):
    w = []
    for action in widget.actions():
        if not action.text():
            continue
        metrics = widget.fontMetrics()
        width = metrics.width(action.text())
        width += (common.MARGIN() * 7)
        w.append(int(width))
    if w:
        widget.setFixedWidth(max(w))



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
        self.index = index
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    @contextmenu
    def add_separator(self, menu_set):
        menu_set['separator' + key()] = None
        return menu_set

    def _add_separator(self, menu_set):
        menu_set['separator' + key()] = None

    def create_menu(self, menu_set, parent=None):
        """This action populates the menu using the action-set dictionaries,
        and it automatically connects the action with a corresponding method based
        on the key/method-name.

        Args:
            menu_set (OrderedDict):    The set of menu items. See keys below.
            parent (QMenu):

        Implemented keys:
            action_set[k]['action'] (bool): The action to execute when the item is clicked.
            action_set[k]['text'] (str): The action's text
            action_set[k]['data'] (object): User data stored in the action
            action_set[k]['disabled'] (bool): Sets wheter the item is disabled.
            action_set[k][u'tool_tip'] (str):The description of the action.
            action_set[k][u'status_tip'] (str): The description of the action.
            action_set[k]['icon'] (QPixmap): The action's icon.
            action_set[k]['shortcut'] (QKeySequence): The action's icon.
            action_set[k]['checkable'] (bool): Sets wheter the item is checkable.
            action_set[k]['checked'] (bool): The state of the checkbox.
            action_set[k]['visible'] (bool): The visibility of the action.

        """
        if not parent:
            parent = self

        for k, v in menu_set.iteritems():
            if u':' in k:
                continue

            if isinstance(v, collections.OrderedDict):
                submenu = QtWidgets.QMenu(k, parent=parent)
                submenu.create_menu = self.create_menu
                submenu.showEvent = functools.partial(show_event, submenu)

                if k + u':icon' in menu_set:
                    submenu.setIcon(QtGui.QIcon(menu_set[k + u':icon']))
                if k + u':text' in menu_set:
                    submenu.setTitle(menu_set[k + u':text'])

                if k + u':action' in menu_set:
                    name = menu_set[k + ':text'] if k + ':text' in menu_set else k
                    icon = menu_set[k + ':icon'] if k + ':icon' in menu_set else QtGui.QPixmap()
                    shortcut = menu_set[k + ':shortcut'] if k + ':shortcut' in menu_set else None

                    action = submenu.addAction(name)
                    action.setIconVisibleInMenu(True)
                    action.setIcon(icon)

                    if shortcut:
                        action.setShortcutVisibleInContextMenu(True)
                        action.setShortcut(shortcut)
                        action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

                    if isinstance(v, collections.Iterable):
                        for func in menu_set[k + u':action']:
                            action.triggered.connect(func)
                    else:
                        action.triggered.connect(v)
                    action.addAction(action)
                    submenu.addSeparator()

                parent.addMenu(submenu)
                parent.create_menu(v, parent=submenu)
            else:
                if u'separator' in k:
                    parent.addSeparator()
                    continue

                action = parent.addAction(k)

                if 'data' in v:  # Skipping disabled items
                    action.setData(v['data'])
                if 'disabled' in v:  # Skipping disabled items
                    action.setDisabled(v['disabled'])
                if 'action' in v:
                    if isinstance(v['action'], (list, tuple)):
                        for func in v['action']:
                            action.triggered.connect(func)
                    else:
                        action.triggered.connect(v['action'])
                if 'text' in v:
                    action.setText(v['text'])
                else:
                    action.setText(k)
                if 'description' in v and v['description']:
                    action.setToolTip(v['description'])
                    action.setStatusTip(v['description'])
                    action.setWhatsThis(v['description'])
                if 'checkable' in v:
                    action.setCheckable(v['checkable'])
                if 'checked' in v:
                    action.setChecked(v['checked'])
                if 'icon' in v:
                    action.setIconVisibleInMenu(True)
                    icon = QtGui.QIcon(v['icon'])
                    action.setIcon(icon)
                if 'shortcut' in v and v['shortcut']:
                    action.setShortcutVisibleInContextMenu(True)
                    action.setShortcut(v['shortcut'])
                    action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
                if 'visible' in v:
                    action.setVisible(v['visible'])
                else:
                    action.setVisible(True)

    def get_icon(self, name, color=common.SECONDARY_TEXT, size=common.MARGIN(), opacity=1.0):
        icon = QtGui.QIcon()

        pixmap = images.ImageCache.get_rsc_pixmap(name, color, size, opacity=opacity)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Normal)
        pixmap = images.ImageCache.get_rsc_pixmap(name, common.TEXT_SELECTED, size, opacity=opacity)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Active)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Selected)

        pixmap = images.ImageCache.get_rsc_pixmap(u'close', common.SEPARATOR, size, opacity=0.5)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Disabled)

        return icon

    def showEvent(self, event):
        """Elides the action text to fit the size of the widget upon showing."""
        show_event(self, event)

    @contextmenu
    def add_window_menu(self, menu_set):
        """Actions associated with the visibility of the widget."""
        if not common.STANDALONE:
            return menu_set

        w = self.parent().window()
        on_top_active = w.windowFlags() & QtCore.Qt.WindowStaysOnTopHint
        frameless_active = w.windowFlags() & QtCore.Qt.FramelessWindowHint

        on_icon = self.get_icon(u'check', color=common.ADD)

        k = u'Window Options'
        menu_set[k] = collections.OrderedDict()
        menu_set[k + u':icon'] = self.get_icon(u'logo', color=None)

        menu_set[k][key()] = {
            'text': u'Keep Window Always on Top',
            'icon': on_icon if on_top_active else None,
            'action': functools.partial(common.toggle_on_top, w, on_top_active)
        }
        menu_set[k][key()] = {
            'text': u'Frameless Window',
            'icon': on_icon if frameless_active else None,
            'action': functools.partial(common.toggle_frameless, w, frameless_active)
        }

        self._add_separator(menu_set[k])

        w = self.parent().window()
        try:
            maximised = w.isMaximized()
            minimised = w.isMinimized()
            full_screen = w.isFullScreen()
            menu_set[k][key()] = {
                'text': u'Maximise',
                'icon': on_icon if maximised else None,
                'action': w.toggle_maximized,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Maximize).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Maximize),
            }
            menu_set[k][key()] = {
                'text': u'Minimise',
                'icon': on_icon if minimised else None,
                'action': w.toggle_minimized,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Minimize).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Minimize),
            }
            menu_set[k][key()] = {
                'text': u'Full Screen',
                'icon': on_icon if full_screen else None,
                'action': w.toggle_fullscreen,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.FullScreen).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.FullScreen),
            }
        except:
            pass

        return menu_set

    @contextmenu
    def add_sort_menu(self, menu_set):
        """Creates the menu needed to set the sort-order of the list."""
        item_on_icon = self.get_icon(u'check', color=common.ADD)

        m = self.parent().model().sourceModel()
        sortorder = m.sort_order()
        sortrole = m.sort_role()

        sort_by_name = sortrole == common.SortByNameRole
        sort_modified = sortrole == common.SortByLastModifiedRole
        sort_size = sortrole == common.SortBySizeRole

        k =u'Sort List'
        menu_set[k] = collections.OrderedDict()
        menu_set[k + u':icon'] = self.get_icon(u'sort')

        menu_set[k][key()] = {
            'text': u'Ascending' if not sortorder else u'Descending',
            'icon': self.get_icon(u'arrow_down') if not sortorder else self.get_icon(u'arrow_up'),
            'action': lambda: m.sortingChanged.emit(sortrole, not sortorder)
        }

        self._add_separator(menu_set[k])

        menu_set[k][key()] = {
            'text': u'Name',
            'icon': item_on_icon if sort_by_name else None,
            'action': lambda: m.sortingChanged.emit(common.SortByNameRole, sortorder)
        }
        menu_set[k][key()] = {
            'text': u'Date Modified',
            'icon': item_on_icon if sort_modified else None,
            'action': lambda: m.sortingChanged.emit(common.SortByLastModifiedRole, sortorder)
        }
        menu_set[k][key()] = {
            'text': u'Size',
            'icon': item_on_icon if sort_size else None,
            'action': lambda: m.sortingChanged.emit(common.SortBySizeRole, sortorder)
        }
        return menu_set

    @contextmenu
    def add_reveal_item_menu(self, menu_set):
        """Creates a menu containing"""
        if not self.index.isValid():
            return menu_set

        path = common.get_sequence_startpath(
            self.index.data(QtCore.Qt.StatusTipRole))

        menu_set[key()] = {
            'text': u'Show Item in File Manager',
            'icon': self.get_icon(u'folder'),
            'action': functools.partial(common.reveal, path),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RevealItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RevealItem),
        }
        return menu_set

    @contextmenu
    def add_urls_menu(self, menu_set):
        if not self.index.isValid():
            return menu_set
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return menu_set

        shotgun_icon = self.get_icon('shotgun')
        bookmark_icon = self.get_icon('bookmark')

        parent_path = self.index.data(common.ParentPathRole)
        if len(parent_path) == 3:
            table = bookmark_db.BookmarkTable
        else:
            table = bookmark_db.AssetTable

        source = u'/'.join(parent_path)
        with bookmark_db.transactions(*parent_path[0:3]) as db:
            primary_url = db.value(source, 'url1', table=table)
            secondary_url = db.value(source, 'url2', table=table)

            # Shotgun properties
            shotgun_domain = db.value(
                u'/'.join(parent_path[0:3]),
                u'shotgun_domain',
                table=bookmark_db.BookmarkTable
            )
            shotgun_id = db.value(source, u'shotgun_id', table=table)
            shotgun_type = db.value(source, u'shotgun_type', table=table)

        from .shotgun import shotgun
        shotgun_entity_url = shotgun.ENTITY_URL.format(
            domain=shotgun_domain,
            shotgun_type=shotgun_type,
            shotgun_id=shotgun_id
        )

        if not any((shotgun_domain, primary_url, secondary_url)):
            return menu_set

        k = u'Open URL...'
        menu_set[k] = collections.OrderedDict()
        if shotgun_domain:
            menu_set[k][key()] = {
                'text': u'Domain   |   {}'.format(shotgun_domain),
                'icon': shotgun_icon,
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(shotgun_domain))
            }
            if all((shotgun_id, shotgun_type)):
                menu_set[k][key()] = {
                    'text': u'{}   |   {}'.format(shotgun_type.title(), shotgun_entity_url),
                    'icon': shotgun_icon,
                    'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(shotgun_entity_url))
                }
        if primary_url:
            menu_set[k][key()] = {
                'text': u'Primary URL   |   {}'.format(primary_url),
                'icon': bookmark_icon,
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(primary_url))
            }
        if secondary_url:
            menu_set[k][key()] = {
                'text': u'Secondary URL   |   {}'.format(secondary_url),
                'icon': bookmark_icon,
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(secondary_url))
            }

        return menu_set

    @contextmenu
    def add_services_menu(self, menu_set):
        """Creates a menu containing"""
        if not self.index.isValid():
            return menu_set
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return menu_set

        k = 'Services'
        menu_set[k] = collections.OrderedDict()
        path = common.get_sequence_startpath(self.index.data(QtCore.Qt.StatusTipRole))

        rv_path = settings.local_settings.value(
            settings.SettingsSection, settings.RVKey)
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', common.SECONDARY_TEXT, common.MARGIN())

        if rv_path:
            menu_set[k][key()] = {
                'text': u'Open with RV',
                'icon': pixmap,
                'action': functools.partial(rv.push, path)
            }


        @QtCore.Slot()
        def show_add_shot_task_widget():
            from .shotgun import task_version
            w = task_version.CreateTaskVersion(
                self.index.data(QtCore.Qt.StatusTipRole))
            w.open()

        @QtCore.Slot()
        def show_publish_widget():
            from .shotgun import task_publish
            w = task_publish.CreateTaskPublish(
                self.index.data(QtCore.Qt.StatusTipRole))
            w.open()

        self._add_separator(menu_set[k])

        from .shotgun import shotgun
        sg_properties = shotgun.get_shotgun_properties(
            *self.index.data(common.ParentPathRole)[0:3],
            asset=self.index.data(common.ParentPathRole)[3]
        )
        if all(sg_properties.values()):
            menu_set[k][key()] = {
                'text': u'Create Version...',
                'icon': pixmap,
                'action': show_add_shot_task_widget
            }

            menu_sechant[k][key()] = {
                'text': u'Publish File...',
                'icon': pixmap,
                'action': show_publish_widget
            }

        self._add_separator(menu_set[k])

        ffmpeg_path = settings.local_settings.value(
            settings.SettingsSection, settings.FFMpegKey)
        if ffmpeg_path:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'file', common.SECONDARY_TEXT, common.MARGIN())

            preset1 = functools.partial(
                ffmpeg.launch_ffmpeg_command, path, ffmpeg.IMAGESEQ_TO_H264
            )
            menu_set[k][key()] = {
                'text': u'Convert to H.264',
                'icon': pixmap,
                'action': preset1
            }
        return menu_set

    @contextmenu
    def add_copy_menu(self, menu_set):
        """Menu containing the subfolders of the selected item."""

        if not self.index.isValid():
            return menu_set

        copy_icon = images.ImageCache.get_rsc_pixmap(
            u'copy', common.SECONDARY_TEXT, common.MARGIN())
        copy_icon2 = images.ImageCache.get_rsc_pixmap(
            u'copy', common.SEPARATOR, common.MARGIN())

        key = u'Copy File Path'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = copy_icon

        path = self.index.data(QtCore.Qt.StatusTipRole)
        menu_set[key][u'windows1'] = {
            'text': common.copy_path(path, mode=common.WindowsPath, copy=False),
            'icon': copy_icon2,
            'action': functools.partial(
                common.copy_path,
                path,
                mode=common.WindowsPath
            ),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyItemPath).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyItemPath),
        }
        menu_set[key][u'unix'] = {
            'text': common.copy_path(path, mode=common.UnixPath, copy=False),
            'icon': copy_icon2,
            'action': functools.partial(
                common.copy_path,
                path,
                mode=common.UnixPath
            ),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyAltPath).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyAltPath),
        }
        menu_set[key][u'slack'] = {
            'text': common.copy_path(path, mode=common.SlackPath, copy=False),
            'icon': copy_icon2,
            'action': functools.partial(
                common.copy_path,
                path,
                mode=common.SlackPath
            )
        }
        menu_set[key][u'macos'] = {
            'text': common.copy_path(path, mode=common.MacOSPath, copy=False),
            'icon': copy_icon2,
            'action': functools.partial(
                common.copy_path,
                path,
                mode=common.MacOSPath
            )
        }

        self._add_separator(menu_set[key])

        path = QtCore.QFileInfo(path).dir().path()
        menu_set[key][u'parent_windows1'] = {
            'text': common.copy_path(path, mode=common.WindowsPath, copy=False),
            'icon': copy_icon2,
            'action': functools.partial(
                common.copy_path,
                path,
                mode=common.WindowsPath)
        }
        menu_set[key][u'parent_unix'] = {
            'text': common.copy_path(path, mode=common.UnixPath, copy=False),
            'icon': copy_icon2,
            'action': functools.partial(
                common.copy_path,
                path,
                mode=common.UnixPath
            )
        }
        menu_set[key][u'parent_slack'] = {
            'text': common.copy_path(path, mode=common.SlackPath, copy=False),
            'icon': copy_icon2,
            'action': functools.partial(
                common.copy_path,
                path,
                mode=common.SlackPath
            )
        }
        menu_set[key][u'parent_macos'] = {
            'text': common.copy_path(path, mode=common.MacOSPath, copy=False),
            'icon': copy_icon2,
            'action': functools.partial(
                common.copy_path,
                path,
                mode=common.MacOSPath
            )
        }
        return menu_set

    @contextmenu
    def add_mode_toggles_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        on_icon = images.ImageCache.get_rsc_pixmap(
            u'check', common.ADD, common.MARGIN())
        favourite_icon = images.ImageCache.get_rsc_pixmap(
            u'favourite', common.SEPARATOR, common.MARGIN())
        archived_icon = images.ImageCache.get_rsc_pixmap(
            u'archived', common.SEPARATOR, common.MARGIN())

        favourite = self.index.flags() & common.MarkedAsFavourite
        archived = self.index.flags() & common.MarkedAsArchived

        if self.__class__.__name__ == u'BookmarksWidgetContextMenu':
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'remove', common.SECONDARY_TEXT, common.MARGIN())
            text = u'Remove Bookmark'
        else:
            text = u'Archived'

        k = 'Flags'
        menu_set[k] = collections.OrderedDict()

        menu_set[k][u'archived'] = {
            'text': text,
            'icon': archived_icon if not archived else on_icon,
            'checkable': False,
            'action': functools.partial(
                self.parent().toggle_item_flag,
                self.index,
                common.MarkedAsArchived,
                state=not archived
            ),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemArchived).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemArchived),
        }
        menu_set[k][u'favourite'] = {
            'text': u'My File',
            'icon': favourite_icon if not favourite else on_icon,
            'checkable': False,
            'action': functools.partial(
                self.parent().toggle_item_flag,
                self.index,
                common.MarkedAsFavourite,
                state=not favourite
            ),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemFavourite).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemFavourite),
        }
        return menu_set

    @contextmenu
    def add_display_toggles_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        item_on = self.get_icon(u'check', color=common.ADD)
        item_off = None
        filter_icon = self.get_icon(u'filter')

        k = u'List Filters'
        menu_set[k] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(k)] = filter_icon

        menu_set[k][u'EditSearchFilter'] = {
            'text': u'Edit Search Filter...',
            'icon': filter_icon,
            'action': self.parent().parent().parent().topbar.filter_button.clicked,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch).key(),
        }

        self._add_separator(menu_set[k])


        proxy = self.parent().model()
        favourite = proxy.filter_flag(common.MarkedAsFavourite)
        archived = proxy.filter_flag(common.MarkedAsArchived)
        active = proxy.filter_flag(common.MarkedAsActive)

        s = (favourite, archived, active)
        all_off = all([not f for f in s])

        def toggle(flag, v):
            proxy.set_filter_flag(flag, v)
            proxy.filterFlagChanged.emit(flag, v)

        if active or all_off:
            menu_set[k][u'active'] = {
                'text': u'Show Active Item',
                'icon': item_on if active else item_off,
                'disabled': favourite,
                'action': functools.partial(toggle, common.MarkedAsActive, not active),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleActive).key(),
            }
        if favourite or all_off:
            menu_set[k][u'favourite'] = {
                'text': u'Show Favourites',
                'icon': item_on if favourite else item_off,
                'disabled': active,
                'action': functools.partial(toggle, common.MarkedAsFavourite, not favourite),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite).key(),
            }
        if archived or all_off:
            menu_set[k][u'archived'] = {
                'text': u'Show Archived',
                'icon': item_on if archived else item_off,
                'disabled': active if active else favourite,
                'action': functools.partial(toggle, common.MarkedAsArchived, not archived),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived).key(),
            }

        return menu_set

    @contextmenu
    def add_row_size_menu(self, menu_set):
        k = u'Adjust Row Height'
        menu_set[k] = collections.OrderedDict()
        menu_set[k + u':icon'] = self.get_icon('expand')

        menu_set[k]['increase_row_height'] = {
            'icon': self.get_icon(u'arrow_up'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowIncrease).key(),
            'text': u'Increase',
            'action': self.parent().increase_row_size,
        }
        menu_set[k]['decrease_row_size'] = {
            'icon': self.get_icon(u'arrow_down'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowDecrease).key(),
            'text': u'Decrease',
            'action': self.parent().decrease_row_size,
        }
        menu_set[k]['reset_row_height'] = {
            'icon': self.get_icon(u'minimize'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowReset).key(),
            'text': u'Reset',
            'action': self.parent().reset_row_size,
        }
        return menu_set

    @contextmenu
    def add_refresh_menu(self, menu_set):
        parent = self.parent()
        refresh_pixmap = images.ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.MARGIN())
        preferences_pixmap = images.ImageCache.get_rsc_pixmap(
            u'settings', common.SECONDARY_TEXT, common.MARGIN())
        quit_pixmap = images.ImageCache.get_rsc_pixmap(
            u'close', common.SEPARATOR, common.MARGIN())

        menu_set[u'RefreshMenu'] = {
            'text': u'Refresh List',
            'action': parent.model().sourceModel().modelDataResetRequested.emit,
            'icon': refresh_pixmap,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Refresh).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Refresh),
        }

        self._add_separator(menu_set)

        menu_set[u'OpenPreferencesMenu'] = {
            'text': u'Preferences...',
            'action': parent.show_preferences,
            'icon': preferences_pixmap,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenPreferences).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenPreferences),
        }

        if common.STANDALONE:

            self._add_separator(menu_set)

            menu_set[u'QuitMenu'] = {
                'text': u'Quit {}'.format(common.PRODUCT),
                'action': parent.parent().parent().shutdown,
                'icon': quit_pixmap,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Quit).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Quit)
            }

        return menu_set

    @contextmenu
    def add_set_generate_thumbnails_menu(self, menu_set):
        item_on_icon = self.get_icon(u'spinner_btn', color=common.ADD)
        item_off_icon = self.get_icon(u'spinner_btn', color=common.SEPARATOR)

        model = self.parent().model().sourceModel()
        enabled = model.generate_thumbnails_enabled()

        menu_set['generate'] = {
            'text': u'Make Thumbnails',
            'icon': item_on_icon if enabled else item_off_icon,
            'action': self.parent().parent().parent().topbar.generate_thumbnails_button.clicked,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleGenerateThumbnails).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleGenerateThumbnails),
        }

        return menu_set

    @contextmenu
    def add_thumbnail_menu(self, menu_set):
        """Menu item resposible for general thumbnail operations."""
        if not self.index.isValid():
            return menu_set

        capture_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'capture_thumbnail', common.SECONDARY_TEXT, common.MARGIN())
        pick_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.MARGIN())
        pick_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.MARGIN())
        remove_thumbnail_pixmap = images.ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, common.MARGIN())
        show_thumbnail = images.ImageCache.get_rsc_pixmap(
            u'active', common.SECONDARY_TEXT, common.MARGIN())

        menu_set[u'header'] = {
            'text': u'Thumbnail',
            'disabled': True,
        }

        self._add_separator(menu_set)

        custom_thumbnail_path = images.get_thumbnail_path(
            self.index.data(common.ParentPathRole)[0],
            self.index.data(common.ParentPathRole)[1],
            self.index.data(common.ParentPathRole)[2],
            self.index.data(QtCore.Qt.StatusTipRole),
        )
        menu_set[u'Show'] = {
            'icon': show_thumbnail,
            'action': self.parent().key_space
        }

        self._add_separator(menu_set)

        source_index = self.index.model().mapToSource(self.index)
        menu_set[u'capture'] = {
            'text': u'Capture Screen',
            'icon': capture_thumbnail_pixmap,
            'action': functools.partial(images.capture, source_index)}

        menu_set[u'file'] = {
            'text': u'Pick...',
            'icon': pick_thumbnail_pixmap,
            'action': functools.partial(
                images.pick, source_index)
        }

        menu_set[u'library'] = {
            'text': u'Pick from library...',
            'icon': pick_thumbnail_pixmap,
            'action': functools.partial(
                images.pick_from_library, source_index)
        }

        self._add_separator(menu_set)

        if QtCore.QFileInfo(custom_thumbnail_path).exists():
            menu_set[u'remove'] = {
                'text': u'Remove thumbnail',
                'action': functools.partial(
                    images.remove, source_index),
                'icon': remove_thumbnail_pixmap
            }
            menu_set[u'reveal'] = {
                'text': u'Reveal thumbnail...',
                'action': functools.partial(
                    common.reveal,
                    custom_thumbnail_path,
                )
            }
        return menu_set

    @contextmenu
    def add_sg_thumbnail_menu(self, menu_set):
        """Menu item resposible for general thumbnail operations."""
        if not self.index.isValid():
            return menu_set

        from .shotgun import shotgun

        parent_path = self.index.data(common.ParentPathRole)
        asset = parent_path[3] if len(parent_path) > 3 else None

        sg_properties = shotgun.get_shotgun_properties(
            *self.index.data(common.ParentPathRole)[0:3],
            asset=asset
        )
        if not all(sg_properties.values()):
            return menu_set

        shotgun_icon = images.ImageCache.get_rsc_pixmap(
            u'shotgun', common.SECONDARY_TEXT, common.MARGIN())

        display_thumbnail_path = images.get_thumbnail(
            self.index.data(common.ParentPathRole)[0],
            self.index.data(common.ParentPathRole)[1],
            self.index.data(common.ParentPathRole)[2],
            self.index.data(QtCore.Qt.StatusTipRole),
            common.MARGIN(),
            fallback_thumb=self.parent().itemDelegate().fallback_thumb,
            get_path=True
        )

        @QtCore.Slot()
        def _upload_thumbnail_to_shotgun():
            """Private slot used to upload the current thumbnail to shotgun.

            """
            from . import common_ui
            with shotgun.connection(*self.index.data(common.ParentPathRole)[0:3]) as sg:
                try:
                    sg.upload_thumbnail(
                        sg_properties[u'shotgun_type'],
                        sg_properties[u'shotgun_id'],
                        display_thumbnail_path
                    )
                    common_ui.OkBox(u'Shotgun thumbnail updated.', u'').open()
                    log.success(u'Thumbnail updated.')
                except Exception as e:
                    common_ui.ErrorBox(
                        u'Upload failed', u'{}'.format(e)
                    ).open()
                    log.error(e)
                    raise

        k = u'Shotgun'
        menu_set[k] = collections.OrderedDict()
        menu_set['{}:icon'.format(k)] = shotgun_icon

        if QtCore.QFileInfo(display_thumbnail_path).exists():
            menu_set[k]['Upload thumbnail to Shotgun'] = {
                'action': _upload_thumbnail_to_shotgun,
                'icon': shotgun_icon
            }
        return menu_set

    @contextmenu
    def add_bookmark_editor_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN())

        menu_set[u'BookmarkEditor'] = {
            'text': u'Bookmark Editor...',
            'icon': pixmap,
            'action': (self.parent().selectionModel().clearSelection, self.parent().show_add_widget),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.AddItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }
        menu_set[u'AddItem'] = {
            'text': u'Add Asset...',
            'icon': pixmap,
            'action': self.parent().show_add_widget,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.AddItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }

        self._add_separator(menu_set)


        return menu_set

    @contextmenu
    def add_collapse_sequence_menu(self, menu_set):
        """Adds the menu needed to change context"""
        expand_pixmap = images.ImageCache.get_rsc_pixmap(
            u'expand', common.SECONDARY_TEXT, common.MARGIN())
        collapse_pixmap = images.ImageCache.get_rsc_pixmap(
            u'collapse', common.ADD, common.MARGIN())

        currenttype = self.parent().model().sourceModel().data_type()
        newtype = common.SequenceItem if currenttype == common.FileItem else common.FileItem
        groupped = currenttype == common.SequenceItem

        menu_set[uuid.uuid1().get_hex()] = {
            'text': u'Expand Sequences' if groupped else u'Group Sequences',
            'icon': expand_pixmap if groupped else collapse_pixmap,
            'checkable': False,
            'action': functools.partial(
                self.parent().model().sourceModel().dataTypeChanged.emit, newtype)
        }
        return menu_set

    @contextmenu
    def add_task_toggles_menu(self, menu_set):
        """Adds the menu needed to change context"""
        taskfolder_pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN())
        item_on_pixmap = images.ImageCache.get_rsc_pixmap(
            u'check', common.SECONDARY_TEXT, common.MARGIN())
        item_off_pixmap = QtGui.QPixmap()

        k = u'Select Task Folder'
        menu_set[k] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(k)] = taskfolder_pixmap

        model = self.parent().model().sourceModel()

        settings.local_settings.load_and_verify_stored_paths()
        if not settings.ACTIVE[settings.AssetKey]:
            return menu_set
        parent_item = (
            settings.ACTIVE[settings.ServerKey],
            settings.ACTIVE[settings.JobKey],
            settings.ACTIVE[settings.RootKey],
            settings.ACTIVE[settings.AssetKey],
        )

        if not parent_item:
            return menu_set
        if not all(parent_item):
            return menu_set

        dir_ = QtCore.QDir(u'/'.join(parent_item))
        dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        for entry in sorted(dir_.entryList()):
            task = model.task()
            if task:
                checked = task == entry
            else:
                checked = False
            menu_set[k][entry] = {
                'text': entry.title(),
                'icon': item_on_pixmap if checked else item_off_pixmap,
                'action': functools.partial(model.taskFolderChanged.emit, entry)
            }
        return menu_set

    @contextmenu
    def add_remove_favourite_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        remove_icon = images.ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, common.MARGIN())

        favourite = self.index.flags() & common.MarkedAsFavourite

        toggle = functools.partial(
            self.parent().toggle_item_flag,
            self.index,
            common.MarkedAsFavourite,
            state=not favourite
        )
        menu_set[key()] = {
            'text': u'Remove from My Files',
            'icon': remove_icon,
            'checkable': False,
            'action': (toggle, self.parent().favouritesChanged.emit)
        }
        return menu_set

    @contextmenu
    def add_control_favourites_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        remove_icon = images.ImageCache.get_rsc_pixmap(
            u'remove', common.SECONDARY_TEXT, common.MARGIN())

        menu_set[key()] = {
            'text': u'Export My Files...',
            'checkable': False,
            'action': self.parent().export_favourites
        }
        menu_set[key()] = {
            'text': u'Import My Files...',
            'checkable': False,
            'action': (self.parent().import_favourites, self.parent().favouritesChanged.emit)
        }

        self._add_separator(menu_set)

        menu_set[key()] = {
            'text': u'Clear My Files',
            'icon': remove_icon,
            'checkable': False,
            'action': (self.parent().clear_favourites, self.parent().favouritesChanged.emit)
        }

        return menu_set

    @contextmenu
    def add_add_file_menu(self, menu_set):
        add_pixmap = images.ImageCache.get_rsc_pixmap(
            u'add_file', common.ADD, common.MARGIN())

        menu_set[u'add_file...'] = {
            'text': u'Add File...',
            'icon': add_pixmap,
            'action': self.parent().show_add_widget
        }
        return menu_set

    @contextmenu
    def add_notes_menu(self, menu_set):
        if not self.index.isValid():
            return

        menu_set[u'add_file...'] = {
            'text': u'Show Notes...',
            'icon': self.get_icon('todo'),
            'action': self.parent().show_todos,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenTodo).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenTodo),
        }
        return menu_set

    @contextmenu
    def add_properties_menu(self, menu_set):
        if not self.index.isValid():
            return menu_set

        settings_pixmap = images.ImageCache.get_rsc_pixmap(
            u'settings', common.SECONDARY_TEXT, common.MARGIN())
        clipboard_pixmap = images.ImageCache.get_rsc_pixmap(
            u'copy', common.SECONDARY_TEXT, common.MARGIN())

        k = u'Properties'
        menu_set[k] = collections.OrderedDict()
        menu_set['{}:icon'.format(k)] = settings_pixmap

        menu_set[k][u'Edit Properties...'] = {
            'icon': settings_pixmap,
            'action': self.parent().show_properties_widget,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenProperties),
        }

        from .properties import base

        menu_set[k][u'Copy Properties'] = {
            'action': functools.partial(
                base.copy_properties,
                self.index.data(common.ParentPathRole)[0],
                self.index.data(common.ParentPathRole)[1],
                self.index.data(common.ParentPathRole)[2]
            ),
            'icon': clipboard_pixmap,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties),
        }

        if not base.CLIPBOARD:
            return menu_set

        from .lists import bookmarks
        menu_set[k][u'Paste Properties'] = {
            'action': (
                functools.partial(
                    base.paste_properties,
                    *self.index.data(common.ParentPathRole)[0:3]
                ),
                functools.partial(bookmarks.update_description, self.index),
            ),
            'icon': clipboard_pixmap,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties),
        }

        return menu_set

    @contextmenu
    def add_show_addasset_menu(self, menu_set):
        add_pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN())
        widget = self.parent().parent().widget(0)
        menu_set[u'add_asset'] = {
            'icon': add_pixmap,
            'text': u'Add Asset...',
            'action': lambda: widget.show_asset_property_widget(update=False)
        }
        return menu_set

    @contextmenu
    def add_sg_bulk_link_menu(self, menu_set):
        if not self.parent().model().sourceModel().rowCount():
            return menu_set

        sg_pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', common.SECONDARY_TEXT, common.MARGIN())

        from .shotgun import shotgun

        parent_path = self.parent().model().sourceModel().parent_path()

        sg_properties = shotgun.get_shotgun_properties(*parent_path[0:3])
        if not all((
            sg_properties['shotgun_domain'],
            sg_properties['shotgun_scriptname'],
            sg_properties['shotgun_api_key']
        )):
            return menu_set


        menu_set[u'sg_bulk_link'] = {
            'text': u'Link all assets with Shotgun...',
            'icon': sg_pixmap,
            'action': self.parent().show_shotgun_bulk_link_widget
        }
        if self.index.isValid():
            menu_set[u'sg_link'] = {
                'text': u'Link {} with Shotgun...'.format(self.index.data(common.ParentPathRole)[-1]),
                'icon': sg_pixmap,
                'action': lambda: self.parent().show_shotgun_bulk_link_widget(current_only=True)
            }

        return menu_set
