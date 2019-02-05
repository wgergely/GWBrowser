# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, E0401
"""Small widget to toggle the BrowserWidget's visibility."""

import collections
import functools
from PySide2 import QtWidgets, QtGui, QtCore

from browser.baselistwidget import BaseContextMenu
from browser.editors import ClickableLabel
from browser.settings import Active
import browser.common as common


class ToolbarContextMenuWidget(BaseContextMenu):
    """The context-menu associated with the BaseToolbarWidget."""

    def __init__(self, parent=None):
        super(ToolbarContextMenuWidget, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_show_menu()
        self.add_toolbar_menu()

    def add_show_menu(self):
        widget = self.parent().findChild(ToolbarButton)
        menu_set = collections.OrderedDict()
        menu_set[u'separator'] = {}
        menu_set[u'show'] = {
            u'icon': common.get_rsc_pixmap(u'custom', None, common.INLINE_ICON_SIZE),
            u'text': u'Show browser...',
            u'action': widget.clicked.emit
        }
        self.create_menu(menu_set)

    def add_toolbar_menu(self):
        active_paths = Active.get_active_paths()
        bookmark = (active_paths[u'server'], active_paths[u'job'], active_paths[u'root'])
        asset = bookmark + (active_paths[u'asset'],)
        file_ = asset + (active_paths[u'location'],)
        menu_set = collections.OrderedDict()

        menu_set[u'separator'] = {}
        menu_set[u'bookmark'] = {
            u'icon': common.get_rsc_pixmap('bookmarks', common.TEXT, common.INLINE_ICON_SIZE),
            u'disabled': not all(bookmark),
            u'text': u'Show active bookmark in the file manager...',
            u'action': functools.partial(common.reveal, u'/'.join(bookmark))
        }
        menu_set[u'asset'] = {
            u'icon': common.get_rsc_pixmap(u'assets', common.TEXT, common.INLINE_ICON_SIZE),
            u'disabled': not all(asset),
            u'text': u'Show active asset in the file manager...',
            u'action': functools.partial(common.reveal, '/'.join(asset))
        }
        menu_set[u'location'] = {
            u'icon': common.get_rsc_pixmap(u'location', common.TEXT, common.INLINE_ICON_SIZE),
            u'disabled': not all(file_),
            u'text': u'Show active location in the file manager...',
            u'action': functools.partial(common.reveal, '/'.join(file_))
        }

        self.create_menu(menu_set)


class ToolbarButton(ClickableLabel):
    """Custom QLabel with a `clicked` signal."""

    def __init__(self, parent=None):
        super(ToolbarButton, self).__init__(parent=parent)
        self.setState(False)

    def setState(self, state):
        opacity = 1.0 if state else 1.0
        pixmap = common.get_rsc_pixmap(u'custom', None, common.ROW_BUTTONS_HEIGHT, opacity=opacity)
        self.setPixmap(pixmap)


class BaseToolbarWidget(QtWidgets.QWidget):
    """Small widget to be used as a dockable item."""

    def __init__(self, parent=None):
        super(BaseToolbarWidget, self).__init__(parent=parent)
        self.context_menu_cls = ToolbarContextMenuWidget
        self._iswidgetvisible = False

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setWindowFlags(
            QtCore.Qt.Widget |
            QtCore.Qt.FramelessWindowHint
        )
        self._createUI()
        self._connectSignals()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        common.set_custom_stylesheet(self)

        self.setFixedSize(self.sizeHint())

        label = ToolbarButton(parent=self)
        # label.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.layout().addWidget(label)

    def sizeHint(self):
        return QtCore.QSize(common.ROW_BUTTONS_HEIGHT, common.ROW_BUTTONS_HEIGHT)

    def _connectSignals(self):
        pass

    def contextMenuEvent(self, event):
        """Context menu event."""
        # Custom context menu
        shift_modifier = event.modifiers() & QtCore.Qt.ShiftModifier
        alt_modifier = event.modifiers() & QtCore.Qt.AltModifier
        control_modifier = event.modifiers() & QtCore.Qt.ControlModifier
        if shift_modifier or alt_modifier or control_modifier:
            self.customContextMenuRequested.emit()
            return

        widget = self.context_menu_cls(parent=self)
        widget.move(self.mapToGlobal(self.rect().bottomLeft()))
        widget.setFixedWidth(300)
        common.move_widget_to_available_geo(widget)
        widget.exec_()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BaseToolbarWidget()
    widget.show()
    app.exec_()
