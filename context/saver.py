import re
from PySide2 import QtCore, QtWidgets, QtGui
import browser.common as common
from browser.editors import ClickableLabel
from browser.settings import path_monitor
from browser.bookmarkswidget import BookmarksModel
from browser.delegate import BaseDelegate
from browser.delegate import paintmethod
from browser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite


class ThumbnailButton(ClickableLabel):
    pass

class BookmarksWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.setFixedHeight(common.ROW_HEIGHT)
        self.setModel(BookmarksModel())
        self.view().setFixedWidth(common.WIDTH)
        self.setItemDelegate(BookmarksListDelegate(parent=self))

    def showPopup(self):
        # Selecting the active bookmark
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0, parent=QtCore.QModelIndex())
            if index.flags() & MarkedAsActive:
                self.setCurrentIndex(n)
                break

        super(BookmarksWidget, self).showPopup()

class BookmarksListDelegate(BaseDelegate):
    """The delegate used to paint the bookmark items."""

    def _get_root_text(self, index, rect, metrics):
        """Gets the text for drawing the root."""
        root = index.data(common.ParentRole)[2]
        count = index.data(common.FileDetailsRole)
        active = index.flags() & MarkedAsActive

        text = re.sub(r'[_]+', ' ', root.upper())
        text = '{} (active)'.format(text) if active else text
        text = '{} ({})'.format(text, count) if count else text

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
        text = ' {} '.format(text)
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


class Saver(QtWidgets.QWidget):
    """Item used to save a new file."""

    def __init__(self, parent=None):
        super(Saver, self).__init__(parent=parent)
        self.data = {
            'thumbnail': QtGui.QPixmap()
        }
        self._createUI()
        self._connectSignals()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        common.set_custom_stylesheet(self)

        label = ThumbnailButton()
        label.setFixedSize(QtCore.QSize(common.ROW_HEIGHT, common.ROW_HEIGHT))
        pixmap = common.get_rsc_pixmap(
            'placeholder', common.TEXT, common.ROW_HEIGHT)
        label.setPixmap(pixmap)
        self.layout().addWidget(label)

        bookmarkswidget = BookmarksWidget()
        self.layout().addWidget(bookmarkswidget)




    def select_thumbnail(self):
        """Prompts to select an image file."""
        active_paths = path_monitor.get_active_paths()
        bookmark = (
            active_paths['server'],
            active_paths['job'],
            active_paths['server']
        )

        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        self.setViewMode(QtWidgets.QFileDialog.List)
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        self.setNameFilter('Image files (*.png *.jpg  *.jpeg)')
        self.setDirectory('/'.join(bookmark))
        self.setOption(
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not self.exec_():
            return
        if not self.selectedFiles():
            return

        print file
        # TODO: Implement this fucker

    def _connectSignals(self):
        self.findChild(ThumbnailButton).clicked.connect(self.select_thumbnail)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = Saver()
    widget.show()
    app.exec_()
