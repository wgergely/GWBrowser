# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""The base-context menu associated with the BaseListWidget subclasses."""

import functools
from functools import wraps
import collections

from PySide2 import QtWidgets, QtGui, QtCore

import browser.common as common
import browser.editors as editors
from browser.imagecache import ImageCache
import browser.settings as Settings
from browser.settings import AssetSettings


def contextmenu(func):
    """Decorator to create a menu set."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        menu_set = collections.OrderedDict()
        # menu_set['__separator__'] = None
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
        sort_menu_icon = ImageCache.get_rsc_pixmap(
            u'sort', common.FAVOURITE, common.INLINE_ICON_SIZE)
        arrow_up_icon = ImageCache.get_rsc_pixmap(
            u'arrow_up', common.FAVOURITE, common.INLINE_ICON_SIZE)
        arrow_down_icon = ImageCache.get_rsc_pixmap(
            u'arrow_down', common.FAVOURITE, common.INLINE_ICON_SIZE)
        item_off_icon = QtGui.QPixmap()
        item_on_icon = ImageCache.get_rsc_pixmap(
            u'check', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)

        sortorder = self.parent().model().get_sortorder()
        sortkey = self.parent().model().get_sortkey()
        sort_by_name = sortkey == common.SortByName
        sort_modified = sortkey == common.SortByLastModified
        sort_size = sortkey == common.SortBySize

        menu_set[u'Sort'] = collections.OrderedDict()
        menu_set[u'Sort:icon'] = sort_menu_icon
        menu_set[u'Sort'][u'Order'] = {
            u'text': u'Ascending' if sortorder else u'Descending',
            u'ckeckable': True,
            u'checked': True if sortorder else False,
            u'icon': arrow_down_icon if sortorder else arrow_up_icon,
            u'action': functools.partial(self.parent().model().sortOrderChanged.emit, sortkey, not sortorder)
        }

        menu_set[u'Sort'][u'separator'] = {}

        menu_set[u'Sort'][u'Name'] = {
            u'icon': item_on_icon if sort_by_name else item_off_icon,
            u'ckeckable': True,
            u'checked': True if sort_by_name else False,
            u'action': functools.partial(self.parent().model().sortOrderChanged.emit, common.SortByName, sortorder)
        }
        menu_set[u'Sort'][u'Date modified'] = {
            u'icon': item_on_icon if sort_modified else item_off_icon,
            u'ckeckable': True,
            u'checked': True if sort_modified else False,
            u'action': functools.partial(self.parent().model().sortOrderChanged.emit, common.SortByLastModified, sortorder)
        }
        menu_set[u'Sort'][u'Size'] = {
            u'icon': item_on_icon if sort_size else item_off_icon,
            u'ckeckable': True,
            u'checked': True if sort_size else False,
            u'action': functools.partial(self.parent().model().sortOrderChanged.emit, common.SortBySize, sortorder)
        }
        return menu_set

    @contextmenu
    def add_reveal_folder_menu(self, menu_set):
        """Creates a menu containing"""
        folder_icon = ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        folder_icon2 = ImageCache.get_rsc_pixmap(
            u'folder', common.FAVOURITE, common.INLINE_ICON_SIZE)

        key = u'Reveal'
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

        sortkey = self.parent().model().get_sortkey()
        if not sortkey:
            items = sorted(
                items, key=common.sort_keys[common.SortByName])
        else:
            if not self.parent().model().get_sortorder():
                items = sorted(
                    items, key=common.sort_keys[sortkey])
            else:
                items = list(
                    reversed(sorted(items, key=common.sort_keys[sortkey])))

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
        copy_icon = ImageCache.get_rsc_pixmap(
            u'copy', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        copy_icon2 = ImageCache.get_rsc_pixmap(
            u'copy', common.FAVOURITE, common.INLINE_ICON_SIZE)

        path = self.index.data(QtCore.Qt.StatusTipRole)
        if self.parent().model().sourceModel().data_key() == common.RendersFolder:
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
        favourite_on_icon = ImageCache.get_rsc_pixmap(
            u'favourite', common.FAVOURITE, common.INLINE_ICON_SIZE)
        favourite_off_icon = ImageCache.get_rsc_pixmap(
            u'favourite', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        archived_on_icon = ImageCache.get_rsc_pixmap(
            u'archived', common.FAVOURITE, common.INLINE_ICON_SIZE)
        archived_off_icon = ImageCache.get_rsc_pixmap(
            u'archived', common.TEXT, common.INLINE_ICON_SIZE)

        favourite = self.index.flags() & Settings.MarkedAsFavourite
        archived = self.index.flags() & Settings.MarkedAsArchived
        source_index = self.parent().model().mapToSource(self.index)

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
            u'text': 'Remove from favourites' if favourite else 'Favourite',
            u'icon': favourite_off_icon if favourite else favourite_on_icon,
            u'checkable': True,
            u'checked': favourite,
            u'action': functools.partial(self.parent().toggle_favourite, index=source_index, state=not favourite)
        }
        return menu_set

    @contextmenu
    def add_display_toggles_menu(self, menu_set):
        """Ads the menu-items needed to add set favourite or archived status."""
        item_on = ImageCache.get_rsc_pixmap(
            u'check', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        item_off = QtGui.QPixmap()


        favourite = self.parent().model().get_filterflag(Settings.MarkedAsFavourite)
        archived = self.parent().model().get_filterflag(Settings.MarkedAsArchived)
        active = self.parent().model().get_filterflag(Settings.MarkedAsActive)

        menu_set[u'toggle_active'] = {
            u'text': 'Show active only',
            u'icon': item_on if active else item_off,
            u'checkable': True,
            u'checked': active,
            u'disabled': favourite,
            u'action': lambda: self.parent().model().filterFlagChanged.emit(Settings.MarkedAsActive, not active),
        }
        menu_set[u'toggle_favourites'] = {
            u'text': 'Show favourites only',
            u'icon': item_on if favourite else item_off,
            u'checkable': True,
            u'checked': favourite,
            u'disabled': active,
            u'action': lambda: self.parent().model().filterFlagChanged.emit(Settings.MarkedAsFavourite, not favourite),
        }
        menu_set[u'toggle_archived'] = {
            u'text': 'Show disabled',
            u'icon': item_on if archived else item_off,
            u'checkable': True,
            u'setChecked': archived,
            u'disabled': active if active else favourite,
            u'action': lambda: self.parent().model().filterFlagChanged.emit(Settings.MarkedAsArchived, not archived),
        }
        return menu_set

    @contextmenu
    def add_refresh_menu(self, menu_set):
        refresh_pixmap = ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        if self.index.isValid():
            menu_set[u'Activate'] = {
                u'action': lambda: self.parent().activate(self.index)
            }
        menu_set[u'Refresh'] = {
            u'action': self.parent().model().sourceModel().modelDataResetRequested.emit,
            # u'icon': refresh_pixmap
        }

        return menu_set

    @contextmenu
    def add_thumbnail_menu(self, menu_set):
        """Menu for thumbnail operations."""
        capture_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'capture_thumbnail', common.FAVOURITE, common.INLINE_ICON_SIZE)
        pick_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.FAVOURITE, common.INLINE_ICON_SIZE)
        pick_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        remove_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'todo_remove', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        show_thumbnail = ImageCache.get_rsc_pixmap(
            u'active', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        addpixmap = ImageCache.get_rsc_pixmap(
            'todo_add', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)

        key = u'Thumbnail'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = capture_thumbnail_pixmap

        settings = AssetSettings(self.index)
        if QtCore.QFileInfo(settings.thumbnail_path()).exists():
            menu_set[key][u'Show'] = {
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
            u'action': functools.partial(ImageCache.instance().capture, self.index)}

        menu_set[key][u'Pick new'] = {
            u'icon': pick_thumbnail_pixmap,
            u'action': functools.partial(ImageCache.instance().pick, self.index)}

        suffix = QtCore.QFileInfo(self.index.data(
            QtCore.Qt.StatusTipRole)).suffix()
        if suffix in common.get_oiio_namefilters(as_array=True):
            menu_set[key]['_separator_'] = {}

            menu_set[key][u'generatethis'] = {
                u'icon': addpixmap,
                u'text': u'Create',
                u'action': functools.partial(ImageCache.instance().generate_all, (QtCore.QPersistentModelIndex(self.index), ), overwrite=True)}

            def generate_all(overwrite=False):
                if overwrite:
                    mbox = QtWidgets.QMessageBox()
                    mbox.setWindowTitle(u'Re-generate all thumbnails?')
                    mbox.setIcon(QtWidgets.QMessageBox.Warning)
                    mbox.setText(
                        u'Are you sure you want to re-generate all thumbnails?'
                    )
                    mbox.setInformativeText(
                        u'This will overwrite all the custom thumbnails you have set previously.\nThe process is resource-intensive, and might take a while to finish. Continue?')
                    mbox.setStandardButtons(
                        QtWidgets.QMessageBox.SaveAll
                        | QtWidgets.QMessageBox.Cancel
                    )
                    mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
                    if mbox.exec_() == QtWidgets.QMessageBox.Cancel:
                        return

                indexes = []
                for n in xrange(self.parent().model().rowCount()):
                    index = self.parent().model().index(n, 0)
                    indexes.append(QtCore.QPersistentModelIndex(index))
                ImageCache.instance().generate_all(indexes, overwrite=overwrite)

            menu_set[key][u'generatemissing'] = {
                u'icon': addpixmap,
                u'text': u'Create missing',
                u'action': functools.partial(generate_all, overwrite=False)
            }

            menu_set[key][u'generateall'] = {
                u'icon': addpixmap,
                u'text': u'Generate all',
                u'action': functools.partial(generate_all, overwrite=True)
            }

        if QtCore.QFileInfo(settings.thumbnail_path()).exists():
            menu_set[key][u'separator.'] = {}
            menu_set[key][u'Remove'] = {
                u'action': functools.partial(ImageCache.instance().remove, self.index),
                u'icon': remove_thumbnail_pixmap
            }
        return menu_set

    @contextmenu
    def add_add_bookmark_menu(self, menu_set):
        pixmap = ImageCache.get_rsc_pixmap(
            'todo_add', common.FAVOURITE, common.INLINE_ICON_SIZE)
        menu_set[u'Add bookmark'] = {
            u'text': 'Add bookmark',
            u'icon': pixmap,
            u'action': self.parent().show_add_bookmark_widget
        }
        return menu_set

    @contextmenu
    def add_collapse_sequence_menu(self, menu_set):
        """Adds the menu needed to change context"""
        expand_pixmap = ImageCache.get_rsc_pixmap(
            u'expand', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        collapse_pixmap = ImageCache.get_rsc_pixmap(
            u'collapse', common.FAVOURITE, common.INLINE_ICON_SIZE)
        collapsed = self.parent().model().sourceModel().data_type() == common.SequenceItem

        menu_set[u'collapse'] = {
            u'text': 'Show individual files' if collapsed else 'Group sequences together',
            u'icon': expand_pixmap if collapsed else collapse_pixmap,
            u'checkable': True,
            u'checked': collapsed,
            u'action': functools.partial(
                self.parent().model().sourceModel().dataTypeChanged.emit, not collapsed)
        }
        return menu_set

    @contextmenu
    def add_location_toggles_menu(self, menu_set):
        """Adds the menu needed to change context"""
        locations_icon_pixmap = ImageCache.get_rsc_pixmap(
            u'location', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        item_on_pixmap = ImageCache.get_rsc_pixmap(
            u'check', common.TEXT_SELECTED, common.INLINE_ICON_SIZE)
        item_off_pixmap = QtGui.QPixmap()

        key = u'Change file folder'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = locations_icon_pixmap

        parent_item = self.parent().model().sourceModel()._parent_item
        if not parent_item:
            return menu_set
        if not all(parent_item):
            return menu_set


        dir_ = QtCore.QDir(u'/'.join(parent_item))
        dir_.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        for entry in sorted(dir_.entryList()):
            checked = self.parent().model().sourceModel().data_key() == entry
            menu_set[key][entry] = {
                u'text': entry.title(),
                u'checkable': True,
                u'checked': checked,
                u'icon': item_on_pixmap if checked else item_off_pixmap,
                u'action': functools.partial(self.parent().model().sourceModel().dataKeyChanged.emit, entry)
            }
        return menu_set
