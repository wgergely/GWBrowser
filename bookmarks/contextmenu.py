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

        self.separator()

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
            'action': functools.partial(
                actions.change_sorting,
                sortrole,
                not sortorder
            )
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

    def urls_menu(self):
        if not self.index.isValid():
            return
        if not self.index.data(QtCore.Qt.StatusTipRole):
            return

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
            return

        k = u'Open URL...'
        self.menu[k] = collections.OrderedDict()
        self.menu[k + ':icon'] = bookmark_icon

        if shotgun_domain:
            self.menu[k][key()] = {
                'text': u'Domain   |   {}'.format(shotgun_domain),
                'icon': shotgun_icon,
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(shotgun_domain))
            }
            if all((shotgun_id, shotgun_type)):
                self.menu[k][key()] = {
                    'text': u'{}   |   {}'.format(shotgun_type.title(), shotgun_entity_url),
                    'icon': shotgun_icon,
                    'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(shotgun_entity_url))
                }
        if primary_url:
            self.menu[k][key()] = {
                'text': u'Primary URL   |   {}'.format(primary_url),
                'icon': bookmark_icon,
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(primary_url))
            }
        if secondary_url:
            self.menu[k][key()] = {
                'text': u'Secondary URL   |   {}'.format(secondary_url),
                'icon': bookmark_icon,
                'action': lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(secondary_url))
            }

        return

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

        self.separator()

        from .shotgun import shotgun
        sg_properties = shotgun.get_shotgun_properties(
            *self.index.data(common.ParentPathRole)[0:3],
            asset=self.index.data(common.ParentPathRole)[3]
        )
        if all(sg_properties.values()):
            self.menu[k][key()] = {
                'text': u'Create Version...',
                'icon': pixmap,
                'action': show_add_shot_task_widget
            }

            self.menu[k][key()] = {
                'text': u'Publish File...',
                'icon': pixmap,
                'action': show_publish_widget
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

    def mode_toggles_menu(self):
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

    def display_toggles_menu(self):
        item_on = self.get_icon(u'check', color=common.ADD)
        item_off = None

        k = u'List Filters'
        self.menu[k] = collections.OrderedDict()
        self.menu[u'{}:icon'.format(k)] = self.get_icon(u'filter')

        self.menu[k][u'EditSearchFilter'] = {
            'text': u'Edit Search Filter...',
            'icon': self.get_icon(u'filter'),
            'action': actions.toggle_search,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleSearch).key(),
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
            }
        if favourite or all_off:
            self.menu[k][u'favourite'] = {
                'text': u'Show Favourites',
                'icon': item_on if favourite else item_off,
                'disabled': active,
                'action': functools.partial(actions.toggle_flag, common.MarkedAsFavourite, not favourite),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleFavourite).key(),
            }
        if archived or all_off:
            self.menu[k][u'archived'] = {
                'text': u'Show Archived',
                'icon': item_on if archived else item_off,
                'disabled': active if active else favourite,
                'action': functools.partial(actions.toggle_flag, common.MarkedAsArchived, not archived),
                'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.ToggleArchived).key(),
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
            'action': self.parent().parent().parent().topbar.generate_thumbnails_button.clicked,
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

        capture_thumbnail_pixmap = self.get_icon(u'capture_thumbnail')
        pick_thumbnail_pixmap = self.get_icon(u'pick_thumbnail')
        pick_thumbnail_pixmap = self.get_icon(u'pick_thumbnail')
        remove_thumbnail_pixmap = self.get_icon(u'remove', color=common.REMOVE)
        show_thumbnail = self.get_icon(u'active')

        self.menu[u'header'] = {
            'text': u'Thumbnail',
            'disabled': True,
        }

        self.separator()

        server, job, root = self.index.data(common.ParentPathRole)[0:3]
        custom_thumbnail_path = images.get_thumbnail_path(
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
            int(images.THUMBNAIL_IMAGE_SIZE),
            fallback_thumb=self.parent().itemDelegate().fallback_thumb,
            get_path=True
        )

        self.menu[u'Show'] = {
            'icon': show_thumbnail,
            'action': self.parent().key_space
        }

        self.separator()

        source_index = self.index.model().mapToSource(self.index)
        self.menu[u'capture'] = {
            'text': u'Capture Screen',
            'icon': capture_thumbnail_pixmap,
            'action': functools.partial(images.capture, source_index)}

        self.menu[u'file'] = {
            'text': u'Pick...',
            'icon': pick_thumbnail_pixmap,
            'action': functools.partial(
                images.pick, source_index)
        }

        self.menu[u'library'] = {
            'text': u'Pick from library...',
            'icon': pick_thumbnail_pixmap,
            'action': functools.partial(
                images.pick_from_library, source_index)
        }

        self.separator()

        if QtCore.QFileInfo(custom_thumbnail_path).exists():
            self.menu[u'remove'] = {
                'text': u'Remove thumbnail',
                'action': functools.partial(
                    images.remove, source_index),
                'icon': remove_thumbnail_pixmap
            }
            self.menu[u'reveal'] = {
                'text': u'Reveal thumbnail...',
                'action': functools.partial(
                    actions.reveal,
                    custom_thumbnail_path,
                )
            }
        elif QtCore.QFileInfo(thumbnail_path).exists():
            self.menu[u'reveal'] = {
                'text': u'Reveal thumbnail...',
                'action': functools.partial(
                    actions.reveal,
                    thumbnail_path,
                )
            }

    def sg_thumbnail_menu(self):
        if not self.index.isValid():
            return

        from .shotgun import shotgun

        parent_path = self.index.data(common.ParentPathRole)
        asset = parent_path[3] if len(parent_path) > 3 else None

        sg_properties = shotgun.get_shotgun_properties(
            *self.index.data(common.ParentPathRole)[0:3],
            asset=asset
        )
        if not all(sg_properties.values()):
            return

        shotgun_icon = self.get_icon(u'shotgun')

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
        self.menu[k] = collections.OrderedDict()
        self.menu['{}:icon'.format(k)] = shotgun_icon

        if QtCore.QFileInfo(display_thumbnail_path).exists():
            self.menu[k]['Upload thumbnail to Shotgun'] = {
                'action': _upload_thumbnail_to_shotgun,
                'icon': shotgun_icon
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
        newtype = common.SequenceItem if currenttype == common.FileItem else common.FileItem
        groupped = currenttype == common.SequenceItem

        self.menu[uuid.uuid1().get_hex()] = {
            'text': u'Expand Sequences' if groupped else u'Group Sequences',
            'icon': expand_pixmap if groupped else collapse_pixmap,
            'checkable': False,
            'action': functools.partial(
                self.parent().model().sourceModel().dataTypeChanged.emit, newtype)
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
        if not settings.ACTIVE[settings.AssetKey]:
            return
        parent_item = (
            settings.ACTIVE[settings.ServerKey],
            settings.ACTIVE[settings.JobKey],
            settings.ACTIVE[settings.RootKey],
            settings.ACTIVE[settings.AssetKey],
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
        self.menu[u'add_file...'] = {
            'text': u'Add Template File...',
            'icon': self.get_icon(u'add_file', color=common.ADD),
            'action': actions.add_file,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.AddItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.AddItem),
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

        settings_icon = self.get_icon(u'settings')
        copy_icon = self.get_icon(u'copy')

        k = u'Properties'
        if k not in self.menu:
            self.menu[k] = collections.OrderedDict()
            self.menu['{}:icon'.format(k)] = settings_icon

        from .properties import base
        server, job, root = self.index.data(common.ParentPathRole)[0:3]

        self.separator(menu=self.menu[k])
        self.menu[k][key()] = {
            'text': u'Copy Properties',
            'action': functools.partial(
                base.copy_properties,
                server,
                job,
                root,
                table=bookmark_db.BookmarkTable
            ),
            'icon': copy_icon,
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.CopyProperties),
        }

        if not base.CLIPBOARD[bookmark_db.BookmarkTable]:
            return

        self.menu[k][key()] = {
            'text': u'Paste Properties',
            'action': functools.partial(
                base.paste_properties,
                server,
                job,
                root,
                table=bookmark_db.BookmarkTable
            ),
            'icon': copy_icon,
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
            'shortcut': shortcuts.get(shortcuts.MainWidgetShortcuts, shortcuts.EditItem).key(),
            'description': shortcuts.hint(shortcuts.MainWidgetShortcuts, shortcuts.EditItem),
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

        from .shotgun import shotgun

        parent_path = self.parent().model().sourceModel().parent_path()

        sg_properties = shotgun.get_shotgun_properties(*parent_path[0:3])
        if not all((
            sg_properties['shotgun_domain'],
            sg_properties['shotgun_scriptname'],
            sg_properties['shotgun_api_key']
        )):
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
