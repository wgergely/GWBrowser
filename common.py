# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903
"""Module used to define common variables and methods used across the project.

Global Variables
    The studio wide servers are defined here. These are hard-coded
    variables that will depend on the context the program is usedself.
    Make sure to customize these settings depending on your environment.

    ``ASSET_IDENTIFIER`` is the file needed to be present to understand a folder
    as an ``asset``. At Glassworks we're using the maya project structure so this is
    a ``workspace.mel`` file.

    ``Assets`` are directory structures compartmentalizing data. ``Browser``
    is designed to read and annote ``scene``, ``cache`` (exports) and
    ``render`` files.

    Depending on your setup these folders might have different names you can
    customize them here. ``Browser`` will assume all of these folder reside in the
    root of the ``asset`` folder.


Thumbnails and UI Icon
    The variables and the methods needed to read and cache thumbnail images
    and UI icon are also defined here.

    All cached images are stored in ``IMAGE_CACHE``.
    To add an image to the cache you can use the ``cache_image()`` method.

    Loading and caching ui resource items is done by ``get_rsc_pixmap()``.

"""

import os
import random
import re

from PySide2 import QtGui, QtCore


SERVERS = [
    {'path': '//gordo/jobs', 'nickname': 'Gordo'},
    {'path': '//sloth/jobs', 'nickname': 'Sloth'},
    {'path': '//localhost/c$/temp', 'nickname': 'Local Drive'},
]

ASSET_IDENTIFIER = 'workspace.mel'
"""When with the given name is present in the root of a folder, it will be
considered an ``assets``."""


ExportsFolder = 'exports'
ScenesFolder = 'scenes'
RendersFolder = 'renders'

NameFilters = {
    ExportsFolder: (
        '*.abc', # Alembic
        '*.obj',
        '*.ass', # Arnold cache
    ),
    ScenesFolder: (
        '*.ma',
        '*.mb',
    ),
    RendersFolder: (
        '*.exr',
        '*.png',
        '*.tiff',
        '*.tff',
        '*.jpg',
        '*.jpeg',
        '*.psd',
    ),
}
"""A list of expected file-formats associated with the location."""

# Extending the
PathRole = 1024
"""Role used to store the path of the item."""
ParentRole = 1025
"""Role used to store the paths the item is associated with."""
DescriptionRole = 1026
"""Role used to store the description of the item."""
TodoCountRole = 1027
"""Asset role used to store the number of todos."""
FileDetailsRole = 1028
"""Special role used to save the information string of a file."""
FileModeRole = 1029
"""Role used to save the mode (subfolder) of the current file."""


SortByName = 0
SortByLastModified = 1
SortByLastCreated = 2
SortBySize = 3
"""Item sort flags"""


def sort_alphanum_key(key):
    def _convert(text):
        return int(text) if text.isdigit() else text

    def _split(key):
        return re.split('([0-9]+)', key.filePath())

    return [_convert(f) for f in _split(key)]


def sort_last_modified_key(key):
    return key.lastModified().toMSecsSinceEpoch()


def sort_last_created_key(key):
    return key.created().toMSecsSinceEpoch()


def sort_size_key(key):
    return key.size()


sort_keys = {
    SortByName: sort_alphanum_key,
    SortByLastModified: sort_last_modified_key,
    SortByLastCreated: sort_last_created_key,
    SortBySize: sort_size_key,
}
"""These are the methods/keys used to sort lists."""

# Sizes
MARGIN = 18.0
ROW_HEIGHT = 54.0

BOOKMARK_ROW_HEIGHT = 54.0
ASSET_ROW_HEIGHT = 84.0
FILE_ROW_HEIGHT = 64.0

WIDTH = 640.0
HEIGHT = 480.0

INDICATOR_WIDTH = 6.0
INLINE_ICON_SIZE = 18

ROW_BUTTONS_HEIGHT = 24.0
STACKED_WIDGET_HEIGHT = 640.0
ROW_FOOTER_HEIGHT = 18.0
THUMBNAIL_IMAGE_SIZE = 1024.0

BACKGROUND_SELECTED = QtGui.QColor(128, 128, 128)
SECONDARY_BACKGROUND = QtGui.QColor(80, 80, 80)
BACKGROUND = QtGui.QColor(98, 98, 98)

THUMBNAIL_BACKGROUND_SELECTED = QtGui.QColor(85, 85, 85)
THUMBNAIL_BACKGROUND = QtGui.QColor(80, 80, 80)
THUMBNAIL_IMAGE_BACKGROUND = QtGui.QColor(30, 30, 30)

TEXT = QtGui.QColor(220, 220, 220)
TEXT_SELECTED = QtGui.QColor(255, 255, 255)
TEXT_DISABLED = QtGui.QColor(130, 130, 130)

TEXT_NOTE = QtGui.QColor(150, 150, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)
TEXT_WARNING = SECONDARY_TEXT

SEPARATOR = QtGui.QColor(58, 58, 58)

SELECTION = QtGui.QColor(100, 161, 255)
FAVOURITE = QtGui.QColor(140, 120, 233)
ARCHIVED_OVERLAY = QtGui.QColor(68, 68, 68, 150)

PRIMARY_FONT = 0
SECONDARY_FONT = 1
TERCIARY_FONT = 2


def move_widget_to_available_geo(widget):
    """Moves the widget inside the available screen geomtery, if any of the edges
    fall outside.

    """
    app = QtCore.QCoreApplication.instance()
    if widget.parentWidget():
        screenID = app.desktop().screenNumber(widget.parentWidget())
    else:
        screenID = app.desktop().primaryScreen()

    screen = app.screens()[screenID]
    screen_rect = screen.availableGeometry()

    # Widget's rectangle in the global screen space
    rect = QtCore.QRect()
    topLeft = widget.mapToGlobal(widget.rect().topLeft())
    rect.setTopLeft(topLeft)
    rect.setWidth(widget.rect().width())
    rect.setHeight(widget.rect().height())

    x = rect.x()
    y = rect.y()

    if rect.left() < screen_rect.left():
        x = screen_rect.x()
    if rect.top() < screen_rect.top():
        y = screen_rect.y()
    if rect.right() > screen_rect.right():
        x = screen_rect.right() - rect.width()
    if rect.bottom() > screen_rect.bottom():
        y = screen_rect.bottom() - rect.height()

    widget.move(x, y)


def _add_custom_fonts():
    """Adds custom fonts to the application."""

    d = QtCore.QDir(
        '{}/rsc/fonts'.format(
            QtCore.QFileInfo(__file__).dir().path()
        )
    )
    d.setNameFilters(['*.ttf', ])

    font_families = []
    for f in d.entryInfoList(
        QtCore.QDir.Files |
        QtCore.QDir.NoDotAndDotDot
    ):
        idx = QtGui.QFontDatabase().addApplicationFont(f.filePath())
        font_families.append(
            QtGui.QFontDatabase().applicationFontFamilies(idx)[0])


def set_custom_stylesheet(widget):
    """Applies the custom stylesheet to the given widget."""
    _add_custom_fonts()

    path = os.path.normpath(
        os.path.abspath(
            os.path.join(
                __file__,
                os.pardir,
                'rsc',
                'customStylesheet.css'
            )
        )
    )

    with open(path, 'r') as f:
        f.seek(0)
        qss = f.read()
        qss = qss.encode(encoding='UTF-8', errors='strict')
        qss = qss.format(
            fontFamily='Roboto Medium',
            fontSize=9,
            BACKGROUND='{},{},{},{}'.format(*BACKGROUND.getRgb()),
            BACKGROUND_SELECTED='{},{},{},{}'.format(
                *BACKGROUND_SELECTED.getRgb()),
            SECONDARY_BACKGROUND='{},{},{},{}'.format(
                *SECONDARY_BACKGROUND.getRgb()),
            TEXT='{},{},{},{}'.format(*TEXT.getRgb()),
            SECONDARY_TEXT='{},{},{},{}'.format(*SECONDARY_TEXT.getRgb()),
            TEXT_DISABLED='{},{},{},{}'.format(*TEXT_DISABLED.getRgb()),
            TEXT_SELECTED='{},{},{},{}'.format(*TEXT_SELECTED.getRgb()),
            SEPARATOR='{},{},{},{}'.format(*SEPARATOR.getRgb()),
            FAVOURITE='{},{},{},{}'.format(*FAVOURITE.getRgb()),
            SELECTION='{},{},{},{}'.format(*SELECTION.getRgb())
        )
        widget.setStyleSheet(qss)


def cache_image(path, height, overwrite=False):
    """Saves the image at the path to the image cache. The cached images are
    stored in the IMAGE_CACHE dictionary.

    If the loading the image fails, we'll use an empty image.

    We're also saving an average of colour to be used as the background when the
    image is not square.

    Args:
        path (str):    Path to the image file.
        height (int):  Description of parameter `height`.

    Returns:
        type: Description of returned object.

    """
    height = int(height)
    path = QtCore.QFileInfo(path)
    path = path.filePath()

    k = '{path}:{height}'.format(
        path=path,
        height=height
    )
    if k in IMAGE_CACHE and not overwrite:
        return IMAGE_CACHE[k]

    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        ppath = QtCore.QFileInfo('{}/../rsc/placeholder.png'.format(__file__))
        ppath = ppath.filePath()
        placeholder_k = '{path}:{height}'.format(
            path=ppath,
            height=height
        )
        if placeholder_k in IMAGE_CACHE:
            IMAGE_CACHE[k] = IMAGE_CACHE[placeholder_k]
            return IMAGE_CACHE[k]

    image = QtGui.QImage()
    image.load(file_info.filePath())

    # If the load fails, use the placeholder image
    image = resize_image(
        image,
        height
    )

    # Average colour
    IMAGE_CACHE[k] = image
    IMAGE_CACHE['{path}:BackgroundColor'.format(
        path=path
    )] = get_color_average(image)


def cache_placeholder(height):
    path = QtCore.QFileInfo('{}/../rsc/placeholder.png'.format(__file__))
    path = path.filePath()
    height = int(height)
    k = '{path}:{height}'.format(
        path=path,
        height=height
    )
    if k in IMAGE_CACHE:
        return IMAGE_CACHE[k]
    file_info = QtCore.QFileInfo(
        '{}/../rsc/placeholder.png'.format(__file__))
    image = QtGui.QImage()
    image.load(file_info.filePath())

    # If the load fails, use the placeholder image
    image = resize_image(
        image,
        height
    )

    # Average colour
    IMAGE_CACHE[k] = image
    IMAGE_CACHE['{path}:BackgroundColor'.format(
        path=path
    )] = get_color_average(image)


def delete_image(path, delete_file=True):
    """Deletes the given file and the associated cached data.

    Args:
        path (type): Path to the image file.

    """
    file_ = QtCore.QFile(path)

    if file_.exists() and delete_file:
        file_.remove()

    keys = [k for k in IMAGE_CACHE if path.lower() in k.lower()]
    for k in keys:
        del IMAGE_CACHE[k]


def label_generator():
    """Generates QColors from an array of RGB values.

    Example:

    .. code-block:: python
        :linenos:

        LABEL_COLORS = label_generator()
        next(LABEL_COLORS)

    Yields:         QtCore.QColor

    """
    arr = []
    for n in xrange(999):
        a = [120, 60, 150] if n % 2 == 0 else [150, 60, 120]
        v = 20
        arr.append([
            random.randint(max(a[0] - v, 0), min(a[0] + v, 255)),
            random.randint(max(a[1] - (v / 3), 0), min(a[1] + (v / 3), 255)),
            random.randint(max(a[2] - v, 0), min(a[2] + v, 255))
        ])
    for color in arr:
        yield QtGui.QColor(*color)


def get_label(k):
    """Returns the QColor for the given key.

    Args:
        k (str):    The key, eg. the name of a folder.

    Raises:         StopIterationrError: When out of labels.
    Returns:        QColor.

    """
    global LABEL_COLORS
    if k.lower() not in ASSIGNED_LABELS:
        ASSIGNED_LABELS[k.lower()] = next(LABEL_COLORS)
    return ASSIGNED_LABELS[k.lower()]


def revert_labels():
    global LABEL_COLORS
    global ASSIGNED_LABELS
    ASSIGNED_LABELS = {}
    LABEL_COLORS = label_generator()


def resize_image(image, size):
    """Returns a scaled copy of the image fitting inside the square of ``size``.

    Args:
        image (QImage): The image to rescale.
        size (int): The width/height of the square.

    Returns:
        QImage: The resized copy of the original image.

    """
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


def get_color_average(image):
    """Returns the average color of an image."""
    r = []
    g = []
    b = []
    for x in xrange(image.width()):
        for y in xrange(image.height()):
            r.append(image.pixelColor(x, y).red())
            g.append(image.pixelColor(x, y).green())
            b.append(image.pixelColor(x, y).blue())
    average_color = QtGui.QColor(
        sum(r) / float(len(r)),
        sum(g) / float(len(g)),
        sum(b) / float(len(b))
    )
    return average_color


def get_rsc_pixmap(name, color, size, opacity=1.0):
    """Loads a rescoure image and returns it as a re-sized and coloured QPixmap.

    Args:
        name (str): Name of the resource without the extension.
        color (QColor): The colour of the icon.
        size (int): The size of pixmap.

    Returns:
        QPixmap: The loaded image

    """
    k = '{name}:{size}:{color}'.format(
        name=name, size=size, color=color.name())

    if k in IMAGE_CACHE:
        return IMAGE_CACHE[k]

    file_info = QtCore.QFileInfo('{}/../rsc/{}.png'.format(__file__, name))
    if not file_info.exists():
        return QtGui.QPixmap()

    image = QtGui.QImage()
    image.load(file_info.filePath())

    if image.isNull():
        return QtGui.QPixmap()

    painter = QtGui.QPainter()
    painter.begin(image)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    painter.setBrush(QtGui.QBrush(color))
    painter.drawRect(image.rect())
    painter.end()

    image = resize_image(image, size)
    pixmap = QtGui.QPixmap()
    pixmap.convertFromImage(image)

    # Setting transparency
    if opacity < 1.0:
        image = QtGui.QImage(
            pixmap.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        image.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(image)
        painter.setOpacity(opacity)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)

    IMAGE_CACHE[k] = pixmap
    return IMAGE_CACHE[k]


def count_assets(path):
    """Returns the number of assets inside the given folder."""
    dir_ = QtCore.QDir(path)
    dir_.setFilter(
        QtCore.QDir.NoDotAndDotDot |
        QtCore.QDir.Dirs |
        QtCore.QDir.NoSymLinks |
        QtCore.QDir.Readable
    )

    # Counting the number assets found
    count = 0
    for file_info in dir_.entryInfoList():
        dir_ = QtCore.QDir(file_info.filePath())
        dir_.setFilter(QtCore.QDir.Files)
        dir_.setNameFilters((ASSET_IDENTIFIER,))
        if dir_.entryInfoList():
            count += 1
    return count


def byte_to_string(num, suffix='B'):
    """Converts a numeric byte-value to a human readable string."""
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def reveal(path):
    """Reveals the specified folder in the file explorer.

    Args:
        name (str): A relative path or the folder's name.

    """
    url = QtCore.QUrl.fromLocalFile(path)
    QtGui.QDesktopServices.openUrl(url)


NoHighlightFlag = 0b000000
HeadingHighlight = 0b000001
QuoteHighlight = 0b000010
CodeHighlight = 0b000100
BoldHighlight = 0b001000
ItalicHighlight = 0b010000

HIGHLIGHT_RULES = {
    # Should yield 3 groups:
    # group 1 = the file:// prefix if exists,
    # group 2 = the //path or \\path
    # group 3 = trailing space
    'file_path': {
        're': re.compile(r'([a-z]{2,4}:)?([\/\\]{2}[^\"\*\<\>\?\|]+\.[a-z0-9]{2,4})[\s\t\n\r]*', flags=re.IGNORECASE),
        'flag': CodeHighlight
    },
    'folder_path': {
        're': re.compile(r'([a-z]{2,4}:)?([\/\\]{2}[^\"\*\<\>\?\|\s]+)', flags=re.IGNORECASE),
        'flag': CodeHighlight
    },
    'quotes': {
        're': re.compile(r'([\"\']+[^\"\']+[\'\"]+)', flags=re.IGNORECASE),
        'flag': CodeHighlight
    },
    'bold': {
        're': re.compile(r'(\*{2}|_{2})([^\*_]+)(\*{2}|_{2})', flags=re.IGNORECASE),
        'flag': BoldHighlight
    },
    'italicized': {
        're': re.compile(r'([\*_]{1})([^\*_]+)([\*_]{1})', flags=re.IGNORECASE),
        'flag': ItalicHighlight
    },
    'heading': {
        're': re.compile(r'^([#]{1,6})', flags=re.IGNORECASE),
        'flag': HeadingHighlight
    },
    'quote': {
        're': re.compile(r'^([>]{1})', flags=re.IGNORECASE),
        'flag': QuoteHighlight
    },
}


def get_ranges(arr, padding):
    """Examines a sequence of numbers and returnsa string representation."""
    arr = list(set(sorted(arr)))
    start = arr[0]
    end = 0
    block = []
    for idx, n in enumerate(arr):
        zfill = '{}'.format(n).zfill(padding)

        start = n if n < start else start
        end = end if n < end else n

        if len(arr) > (idx + 1):
            if arr[idx + 1] != n + 1:
                if zfill not in block:
                    block.append(zfill)
                    block.append(',')

        if idx > 0:
            if arr[idx - 1] != n - 1:
                if zfill not in block:
                    block.append(zfill)
                    block.append('-')
    if start == end:
        return '{}'.format(start).zfill(padding)
    block.insert(0, '{}'.format(start).zfill(padding))
    block.insert(1, '-')
    block.append('{}'.format(end).zfill(padding))
    return ''.join(block)


# Label LABEL_COLORS
ASSIGNED_LABELS = {}
# Thumbnail cache
IMAGE_CACHE = {}

# Property contains all the saVed label LABEL_COLORS
LABEL_COLORS = label_generator()
#
cache_placeholder(FILE_ROW_HEIGHT)
cache_placeholder(ASSET_ROW_HEIGHT)
cache_placeholder(BOOKMARK_ROW_HEIGHT)
