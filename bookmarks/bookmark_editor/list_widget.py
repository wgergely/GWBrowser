# -*- coding: utf-8 -*-
"""Base widget used by the Bookmark Editor subwidgets to list server, job and
bookmark items.

"""
from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import images


class OverlayWidget(QtWidgets.QWidget):
    """Widget used to display a status message over the list widget.

    """

    def __init__(self, parent=None):
        super(OverlayWidget, self).__init__(parent=parent)
        self._message = u''

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

    @QtCore.Slot(unicode)
    def set_message(self, message):
        if message == self._message:
            return

        self._message = message
        self.update()
        QtWidgets.QApplication.instance().processEvents(
            flags=QtCore.QEventLoop.AllEvents)

    def paintEvent(self, event):
        """Custom paint event used to paint the widget's message.

        """
        if not self._message and not self.parent().parent().count():
            message = self.parent().parent().default_message
        elif not self._message:
            return
        elif self._message:
            message = self._message

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(common.SECONDARY_TEXT)

        o = common.MARGIN()
        rect = self.rect().adjusted(o, o, -o, -o)
        text = QtGui.QFontMetrics(self.font()).elidedText(
            message,
            QtCore.Qt.ElideMiddle,
            rect.width(),
        )

        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            text,
        )
        painter.end()


class ListWidgetDelegate(QtWidgets.QStyledItemDelegate):
    """Custom delegate to display label-like QListWidgetItems.

    """

    def paint(self, painter, option, index):
        checked = index.data(QtCore.Qt.CheckStateRole) == QtCore.Qt.Checked
        hover = option.state & QtWidgets.QStyle.State_MouseOver
        selected = option.state & QtWidgets.QStyle.State_Selected
        focus = option.state & QtWidgets.QStyle.State_HasFocus
        checkable = index.flags() & QtCore.Qt.ItemIsUserCheckable
        decoration = index.data(QtCore.Qt.DecorationRole)
        text = index.data(QtCore.Qt.DisplayRole)
        disabled = index.flags() == QtCore.Qt.NoItemFlags

        painter.setRenderHint(
            QtGui.QPainter.Antialiasing, on=True)
        painter.setRenderHint(
            QtGui.QPainter.SmoothPixmapTransform, on=True)

        o = common.INDICATOR_WIDTH() * 0.5
        rect = option.rect.adjusted(o, o, -o, -o)

        # Background
        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(common.ROW_SEPARATOR() * 2.0)
        painter.setPen(pen)

        _ = painter.setOpacity(0.8) if hover else painter.setOpacity(0.6)
        _ = painter.setOpacity(
            0.0) if disabled else painter.setOpacity(painter.opacity())

        painter.setBrush(common.SEPARATOR)
        painter.drawRoundedRect(rect, o, o)

        painter.setPen(QtCore.Qt.NoPen)
        if selected:
            painter.setBrush(common.BACKGROUND_SELECTED)

            pen = QtGui.QPen(common.ADD)
            pen.setWidthF(common.ROW_SEPARATOR() * 3.0)
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o, o)

        if checked:
            painter.setPen(QtCore.Qt.NoPen)
            color = QtGui.QColor(common.ADD)
            color.setAlpha(150)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, o, o)

        if focus:
            painter.setBrush(QtCore.Qt.NoBrush)
            pen = QtGui.QPen(common.FAVOURITE)
            pen.setWidthF(common.ROW_SEPARATOR())
            painter.setPen(pen)
            painter.drawRoundedRect(rect, o, o)

        # Checkbox
        rect = QtCore.QRect(rect)
        rect.setWidth(rect.height())
        center = rect.center()
        h = common.MARGIN() * 0.7
        rect.setSize(QtCore.QSize(h, h))
        rect.moveCenter(center)

        h = rect.height() / 2.0
        painter.setPen(QtCore.Qt.NoPen)

        painter.setOpacity(1.0) if hover else painter.setOpacity(0.9)
        if checkable and checked:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'check', common.ADD, rect.height())
            painter.drawPixmap(rect, pixmap)
        elif checkable and not checked:
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'close', common.SEPARATOR, rect.height())
            painter.drawPixmap(rect, pixmap)
        elif not checkable and decoration and isinstance(decoration, QtGui.QPixmap):
            painter.drawPixmap(rect, decoration)
        elif not checkable and decoration and isinstance(decoration, QtGui.QIcon):
            mode = QtGui.QIcon.Normal
            if not (option.state & QtWidgets.QStyle.State_Enabled):
                mode = QtGui.QIcon.Disabled
            elif option.state & QtWidgets.QStyle.State_Selected:
                mode = QtGui.QIcon.Selected
            decoration.paint(
                painter,
                rect,
                QtCore.Qt.AlignCenter,
                mode,
                QtGui.QIcon.On
            )
        else:
            rect.setWidth(o * 2)

        # Label
        font, metrics = common.font_db.primary_font(
            font_size=common.SMALL_FONT_SIZE())

        color = common.TEXT
        color = common.TEXT_SELECTED if selected or checked else color

        painter.setBrush(color)

        x = rect.right() + common.INDICATOR_WIDTH() * 3
        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            option.rect.width() - x - common.INDICATOR_WIDTH(),
        )

        y = option.rect.center().y() + (metrics.ascent() / 2.0)

        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)
        painter.drawPath(path)


class ListWidget(QtWidgets.QListWidget):
    """A custom list widget used to display selectable item.

    """
    progressUpdate = QtCore.Signal(unicode)
    resized = QtCore.Signal(QtCore.QSize)

    def __init__(self, default_message=u'No items', parent=None):
        super(ListWidget, self).__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        self.default_message = default_message

        self.server = None
        self.job = None
        self.root = None

        self.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed
        )
        self.setAcceptDrops(False)
        self.setDragEnabled(False)
        self.setSpacing(0)
        self.setItemDelegate(ListWidgetDelegate(parent=self))
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )

        self.overlay = OverlayWidget(parent=self.viewport())
        self.overlay.show()

    def _connect_signals(self):
        self.resized.connect(self.overlay.resize)
        self.progressUpdate.connect(self.overlay.set_message)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def toggle(self, item):
        if not item.flags() & QtCore.Qt.ItemIsUserCheckable:
            return
        if item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            return
        item.setCheckState(QtCore.Qt.Unchecked)

    def addItem(self, label, icon=None, color=common.SECONDARY_TEXT):
        if isinstance(label, QtWidgets.QListWidgetItem):
            return super(ListWidget, self).addItem(label)

        _, metrics = common.font_db.primary_font(
            font_size=common.SMALL_FONT_SIZE())
        width = metrics.width(label) + common.ROW_HEIGHT() + common.MARGIN()
        item = QtWidgets.QListWidgetItem(label)

        size = QtCore.QSize(width, common.ROW_HEIGHT())
        item.setData(QtCore.Qt.SizeHintRole, size)

        if icon:
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            pixmap = images.ImageCache.get_rsc_pixmap(
                icon,
                color,
                common.ROW_HEIGHT() - (common.INDICATOR_WIDTH() * 2)
            )
            item.setData(QtCore.Qt.DecorationRole, pixmap)
        else:
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsUserCheckable
            )

        item.setCheckState(QtCore.Qt.Unchecked)
        return super(ListWidget, self).addItem(item)

    def resizeEvent(self, event):
        self.resized.emit(event.size())
