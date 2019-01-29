# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""``BrowserWidget`` is the plug-in's main widget.
When launched from within Maya it inherints from MayaQWidgetDockableMixin baseclass,
otherwise MayaQWidgetDockableMixin is replaced with a ``common.LocalContext``, a dummy class.

Example:

.. code-block:: python
    :linenos:

    from mayabrowser.toolbar import BrowserWidget
    widget = BrowserWidget()
    widget.show()

The asset and the file lists are collected by the ``collector.AssetCollector``
and ```collector.FilesCollector`` classes. The gathered files then are displayed
in the ``listwidgets.AssetsListWidget`` and ``listwidgets.FilesListWidget`` items.

"""

import functools
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common

from mayabrowser.bookmarkswidget import BookmarksWidget
from mayabrowser.assetwidget import AssetWidget
from mayabrowser.fileswidget import FilesWidget
from mayabrowser.settings import local_settings, path_monitor


class StackFaderWidget(QtWidgets.QWidget):
    """Overlay widget responsible for the `stackedwidget` cross-fade effect."""

    def __init__(self, old_widget, new_widget):
        super(StackFaderWidget, self).__init__(parent=new_widget)

        self.old_pixmap = QtGui.QPixmap(new_widget.size())
        self.old_pixmap.fill(common.SEPARATOR)
        self.pixmap_opacity = 1.0

        self.timeline = QtCore.QTimeLine()
        self.timeline.valueChanged.connect(self.animate)
        self.timeline.finished.connect(self.close)
        self.timeline.setDuration(150)
        self.timeline.start()

        self.resize(new_widget.size())
        self.show()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setOpacity(self.pixmap_opacity)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.end()

    def animate(self, value):
        self.pixmap_opacity = 1.0 - value
        self.repaint()


class OverlayWidget(QtWidgets.QWidget):
    """Widget shown over the stackedwidget when picking the current list."""

    def __init__(self, new_widget):
        super(OverlayWidget, self).__init__(parent=new_widget)

        self.old_pixmap = QtGui.QPixmap(new_widget.size())
        self.old_pixmap.fill(QtGui.QColor(50, 50, 50))
        # old_widget.render(self.old_pixmap)
        self.pixmap_opacity = 0.0

        self.timeline = QtCore.QTimeLine()
        self.timeline.valueChanged.connect(self.animate)
        # self.timeline.finished.connect(self.close)
        self.timeline.setDuration(300)
        self.timeline.start()

        self.resize(new_widget.size())
        self.show()

    def animate(self, value):
        self.pixmap_opacity = (0.0 + value) * 0.8
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setOpacity(self.pixmap_opacity)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.end()


class ListStackWidget(QtWidgets.QStackedWidget):
    """Stacked widget to switch between the Bookmark-, Asset - and File lists."""

    def __init__(self, parent=None):
        super(ListStackWidget, self).__init__(parent=parent)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.setMinimumHeight(common.ROW_HEIGHT)
        self.setMinimumWidth(200)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH, common.HEIGHT)


class ListControlWidget(QtWidgets.QWidget):
    """The bar above the list to control the mode, filters and sorting."""

    modeChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(ListControlWidget, self).__init__(parent=parent)
        self._createUI()
        self._connectSignals()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )


        # Mode indicator button
        self.layout().addSpacing(common.INDICATOR_WIDTH)
        label = ModePickButton()
        label.setStyleSheet("""
            QLabel {{
                background-color: rgba({});
            }}
        """.format('{},{},{},{}'.format(*common.SEPARATOR.getRgb())))
        label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.layout().addWidget(label)  # QComboBox

        # Listwidget
        self.layout().addWidget(ChangeListWidget(), 1)

        self.layout().addStretch(1)

        # Add bookmarks
        label = AddBookmarkButton()
        label.setStyleSheet("""
            QLabel {{
                background-color: rgba({});
            }}
        """.format('{},{},{},{}'.format(*common.SEPARATOR.getRgb())))
        label.setFixedSize(QtCore.QSize(common.ROW_BUTTONS_HEIGHT, common.ROW_BUTTONS_HEIGHT))
        pixmap = common.get_rsc_pixmap('todo_add', common.FAVOURITE, common.ROW_BUTTONS_HEIGHT / 1.5)
        label.setPixmap(pixmap)
        self.layout().addWidget(label)


    def _connectSignals(self):
        modepickbutton = self.findChild(ModePickButton)
        addbookmarkbutton = self.findChild(AddBookmarkButton)

        combobox = self.findChild(ChangeListWidget)
        bookmarkswidget = self.parent().findChild(BookmarksWidget)

        modepickbutton.clicked.connect(combobox.showPopup)
        combobox.currentIndexChanged.connect(self.setCurrentMode)
        addbookmarkbutton.clicked.connect(bookmarkswidget.show_add_bookmark_widget)

    @QtCore.Slot(int)
    def setCurrentMode(self, idx):
        """Sets the current mode of ``ListControlWidget``."""
        combobox = self.findChild(ChangeListWidget)
        label = self.findChild(ModePickButton)

        if idx == 0:  # Bookmarks
            pixmap = common.get_rsc_pixmap(
                'bookmarks', common.FAVOURITE, common.ROW_BUTTONS_HEIGHT / 1.5)
        elif idx == 1:  # Assets
            pixmap = common.get_rsc_pixmap(
                'assets', common.FAVOURITE, common.ROW_BUTTONS_HEIGHT / 1.5)
        elif idx == 2:  # Files
            pixmap = common.get_rsc_pixmap(
                'files', common.FAVOURITE, common.ROW_BUTTONS_HEIGHT / 1.5)

        label.setPixmap(pixmap)
        combobox.setCurrentIndex(idx)


class BrowserWidget(QtWidgets.QWidget):
    """Main widget to browse pipline data."""

    def __init__(self, parent=None):
        super(BrowserWidget, self).__init__(parent=parent)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint
        )

        self._contextMenu = None

        self.stackedfaderwidget = None
        self.stackedwidget = None
        self.bookmarkswidget = None
        self.assetswidget = None
        self.fileswidget = None



        # Applying the initial config settings.
        active_paths = path_monitor.get_active_paths()
        self.bookmarkswidget = BookmarksWidget()
        self.assetswidget = AssetWidget((
            active_paths['server'],
            active_paths['job'],
            active_paths['root']
        ))
        self.fileswidget = FilesWidget((
            active_paths['server'],
            active_paths['job'],
            active_paths['root'],
            active_paths['asset'])
        )

        # Create layout
        self._createUI()

        self._init_saved_state()
        self._connectSignals()

    def _init_saved_state(self):
        # Setting initial state
        idx = local_settings.value(
            'widget/{}/current_index'.format(self.__class__.__name__))
        if not idx:
            idx = 0
        self.stackedwidget.setCurrentIndex(idx)
        self.listcontrolwidget.setCurrentMode(idx)

    def _createUI(self):
        """Creates the layout.

        +-----------------+
        | header          |
        +-----------------+
        |listcontrolwidget|     A row of buttons to toggle filters and views.
        +-----------------+
        |                 |
        |                 |
        |  stackedwidget  |     This a the widget containing the lists widgets of `assets`, `assets` and `files`.
        |                 |
        |                 |
        +-----------------+
        |    status_bar   |     Infobar
        +-----------------+

        """
        common.set_custom_stylesheet(self)

        # Main layout
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, common.INDICATOR_WIDTH, 0, 0)
        self.layout().setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )

        self.stackedwidget = ListStackWidget(parent=self)
        self.stackedwidget.addWidget(self.bookmarkswidget)
        self.stackedwidget.addWidget(self.assetswidget)
        self.stackedwidget.addWidget(self.fileswidget)

        self.listcontrolwidget = ListControlWidget(parent=self)

        self.status_bar = QtWidgets.QStatusBar()
        self.status_bar.setFixedHeight(common.ROW_FOOTER_HEIGHT)
        self.status_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.layout().addWidget(self.listcontrolwidget)
        self.layout().addWidget(self.stackedwidget)
        self.layout().addWidget(self.status_bar)

    def _connectSignals(self):
        self.stackedwidget.currentChanged.connect(
            self.listcontrolwidget.setCurrentMode)

        # Bookmark
        self.bookmarkswidget.activeBookmarkChanged.connect(
            self.assetswidget.model().sourceModel().set_bookmark)
        self.bookmarkswidget.activeBookmarkChanged.connect(
            functools.partial(self.mode_changed, 1)
        )
        # Asset
        self.assetswidget.activeAssetChanged.connect(
            self.fileswidget.model().sourceModel().set_asset)
        self.assetswidget.activeAssetChanged.connect(
            functools.partial(self.mode_changed, 2)
        )

        # Statusbar
        self.bookmarkswidget.entered.connect(self.entered)
        self.assetswidget.entered.connect(self.entered)
        self.fileswidget.entered.connect(self.entered)

    def entered(self, index):
        """Custom itemEntered signal."""
        message = index.data(QtCore.Qt.StatusTipRole)
        self.status_bar.showMessage(message, timeout=1500)

    def mode_changed(self, idx, *args, **kwargs):
        """Saves and applies the given mode."""
        local_settings.setValue(
            'widget/{}/current_index'.format(self.__class__.__name__),
            idx
        )
        self.activate_widget(self.stackedwidget.widget(idx))

    def activate_widget(self, widget):
        """Method to change between views."""
        self.stackedfaderwidget = StackFaderWidget(
            self.stackedwidget.currentWidget(), widget)
        self.stackedwidget.setCurrentWidget(widget)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH, common.HEIGHT)


class ModePickButton(QtWidgets.QLabel):
    """Custom QLabel with a `clicked` signal."""
    clicked = QtCore.Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class AddBookmarkButton(QtWidgets.QLabel):
    """Custom QLabel with a `clicked` signal."""
    clicked = QtCore.Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()


class ChangeListWidgetDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ChangeListWidgetDelegate, self).__init__(parent=parent)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().parent().width(), common.ROW_HEIGHT)

    def paint(self, painter, option, index):
        """The main paint method."""
        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )
        selected = option.state & QtWidgets.QStyle.State_Selected
        args = (painter, option, index, selected)

        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_name(*args)

    def paint_name(self, *args):
        painter, option, index, _ = args
        active = self.parent().currentIndex() == index.row()
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter.save()

        font = QtGui.QFont('Roboto Black')
        font.setPointSize(9.0)
        font.setBold(True)
        painter.setFont(font)

        rect = QtCore.QRect(option.rect)
        rect.moveLeft(rect.left() + rect.height() + common.MARGIN)
        rect.setRight(rect.width() - (common.MARGIN * 2))

        if active:
            painter.setPen(QtGui.QPen(common.FAVOURITE))
        else:
            painter.setPen(QtGui.QPen(common.TEXT))

        if hover and not active:
            painter.setPen(QtGui.QPen(common.TEXT_SELECTED))

        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))

        text = index.data(QtCore.Qt.DisplayRole).upper()
        text = '{}  |  Current'.format(text) if active else text
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )
        painter.restore()

    def paint_background(self, *args):
        """Paints the background."""
        painter, option, _, selected = args
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        if selected:
            color = common.BACKGROUND_SELECTED
        else:
            color = common.BACKGROUND
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(option.rect)

    def paint_thumbnail(self, *args):
        """Paints the thumbnail of the item."""
        painter, option, index, selected = args
        active = self.parent().currentIndex() == index.row()
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        painter.save()

        if selected:
            color = common.THUMBNAIL_BACKGROUND_SELECTED
        else:
            color = common.THUMBNAIL_BACKGROUND

        rect = QtCore.QRect(option.rect)
        rect.setWidth(rect.height())

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        # Shadow next to the thumbnail
        shd_rect = QtCore.QRect(option.rect)
        shd_rect.setLeft(rect.left() + rect.width())

        gradient = QtGui.QLinearGradient(
            shd_rect.topLeft(), shd_rect.topRight())
        gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 50))
        gradient.setColorAt(0.2, QtGui.QColor(68, 68, 68, 0))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRect(shd_rect)

        gradient = QtGui.QLinearGradient(
            shd_rect.topLeft(), shd_rect.topRight())
        gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 50))
        gradient.setColorAt(0.02, QtGui.QColor(68, 68, 68, 0))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRect(shd_rect)

        color = common.TEXT
        if active:
            color = common.FAVOURITE

        if index.row() == 0:
            pixmap = common.get_rsc_pixmap('bookmark', color, rect.height())
        if index.row() == 1:
            pixmap = common.get_rsc_pixmap('package', color, rect.height())
        if index.row() == 2:
            pixmap = common.get_rsc_pixmap('file', color, rect.height())


        painter.drawPixmap(
            rect,
            pixmap,
            pixmap.rect()
        )
        painter.restore()


class ChangeListWidget(QtWidgets.QComboBox):
    """Drop-down widget to switch between the list"""

    def __init__(self, parent=None):
        super(ChangeListWidget, self).__init__(parent=parent)
        self.setItemDelegate(ChangeListWidgetDelegate(parent=self))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.overlayWidget = None

        self.addItem('Bookmarks')
        self.addItem('Assets')
        self.addItem('Files')

    def showPopup(self):
        """Toggling overlay widget when combobox is shown."""
        self.overlayWidget = OverlayWidget(
            self.parent().parent().stackedwidget)
        popup = self.findChild(QtWidgets.QFrame)
        popup.show()

        pos = self.parent().mapToGlobal(self.parent().rect().bottomLeft())
        popup.move(pos)
        popup.setFixedWidth(self.parent().rect().width())
        popup.setFixedHeight(common.ROW_HEIGHT * 3)

        # Selecting the current item
        index = self.view().model().index(self.currentIndex(), 0)
        self.view().selectionModel().setCurrentIndex(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect
        )

        # Hiding the AddBookmarkButton
        self.parent().findChild(AddBookmarkButton).hide()

    def hidePopup(self):
        """Toggling overlay widget when combobox is shown."""
        if self.overlayWidget:
            self.overlayWidget.close()
        super(ChangeListWidget, self).hidePopup()

        # Showing the AddBookmarkButton
        self.parent().findChild(AddBookmarkButton).show()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BrowserWidget()
    # widget.move(50, 50)
    widget.show()
    app.exec_()
