# -*- coding: utf-8 -*-
"""Delegate and editor classes for the list widgets.
"""
# pylint: disable=E1101, C0103, R0913, I1101, W0613, R0201

import re
from PySide2 import QtWidgets, QtGui, QtCore

import mayabrowser.common as common
from mayabrowser.common import cmds
import mayabrowser.configparsers as configparser
from mayabrowser.configparsers import local_settings
from mayabrowser.configparsers import AssetSettings
# from mayabrowser.configparsers import FileConfig


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

    def paint_focus(self, *args):
        painter, option, _, _, focused, _, _, _ = args

        if not focused:
            return

        painter.save()

        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=False
        )

        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.SELECTION)
        pen.setWidth(1.0)

        rect = QtCore.QRectF(option.rect)
        rect.setLeft(rect.left() + 1)
        rect.setTop(rect.top() + 1)
        rect.setRight(rect.right() - 1)
        rect.setBottom(rect.bottom() - 1)

        path = QtGui.QPainterPath()
        path.addRect(rect)

        painter.strokePath(path, pen)

        painter.restore()

    def paint_favourite(self, *args):
        """Paints the little yellow dot, that marks items as the favourite item."""
        painter, option, index, selected, focused, active, archived, favourite = args

        if not favourite:
            return

        painter.save()

        if selected:
            color = QtGui.QColor(common.SELECTION)
            color.setRed(color.red() + 20)
            color.setGreen(color.green() + 20)
            color.setBlue(color.blue() + 20)
        else:
            color = common.SELECTION

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))

        size = 6
        rect = QtCore.QRect(option.rect)
        rect.setLeft(option.rect.width() - size * 2)
        rect.setWidth(size)

        rect.setHeight(size)
        rect.moveTop(rect.top() + (rect.height()))
        # rect.moveTop(rect.top() - (rect.height() / 2.0))

        painter.drawRoundedRect(rect, size * 0.5, size * 0.5)

        painter.restore()

    def paint_background(self, *args):
        """Paints the background."""
        painter, option, _, selected, _, _, _, _ = args

        painter.save()

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        if selected:
            color = common.BACKGROUND_SELECTED
        else:
            color = common.BACKGROUND
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(option.rect)

        painter.restore()

    def paint_separators(self, *args):
        """Paints horizontal separators."""
        painter, option, index, selected, _, _, _, _ = args

        painter.save()

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(common.SEPARATOR))

        if not selected:
            THICKNESS = 1.0
        else:
            THICKNESS = 1.0

        # Bottom
        rect = QtCore.QRectF(
            option.rect.left(),
            option.rect.top() + option.rect.height() - THICKNESS,
            option.rect.width(),
            (THICKNESS / 2.0)
        )
        painter.drawRect(rect)

        # Top
        rect = QtCore.QRectF(
            option.rect.left(),
            option.rect.top(),
            option.rect.width(),
            (THICKNESS / 2.0)
        )
        painter.drawRect(rect)
        painter.save()

    def paint_selection_indicator(self, *args):
        """Paints the blue leading rectangle to indicate the current selection."""
        painter, option, _, selected, _, _, _, _ = args

        painter.save()

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        if selected:
            painter.setBrush(QtGui.QBrush(common.SELECTION))
        else:
            painter.setBrush(QtGui.QBrush(common.SEPARATOR))

        rect = QtCore.QRect(option.rect)
        rect.setWidth(4)
        painter.drawRect(rect)

        painter.restore()

    def paint_active_indicator(self, *args):
        """Paints the yellow leading rectangle to indicate item is set as current."""
        painter, option, index, selected, _, active, _, _ = args

        if not active:
            return

        painter.save()

        WIDTH = 6

        painter.setBrush(QtCore.Qt.NoBrush)
        pen = QtGui.QPen(common.SELECTION)

        pen.setWidth(2)
        painter.setPen(pen)

        # Main rectangle
        rect = QtCore.QRect(option.rect)
        rect.setLeft(4 + option.rect.height())

        rect.setTop(rect.top() + WIDTH)
        rect.setBottom(rect.bottom() - (WIDTH))
        rect.setLeft(rect.left() + WIDTH)
        rect.setRight(rect.right() - (WIDTH))

        painter.drawRect(rect)

        # Leading rectangle
        rect = QtCore.QRect(option.rect)
        rect.setWidth(4)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(common.SELECTION))
        painter.drawRect(rect)
        painter.restore()


    def paint_thumbnail_shadow(self, *args):
        """Paints a drop-shadow"""
        painter, option, index, selected, focused, active, archived, favourite = args

        painter.save()

        rect = QtCore.QRect(option.rect)
        rect.setLeft(rect.left() + 4 + option.rect.height())
        rect.setWidth(option.rect.height())

        # rect.setLeft(rect.left() + rect.width())

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

        if selected:
            color = common.THUMBNAIL_BACKGROUND_SELECTED
        else:
            color = common.THUMBNAIL_BACKGROUND

        rect = QtCore.QRect(option.rect)
        rect.setLeft(rect.left() + 4)  # Accounting for the leading indicator
        rect.setWidth(rect.height())

        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(color))
        painter.drawRect(rect)

        # Checking if the images are in the cache already:
        # Placeholder image
        if common.MAYA_THUMBNAIL in common.IMAGE_CACHE:
            placeholder = common.IMAGE_CACHE[common.MAYA_THUMBNAIL]
        else:
            placeholder = QtGui.QImage()
            placeholder.load(common.MAYA_THUMBNAIL)
            placeholder = ThumbnailEditor.smooth_copy(
                placeholder,
                option.rect.height()
            )
            common.IMAGE_CACHE[common.MAYA_THUMBNAIL] = placeholder

        path = AssetSettings(index.data(QtCore.Qt.PathRole).filePath()).thumbnail_path()
        image = placeholder

        # Thumbnail image
        if QtCore.QFileInfo(path).exists():
            if path in common.IMAGE_CACHE:
                image = common.IMAGE_CACHE[path]
            else:
                image = QtGui.QImage()
                image.load(path)
                if image.isNull():
                    image = placeholder
                else:
                    image = ThumbnailEditor.smooth_copy(
                        image,
                        option.rect.height()
                    )
                    common.IMAGE_CACHE[path] = image
        else:
            image = placeholder

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
        painter, option, index, selected, _, _, _, _ = args

        painter.save()

        font = painter.font()
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.setBrush(QtCore.Qt.NoBrush)

        if selected:
            painter.setPen(QtGui.QPen(common.TEXT))
        else:
            painter.setPen(QtGui.QPen(common.TEXT_SELECTED))

        rect = QtCore.QRect(option.rect)
        rect.setLeft(rect.left() + 4 + option.rect.height() + common.MARGIN)
        rect.setRight(rect.left() - common.MARGIN)

        metrics = QtGui.QFontMetrics(painter.font())
        text = metrics.elidedText(
            index.data(QtCore.Qt.DisplayRole),
            QtCore.Qt.ElideMiddle,
            rect.width()
        )
        width = metrics.width(text) + common.MARGIN
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
        rect.setWidth(4)
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        painter.setBrush(QtGui.QBrush(common.get_label(_filter)))
        painter.drawRect(rect)

        painter.restore()

    def paint_archived(self, *args):
        """Paints a `disabled` overlay on top of items flagged as `archived`."""
        painter, option, index, selected, focused, active, archived, favourite = args

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

    @staticmethod
    def get_thumbnaileditor_cls(*args, **kwargs):
        """Abstract method needs to be overriden in the subclass.
        Should return the Class Type of the editor.

        """
        raise NotImplementedError('get_thumbnaileditor_cls() is abstract.')

    @staticmethod
    def get_noteeditor_cls(*args, **kwargs):
        """Abstract method needs to be overriden in the subclass.
        Should return the Class Type of the editor.

        """
        raise NotImplementedError('get_noteeditor_cls() is abstract.')

    def get_name_rect(self, rect):
        """Returns the rectangle containing the name.

        Args:
            rect (QtCore.QRect): The QListWidgetItem's visual rectangle.

        Returns:            QtCore.QRect

        """
        painter = QtGui.QPainter()
        font = QtGui.QFont('Roboto Black')
        font.setBold(False)
        font.setPointSize(9.0)
        painter.setFont(font)
        metrics = QtGui.QFontMetrics(painter.font())
        editor_rect = QtCore.QRect(rect)

        editor_rect.setLeft(editor_rect.left() + 4 + rect.height() + common.MARGIN)
        editor_rect.setRight(editor_rect.right() - common.MARGIN)
        editor_rect.setHeight(metrics.height())

        # Center rectangle
        editor_rect.moveTop(
            rect.top() +
            (rect.height() * 0.5) -
            (editor_rect.height() * 0.5)
        )
        return editor_rect, font, metrics

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

        offset = 4 + rect.height() + common.MARGIN
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

        rect.setLeft(rect.left() + 4 + rect.height() + common.MARGIN)
        rect.setRight(rect.right() - common.MARGIN)

        # Center rectangle
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        rect.setHeight(metrics.height())
        rect.moveTop(rect.top() + (rect.height() / 2.0))
        return rect, font, metrics

    def get_thumbnail_rect(self, rect):
        """Returns the rectangle for the thumbnail editor."""
        rect = QtCore.QRect(rect)
        rect.moveLeft(4)
        rect.setWidth(rect.height())
        return rect

    def get_location_editor_rect(self, rect):
        rect = QtCore.QRect(rect)
        rect.setLeft(rect.right() - rect.height())
        rect.setWidth(rect.height())
        return rect

    def createEditor(self, parent, option, index, editor=0):  # pylint: disable=W0613
        """Creates the custom editors needed to edit the thumbnail and the description.

        References:
        http: // doc.qt.io/qt-5/QItemEditorFactory.html  # standard-editing-widgets

        """
        if not editor:
            return
        elif editor == 1:  # Editor to edit notes
            rect, _, _ = self.get_description_rect(option.rect)
            return self.get_noteeditor_cls(index, rect, self.parent(), parent=parent)
        elif editor == 2:  # Editor to pick a thumbnail
            rect = self.get_thumbnail_rect(option.rect)
            return self.get_thumbnaileditor_cls(index, rect, self.parent(), parent=parent)
        elif editor == 3:  # Button to remove a location, no editor needed
            return

    def sizeHint(self, option, index):
        """Custom size-hint. Sets the size of the files and asset widget items."""
        selected = index.row() == self.parent().currentIndex().row()
        size = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)
        return size

    def get_thumbnail_path(self, index):
        """Abstract method to be overriden in the subclass.
        Should return the path to the thumbnail file.

        """
        raise NotImplementedError(
            'get_thumbnail_path() is abstract and has to be overriden in the subclass.'
        )


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
        rect.moveLeft(rect.left() + 4)
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
            image = ThumbnailEditor.smooth_copy(
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
        painter, option, index, selected, focused, active, archived, favourite = args

        painter.save()

        if selected:
            color = common.THUMBNAIL_BACKGROUND_SELECTED
        else:
            color = common.BACKGROUND

        rect = QtCore.QRect(option.rect)
        # Making the aspect ratio of the image 16/9
        rect.setWidth(rect.height())
        rect.moveLeft(rect.left() + 4)  # Accounting for the leading indicator

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
            image = ThumbnailEditor.smooth_copy(
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
        rect.setLeft(4 + option.rect.height() + common.MARGIN)
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

    def get_thumbnaileditor_cls(self, *args, **kwargs):
        """Double-clicking the thumbnail on the BookmarksWidget will set the said
        item to become active. Hence, no editor widget is returned.

        It will, however set the selected bookmark to be active one.

        """
        self.parent().set_current_item_as_active()
        return None


class AssetWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetWidget`` to display the collecteds assets."""

    @staticmethod
    def get_thumbnaileditor_cls(*args, **kwargs):
        """The widget used to edit the thumbnail of the asset."""
        return ThumbnailEditor(*args, **kwargs)

    @staticmethod
    def get_noteeditor_cls(*args, **kwargs):
        """The widget used to edit the description of the asset."""
        return NoteEditor(*args, **kwargs)

    def paint(self, painter, option, index):
        """Defines how the BookmarksWidgetItems should be painted."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_separators(*args)
        self.paint_thumbnail(*args)
        self.paint_favourite(*args)
        self.paint_archived(*args)
        self.paint_data(*args)
        self.paint_selection_indicator(*args)
        self.paint_active_indicator(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_focus(*args)

    def paint_custom(self, *args):
        """Custom paint action to draw the buttons to trigger."""
        pass

    def paint_data(self, *args):
        """Paints the ``AssetWidget``'s `QListWidgetItems`' names and notes."""
        painter, option, index, selected, focused, active, archived, favourite = args

        painter.save()
        painter.setRenderHints(
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform,
            on=True
        )
        painter.setBrush(QtCore.Qt.NoBrush)
        if not selected:
            color = common.TEXT
        elif selected:
            color = common.TEXT_SELECTED

        painter.setPen(QtGui.QPen(color))

        # Name
        rect, font, metrics = self.get_name_rect(option.rect)


        painter.setFont(font)
        text = index.data(QtCore.Qt.DisplayRole)
        text = re.sub('[^0-9a-zA-Z]+', ' ', text)
        text = re.sub('[_]{1,}', ' ', text)
        text = text.lstrip().rstrip().upper()

        text = metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            rect.width()
        )

        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
            text
        )

        rect, font, metrics = self.get_description_rect(option.rect)
        painter.setFont(font)

        text = metrics.elidedText(
            index.data(QtCore.Qt.UserRole),
            QtCore.Qt.ElideRight,
            rect.width()
        )

        if not selected:
            painter.setPen(common.TEXT_NOTE)
        else:
            color = QtGui.QColor(common.TEXT_NOTE)
            color.setRed(color.red() + 50)
            color.setGreen(color.green() + 50)
            color.setBlue(color.blue() + 50)
        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
            text
        )

        painter.restore()

    def sizeHint(self, option, index):
        return QtCore.QSize(common.WIDTH, common.ASSET_ROW_HEIGHT)


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
        rect.setWidth(4)

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
            basedir_rect.setWidth(basedir_rect.width() + 4)
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

    @staticmethod
    def _byte_to_string(num, suffix='B'):
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

    @staticmethod
    def get_thumbnaileditor_cls(*args, **kwargs):
        return SceneThumbnailEditor(*args, **kwargs)

    @staticmethod
    def get_noteeditor_cls(*args, **kwargs):
        return NoteEditor(*args, **kwargs)


class ThumbnailEditor(QtWidgets.QWidget):
    """Thumbnail editor baseclass."""

    def __init__(self, index, rect, view, parent=None):
        super(ThumbnailEditor, self).__init__(parent=parent)

        file_info = index.data(QtCore.Qt.PathRole)
        settings = AssetSettings(file_info.filePath())
        dialog = QtWidgets.QFileDialog()
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter('Image files (*.png *.jpg  *.jpeg)')
        dialog.setDirectory(QtCore.QDir(file_info.filePath()))
        dialog.setOption(QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not dialog.exec_():
            return

        if not dialog.selectedFiles():
            return

        image = QtGui.QImage()
        image.load(next(f for f in dialog.selectedFiles()))
        image = self.smooth_copy(image, common.THUMBNAIL_IMAGE_SIZE)

        # Deleting previous thumbnail from the image cache
        if settings.thumbnail_path() in common.IMAGE_CACHE:
            del common.IMAGE_CACHE[settings.thumbnail_path()]

        # Saving the thumbnail and creating the directories as necessary
        file_info = QtCore.QFileInfo(settings.thumbnail_path())
        if not file_info.dir().exists():
            QtCore.QDir().mkpath(file_info.dir().path())
        if image.save(settings.thumbnail_path()):
            self.parent().update()

    @staticmethod
    def smooth_copy(image, size):
        """Returns an aspect-ratio aware smooth scaled copy of the image."""
        longer = float(max(image.width(), image.height()))
        factor = float(float(size) / float(longer))
        if image.width() < image.height():
            image = image.smoothScaled(
                float(image.width()) * factor,
                size
            )
            return image
        image = image.smoothScaled(
            size,
            float(image.height()) * factor
        )
        return image


class NoteEditor(QtWidgets.QWidget):
    """Note editor baseclass."""

    def __init__(self, index, parent=None):
        super(NoteEditor, self).__init__(parent=parent)
        self._index = index

        self.editor = None
        self.settings = configparser.AssetSettings(self._index.data(QtCore.Qt.PathRole).filePath())
        self._createUI()

        self.editor.focusOutEvent = self.focusOutEvent
        self.editor.installEventFilter(self)

        self._connectSignals()

        # Widget is show when created
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.set_size(self.parent().viewport().size())
        self.setFocusProxy(self.editor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.show()
        self.setFocus()

        self.editor.setText(self.settings.value('description/description'))
        self.editor.selectAll()

    def sizeHint(self):
        return QtCore.QSize(
            self.parent().visualRect(self._index).width(),
            self.parent().visualRect(self._index).height()
        )

    def set_size(self, size):
        """Sets the widget size."""
        rect = QtCore.QRect(self.parent().visualRect(self._index))
        rect.setLeft(rect.left() + 4 + rect.height())

        self.move(rect.topLeft())
        self.resize(size.width() - rect.left(), rect.height())

    def eventFilter(self, widget, event):
        """We're filtering the enter key event here, otherwise, the
        list widget would close open finishing editing.

        """
        if not event.type() == QtCore.QEvent.KeyPress:
            return False

        if event.modifiers() == QtCore.Qt.NoModifier:
            if (event.key() == QtCore.Qt.Key_Return) or event.key() == QtCore.Qt.Key_Enter:
                self.action()
                return True
            elif event.key() == QtCore.Qt.Key_Tab:
                self.action()
                self.parent().key_down()
                self.parent().key_tab()
                return True
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.action()
                self.parent().key_up()
                self.parent().key_tab()
                return True
            elif event.key() == QtCore.Qt.Key_Escape:
                self.close()
                return True

        if event.modifiers() == QtCore.Qt.ShiftModifier:
            if event.key() == QtCore.Qt.Key_Tab:
                self.action()
                self.parent().key_up()
                self.parent().key_tab()
                return True
            elif event.key() == QtCore.Qt.Key_Backtab:
                self.action()
                self.parent().key_up()
                self.parent().key_tab()
                return True
        return False

    def focusOutEvent(self, event):
        """Closes the editor on focus loss."""
        if event.lostFocus():
            self.close()

    def _connectSignals(self):
        """Connects signals."""
        self.editor.editingFinished.connect(self.action)
        self.parent().sizeChanged.connect(self.set_size)

    def _createUI(self):
        """Creates the layout."""
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(common.MARGIN * 0.5, 0, common.MARGIN * 0.5, 0)
        self.layout().setSpacing(6)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.editor = QtWidgets.QLineEdit()
        self.editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.editor.setTextMargins(0, 0, 0, 0)

        self.editor.setStyleSheet(
            'background-color: rgb(50,50,50);\
            color: rgba({},{},{},{});\
            font-family: "Roboto Medium"; font-size: 8pt;'.format(*common.TEXT_NOTE.getRgb())
        )

        label = QtWidgets.QLabel('Description')
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label.setStyleSheet(
            'font-family: "Roboto Black";\
            font-size: 8pt;\
            color: rgba({},{},{},{});'.format(*common.TEXT.getRgb())
        )

        self.layout().addStretch(1)
        self.layout().addWidget(label, 1)
        self.layout().addWidget(self.editor, 1)
        self.layout().addStretch(1)

    def paintEvent(self, event):
        """Custom paint used to paint the background."""
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            rect = QtCore.QRect()
            rect.setWidth(self.width())
            rect.setHeight(self.height())

            pen = QtGui.QPen(common.SELECTION)
            pen.setWidth(2)
            painter.setPen(pen)
            color = QtGui.QColor(common.BACKGROUND_SELECTED)
            painter.setBrush(QtGui.QBrush(color))
            painter.drawRect(rect)
            painter.end()

            return
        super(NoteEditor, self).paintEvent(event)

    def action(self):
        """Main actions to run when the return key is pressed."""
        if self.settings.value('description/description') == self.editor.text():
            self.close()
            return

        item = self.parent().itemFromIndex(self._index)
        item.setData(QtCore.Qt.UserRole, self.editor.text())
        self.settings.setValue('description/description', self.editor.text())
        self.close()
