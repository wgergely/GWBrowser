# -*- coding: utf-8 -*-
"""Module defines the QListWidget items used to browse the projects and the files
found by the collector classes.

"""
# pylint: disable=E1101, C0103, R0913, I1101

import re
from PySide2 import QtWidgets, QtGui, QtCore

from mayabrowser.common import cmds
import mayabrowser.common as common
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_config
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
        """Toggles the state of the item."""
        data = self.index.data(QtCore.Qt.StatusTipRole)
        file_info = QtCore.QFileInfo(data)
        config = self.parent().Config(file_info.filePath())

        flags = configparser.NoFlag
        if config.archived:
            flags = flags | configparser.MarkedAsArchived

        # Saving the config file and flags
        if local_config.is_favourite(file_info.fileName()):
            local_config.remove_favourite(file_info.fileName())
        else:
            flags = flags | configparser.MarkedAsFavourite
            local_config.set_favourite(file_info.fileName())

        item = self.parent().itemFromIndex(self.index)
        item.setData(
            QtCore.Qt.UserRole,
            flags
        )
        self.parent().set_row_visibility()

    def isolate_favourites(self):
        """Hides all items except the items marked as favouire."""
        self.parent().show_favourites()

    def archived(self):
        """Marks the curent item as 'archived'."""
        data = self.index.data(QtCore.Qt.StatusTipRole)
        file_info = QtCore.QFileInfo(data)
        config = self.parent().Config(file_info.filePath())

        # Write the change to the config file.
        config.archived = not config.archived
        config.write_ini()

        # Set the flag
        flags = configparser.NoFlag
        if config.archived:
            flags = flags | configparser.MarkedAsArchived
        elif local_config.is_favourite(file_info.fileName()):
            flags = flags | configparser.MarkedAsFavourite

        # Set the flag as custom user data
        item = self.parent().itemFromIndex(self.index)
        item.setData(
            QtCore.Qt.UserRole,
            flags
        )
        self.parent().set_row_visibility()

    def show_archived(self):
        self.parent().show_archived()



class BaseListWidget(QtWidgets.QListWidget):
    """Base class for the custom list widgets."""

    projectChanged = QtCore.Signal()
    sceneChanged = QtCore.Signal()
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
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformItemSizes(False)

        # Scrollbar visibility
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Keyboard search timer and placeholder string.
        self.timer = QtCore.QTimer(parent=self)
        app = QtCore.QCoreApplication.instance()
        self.timer.setInterval(app.keyboardInputInterval())
        self.timer.setSingleShot(True)
        self.timed_search_string = ''

        self.add_collector_items()
        self.set_row_visibility()
        self._connectSignals()

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # Animate on show
        self.setWindowOpacity(50)
        self.animation = None

        self.setStyleSheet(
            """
            QListWidget {\
                outline: none;\
                border: none;\
                margin: 0px;\
                padding: 0px;\
                background: rgb(50, 50, 50);
                font-family: "Roboto Black";\
                font-size: 8pt;\
            }\
            QScrollBar {\
            	width:6px;\
            	height:6px;\
            }\
            QScrollBar:vertical, QScrollBar:horizontal {\
            	background: rgb(40, 40, 40);\
            	border: none;\
            }\
            QScrollBar::handle:vertical, QScrollBar::handle:vertical, QScrollBar::handle:horizontal, QScrollBar::handle:horizontal {\
            	background: rgb(75, 75, 75);\
            	border: 0px solid;\
            	border-radius: 2px;\
            	max-height: 250px;\
            	min-height: 50px;\
            }\
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical, QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {\
            	background: rgb(40, 40, 40);\
            }\
            """
        )

    def capture_thumbnail(self):
        """Captures a thumbnail for the current item."""
        item = self.currentItem()
        if not item:
            return

        scene_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))
        file_info = QtCore.QFileInfo(item.data(QtCore.Qt.StatusTipRole))

        if scene_info.filePath() != file_info.filePath():
            mbox = QtWidgets.QMessageBox()
            mbox.setText(
                'The selected scene is not the one currently open.'
            )
            mbox.setInformativeText(
                'Are you sure you want to use this scene to make the thumbnail?')
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Save |
                QtWidgets.QMessageBox.Cancel
            )
            mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            result = mbox.exec_()

            if result != QtWidgets.QMessageBox.Save:
                return

        # Hide
        self.hide()

        path = self.Config.getThumbnailPath(file_info.filePath())
        # Deleting the thumbnail from our image cache
        if path in common.IMAGE_CACHE:
            del common.IMAGE_CACHE[path]

        ScreenGrabber.screen_capture_file(output_path=path)
        self.Config.set_hidden(path)

        # Show
        self.parent_.activate_widget(self)

    def _paint_widget_background(self):
        """Our list widgets arer see-through, because of their drop-shadow.
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

    def animate_opacity(self):
        self.animation = QtCore.QPropertyAnimation(
            self, 'windowOpacity', parent=self)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InQuad)
        self.animation.setDuration(150)
        self.animation.setStartValue(0.01)
        self.animation.setEndValue(1)
        self.animation.start(QtCore.QPropertyAnimation.KeepWhenStopped)

    def action_on_enter_key(self):
        raise NotImplementedError('Method is abstract.')

    def key_down(self):
        """Custom action tpo perform when the `down` arrow is pressed
        on the keyboard.

        """
        visible_items = [self.item(n) for n in xrange(self.count()) if not self.item(n).isHidden()]
        if visible_items: # jumping to the beginning of the list after the last item
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
        visible_items = [self.item(n) for n in xrange(self.count()) if not self.item(n).isHidden()]
        if visible_items: # jumping to the end of the list after the first item
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
        rect, _, _ = self.itemDelegate().get_note_rect(rect)
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
                self.hide()
            elif event.key() == QtCore.Qt.Key_Down:
                self.key_down()
            elif event.key() == QtCore.Qt.Key_Up:
                self.key_up()
            elif (event.key() == QtCore.Qt.Key_Return) or (event.key() == QtCore.Qt.Key_Enter):
                self.action_on_enter_key()
                self.hide()
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
                self.timer.start() # restarting timer on input

                visible_items = [self.item(n) for n in xrange(self.count()) if not self.item(n).isHidden()]
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

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        self._contextMenu = self.ContextMenu(index, parent=self)
        if index.isValid():
            rect = self.visualRect(index)
            self._contextMenu.setFixedWidth(200)
            self._contextMenu.show()
            self._contextMenu.move(self.mapToGlobal(rect.bottomLeft()))
        else:
            self._contextMenu.setFixedWidth(self.rect().width())
            self._contextMenu.show()
            self._contextMenu.move(self.mapToGlobal(self.rect().topLeft()))
        self._contextMenu.move(self._contextMenu.x(), self._contextMenu.y())

        self.parent_.move_widget_to_available_geo(self._contextMenu)

    def _connectSignals(self):
        self.fileSystemWatcher.directoryChanged.connect(self.refresh)
        # self.fileSystemWatcher.fileChanged.connect(self.refresh)

    def set_row_visibility(self):
        """Sets the visibility of the list-items based on modes and options."""
        for n in xrange(self.count()):
            item = self.item(n)

            markedAsArchived = bool(item.data(
                QtCore.Qt.UserRole) & configparser.MarkedAsArchived)
            markedAsFavourite = bool(item.data(
                QtCore.Qt.UserRole) & configparser.MarkedAsFavourite)

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
        rect = QtCore.QRect(self.rect())
        rect.moveLeft(rect.left())  # offsetting by the margin
        rect.setWidth(self.rect().width())

        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200)))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignCenter,
            text
        )

        painter.end()
