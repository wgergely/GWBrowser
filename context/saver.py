import re
from PySide2 import QtCore, QtWidgets, QtGui

import browser.common as common

from browser.delegate import BaseDelegate
from browser.delegate import paintmethod
from browser.editors import ClickableLabel
from browser.settings import Active

from browser.bookmarkswidget import BookmarksModel
from browser.assetwidget import AssetModel

from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite


class ThumbnailButton(ClickableLabel):
    """Button used to select the thumbnail for this item."""

    def __init__(self, parent=None):
        super(ThumbnailButton, self).__init__(parent=parent)
        self.setFixedSize(QtCore.QSize(common.ROW_HEIGHT, common.ROW_HEIGHT))
        pixmap = common.get_rsc_pixmap(
            u'placeholder', common.TEXT, common.ROW_HEIGHT)
        self.setPixmap(pixmap)

class ParentButton(ClickableLabel):
    def __init__(self, parent=None):
        super(ParentButton, self).__init__(parent=parent)
        self.setStyleSheet("""
            QLabel {{
                background-color: rgba({});
            }}
        """.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND_SELECTED.getRgb())))
        self.setFixedSize(QtCore.QSize(common.ROW_HEIGHT / 2.0, common.ROW_HEIGHT / 2.0))
        pixmap = common.get_rsc_pixmap(
            u'folder', common.TEXT, common.INLINE_ICON_SIZE)
        self.setPixmap(pixmap)

        self.clicked.connect(self.get_parent_folders)

    def get_parent_folders(self):
        """Collects the available parent folders."""
        active_paths = Active.get_active_paths()
        parent = (
            active_paths[u'server'],
            active_paths[u'job'],
            active_paths[u'root'],
            active_paths[u'asset'],
            common.ScenesFolder
        )
        if not all(parent):
            return

        path = u'/'.join(parent)
        dir_ = QtCore.QDir(path)
        dir_.setFilter(QtCore.QDir.NoDotAndDotDot |
                       QtCore.QDir.Dirs |
                       QtCore.QDir.Readable)
        it = QtCore.QDirIterator(
            dir_, flags=QtCore.QDirIterator.Subdirectories)

        # menus =
        while it.hasNext():
            filepath = it.next()
            rootpath = filepath.replace(path, u'')
            print rootpath.strip(u'/')


class BookmarksWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setModel(BookmarksModel(parent=self))

        self.setFixedHeight(common.ROW_HEIGHT / 2.0)
        self.view().setFixedWidth(common.WIDTH)
        self.view().parent().setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        self.view().setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setItemDelegate(BookmarksListDelegate(parent=self))

        # Selecting the active bookmark
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                self.setCurrentIndex(n)
                self.view().scrollTo(index)
                break
        self.view().setDisabled(True)
        self.view().parent().setDisabled(True)


class BookmarksListDelegate(BaseDelegate):
    """The delegate used to paint the bookmark items."""

    def _get_root_text(self, index, rect, metrics):
        """Gets the text for drawing the root."""
        root = index.data(common.ParentRole)[2]
        count = index.data(common.FileDetailsRole)
        active = index.flags() & MarkedAsActive

        text = re.sub(r'[_]+', ' ', root.upper())
        text = u'{} ({})'.format(text, count) if count else text

        return metrics.elidedText(
            text,
            QtCore.Qt.ElideLeft,
            rect.width()
        )

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_archived(*args)
        self.paint_name(*args)
        self.paint_active_indicator(*args)

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, _, selected, _, active, _, _ = args

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        if selected and not active:
            color = QtGui.QColor(common.BACKGROUND_SELECTED)
        elif not selected and not active:
            color = QtGui.QColor(common.BACKGROUND)
        elif selected and active:
            color = QtGui.QColor(49, 107, 218)
        elif not selected and active:
            color = QtGui.QColor(29, 87, 198)

        rect = QtCore.QRect(option.rect)
        rect.setTop(rect.top() + 1)
        rect.setBottom(rect.bottom() - 1)

        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

    @paintmethod
    def paint_name(self, *args):
        """Paints name of the ``bookmarkswidget``'s items."""
        painter, option, index, selected, _, _, _, _ = args

        active = index.flags() & MarkedAsActive
        count = index.data(common.FileDetailsRole)

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)
        rect.setLeft(option.rect.left() + common.MARGIN)
        painter.setFont(font)

        # Centering rect
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        # Job
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[\W\d\_]+', '', text)
        text = u' {} '.format(text)
        width = metrics.width(text)
        rect.setWidth(width)

        offset = common.INDICATOR_WIDTH

        # Name background
        pen = QtGui.QPen(common.FAVOURITE)
        pen.setWidth(offset)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(common.FAVOURITE))
        painter.drawRoundedRect(rect, 2, 2)
        # Name
        painter.setPen(common.TEXT)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            text
        )

        if count:
            color = QtGui.QColor(common.TEXT)
        else:
            color = QtGui.QColor(common.TEXT_DISABLED)
            if selected:
                color = QtGui.QColor(common.TEXT)
        if active:
            color = common.SELECTION

        rect.setLeft(rect.right() + common.MARGIN)
        rect.setRight(option.rect.right() - common.MARGIN)
        # Name
        text = self._get_root_text(index, rect, metrics)

        painter.setFont(font)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(color)
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ROW_BUTTONS_HEIGHT)


class AssetsWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(AssetsWidget, self).__init__(parent=parent)
        active_paths = Active.get_active_paths()
        bookmark = (
            active_paths[u'server'],
            active_paths[u'job'],
            active_paths[u'root']
        )
        self.setModel(AssetModel(bookmark, parent=self))


        self.setFixedHeight(common.ROW_HEIGHT / 2.0)
        self.view().setFixedWidth(common.WIDTH)
        self.view().setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view().parent().setFixedHeight(common.ASSET_ROW_HEIGHT)
        self.setItemDelegate(AssetWidgetDelegate(parent=self))

        # Selecting the active bookmark
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                self.setCurrentIndex(n)
                self.view().scrollTo(index)
                break
        self.view().setDisabled(True)
        self.view().parent().setDisabled(True)

    def inline_icons_count(self):
        return 0


class AssetWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        #
        self.paint_name(*args)
        self.paint_description(*args)
        #
        # self.paint_selection_indicator(*args)
        self.paint_active_indicator(*args)

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``AssetWidget``."""
        painter, option, index, _, _, active, _, _ = args

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        # Asset name
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[^0-9a-zA-Z]+', ' ', text)
        text = re.sub(r'[_]{1,}', '_', text)
        text = metrics.elidedText(
            text.upper(),
            QtCore.Qt.ElideRight,
            rect.width()
        )

        color = self.get_state_color(option, index, common.TEXT)

        painter.setFont(font)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)


class Saver(QtWidgets.QDialog):
    """Item used to save a new file."""

    def __init__(self, parent=None):
        super(Saver, self).__init__(parent=parent)
        self.data = {
            u'thumbnail': QtGui.QPixmap()
        }
        self._createUI()
        self._connectSignals()

    def _createUI(self):
        o = common.INDICATOR_WIDTH

        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(o * 2, o * 2, o * 2, o * 2)
        self.layout().setSpacing(o)

        common.set_custom_stylesheet(self)
        stylesheet = u'Saver {{background-color: rgba({});}}'.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND.getRgb()))
        stylesheet = u'{}\n{}'.format(self.styleSheet(), stylesheet)
        self.setStyleSheet(stylesheet)


        label = ThumbnailButton()
        self.layout().addWidget(label)

        stack = QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(stack)
        stack.layout().setContentsMargins(0,0,0,0)
        stack.layout().setSpacing(0)

        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(o,o,o,o)
        row.layout().setSpacing(o)

        row.layout().addWidget(BookmarksWidget(parent=self))
        row.layout().addWidget(AssetsWidget(parent=self))
        row.layout().addWidget(ParentButton(parent=self))
        stack.layout().addWidget(row)

        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(o,o,o,o)
        row.layout().setSpacing(o)

        editor = QtWidgets.QLineEdit()
        editor.setPlaceholderText(u'Add description here...')
        editor.setFixedWidth(350)
        row.layout().addWidget(editor)
        stack.layout().addWidget(row)

        self.layout().addWidget(stack)


    def select_thumbnail(self):
        """Prompts to select an image file."""
        active_paths = Active.get_active_paths()
        bookmark = (
            active_paths[u'server'],
            active_paths[u'job'],
            active_paths[u'root']
        )
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(u'Image files (*.png *.jpg  *.jpeg)')
        dialog.setDirectory(u'/'.join(bookmark))
        dialog.setOption(
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not dialog.exec_():
            return
        if not dialog.selectedFiles():
            return

        print dialog.selectedFiles()
        # TODO: Implement this fucker

    def _connectSignals(self):
        self.findChild(ThumbnailButton).clicked.connect(self.select_thumbnail)

        # bookmarksmodel = self.findChild(BookmarksModel)
        # assetmodel = self.findChild(AssetModel)
        # bookmarksmodel.activeBookmarkChanged.connect(assetmodel.set_bookmark)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = Saver()
    widget.show()
    app.exec_()
