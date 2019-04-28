# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201
"""Main modules defining the delegates used to represent the QListWidgetItems."""


import re
from functools import wraps
from PySide2 import QtWidgets, QtGui, QtCore

import gwbrowser.common as common
from gwbrowser.imagecache import ImageCache
from gwbrowser.settings import AssetSettings
from gwbrowser.settings import MarkedAsActive, MarkedAsArchived, MarkedAsFavourite


def paintmethod(func):
    """@Decorator to save the painter state."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        args[0].save()
        res = func(self, *args, **kwargs)
        args[0].restore()
        return res
    return func_wrapper


class BaseDelegate(QtWidgets.QAbstractItemDelegate):
    """Base delegate containing methods to draw our list items."""

    def __init__(self, parent=None):
        super(BaseDelegate, self).__init__(parent=parent)

    def _get_paint_args(self, painter, option, index):
        """Returns a list of boolean arguments used to paint items."""
        selected = option.state & QtWidgets.QStyle.State_Selected
        focused = option.state & QtWidgets.QStyle.State_HasFocus

        favourite = index.flags() & MarkedAsFavourite
        archived = index.flags() & MarkedAsArchived
        active = index.flags() & MarkedAsActive

        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        args = (painter, option, index, selected,
                focused, active, archived, favourite)
        return args

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
        archived = index.flags() & MarkedAsArchived
        color = QtGui.QColor(color)
        if selected:
            color.setRed(color.red() / 0.92)
            color.setGreen(color.green() / 0.92)
            # color.setBlue(color.blue() / 0.92)
            return color

        if archived:  # Disabled colour
            color.setRed(color.red() / 1.96)
            color.setGreen(color.green() / 1.96)
            color.setBlue(color.blue() / 1.96)

        return color

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
        center = rect.center()
        rect.setHeight(int(size))
        rect.moveCenter(center)
        # Horizontal
        rect.setLeft(rect.right() - size)
        rect.moveRight(rect.right() - common.MARGIN)

        for _ in xrange(idx):
            rect.moveRight(
                rect.right() - common.INDICATOR_WIDTH - size - (common.INDICATOR_WIDTH * 2))

        rect.setWidth(int(size))
        center = rect.center()

        # Background
        size = max(rect.width(), rect.height())
        bg_rect = QtCore.QRect(rect)
        # center = rect.center()
        bg_rect.setWidth(size + int(common.INDICATOR_WIDTH * 1.5))
        bg_rect.setHeight(size + int(common.INDICATOR_WIDTH * 1.5))
        bg_rect.moveCenter(center)
        return rect, bg_rect

    @paintmethod
    def paint_background(self, *args):
        """Paints the background."""
        painter, option, index, selected, _, active, _, _ = args

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.drawRect(option.rect)

        if selected:
            color = QtGui.QColor(common.BACKGROUND_SELECTED)
        else:
            color = QtGui.QColor(common.BACKGROUND)

        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - 2)
        rect.setWidth(rect.height())
        rect.moveCenter(center)
        rect.moveLeft(common.INDICATOR_WIDTH)

        thumbcolor = QtGui.QColor(color)
        thumbcolor.setHsl(
            color.hue(),
            color.saturation(),
            color.lightness() - 10
        )
        painter.setBrush(thumbcolor)
        painter.drawRect(rect)

        rect.setRight(option.rect.right())

        painter.setBrush(color)
        painter.drawRect(rect)

        if active:
            color = self.get_state_color(option, index, common.SELECTION)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)
            painter.setOpacity(0.5)
            painter.setBrush(common.FAVOURITE)
            painter.drawRect(rect)

    @paintmethod
    def paint_selection_indicator(self, *args):
        """Paints the leading rectangle indicating the selection."""
        painter, option, index, selected, active, _, _, _ = args

        rect = QtCore.QRect(option.rect)
        rect.setWidth(common.INDICATOR_WIDTH)
        rect.setTop(rect.top() + 1)
        rect.setBottom(rect.bottom() - 1)

        if selected:
            color = common.SELECTION
        else:
            color = common.SEPARATOR

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

    @paintmethod
    def paint_thumbnail(self, *args):
        """Paints the thumbnail of an item."""
        painter, option, index, selected, _, _, _, _ = args

        # Background rectangle
        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - 2)
        rect.setWidth(rect.height())
        rect.moveCenter(center)

        rect.moveLeft(common.INDICATOR_WIDTH)

        image = index.data(common.ThumbnailRole)
        color = index.data(common.ThumbnailBackgroundRole)
        color = color if color else QtGui.QColor(0,0,0,55)

        # Background
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        painter.drawRect(rect)

        # Resizing the rectangle to accommodate the image's aspect ratio
        longer = float(max(image.rect().width(), image.rect().height()))
        factor = float(rect.width() / float(longer))
        center = rect.center()
        if image.rect().width() < image.rect().height():
            rect.setWidth(int(image.rect().width() * factor))
        else:
            rect.setHeight(int(image.rect().height() * factor))
        rect.moveCenter(center)
        painter.drawImage(
            rect,
            image,
            image.rect()
        )

    @paintmethod
    def paint_thumbnail_shadow(self, *args):
        """Paints a drop-shadow"""
        painter, option, _, _, _, _, archived, _ = args
        if archived:
            return

        rect = QtCore.QRect(option.rect)
        center = rect.center()
        rect.setHeight(rect.height() - 2)
        rect.setWidth(rect.height() * 2)
        rect.moveCenter(center)
        rect.moveLeft(common.INDICATOR_WIDTH + rect.height())

         # name, color, size, opacity=1.0
        pixmap = ImageCache.get_rsc_pixmap(u'gradient', None, rect.height())
        painter.drawPixmap(rect, pixmap, pixmap.rect())


    @paintmethod
    def paint_data(self, *args):
        """Generic paint method to draw the name of an item."""
        painter, option, index, selected, _, _, _, _ = args

        if selected:
            color = QtGui.QColor(common.TEXT_SELECTED)
        elif not selected:
            color = QtGui.QColor(common.TEXT)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH +
            rect.height() +
            common.MARGIN
        )
        rect.setRight(rect.right() - common.MARGIN)

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        text = metrics.elidedText(
            index.data(QtCore.Qt.DisplayRole),
            QtCore.Qt.ElideMiddle,
            rect.width()
        )

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        path = QtGui.QPainterPath()
        path.addText(rect.left(), rect.center().y() +
                     (metrics.ascent() / 2.0), font, text)
        painter.drawPath(path)

    @paintmethod
    def paint_archived(self, *args):
        """Paints a `disabled` overlay on top of items flagged as `archived`."""
        painter, option, index, _, _, _, archived, _ = args
        if not archived:
            return

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50, 150)))
        painter.drawRect(option.rect)

        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 40))
        brush.setStyle(QtCore.Qt.BDiagPattern)
        painter.setBrush(brush)
        painter.drawRect(option.rect)

    @paintmethod
    def paint_archived_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, archived, _ = args

        if option.rect.width() < 360.0:
            return
        if not self.parent().inline_icons_count():
            return

        rect, bg_rect = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 1)

        pos = QtGui.QCursor().pos()
        pos = self.parent().mapFromGlobal(pos)

        # Icon
        sep = QtGui.QColor(common.SEPARATOR)
        sep.setAlpha(150)
        color = common.FAVOURITE if archived else sep
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(color))

        if archived:
            pixmap = ImageCache.get_rsc_pixmap(
                u'archived', color, common.INLINE_ICON_SIZE)
            painter.setBrush(sep)
            painter.drawRoundedRect(
                bg_rect, bg_rect.width() / 2.0, bg_rect.width() / 2.0)
        else:
            pixmap = ImageCache.get_rsc_pixmap(
                u'active', color, common.INLINE_ICON_SIZE)

        # Icon
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def paint_folder_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, _, _ = args

        if option.rect.width() < 360.0:
            return
        if not self.parent().inline_icons_count():
            return

        rect, _ = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 2)

        sep = QtGui.QColor(common.SEPARATOR)
        sep.setAlpha(150)

        pixmap = ImageCache.get_rsc_pixmap(
            u'folder', sep, common.INLINE_ICON_SIZE)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def paint_todo_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""

        painter, option, index, _, _, _, _, _ = args

        if option.rect.width() < 360.0:
            return
        if not self.parent().inline_icons_count():
            return

        rect, _ = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 3)
        sep = QtGui.QColor(common.SEPARATOR)
        sep.setAlpha(150)
        pixmap = ImageCache.get_rsc_pixmap(
            u'todo', sep, common.INLINE_ICON_SIZE)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPixmap(rect, pixmap)

        if not index.data(common.TodoCountRole):
            return

        count_rect = QtCore.QRect(rect)
        count_rect.setWidth(8)
        count_rect.setHeight(8)

        count_rect.moveCenter(rect.bottomRight())
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(common.SMALL_FONT_SIZE)
        painter.setFont(font)

        pen = QtGui.QPen(common.FAVOURITE)
        pen.setWidth(8.0)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(common.FAVOURITE))
        painter.drawRoundedRect(
            count_rect, count_rect.width() / 2.0, count_rect.height() / 2.0)

        text = u'{}'.format(index.data(common.TodoCountRole))
        common.draw_aliased_text(
            painter, font, count_rect, text, QtCore.Qt.AlignCenter, common.TEXT)

    @paintmethod
    def paint_favourite_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, _, favourite = args

        if option.rect.width() < 360.0:
            return
        if not self.parent().inline_icons_count():
            return

        rect, bg_rect = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 0)

        # Icon
        if favourite:
            color = QtGui.QColor(common.FAVOURITE)
        else:
            color = QtGui.QColor(common.SEPARATOR)
            color.setAlpha(150)

        pos = QtGui.QCursor().pos()
        pos = self.parent().mapFromGlobal(pos)

        pixmap = ImageCache.get_rsc_pixmap(
            u'favourite', color, common.INLINE_ICON_SIZE)

        painter.setPen(QtCore.Qt.NoPen)

        if favourite:
            # sep = QtGui.QColor(common.SEPARATOR)
            # sep.setAlpha(150)
            # painter.setBrush(sep)
            # painter.drawRoundedRect(
            #     bg_rect, bg_rect.width() / 2, bg_rect.width() / 2)

            rect2 = QtCore.QRect(option.rect)
            rect2.setTop(rect2.top() + 1)
            rect2.setBottom(rect2.bottom() - 1)
            rect2.setWidth(common.INDICATOR_WIDTH)
            rect2.moveRight(option.rect.right())

            painter.setBrush(common.FAVOURITE)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(rect2)

        # Icon
        painter.drawPixmap(rect, pixmap)

    @paintmethod
    def paint_inline_icons_background(self, *args):
        painter, option, index, selected, _, active, archived, _ = args
        if option.rect.width() < 360.0:
            return

        if not self.parent().inline_icons_count():
            return

        rect, _ = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, self.parent().inline_icons_count() - 1)

        # Background rectangle
        bg_rect = QtCore.QRect(option.rect)
        bg_rect.setLeft(rect.left() - common.MARGIN)
        center = bg_rect.center()
        bg_rect.setHeight(bg_rect.height() - 2)
        bg_rect.moveCenter(center)

        painter.setPen(QtCore.Qt.NoPen)

        if not archived:
            if selected:
                color = QtGui.QColor(common.BACKGROUND_SELECTED)
            else:
                color = QtGui.QColor(common.BACKGROUND)


            painter.setBrush(color)
            painter.drawRect(bg_rect)

        if active:
            color = self.get_state_color(option, index, common.SELECTION)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)

            painter.setOpacity(0.5)
            painter.setBrush(common.FAVOURITE)
            painter.drawRect(bg_rect)
            painter.setOpacity(1)

        painter.setPen(QtCore.Qt.NoPen)
        if selected:
            painter.setBrush(common.SECONDARY_TEXT)
        else:
            painter.setBrush(common.SECONDARY_BACKGROUND)
        for n in xrange(self.parent().inline_icons_count()):
            rect, bg_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, n)
            painter.setOpacity(0.3)
            painter.drawRoundedRect(
                bg_rect, bg_rect.height() / 2, bg_rect.height() / 2)

    @paintmethod
    def paint_description(self, *args):
        """Paints the item description inside the ``AssetsWidget``."""
        painter, option, index, _, _, _, _, _ = args

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        if not index.data(common.DescriptionRole) and not hover:
            return

        # Resizing the height and moving below the name
        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH +
            rect.height() +
            common.MARGIN
        )
        rect.setRight(rect.right() - common.MARGIN)

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(common.MEDIUM_FONT_SIZE - 0.5)
        metrics = QtGui.QFontMetrics(font)

        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0) +
                     metrics.lineSpacing())

        color = self.get_state_color(option, index, common.SECONDARY_TEXT)

        if not index.data(common.DescriptionRole):
            text = u'Double-click to add description...'
            color.setAlpha(100)
        elif index.data(common.DescriptionRole):
            text = index.data(common.DescriptionRole)

        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, self.parent().inline_icons_count() - 1)
            if self.parent().inline_icons_count():
                rect.setRight(icon_rect.left() - common.MARGIN)
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)
        return metrics.width(text)

    def sizeHint(self, option, index):
        """Custom size-hint. Sets the size of the files and asset widget items."""
        size = QtCore.QSize(
            self.parent().viewport().width(), common.ROW_HEIGHT)
        return size


class BookmarksWidgetDelegate(BaseDelegate):
    """The delegate used to paint the bookmark items."""

    def paint(self, painter, option, index):
        """Defines how the ``BookmarksWidgetItems`` should be painted."""
        args = self._get_paint_args(painter, option, index)
        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_thumbnail_shadow(*args)
        #
        self.paint_name(*args)
        #
        self.paint_inline_icons_background(*args)
        self.paint_todo_icon(*args)
        self.paint_folder_icon(*args)
        self.paint_archived_icon(*args)
        self.paint_favourite_icon(*args)
        self.paint_count_icon(*args)
        #
        self.paint_selection_indicator(*args)

    @paintmethod
    def paint_name(self, *args):
        """Paints name of the ``BookmarkWidget``'s items."""
        painter, option, index, selected, _, _, _, _ = args

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH +
            rect.height() +
            common.MARGIN - 2
        )
        rect.setRight(rect.right() - common.MARGIN)

        # Centering rect
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[\W\d\_]+', '', text)
        text = u'  {}  |  {}  '.format(
            text, index.data(common.ParentRole)[-1].upper())
        width = metrics.width(text)
        rect.setWidth(width)

        offset = common.INDICATOR_WIDTH
        center = rect.center()
        rect.setHeight(common.INLINE_ICON_SIZE)
        rect.moveCenter(center)

        # Name background
        pen = QtGui.QPen(common.FAVOURITE)
        painter.setBrush(QtGui.QBrush(common.FAVOURITE))

        pen.setWidth(offset)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 2, 2)
        _text = text.split(u'/')
        text_ = _text.pop()
        _text = '/'.join(_text)

        if _text:
            t1, t2 = _text.split(u'|')
        else:
            t1, t2 = text_.split(u'|')

        color = common.TEXT_SELECTED if selected else common.TEXT
        width = common.draw_aliased_text(
            painter, font, rect, t1, QtCore.Qt.AlignLeft, color)
        rect.setLeft(rect.left() + width)


        width = common.draw_aliased_text(
            painter, font, rect, u'|', QtCore.Qt.AlignLeft, common.SECONDARY_BACKGROUND)
        rect.setLeft(rect.left() + width)
        width = common.draw_aliased_text(
            painter, font, rect, t2, QtCore.Qt.AlignLeft, color)
        rect.setLeft(rect.left() + width)

        if _text:
            width = common.draw_aliased_text(
                painter, font, rect, u'/', QtCore.Qt.AlignLeft, common.SECONDARY_BACKGROUND)
            rect.setLeft(rect.left() + width)

            text_ = '{}'.format(text_)

            width = common.draw_aliased_text(
                painter, font, rect, text_, QtCore.Qt.AlignLeft, color)


        rect.moveLeft(rect.right() + common.MARGIN)

        # Paint description
        text = index.data(common.DescriptionRole)
        if not text:
            return

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(common.MEDIUM_FONT_SIZE - 0.5)

        if option.rect.width() < 360.0:
            rect.setRight(option.rect.right() - common.MARGIN)
        else:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, self.parent().inline_icons_count() - 1)
            if self.parent().inline_icons_count():
                rect.setRight(icon_rect.left() - common.MARGIN)
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, color)

    @paintmethod
    def paint_count_icon(self, *args):
        """Paints name of the ``BookmarkWidget``'s items."""
        painter, option, index, selected, _, _, _, _ = args
        # Count
        if option.rect.width() < 360.0:
            return

        count = index.data(common.AssetCountRole)

        rect, bg_rect = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, self.parent().inline_icons_count() - 1)

        w = float(bg_rect.width() - 4)
        bg_rect.setHeight(w)
        bg_rect.setWidth(w)
        bg_rect.moveCenter(rect.center())

        color = QtGui.QColor(common.TEXT_SELECTED) if selected else QtGui.QColor(common.FAVOURITE)
        color.setAlpha(175)

        if count:
            pen = QtGui.QPen(color)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(
                bg_rect, float(bg_rect.height() / 2.0), float(bg_rect.height() / 2.0))

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(common.SMALL_FONT_SIZE)

        text = u'{}'.format(count)
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignCenter, common.TEXT if count else common.TEXT_DISABLED)

    def sizeHint(self, option, index):
        """Custom size-hint. Sets the size of the files and asset widget items."""
        size = QtCore.QSize(
            self.parent().viewport().width(), common.BOOKMARK_ROW_HEIGHT)
        return size


class AssetsWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetsWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetsWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        #
        self.paint_thumbnail(*args)
        self.paint_archived(*args)
        self.paint_thumbnail_shadow(*args)
        #
        self.paint_name(*args)
        self.paint_description(*args)
        #
        self.paint_inline_icons_background(*args)
        self.paint_todo_icon(*args)
        self.paint_archived_icon(*args)
        self.paint_favourite_icon(*args)
        self.paint_folder_icon(*args)
        #
        self.paint_selection_indicator(*args)

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``AssetsWidget``."""
        painter, option, index, _, _, active, archived, _ = args

        font = QtGui.QFont(common.PrimaryFont)
        metrics = QtGui.QFontMetrics(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH +
            rect.height() +
            common.MARGIN
        )
        rect.setRight(rect.right() - common.MARGIN)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect, common.INLINE_ICON_SIZE, self.parent().inline_icons_count() - 1)
            if self.parent().inline_icons_count():
                rect.setRight(icon_rect.left())

        # Asset name
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub(r'[^0-9a-zA-Z]+', ' ', text)
        text = re.sub(r'[_]{1,}', '_', text).strip('_')
        text = metrics.elidedText(
            text.upper(),
            QtCore.Qt.ElideRight,
            rect.width()
        )
        color = self.get_state_color(
            option, index, common.SECONDARY_TEXT if archived else common.TEXT)
        common.draw_aliased_text(
            painter, font, rect, text, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, color)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().viewport().width(), common.ASSET_ROW_HEIGHT)


class FilesWidgetDelegate(BaseDelegate):
    """QAbstractItemDelegate associated with ``FilesWidget``."""

    def paint(self, painter, option, index):
        """Defines how the ``FilesWidget``'s' items should be painted."""
        if index.data(QtCore.Qt.DisplayRole) is None:
            return

        args = self._get_paint_args(painter, option, index)
        #
        self.paint_background(*args)

        #
        self.paint_thumbnail(*args)
        if index.data(common.StatusRole):
            self.paint_archived(*args)
        self.paint_thumbnail_shadow(*args)
        #
        left = self.paint_mode(*args)
        self.paint_name(*args, left=left)
        if index.data(common.StatusRole):
            self.paint_description(*args, left=left)
        #
        self.paint_inline_icons_background(*args)
        self.paint_folder_icon(*args)
        self.paint_favourite_icon(*args)
        self.paint_archived_icon(*args)
        #
        self.paint_selection_indicator(*args)

    def _draw(self, painter, font, rect, text, align, color, option, left):
        """Draws a sequence element."""
        metrics = QtGui.QFontMetrics(font)
        width = metrics.width(text)
        rect.setLeft(rect.right() - width)

        if rect.left() < (left + common.MARGIN):
            rect.setLeft(left + common.MARGIN)
            if option.rect.width() < 360.0:
                rect.setLeft(rect.left() - common.MARGIN)
        common.draw_aliased_text(painter, font, rect, text, align, color)

        rect.moveRight(rect.right() - width)
        return rect

    @paintmethod
    def paint_description(self, *args, **kwargs):
        """Paints the item description inside the ``FilesWidget``."""
        painter, option, index, selected, _, _, _, _ = args

        hover = option.state & QtWidgets.QStyle.State_MouseOver

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(common.SMALL_FONT_SIZE - 0.5)
        metrics = QtGui.QFontMetrics(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH +
            rect.height() +
            (common.MARGIN / 2.0)
        )
        rect.setRight(rect.right() - common.MARGIN)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.bottom() - rect.height() + (rect.height() / 3))

        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect,
                common.INLINE_ICON_SIZE, self.parent().inline_icons_count() - 1)
            if self.parent().inline_icons_count():
                rect.setRight(icon_rect.left() - common.MARGIN)
            rect.setRight(rect.right())

        align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight
        text = index.data(common.FileDetailsRole)

        rect = self._draw(painter, font, rect, text, align,
                          common.SECONDARY_TEXT, option, kwargs['left'])

        if option.rect.width() < 360.0:
            return

        if index.data(common.DescriptionRole):
            if selected:
                color = common.TEXT_SELECTED
            else:
                color = common.FAVOURITE
            text = u'{}  |  \n'.format(index.data(common.DescriptionRole))
            rect = self._draw(painter, font, rect, text, align,
                              color, option, kwargs['left'])
        elif not index.data(common.DescriptionRole) and hover:
            color = QtGui.QColor(common.SECONDARY_TEXT)
            color.setAlpha(150)
            text = u'Double-click to add description...  |  '
            rect = self._draw(painter, font, rect, text,
                              align, color, option, kwargs['left'])
        return metrics.width(text)

    @paintmethod
    def paint_mode(self, *args):
        """Paints the FilesWidget's mode and the subfolders."""
        painter, option, index, selected, _, _, _, _ = args
        if index.data(common.ParentRole) is None:
            return

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(common.SMALL_FONT_SIZE)
        metrics = QtGui.QFontMetrics(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH +
            rect.height() +
            (common.MARGIN / 2.0)
        )
        rect.setRight(rect.right() - common.MARGIN)

        # Resizing the height and Centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height() + common.INDICATOR_WIDTH)
        rect.moveTop(rect.top() - (rect.height() / 2.0))

        modes = index.data(common.ParentRole)[-1]
        modes = modes.split(u'/')
        rect.setWidth(0)

        if not modes[0]:
            return rect.right()
        if option.rect.width() < 360.0:
            return rect.right()

        max_depth = 4
        padding = common.INDICATOR_WIDTH
        for n, text in enumerate(modes):
            if n > max_depth:  # Not painting folders deeper than this...
                return rect.right() - common.MARGIN

            if n == max_depth:
                text = u'...'
            else:
                text = u'{}'.format(text.upper())

            if n == 0:
                bg_color = common.FAVOURITE
            else:
                bg_color = QtGui.QColor(85, 85, 85)

            pen = QtGui.QPen(bg_color)
            pen.setWidth(common.INDICATOR_WIDTH)
            painter.setPen(pen)
            painter.setBrush(QtGui.QBrush(bg_color))

            rect.setWidth(metrics.width(text) + (common.INDICATOR_WIDTH * 2))
            # rect.moveLeft(rect.left() + (common.INDICATOR_WIDTH * 3))
            painter.drawRoundedRect(rect, 3.0, 3.0)

            if n == 0:
                color = QtGui.QColor(common.TEXT)
                color = common.TEXT_SELECTED if selected else color
            elif n == max_depth:
                color = QtGui.QColor(common.TEXT_DISABLED)
            else:
                color = QtGui.QColor(common.SECONDARY_TEXT)
                color = common.TEXT if selected else color

            common.draw_aliased_text(
                painter, font, rect, text, QtCore.Qt.AlignCenter, color)

            if len(modes) - 1 == n:
                return rect.right()
            rect.moveLeft(rect.right() + (common.INDICATOR_WIDTH * 2))

    @paintmethod
    def paint_name(self, *args, **kwargs):
        """Paints the ``FilesWidget``'s name."""
        painter, option, index, selected, _, active, _, _ = args
        if not index.data(QtCore.Qt.DisplayRole):
            return

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(common.MEDIUM_FONT_SIZE - 0.5)
        metrics = QtGui.QFontMetrics(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(
            common.INDICATOR_WIDTH +
            rect.height() +
            common.MARGIN
        )
        rect.setRight(rect.right() - common.MARGIN)

        # Resizing the height and centering
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - rect.height() + (rect.height() / 3))

        # Taking the control-icons into consideration
        if option.rect.width() >= 360.0:
            _, icon_rect = self.get_inline_icon_rect(
                option.rect,
                common.INLINE_ICON_SIZE, self.parent().inline_icons_count() - 1)
            if self.parent().inline_icons_count():
                rect.setRight(icon_rect.left() - common.MARGIN)
        align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight
        # Name
        text = index.data(QtCore.Qt.DisplayRole)
        # Removing the 'v' from 'v010' style version strings.
        text = re.sub(r'(.*)(v)([\[0-9\-\]]+.*)',
                      r'\1\3', text, flags=re.IGNORECASE)

        match = common.is_collapsed(text)
        if match:  # sequence collapsed
            text = match.group(3).split(u'.')
            text = u'{suffix}.{ext}'.format(
                ext=text.pop().lower(),
                suffix=u'.'.join(text).upper()
            )

            # The extension and the suffix
            color = common.TEXT_SELECTED if selected else common.TEXT
            rect = self._draw(painter, font, rect, text, align,
                              color, option, kwargs['left'])

            # The frame-range - this can get quite long - we're trimming it to
            # avoid long and meaningless names
            frange = match.group(2).upper()
            if len(frange) > 17:
                frange = '{}...{}'.format(frange[0:8], frange[-8:])
            color = common.TEXT_SELECTED if selected else common.FAVOURITE
            color = common.TEXT_SELECTED if active else color
            rect = self._draw(painter, font, rect, frange, align, color, option, kwargs['left'])

            # The prefix
            color = common.TEXT_SELECTED if selected else common.TEXT
            rect = self._draw(painter, font, rect, match.group(
                1).upper(), align, color, option, kwargs['left'])
            return

        match = common.get_sequence(text)
        if match:
            # The extension and the suffix
            if match.group(4):
                text = u'{}.{}'.format(
                    match.group(3).upper(), match.group(4).lower())
            else:
                text = u'{}'.format(
                    match.group(3).upper())

            color = common.TEXT_SELECTED if selected else common.TEXT
            rect = self._draw(
                painter, font, rect, text, align, color, option, kwargs['left'])
            # The frame-range
            color = common.TEXT_SELECTED if selected else common.FAVOURITE
            color = common.TEXT_SELECTED if active else color
            rect = self._draw(
                painter, font, rect, match.group(2).upper(), align, color, option, kwargs['left'])

            # The prefix
            color = common.TEXT_SELECTED if selected else common.TEXT
            rect = self._draw(
                painter, font, rect, match.group(1).upper(),
                align, color, option, kwargs['left'])
            return

        text = text.split(u'.')
        if len(text) > 1:
            text = u'{suffix}.{ext}'.format(
                ext=text.pop().lower(),
                suffix=u'.'.join(text).upper())
        else:
            text = text[0].upper()

        color = common.TEXT_SELECTED if selected else common.TEXT
        self._draw(painter, font, rect, text, align,
                   color, option, kwargs['left'])

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().viewport().width(), common.ROW_HEIGHT)


class FavouritesWidgetDelegate(FilesWidgetDelegate):

    def paint(self, painter, option, index):
        """Defines how the ``FilesWidget``'s' items should be painted."""
        if index.data(QtCore.Qt.DisplayRole) is None:
            return

        args = self._get_paint_args(painter, option, index)
        #
        self.paint_background(*args)

        #
        self.paint_thumbnail(*args)
        if index.data(common.StatusRole):
            self.paint_archived(*args)
        self.paint_thumbnail_shadow(*args)
        #
        left = self.paint_mode(*args)
        self.paint_name(*args, left=left)
        if index.data(common.StatusRole):
            self.paint_description(*args, left=left)
        #
        self.paint_inline_icons_background(*args)
        self.paint_folder_icon(*args)
        #
        self.paint_selection_indicator(*args)

    @paintmethod
    def paint_folder_icon(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, _, _ = args

        if option.rect.width() < 360.0:
            return
        if not self.parent().inline_icons_count():
            return

        rect, _ = self.get_inline_icon_rect(
            option.rect, common.INLINE_ICON_SIZE, 0)

        sep = QtGui.QColor(common.SEPARATOR)
        sep.setAlpha(150)

        pixmap = ImageCache.get_rsc_pixmap(
            u'folder', sep, common.INLINE_ICON_SIZE)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPixmap(rect, pixmap)
