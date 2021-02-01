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
from . import actions
from .shotgun import actions as sg_actions
from .shotgun import shotgun


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


class BaseContextMenu(QtWidgets.QMenu):
    """Base class containing the context menu definitions.

    The menu structure is defined in `self.menu`, a `collections.OrderedDict` instance.
    The data is expanded into a UI layout by `self.create_menu`. The menu is principally designed
    to work with index-based views and as a result the default constructor takes
    a QModelIndex, stored in `self.index`.

    Properties:
        index (QModelIndex): The index the context menu is associated with.

    Methods:
        create_menu():  Populates the menu with actions based on the ``self.menu`` given.

    """

    def __init__(self, index, parent=None):
        super(BaseContextMenu, self).__init__(parent=parent)
        self.index = index
        self.menu = collections.OrderedDict()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setTearOffEnabled(False)
        self.setSeparatorsCollapsible(True)

        self.setup()
        self.create_menu(self.menu)

    @common.debug
    @common.error
    def setup(self):
        raise NotImplementedError('Abstract method must be overriden in subclass.')

    @common.debug
    @common.error
    def create_menu(self, menu, parent=None):
        """Expands the given menu set into a UI layout.

        """
        if not parent:
            parent = self

        for k, v in menu.iteritems():
            if u':' in k:
                continue

            if isinstance(v, collections.OrderedDict):
                submenu = QtWidgets.QMenu(k, parent=parent)
                submenu.create_menu = self.create_menu
                submenu.showEvent = functools.partial(show_event, submenu)

                if k + u':icon' in menu:
                    submenu.setIcon(QtGui.QIcon(menu[k + u':icon']))
                if k + u':text' in menu:
                    submenu.setTitle(menu[k + u':text'])

                if k + u':action' in menu:
                    name = menu[k + ':text'] if k + ':text' in menu else k
                    icon = menu[k + ':icon'] if k + \
                        ':icon' in menu else QtGui.QIcon()
                    shortcut = menu[k + ':shortcut'] if k + \
                        ':shortcut' in menu else None

                    action = submenu.addAction(name)
                    action.setIconVisibleInMenu(True)
                    action.setIcon(icon)

                    if shortcut:
                        action.setShortcutVisibleInContextMenu(True)
                        action.setShortcut(shortcut)
                        action.setShortcutContext(
                            QtCore.Qt.WidgetWithChildrenShortcut)

                    if isinstance(v, collections.Iterable):
                        for func in menu[k + u':action']:
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
                    action.setShortcutContext(
                        QtCore.Qt.WidgetWithChildrenShortcut)
                if 'visible' in v:
                    action.setVisible(v['visible'])
                else:
                    action.setVisible(True)

    def get_icon(self, name, color=common.SECONDARY_TEXT, size=common.MARGIN(), opacity=1.0):
        icon = QtGui.QIcon()

        pixmap = images.ImageCache.get_rsc_pixmap(name, color, size, opacity=opacity)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Normal)
        pixmap = images.ImageCache.get_rsc_pixmap(
            name, common.TEXT_SELECTED, size, opacity=opacity)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Active)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Selected)

        pixmap = images.ImageCache.get_rsc_pixmap(u'close', common.SEPARATOR, size, opacity=0.5)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Disabled)

        return icon

    def showEvent(self, event):
        """Elides the action text to fit the size of the widget upon showing."""
        show_event(self, event)

    def separator(self, menu=None):
        if menu is None:
            menu = self.menu
        menu['separator' + key()] = None

    def window_menu(self):
        if not common.STANDALONE:
            return

        w = self.parent().window()
        on_top_active = w.windowFlags() & QtCore.Qt.WindowStaysOnTopHint
        frameless_active = w.windowFlags() & QtCore.Qt.FramelessWindowHint

        on_icon = self.get_icon(u'check', color=common.ADD)
        logo_icon = self.get_icon(u'logo', color=None)

        k = u'Window Options'
        self.menu[k] = collections.OrderedDict()
        self.menu[k + u':icon'] = logo_icon

        try:
            self.menu[k][key()] = {
                'text': u'Open a New {} Instance...'.format(common.PRODUCT),
                'icon': logo_icon,
                'action': actions.exec_instance,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenNewInstance).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenNewInstance),
            }

            self.separator(self.menu[k])
        except:
            pass

        self.menu[k][key()] = {
            'text': u'Keep Window Always on Top',
            'icon': on_icon if on_top_active else None,
            'action': actions.toggle_stays_on_top
        }
        self.menu[k][key()] = {
            'text': u'Frameless Window',
            'icon': on_icon if frameless_active else None,
            'action': actions.toggle_frameless
        }

        self.separator(self.menu[k])

        w = self.parent().window()
        try:
            maximised = w.isMaximized()
            minimised = w.isMinimized()
            full_screen = w.isFullScreen()
            self.menu[k][key()] = {
                'text': u'Maximise',
                'icon': on_icon if maximised else None,
                'action': actions.toggle_maximized,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Maximize).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Maximize),
            }
            self.menu[k][key()] = {
                'text': u'Minimise',
                'icon': on_icon if minimised else None,
                'action': actions.toggle_minimized,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Minimize).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Minimize),
            }
            self.menu[k][key()] = {
                'text': u'Full Screen',
                'icon': on_icon if full_screen else None,
                'action': actions.toggle_fullscreen,
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.FullScreen).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.FullScreen),
            }
        except:
            pass

    def sort_menu(self):
        item_on_icon = self.get_icon(u'check', color=common.ADD)

        m = self.parent().model().sourceModel()
        sortorder = m.sort_order()
        sortrole = m.sort_role()

        sort_by_name = sortrole == common.SortByNameRole
        sort_modified = sortrole == common.SortByLastModifiedRole
        sort_size = sortrole == common.SortBySizeRole

        k = u'Sort List'
        self.menu[k] = collections.OrderedDict()
        self.menu[k + u':icon'] = self.get_icon(u'sort')

        self.menu[k][key()] = {
            'text': u'Ascending' if not sortorder else u'Descending',
            'icon': self.get_icon(u'arrow_down') if not sortorder else self.get_icon(u'arrow_up'),
            'action': actions.toggle_sort_order,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSortOrder).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSortOrder),
        }

        self.separator(self.menu[k])

        self.menu[k][key()] = {
            'text': u'Name',
            'icon': item_on_icon if sort_by_name else None,
            'action': functools.partial(
                actions.change_sorting,
                common.SortByNameRole,
                sortorder
            )
        }
        self.menu[k][key()] = {
            'text': u'Date Modified',
            'icon': item_on_icon if sort_modified else None,
            'action': functools.partial(
                actions.change_sorting,
                common.SortByLastModifiedRole,
                sortorder
            )
        }
        self.menu[k][key()] = {
            'text': u'Size',
            'icon': item_on_icon if sort_size else None,
            'action': functools.partial(
                actions.change_sorting,
                common.SortBySizeRole,
                sortorder
            )
        }

    def reveal_item_menu(self):
        if not self.index.isValid():
            return

        path = common.get_sequence_startpath(
            self.index.data(QtCore.Qt.StatusTipRole))

        self.menu[key()] = {
            'text': u'Show Item in File Manager',
            'icon': self.get_icon(u'folder'),
            'action': functools.partial(actions.reveal, path),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RevealItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RevealItem),
        }
        return

    def bookmark_url_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return

        k = u'Visit Website...'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('bookmark')

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        with bookmark_db.transactions(server, job, root) as db:
            primary_url = db.value(db.source(), 'url1', table=bookmark_db.BookmarkTable)
            secondary_url = db.value(db.source(), 'url2', table=bookmark_db.BookmarkTable)

        if not any((primary_url, secondary_url)):
            return

        if primary_url:
            self.menu[k][key()] = {
                'text': primary_url,
                'icon': self.get_icon('bookmark'),
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(primary_url)),
            }
        if secondary_url:
            self.menu[k][key()] = {
                'text': secondary_url,
                'icon': self.get_icon('bookmark'),
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(secondary_url))
            }

        self.separator(self.menu[k])

    def asset_url_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return
        if len(self.index.data(common.ParentPathRole)) < 4:
            return

        k = u'Visit Website...'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('bookmark')

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        asset = self.index.data(common.ParentPathRole)[3]
        with bookmark_db.transactions(server, job, root) as db:
            primary_url = db.value(db.source(asset), 'url1')
            secondary_url = db.value(db.source(asset), 'url2')

        if not any((primary_url, secondary_url)):
            return

        if primary_url:
            self.menu[k][key()] = {
                'text': primary_url,
                'icon': self.get_icon('bookmark'),
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(primary_url)),
            }
        if secondary_url:
            self.menu[k][key()] = {
                'text': secondary_url,
                'icon': self.get_icon('bookmark'),
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(secondary_url))
            }

        self.separator(self.menu[k])

    def services_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return

        k = 'Services'
        self.menu[k] = collections.OrderedDict()
        path = common.get_sequence_startpath(
            self.index.data(QtCore.Qt.StatusTipRole))

        rv_path = settings.local_settings.value(
            settings.SettingsSection, settings.RVKey)
        pixmap = self.get_icon(u'shotgun')

        if rv_path:
            self.menu[k][key()] = {
                'text': u'Open with RV',
                'icon': pixmap,
                'action': functools.partial(rv.push, path)
            }

        self.separator()

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        asset = self.index.data(common.ParentPathRole)[3]

        sg_properties = shotgun.get_properties(server, job, root, asset)
        if shotgun.is_valid(sg_properties):
            self.menu[k][key()] = {
                'text': u'Create Version...',
                'icon': pixmap,
                'action': actions.show_add_shot_task_widget
            }

            self.menu[k][key()] = {
                'text': u'Publish File...',
                'icon': pixmap,
                'action': actions.show_publish_widget
            }

        self.separator()

        ffmpeg_path = settings.local_settings.value(
            settings.SettingsSection, settings.FFMpegKey)
        if ffmpeg_path:
            pixmap = self.get_icon(u'file')

            preset1 = functools.partial(
                ffmpeg.launch_ffmpeg_command, path, ffmpeg.IMAGESEQ_TO_H264
            )
            self.menu[k][key()] = {
                'text': u'Convert to H.264',
                'icon': pixmap,
                'action': preset1
            }
        return

    def copy_menu(self):
        if not self.index.isValid():
            return

        k = u'Copy File Path'
        self.menu[k] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(k)] = self.get_icon(u'copy')

        path = self.index.data(QtCore.Qt.StatusTipRole)
        for mode in (common.WindowsPath, common.MacOSPath, common.UnixPath, common.SlackPath):
            m = u'{}'.format(mode)
            self.menu[k][m] = {
                'text': actions.copy_path(path, mode=mode, copy=False),
                'icon': self.get_icon(u'copy', color=common.SEPARATOR),
                'action': functools.partial(actions.copy_path, path, mode=mode),
            }
            if common.get_platform() == mode:
                self.menu[k][m]['shortcut'] = shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyItemPath).key()
                self.menu[k][m]['description'] = shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyItemPath)
            elif mode == common.UnixPath:
                self.menu[k][m]['shortcut'] = shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyAltItemPath).key()
                self.menu[k][m]['description'] = shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyAltItemPath)

    def toggle_item_flags_menu(self):
        if not self.index.isValid():
            return

        on_icon = self.get_icon(u'check', color=common.ADD)
        favourite_icon = self.get_icon(u'favourite', color=common.SEPARATOR)
        archived_icon = self.get_icon(u'archived', color=common.SEPARATOR)

        favourite = self.index.flags() & common.MarkedAsFavourite
        archived = self.index.flags() & common.MarkedAsArchived

        if self.__class__.__name__ == u'BookmarksWidgetContextMenu':
            text = u'Remove Bookmark'
        else:
            text = u'Archived'

        k = 'Flags'
        self.menu[k] = collections.OrderedDict()

        self.menu[k][u'archived'] = {
            'text': text,
            'icon': archived_icon if not archived else on_icon,
            'checkable': False,
            'action': actions.toggle_archived,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemArchived).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemArchived),
        }
        self.menu[k][u'favourite'] = {
            'text': u'My File',
            'icon': favourite_icon if not favourite else on_icon,
            'checkable': False,
            'action': actions.toggle_favourite,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemFavourite).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleItemFavourite),
        }
        return

    def list_filter_menu(self):
        item_on = self.get_icon(u'check', color=common.ADD)
        item_off = None

        k = u'List Filters'
        self.menu[k] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(k)] = self.get_icon(u'filter')

        self.menu[k][u'EditSearchFilter'] = {
            'text': u'Edit Search Filter...',
            'icon': self.get_icon(u'filter'),
            'action': actions.toggle_filter_editor,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch),
        }

        proxy = self.parent().model()
        favourite = proxy.filter_flag(common.MarkedAsFavourite)
        archived = proxy.filter_flag(common.MarkedAsArchived)
        active = proxy.filter_flag(common.MarkedAsActive)

        s = (favourite, archived, active)
        all_off = all([not f for f in s])

        if active or all_off:
            self.menu[k][u'active'] = {
                'text': u'Show Active Item',
                'icon': item_on if active else item_off,
                'disabled': favourite,
                'action': functools.partial(actions.toggle_flag, common.MarkedAsActive, not active),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleActive).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleActive),
            }
        if favourite or all_off:
            self.menu[k][u'favourite'] = {
                'text': u'Show Favourites',
                'icon': item_on if favourite else item_off,
                'disabled': active,
                'action': functools.partial(actions.toggle_flag, common.MarkedAsFavourite, not favourite),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite),
            }
        if archived or all_off:
            self.menu[k][u'archived'] = {
                'text': u'Show Archived',
                'icon': item_on if archived else item_off,
                'disabled': active if active else favourite,
                'action': functools.partial(actions.toggle_flag, common.MarkedAsArchived, not archived),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived).key(),
                'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived),
            }

    def row_size_menu(self):
        k = u'Change Row Height'
        self.menu[k] = collections.OrderedDict()
        self.menu[k + u':icon'] = self.get_icon('expand')

        self.menu[k][key()] = {
            'text': u'Increase',
            'icon': self.get_icon(u'arrow_up'),
            'action': actions.increase_row_size,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowIncrease).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RowIncrease),
        }
        self.menu[k][key()] = {
            'text': u'Decrease',
            'icon': self.get_icon(u'arrow_down'),
            'action': actions.decrease_row_size,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowDecrease).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RowDecrease),
        }
        self.menu[k][key()] = {
            'text': u'Reset',
            'icon': self.get_icon(u'minimize'),
            'action': actions.reset_row_size,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.RowReset).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.RowReset),
        }

    def refresh_menu(self):
        self.menu[u'RefreshMenu'] = {
            'text': u'Refresh List',
            'action': actions.refresh,
            'icon': self.get_icon(u'refresh'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Refresh).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Refresh),
        }

    def preferences_menu(self):
        self.menu[u'OpenPreferencesMenu'] = {
            'text': u'Preferences...',
            'action': actions.show_preferences,
            'icon': self.get_icon(u'settings'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenPreferences).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenPreferences),
        }

    def quit_menu(self):
        if not common.STANDALONE:
            return
        self.menu[u'QuitMenu'] = {
            'text': u'Quit {}'.format(common.PRODUCT),
            'action': actions.quit,
            'icon': self.get_icon(u'close'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.Quit).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.Quit)
        }

    def set_generate_thumbnails_menu(self):
        item_on_icon = self.get_icon(u'spinner_btn', color=common.ADD)
        item_off_icon = self.get_icon(u'spinner_btn', color=common.SEPARATOR)

        model = self.parent().model().sourceModel()
        enabled = model.generate_thumbnails_enabled()

        self.menu['generate'] = {
            'text': u'Make Thumbnails',
            'icon': item_on_icon if enabled else item_off_icon,
            'action': actions.signals.toggleMakeThumbnailsButton,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleGenerateThumbnails).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleGenerateThumbnails),
        }

    def title(self):
        if not self.index.isValid():
            return
        self.menu[u'item'] = {
            'text': self.index.data(common.ParentPathRole)[-1],
            'disabled': True,
        }

    def thumbnail_menu(self):
        if not self.index.isValid():
            return

        self.menu[u'header'] = {
            'text': u'Thumbnail',
            'disabled': True,
        }

        self.separator()

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        item_thumbnail_path = images.get_cached_thumbnail_path(
            server,
            job,
            root,
            self.index.data(QtCore.Qt.StatusTipRole),
        )
        thumbnail_path = images.get_thumbnail(
            server,
            job,
            root,
            self.index.data(QtCore.Qt.StatusTipRole),
            fallback_thumb=self.parent().itemDelegate().fallback_thumb,
            get_path=True
        )

        self.menu[key()] = {
            'text': u'Preview',
            'icon': self.get_icon(u'active'),
            'action': actions.preview
        }

        self.separator()

        source_index = self.index.model().mapToSource(self.index)
        self.menu[u'capture'] = {
            'text': u'Capture Screen...',
            'icon': self.get_icon(u'capture_thumbnail'),
            'action': actions.capture_thumbnail
        }

        self.menu[u'file'] = {
            'text': u'Pick Thumbnail File...',
            'icon': self.get_icon(u'pick_thumbnail'),
            'action': actions.pick_thumbnail_from_file
        }

        self.menu[u'library'] = {
            'text': u'Pick Thumbnail From Library...',
            'icon': self.get_icon(u'pick_thumbnail'),
            'action': actions.pick_thumbnail_from_library
        }

        self.separator()

        if QtCore.QFileInfo(item_thumbnail_path).exists():
            self.menu[u'reveal'] = {
                'text': u'Reveal Thumbnail...',
                'action': functools.partial(
                    actions.reveal,
                    item_thumbnail_path,
                )
            }
            self.separator()
            self.menu[u'remove'] = {
                'text': u'Remove Thumbnail',
                'action': actions.remove_thumbnail,
                'icon': self.get_icon(u'remove', color=common.REMOVE)
            }
        elif QtCore.QFileInfo(thumbnail_path).exists():
            self.menu[u'reveal'] = {
                'text': u'Reveal File...',
                'action': functools.partial(
                    actions.reveal,
                    thumbnail_path,
                )
            }

    def bookmark_editor_menu(self):
        icon = self.get_icon('add', color=common.ADD)
        self.menu[key()] = {
            'text': u'Add Bookmark...',
            'icon': icon,
            'action': actions.add_bookmark,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.AddItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }

    def add_asset_to_bookmark_menu(self):
        if not self.index.isValid():
            return
        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        self.menu[key()] = {
            'text': u'Add Asset...',
            'icon': self.get_icon('add'),
            'action': functools.partial(actions.add_asset, server=server, job=job, root=root),
        }

    def collapse_sequence_menu(self):
        expand_pixmap = self.get_icon(u'expand')
        collapse_pixmap = self.get_icon(u'collapse', common.ADD)

        currenttype = self.parent().model().sourceModel().data_type()
        groupped = currenttype == common.SequenceItem

        self.menu[key()] = {
            'text': u'Show Sequences' if groupped else u'Show Files',
            'icon': expand_pixmap if groupped else collapse_pixmap,
            'checkable': False,
            'action': actions.signals.toggleSequenceButton,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSequence).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSequence),
        }

    def task_toggles_menu(self):
        taskfolder_pixmap = self.get_icon(u'folder')
        item_on_pixmap = self.get_icon(u'check')
        item_off_pixmap = QtGui.QIcon()

        k = u'Select Task Folder'
        self.menu[k] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(k)] = taskfolder_pixmap

        model = self.parent().model().sourceModel()

        settings.local_settings.load_and_verify_stored_paths()
        if not settings.active(settings.AssetKey):
            return
        parent_item = (
            settings.active(settings.ServerKey),
            settings.active(settings.JobKey),
            settings.active(settings.RootKey),
            settings.active(settings.AssetKey),
        )

        if not parent_item:
            return
        if not all(parent_item):
            return

        dir_ = QtCore.QDir(u'/'.join(parent_item))
        dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        for entry in sorted(dir_.entryList()):
            task = model.task()
            if task:
                checked = task == entry
            else:
                checked = False
            self.menu[k][entry] = {
                'text': entry.title(),
                'icon': item_on_pixmap if checked else item_off_pixmap,
                'action': functools.partial(model.taskFolderChanged.emit, entry)
            }

    def remove_favourite_menu(self):
        self.menu[key()] = {
            'text': u'Remove from My Files',
            'icon': self.get_icon(u'remove', color=common.REMOVE),
            'checkable': False,
            'action': actions.toggle_favourite
        }

    def control_favourites_menu(self):
        remove_icon = self.get_icon(u'remove')

        self.menu[key()] = {
            'text': u'Export My Files...',
            'checkable': False,
            'action': self.parent().export_favourites
        }
        self.menu[key()] = {
            'text': u'Import My Files...',
            'checkable': False,
            'action': self.parent().import_favourites,
        }

        self.separator()

        self.menu[key()] = {
            'text': u'Clear My Files',
            'icon': remove_icon,
            'checkable': False,
            'action': self.parent().clear_favourites
        }

    def add_file_menu(self):
        self.menu[key()] = {
            'text': u'Add Template File...',
            'icon': self.get_icon(u'add_file', color=common.ADD),
            'action': actions.add_file,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.AddItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
        }

    def add_file_to_asset_menu(self):
        if not self.index.isValid():
            return

        asset = self.index.data(common.ParentPathRole)[3]
        self.menu[key()] = {
            'text': u'Add Template File...',
            'icon': self.get_icon(u'add_file'),
            'action': functools.partial(actions.add_file, asset=asset)
        }

    def notes_menu(self):
        if not self.index.isValid():
            return

        self.menu[u'add_file...'] = {
            'text': u'Show Notes...',
            'icon': self.get_icon('todo'),
            'action': actions.show_todos,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.OpenTodo).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.OpenTodo),
        }

    def edit_selected_bookmark_menu(self):
        if not self.index.isValid():
            return

        settings_icon = self.get_icon(u'settings')
        server, job, root = self.index.data(common.ParentPathRole)[0:3]

        k = u'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': u'Edit Bookmark Properties...',
            'icon': settings_icon,
            'action': functools.partial(actions.edit_bookmark, server=server, job=job, root=root),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
        }

    def bookmark_clipboard_menu(self):
        if not self.index.isValid():
            return

        k = u'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = self.get_icon(u'settings')

        self.separator(menu=self.menu[k])

        self.menu[k][key()] = {
            'text': u'Copy Bookmark Properties',
            'action': actions.copy_bookmark_properties,
            'icon': self.get_icon(u'copy'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties),
        }

        if not bookmark_db.CLIPBOARD[bookmark_db.BookmarkTable]:
            return

        self.menu[k][key()] = {
            'text': u'Paste Bookmark Properties',
            'action': actions.paste_bookmark_properties,
            'icon': self.get_icon(u'copy'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties),
        }

    def asset_clipboard_menu(self):
        if not self.index.isValid():
            return

        k = u'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = self.get_icon(u'settings')

        self.separator(menu=self.menu[k])

        self.menu[k][key()] = {
            'text': u'Copy Asset Properties',
            'action': actions.copy_asset_properties,
            'icon': self.get_icon(u'copy'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties),
        }

        if not bookmark_db.CLIPBOARD[bookmark_db.AssetTable]:
            return

        self.menu[k][key()] = {
            'text': u'Paste Asset Properties',
            'action': actions.paste_asset_properties,
            'icon': self.get_icon(u'copy'),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.PasteProperties),
        }

    def edit_active_bookmark_menu(self):
        settings_icon = self.get_icon(u'settings')

        k = u'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': u'Edit Bookmark Properties...',
            'icon': settings_icon,
            'action': actions.edit_bookmark,
        }

    def edit_selected_asset_menu(self):
        if not self.index.isValid():
            return

        settings_icon = self.get_icon(u'settings')
        asset = self.index.data(common.ParentPathRole)[3]

        k = u'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': u'Edit Asset Properties...',
            'icon': settings_icon,
            'action': functools.partial(actions.edit_asset, asset=asset),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
        }

    def edit_active_asset_menu(self):
        settings_icon = self.get_icon(u'settings')

        k = u'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': u'Edit Asset Properties...',
            'icon': settings_icon,
            'action': actions.edit_asset,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
        }

    def edit_selected_file_menu(self):
        if not self.index.isValid():
            return

        settings_icon = self.get_icon(u'settings')
        _file = self.index.data(QtCore.Qt.StatusTipRole)

        k = u'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        self.menu[k][key()] = {
            'text': u'Edit File Properties...',
            'icon': settings_icon,
            'action': functools.partial(actions.edit_file, _file),
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
        }

    def show_addasset_menu(self):
        add_pixmap = self.get_icon(u'add', color=common.ADD)
        self.menu[u'add_asset'] = {
            'icon': add_pixmap,
            'text': u'Add Asset...',
            'action': actions.add_asset
        }

    def sg_bulk_link_menu(self):
        if not self.parent().model().sourceModel().rowCount():
            return

        sg_pixmap = self.get_icon(u'shotgun')
        parent_path = self.parent().model().sourceModel().parent_path()

        sg_properties = shotgun.get_properties(*parent_path[0:4])
        if not shotgun.is_valid(sg_properties):
            return

        self.menu[u'sg_bulk_link'] = {
            'text': u'Link all assets with Shotgun...',
            'icon': sg_pixmap,
            'action': self.parent().show_shotgun_bulk_link_widget
        }
        if self.index.isValid():
            self.menu[u'sg_link'] = {
                'text': u'Link {} with Shotgun...'.format(self.index.data(common.ParentPathRole)[-1]),
                'icon': sg_pixmap,
                'action': lambda: self.parent().show_shotgun_bulk_link_widget(current_only=True)
            }

    def sg_thumbnail_menu(self):
        if not self.index.isValid():
            return

        p = self.index.data(common.ParentPathRole)
        source = self.index.data(QtCore.Qt.StatusTipRole)
        server, job, root = p[0:3]
        asset = p[3] if len(p) > 3 else None

        sg_properties = shotgun.get_properties(server, job, root, asset)
        if not shotgun.is_valid(sg_properties):
            return

        shotgun_icon = self.get_icon(u'shotgun')
        thumbnail_path = images.get_thumbnail(
            server,
            job,
            root,
            source,
            fallback_thumb=self.parent().itemDelegate().fallback_thumb,
            get_path=True
        )

        k = u'Shotgun'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = shotgun_icon

        if not QtCore.QFileInfo(thumbnail_path).exists():
            return

        self.menu[k][key()] = {
            'text': u'Upload Thumbnail to Shotgun...',
            'action': functools.partial(sg_actions.upload_thumbnail, sg_properties, thumbnail_path),
            'icon': shotgun_icon
        }

    def sg_url_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return

        k = u'Visit Website...'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('bookmark')

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        if len(self.index.data(common.ParentPathRole)) >= 4:
            asset = self.index.data(common.ParentPathRole)[3]
        else:
            asset = None

        sg_properties = shotgun.get_properties(server, job, root, asset)
        for url in shotgun.get_urls(sg_properties):
            self.menu[k][key()] = {
                'text': url,
                'icon': self.get_icon('shotgun'),
                'action': functools.partial(QtGui.QDesktopServices.openUrl, QtCore.QUrl(url))
            }

    def sg_link_bookmark_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        asset = None

        sg_properties = shotgun.get_properties(server, job, root, asset)
        self.menu[key()] = {
            'text': u'Link with Shotgun...',
            'icon': self.get_icon('shotgun'),
            'action': functools.partial(sg_actions.link_bookmark_entity, sg_properties)
        }

    def sg_link_asset_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return

        server, job, root, asset = self.index.data(common.ParentPathRole)[0:4]

        k = u'Link with Shotgun...'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu[k + ':icon'] = self.get_icon('shotgun')

        sg_properties = shotgun.get_properties(server, job, root, asset)
        for entity_type in (shotgun.AssetEntity, shotgun.ShotEntity, shotgun.SequenceEntity):
            _sg_properties = sg_properties.copy()
            _sg_properties[shotgun.SGAssetEntityType] = entity_type
            self.menu[k][key()] = {
                'text': u'Link {}...'.format(entity_type.title()),
                'icon': self.get_icon('shotgun'),
                'action': functools.partial(sg_actions.link_asset_entity, _sg_properties)
            }
