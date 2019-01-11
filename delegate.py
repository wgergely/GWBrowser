# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201


"""This module defines the delegates used to paint the ListWidgetItems and the
associated data.

"""


import re
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.common import cmds
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.configparsers import AssetSettings


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
            font.setPointSizeF(9.5)
            font.setBold(False)
            font.setItalic(False)
        # Secondary fonts are used to draw description and file information
        elif emphasis is common.SECONDARY_FONT:
            font = QtGui.QFont('Roboto Medium')
            font.setPointSizeF(9.0)
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

    def paint_favourite(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, _, favourite = args
        if option.rect.width() < 250.0:
            return

        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )

        rect, bg_rect = self.get_inline_icon_rect(option.rect, common.INLINE_ICON_SIZE, 0)

        # Icon
        if favourite:
            color = QtGui.QColor(common.FAVOURITE)
        else:
            color = QtGui.QColor(common.SECONDARY_TEXT)

        pos = QtGui.QCursor().pos()
        pos = self.parent().mapFromGlobal(pos)

        pixmap = common.get_rsc_pixmap('favourite', color, common.INLINE_ICON_SIZE)


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

        settings = AssetSettings(index.data(QtCore.Qt.PathRole).filePath())

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
        brush = QtGui.QBrush(common.ARCHIVED_OVERLAY)
        painter.setBrush(brush)
        painter.drawRect(option.rect)

        gradient = QtGui.QLinearGradient(
            option.rect.topLeft(), option.rect.topRight())
        gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        gradient.setColorAt(0.5, QtGui.QColor(50, 50, 50, 200))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRect(option.rect)

        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 40))
        brush.setStyle(QtCore.Qt.BDiagPattern)
        painter.setBrush(brush)
        painter.drawRect(option.rect)

        painter.restore()
    #
    # def get_name_rect(self, rect):
    #     """Returns the rectangle containing the name.
    #
    #     Args:
    #         rect (QtCore.QRect): The QListWidgetItem's visual rectangle.
    #
    #     Returns:            QtCore.QRect
    #
    #     """
    #     painter = QtGui.QPainter()
    #     font = QtGui.QFont('Roboto Black')
    #     font.setBold(False)
    #     font.setPointSize(9.0)
    #     painter.setFont(font)
    #     metrics = QtGui.QFontMetrics(painter.font())
    #     editor_rect = QtCore.QRect(rect)
    #
    #     editor_rect.setLeft(
    #         editor_rect.left() + common.INDICATOR_WIDTH +
    #         rect.height() + (common.MARGIN * 1.5)
    #     )
    #
    #     editor_rect.setRight(editor_rect.right() - common.MARGIN)
    #     editor_rect.setHeight(metrics.height())
    #
    #     # Center rectangle
    #     editor_rect.moveTop(
    #         rect.top() +
    #         (rect.height() * 0.5) -
    #         (editor_rect.height() * 0.5)
    #     )
    #     return editor_rect, font, metrics

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

    # def createEditor(self, parent, option, index, editor=0):  # pylint: disable=W0613
    #     """Creates the custom editors needed to edit the thumbnail and the description.
    #
    #     References:
    #     http: // doc.qt.io/qt-5/QItemEditorFactory.html  # standard-editing-widgets
    #
    #     """
    #     if not editor:
    #         return
    #     elif editor == 1:  # Editor to edit notes
    #         rect, _, _ = self.get_description_rect(option.rect)
    #         return self.get_noteeditor_cls(index, rect, self.parent(), parent=parent)
    #     elif editor == 2:  # Editor to pick a thumbnail
    #         rect = self.get_thumbnail_rect(option.rect)
    #         return self.get_thumbnaileditor_cls(index, rect, self.parent(), parent=parent)
    #     elif editor == 3:  # Button to remove a location, no editor needed
    #         return

    def sizeHint(self, option, index):
        """Custom size-hint. Sets the size of the files and asset widget items."""
        size = QtCore.QSize(self.parent().viewport().width(), common.ROW_HEIGHT)
        return size


class BookmarksWidgetDelegate(BaseDelegate):
    """The delegate used to paint the bookmark items."""

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""

        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)

        if index.row() == (self.parent().count() - 1):
            self.paint_add_button(*args)
            self.paint_focus(*args)
            return

        self.paint_data(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail(*args)
        self.paint_separators(*args)
        self.paint_active_indicator(*args)
        self.paint_archived(*args)
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
            path = '{}/rsc/bookmark_add_hover.png'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )
        else:
            path = '{}/rsc/bookmark_add.png'.format(
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

    def paint_thumbnail(self, *args):
        """Paints the thumbnail of the bookmark item."""
        painter, option, _, selected, _, active, _, _ = args

        painter.save()

        if selected:
            color = common.THUMBNAIL_BACKGROUND_SELECTED
        else:
            color = common.BACKGROUND

        rect = QtCore.QRect(option.rect)
        # Making the aspect ratio of the image 16/9
        rect.setWidth(rect.height())
        rect.moveLeft(rect.left() + common.INDICATOR_WIDTH)

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        if active:
            path = '{}/rsc/bookmark_active.png'.format(
                QtCore.QFileInfo(__file__).dir().path()
            )
        else:
            path = '{}/rsc/bookmark.png'.format(
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

    def paint_data(self, *args):
        """Paints the bookmark's name, path."""
        painter, option, index, selected, _, _, _, _ = args

        painter.save()
        painter.setBrush(QtCore.Qt.NoBrush)

        font = QtGui.QFont('Roboto Medium')
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)

        server, job, root, count = index.data(QtCore.Qt.UserRole).split(',')
        count = int(count)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(option.rect.height() +
                     common.INDICATOR_WIDTH + common.MARGIN)
        rect.setRight(rect.right() - common.MARGIN)

        # Root
        font = QtGui.QFont('Roboto')
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(painter.font())
        text = re.sub(r'[_]+', ' ', root.upper())
        if count:
            text = '{} ({} items)'.format(text, count)
        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideLeft,
            rect.width()
        )
        width = metrics.width(text) + common.MARGIN

        # Text background
        # Sizing it to the text
        bg_rect = QtCore.QRect(rect)
        bg_rect.setLeft(bg_rect.right() - metrics.width(text))
        bg_rect.setHeight(metrics.height())
        bg_rect.moveTop(bg_rect.top() + (option.rect.height() /
                                         2.0) - (bg_rect.height() / 2.0))
        # Adding margin
        offset = 4.0
        bg_rect.setTop(bg_rect.top() - (offset / 2))
        bg_rect.setBottom(bg_rect.bottom() + (offset / 2))
        bg_rect.setLeft(bg_rect.left() - offset)
        bg_rect.setRight(bg_rect.right() + offset)

        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(bg_rect), 1.5, 1.5)

        if not count:
            painter.setPen(QtGui.QPen(common.TEXT_WARNING))

        color = common.get_label(root)
        if selected:
            selected_color = QtGui.QColor(color)
            selected_color.setRed(selected_color.red() + 20)
            selected_color.setGreen(selected_color.green() + 20)
            selected_color.setBlue(selected_color.blue() + 20)
            if count:
                painter.setPen(QtGui.QPen(common.TEXT_SELECTED))
                painter.fillPath(path, selected_color)
            else:
                txtColor = QtGui.QColor(common.TEXT_WARNING)
                txtColor.setRed(txtColor.red() + 20)
                txtColor.setGreen(txtColor.green() + 20)
                txtColor.setBlue(txtColor.blue() + 20)
                painter.setPen(QtGui.QPen(txtColor))
        else:
            if count:
                painter.setPen(QtGui.QPen(common.TEXT))
                painter.fillPath(path, color)
            else:
                color = QtGui.QColor(common.BACKGROUND)
                painter.setPen(QtGui.QPen(common.TEXT_WARNING))
                painter.fillPath(path, color)

        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
            text
        )

        metrics = QtGui.QFontMetrics(painter.font())
        text = metrics.elidedText(
            re.sub(r'[\W\d\_]+', ' ', job.upper()),
            QtCore.Qt.ElideRight,
            rect.width() - width
        )
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text + '\n'
        )

        # Path
        font = QtGui.QFont('Roboto')
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(painter.font())
        text = metrics.elidedText(
            '{}/{}/{}'.format(server, job, root),
            QtCore.Qt.ElideRight,
            rect.width() - width
        )
        painter.setPen(QtGui.QPen(common.SECONDARY_TEXT))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap,
            '\n' + text
        )

        painter.restore()

    def get_description_rect(self, *args):
        """There's no editable note on the Bookmarks widget, hence setting it to zero."""
        return QtCore.QRect(0, 0, 0, 0), None, None


class AssetWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetWidget`` to display the collecteds assets."""

    def paint(self, painter, option, index):
        """Defines how the ``AssetWidget``'s' items should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_favourite(*args)
        self.paint_name(*args)
        self.paint_description(*args)
        self.paint_selection_indicator(*args)
        self.paint_separators(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_active_indicator(*args)
        self.paint_archived(*args)
        self.paint_focus(*args)


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

        #Vertical
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(size)
        rect.moveTop(rect.top() - (rect.height() / 2.0))
        # Horizontal
        rect.setLeft(rect.right() - size)
        rect.moveRight(rect.right() - common.MARGIN)

        for _ in xrange(idx):
            rect.moveRight(rect.right() - common.INDICATOR_WIDTH - size)

        # Background
        size = max(rect.width(), rect.height())
        bg_rect = QtCore.QRect(rect)
        bg_rect.setWidth(size)
        bg_rect.setHeight(size)

        offset = 4.0
        bg_rect.setLeft(bg_rect.left() - offset)
        bg_rect.setTop(bg_rect.top() - offset)
        bg_rect.setRight(bg_rect.right() + offset)
        bg_rect.setBottom(bg_rect.bottom() + offset)

        return rect, bg_rect

    def paint_favourite(self, *args):
        """Paints the icon for indicating the item is a favourite."""
        painter, option, _, _, _, _, _, favourite = args
        if option.rect.width() < 250.0:
            return

        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )

        rect, bg_rect = self.get_inline_icon_rect(option.rect, common.INLINE_ICON_SIZE, 0)

        # Icon
        if favourite:
            color = QtGui.QColor(common.FAVOURITE)
        else:
            color = QtGui.QColor(common.SECONDARY_TEXT)

        pos = QtGui.QCursor().pos()
        pos = self.parent().mapFromGlobal(pos)

        pixmap = common.get_rsc_pixmap('favourite', color, common.INLINE_ICON_SIZE)


        painter.setPen(QtCore.Qt.NoPen)
        if favourite:
            color = QtGui.QColor(common.SEPARATOR)
            color.setAlpha(60)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRoundedRect(bg_rect, 2.0, 2.0)

        # Icon
        painter.drawPixmap(rect, pixmap)

        painter.restore()

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

    def paint_description(self, *args):
        """Paints the item description inside the ``AssetWidget``."""
        painter, option, index, _, _, _, _, _ = args
        painter.save()

        rect, font, metrics = self.get_text_area(
            option.rect, common.SECONDARY_FONT)

        hover = option.state & QtWidgets.QStyle.State_MouseOver
        if not index.data(QtCore.Qt.UserRole) and not hover:
            return

        # Resizing the height and moving below the name
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() - (rect.height() / 2.0) +
                     metrics.lineSpacing())

        color = self.get_state_color(option, index, common.TEXT_NOTE)
        if not index.data(QtCore.Qt.UserRole):
            _, font, metrics = self.get_text_area(
                option.rect, common.TERCIARY_FONT)
            text = 'Double-click to add description...'
            color.setAlpha(100)
        elif index.data(QtCore.Qt.UserRole):
            text = index.data(QtCore.Qt.UserRole)

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

    def sizeHint(self, option, index):
        return QtCore.QSize(self.parent().viewport().width(), common.ASSET_ROW_HEIGHT)


class FilesWidgetDelegate(BaseDelegate):
    """QAbstractItemDelegate associated with ``FilesWidget``."""

    def paint_active_indicator(self, *args):
        """Paints the yellow leading rectangle to indicate item is set as current."""
        painter, option, index, selected, _, _ = args

        maya_file_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))
        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))

        if maya_file_info.filePath() != file_info.filePath():
            return

        rect = QtCore.QRect(option.rect)
        rect.setWidth(common.INDICATOR_WIDTH)

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        if selected:
            color = common.FAVORUITE_SELECTED
        else:
            color = common.FAVORUITE
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

    def paint_data(self, *args):
        """Paints the ``FilesWidget``'s `QListWidgetItem` names, sub-directories and
        file informations.

        """
        painter, option, index, selected, _, _ = args
        if selected:
            color = common.TEXT_SELECTED
        elif not selected:
            color = common.TEXT

        file_info = QtCore.QFileInfo(index.data(QtCore.Qt.DisplayRole))
        rect, font, _ = self.get_filename_rect(option.rect)
        painter.setFont(font)
        rect.setTop(rect.top() - 3)

        metrics = QtGui.QFontMetrics(painter.font())

        filename = file_info.baseName().upper()
        filename = re.sub('[^0-9a-zA-Z]+', '_', filename)
        filename = re.sub('[_]{1,}', '_', filename)
        filename = filename.strip('_')
        filename = metrics.elidedText(
            filename,
            QtCore.Qt.ElideMiddle,
            rect.width()
        )

        # Geting the base directories
        basedirs = file_info.dir().path()
        basedirs = basedirs.replace(
            self.parent().collector.root_info.filePath(), ''
        ).replace(
            local_settings.asset_scenes_folder, ''
        ).lstrip('/').rstrip('/')

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(color))

        # Iterating the base directories
        basedir_rect = QtCore.QRect(rect)
        available_width = rect.width() - metrics.width(filename) - common.MARGIN
        basedir_total_width = 0

        for idx, basedir in enumerate(basedirs.split('/')):
            if not len(basedir):
                continue

            if idx == 0:
                basedir = basedir.upper()
            else:
                basedir = basedir.upper()

            basedir_rect.setWidth(metrics.width(basedir))
            basedir_rect.setLeft(basedir_rect.left() - 2)
            basedir_rect.setWidth(basedir_rect.width() +
                                  common.INDICATOR_WIDTH)
            basedir_total_width += metrics.width(basedir) + 6

            # Skip folders that are too long to draw
            if available_width < basedir_total_width:
                painter.drawText(
                    basedir_rect,
                    QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                    '...'
                )
                break

            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(basedir_rect), 1.5, 1.5)

            # First subdir
            if idx == 0:
                bgcolor = common.get_label(basedir)
                if selected:
                    bgcolor = QtGui.QColor(bgcolor)
                    bgcolor.setRed(bgcolor.red() + 20)
                    bgcolor.setGreen(bgcolor.green() + 20)
                    bgcolor.setBlue(bgcolor.blue() + 20)
                painter.fillPath(path, bgcolor)
            # Secondary subdirs
            else:
                bgcolor = common.SECONDARY_BACKGROUND
                if selected:
                    bgcolor = common.BACKGROUND_SELECTED
                painter.fillPath(path, bgcolor)

            # painter.drawPath(path)

            # Draw name
            if idx == 0:  # first subdir
                data_color = QtGui.QColor(common.get_label(basedir))
                data_color.setRed(data_color.red() + 80)
                data_color.setGreen(data_color.green() + 80)
                data_color.setBlue(data_color.blue() + 80)
            elif idx > 0:  # secondary subdirs
                data_color = QtGui.QColor(common.SECONDARY_TEXT)

            painter.setPen(QtGui.QPen(data_color))
            painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
            painter.drawText(
                basedir_rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignCenter,
                basedir
            )

            # Move rect
            basedir_rect.moveLeft(
                basedir_rect.left() +
                basedir_rect.width() +
                6 * 1
            )

        # Filename
        font = QtGui.QFont(painter.font())
        font.setBold(True)
        font.setItalic(False)
        font.setPointSize(8.0)
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(painter.font())

        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        painter.setPen(QtGui.QPen(color))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
            filename
        )

        rect.setHeight(metrics.height())
        rect.moveTop(
            option.rect.top() +
            (option.rect.height() * 0.5) -
            (rect.height() * 0.5) +
            metrics.height()
        )

        # File information
        font = QtGui.QFont(painter.font())
        font.setBold(False)
        # font.setItalic(True)
        font.setPointSize(7.0)
        painter.setFont(font)

        metrics = QtGui.QFontMetrics(painter.font())

        info = QtCore.QFileInfo(index.data(QtCore.Qt.StatusTipRole))
        info_string = '{day}/{month}/{year} {hour}:{minute}  {size}'.format(
            day=info.lastModified().toString('dd'),
            month=info.lastModified().toString('MM'),
            year=info.lastModified().toString('yyyy'),
            hour=info.lastModified().toString('hh'),
            minute=info.lastModified().toString('mm'),
            size=self._byte_to_string(info.size())
        )

        info_string = metrics.elidedText(
            info_string,
            QtCore.Qt.ElideRight,
            rect.width() - common.MARGIN
        )

        if selected:
            color = common.TEXT
        else:
            color = common.SECONDARY_TEXT
        painter.setPen(QtGui.QPen(color))
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
            info_string
        )
        info_width = metrics.width(info_string)

        # Description
        config_info = QtCore.QFileInfo(self.get_config_path(index))
        if not config_info.exists():
            return

        text = None
        with open(self.get_config_path(index), 'r') as f:
            text = next((l for l in f if 'description' in l), None)

        if not text:
            return

        rect, font, metrics = self.get_description_rect(option.rect)
        painter.setFont(font)

        metrics = QtGui.QFontMetrics(painter.font())
        text = metrics.elidedText(
            text.replace('description = ', '').lstrip().rstrip(),
            QtCore.Qt.ElideRight,
            rect.width() - common.MARGIN - info_width
        )

        rect.setWidth(rect.width() - info_width - common.MARGIN)
        if not selected:
            painter.setPen(common.TEXT_NOTE)
        else:
            color = QtGui.QColor(common.TEXT_NOTE)
            color.setRed(color.red() + 50)
            color.setGreen(color.green() + 50)
            color.setBlue(color.blue() + 50)
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            text
        )
