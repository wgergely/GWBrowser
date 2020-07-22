# -*- coding: utf-8 -*-
"""The listdelegate used to  paint the bookmark, asset and file widgets.

The listdelegate is fully integerated with the BaseListViews because we're relying
on the drawing of the elements to define clickable regions on a row.

The listdelegate itself is very slow - we're using QPainterPaths to draw aliased
text output and hence backing some of the operations by simple caches.

"""
import re
from functools import wraps
from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.common as common
import bookmarks.images as images


regex_remove_version = re.compile(
    ur'(.*)(v)([\[0-9\-\]]+.*)', flags=re.IGNORECASE | re.UNICODE)
regex_remove_bracket = re.compile(
    ur'[\[\]]*', flags=re.IGNORECASE | re.UNICODE)


HOVER_COLOR = QtGui.QColor(255, 255, 255, 10)
BACKGROUND_COLOR = QtGui.QColor(0, 0, 0, 100)


BackgroundRect = 0
IndicatorRect = 1
ThumbnailRect = 2
AssetNameRect = 3
AssetDescriptionRect = 4
AddAssetRect = 5
TodoRect = 6
RevealRect = 7
ArchiveRect = 8
FavouriteRect = 9
DataRect = 10
BookmarkPropertiesRect = 11


PATH_CACHE = {}


def get_painter_path(x, y, font, text):
    """Creates, populates and caches a QPainterPath instance."""
    k = u'{}{}{}{}'.format(x, y, font, text)
    if k not in PATH_CACHE:
        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)
        PATH_CACHE[k] = path
    return PATH_CACHE[k]


RECTANGLE_CACHE = {}


def get_rectangles(rectangle, count):
    """Returns the paintable/clickable regions based on the number of
    inline icons and the source rectangle.

    Args:
        rectangle (QtCore.QRect): A source rectangle.
        count (int):    The number of inline icons.

    Returns:
        dict: A dictionary with all the requested rectangles.

    """
    k = '{}{}'.format(rectangle, count)
    if k in RECTANGLE_CACHE:
        return RECTANGLE_CACHE[k]

    def adjusted():
        return rectangle.adjusted(0, 0, 0, -common.ROW_SEPARATOR())

    background_rect = adjusted()
    background_rect.setLeft(common.INDICATOR_WIDTH())

    indicator_rect = QtCore.QRect(rectangle)
    indicator_rect.setWidth(common.INDICATOR_WIDTH())

    thumbnail_rect = QtCore.QRect(rectangle)
    thumbnail_rect.setWidth(thumbnail_rect.height())
    thumbnail_rect.moveLeft(common.INDICATOR_WIDTH())

    # Inline icons rect
    inline_icon_rects = []
    inline_icon_rect = adjusted()
    spacing = common.INDICATOR_WIDTH() * 2
    center = inline_icon_rect.center()
    size = QtCore.QSize(common.MARGIN(), common.MARGIN())
    inline_icon_rect.setSize(size)
    inline_icon_rect.moveCenter(center)
    inline_icon_rect.moveRight(rectangle.right() - spacing)

    offset = 0
    for _ in xrange(count):
        r = inline_icon_rect.translated(offset, 0)
        inline_icon_rects.append(r)
        offset -= inline_icon_rect.width() + spacing
    offset -= spacing

    data_rect = adjusted()
    data_rect.setLeft(thumbnail_rect.right() + spacing)
    data_rect.setRight(rectangle.right() + offset)

    null_rect = QtCore.QRect()

    RECTANGLE_CACHE[k] = {
        BackgroundRect: background_rect,
        IndicatorRect: indicator_rect,
        ThumbnailRect: thumbnail_rect,
        FavouriteRect: inline_icon_rects[0] if count > 0 else null_rect,
        ArchiveRect: inline_icon_rects[1] if count > 1 else null_rect,
        RevealRect: inline_icon_rects[2] if count > 2 else null_rect,
        TodoRect: inline_icon_rects[3] if count > 3 else null_rect,
        AddAssetRect: inline_icon_rects[4] if count > 4 else null_rect,
        BookmarkPropertiesRect: inline_icon_rects[5] if count > 5 else null_rect,
        DataRect: data_rect
    }
    return RECTANGLE_CACHE[k]


TEXT_SEGMENT_CACHE = {}


def paintmethod(func):
    """@Decorator to save the painter state."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        args[1].save()
        res = func(self, *args, **kwargs)
        args[1].restore()
        return res
    return func_wrapper


class BaseDelegate(QtWidgets.QAbstractItemDelegate):
    """Base listdelegate containing methods to draw our list items."""
    fallback_thumb = u'placeholder'

    def __init__(self, parent=None):
        super(BaseDelegate, self).__init__(parent=parent)
        self._clickable_rectangles = {}

    def paint(self, painter, option, index):
        raise NotImplementedError(
            '`paint()` is abstract and has to be overriden in the subclass!')

    def get_paint_arguments(self, painter, option, index, antialiasing=True):
        """A utility class for gathering all the arguments needed to paint
        the individual listelements.

        """
        if antialiasing:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
            painter.setRenderHint(
                QtGui.QPainter.SmoothPixmapTransform, on=True)
        else:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, on=False)
            painter.setRenderHint(
                QtGui.QPainter.SmoothPixmapTransform, on=False)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)

        selected = option.state & QtWidgets.QStyle.State_Selected
        focused = option.state & QtWidgets.QStyle.State_HasFocus
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        flags = index.flags()
        favourite = flags & common.MarkedAsFavourite
        archived = flags & common.MarkedAsArchived
        active = flags & common.MarkedAsActive
        rectangles = get_rectangles(
            option.rect, self.parent().inline_icons_count())
        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())
        painter.setFont(font)

        cursor_position = self.parent().mapFromGlobal(common.cursor.pos())

        args = (
            rectangles,
            painter,
            option,
            index,
            selected,
            focused,
            active,
            archived,
            favourite,
            hover,
            font,
            metrics,
            cursor_position
        )
        return args

    def get_clickable_rectangles(self, index, rectangles):
        """Clickable rectangles are used by the the QListView to identify
        interactive regions.

        For instance, folder names are clickable and used to toggle filters.
        Since the size of the rectangle depends on how the listdelegate is handling
        painting, we're using the listdelegate calculate and cache these rectangles.

        The actual rectangles are calculated and saved when a relavant paint
        method is called.

        """
        if index.row() in self._clickable_rectangles:
            return self._clickable_rectangles[index.row()]
        return []

    def paint_name(self, *args):
        pass

    @paintmethod
    def paint_description_editor_background(self, *args, **kwargs):
        """Overlay do indicate the source of a drag operation."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        if index != self.parent().selectionModel().currentIndex():
            return
        if not self.parent().description_editor_widget.isVisible():
            return

        painter.setBrush(common.BACKGROUND_SELECTED)
        painter.setPen(QtCore.Qt.NoPen)
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rectangles[ThumbnailRect].right())
        rect.setRight(rect.right() - (common.MARGIN() * 0.5))
        painter.drawRect(rect)

    @paintmethod
    def paint_thumbnail(self, *args):
        """Paints an item's thumbnail.

        The underlying image data is stored in `ImageCache`. If the
        requested QPixmap has never been drawn before we will create and store
        it by calling `images.ImageCache.get_pixmap()`.

        If no associated image data is available, we will use a generic thumbnail
        associated with the item's type.

        See the `images` module for implementation details.

        """
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        # painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        # Background
        color = common.THUMBNAIL_BACKGROUND
        painter.setBrush(color)
        painter.drawRect(rectangles[ThumbnailRect])

        o = 1.0 if selected or active or hover else 0.9
        painter.setOpacity(o)

        _p = index.data(common.ParentPathRole)
        if not _p:
            return

        source = index.data(QtCore.Qt.StatusTipRole)
        if not source:
            return

        thumbnail_path = images.get_thumbnail_path(
            _p[0],
            _p[1],
            _p[2],
            source
        )

        _h = index.data(QtCore.Qt.SizeHintRole)
        if not _h:
            return
        size = _h.height()

        pixmap = images.ImageCache.get_pixmap(thumbnail_path, size)
        if not pixmap:
            # If this item is an un-collapsed sequence item, the sequence
            # might have a thumbnail...
            thumbnail_path = images.get_thumbnail_path(
                _p[0],
                _p[1],
                _p[2],
                source,
                proxy=True
            )
            pixmap = images.ImageCache.get_pixmap(thumbnail_path, size)
            if pixmap:
                color = images.ImageCache.get_color(thumbnail_path)
                if color:
                    painter.setBrush(color)
                    painter.drawRect(rectangles[ThumbnailRect])
            else:
                # Let's load a placeholder if there's not generated thumbnail
                pixmap = images.ImageCache.get_pixmap(
                    images.get_placeholder_path(
                        source, fallback=self.fallback_thumb),
                    size
                )
                if not pixmap:
                    return
        else:
            color = images.ImageCache.get_color(thumbnail_path)
            if color:
                painter.setBrush(color)
                painter.drawRect(rectangles[ThumbnailRect])

        # Let's make sure the image is fully fitted, even if the image's size
        # doesn't match ThumbnailRect
        s = float(rectangles[ThumbnailRect].height())
        longest_edge = float(max((pixmap.width(), pixmap.height())))
        ratio = s / longest_edge
        w = pixmap.width() * ratio
        h = pixmap.height() * ratio

        _rect = QtCore.QRect(0, 0, int(w), int(h))
        _rect.moveCenter(rectangles[ThumbnailRect].center())
        painter.drawPixmap(_rect, pixmap, pixmap.rect())

    def paint_thumbnail_drop_indicator(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        drop = self.parent()._thumbnail_drop
        if drop[1] and drop[0] == index.row():
            painter.setOpacity(0.9)
            painter.setBrush(common.SEPARATOR)
            painter.drawRect(option.rect)

            painter.setPen(common.ADD)
            font, metrics = common.font_db.secondary_font(
                common.SMALL_FONT_SIZE())
            painter.setFont(font)

            text = u'Drop image to add as thumbnail'
            painter.drawText(
                option.rect.marginsRemoved(QtCore.QMargins(
                    common.MARGIN(), 0, common.MARGIN(), 0)),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                text,
                boundingRect=option.rect,
            )

            o = common.ROW_SEPARATOR() * 2.0
            rect = rectangles[ThumbnailRect].marginsRemoved(
                QtCore.QMargins(o, o, o, o))
            painter.drawRect(rect)

            pen = QtGui.QPen(common.ADD)
            pen.setWidth(o)
            painter.setPen(pen)
            painter.setBrush(common.ADD)
            painter.setOpacity(0.5)
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'add', common.ADD, rect.height() * 0.5)
            painter.drawRect(rect)
            irect = pixmap.rect()
            irect.moveCenter(rect.center())
            painter.drawPixmap(irect, pixmap, pixmap.rect())

    @paintmethod
    def paint_background(self, *args):
        """Paints the background for all list items."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = QtCore.QRect(rectangles[BackgroundRect])

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        color = common.BACKGROUND_SELECTED if selected else common.BACKGROUND
        painter.setBrush(color)

        painter.setOpacity(1.0)
        painter.drawRect(rect)

        # Setting the opacity of the separator
        if index.row() != (self.parent().model().rowCount() - 1):
            painter.setOpacity(0.5)
            painter.setBrush(color)
            _rect = QtCore.QRect(rect)
            _rect.setBottom(_rect.bottom() + common.INDICATOR_WIDTH())
            _rect.setTop(_rect.bottom() - common.INDICATOR_WIDTH())
            _rect.setLeft(common.INDICATOR_WIDTH() +
                          option.rect.height() - common.ROW_SEPARATOR())
            painter.drawRect(_rect)

        # Active indicator
        if active:
            rect.setLeft(option.rect.left() +
                         common.INDICATOR_WIDTH() + option.rect.height())
            painter.setOpacity(0.5)
            painter.setBrush(common.ADD)
            painter.drawRoundedRect(
                rect, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())
            painter.setOpacity(0.8)
            pen = QtGui.QPen(common.ADD)
            pen.setWidth(common.ROW_SEPARATOR() * 2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            o = common.ROW_SEPARATOR()
            rect = rect.marginsRemoved(QtCore.QMargins(o, o, o * 1.5, o * 1.5))
            painter.drawRoundedRect(
                rect, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())

        # Hover indicator
        if hover:
            painter.setBrush(HOVER_COLOR)
            painter.drawRect(rect)

    @paintmethod
    def paint_inline_icons(self, *args):
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        c = self.parent().inline_icons_count()
        if c:
            o = (common.MARGIN() + (common.INDICATOR_WIDTH() * 2)) * \
                c + common.MARGIN()
            bg_rect = QtCore.QRect(rectangles[BackgroundRect])
            bg_rect.setLeft(bg_rect.right() - o)
            painter.setBrush(common.SEPARATOR)
            painter.setOpacity(0.3)
            painter.drawRect(bg_rect)

        painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)
        rect = rectangles[FavouriteRect]
        if rect and not archived:
            if rect.contains(cursor_position) or favourite:
                painter.setOpacity(1.0)

            color = common.TEXT_DISABLED if rect.contains(
                cursor_position) else common.SEPARATOR
            color = common.TEXT_SELECTED if favourite else color

            pixmap = images.ImageCache.get_rsc_pixmap(
                u'favourite', color, common.MARGIN())
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[ArchiveRect]
        if rect:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
            color = common.ADD if archived else common.REMOVE
            color = color if rect.contains(
                cursor_position) else common.SEPARATOR

            if archived:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'check', common.ADD, common.MARGIN())
            else:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'remove', color, common.MARGIN())
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[RevealRect]
        if rect and not archived:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
            color = common.TEXT_SELECTED if rect.contains(
                cursor_position) else common.SEPARATOR
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'reveal_folder', color, common.MARGIN())
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[TodoRect]
        if rect and not archived:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)

            color = common.TEXT_SELECTED if rect.contains(
                cursor_position) else common.SEPARATOR
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'todo', color, common.MARGIN())
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

            # Circular background
            size = common.LARGE_FONT_SIZE()
            count_rect = QtCore.QRect(0, 0, size, size)
            count_rect.moveCenter(rect.bottomRight())

            if index.data(common.TodoCountRole):
                painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
                if rect.contains(cursor_position):
                    color = common.TEXT_SELECTED
                    pixmap = images.ImageCache.get_rsc_pixmap(
                        u'add', color, size)
                    painter.drawPixmap(count_rect, pixmap)
                else:
                    color = common.FAVOURITE
                    painter.setBrush(color)
                    painter.drawRoundedRect(
                        count_rect, count_rect.width() / 2.0, count_rect.height() / 2.0)

                    text = unicode(index.data(common.TodoCountRole))
                    _font, _metrics = common.font_db.primary_font(
                        font_size=common.SMALL_FONT_SIZE())
                    x = count_rect.center().x() - (_metrics.width(text) / 2.0) + common.ROW_SEPARATOR()
                    y = count_rect.center().y() + (_metrics.ascent() / 2.0)

                    painter.setBrush(common.TEXT)
                    path = get_painter_path(x, y, _font, text)
                    painter.drawPath(path)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[AddAssetRect]
        if rect and not archived:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
            color = common.TEXT_SELECTED if rect.contains(
                cursor_position) else common.SEPARATOR
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'add', color, common.MARGIN())
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

        rect = rectangles[BookmarkPropertiesRect]
        if rect and not archived:
            if rect.contains(cursor_position):
                painter.setOpacity(1.0)
            color = common.TEXT_SELECTED if rect.contains(
                cursor_position) else common.SEPARATOR
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'settings', color, common.MARGIN())
            painter.drawPixmap(rect, pixmap)
            painter.setOpacity(0.85) if hover else painter.setOpacity(0.6667)

    @paintmethod
    def paint_selection_indicator(self, *args):
        """Paints the leading rectangle indicating the selection."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = rectangles[IndicatorRect]
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        color = common.TEXT_SELECTED if selected else common.TRANSPARENT
        painter.setBrush(color)
        painter.drawRoundedRect(rect, rect.width() * 0.5, rect.width() * 0.5)

    @paintmethod
    def paint_thumbnail_shadow(self, *args):
        """Paints a drop-shadow"""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        rect = QtCore.QRect(rectangles[ThumbnailRect])
        rect.moveLeft(rect.left() + rect.width())
        rect.setWidth(common.MARGIN())

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'gradient', None, rect.height())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_file_shadow(self, *args):
        """Paints a drop-shadow"""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        rect = QtCore.QRect(rectangles[DataRect])
        thumb_rect = QtCore.QRect(rectangles[ThumbnailRect])

        if index.row() != (self.parent().model().rowCount() - 1):
            thumb_rect.setHeight(thumb_rect.height() + common.ROW_SEPARATOR())
            rect.setHeight(rect.height() + common.ROW_SEPARATOR())

        if not self.parent().buttons_hidden():
            rect.setLeft(rect.right() - (common.MARGIN() * 0.5))
            rect.setWidth(common.MARGIN())
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'gradient', None, rect.height())
            painter.setOpacity(1.0)
            painter.drawPixmap(rect, pixmap, pixmap.rect())

        rect = QtCore.QRect(thumb_rect)
        rect.setWidth(common.MARGIN())
        rect.moveRight(thumb_rect.right())
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'gradient3', None, rect.height())
        painter.setOpacity(0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

        rect.setWidth(common.MARGIN() * 0.5)
        rect.moveRight(thumb_rect.right())
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'gradient3', None, rect.height())
        painter.setOpacity(0.5)
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    @paintmethod
    def paint_archived(self, *args):
        """Paints a gray overlay when an item is archived."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not archived:
            return
        painter.setBrush(common.SEPARATOR)
        painter.setOpacity(0.8)
        painter.drawRect(option.rect)


class BookmarksWidgetDelegate(BaseDelegate):
    """The listdelegate used to paint the bookmark items."""
    fallback_thumb = u'thumb_bookmark_gray'

    def paint(self, painter, option, index):
        """Defines how the ``BookmarksWidget`` should be painted."""
        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)
        self.paint_background(*args)
        self.paint_thumbnail(*args)
        self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        self.paint_archived(*args)
        self.paint_inline_icons(*args)
        self.paint_description_editor_background(*args)
        self.paint_file_shadow(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)

    def get_description_rect(self, *args):
        """We don't have editable descriptions for bookmark items."""
        return QtCore.QRect()

    @paintmethod
    def paint_name(self, *args):
        """Paints name of the ``BookmarkWidget``'s items."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        if not index.isValid():
            return
        if not index.data(QtCore.Qt.DisplayRole):
            return
        if not index.data(common.ParentPathRole):
            return

        # Standin for the descirption rectangle
        self._clickable_rectangles[index.row()] = []
        self._clickable_rectangles[index.row()].append((QtCore.QRect(), u''))

        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        _datarect = QtCore.QRect(rectangles[DataRect])
        if not self.parent().buttons_hidden():
            rectangles[DataRect].setRight(
                rectangles[DataRect].right() - common.MARGIN())

        if hover or selected or active:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.66)

        text_segments = index.data(common.TextSegmentRole)
        text = u''.join([text_segments[f][0] for f in text_segments])

        rect = rectangles[DataRect]
        rect.setLeft(rect.left() + common.MARGIN())

        # First let's paint the background rectangle
        o = common.INDICATOR_WIDTH()

        text_width = metrics.width(text)
        r = QtCore.QRect(rect)
        r.setWidth(text_width)
        center = r.center()
        r.setHeight(metrics.height())
        r.moveCenter(center)
        r = r.marginsAdded(QtCore.QMargins(o * 3, o, o * 3, o))
        if (r.right() + o) > rect.right():
            r.setRight(rect.right() - o)

        color = common.ADD.darker(
            120) if active else common.FAVOURITE.darker(120)
        color = common.ADD.darker(150) if r.contains(
            cursor_position) else color
        f_subpath = u'"/' + index.data(common.ParentPathRole)[1] + u'/"'

        filter_text = self.parent().model().filter_text()
        if filter_text:
            if f_subpath.lower() in filter_text.lower():
                color = common.ADD.darker(120)

        painter.setBrush(color)
        pen = QtGui.QPen(color.darker(220))
        pen.setWidth(common.ROW_SEPARATOR())
        painter.setPen(pen)

        painter.drawRoundedRect(
            r, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())

        # Let's save the rectangle as a clickable rect
        self._clickable_rectangles[index.row()].append(
            (r, index.data(common.ParentPathRole)[1])
        )

        offset = 0
        painter.setPen(QtCore.Qt.NoPen)
        for segment in text_segments.itervalues():
            text, color = segment
            width = metrics.width(text)
            _r = QtCore.QRect(rect)
            _r.setWidth(width)
            center = _r.center()
            _r.setHeight(metrics.ascent())
            _r.moveCenter(center)
            _r.moveLeft(_r.left() + offset)

            if _r.left() >= rect.right():
                break

            if (_r.right() + o) > rect.right():
                _r.setRight(rect.right() - o)
                text = metrics.elidedText(
                    text,
                    QtCore.Qt.ElideRight,
                    _r.width()
                )

            painter.setBrush(color)
            x = _r.x()
            y = _r.bottom()
            path = path = get_painter_path(x, y, font, text)
            painter.drawPath(path)

            offset += width

        rectangles[DataRect] = _datarect

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().ROW_SIZE


class AssetsWidgetDelegate(BaseDelegate):
    """Delegate used by the ``AssetsWidget`` to display the collecteds assets."""
    fallback_thumb = u'thumb_item_gray'

    def paint(self, painter, option, index):
        """Defines how the ``AssetsWidget``'s' items should be painted."""
        # The index might still be populated...
        if index.data(QtCore.Qt.DisplayRole) is None:
            return
        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)
        self.paint_background(*args)
        self.paint_thumbnail(*args)
        # self.paint_thumbnail_shadow(*args)
        self.paint_name(*args)
        self.paint_archived(*args)
        self.paint_description_editor_background(*args)
        self.paint_inline_icons(*args)
        self.paint_file_shadow(*args)
        self.paint_selection_indicator(*args)
        self.paint_thumbnail_drop_indicator(*args)

    def get_description_rect(self, rectangles, index):
        """Returns the description area of an ``AssetsWidget`` item."""
        if not index.isValid():
            return

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + common.MARGIN())

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())

        name_rect = QtCore.QRect(rect)
        center = name_rect.center()
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(center)

        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        description_rect = QtCore.QRect(name_rect)
        description_rect.moveCenter(
            QtCore.QPoint(name_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )
        description_rect.setRight(description_rect.right() - common.MARGIN())
        return description_rect

    @paintmethod
    def paint_name(self, *args):
        """Paints the item names inside the ``AssetsWidget``."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setRight(rect.right() - common.MARGIN())
        rect.setLeft(rect.left() + common.MARGIN())

        # Name
        color = common.TEXT_SELECTED if hover else common.TEXT
        color = common.TEXT_SELECTED if selected else color
        painter.setBrush(color)

        name_rect = QtCore.QRect(rect)
        center = name_rect.center()
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(center)

        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        text = index.data(QtCore.Qt.DisplayRole)
        text = metrics.elidedText(
            text.upper(),
            QtCore.Qt.ElideRight,
            name_rect.width()
        )

        x = name_rect.left()
        y = name_rect.center().y() + (metrics.ascent() / 2.0)
        path = get_painter_path(x, y, font, text)
        painter.drawPath(path)

        description_rect = QtCore.QRect(name_rect)
        description_rect.moveCenter(
            QtCore.QPoint(name_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )
        description_rect.setWidth(description_rect.width() - common.MARGIN())

        color = common.TEXT if hover else common.SECONDARY_TEXT
        color = common.TEXT_SELECTED if selected else color
        painter.setBrush(color)

        text = index.data(common.DescriptionRole)
        text = text if text else u''
        font, _metrics = common.font_db.primary_font(
            font_size=common.MEDIUM_FONT_SIZE())
        painter.setFont(font)
        text = _metrics.elidedText(
            text,
            QtCore.Qt.ElideRight,
            description_rect.width()
        )

        if description_rect.contains(cursor_position):
            underline_rect = QtCore.QRect(description_rect)
            underline_rect.setTop(underline_rect.bottom())
            underline_rect.moveTop(
                underline_rect.top() + common.ROW_SEPARATOR())
            painter.setOpacity(0.5)
            painter.setBrush(common.SEPARATOR)
            painter.drawRect(underline_rect)

            painter.setOpacity(1.0)
            if not text:
                painter.setBrush(common.SECONDARY_TEXT)
            else:
                painter.setBrush(color)
            text = u'Double-click to edit...' if not text else text

        x = description_rect.left()
        y = description_rect.center().y() + (metrics.ascent() / 2.0)
        path = get_painter_path(x, y, font, text)
        painter.drawPath(path)

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().ROW_SIZE


class FilesWidgetDelegate(BaseDelegate):
    """QAbstractItemDelegate associated with ``FilesWidget``."""
    maximum_subdirs = 4

    def __init__(self, parent=None):
        super(FilesWidgetDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """Defines how the ``FilesWidget``'s' items should be painted."""
        args = self.get_paint_arguments(
            painter, option, index, antialiasing=False)
        if index.data(QtCore.Qt.DisplayRole) is None:
            return

        # Skip active elements
        _args = list(args)
        _args.pop(6)
        _args.insert(6, False)
        self.paint_background(*_args)
        self.paint_thumbnail(*args)

        b_hidden = self.parent().buttons_hidden()
        p_role = index.data(common.ParentPathRole)
        if p_role and not b_hidden:
            self.paint_file_shadow(*args)
            self.paint_name(*args)
        elif p_role and b_hidden:
            self.paint_simple_name(*args)

        if index.data(common.FileInfoLoaded):
            self.paint_archived(*args)
        self.paint_description_editor_background(*args)

        self.paint_inline_icons(*args)
        self.paint_selection_indicator(*args)

        if self.parent().drag_source_index.isValid():
            self.paint_drag_source(*args)
        self.paint_thumbnail_drop_indicator(*args)

    def get_description_rect(self, rectangles, index):
        """The description rectangle of a file item."""
        if self.parent().buttons_hidden():
            return self.get_simple_description_rectangle(rectangles, index)

        clickable = self.get_clickable_rectangles(index, rectangles)
        if not clickable:
            return QtCore.QRect()

        return clickable[0][0]

    @paintmethod
    def paint_name(self, *args):
        """Paints the subfolders and the filename of the current file inside the ``FilesWidget``."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        self._clickable_rectangles[index.row()] = []

        def draw_segments(it, font, metrics, offset):
            x = 0

            rect = QtCore.QRect(rectangles[DataRect])
            rect.setRight(rectangles[DataRect].right() - common.MARGIN() * 1.5)

            o = 0.9 if selected else 0.8
            o = 1.0 if hover else o
            painter.setOpacity(o)
            painter.setPen(QtCore.Qt.NoPen)
            for v in it:
                text, color = v

                color = common.TEXT_SELECTED if selected else color
                color = common.TEXT if hover else color

                width = metrics.width(text)
                rect.setLeft(rect.right() - width)

                if (rectangles[DataRect].left()) >= rect.left():
                    rect.setLeft(
                        rectangles[DataRect].left())
                    text = metrics.elidedText(
                        text,
                        QtCore.Qt.ElideLeft,
                        rect.width()
                    )
                    width = metrics.width(text)
                    rect.setLeft(rect.right() - width)

                x = rect.center().x() - (width / 2.0) + common.ROW_SEPARATOR()
                y = rect.center().y() + offset

                painter.setBrush(color)
                path = get_painter_path(x, y, font, text)
                painter.drawPath(path)

                rect.translate(-width, 0)

            return x

        def draw_subdirs(text_edge):
            font, metrics = common.font_db.primary_font(
                font_size=common.SMALL_FONT_SIZE())

            subdir_rectangles = self.get_subdir_rectangles(
                index, rectangles, metrics)
            if not subdir_rectangles:
                return rectangles[DataRect].left()

            r = rectangles[DataRect]

            filter_text = self.parent().model().filter_text()
            rootdir = index.data(common.ParentPathRole)[-1]
            rootdirs = rootdir.split(u'/')
            _o = common.INDICATOR_WIDTH() * 2

            if text_edge > rectangles[DataRect].left() + common.MARGIN():
                # Inner gray rectangle containing all other subfolder rectangles
                painter.setBrush(common.SEPARATOR)
                _r = QtCore.QRect(rectangles[DataRect])
                _r.setRight(
                    subdir_rectangles[-1][0].right() + _o)
                _r.setLeft(_r.left() - _o)

                if (_r.right() > (text_edge + _o)):
                    _r.setRight(text_edge)

                if _r.left() < rectangles[DataRect].left():
                    o = common.INDICATOR_WIDTH()
                    y = (option.rect.height() - common.ROW_HEIGHT()) / 2
                    __r = _r.marginsRemoved(
                        QtCore.QMargins(o, o + y, o, o + y))
                else:
                    __r = _r

                if not hover and not selected and not active:
                    painter.setOpacity(0.3)
                    _r.setRight(text_edge + _o)
                    if (_r.right() - common.ASSET_ROW_HEIGHT()) > rectangles[DataRect].left():
                        painter.drawRect(_r)

                painter.setOpacity(1.0)
                if not hover and not selected and not active:
                    _r.setLeft(_r.right() - common.ASSET_ROW_HEIGHT())
                    if _r.left() > rectangles[DataRect].left():
                        pixmap = images.ImageCache.get_rsc_pixmap(
                            'gradient4', common.BACKGROUND, common.ASSET_ROW_HEIGHT())
                        o_ = common.ROW_SEPARATOR()
                        painter.drawPixmap(_r, pixmap, pixmap.rect().marginsRemoved(
                            QtCore.QMargins(o_, o_, o_, o_)))

                painter.setOpacity(0.6)
                pen = QtGui.QPen(BACKGROUND_COLOR)
                pen.setWidth(common.ROW_SEPARATOR())
                painter.setPen(pen)
                o = common.INDICATOR_WIDTH()
                painter.drawRoundedRect(__r, o, o)

            o = 0.6
            if not hover:
                o += -0.2
            painter.setOpacity(o)

            for n, val in enumerate(subdir_rectangles):
                r, text = val
                if r.left() > text_edge:
                    break
                if r.right() > text_edge:
                    r.setRight(text_edge - (common.INDICATOR_WIDTH() * 2))
                    text = metrics.elidedText(
                        text,
                        QtCore.Qt.ElideRight,
                        r.width()
                    )
                    if not text:
                        continue

                # Background
                color = common.SEPARATOR if n == 0 else common.SECONDARY_BACKGROUND
                color = common.ADD if r.contains(cursor_position) else color

                if n >= len(rootdirs):
                    continue
                _subpath = rootdirs[n]
                f_subpath = u'"/' + _subpath + u'/"'
                if filter_text:
                    if f_subpath.lower() in filter_text.lower():
                        color = common.ADD

                painter.setBrush(color)
                pen = QtGui.QPen(BACKGROUND_COLOR)
                pen.setWidth(common.ROW_SEPARATOR())
                painter.setPen(pen)
                o = common.INDICATOR_WIDTH() * 0.5
                painter.drawRoundedRect(QtCore.QRect(r), o, o)

                # Save the rectangle as a clickable region to be used by
                # the list widget's mouse events
                self._clickable_rectangles[index.row()].append((r, text))

                if filter_text:
                    if f_subpath.lower() in filter_text.lower():
                        color = common.TEXT_SELECTED
                x = r.center().x() - (metrics.width(text) / 2.0)
                y = r.center().y() + (metrics.ascent() / 2.0)

                color = color.lighter(250)
                painter.setBrush(color)
                painter.setPen(QtCore.Qt.NoPen)
                path = get_painter_path(x, y, font, text)
                painter.drawPath(path)
            return r.right()

        def draw_description(font, metrics, left_limit, right_limit, offset):
            left_limit += common.INDICATOR_WIDTH() * 2
            color = common.TEXT_SELECTED if selected else common.ADD

            large_mode = option.rect.height() >= (common.ROW_HEIGHT() * 2)
            if large_mode:
                left_limit = rectangles[DataRect].left()
                right_limit = rectangles[DataRect].right() - common.MARGIN()
                font, metrics = common.font_db.primary_font(
                    common.MEDIUM_FONT_SIZE())

            text = index.data(common.DescriptionRole)
            text = metrics.elidedText(
                text,
                QtCore.Qt.ElideLeft,
                right_limit - left_limit
            )
            width = metrics.width(text)

            x = right_limit - width
            y = rectangles[DataRect].center().y() + offset
            if large_mode:
                y += metrics.lineSpacing()

            rect = QtCore.QRect()
            rect.setHeight(metrics.height())
            center = QtCore.QPoint(rectangles[DataRect].center().x(), y)
            rect.moveCenter(center)
            rect.setLeft(left_limit)
            rect.setRight(right_limit)
            self._clickable_rectangles[index.row()].insert(0, (rect, text))

            if rectangles[DataRect].contains(cursor_position):
                rect = QtCore.QRect(rectangles[DataRect])
                rect.setHeight(common.ROW_SEPARATOR())
                rect.moveTop(y)
                rect.setLeft(left_limit)
                rect.setRight(right_limit)

                painter.setOpacity(0.3)
                painter.setBrush(common.SEPARATOR)
                painter.drawRect(rect)
                painter.setOpacity(1.0)
                color = common.TEXT_SELECTED

            painter.setBrush(color)
            path = get_painter_path(x, y, font, text)
            painter.drawPath(path)

        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)
        font, metrics = common.font_db.primary_font(
            font_size=common.SMALL_FONT_SIZE())
        it = self.get_text_segments(index).itervalues()
        offset = 0

        left = draw_segments(it, font, metrics, offset)
        left_limit = draw_subdirs(left - common.MARGIN())

        it = self.get_filedetail_text_segments(index).itervalues()
        offset = metrics.ascent()
        font, metrics = common.font_db.primary_font(
            font_size=common.SMALL_FONT_SIZE() * 0.95)
        right_limit = draw_segments(it, font, metrics, offset)
        draw_description(font, metrics, left_limit, right_limit, offset)

    @paintmethod
    def paint_simple_name(self, *args):
        """Paints an the current file-names in a simpler form, with only the
        filename and the description visible.

        """
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args
        painter.setRenderHint(QtGui.QPainter.Antialiasing, on=True)

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + (common.INDICATOR_WIDTH() * 2))

        # File-name
        name_rect = QtCore.QRect(rect)
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(rect.center())
        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        text_segments = self.get_text_segments(index)
        painter.setPen(common.TEXT)
        painter.setBrush(QtCore.Qt.NoBrush)
        font, metrics = common.font_db.primary_font(
            font_size=common.SMALL_FONT_SIZE() * 1.1)

        offset = 0

        o = 0.9 if selected else 0.8
        o = 1.0 if hover else o
        painter.setOpacity(o)
        painter.setPen(QtCore.Qt.NoPen)

        for k in sorted(text_segments, reverse=True):
            text, color = text_segments[k]
            r = QtCore.QRect(name_rect)
            width = metrics.width(text)
            r.setWidth(width)
            r.moveLeft(rect.left() + offset)
            offset += width

            if r.left() > rect.right():
                break
            if r.right() > rect.right():
                r.setRight(rect.right() - (common.INDICATOR_WIDTH()))
                text = metrics.elidedText(
                    text,
                    QtCore.Qt.ElideRight,
                    r.width() - 6
                )

            x = r.center().x() - (metrics.width(text) / 2.0)
            y = r.center().y() + (metrics.ascent() / 2.0)

            painter.setBrush(color)
            path = get_painter_path(x, y, font, text)
            painter.drawPath(path)

        # Description
        if not index.data(common.DescriptionRole):
            return

        font, metrics = common.font_db.secondary_font(
            font_size=common.SMALL_FONT_SIZE() * 1.2)

        description_rect = QtCore.QRect(rect)
        description_rect.setHeight(metrics.height())
        description_rect.moveCenter(rect.center())
        description_rect.moveCenter(
            QtCore.QPoint(description_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )

        painter.setOpacity(1.0)
        color = common.TEXT_SELECTED if selected or hover else common.ADD

        text = index.data(common.DescriptionRole)
        width = metrics.width(text)

        r = QtCore.QRect(description_rect)
        r.setWidth(width)

        if r.left() > rect.right():
            return
        if r.right() > (rect.right()):
            r.setRight(rect.right())
            text = metrics.elidedText(
                text,
                QtCore.Qt.ElideRight,
                r.width() - common.INDICATOR_WIDTH()
            )

        x = r.center().x() - (metrics.width(text) / 2.0)
        y = r.center().y() + (metrics.ascent() / 2.0)

        painter.setBrush(color)
        path = get_painter_path(x, y, font, text)
        painter.drawPath(path)

    def get_simple_description_rectangle(self, rectangles, index):
        if not index.isValid():
            return

        rect = QtCore.QRect(rectangles[DataRect])
        rect.setLeft(rect.left() + (common.INDICATOR_WIDTH() * 2))

        font, metrics = common.font_db.primary_font(common.MEDIUM_FONT_SIZE())

        # File-name
        name_rect = QtCore.QRect(rect)
        name_rect.setHeight(metrics.height())
        name_rect.moveCenter(rect.center())
        if index.data(common.DescriptionRole):
            name_rect.moveCenter(
                QtCore.QPoint(name_rect.center().x(),
                              name_rect.center().y() - (metrics.lineSpacing() / 2.0))
            )

        text_segments = self.get_text_segments(index)
        font, metrics = common.font_db.primary_font(
            font_size=common.SMALL_FONT_SIZE() * 1.1)

        offset = 0
        for k in sorted(text_segments, reverse=True):
            text, _ = text_segments[k]
            r = QtCore.QRect(name_rect)
            width = metrics.width(text)
            r.setWidth(width)
            r.moveLeft(rect.left() + offset)
            offset += width

            if r.left() > rect.right():
                break
            if r.right() > rect.right():
                r.setRight(rect.right() - (common.INDICATOR_WIDTH()))

        font, metrics = common.font_db.secondary_font(
            font_size=common.SMALL_FONT_SIZE() * 1.2)

        description_rect = QtCore.QRect(name_rect)
        description_rect = QtCore.QRect(rect)
        description_rect.setHeight(metrics.height())
        description_rect.moveCenter(rect.center())
        description_rect.moveCenter(
            QtCore.QPoint(description_rect.center().x(),
                          name_rect.center().y() + metrics.lineSpacing())
        )
        return description_rect

    def get_text_segments(self, index):
        """Returns the `FilesWidget` item `DisplayRole` segments associated with
        custom colors. It is used to paint the FilesWidget items' extension,
        name, and sequence.

        Args:
            index (QModelIndex): The index currently being painted.

        Returns:
            dict: A dictionary of tuples. (unicode, QtGui.QColor)

        """
        if not index.isValid():
            return {}
        s = index.data(QtCore.Qt.DisplayRole)
        if not s:
            return {}

        k = index.data(QtCore.Qt.StatusTipRole)
        if k in TEXT_SEGMENT_CACHE:
            return TEXT_SEGMENT_CACHE[k]

        s = regex_remove_version.sub(ur'\1\3', s)
        d = {}
        # Item is a collapsed sequence
        match = common.is_collapsed(s)
        if match:
            # Suffix + extension
            s = match.group(3).split(u'.')
            s = u'.'.join(s[:-1]).upper() + u'.' + s[-1].lower()
            d[len(d)] = (s, common.TEXT)

            # Frame-range without the "[]" characters
            s = match.group(2)
            s = regex_remove_bracket.sub(u'', s)
            if len(s) > 17:
                s = s[0:8] + u'...' + s[-8:]
            if index.data(common.FramesRole) > 1:
                d[len(d)] = (s, common.REMOVE)
            else:
                d[len(d)] = (s, common.TEXT)

            # Filename
            d[len(d)] = (
                match.group(1).upper(), common.TEXT_SELECTED)
            TEXT_SEGMENT_CACHE[k] = d
            return d

        # Item is a non-collapsed sequence
        match = common.get_sequence(s)
        if match:
            # The extension and the suffix
            if match.group(4):
                s = match.group(3).upper() + u'.' + match.group(4).lower()
            else:
                s = match.group(3).upper()
            d[len(d)] = (s, common.TEXT_SELECTED)

            # Sequence
            d[len(d)] = (match.group(
                2).upper(), common.SECONDARY_TEXT)

            # Prefix
            d[len(d)] = (
                match.group(1).upper(), common.TEXT_SELECTED)
            TEXT_SEGMENT_CACHE[k] = d
            return d

        # Items is not collapsed and it isn't a sequence either
        s = s.split(u'.')
        if len(s) > 1:
            s = u'.'.join(s[:-1]).upper() + u'.' + s[-1].lower()
        else:
            s = s[0].upper()
        d[len(d)] = (s, common.TEXT_SELECTED)
        TEXT_SEGMENT_CACHE[k] = d
        return d

    def get_filedetail_text_segments(self, index):
        """Returns the `FilesWidget` item `common.FileDetailsRole` segments
        associated with custom colors.

        Args:
            index (QModelIndex): The index currently being painted.

        Returns:
            dict: A dictionary of tuples "{0: (unicode, QtGui.QColor)}".

        """
        d = {}

        if not index.data(common.FileInfoLoaded):
            d[len(d)] = (u'...', common.SECONDARY_TEXT)
            return d

        text = index.data(common.FileDetailsRole)
        texts = text.split(u';')
        for n, text in enumerate(reversed(texts)):
            d[len(d)] = (text, common.SECONDARY_TEXT)
            if n == (len(texts) - 1) and not index.data(common.DescriptionRole):
                break
            d[len(d)] = (u'  |  ', common.SECONDARY_BACKGROUND)
        return d

    def get_subdir_rectangles(self, index, rectangles, metrics):
        """Returns the available mode rectangles for FileWidget index."""
        arr = []

        o = common.INDICATOR_WIDTH() * 0.5
        rect = QtCore.QRect(rectangles[DataRect])
        rect.setHeight(metrics.height() + (o * 2))
        rect.moveCenter(rectangles[DataRect].center())
        rect.moveLeft(rectangles[DataRect].left())

        subdirs = index.data(common.ParentPathRole)
        if not subdirs:
            return []

        offset = 0
        for n, text in enumerate(subdirs[-1].upper().split(u'/')):
            if not text:
                continue
            if n >= self.maximum_subdirs:
                break
            if len(text) > 36:
                text = text[0:16] + u'...' + text[-17:]
            width = metrics.width(text)
            rect.setWidth(width)
            rect = rect.marginsAdded(QtCore.QMargins(o * 3, 0, o * 3, 0))

            if rect.right() > rectangles[DataRect].right():
                rect.setRight(rectangles[DataRect].right())
            if rect.left() < rectangles[DataRect].left():
                rect.setLeft(rectangles[DataRect].left())

            arr.append((QtCore.QRect(rect), text))
            rect.moveLeft(rect.left() + rect.width() + (o * 5))
        return arr

    @paintmethod
    def paint_drag_source(self, *args, **kwargs):
        """Overlay do indicate the source of a drag operation."""
        rectangles, painter, option, index, selected, focused, active, archived, favourite, hover, font, metrics, cursor_position = args

        if index != self.parent().drag_source_index:
            return
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(option.rect)

        painter.setPen(common.BACKGROUND)
        font, metrics = common.font_db.secondary_font(common.SMALL_FONT_SIZE())
        painter.setFont(font)

        text = '"Drag+Shift" grabs all files    |    "Drag+Alt" grabs the first file    |    "Drag+Shift+Alt" grabs the parent folder'
        painter.drawText(
            option.rect.marginsRemoved(QtCore.QMargins(
                common.MARGIN(), 0, common.MARGIN(), 0)),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
            text,
            boundingRect=option.rect,
        )

    def sizeHint(self, option, index):
        return self.parent().model().sourceModel().ROW_SIZE


class FavouritesWidgetDelegate(FilesWidgetDelegate):

    def get_paint_arguments(self, *args, **kwargs):
        args = super(FavouritesWidgetDelegate, self).get_paint_arguments(*args, **kwargs)
        rects = args[0].copy()
        rects[FavouriteRect] = QtCore.QRect()
        args = list(args)
        args[0] = rects
        return tuple(args)
