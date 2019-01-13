# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the projects and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import re
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.configparsers import AssetSettings
from mayabrowser.actions import Actions
from mayabrowser.capture import ScreenGrabber


class BaseContextMenu(Actions):
    """Base class for our custom context menu."""

    def __init__(self, index, parent=None):
        self.index = index
        super(BaseContextMenu, self).__init__(parent=parent)

    def add_actions(self):
        self.add_action_set(self.ActionSet)

    def favourite(self):
        """Toggles the favourite state of the item."""
        self.parent().toggle_favourite()

    def archived(self):
        """Marks the curent item as 'archived'."""
        self.parent().toggle_archived()

    def isolate_favourites(self):
        """Hides all items except the items marked as favouire."""
        self.parent().show_favourites()

    def show_archived(self):
        self.parent().show_archived()


class BaseListWidget(QtWidgets.QListWidget):
    """Base class for the custom list widgets."""

    # Signals
    assetChanged = QtCore.Signal()
    sceneChanged = QtCore.Signal()
    sizeChanged = QtCore.Signal(QtCore.QSize)

    Delegate = NotImplementedError
    ContextMenu = NotImplementedError

    def __init__(self, parent=None):
        super(BaseListWidget, self).__init__(parent=parent)
        self._contextMenu = None

        self.fileSystemWatcher = QtCore.QFileSystemWatcher(parent=self)

        self.setItemDelegate(self.Delegate(parent=self))
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
    def filter(self):
        """The current filter."""
        val = local_settings.value(
            'widget/{}/filter'.format(self.__class__.__name__))
        return val if val else False

    @filter.setter
    def filter(self, val):
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

    @property
    def sort_order(self):
        val = local_settings.value(
            'widget/{}/sort_order'.format(self.__class__.__name__))
        return val if val else False

    @sort_order.setter
    def sort_order(self, val):
        local_settings.setValue(
            'widget/{}/sort_order'.format(self.__class__.__name__), val)

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

        file_info = item.data(QtCore.Qt.PathRole)

        # Favouriting archived items are not allowed
        archived = item.flags() & configparser.MarkedAsArchived
        if archived:
            return

        favourites = local_settings.value('favourites')
        favourites = favourites if favourites else []

        if file_info.filePath() in favourites:
            if state is None or state is False: # clears flag
                item.setFlags(item.flags() & ~configparser.MarkedAsFavourite)
                favourites.remove(file_info.filePath())
        else:
            if state is None or state is True: # adds flag
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
        settings = AssetSettings(item.data(QtCore.Qt.PathRole).filePath())
        favourites = local_settings.value('favourites')
        favourites = favourites if favourites else []
        file_info = item.data(QtCore.Qt.PathRole)

        if archived:
            if state is None or state is False: # clears flag
                item.setFlags(item.flags() & ~configparser.MarkedAsArchived)
                settings.setValue('config/archived', False)
        else:
            if state is None or state is True: # adds flag
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

        settings = AssetSettings(item.data(QtCore.Qt.PathRole).filePath())

        # Saving the image
        common.delete_image(settings.thumbnail_path())
        ScreenGrabber.screen_capture_file(
            output_path=settings.thumbnail_path())
        common.delete_image(settings.thumbnail_path(), delete_file=False)
        self.repaint()

    def remove_thumbnail(self):
        """Deletes the given thumbnail."""
        item = self.currentItem()
        settings = AssetSettings(item.data(QtCore.Qt.PathRole).filePath())
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

    def action_on_enter_key(self):
        raise NotImplementedError('Method is abstract.')

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

    def resizeEvent(self, event):
        """Custom resize event."""
        self.sizeChanged.emit(self.viewport().size())
        super(BaseListWidget, self).resizeEvent(event)

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        widget = self.ContextMenu(index, parent=self)
        if index.isValid():
            rect = self.visualRect(index)
            widget.setFixedWidth(self.viewport().geometry().width())
            widget.move(
                self.viewport().mapToGlobal(rect.bottomLeft()).x(),
                self.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
            )
        else:
            widget.setFixedWidth(self.viewport().geometry().width())
            cursor_pos = QtGui.QCursor().pos()
            widget.move(
                self.viewport().mapToGlobal(self.viewport().geometry().topLeft()).x(),
                cursor_pos.y() + 1
            )
        widget.move(widget.x(), widget.y())
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
        active_item = self.active_item()
        if active_item:
            active_item.setFlags(active_item.flags() & ~
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

        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        painter.setPen(QtGui.QPen(common.FAVOURITE))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap,
            text
        )

        painter.end()
