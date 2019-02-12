# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Module defines the QListWidget items used to browse the projects and the files
found by the collector classes.

"""

import re
import functools
from functools import wraps
import collections
from PySide2 import QtWidgets, QtGui, QtCore

import browser.common as common
import browser.editors as editors
from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite
from browser.settings import local_settings
from browser.settings import AssetSettings
from browser.capture import ScreenGrabber


def contextmenu(func):
    """Decorator to create a menu set."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        menu_set = collections.OrderedDict()
        menu_set['__separator__'] = None
        menu_set = func(self, menu_set, *args, **kwargs)
        if not isinstance(menu_set, collections.OrderedDict):
            raise ValueError(
                'Invalid return type from context menu function, expected an OrderedDict, got {}'.format(type(menu_set)))
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
        self.setToolTipsVisible(True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.NoDropShadowWindowHint |
            QtCore.Qt.Popup |
            QtCore.Qt.FramelessWindowHint
        )

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

            metrics = QtGui.QFontMetrics(self.font())
            text = metrics.elidedText(
                action.text(),
                QtCore.Qt.ElideMiddle,
                self.width() - 32 - 10  # padding set in the stylesheet
            )
            action.setText(text)

    @contextmenu
    def add_sort_menu(self, menu_set):
        """Creates the menu needed to set the sort-order of the list."""
        sort_menu_icon = common.get_rsc_pixmap(
            u'sort', common.FAVOURITE, common.INLINE_ICON_SIZE)
        arrow_up_icon = common.get_rsc_pixmap(
            u'arrow_up', common.FAVOURITE, common.INLINE_ICON_SIZE)
        arrow_down_icon = common.get_rsc_pixmap(
            u'arrow_down', common.FAVOURITE, common.INLINE_ICON_SIZE)
        item_off_icon = common.get_rsc_pixmap(
            u'item_off', common.TEXT, common.INLINE_ICON_SIZE)
        item_on_icon = common.get_rsc_pixmap(
            u'item_on', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)

        sort_by_name = self.parent().model().sortkey == common.SortByName
        sort_modified = self.parent().model().sortkey == common.SortByLastModified
        sort_created = self.parent().model().sortkey == common.SortByLastCreated
        sort_size = self.parent().model().sortkey == common.SortBySize

        menu_set[u'Sort'] = collections.OrderedDict()
        menu_set[u'Sort:icon'] = sort_menu_icon
        menu_set[u'Sort'][u'Order'] = {
            u'text': u'Ascending' if self.parent().model().sortorder else u'Descending',
            u'ckeckable': True,
            u'checked': True if self.parent().model().sortorder else False,
            u'icon': arrow_down_icon if self.parent().model().sortorder else arrow_up_icon,
            u'action': functools.partial(self.parent().model().set_sortorder,
                                         not self.parent().model().sortorder)
        }

        menu_set[u'Sort'][u'separator'] = {}

        menu_set[u'Sort'][u'Name'] = {
            u'icon': item_on_icon if sort_by_name else item_off_icon,
            u'ckeckable': True,
            u'checked': True if sort_by_name else False,
            u'action': functools.partial(
                self.parent().model().set_sortkey, common.SortByName)
        }
        menu_set[u'Sort'][u'Date modified'] = {
            u'icon': item_on_icon if sort_modified else item_off_icon,
            u'ckeckable': True,
            u'checked': True if sort_modified else False,
            u'action': functools.partial(self.parent().model().set_sortkey,
                                         common.SortByLastModified)
        }
        menu_set[u'Sort'][u'Date created'] = {
            u'icon': item_on_icon if sort_created else item_off_icon,
            u'ckeckable': True,
            u'checked': True if sort_created else False,
            u'action': functools.partial(self.parent().model().set_sortkey,
                                         common.SortByLastCreated)
        }
        menu_set[u'Sort'][u'Size'] = {
            u'icon': item_on_icon if sort_size else item_off_icon,
            u'ckeckable': True,
            u'checked': True if sort_size else False,
            u'action': functools.partial(self.parent().model().set_sortkey,
                                         common.SortBySize)
        }
        return menu_set

    @contextmenu
    def add_reveal_folder_menu(self, menu_set):
        """Creates a menu containing"""
        folder_icon = common.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        folder_icon2 = common.get_rsc_pixmap(
            u'folder', common.FAVOURITE, common.INLINE_ICON_SIZE)

        key = u'Show in File Manager'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = folder_icon

        if len(self.index.data(common.ParentRole)) >= 4:
            file_info = QtCore.QFileInfo(
                self.index.data(QtCore.Qt.StatusTipRole))
            menu_set[key][u'file'] = {
                u'text': 'Show file',
                u'icon': folder_icon2,
                u'action': functools.partial(
                    common.reveal,
                    u'/'.join(self.index.data(common.ParentRole)))
            }
            path = u'{}/{}/{}/{}'.format(
                self.index.data(common.ParentRole)[0],
                self.index.data(common.ParentRole)[1],
                self.index.data(common.ParentRole)[2],
                self.index.data(common.ParentRole)[3],
            )
            menu_set[key][u'asset'] = {
                u'text': 'Show asset',
                u'icon': folder_icon2,
                u'action': functools.partial(
                    common.reveal, path)
            }
        elif len(self.index.data(common.ParentRole)) == 3:
            menu_set[key][u'asset'] = {
                u'text': 'Show asset',
                u'icon': folder_icon2,
                u'action': functools.partial(common.reveal,
                                             self.index.data(QtCore.Qt.StatusTipRole))
            }
        menu_set[key][u'root'] = {
            u'text': 'Show bookmark',
            u'icon': folder_icon2,
            u'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo(u'{}/{}/{}'.format(
                    self.index.data(common.ParentRole)[0],
                    self.index.data(common.ParentRole)[1],
                    self.index.data(common.ParentRole)[2]
                )).filePath()),
        }
        menu_set[key][u'separator.'] = {}
        menu_set[key][u'job'] = {
            u'text': 'Show job folder',
            u'icon': folder_icon2,
            u'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo(u'{}/{}'.format(
                    self.index.data(common.ParentRole)[0],
                    self.index.data(common.ParentRole)[1]
                )).filePath())
        }

        menu_set[key][u'separator'] = {}

        dir_ = QtCore.QDir(u'/'.join(self.index.data(common.ParentRole)))
        dir_.setFilter(QtCore.QDir.NoDotAndDotDot |
                       QtCore.QDir.Dirs |
                       QtCore.QDir.Readable)
        it = QtCore.QDirIterator(
            dir_, flags=QtCore.QDirIterator.NoIteratorFlags)
        items = []
        while it.hasNext():
            it.next()
            items.append(it.fileInfo())

        if not self.parent().model().sortorder:
            items = sorted(
                items, key=common.sort_keys[self.parent().model().sortkey])
        else:
            items = list(
                reversed(sorted(items, key=common.sort_keys[self.parent().model().sortkey])))

        for file_info in items:
            if file_info.fileName()[0] == u'.':
                continue
            if not file_info.isDir():
                continue

            menu_set[key][file_info.fileName()] = {
                u'text': file_info.fileName().upper(),
                u'icon': folder_icon,
                u'action': functools.partial(
                    common.reveal,
                    file_info.filePath())
            }
        return menu_set

    @contextmenu
    def add_copy_menu(self, menu_set):
        """Menu containing the subfolders of the selected item."""
        copy_icon = common.get_rsc_pixmap(
            u'copy', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        copy_icon2 = common.get_rsc_pixmap(
            u'copy', common.FAVOURITE, common.INLINE_ICON_SIZE)

        path = self.index.data(QtCore.Qt.StatusTipRole)
        if self.parent().model().sourceModel().get_location() == common.RendersFolder:
            path = common.get_sequence_startpath(path)
        else:
            path = common.get_sequence_endpath(path)

        url = QtCore.QUrl().fromLocalFile(path).toString()

        key = u'Copy path'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = copy_icon

        menu_set[key][u'windows1'] = {
            u'text': 'Windows  -  \\\\back\\slashes',
            u'icon': copy_icon2,
            u'action': functools.partial(
                QtGui.QClipboard().setText,
                QtCore.QDir.toNativeSeparators(path))
        }
        menu_set[key][u'windows2'] = {
            u'text': 'Windows  -  //forward/slashes',
            u'icon': copy_icon2,
            u'action': functools.partial(QtGui.QClipboard().setText, path)
        }
        menu_set[key][u'slack'] = {
            u'text': 'URL  -  file://Slack/friendly',
            u'icon': copy_icon2,
            u'action': functools.partial(QtGui.QClipboard().setText, url)
        }
        menu_set[key][u'macos'] = {
            u'text': 'SMB  -  smb://MacOS/path',
            u'icon': copy_icon2,
            u'action': functools.partial(
                QtGui.QClipboard().setText,
                url.replace(u'file://', 'smb://'))
        }
        return menu_set

    @contextmenu
    def add_mode_toggles_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        favourite_on_icon = common.get_rsc_pixmap(
            u'favourite', common.FAVOURITE, common.INLINE_ICON_SIZE)
        favourite_off_icon = common.get_rsc_pixmap(
            u'favourite', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        archived_on_icon = common.get_rsc_pixmap(
            u'archived', common.FAVOURITE, common.INLINE_ICON_SIZE)
        archived_off_icon = common.get_rsc_pixmap(
            u'archived', common.TEXT, common.INLINE_ICON_SIZE)

        favourite = self.index.flags() & MarkedAsFavourite
        archived = self.index.flags() & MarkedAsArchived
        source_index = self.parent().model().mapToSource(self.index)

        menu_set[u'separator'] = {}
        if self.__class__.__name__ == u'BookmarksWidgetContextMenu':
            text = u'Remove bookmark'
        else:
            text = u'Enable' if archived else 'Disable'
        menu_set[u'archived'] = {
            u'text': text,
            u'icon': archived_off_icon if archived else archived_on_icon,
            u'checkable': True,
            u'checked': archived,
            u'action': functools.partial(self.parent().toggle_archived, index=source_index, state=not archived)
        }
        menu_set[u'favourite'] = {
            u'text': 'Remove from favourites' if favourite else 'Mark as favourite',
            u'icon': favourite_off_icon if favourite else favourite_on_icon,
            u'checkable': True,
            u'checked': favourite,
            u'action': functools.partial(self.parent().toggle_favourite, index=source_index, state=not favourite)
        }
        return menu_set

    @contextmenu
    def add_display_toggles_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        item_on = common.get_rsc_pixmap(
            u'item_on', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        item_off = common.get_rsc_pixmap(
            u'item_off', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)

        favourite = self.parent().model().get_filtermode(u'favourite')
        archived = self.parent().model().get_filtermode(u'archived')

        menu_set[u'toggle_favoruites'] = {
            u'text': 'Show favourites only',
            u'icon': item_on if favourite else item_off,
            u'checkable': True,
            u'checked': favourite,
            u'action':
                functools.partial(
                    self.parent().model().set_filtermode,
                    u'favourite',
                    not favourite
                ),
        }
        menu_set[u'toggle_archived'] = {
            u'text': 'Show archived items',
            u'icon': item_on if archived else item_off,
            u'checkable': True,
            u'checked': archived,
            u'disabled': favourite,
            u'action':
                functools.partial(
                    self.parent().model().set_filtermode,
                    u'archived',
                    not archived
                ),
        }
        return menu_set

    @contextmenu
    def add_refresh_menu(self, menu_set):
        menu_set[u'Refresh'] = {
            u'action': self.parent().refresh
        }
        if self.index:
            menu_set[u'Activate'] = {
                u'action': self.parent().activate_current_index
            }
        return menu_set

    @contextmenu
    def add_thumbnail_menu(self, menu_set):
        """Menu for thumbnail operations."""
        capture_thumbnail_pixmap = common.get_rsc_pixmap(
            u'capture_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        pick_thumbnail_pixmap = common.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        pick_thumbnail_pixmap = common.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        remove_thumbnail_pixmap = common.get_rsc_pixmap(
            u'todo_remove', common.FAVOURITE, common.INLINE_ICON_SIZE)
        show_thumbnail = common.get_rsc_pixmap(
            u'active', common.FAVOURITE, common.INLINE_ICON_SIZE)

        key = u'Thumbnail'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = capture_thumbnail_pixmap

        settings = AssetSettings(self.index)

        if QtCore.QFileInfo(settings.thumbnail_path()).exists():
            menu_set[key][u'Show thumbnail'] = {
                u'icon': show_thumbnail,
                u'action': functools.partial(
                    editors.ThumbnailViewer,
                    self.index,
                    parent=self.parent()
                )
            }
            menu_set[key][u'separator'] = {}
        menu_set[key][u'Capture new'] = {
            u'icon': capture_thumbnail_pixmap,
            u'action': self.parent().capture_thumbnail
        }
        menu_set[key][u'Pick new'] = {
            u'icon': pick_thumbnail_pixmap,
            u'action': functools.partial(
                editors.ThumbnailEditor,
                self.index
            )
        }
        if QtCore.QFileInfo(settings.thumbnail_path()).exists():
            menu_set[key][u'separator.'] = {}
            menu_set[key][u'Remove'] = {
                u'action': self.parent().remove_thumbnail,
                u'icon': remove_thumbnail_pixmap
            }
        return menu_set

    @contextmenu
    def add_add_bookmark_menu(self, menu_set):
        menu_set[u'Add bookmark'] = {
            u'text': 'Add bookmark',
            u'action': self.parent().show_add_bookmark_widget
        }
        return menu_set

    @contextmenu
    def add_collapse_sequence_menu(self, menu_set):
        """Adds the menu needed to change context"""
        if self.parent().model().sourceModel().get_location() == common.RendersFolder:
            return menu_set # Render sequences are always collapsed

        expand_pixmap = common.get_rsc_pixmap(
            u'expand', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        collapse_pixmap = common.get_rsc_pixmap(
            u'collapse', common.FAVOURITE, common.INLINE_ICON_SIZE)
        collapsed = self.parent().model().sourceModel().is_grouped()

        menu_set[u'collapse'] = {
            u'text': 'Show individual files' if collapsed else 'Group sequences together',
            u'icon': expand_pixmap if collapsed else collapse_pixmap,
            u'checkable': True,
            u'checked': collapsed,
            u'action': functools.partial(
                self.parent().model().sourceModel().set_grouped, not collapsed)
        }
        return menu_set

    @contextmenu
    def add_location_toggles_menu(self, menu_set):
        """Adds the menu needed to change context"""
        locations_icon_pixmap = common.get_rsc_pixmap(
            u'location', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        item_on_pixmap = common.get_rsc_pixmap(
            u'item_on', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        item_off_pixmap = common.get_rsc_pixmap(
            u'item_off', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)

        key = u'Switch location'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = locations_icon_pixmap

        for k in sorted(list(common.NameFilters)):
            checked = self.parent().model().sourceModel().get_location() == k
            menu_set[key][k] = {
                u'text': k.title(),
                u'checkable': True,
                u'checked': checked,
                u'icon': item_on_pixmap if checked else item_off_pixmap,
                u'action': functools.partial(self.parent().model().sourceModel().set_location, k)
            }
        return menu_set


def flagsmethod(func):
    """Decorator to make sure the ItemFlag values are always correct."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        if not res:
            res = QtCore.Qt.NoItemFlags
        return res
    return func_wrapper


class BaseModel(QtCore.QAbstractItemModel):
    """Flat base-model for storing items."""

    grouppingChanged = QtCore.Signal()  # The sequence view mode

    # Emit before the model is about to change
    modelDataAboutToChange = QtCore.Signal()
    """Signal emited before the model data changes."""
    modelDataResetRequested = QtCore.Signal()
    activeBookmarkChanged = QtCore.Signal(tuple)
    activeAssetChanged = QtCore.Signal(tuple)
    activeLocationChanged = QtCore.Signal(basestring)
    activeFileChanged = QtCore.Signal(basestring)

    def __init__(self, parent=None):
        super(BaseModel, self).__init__(parent=parent)
        self._model_data = {
            common.RendersFolder: {True: {}, False: {}},
            common.ScenesFolder: {True: {}, False: {}},
            common.TexturesFolder: {True: {}, False: {}},
            common.ExportsFolder: {True: {}, False: {}},
        }
        self.model_data = {}
        self.__initdata__()

    def __resetdata__(self):
        """Resets the internal data."""
        self.modelDataAboutToChange.emit()
        self.beginResetModel()
        self._model_data = {
            common.RendersFolder: {True: {}, False: {}},
            common.ScenesFolder: {True: {}, False: {}},
            common.TexturesFolder: {True: {}, False: {}},
            common.ExportsFolder: {True: {}, False: {}},
        }
        self.model_data = {}
        self.endResetModel()

    def __initdata__(self):
        raise NotImplementedError(u'__initdata__ is abstract')

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(list(self.model_data))

    def index(self, row, column, parent=QtCore.QModelIndex()):
        return self.createIndex(row, 0, parent=parent)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        if index.row() not in self.model_data:
            return None

        if role in self.model_data[index.row()]:
            return self.model_data[index.row()][role]

    @flagsmethod
    def flags(self, index):
        return index.data(common.FlagsRole)

    def parent(self, child):
        return QtCore.QModelIndex()

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        self.model_data[index.row()][role] = data
        self.dataChanged.emit(index, index)

    def switch_location_data(self):
        pass

    def is_grouped(self):
        return False


class FilterProxyModel(QtCore.QSortFilterProxyModel):
    """Proxy model responsible for filtering and sorting data."""

    def __init__(self, parent=None):
        super(FilterProxyModel, self).__init__(parent=parent)
        self.parentwidget = parent
        self.sortkey = self.get_sortkey()  # Alphabetical/Modified...etc.
        self.sortorder = self.get_sortorder()  # Ascending/descending
        self.filterstring = self.get_filterstring()  # Ascending/descending

        self.filter_mode = {
            u'favourite': self.get_filtermode(u'favourite'),
            u'archived': self.get_filtermode(u'archived')
        }

    def get_filterstring(self):
        """Will only display items contaning this string."""
        cls = self.parentwidget.__class__.__name__
        val = local_settings.value(u'widget/{}/filterstring'.format(cls))
        return val if val else u'/'

    def set_filterstring(self, val):
        """Sets and saves the sort-key."""
        cls = self.parentwidget.__class__.__name__
        val = val if val else u'/'
        self.filterstring = val
        local_settings.setValue(u'widget/{}/filterstring'.format(cls), val)
        self.invalidate()

    def get_sortkey(self):
        """The sort-key used to determine the order of the list."""
        cls = self.parentwidget.__class__.__name__
        val = local_settings.value(u'widget/{}/sortkey'.format(cls))
        return int(val) if val else common.SortByName

    def set_sortkey(self, val):
        """Sets and saves the sort-key."""
        cls = self.parentwidget.__class__.__name__
        self.sortkey = val
        local_settings.setValue(u'widget/{}/sortkey'.format(cls), val)

        self.invalidate()

    def get_sortorder(self):
        cls = self.parentwidget.__class__.__name__
        val = local_settings.value(
            u'widget/{}/sortorder'.format(cls))
        return int(val) if val else False

    def set_sortorder(self, val):
        cls = self.parentwidget.__class__.__name__
        self.sortorder = val
        local_settings.setValue(u'widget/{}/sortorder'.format(cls), val)
        self.invalidate()
        self.sort()

    def get_filtermode(self, mode):
        cls = self.parentwidget.__class__.__name__
        val = local_settings.value(u'widget/{}/mode:{}'.format(cls, mode))
        return val if val else False

    def set_filtermode(self, mode, val):
        cls = self.parentwidget.__class__.__name__
        self.filter_mode[mode] = val
        local_settings.setValue(u'widget/{}/mode:{}'.format(cls, mode), val)
        self.invalidateFilter()

    def filterAcceptsColumn(self, source_column, parent=QtCore.QModelIndex()):
        return True

    def filterAcceptsRow(self, source_row, parent=QtCore.QModelIndex()):
        """The main method used to filter the elements using the flags and the filter string."""
        index = self.sourceModel().index(source_row, 0, parent=QtCore.QModelIndex())
        archived = index.flags() & MarkedAsArchived
        favourite = index.flags() & MarkedAsFavourite

        if self.filterstring.lower() not in index.data(QtCore.Qt.StatusTipRole).lower():
            return False
        if archived and not self.filter_mode[u'archived']:
            return False
        if not favourite and self.filter_mode[u'favourite']:
            return False
        return True

    def sort(self, column=0):
        if self.sortorder:
            super(FilterProxyModel, self).sort(
                column, order=QtCore.Qt.AscendingOrder)
        else:
            super(FilterProxyModel, self).sort(
                column, order=QtCore.Qt.DescendingOrder)

    def lessThan(self, source_left, source_right):
        """The main method responsible for sorting the items."""
        left_info = QtCore.QFileInfo(source_left.data(QtCore.Qt.StatusTipRole))
        right_info = QtCore.QFileInfo(
            source_right.data(QtCore.Qt.StatusTipRole))

        return common.sort_keys[self.sortkey](left_info) < common.sort_keys[self.sortkey](right_info)


class BaseListWidget(QtWidgets.QListView):
    """Defines the base of the ``Asset``, ``Bookmark`` and ``File`` list widgets."""

    customContextMenuRequested = QtCore.Signal(
        QtCore.QModelIndex, QtCore.QObject)

    # Signals
    sizeChanged = QtCore.Signal(QtCore.QSize)

    def __init__(self, model, parent=None):
        super(BaseListWidget, self).__init__(parent=parent)
        proxy_model = FilterProxyModel(parent=self)
        proxy_model.setSourceModel(model)
        self.setModel(proxy_model)
        self.model().sort()

        self._previouspathtoselect = None
        self.model().sourceModel().modelDataAboutToChange.connect(self.store_previous_path)
        self.model().sourceModel().grouppingChanged.connect(self.reselect_previous_path)

        self._location = None

        self.collector_count = 0
        self.context_menu_cls = BaseContextMenu

        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformItemSizes(True)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.installEventFilter(self)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        common.set_custom_stylesheet(self)

        # Keyboard search timer and placeholder string.
        self.timer = QtCore.QTimer(parent=self)
        app = QtCore.QCoreApplication.instance()
        self.timer.setInterval(app.keyboardInputInterval())
        self.timer.setSingleShot(True)
        self.timed_search_string = u''

    def store_previous_path(self):
        """Saves the currently selected path."""
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            self._previouspathtoselect = None
            return
        self._previouspathtoselect = index.data(QtCore.Qt.StatusTipRole)

    def get_item_filter(self):
        """A path segment used to filter the collected items."""
        val = local_settings.value(
            u'widget/{}/filter'.format(self.__class__.__name__))
        return val if val else u'/'

    def set_item_filter(self, val):
        cls = self.__class__.__name__
        local_settings.setValue(u'widget/{}/filter'.format(cls), val)

    def toggle_favourite(self, index=None, state=None):
        """Toggles the ``favourite`` state of the current item.
        If `item` and/or `state` are set explicity, those values will be used
        instead of the currentItem.

        Args:
            item (QListWidgetItem): The item to change.
            state (None or bool): The state to set.

        """
        if not index:
            index = self.selectionModel().currentIndex()
            index = self.model().mapToSource(index)

        if not index.isValid():
            return

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))

        # Favouriting archived items are not allowed
        archived = index.flags() & MarkedAsArchived
        if archived:
            return

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        if file_info.filePath() in favourites:
            if state is None or state is False:  # clears flag
                self.model().sourceModel().setData(
                    index,
                    index.flags() & ~MarkedAsFavourite,
                    role=common.FlagsRole
                )
                favourites.remove(file_info.filePath())
        else:
            if state is None or state is True:  # adds flag
                favourites.append(file_info.filePath())
                self.model().sourceModel().setData(
                    index,
                    index.flags() | MarkedAsFavourite,
                    role=common.FlagsRole
                )

        local_settings.setValue(u'favourites', favourites)

    def toggle_archived(self, index=None, state=None):
        """Toggles the ``archived`` state of the current item.
        If `item` and/or `state` are set explicity, those values will be used
        instead of the currentItem.

        Note:
            Archived items are automatically removed from ``favourites``.

        Args:
            item (QListWidgetItem): The explicit item to change.
            state (None or bool): The explicit state to set.

        """
        if not index:
            index = self.selectionModel().currentIndex()
            index = self.model().mapToSource(index)

        if not index.isValid():
            return

        archived = index.flags() & MarkedAsArchived

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        settings = AssetSettings(index)

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        if archived:
            if state is None or state is False:  # clears flag
                self.model().sourceModel().setData(
                    index,
                    index.flags() & ~MarkedAsArchived,
                    role=common.FlagsRole
                )
                settings.setValue(u'config/archived', False)
        else:
            if state is None or state is True:  # adds flag
                settings.setValue(u'config/archived', True)
                self.model().sourceModel().setData(
                    index,
                    index.flags() | MarkedAsArchived,
                    role=common.FlagsRole
                )
                if file_info.filePath() in favourites:
                    self.model().sourceModel().setData(
                        index,
                        index.flags() & ~MarkedAsFavourite,
                        role=common.FlagsRole
                    )
                    favourites.remove(file_info.filePath())
                    local_settings.setValue(u'favourites', favourites)

    def capture_thumbnail(self):
        """Captures a thumbnail for the current item using ScreenGrabber."""
        index = self.selectionModel().currentIndex()

        if not index.isValid():
            return

        settings = AssetSettings(index)
        # Making config folder
        conf_dir = QtCore.QFileInfo(settings.conf_path())
        if not conf_dir.exists():
            QtCore.QDir().mkpath(conf_dir.path())

        # Saves the iamge
        path = ScreenGrabber.capture(
            output_path=settings.thumbnail_path())
        if not path:
            return

        common.delete_image(settings.thumbnail_path(), delete_file=False)
        height = self.visualRect(index).height() - 2
        common.cache_image(settings.thumbnail_path(), height)

        self.repaint()

    def remove_thumbnail(self):
        """Deletes the given thumbnail."""
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        settings = AssetSettings(index)
        common.delete_image(settings.thumbnail_path())
        height = self.visualRect(index).height() - 2
        common.cache_image(settings.thumbnail_path(), height)

        self.repaint()

    def refresh(self):
        """Refreshes the model data, and the sorting."""
        self.model().sourceModel().modelDataAboutToChange.emit()
        self.model().sourceModel().beginResetModel()
        self.model().sourceModel().__initdata__()
        self.model().sourceModel().switch_location_data()
        self.model().sourceModel().endResetModel()
        self.model().invalidate()
        self.model().sort()
        self.reselect_previous_path()

    def reselect_previous_path(self):
        """Reselects the index based on the path given."""
        if not self._previouspathtoselect:
            return

        path = common.get_sequence_endpath(self._previouspathtoselect)

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())

            data = index.data(QtCore.Qt.StatusTipRole)
            if not data:
                continue

            if path != common.get_sequence_endpath(data):
                continue

            self.selectionModel().setCurrentIndex(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            self.scrollTo(index)

    def action_on_enter_key(self):
        self.activate_current_index()

    def key_down(self):
        """Custom action tpo perform when the `down` arrow is pressed
        on the keyboard.

        """
        sel = self.selectionModel()
        current_index = self.selectionModel().currentIndex()
        first_index = self.model().index(0, 0, parent=QtCore.QModelIndex())
        last_index = self.model().index(self.model().rowCount() -
                                        1, 0, parent=QtCore.QModelIndex())

        if first_index == last_index:
            return

        if not current_index.isValid():  # No selection
            sel.setCurrentIndex(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return
        if current_index == last_index:  # Last item is selected
            sel.setCurrentIndex(
                first_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return
        for n in xrange(self.model().rowCount()):
            if current_index.row() >= n:
                continue
            sel.setCurrentIndex(
                self.model().index(n, 0, parent=QtCore.QModelIndex()),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            break

    def key_up(self):
        """Custom action to perform when the `up` arrow is pressed
        on the keyboard.

        """
        sel = self.selectionModel()
        current_index = self.selectionModel().currentIndex()
        first_index = self.model().index(0, 0, parent=QtCore.QModelIndex())
        last_index = self.model().index(self.model().rowCount() -
                                        1, 0, parent=QtCore.QModelIndex())

        if first_index == last_index:
            return

        if not current_index.isValid():  # No selection
            sel.setCurrentIndex(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return
        if current_index == first_index:  # First item is selected
            sel.setCurrentIndex(
                last_index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return

        for n in reversed(xrange(self.model().rowCount())):  # Stepping back
            if current_index.row() <= n:
                continue
            sel.setCurrentIndex(
                self.model().index(n, 0, parent=QtCore.QModelIndex()),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            break

    def key_tab(self):
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            index = self.model().index(0, 0, parent=QtCore.QModelIndex())

        widget = editors.DescriptionEditorWidget(index, parent=self)
        widget.show()

    def keyPressEvent(self, event):
        """Customized key actions.

        We're defining the default behaviour of the list-items here, including
        defining the actions needed to navigate the list using keyboard presses.

        """
        numpad_modifier = event.modifiers() & QtCore.Qt.KeypadModifier
        no_modifier = event.modifiers() == QtCore.Qt.NoModifier
        if no_modifier or numpad_modifier:
            if event.key() == QtCore.Qt.Key_Escape:
                pass
            elif event.key() == QtCore.Qt.Key_Down:
                self.key_down()
            elif event.key() == QtCore.Qt.Key_Up:
                self.key_up()
            elif (event.key() == QtCore.Qt.Key_Return) or (event.key() == QtCore.Qt.Key_Enter):
                self.action_on_enter_key()
            elif event.key() == QtCore.Qt.Key_Tab:
                self.key_down()
                self.key_tab()
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.key_up()
                self.key_tab()
            else:  # keyboard search and select
                if not self.timer.isActive():
                    self.timed_search_string = u''
                    self.timer.start()

                self.timed_search_string += event.text()
                self.timer.start()  # restarting timer on input

                sel = self.selectionModel()
                for n in xrange(self.model().rowCount()):
                    index = self.model().index(n, 0, parent=QtCore.QModelIndex())

                    # When only one key is pressed we want to cycle through
                    # only items starting with that letter:
                    if len(self.timed_search_string) == 1:
                        if n <= sel.currentIndex().row():
                            continue

                        if index.data(QtCore.Qt.DisplayRole)[0].lower() == self.timed_search_string.lower():
                            sel.setCurrentIndex(
                                index,
                                QtCore.QItemSelectionModel.ClearAndSelect
                            )
                            break
                    else:
                        match = re.search(
                            self.timed_search_string,
                            index.data(QtCore.Qt.DisplayRole),
                            flags=re.IGNORECASE
                        )
                        if match:
                            sel.setCurrentIndex(
                                index,
                                QtCore.QItemSelectionModel.ClearAndSelect
                            )
                            break

        if event.modifiers() & QtCore.Qt.ControlModifier:
            pass

        if event.modifiers() & QtCore.Qt.ShiftModifier:
            if event.key() == QtCore.Qt.Key_Tab:
                self.key_up()
                self.key_tab()
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.key_up()
                self.key_tab()

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())

        width = self.viewport().geometry().width()
        width = (width * 0.5) if width > 400 else width
        width = width - common.INDICATOR_WIDTH

        # Custom context menu
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier
        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit(index, self)
            return

        widget = self.context_menu_cls(index, parent=self)

        if index.isValid():
            rect = self.visualRect(index)
            widget.move(
                self.viewport().mapToGlobal(rect.bottomLeft()).x(),
                self.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
            )
        else:
            widget.move(QtGui.QCursor().pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH, widget.y())
        common.move_widget_to_available_geo(widget)
        widget.exec_()

    def active_index(self):
        """Return the ``active`` item.

        The active item is indicated by the ``MarkedAsActive`` flag.
        If no item has been flagged as `active`, returns ``None``.

        """
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                return index
        return QtCore.QModelIndex()

    def unmark_active_index(self):
        """Unsets the active flag."""
        source_index = self.model().mapToSource(self.active_index())
        if not source_index.isValid():
            return

        self.model().sourceModel().setData(
            source_index,
            source_index.flags() & ~MarkedAsActive,
            role=common.FlagsRole
        )

    def activate_current_index(self):
        """Sets the current index as ``active``.

        Note:
            The method doesn't alter the config files or emits signals,
            merely sets the item flags. Make sure to implement that in the subclass.

        """
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return False
        if index.flags() == QtCore.Qt.NoItemFlags:
            return False
        if index.flags() & MarkedAsArchived:
            return False

        self.unmark_active_index()

        source_index = self.model().mapToSource(index)
        self.model().sourceModel().setData(
            source_index,
            source_index.flags() | MarkedAsActive,
            role=common.FlagsRole
        )
        return True

    def select_active_index(self):
        """Selects the active item."""
        self.selectionModel().setCurrentIndex(
            self.active_index(),
            QtCore.QItemSelectionModel.ClearAndSelect
        )

    def showEvent(self, event):
        """Show event will set the size of the widget."""

        self.select_active_index()

        idx = local_settings.value(
            u'widget/{}/selected_row'.format(self.__class__.__name__),
        )
        if not idx:
            idx = 0
        if self.model().rowCount():
            self.selectionModel().setCurrentIndex(
                self.model().index(idx, 0, parent=QtCore.QModelIndex()),
                QtCore.QItemSelectionModel.ClearAndSelect
            )

        super(BaseListWidget, self).showEvent(event)

    def hideEvent(self, event):
        """We're saving the selection upon hiding the widget."""
        local_settings.setValue(
            u'widget/{}/selected_row'.format(self.__class__.__name__),
            self.selectionModel().currentIndex().row()
        )

    def resizeEvent(self, event):
        """Custom resize event will emit the ``sizeChanged`` signal."""
        self.sizeChanged.emit(event.size())
        super(BaseListWidget, self).resizeEvent(event)

    def mousePressEvent(self, event):
        """Deselecting item when the index is invalid."""
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.selectionModel().setCurrentIndex(
                QtCore.QModelIndex(),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
        super(BaseListWidget, self).mousePressEvent(event)

    def eventFilter(self, widget, event):
        """Custom paint event used to paint the background of the list."""
        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)

            sizehint = self.itemDelegate().sizeHint(
                self.viewOptions(), QtCore.QModelIndex())

            rect = QtCore.QRect(
                common.INDICATOR_WIDTH,
                2,
                self.viewport().rect().width() - (common.INDICATOR_WIDTH * 2),
                sizehint.height() - common.INDICATOR_WIDTH
            )

            favourite_mode = self.model().filter_mode[u'favourite']

            text_rect = QtCore.QRect(rect)
            text_rect.setLeft(rect.left() + rect.height() + common.MARGIN)
            text_rect.setRight(rect.right() - common.MARGIN)

            painter.setRenderHints(
                QtGui.QPainter.TextAntialiasing |
                QtGui.QPainter.Antialiasing |
                QtGui.QPainter.SmoothPixmapTransform,
                on=True
            )

            painter.setPen(QtCore.Qt.NoPen)
            font = QtGui.QFont(common.PrimaryFont)
            font.setPointSize(8)
            painter.setFont(font)

            for n in xrange((self.height() / sizehint.height()) + 1):
                if n >= self.model().rowCount():  # Empty items
                    rect_ = QtCore.QRect(rect)
                    rect_.setWidth(sizehint.height() - 2)
                    painter.setBrush(QtGui.QBrush(
                        QtGui.QColor(100, 100, 100, 5)))
                    # painter.drawRect(rect_)
                    # painter.drawRect(rect)
                if n == 0 and not favourite_mode:  # Empty model
                    painter.setPen(common.TEXT_DISABLED)
                    painter.drawText(
                        text_rect,
                        QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
                        u'  No items to show.'
                    )
                    painter.setPen(QtCore.Qt.NoPen)
                elif n == self.model().rowCount():  # filter mode
                    if favourite_mode:
                        painter.setPen(common.SECONDARY_TEXT)
                        painter.drawText(
                            text_rect,
                            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
                            u'{} items are hidden'.format(
                                self.model().sourceModel().rowCount() - self.model().rowCount())
                        )
                        painter.setPen(QtCore.Qt.NoPen)

                text_rect.moveTop(text_rect.top() + sizehint.height())
                rect.moveTop(rect.top() + sizehint.height())

            painter.end()
            return True
        return False


class BaseInlineIconWidget(BaseListWidget):
    """Multi-toggle capable widget with clickable in-line icons."""

    def __init__(self, model, parent=None):
        super(BaseInlineIconWidget, self).__init__(model, parent=parent)
        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def inline_icons_count(self):
        """The numberof inline icons."""
        raise NotImplementedError(u'method is abstract.')

    def _reset_multitoggle(self):
        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

    def mousePressEvent(self, event):
        """The custom mousePressEvent initiates the multi-toggle operation.
        Only the `favourite` and `archived` buttons are multi-toggle capable."""
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)

        if self.viewport().width() < 360.0:
            return super(BaseInlineIconWidget, self).mousePressEvent(event)

        self._reset_multitoggle()

        for n in xrange(self.inline_icons_count()):
            _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                rect, common.INLINE_ICON_SIZE, n)

            # Beginning multi-toggle operation
            if not bg_rect.contains(event.pos()):
                continue

            self.multi_toggle_pos = event.pos()
            if n == 0:  # Favourite button
                self.multi_toggle_state = not index.flags() & MarkedAsFavourite
            elif n == 1:  # Archive button
                self.multi_toggle_state = not index.flags() & MarkedAsArchived
            elif n == 2:  # Reveal button
                continue
            elif n == 3:  # Todo button
                continue

            self.multi_toggle_idx = n
            return True

        return super(BaseInlineIconWidget, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Inline-button methods are triggered here."""
        index = self.indexAt(event.pos())
        source_index = self.model().mapToSource(index)
        rect = self.visualRect(index)
        idx = index.row()

        if self.viewport().width() < 360.0:
            return super(BaseInlineIconWidget, self).mouseReleaseEvent(event)

        # Cheking the button
        if idx in self.multi_toggle_items:
            self._reset_multitoggle()
            return super(BaseInlineIconWidget, self).mouseReleaseEvent(event)

        for n in xrange(self.inline_icons_count()):
            _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                rect, common.INLINE_ICON_SIZE, n)

            if not bg_rect.contains(event.pos()):
                continue

            if n == 0:
                self.toggle_favourite(index=source_index)
                break
            elif n == 1:
                self.toggle_archived(index=source_index)
                break
            elif n == 2:
                common.reveal(index.data(QtCore.Qt.StatusTipRole))
                break
            elif n == 3:
                self.show_todos()
                break

        self._reset_multitoggle()
        super(BaseInlineIconWidget, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Multi-toggle is handled here."""
        if self.viewport().width() < 360.0:
            return super(BaseInlineIconWidget, self).mouseMoveEvent(event)

        if self.multi_toggle_pos is None:
            return super(BaseInlineIconWidget, self).mouseMoveEvent(event)

        app_ = QtWidgets.QApplication.instance()
        # if (event.pos() - self.multi_toggle_pos).manhattanLength() < app_.startDragDistance():
        #     return super(BaseInlineIconWidget, self).mouseMoveEvent(event)

        pos = event.pos()
        pos.setX(0)
        index = self.indexAt(pos)
        source_index = self.model().mapToSource(index)
        initial_index = self.indexAt(self.multi_toggle_pos)
        idx = index.row()

        favourite = index.flags() & MarkedAsFavourite
        archived = index.flags() & MarkedAsArchived

        # Filter the current item
        if index == self.multi_toggle_item:
            return

        self.multi_toggle_item = index

        # Before toggling the item, we're saving it's state

        if idx not in self.multi_toggle_items:
            if self.multi_toggle_idx == 0:  # Favourite button
                # A state
                self.multi_toggle_items[idx] = favourite
                # Apply first state
                self.toggle_favourite(
                    index=source_index,
                    state=self.multi_toggle_state
                )
            if self.multi_toggle_idx == 1:  # Archived button
                # A state
                self.multi_toggle_items[idx] = archived
                # Apply first state
                self.toggle_archived(
                    index=source_index,
                    state=self.multi_toggle_state
                )
        else:  # Reset state
            if index == initial_index:
                return
            if self.multi_toggle_idx == 0:  # Favourite button
                self.toggle_favourite(
                    index=source_index,
                    state=self.multi_toggle_items.pop(idx)
                )
            elif self.multi_toggle_idx == 1:  # Favourite button
                self.toggle_archived(
                    index=source_index,
                    state=self.multi_toggle_items.pop(idx)
                )
