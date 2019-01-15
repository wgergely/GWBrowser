# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the projects and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

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
        if index.isValid():
            self.add_reveal_folder_menu()

    def add_sort_menu(self):
        """Creates the menu needed to set the sort-order of the list."""
        sort_menu_icon = common.get_rsc_pixmap('sort', common.FAVOURITE, 18.0)
        arrow_up_icon = common.get_rsc_pixmap('arrow_up', common.FAVOURITE, 18.0)
        arrow_down_icon = common.get_rsc_pixmap('arrow_down', common.FAVOURITE, 18.0)
        item_off_icon = common.get_rsc_pixmap('item_off', common.TEXT, 18.0)
        item_on_icon = common.get_rsc_pixmap('item_on', common.TEXT_SELECTED, 18.0)

        sort_by_name = self.parent().sort_order() == common.SortByName
        sort_modified = self.parent().sort_order() == common.SortByLastModified
        sort_created = self.parent().sort_order() == common.SortByLastCreated
        sort_size = self.parent().sort_order() == common.SortBySize

        menu_set = collections.OrderedDict()
        menu_set['Sort'] = collections.OrderedDict()
        menu_set['Sort:icon'] = sort_menu_icon
        menu_set['Sort']['Order'] = {
            'text': 'Ascending' if self.parent().is_reversed() else 'Descending',
            'ckeckable': True,
            'checked': True if self.parent().is_reversed() else False,
            'icon': arrow_down_icon if self.parent().is_reversed() else arrow_up_icon,
            'action': (
                functools.partial(self.parent().set_reversed, not self.parent().is_reversed()),
                self.parent().refresh
            )
        }

        menu_set['Sort']['separator'] = {}

        menu_set['Sort']['Name'] = {
            'icon': item_on_icon if sort_by_name else item_off_icon,
            'ckeckable': True,
            'checked': True if sort_by_name else False,
            'action': (
                functools.partial(self.parent().set_sort_order, common.SortByName),
                self.parent().refresh
            )
        }
        menu_set['Sort']['Date modified'] = {
            'icon': item_on_icon if sort_modified else item_off_icon,
            'ckeckable': True,
            'checked': True if sort_modified else False,
            'action': (
                functools.partial(self.parent().set_sort_order, common.SortByLastModified),
                self.parent().refresh
            )
        }
        menu_set['Sort']['Date created'] = {
            'icon': item_on_icon if sort_created else item_off_icon,
            'ckeckable': True,
            'checked': True if sort_created else False,
            'action': (
                functools.partial(self.parent().set_sort_order, common.SortByLastCreated),
                self.parent().refresh
            )
        }
        menu_set['Sort']['Size'] = {
            'icon': item_on_icon if sort_size else item_off_icon,
            'ckeckable': True,
            'checked': True if sort_size else False,
            'action': (
                functools.partial(self.parent().set_sort_order, common.SortBySize),
                self.parent().refresh
            )
        }
        menu_set['separator'] = {}
        self.create_menu(menu_set)

    def add_reveal_folder_menu(self):
        """Menu containing the subfolders of the selected item."""
        if not self.index.data(common.DescriptionRole):
            return

        folder_icon = common.get_rsc_pixmap('folder', common.SECONDARY_TEXT, 18.0)
        folder_icon2 = common.get_rsc_pixmap('folder', common.FAVOURITE, 18.0)
        menu_set = collections.OrderedDict()
        menu_set['separator>'] = {}
        menu_set['Show in File Manager'] = collections.OrderedDict()
        menu_set['Show in File Manager:icon'] = folder_icon

        server, job, root, _ = self.index.data(common.DescriptionRole).split(',')
        menu_set['Show in File Manager']['root'] = {
            'text': 'Show bookmark',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo('{}/{}/{}'.format(server, job, root)).filePath())
        }
        menu_set['Show in File Manager']['separator.'] = {}
        menu_set['Show in File Manager']['server'] = {
            'text': 'Show server',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo(server).filePath())
        }
        menu_set['Show in File Manager']['job'] = {
            'text': 'Show job folder',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo('{}/{}'.format(server, job)).filePath())
        }
        menu_set['Show in File Manager']['separator'] = {}

        it = QtCore.QDirIterator(
            self.index.data(common.PathRole).filePath(),
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

        if not self.parent().is_reversed():
            items = sorted(items, key=common.sort_keys[self.parent().sort_order()])
        else:
            items = list(reversed(sorted(items, key=common.sort_keys[self.parent().sort_order()])))

        for file_info in items:
            if file_info.fileName() == '.' or file_info.fileName() == '..':
                continue
            if not file_info.isDir():
                continue

            menu_set['Show in File Manager'][file_info.baseName()] = {
                'text': file_info.baseName().upper(),
                'icon': folder_icon,
                'action': functools.partial(
                    common.reveal,
                    file_info.filePath())
            }
        self.create_menu(menu_set)

    def add_file_folder_menu(self):
        """Menu containing the subfolders of the selected item."""
        if not self.index.data(common.DescriptionRole):
            return

        folder_icon = common.get_rsc_pixmap('folder', common.SECONDARY_TEXT, 18.0)
        folder_icon2 = common.get_rsc_pixmap('folder', common.FAVOURITE, 18.0)
        menu_set = collections.OrderedDict()
        menu_set['separator>'] = {}
        menu_set['Show in File Manager'] = collections.OrderedDict()
        menu_set['Show in File Manager:icon'] = folder_icon

        server, job, root, _ = self.index.data(common.DescriptionRole).split(',')
        menu_set['Show in File Manager']['root'] = {
            'text': 'Show bookmark...',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo('{}/{}/{}'.format(server, job, root)).filePath())
        }
        menu_set['Show in File Manager']['separator.'] = {}
        menu_set['Show in File Manager']['server'] = {
            'text': 'Show server...',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo(server).filePath())
        }
        menu_set['Show in File Manager']['job'] = {
            'text': 'Show job folder...',
            'icon': folder_icon2,
            'action': functools.partial(
                common.reveal,
                QtCore.QFileInfo('{}/{}'.format(server, job)).filePath())
        }
        menu_set['Show in File Manager']['separator'] = {}

        it = QtCore.QDirIterator(
            self.index.data(common.PathRole).filePath(),
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

        if not self.parent().is_reversed():
            items = sorted(items, key=common.sort_keys[self.parent().sort_order()])
        else:
            items = list(reversed(sorted(items, key=common.sort_keys[self.parent().sort_order()])))

        for file_info in items:
            if file_info.fileName() == '.' or file_info.fileName() == '..':
                continue
            if not file_info.isDir():
                continue

            menu_set['Show in File Manager'][file_info.baseName()] = {
                'text': file_info.baseName().upper(),
                'icon': folder_icon,
                'action': functools.partial(
                    common.reveal,
                    file_info.filePath())
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
            if ':' in k: # Skipping `speudo` keys
                continue

            if isinstance(menu_set[k], collections.OrderedDict): # Recursive menu creation
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
                action.shortcutVisibleInContextMenu(True)
                action.setShortCut(menu_set[k]['shortcut'])
            if 'visible' in menu_set[k]:
                action.setVisible(menu_set[k]['visible'])
            else:
                action.setVisible(True)


    # def favourite(self):
    #     """Toggles the favourite state of the item."""
    #     self.parent().toggle_favourite()
    #
    # def archived(self):
    #     """Marks the curent item as 'archived'."""
    #     self.parent().toggle_archived()
    #
    # def isolate_favourites(self):
    #     """Hides all items except the items marked as favouire."""
    #     self.parent().show_favourites()
    #
    # def show_archived(self):
    #     self.parent().show_archived()


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
    """Defines the base of the ``asset``, ``bookmark`` and ``file`` list widgets.

    Signals:
        activeBookmarkChanged (tuple): Emited when the active bookmark changes.
        activeAssetChanged (str): Emited when the active asset changes.
        activeFileChanged (str): Emited when the active file changes.

    """

    # Signals
    activeBookmarkChanged = QtCore.Signal(tuple)
    activeAssetChanged = QtCore.Signal(str)
    activeFileChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(BaseListWidget, self).__init__(parent=parent)
        self._path = None
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

        self.multi_toggle_pos = None
        self.multi_toggle_state = None
        self.multi_toggle_idx = None
        self.multi_toggle_item = None
        self.multi_toggle_items = {}

        self.add_items()
        self.set_row_visibility()
        self._connectSignals()

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    @property
    def path(self):
        """The path of the assets folder as a (server, job, root) string tuple."""
        return self._path

    @path.setter
    def path(self, *args):
        self._path = args

    def filter(self):
        """The current filter."""
        val = local_settings.value(
            'widget/{}/filter'.format(self.__class__.__name__))
        return val if val else '/'

    def set_filter(self, val):
        local_settings.setValue(
            'widget/{}/filter'.format(self.__class__.__name__), val)

    @property
    def show_favourites_mode(self):
        """The current show favourites state as saved in the local configuration file."""
        val = local_settings.value(
            'widget/{}/show_favourites'.format(self.__class__.__name__))
        return val if val else False

    @show_favourites_mode.setter
    def show_favourites_mode(self, val):
        local_settings.setValue(
            'widget/{}/show_favourites'.format(self.__class__.__name__), val)

    @property
    def show_archived_mode(self):
        """The current Show archived state as saved in the local configuration file."""
        val = local_settings.value(
            'widget/{}/show_archived'.format(self.__class__.__name__))
        return val if val else False

    @show_archived_mode.setter
    def show_archived_mode(self, val):
        local_settings.setValue(
            'widget/{}/show_archived'.format(self.__class__.__name__), val)

    def sort_order(self):
        """Returns the currently saved sort order for this widget."""
        val = local_settings.value(
            'widget/{}/sort_order'.format(self.__class__.__name__))
        return int(val) if val else common.SortByName

    def set_sort_order(self, val):
        local_settings.setValue(
            'widget/{}/sort_order'.format(self.__class__.__name__), val)

    def is_reversed(self):
        """Returns the order of the list."""
        val = local_settings.value(
            'widget/{}/is_reversed'.format(self.__class__.__name__))
        return int(val) if val else False

    def set_reversed(self, val):
        local_settings.setValue(
            'widget/{}/is_reversed'.format(self.__class__.__name__), val)

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

        file_info = item.data(common.PathRole)

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
            Archived items are automatically removed from the favourites.

        Args:
            item (QListWidgetItem): The item to change.
            state (None or bool): The state to set.

        """
        if not item:
            item = self.currentItem()

        archived = item.flags() & configparser.MarkedAsArchived
        settings = AssetSettings(item.data(common.PathRole).filePath())
        favourites = local_settings.value('favourites')
        favourites = favourites if favourites else []
        file_info = item.data(common.PathRole)

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

        settings = AssetSettings(item.data(common.PathRole).filePath())

        # Saving the image
        common.delete_image(settings.thumbnail_path())
        ScreenGrabber.screen_capture_file(
            output_path=settings.thumbnail_path())
        common.delete_image(settings.thumbnail_path(), delete_file=False)
        self.repaint()

    def remove_thumbnail(self):
        """Deletes the given thumbnail."""
        item = self.currentItem()
        settings = AssetSettings(item.data(common.PathRole).filePath())
        common.delete_image(settings.thumbnail_path())
        self.repaint()

    def _paint_widget_background(self):
        """Our list widgets are see-through, because of their drop-shadow.
        Hence, we manually have to paint a solid background to them.

        """
        rect = QtCore.QRect(self.viewport().rect())
        rect.moveLeft(rect.left())

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50)))
        painter.drawRect(rect)
        painter.end()

    def refresh(self, *args):
        """Re-populates the list-widget with the collected items."""
        index = self.currentItem()
        data = index.data(QtCore.Qt.DisplayRole)

        self.add_items()
        self.set_row_visibility()

        item = self.findItems(data, QtCore.Qt.MatchExactly)
        item = next((f for f in item), None)
        if item:
            self.setCurrentItem(item)

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
            self.action_on_custom_keys(event)
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

    def mouseDoubleClickEvent(self, event):
        """Custom double-click event.

        A double click can `activate` an item, or it can trigger an edit event.
        As each item is associated with multiple editors we have to inspect
        the double-click location before calling deciding what action to take.

        Make sure to overwrite this in the subclass.
        """
        raise NotImplementedError('mouseDoubleClickEvent is abstract.')

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

    def _connectSignals(self):
        self.fileSystemWatcher.directoryChanged.connect(self.refresh)
        # self.fileSystemWatcher.fileChanged.connect(self.refresh)

    def set_current_item_as_active(self):
        """Sets the current item item as ``active``."""
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

    def select_active_item(self):
        """Selects the active item."""
        self.setCurrentItem(self.active_item())

    def set_row_visibility(self):
        """Sets the visibility of the list-items based on modes and options."""
        for n in xrange(self.count()):
            item = self.item(n)

            markedAsArchived = item.flags() & configparser.MarkedAsArchived
            markedAsFavourite = item.flags() & configparser.MarkedAsFavourite

            if self.show_archived_mode and self.show_favourites_mode:
                if markedAsFavourite:
                    item.setHidden(False)
                    continue
                item.setHidden(True)
                continue
            elif not self.show_archived_mode and self.show_favourites_mode:
                if markedAsFavourite:
                    item.setHidden(False)
                    continue
                item.setHidden(True)
                continue
            elif self.show_archived_mode and not self.show_favourites_mode:
                item.setHidden(False)
                continue
            elif not self.show_archived_mode and not self.show_favourites_mode:
                item.setHidden(markedAsArchived)

    def show_archived(self):
        self.show_archived_mode = not self.show_archived_mode
        self.set_row_visibility()

    def show_favourites(self):
        self.show_favourites_mode = not self.show_favourites_mode
        self.set_row_visibility()

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
