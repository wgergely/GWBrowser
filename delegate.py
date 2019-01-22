# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201
"""Main modules defining the delegates used to represent the QListWidgetItems."""


import re
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
import mayabrowser.settings as configparser
from mayabrowser.settings import AssetSettings


class BaseDelegate(QtWidgets.QAbstractItemDelegate):
    """Base delegate containing methods to draw our list items."""

    def __init__(self, parent=None):
        super(BaseDelegate, self).__init__(parent=parent)

    def _get_paint_args(self, painter, option, index):
        """Returns a list of boolean arguments used to paint items."""
        selected = option.state & QtWidgets.QStyle.State_Selected
        focused = option.state & QtWidgets.QStyle.State_HasFocus

        favourite = index.flags() & configparser.MarkedAsFavourite
        archived = index.flags() & configparser.MarkedAsArchived
        active = index.flags() & configparser.MarkedAsActive

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )
        args = (painter, option, index, selected,
                focused, active, archived, favourite)
        return args

    @staticmethod
    def get_text_area(rect, emphasis):
        """Returns the elements needed to paint primary text elements.
        Note that the returned rectangle covers the whole

        Args:
            rect (QRect): style option item.
            section (int): The empasis of the font.

        Returns:
            Tuple: Tuple of [`QRect`, `QFont`, `QFontMetrics`]

        """
        rect = QtCore.QRect(rect)
        rect.setLeft(
            common.INDICATOR_WIDTH +
            rect.height() +
            common.MARGIN
        )
        rect.setRight(rect.right() - common.MARGIN)

        # Primary font is used to draw item names
        if emphasis is common.PRIMARY_FONT:
            font = QtGui.QFont('Roboto Black')
            font.setPointSizeF(9)
            font.setBold(False)
            font.setItalic(False)
        # Secondary fonts are used to draw description and file information
        elif emphasis is common.SECONDARY_FONT:
            font = QtGui.QFont('Roboto Medium')
            font.setPointSizeF(8.0)
            font.setBold(False)
            font.setItalic(False)
        elif emphasis is common.TERCIARY_FONT:
            font = QtGui.QFont('Roboto')
            font.setPointSizeF(8.0)
            font.setBold(False)
            font.setItalic(True)

        # Metrics
        metrics = QtGui.QFontMetrics(font)
        return rect, font, metrics

    @staticmethod
    def get_state_color(option, index, color):
        """Returns a modified colour taking the current item state into
        consideration.

        Args:
            option (QStyleOption): Description of parameter `option`.
            index (QModelIndex): Item's index.
            color (QColor): The colour to apply the state to.

        Returns:
            QColor: The new colour.

        """
        selected = option.state & QtWidgets.QStyle.State_Selected
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        # Custom states
        favourite = index.flags() & configparser.MarkedAsFavourite
        archived = index.flags() & configparser.MarkedAsArchived
        active = index.flags() & configparser.MarkedAsActive

        color = QtGui.QColor(color)

        if favourite:
            color = QtGui.QColor(common.FAVOURITE)
        if active:
            color = QtGui.QColor(common.SELECTION)

        if selected:
            color.setRed(color.red() / 0.92)
            color.setGreen(color.green() / 0.92)
            color.setBlue(color.blue() / 0.92)
            return color

        if archived:  # Disabled colour
            color.setRed(color.red() / 1.96)
            color.setGreen(color.green() / 1.96)
            color.setBlue(color.blue() / 1.96)

        if hover:
            color.setRed(color.red() + 15)
            color.setGreen(color.green() + 15)
            color.setBlue(color.blue() + 15)

        return color

    def paint_focus(self, *args):
        """Paintets the rectangle around theitem indicating keyboard focus."""
        painter, option, index, _, focused, _, _, _ = args

        if not focused:
            return

        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=False
        )

        color = self.get_state_color(option, index, common.SELECTION)
        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(color)
        pen.setWidth(1.0)

        rect = QtCore.QRectF(option.rect)
        rect.setLeft(rect.left())
        rect.setTop(rect.top() + 1)
        rect.setRight(rect.right() - 1)
        rect.setBottom(rect.bottom() - 1)

        path = QtGui.QPainterPath()
        path.addRect(rect)
        painter.strokePath(path, pen)

        painter.restore()

    def paint_archived_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, archived, _ = args
        if option.rect.width() < 360.0:
            return

        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )

        rect, bg_rect = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 1)

        pos = QtGui.QCursor().pos()
        pos = self.parent().mapFromGlobal(pos)

        # Icon
        if archived:
            color = QtGui.QColor(common.FAVOURITE)
        else:
            color = QtGui.QColor(common.SECONDARY_TEXT)

        painter.setPen(QtCore.Qt.NoPen)

        if archived:
            pixmap = common.get_rsc_pixmap(
                'archived', color, common.INLINE_ICON_SIZE)
            color = QtGui.QColor(common.SEPARATOR)
            color.setAlpha(60)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRoundedRect(bg_rect, 2.0, 2.0)
        else:
            pixmap = common.get_rsc_pixmap(
                'active', color, common.INLINE_ICON_SIZE)

        # Icon
        painter.drawPixmap(rect, pixmap)

        painter.restore()

    def paint_favourite_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, _, favourite = args
        if option.rect.width() < 360.0:
            return

        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )

        rect, bg_rect = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 0)

        # Icon
        if favourite:
            color = QtGui.QColor(common.FAVOURITE)
        else:
            color = QtGui.QColor(common.SECONDARY_TEXT)

        pos = QtGui.QCursor().pos()
        pos = self.parent().mapFromGlobal(pos)

        pixmap = common.get_rsc_pixmap(
            'favourite', color, common.INLINE_ICON_SIZE)

        painter.setPen(QtCore.Qt.NoPen)
        if favourite:
            color = QtGui.QColor(common.SEPARATOR)
            color.setAlpha(60)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRoundedRect(bg_rect, 2.0, 2.0)

        # Icon
        painter.drawPixmap(rect, pixmap)

        painter.restore()

    def paint_background(self, *args):
        """Paints the background."""
        painter, option, _, selected, _, active, _, _ = args

        painter.save()
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        if selected and not active:
            color = common.BACKGROUND_SELECTED
        elif not selected and not active:
            color = common.BACKGROUND
        elif selected and active:
            color = QtGui.QColor(common.SELECTION)
            color.setRed(color.red() - 20)
            color.setGreen(color.green() - 20)
            color.setBlue(color.blue())
        elif not selected and active:
            color = QtGui.QColor(49, 107, 218)

        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(option.rect)

        painter.restore()

    def paint_separators(self, *args):
        """Paints horizontal separators."""
        painter, option, _, selected, _, _, _, _ = args

        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=False
        )

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(common.SEPARATOR))

        if not selected:
            THICKNESS = 0.5
        else:
            THICKNESS = 0.5

        # Bottom
        rect = QtCore.QRectF(
            option.rect.left(),
            option.rect.top() + option.rect.height() - THICKNESS,
            option.rect.width(),
            (THICKNESS)
        )
        painter.drawRect(rect)

        # Top
        rect = QtCore.QRectF(
            option.rect.left(),
            option.rect.top(),
            option.rect.width(),
            (THICKNESS)
        )
        painter.drawRect(rect)
        painter.save()

    def paint_selection_indicator(self, *args):
        """Paints the leading rectangle indicating the selection."""
        painter, option, index, selected, _, _, _, _ = args

        painter.save()

        rect = QtCore.QRect(option.rect)
        rect.setWidth(common.INDICATOR_WIDTH)
        rect.setTop(rect.top() + 1)

        if selected:
            color = self.get_state_color(option, index, common.SELECTION)
        else:
            color = self.get_state_color(option, index, common.SEPARATOR)

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        painter.restore()

    def paint_active_indicator(self, *args):
        """Paints the leading rectangle to indicate item is set as current."""
        painter, option, index, _, _, active, _, _ = args

        if not active:
            return

        painter.save()

        rect = QtCore.QRect(option.rect)
        rect.setTop(rect.top() + 1)

        color = self.get_state_color(option, index, common.SELECTION)

        rect.setWidth(common.INDICATOR_WIDTH)
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(rect)

        rect.moveRight(option.rect.right())
        painter.drawRect(rect)

        painter.restore()

    def paint_thumbnail_shadow(self, *args):
        """Paints a drop-shadow"""
        painter, option, _, _, _, _, _, _ = args

        painter.save()

        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            rect.left() +
            common.INDICATOR_WIDTH +
            option.rect.height()
        )
        rect.setWidth(option.rect.height())

        gradient = QtGui.QLinearGradient(
            rect.topLeft(), rect.topRight())
        gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 50))
        gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRect(rect)

        gradient = QtGui.QLinearGradient(
            rect.topLeft(), rect.topRight())
        gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 50))
        gradient.setColorAt(0.3, QtGui.QColor(0, 0, 0, 0))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRect(rect)

        painter.restore()

    def paint_thumbnail(self, *args):
        """Paints the thumbnail of the item."""
        painter, option, index, selected, _, _, _, _ = args

        painter.save()

        rect = QtCore.QRect(option.rect)
        rect.setLeft(rect.left() + common.INDICATOR_WIDTH)
        rect.setWidth(rect.height())

        # Background rectangle
        if selected:
            color = common.THUMBNAIL_BACKGROUND_SELECTED
        else:
            color = common.THUMBNAIL_BACKGROUND

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        settings = AssetSettings(
            '/'.join(index.data(common.ParentRole)),
            index.data(common.PathRole)
        )
        # Caching image
        common.cache_image(settings.thumbnail_path(), option.rect.height())

        # Painting background rectangle when the image exists
        if QtCore.QFileInfo(settings.thumbnail_path()).exists():
            bg_rect = QtCore.QRect(option.rect)
            bg_rect.setLeft(bg_rect.left() + common.INDICATOR_WIDTH)
            bg_rect.setWidth(bg_rect.height())
            bg_color = common.IMAGE_CACHE['{path}:BackgroundColor'.format(
                path=settings.thumbnail_path(),
            )]
            painter.setBrush(QtGui.QBrush(bg_color))
            painter.drawRect(bg_rect)

        # Getting the thumbnail from the cache
        k = '{path}:{height}'.format(
            path=settings.thumbnail_path(),
            height=option.rect.height()
        )
        image = common.IMAGE_CACHE[k]

        # Resizing the rectangle to accommodate the image's aspect ration
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

    def paint_data(self, *args):
        """Generic paint method to draw the name of an item."""
        painter, option, index, selected, _, _, _, _ = args
        painter.save()

        if selected:
            color = QtGui.QColor(common.TEXT_SELECTED)
        elif not selected:
            color = QtGui.QColor(common.TEXT)

        rect, metrics, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)

        text = metrics.elidedText(
            index.data(QtCore.Qt.DisplayRole),
            QtCore.Qt.ElideMiddle,
            rect.width()
        )

        painter.setPen(QtGui.QPen(color))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )

        painter.restore()

    def paint_filter_indicator(self, *args):
        """Paints the leading color-bar if a filter is active."""
        painter, option, _, _, _, _, _, _ = args

        painter.save()

        _filter = self.parent().current_filter
        if _filter == '/':
            return

        rect = QtCore.QRect(option.rect)
        rect.setWidth(common.INDICATOR_WIDTH)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(common.get_label(_filter)))
        painter.drawRect(rect)

        painter.restore()

    def paint_archived(self, *args):
        """Paints a `disabled` overlay on top of items flagged as `archived`."""
        painter, option, _, _, _, _, archived, _ = args

        if not archived:
            return

        painter.save()

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50, 150)))
        painter.drawRect(option.rect)

        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 40))
        brush.setStyle(QtCore.Qt.BDiagPattern)
        painter.setBrush(brush)
        painter.drawRect(option.rect)

        painter.restore()

    def get_filename_rect(self, rect):
        """Returns the rectangle containing the name.

        Args:
            rect (QtCore.QRect): The QListWidgetItem's visual rectangle.

        Returns:            QtCore.QRect

        """
        painter = QtGui.QPainter()
        font = QtGui.QFont('Roboto Black')
        font.setBold(True)
        font.setItalic(False)
        font.setPointSize(7.0)
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(painter.font())
        editor_rect = QtCore.QRect(rect)

        offset = rect.height() + common.INDICATOR_WIDTH + common.MARGIN
        editor_rect.moveLeft(editor_rect.left() + offset)
        editor_rect.setWidth(editor_rect.width() - offset - common.MARGIN)
        editor_rect.setHeight(metrics.height())

        # Center rectangle
        editor_rect.moveTop(
            rect.top() +
            (rect.height() * 0.5) -
            (editor_rect.height() * 0.5)
        )
        return editor_rect, font, metrics

    def get_description_rect(self, rect):
        """Returns the rectangle, font and the font metrics used to draw the note text.

        Arguments:
            rect (QtCore.QRect):  The visual rectangle of the current row.

        Returns:
            tuple: A tuple of QtCore.QRect, QtGui.QFont, QtGui.QFontMetrics instances.

        """
        painter = QtGui.QPainter()
        font = QtGui.QFont(painter.font())
        font = QtGui.QFont('Roboto Medium')
        font.setBold(False)
        font.setPointSize(8.0)
        metrics = QtGui.QFontMetrics(font)
        rect = QtCore.QRect(rect)

        rect.setLeft(
            rect.left() +
            common.INDICATOR_WIDTH +
            rect.height() +
            (common.MARGIN * 1.5)
        )
        rect.setRight(rect.right() - (common.MARGIN))

        padding = 2.0

        # Centering rectangle vertically
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height() + (padding * 2))
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        return rect, font, metrics

    def get_thumbnail_rect(self, rect):
        """Returns the rectangle for the thumbnail editor."""
        rect = QtCore.QRect(rect)
        rect.moveLeft(common.INDICATOR_WIDTH)
        rect.setWidth(rect.height())
        return rect

    def get_location_editor_rect(self, rect):
        rect = QtCore.QRect(rect)
        rect.setLeft(rect.right() - rect.height())
        rect.setWidth(rect.height())
        return rect

    @staticmethod
    def get_inline_icon_rect(rect, size, idx):
        """Returns the rectangle needed to draw an in-line item icon.

        Args:
            rect (QRect): The original item rectangle.
            size (int): The size of the rectangle.
            idx (int): The id number of the rectangle.

        Returns:
            Tuple: The pixmap and the icon's background rectangle.

        """
        rect = QtCore.QRect(rect)

        # Vertical
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(size)
        rect.moveTop(rect.top() - (rect.height() / 2.0))
        # Horizontal
        rect.setLeft(rect.right() - size)
        rect.moveRight(rect.right() - common.MARGIN)

        offset = 4.0
        for _ in xrange(idx):
            rect.moveRight(
                rect.right() - common.INDICATOR_WIDTH - size - (offset * 2))

        # Background
        size = max(rect.width(), rect.height())
        bg_rect = QtCore.QRect(rect)
        bg_rect.setWidth(size)
        bg_rect.setHeight(size)
        bg_rect.setLeft(bg_rect.left() - offset)
        bg_rect.setTop(bg_rect.top() - offset)
        bg_rect.setRight(bg_rect.right() + offset)
        bg_rect.setBottom(bg_rect.bottom() + offset)

        return rect, bg_rect
    #
    # def paint_favourite_icon(self, *args):
    #     """Paints the icon for indicating the item is a favourite."""
    #     painter, option, _, _, _, _, _, favourite = args
    #     if option.rect.width() < 360.0:
    #         return
    #
    #     painter.save()
    #     painter.setRenderHints(
    #         QtGui.QPainter.TextAntialiasing |
    #         QtGui.QPainter.Antialiasing |
    #         QtGui.QPainter.SmoothPixmapTransform,
    #         on=True
    #     )
    #     rect, bg_rect = self.get_inline_icon_rect(
    #         option.rect, common.INLINE_ICON_SIZE, 0)
    #
    #     if favourite:
    #         color = QtGui.QColor(common.FAVOURITE)
    #     else:
    #         color = QtGui.QColor(common.SECONDARY_TEXT)
    #
    #     pixmap = common.get_rsc_pixmap(
    #         'favourite', color, common.INLINE_ICON_SIZE)
    #     painter.setPen(QtCore.Qt.NoPen)
    #
    #     if favourite:
    #         color = QtGui.QColor(common.SEPARATOR)
    #         color.setAlpha(60)
    #         painter.setBrush(QtGui.QBrush(color))
    #         painter.drawRoundedRect(bg_rect, 2.0, 2.0)
    #     painter.drawPixmap(rect, pixmap)
    #     painter.restore()

    def paint_folder_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, _, _ = args
        if option.rect.width() < 360.0:
            return
        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )

        rect, _ = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 2)
        color = QtGui.QColor(common.SECONDARY_TEXT)
        pixmap = common.get_rsc_pixmap(
            'folder', color, common.INLINE_ICON_SIZE)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPixmap(rect, pixmap)
        painter.restore()

    def paint_todo_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, index, _, _, _, _, _ = args
        if option.rect.width() < 360.0:
            return

        painter.save()
        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )

        rect, _ = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 3)

        # Background rectangle
        bg_rect = QtCore.QRect(rect)
        bg_rect.setTop(option.rect.top())
        bg_rect.setBottom(option.rect.bottom())
        bg_rect.moveLeft(bg_rect.left() - (common.MARGIN))
        painter.setPen(QtCore.Qt.NoPen)
        bg_rect.setRight(option.rect.right())
        color = QtGui.QColor(common.SEPARATOR)
        color.setAlpha(100)
        painter.setBrush(color)
        painter.drawRect(bg_rect)

        color = QtGui.QColor(common.TEXT)
        pixmap = common.get_rsc_pixmap('todo', color, common.INLINE_ICON_SIZE)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPixmap(rect, pixmap)

        if not index.data(common.TodoCountRole):
            return

        count_rect = QtCore.QRect(rect)
        count_rect.setWidth(8)
        count_rect.setHeight(8)

        count_rect.moveCenter(rect.bottomRight())
        font = QtGui.QFont('Roboto Black')
        font.setPointSizeF(8.0)
        painter.setFont(font)

        pen = QtGui.QPen(common.FAVOURITE)
        pen.setWidth(8.0)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(common.FAVOURITE))
        painter.drawRoundedRect(
            count_rect, count_rect.width() / 2.0, count_rect.height() / 2.0)

        painter.setPen(QtGui.QPen(common.TEXT))
        painter.drawText(
            count_rect,
            QtCore.Qt.AlignCenter,
            '{}'.format(index.data(common.TodoCountRole))
        )

        painter.restore()

    def paint_description(self, *args):
        """Paints the item description inside the ``AssetWidget``."""
        painter, option, index, _, _, _, _, _ = args
        painter.save()

        rect, font, metrics = self.get_text_area(
            option.rect, common.SECONDARY_FONT)

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        if not index.data(common.DescriptionRole) and not hover:
            return

        # Resizing the height and moving below the name
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0) +
                     metrics.lineSpacing())

        color = self.get_state_color(option, index, common.TEXT_NOTE)
        if not index.data(common.DescriptionRole):
            _, font, metrics = self.get_text_area(
                option.rect, common.TERCIARY_FONT)
            text = 'Double-click to add description...'
            color.setAlpha(100)
        elif index.data(common.DescriptionRole):
            text = index.data(common.DescriptionRole)

        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, 3)
            rect.setRight(icon_rect.left() - common.MARGIN)

        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            rect.width()
        )

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))
        painter.setFont(font)
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )

        painter.restore()

        return metrics.width(text)

    def sizeHint(self, option, index):
        """Custom size-hint. Sets the size of the files and asset widget items."""
        size = QtCore.QSize(
            self.parent().viewport().width(), common.ROW_HEIGHT)
        return size


class BookmarksWidgetDelegate(BaseDelegate):
    """The delegate used to paint the bookmark items."""

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""

        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        if index.row() == (self.parent().count() - 1):
            self.paint_add_button(*args)
            return

        self.paint_selection_indicator(*args)
        self.paint_thumbnail(*args)
        self.paint_separators(*args)
        self.paint_thumbnail_shadow(*args)

        self.paint_active_indicator(*args)
        self.paint_archived(*args)
        #
        self.paint_name(*args)
        self.paint_description(*args)
        self.paint_root(*args)
        #
        self.paint_focus(*args)

    def paint_add_button(self, *args):
        """Paints the special add button."""
        painter, option, _, _, _, _, _, _ = args

        painter.save()

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(common.SEPARATOR))
        painter.drawRect(option.rect)

        rect = QtCore.QRect(option.rect)
        rect.setWidth(rect.height())
        rect.moveLeft(rect.left() + common.INDICATOR_WIDTH)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter.setPen(QtCore.Qt.NoPen)

        if hover:
            pixmap = common.get_rsc_pixmap(
                'bookmark_add', common.TEXT, option.rect.height())
        else:
            pixmap = common.get_rsc_pixmap(
                'bookmark_add', common.SELECTION, option.rect.height())
        painter.drawPixmap(
            rect,
            pixmap,
            pixmap.rect()
        )

        painter.restore()

    def paint_thumbnail(self, *args):
        """Paints the thumbnail of the bookmark item."""
        painter, option, index, selected, _, active, _, _ = args
        painter.save()

        favourite = index.flags() & configparser.MarkedAsFavourite
        active = index.flags() & configparser.MarkedAsActive

        rect = QtCore.QRect(option.rect)
        # Making the aspect ratio of the image 16/9
        rect.setWidth(rect.height())
        rect.moveLeft(rect.left() + common.INDICATOR_WIDTH)

        color = common.BACKGROUND
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        if active:
            pixmap = common.get_rsc_pixmap(
                'bookmark', common.SELECTION, rect.height())
        else:
            if favourite:
                pixmap = common.get_rsc_pixmap(
                    'bookmark', common.FAVOURITE, rect.height())
            else:
                pixmap = common.get_rsc_pixmap(
                    'bookmark', common.SECONDARY_TEXT, rect.height())

        painter.drawPixmap(
            rect,
            pixmap,
            pixmap.rect()
        )

        painter.restore()

    def paint_name(self, *args):
        """Paints name of the ``BookmarkWidget``'s items."""
        painter, option, index, _, _, _, _, _ = args
        painter.save()

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)

        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        # Count
        if not index.data(common.FileDetailsRole):
            color = self.get_state_color(option, index, common.SECONDARY_TEXT)
        else:
            color = self.get_state_color(option, index, common.TEXT)

        text = index.data(QtCore.Qt.DisplayRole)
        text = metrics.elidedText(
            re.sub(r'[\W\d\_]+', ' ', text.upper()),
            QtCore.Qt.ElideLeft,
            rect.width()
        )

        painter.setFont(font)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )

        painter.restore()

    def _get_root_text(self, item, rect, metrics):
        """Gets the text for drawing the root."""
        root = item.data(common.ParentRole)[2]
        count = item.data(common.FileDetailsRole)

        text = re.sub(r'[_]+', ' ', root.upper())
        if count:
            if count == 1:
                text = '{}  |  {} asset'.format(text, count)
            else:
                text = '{}  |  {} assets'.format(text, count)
        return metrics.elidedText(
            text,
            QtCore.Qt.ElideLeft,
            rect.width()
        )

    def _get_longest_root_width(self, rect, metrics):
        # Finding the longest root string
        width = [0, ]
        for n in xrange(self.parent().count()):
            try:
                item = self.parent().item(n)
                if item.isHidden():
                    continue
                text = self._get_root_text(item, rect, metrics)
                width.append(metrics.width(text))
            except:
                break
        return max(width)

    def paint_root(self, *args):
        """Paints the ``Bookmark``'s root information."""
        painter, option, index, _, _, active, _, _ = args
        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )
        count = index.data(common.FileDetailsRole)

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)

        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        width = self._get_longest_root_width(rect, metrics)

        text = self._get_root_text(
            self.parent().itemFromIndex(index), rect, metrics)

        rect.setLeft(rect.left() + (rect.width() - metrics.width(text)))

        bg_rect = QtCore.QRect(option.rect)
        bg_rect.setWidth(rect.width() - (rect.width() - width) + common.MARGIN)
        bg_rect.moveRight(rect.right())
        bg_rect.setRight(option.rect.right())

        if option.rect.width() < 360.0:
            return

        painter.setPen(QtCore.Qt.NoPen)
        color = QtGui.QColor(common.SEPARATOR)
        if not active:
            color.setAlpha(230)
        else:
            color.setAlpha(30)
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(bg_rect)

        font = QtGui.QFont('Roboto Black')
        font.setPointSizeF(8.5)
        painter.setFont(font)

        if count:
            color = QtGui.QColor(common.FAVOURITE)
            color.setHsl(
                color.hue(),
                color.saturation() - 50,
                color.lightness() - 20
            )
        else:
            color = QtGui.QColor(common.SEPARATOR)
        pen = QtGui.QPen(color)
        pen.setWidth(4.0)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(color))

        painter.drawRoundedRect(rect, 2.0, 2.0)

        color.setRed(color.red() + 100)
        color.setGreen(color.green() + 100)
        color.setBlue(color.blue() + 100)
        painter.setPen(QtGui.QPen(color))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            text
        )
        painter.restore()
        return


class AssetWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_separators(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_shadow(*args)
        #
        self.paint_todo_icon(*args)
        self.paint_archived_icon(*args)
        self.paint_favourite_icon(*args)
        self.paint_folder_icon(*args)
        #
        self.paint_active_indicator(*args)
        #
        self.paint_name(*args)
        self.paint_description(*args)
        #
        self.paint_focus(*args)

    def paint_name(self, *args):
        """Paints the item names inside the ``AssetWidget``."""
        painter, option, index, _, _, active, _, _ = args
        painter.save()

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, 3)
            rect.setRight(icon_rect.left())

        # Asset name
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub('[^0-9a-zA-Z]+', ' ', text)
        text = re.sub('[_]{1,}', ' ', text)
        text = '{}*'.format(text) if active else text.strip()
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

        painter.restore()

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().viewport().width(), common.ASSET_ROW_HEIGHT)


class FilesWidgetDelegate(BaseDelegate):
    """QAbstractItemDelegate associated with ``FilesWidget``."""

    def paint(self, painter, option, index):
        """Defines how the ``FilesWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_separators(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_active_indicator(*args)
        #
        self.paint_folder_icon(*args)
        self.paint_favourite_icon(*args)
        self.paint_archived_icon(*args)
        #
        rect = self.paint_mode(*args)
        self.paint_name(rect, *args)
        self.paint_description(*args)
        #
        self.paint_focus(*args)

    def paint_description(self, *args):
        """Paints the item description inside the ``AssetWidget``."""
        painter, option, index, _, _, _, _, _ = args
        favourite = index.flags() & configparser.MarkedAsFavourite
        archived = index.flags() & configparser.MarkedAsArchived
        active = index.flags() & configparser.MarkedAsActive
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter.save()

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)

        font.setPointSizeF(8.0)
        metrics = QtGui.QFontMetrics(font)
        painter.setFont(font)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0) + metrics.lineSpacing() + metrics.descent())

        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, 2)
            rect.setRight(icon_rect.left() -
                          (common.INLINE_ICON_SIZE) - common.MARGIN)

        color = self.get_state_color(option, index, common.TEXT_NOTE)

        if not index.data(common.DescriptionRole) and hover:
            text = '{}  |  {}'.format(
                'Double-click to add description...',
                index.data(common.FileDetailsRole)
            )
            color.setAlpha(200)
        if not index.data(common.DescriptionRole) and not hover:
            text = '{}'.format(
            index.data(common.FileDetailsRole)
            )
        elif index.data(common.DescriptionRole):
            text = '{}  |  {}'.format(
                index.data(common.DescriptionRole),
                index.data(common.FileDetailsRole)
            )

        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, 3)
            rect.setRight(icon_rect.left())

        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            rect.width()
        )

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))
        painter.setFont(font)
        if option.rect.width() > 360.0:
            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
                text
            )
        else:
            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                text
            )

        painter.restore()

        return metrics.width(text)

    def paint_mode(self, *args):
        """Paints the mode and the subsequent subfolders."""
        painter, option, index, _, _, active, _, _ = args
        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)
        font.setPointSizeF(8)

        # Resizing the height and Centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        painter.setFont(font)
        modes = index.data(common.FileModeRole)

        if not modes[0]:
            rect.setWidth(0)
            return rect

        padding = 2.0
        rect.setWidth(0)

        if option.rect.width() < 440.0:
            return rect

        for n, mode in enumerate(modes):
            mode = mode.upper()

            if n == 0:
                bg_color = common.FAVOURITE
            else:
                bg_color = QtGui.QColor(80, 80, 80)

            pen = QtGui.QPen(bg_color)
            pen.setWidth(padding)
            painter.setPen(pen)
            painter.setBrush(QtGui.QBrush(bg_color))

            rect.setWidth(metrics.width(mode))
            painter.drawRoundedRect(rect, 2.0, 2.0)

            if n == 0:
                color = common.TEXT
            else:
                color = common.SECONDARY_TEXT

            painter.setPen(QtGui.QPen(color))
            painter.drawText(
                rect,
                QtCore.Qt.AlignCenter,
                mode
            )

            if n >= 1:
                break
            rect.moveLeft(rect.left() + metrics.width(mode) + padding + 2)

        return rect

    def paint_name(self, mode_rect, *args):
        """Paints the ``FilesWidget``'s `QListWidgetItem` names, sub-directories and
        file informations.

        """
        painter, option, index, _, _, active, _, _ = args

        favourite = index.flags() & configparser.MarkedAsFavourite
        archived = index.flags() & configparser.MarkedAsArchived
        active = index.flags() & configparser.MarkedAsActive

        painter.save()

        rect, font, metrics = self.get_text_area(
            option.rect, common.PRIMARY_FONT)

        font.setPointSizeF(8.0)
        metrics = QtGui.QFontMetrics(font)
        painter.setFont(font)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))
        rect.setLeft(mode_rect.right())

        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, 2)
            rect.setRight(icon_rect.left() -
                          (common.INLINE_ICON_SIZE) - common.MARGIN)

        # Asset name
        text = index.data(QtCore.Qt.DisplayRole)
        text = text.split('.')
        ext = text.pop(-1)
        text = '.'.join(text).upper()
        text = '{}.{}'.format(text, ext)

        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideMiddle,
            rect.width()
        )

        color = self.get_state_color(option, index, common.TEXT)
        if favourite or active:
            color = common.TEXT_SELECTED
        if archived:
            color = common.SECONDARY_TEXT

        painter.setFont(font)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))
        if option.rect.width() > 360.0:
            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
                text
            )
        else:
            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                text
            )

        # Bg rectangle
        rect.setLeft(rect.right())
        rect.setTop(option.rect.top())
        rect.setBottom(option.rect.bottom())
        rect.moveLeft(rect.left() + (common.MARGIN))
        painter.setPen(QtCore.Qt.NoPen)

        rect.setRight(option.rect.right())
        color = QtGui.QColor(common.SEPARATOR)
        color.setAlpha(100)

        painter.setBrush(color)
        painter.drawRect(rect)

        painter.restore()

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().viewport().width(), common.ROW_HEIGHT)
