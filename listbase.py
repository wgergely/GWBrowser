# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Module defines the QListWidget items used to browse the projects and the files
found by the collector classes.

"""

import re
import functools
import collections
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.configparsers import AssetSettings
from mayabrowser.capture import ScreenGrabber


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
        self._index = index
        self.setToolTipsVisible(True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Adding persistent actions
        self.add_sort_menu()
        self.add_display_toggles_menu()
        if index.isValid():
            self.add_reveal_folder_menu()
            self.add_copy_menu()
            self.add_mode_toggles_menu()


    def add_sort_menu(self):
        """Creates the menu needed to set the sort-order of the list."""
        sort_menu_icon = common.get_rsc_pixmap('sort', common.FAVOURITE, 18.0)
        arrow_up_icon = common.get_rsc_pixmap(
            'arrow_up', common.FAVOURITE, 18.0)
        arrow_down_icon = common.get_rsc_pixmap(
            'arrow_down', common.FAVOURITE, 18.0)
        item_off_icon = common.get_rsc_pixmap('item_off', common.TEXT, 18.0)
        item_on_icon = common.get_rsc_pixmap(
            'item_on', common.TEXT_SELECTED, 18.0)

        sort_by_name = self.parent().get_item_sort_order() == common.SortByName
        sort_modified = self.parent().get_item_sort_order() == common.SortByLastModified
        sort_created = self.parent().get_item_sort_order() == common.SortByLastCreated
        sort_size = self.parent().get_item_sort_order() == common.SortBySize

        menu_set = collections.OrderedDict()
        menu_set['Sort'] = collections.OrderedDict()
        menu_set['Sort:icon'] = sort_menu_icon
        menu_set['Sort']['Order'] = {
            'text': 'Ascending' if self.parent().is_item_sort_reversed() else 'Descending',
            'ckeckable': True,
            'checked': True if self.parent().is_item_sort_reversed() else False,
            'icon': arrow_down_icon if self.parent().is_item_sort_reversed() else arrow_up_icon,
            'action': (
                functools.partial(self.parent().set_item_sort_reversed,
                                  not self.parent().is_item_sort_reversed()),
                self.parent().refresh
            )
        }

        menu_set['Sort']['separator'] = {}

        menu_set['Sort']['Name'] = {
            'icon': item_on_icon if sort_by_name else item_off_icon,
            'ckeckable': True,
            'checked': True if sort_by_name else False,
            'action': (
                functools.partial(
                    self.parent().set_item_sort_order, common.SortByName),
                self.parent().refresh
            )
        }
        menu_set['Sort']['Date modified'] = {
            'icon': item_on_icon if sort_modified else item_off_icon,
            'ckeckable': True,
            'checked': True if sort_modified else False,
            'action': (
                functools.partial(self.parent().set_item_sort_order,
                                  common.SortByLastModified),
                self.parent().refresh
            )
        }
        menu_set['Sort']['Date created'] = {
            'icon': item_on_icon if sort_created else item_off_icon,
            'ckeckable': True,
            'checked': True if sort_created else False,
            'action': (
                functools.partial(self.parent().set_item_sort_order,
                                  common.SortByLastCreated),
                self.parent().refresh
            )
        }
        menu_set['Sort']['Size'] = {
            'icon': item_on_icon if sort_size else item_off_icon,
            'ckeckable': True,
            'checked': True if sort_size else False,
            'action': (
                functools.partial(
                    self.parent().set_item_sort_order, common.SortBySize),
                self.parent().refresh
            )
        }
        menu_set['separator'] = {}
        self.create_menu(menu_set)

    def add_reveal_folder_menu(self):
        """Creates a menu containing"""
        folder_icon = common.get_rsc_pixmap(
            'folder', common.SECONDARY_TEXT, 18.0)
        folder_icon2 = common.get_rsc_pixmap('folder', common.FAVOURITE, 18.0)

        menu_set = collections.OrderedDict()

        key = 'Show in File Manager'
        menu_set['separator>'] = {}
        menu_set[key] = collections.OrderedDict()
        menu_set['{}:icon'.format(key)] = folder_icon

        server, job, root, asset, file_ = self.index.data(common.ParentRole)
        if file_:
            menu_set[key]['asset'] = {
                'text': 'Show bookmark',
                'icon': folder_icon2,
                'action': functools.partial(
                    common.reveal,
                    QtCore.QFileInfo('{}/{}/{}/{}/{}'.format(server, job, root, asset, file)).filePath()),
            }
        if asset:
            menu_set[key]['asset'] = {
                'text': 'Show bookmark',
                'icon': folder_icon2,
                'action': functools.partial(
                    common.reveal,
                    QtCore.QFileInfo('{}/{}/{}/{}'.format(server, job, root, asset)).filePath()),
            }
        menu_set[key]['root'] = {
            'text': 'Show bookmark',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo('{}/{}/{}'.format(server, job, root)).filePath()),
        }
        menu_set[key]['separator.'] = {}
        menu_set[key]['server'] = {
            'text': 'Show server',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo(server).filePath())
        }
        menu_set[key]['job'] = {
            'text': 'Show job folder',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo('{}/{}'.format(server, job)).filePath())
        }

        menu_set[key]['separator'] = {}

        it = QtCore.QDirIterator(
            self.index.data(common.PathRole),
            flags=QtCore.QDirIterator.NoIteratorFlags,
            filters=QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs |
            QtCore.QDir.NoSymLinks |
            QtCore.QDir.Readable
        )
        items = []
        while it.hasNext():
            path = it.next()
            file_info = QtCore.QFileInfo(path)
            items.append(file_info)

        if not self.parent().is_item_sort_reversed():
            items = sorted(
                items, key=common.sort_keys[self.parent().get_item_sort_order()])
        else:
            items = list(
                reversed(sorted(items, key=common.sort_keys[self.parent().get_item_sort_order()])))

        for file_info in items:
            if file_info.fileName()[0] == '.':
                continue
            if not file_info.isDir():
                continue

            menu_set[key][file_info.baseName()] = {
                'text': file_info.baseName().upper(),
                'icon': folder_icon,
                'action': functools.partial(
                    common.reveal,
                    file_info.filePath())
            }
        self.create_menu(menu_set)

    def add_copy_menu(self):
        """Menu containing the subfolders of the selected item."""
        if not self.index.data(common.DescriptionRole):
            return

        copy_icon = common.get_rsc_pixmap('copy', common.SECONDARY_TEXT, 18.0)
        copy_icon2 = common.get_rsc_pixmap('copy', common.FAVOURITE, 18.0)

        menu_set = collections.OrderedDict()
        menu_set['Copy'] = collections.OrderedDict()
        menu_set['Copy:icon'] = copy_icon

        path = self.index.data(common.PathRole)
        url = QtCore.QUrl().fromLocalFile(path).toString()

        key = 'Copy'

        menu_set[key]['windows1'] = {
            'text': 'Windows  -  \\\\back\\slashes',
            'icon': copy_icon2,
            'action': functools.partial(
                QtGui.QClipboard().setText,
                QtCore.QDir.toNativeSeparators(path))
        }
        menu_set[key]['windows2'] = {
            'text': 'Windows  -  //forward/slashes',
            'icon': copy_icon2,
            'action': functools.partial(QtGui.QClipboard().setText, path)
        }
        menu_set[key]['slack'] = {
            'text': 'URL  -  file://Slack/friendly',
            'icon': copy_icon2,
            'action': functools.partial(QtGui.QClipboard().setText, url)
        }
        menu_set[key]['macos'] = {
            'text': 'SMB  -  smb://MacOS/path',
            'icon': copy_icon2,
            'action': functools.partial(
                QtGui.QClipboard().setText,
                url.replace('file://', 'smb://'))
        }
        self.create_menu(menu_set)

    def add_mode_toggles_menu(self):
        """Ads the menu-items needed to add set favourite or archived status."""
        favourite_on_icon = common.get_rsc_pixmap(
            'favourite', common.FAVOURITE, 18.0)
        favourite_off_icon = common.get_rsc_pixmap(
            'favourite', common.SECONDARY_TEXT, 18.0)
        archived_on_icon = common.get_rsc_pixmap(
            'archived', common.FAVOURITE, 18.0)
        archived_off_icon = common.get_rsc_pixmap(
            'archived', common.TEXT, 18.0)

        favourite = self.index.flags() & configparser.MarkedAsFavourite
        archived = self.index.flags() & configparser.MarkedAsArchived

        menu_set = collections.OrderedDict()
        menu_set['separator'] = {}
        if self.__class__.__name__ == 'BookmarksWidgetContextMenu':
            text = 'Remove bookmark'
        else:
            text = 'Disable'
        menu_set['archived'] = {
            'text': 'Enable' if archived else text,
            'icon': archived_off_icon if archived else archived_on_icon,
            'checkable': True,
            'checked': archived,
            'action':   self.parent().toggle_archived
        }
        menu_set['favourite'] = {
            'text': 'Remove from favourites' if favourite else 'Mark as favourite',
            'icon': favourite_off_icon if archived else favourite_on_icon,
            'checkable': True,
            'checked': favourite,
            'action': self.parent().toggle_favourite
        }

        self.create_menu(menu_set)

    def add_display_toggles_menu(self):
        """Ads the menu-items needed to add set favourite or archived status."""
        item_on = common.get_rsc_pixmap(
            'item_on', common.TEXT_SELECTED, 18.0)
        item_off = common.get_rsc_pixmap(
            'item_off', common.SECONDARY_TEXT, 18.0)

        favourite = self.parent().get_display_mode('favourite')
        archived = self.parent().get_display_mode('archived')

        menu_set = collections.OrderedDict()
        menu_set['separator'] = {}
        menu_set['toggle_favoruites'] = {
            'text': 'Show favourites only',
            'icon': item_on if favourite else item_off,
            'checkable': True,
            'checked': favourite,
            'action': (
                functools.partial(
                    self.parent().set_display_mode,
                    'favourite',
                    not favourite
                ),
                self.parent().refresh)
        }
        menu_set['toggle_archived'] = {
            'text': 'Show archived items',
            'icon': item_on if archived else item_off,
            'checkable': True,
            'checked': archived,
            'action': (
                functools.partial(
                    self.parent().set_display_mode,
                    'archived',
                    not archived
                ),
                self.parent().refresh)
        }

        self.create_menu(menu_set)

    def add_refresh_menu(self):
        menu_set = collections.OrderedDict()
        menu_set['separator'] = {}
        menu_set['Refresh'] = {
            'action': self.parent().refresh
        }
        if self.index.isValid():
            menu_set['Activate'] = {
                'action': self.parent().set_current_item_as_active
            }

        self.create_menu(menu_set)

    @property
    def index(self):
        """The QModelIndex the context menu is associated with."""
        return self._index

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
            action_set[k]['tool_tip'] (str):The description of the action.
            action_set[k]['status_tip'] (str): The description of the action.
            action_set[k]['icon'] (QPixmap): The action's icon.
            action_set[k]['shortcut'] (QKeySequence): The action's icon.
            action_set[k]['checkable'] (bool): Sets wheter the item is checkable.
            action_set[k]['checked'] (bool): The state of the checkbox.
            action_set[k]['visible'] (bool): The visibility of the action.

        """
        if not parent:
            parent = self

        for k in menu_set:
            if ':' in k:  # Skipping `speudo` keys
                continue

            # Recursive menu creation
            if isinstance(menu_set[k], collections.OrderedDict):
                parent = QtWidgets.QMenu(k, parent=self)

                # width = self.parent().viewport().geometry().width()
                # width = (width * 0.5) if width > 400 else width
                # parent.setFixedWidth(width)

                if '{}:icon'.format(k) in menu_set:
                    icon = QtGui.QIcon(menu_set['{}:icon'.format(k)])
                    parent.setIcon(icon)
                self.addMenu(parent)
                self.create_menu(menu_set[k], parent=parent)
                continue

            if 'separator' in k:
                parent.addSeparator()
                continue

            action = parent.addAction(k)

            if 'data' in menu_set[k]:  # Skipping disabled items
                action.setData(menu_set[k]['data'])
            if 'disabled' in menu_set[k]:  # Skipping disabled items
                action.setDisabled(menu_set[k]['disabled'])
            if 'action' in menu_set[k]:
                if isinstance(menu_set[k]['action'], collections.Iterable):
                    for func in menu_set[k]['action']:
                        action.triggered.connect(func)
                else:
                    action.triggered.connect(menu_set[k]['action'])
            if 'text' in menu_set[k]:
                action.setText(menu_set[k]['text'])
            else:
                action.setText(k)
            if 'status_tip' in menu_set[k]:
                action.setStatusTip(menu_set[k]['status_tip'])
            if 'tool_tip' in menu_set[k]:
                action.setToolTip(menu_set[k]['tool_tip'])
            if 'checkable' in menu_set[k]:
                action.setCheckable(menu_set[k]['checkable'])
            if 'checked' in menu_set[k]:
                action.setChecked(menu_set[k]['checked'])
            if 'icon' in menu_set[k]:
                action.setIconVisibleInMenu(True)
                action.setIcon(menu_set[k]['icon'])
            if 'shortcut' in menu_set[k]:
                action.setShortcut(menu_set[k]['shortcut'])
            if 'visible' in menu_set[k]:
                action.setVisible(menu_set[k]['visible'])
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


class BaseListWidget(QtWidgets.QListWidget):
    """Defines the base of the ``Asset``, ``Bookmark`` and ``File`` list widgets.

    Args:
        path (str): The path used to initialize

    Signals:
        sizeChanged (QSize): Emitted when the size of the widget changes.
        activeBookmarkChanged (tuple): Emited when the active bookmark changes.
        activeAssetChanged (str): Emited when the active asset changes.
        activeFileChanged (str): Emited when the active file changes.

    """
    sizeChanged = QtCore.Signal(QtCore.QSize)
    activeBookmarkChanged = QtCore.Signal(tuple)
    activeAssetChanged = QtCore.Signal(str)
    activeFileChanged = QtCore.Signal(str)

    def __init__(self, path, parent=None):
        super(BaseListWidget, self).__init__(parent=parent)
        # The timer used to check for changes in the active path
        self._path = path
        self._context_menu_cls = BaseContextMenu
        self.fileSystemWatcher = QtCore.QFileSystemWatcher(parent=self)

        self.setSortingEnabled(False)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformItemSizes(True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        # Scrollbar visibility
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # Style
        common.set_custom_stylesheet(self)

        # Keyboard search timer and placeholder string.
        self.timer = QtCore.QTimer(parent=self)
        app = QtCore.QCoreApplication.instance()
        self.timer.setInterval(app.keyboardInputInterval())
        self.timer.setSingleShot(True)
        self.timed_search_string = ''

        # Properties needed to toggle multiple item's state while dragging
        # the mouse
        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

        # Populating the
        self.add_items()
        self.set_row_visibility()

    def get_item_filter(self):
        """A path segment used to filter the collected items."""
        val = local_settings.value(
            'widget/{}/filter'.format(self.__class__.__name__))
        return val if val else '/'

    def set_item_filter(self, val):
        """Sets the ``item_filter``."""
        local_settings.setValue(
            'widget/{}/filter'.format(self.__class__.__name__), val)

    def get_display_mode(self, mode):
        """Querries this widget's display mode."""
        setting = local_settings.value(
            'widget/{widget}/mode:{mode}'.format(
                widget=self.__class__.__name__,
                mode=mode
            ))
        return setting if setting else False

    def set_display_mode(self, mode, val):
        """Sets this widget's display mode."""
        local_settings.setValue(
            'widget/{widget}/mode:{mode}'.format(
                widget=self.__class__.__name__,
                mode=mode
            ), val)

    def get_item_sort_order(self):
        """Returns the saved sort order for this widget."""
        val = local_settings.value(
            'widget/{}/sort_order'.format(self.__class__.__name__))
        return int(val) if val else common.SortByName

    def set_item_sort_order(self, val):
        local_settings.setValue(
            'widget/{}/sort_order'.format(self.__class__.__name__), val)

    def is_item_sort_reversed(self):
        """Returns the order of the list."""
        val = local_settings.value(
            'widget/{}/sort_reversed'.format(self.__class__.__name__))
        return int(val) if val else False

    def set_item_sort_reversed(self, val):
        local_settings.setValue(
            'widget/{}/sort_reversed'.format(self.__class__.__name__), val)

    def toggle_favourite(self, item=None, state=None):
        """Toggles the ``favourite`` state of the current item.
        If `item` and/or `state` are set explicity, those values will be used
        instead of the currentItem.

        Args:
            item (QListWidgetItem): The item to change.
            state (None or bool): The state to set.

        """
        if not item:
            item = self.currentItem()

        file_info = QtCore.QFileInfo(item.data(common.PathRole))

        # Favouriting archived items are not allowed
        archived = item.flags() & configparser.MarkedAsArchived
        if archived:
            return

        favourites = local_settings.value('favourites')
        favourites = favourites if favourites else []

        if file_info.filePath() in favourites:
            if state is None or state is False:  # clears flag
                item.setFlags(item.flags() & ~configparser.MarkedAsFavourite)
                favourites.remove(file_info.filePath())
        else:
            if state is None or state is True:  # adds flag
                favourites.append(file_info.filePath())
                item.setFlags(item.flags() | configparser.MarkedAsFavourite)

        local_settings.setValue('favourites', favourites)
        self.set_row_visibility()

    def toggle_archived(self, item=None, state=None):
        """Toggles the ``archived`` state of the current item.
        If `item` and/or `state` are set explicity, those values will be used
        instead of the currentItem.

        Note:
            Archived items are automatically removed from ``favourites``.

        Args:
            item (QListWidgetItem): The explicit item to change.
            state (None or bool): The explicit state to set.

        """
        if not item:
            item = self.currentItem()

        archived = item.flags() & configparser.MarkedAsArchived
        settings = AssetSettings(item.data(common.PathRole))

        favourites = local_settings.value('favourites')
        favourites = favourites if favourites else []
        file_info = QtCore.QFileInfo(item.data(common.PathRole))

        if archived:
            if state is None or state is False:  # clears flag
                item.setFlags(item.flags() & ~configparser.MarkedAsArchived)
                settings.setValue('config/archived', False)
        else:
            if state is None or state is True:  # adds flag
                settings.setValue('config/archived', True)
                item.setFlags(item.flags() | configparser.MarkedAsArchived)
                item.setFlags(item.flags() & ~configparser.MarkedAsFavourite)
                if file_info.filePath() in favourites:
                    favourites.remove(file_info.filePath())
                    local_settings.setValue('favourites', favourites)

        self.set_row_visibility()

    def capture_thumbnail(self):
        """Captures a thumbnail for the current item using ScreenGrabber."""
        item = self.currentItem()

        if not item:
            return

        settings = AssetSettings(item.data(common.PathRole))

        # Saving the image
        common.delete_image(settings.thumbnail_path())
        ScreenGrabber.screen_capture_file(
            output_path=settings.thumbnail_path())
        common.delete_image(settings.thumbnail_path(), delete_file=False)
        self.repaint()

    def remove_thumbnail(self):
        """Deletes the given thumbnail."""
        item = self.currentItem()
        settings = AssetSettings(item.data(common.PathRole))
        common.delete_image(settings.thumbnail_path())
        self.repaint()

    def refresh(self):
        """Re-populates the list-widget with the collected items."""
        item = self.currentItem()

        path = None
        if item:
            if item.data(common.PathRole):
                path = item.data(common.PathRole)

        self.add_items()
        self.set_row_visibility()

        if not path:
            return
        for n in xrange(self.count()):
            if self.item(n).isHidden():
                continue
            if not self.item(n).data(common.PathRole):
                continue
            if self.item(n).data(common.PathRole) == path:
                self.setCurrentItem(self.item(n))
                break

    def action_on_enter_key(self):
        self.set_current_item_as_active()

    def key_down(self):
        """Custom action tpo perform when the `down` arrow is pressed
        on the keyboard.

        """
        visible_items = [self.item(n) for n in xrange(
            self.count()) if not self.item(n).isHidden()]
        if visible_items:  # jumping to the beginning of the list after the last item
            if self.currentItem() is visible_items[-1]:
                self.setCurrentItem(
                    visible_items[0],
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                return
        for n in xrange(self.count()):
            if self.item(n).isHidden():
                continue
            if self.currentRow() >= n:
                continue

            self.setCurrentItem(
                self.item(n),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            break

    def key_up(self):
        """Custom action to perform when the `up` arrow is pressed
        on the keyboard.

        """
        visible_items = [self.item(n) for n in xrange(
            self.count()) if not self.item(n).isHidden()]
        if visible_items:  # jumping to the end of the list after the first item
            if self.currentItem() is visible_items[0]:
                self.setCurrentItem(
                    visible_items[-1],
                    QtCore.QItemSelectionModel.ClearAndSelect
                )
                return
        if self.currentRow() == -1:
            self.setCurrentItem(
                visible_items[0],
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            return
        for n in reversed(xrange(self.count())):
            if self.item(n).isHidden():
                continue
            if self.currentRow() <= n:
                continue

            self.setCurrentItem(
                self.item(n),
                QtCore.QItemSelectionModel.ClearAndSelect
            )
            break

    def key_tab(self):
        self.setUpdatesEnabled(False)

        cursor = QtGui.QCursor()
        opos = cursor.pos()
        rect = self.visualRect(self.currentIndex())
        rect, _, _ = self.itemDelegate().get_description_rect(rect)
        pos = self.mapToGlobal(rect.topLeft())
        cursor.setPos(pos)
        self.editItem(self.currentItem())
        cursor.setPos(opos)

        self.setUpdatesEnabled(True)

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
                    self.timed_search_string = ''
                    self.timer.start()

                self.timed_search_string += event.text()
                self.timer.start()  # restarting timer on input

                visible_items = [self.item(n) for n in xrange(
                    self.count()) if not self.item(n).isHidden()]
                for item in visible_items:
                    # When only one key is pressed we want to cycle through
                    # only items starting with that letter:
                    if len(self.timed_search_string) == 1:
                        if self.row(item) <= self.row(self.currentItem()):
                            continue
                        if item.data(QtCore.Qt.DisplayRole)[0].lower() == self.timed_search_string.lower():
                            self.setCurrentItem(
                                item,
                                QtCore.QItemSelectionModel.ClearAndSelect
                            )
                            break
                    else:
                        match = re.search(
                            '{}'.format(self.timed_search_string),
                            item.data(QtCore.Qt.DisplayRole),
                            flags=re.IGNORECASE
                        )
                        if match:
                            self.setCurrentItem(
                                item,
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

    def count_visible(self):
        """Counts the visible list-items.

        Returns:
            int: The number of visible of items.

        """
        c = 0
        for n in xrange(self.count()):
            if not self.item(n).isHidden():
                c += 1
        return c

    def contextMenuEvent(self, event):
        """Custom context menu event."""
        index = self.indexAt(event.pos())
        widget = self._context_menu_cls(index, parent=self)

        width = self.viewport().geometry().width()
        width = (width * 0.5) if width > 400 else width
        width = width - common.INDICATOR_WIDTH

        if index.isValid():
            rect = self.visualRect(index)
            widget.move(
                self.viewport().mapToGlobal(rect.bottomLeft()).x(),
                self.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
            )
        else:
            cursor_pos = QtGui.QCursor().pos()
            widget.move(
                self.mapToGlobal(self.viewport().geometry().topLeft()).x(),
                cursor_pos.y() + 1
            )

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH, widget.y())
        common.move_widget_to_available_geo(widget)
        widget.show()

    def active_item(self):
        """Return the ``active`` item.

        The active item is indicated by the ``configparser.MarkedAsActive`` flag.
        If no item has been flagged as `active`, returns ``None``.

        """
        for n in xrange(self.count()):
            item = self.item(n)
            if item.flags() & configparser.MarkedAsActive:
                return item
        return None

    def set_current_item_as_active(self):
        """Sets the current item item as ``active``.

        Note:
            This doesn't alter the local config file only sets, the flags.
            Make sure to implement that in the subclass.

        """
        item = self.currentItem()
        if not item:
            return

        archived = item.flags() & configparser.MarkedAsArchived
        if archived:
            return

        # Set flags
        if self.active_item():
            self.active_item().setFlags(item.flags() & ~
                                        configparser.MarkedAsActive)
        item.setFlags(item.flags() | configparser.MarkedAsActive)

    def select_active_item(self):
        """Selects the active item."""
        self.setCurrentItem(self.active_item())

    def set_row_visibility(self):
        """Sets the visibility of the list-items based on their set flags."""
        for n in xrange(self.count()):
            item = self.item(n)

            markedAsArchived = item.flags() & configparser.MarkedAsArchived
            markedAsFavourite = item.flags() & configparser.MarkedAsFavourite

            if self.get_display_mode('archive') and self.get_display_mode('favourite'):
                if markedAsFavourite:
                    item.setHidden(False)
                    continue
                item.setHidden(True)
                continue
            elif not self.get_display_mode('archive') and self.get_display_mode('favourite'):
                if markedAsFavourite:
                    item.setHidden(False)
                    continue
                item.setHidden(True)
                continue
            elif self.get_display_mode('archive') and not self.get_display_mode('favourite'):
                item.setHidden(False)
                continue
            elif not self.get_display_mode('archive') and not self.get_display_mode('favourite'):
                item.setHidden(markedAsArchived)

    def paint_message(self, text):
        """Paints a custom message onto the list widget."""
        painter = QtGui.QPainter()
        painter.begin(self)

        rect = QtCore.QRect(self.viewport().rect())
        rect.setLeft(rect.left() + common.MARGIN)
        rect.setRight(rect.right() - common.MARGIN)
        rect.setBottom(rect.bottom() - common.MARGIN)

        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        painter.setPen(QtGui.QPen(common.SECONDARY_TEXT))
        painter.drawText(
            rect,
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom | QtCore.Qt.TextWordWrap,
            text
        )

        painter.end()

    def showEvent(self, event):
        """Show event will set the size of the widget."""
        self.select_active_item()
        super(BaseListWidget, self).showEvent(event)

    def resizeEvent(self, event):
        """Custom resize event will emit the ``sizeChanged`` signal."""
        self.sizeChanged.emit(event.size())
        super(BaseListWidget, self).resizeEvent(event)
