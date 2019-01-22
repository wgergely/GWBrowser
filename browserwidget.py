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

from collections import OrderedDict
import functools
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common

from mayabrowser.bookmarksWidget import BookmarksWidget
from mayabrowser.assetwidget import AssetWidget
from mayabrowser.fileswidget import FilesWidget
from mayabrowser.settings import local_settings, path_monitor


SingletonType = type(QtWidgets.QWidget)


class Singleton(SingletonType):
    """Singleton metaclass for the BrowserWidget widget.

    Note:
        We have to supply an appropiate type object as the base class,
        'object' won't work. Creating type(QtWidgets.QWidget) seems to function.

    """
    _instances = {}

    def __call__(cls, *args, **kwargs):  # pylint: disable=E0213
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class FaderWidget(QtWidgets.QWidget):
    """Overlaywidget responsible for the `stacked_widget` cross-fade effect."""

    def __init__(self, old_widget, new_widget):
        super(FaderWidget, self).__init__(parent=new_widget)

        self.old_pixmap = QtGui.QPixmap(new_widget.size())
        self.old_pixmap.fill(QtGui.QColor(50, 50, 50))
        # old_widget.render(self.old_pixmap)
        self.pixmap_opacity = 1.0

        self.timeline = QtCore.QTimeLine()
        self.timeline.valueChanged.connect(self.animate)
        self.timeline.finished.connect(self.close)
        self.timeline.setDuration(200)
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
    """Widget shown over the stacked_widget when mode_select_widget is active."""

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


class BrowserWidget(QtWidgets.QWidget):  # pylint: disable=E1139
    """Singleton MayaQWidgetDockable widget containing the lists of locations, assets and scenes.

    Attributes:
        instances (dict):               Class instances.
        assets_widget (QListWidget):   List of the collected Maya assets.
        files_widget (QListWidget):      List of files found associated with the asset.

        configChanged (QtCore.QSignal): Custom signal emitted when the configuration file changes.

    """

    __metaclass__ = Singleton
    # """Singleton metaclass."""

    instances = {}

    def __init__(self, parent=None):
        super(BrowserWidget, self).__init__(parent=parent)
        self.instances[self.objectName()] = self

        # Applying the initial config settings.
        self.current_paths = OrderedDict(path_monitor.get_active_paths())

        self._contextMenu = None
        self.fader_widget = None

        # Create layout
        self._createUI()

        self.bookmarks_widget = BookmarksWidget()
        self.assets_widget = AssetWidget((
            self.current_paths['server'],
            self.current_paths['job'],
            self.current_paths['root']
        ))
        self.files_widget = FilesWidget((
            self.current_paths['server'],
            self.current_paths['job'],
            self.current_paths['root'],
            self.current_paths['asset'])
        )

        self.stacked_widget.addWidget(self.bookmarks_widget)
        self.stacked_widget.addWidget(self.assets_widget)
        self.stacked_widget.addWidget(self.files_widget)

        self._init_saved_state()
        self._connectSignals()

    def _init_saved_state(self):
        # Setting initial state
        idx = local_settings.value(
            'widget/{}/current_index'.format(self.__class__.__name__))
        if not idx:
            idx = 0
        self.stacked_widget.setCurrentIndex(idx)
        self.mode_select_widget.setCurrentIndex(idx)

    def _createUI(self):
        """Creates the layout.

        +-----------------+
        |   row_buttons   |     A row of buttons to toggle filters and views.
        +-----------------+
        |                 |
        |                 |
        | stacked_widget  |     This a the widget containing the lists widgets of `assets`, `assets` and `files`.
        |                 |
        |                 |
        +-----------------+
        |    status_bar   |     Infobar
        +-----------------+

        """
        common.set_custom_stylesheet(self)

        # Main layout
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.setMinimumWidth(200.0)
        # self.setPreferredWidth(common.WIDTH)
        self.setMaximumWidth(common.WIDTH * 2)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )

        self.row_buttons = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(self.row_buttons)

        self.row_buttons.layout().setContentsMargins(0, 0, 0, 0)
        self.row_buttons.layout().setSpacing(0)
        self.row_buttons.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.row_buttons.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.stacked_widget = QtWidgets.QStackedWidget()
        self.stacked_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.stacked_widget.layout().setSpacing(0)
        self.stacked_widget.setMinimumHeight(common.ROW_HEIGHT)
        self.stacked_widget.sizeHint = self.sizeHint
        self.stacked_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.status_bar = QtWidgets.QStatusBar()
        self.status_bar.setFixedHeight(common.ROW_FOOTER_HEIGHT)
        self.status_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.layout().addWidget(self.row_buttons)
        self.layout().addWidget(self.stacked_widget)
        self.layout().addWidget(self.status_bar)

        self.mode_select_widget = DropdownWidget(parent=self)
        for idx, data in enumerate((('Bookmarks', 'Alt+1'), ('Assets', 'Alt+2'), ('Files', 'Alt+3'))):
            self.mode_select_widget.addItem(data[0])
            self.mode_select_widget.setItemData(
                idx, data[1], QtCore.Qt.UserRole)

        self.row_buttons.layout().addWidget(self.mode_select_widget, 1)

    def _connectSignals(self):
        self.mode_select_widget.currentIndexChanged.connect(self.mode_changed)
        self.stacked_widget.currentChanged.connect(
            self.mode_select_widget.setCurrentIndex)

        # Bookmark
        self.bookmarks_widget.activeBookmarkChanged.connect(
            self.assets_widget.set_bookmark)
        self.bookmarks_widget.activeBookmarkChanged.connect(
            functools.partial(self.mode_changed, 1)
        )
        # Asset
        self.assets_widget.activeAssetChanged.connect(
            self.files_widget.set_asset)
        self.assets_widget.activeAssetChanged.connect(
            functools.partial(self.mode_changed, 2)
        )

        # Statusbar
        self.bookmarks_widget.itemEntered.connect(self.itemEntered)
        self.assets_widget.itemEntered.connect(self.itemEntered)
        self.files_widget.itemEntered.connect(self.itemEntered)

    def itemEntered(self, item):
        """Custom itemEntered signal."""
        message = item.data(QtCore.Qt.StatusTipRole)
        self.status_bar.showMessage(message, timeout=1500)

    def mode_changed(self, idx, *args, **kwargs):
        """Saves and applies the given mode."""
        local_settings.setValue(
            'widget/{}/current_index'.format(self.__class__.__name__),
            idx
        )
        self.activate_widget(self.stacked_widget.widget(idx))

    def activate_widget(self, widget):
        """Method to change between views."""
        self.fader_widget = FaderWidget(
            self.stacked_widget.currentWidget(), widget)
        self.stacked_widget.setCurrentWidget(widget)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH, common.HEIGHT)


class DropdownWidgetDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(DropdownWidgetDelegate, self).__init__(parent=parent)

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
        self.paint_selection_indicator(*args)
        self.paint_name(*args)

    def paint_selection_indicator(self, *args):
        """Paints the blue leading rectangle to indicate the current selection."""
        painter, option, _, selected = args

        if not selected:
            return

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(common.SELECTION))
        rect = QtCore.QRect(option.rect)
        rect.setWidth(4)
        painter.drawRect(rect)

    def paint_name(self, *args):
        painter, option, index, _ = args

        painter.save()

        font = QtGui.QFont('Roboto Black')
        font.setPointSize(9.0)
        font.setBold(True)
        painter.setFont(font)

        rect = QtCore.QRect(option.rect)
        rect.moveLeft(rect.left() + 4 + rect.height() + common.MARGIN)
        rect.setRight(rect.width() - (common.MARGIN * 2))
        painter.setPen(QtGui.QPen(common.TEXT))
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))

        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            index.data(QtCore.Qt.DisplayRole).upper()
        )
        font = QtGui.QFont('Roboto Medium')
        font.setPointSize(8)
        painter.setFont(font)

        painter.setPen(QtGui.QPen(common.SECONDARY_TEXT))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
            index.data(QtCore.Qt.UserRole)
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

        painter.save()

        if selected:
            color = common.THUMBNAIL_BACKGROUND_SELECTED
        else:
            color = common.THUMBNAIL_BACKGROUND

        rect = QtCore.QRect(option.rect)
        # Making the aspect ratio of the image 16/9
        rect.setWidth(rect.height())
        rect.moveLeft(rect.left() + 4)  # Accounting for the leading indicator

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

        if index.row() == 0:
            path = '{}/rsc/bookmark.png'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )
        if index.row() == 1:
            path = '{}/rsc/package.png'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )
        if index.row() == 2:
            path = '{}/rsc/file.png'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )

        # Thumbnail image
        if path in common.IMAGE_CACHE:
            image = common.IMAGE_CACHE[path]
        else:
            image = QtGui.QImage()
            image.load(path)
            image = common.resize_image(
                image,
                option.rect.height()
            )
            common.IMAGE_CACHE[path] = image

        # Factoring aspect ratio in
        longer = float(max(image.rect().width(), image.rect().height()))
        factor = float(rect.width() / longer)
        if image.rect().width() < image.rect().height():
            rect.setWidth(float(image.rect().width()) * factor)
        else:
            rect.setHeight(float(image.rect().height()) * factor)

        rect.moveLeft(
            rect.left() + ((option.rect.height() - rect.width()) * 0.5)
        )
        rect.moveTop(
            rect.top() + ((option.rect.height() - rect.height()) * 0.5)
        )

        painter.drawImage(
            rect,
            image,
            image.rect()
        )
        painter.restore()


class DropdownWidget(QtWidgets.QComboBox):
    """Custom dropdown widget to select the current mode."""

    def __init__(self, parent=None):
        super(DropdownWidget, self).__init__(parent=parent)
        self.setItemDelegate(DropdownWidgetDelegate(parent=self))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.overlayWidget = None

    def showPopup(self):
        """Toggling overlay widget when combobox is shown."""
        self.overlayWidget = OverlayWidget(
            self.parent().parent().stacked_widget)
        super(DropdownWidget, self).showPopup()

    def hidePopup(self):
        """Toggling overlay widget when combobox is shown."""
        if self.overlayWidget:
            self.overlayWidget.close()
        super(DropdownWidget, self).hidePopup()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = BrowserWidget()
    # widget.move(50, 50)
    widget.show()
    app.exec_()
