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
    {u'path': u'//gordo/jobs', u'nickname': u'Gordo'},
    {u'path': u'//sloth/jobs', u'nickname': u'Sloth'},
    {u'path': u'//localhost/c$/temp', u'nickname': u'Local Drive'},
]

ASSET_IDENTIFIER = u'workspace.mel'
"""When with the given name is present in the root of a folder, it will be
considered an ``assets``."""


ExportsFolder = u'exports'
ScenesFolder = u'scenes'
RendersFolder = u'renders'
TexturesFolder = u'textures'

NameFilters = {
    ExportsFolder: (
        u'*.abc',  # Alembic
        u'*.obj',
        u'*.ass',  # Arnold cache
    ),
    ScenesFolder: (
        u'*.psd',  # 2D Animation
        u'*.ma',  # Maya ASCII
        u'*.mb',  # Maya Binary
        u'*.c4d',  # Cinema 4D
        u'*.hud',  # Houdini
        u'*.aep',  # After-Effects
        u'*.nk',  # Nuke
    ),
    RendersFolder: (
        u'*.exr',
        u'*.png',
        u'*.tiff',
        u'*.tff',
        u'*.jpg',
        u'*.jpeg',
        u'*.psd',
        u'*.dpx',
        u'*.tga',
        u'*.psd',
    ),
    TexturesFolder: (
        u'*.exr',
        u'*.tx',
        u'*.dpx',
        u'*.png',
        u'*.tiff',
        u'*.tff',
        u'*.jpg',
        u'*.jpeg',
        u'*.psd',
    ),
}
"""A list of expected file-formats associated with the location."""

# Extending the
FlagsRole = 1024
"""Role used to store the path of the item."""
ParentRole = 1026
"""Role used to store the paths the item is associated with."""
DescriptionRole = 1027
"""Role used to store the description of the item."""
TodoCountRole = 1028
"""Asset role used to store the number of todos."""
FileDetailsRole = 1029
"""Special role used to save the information string of a file."""


SortByName = 0
SortByLastModified = 1
SortByLastCreated = 2
SortBySize = 3
"""Item sort flags"""

LowerCase = 0
UpperCase = 1
"""Filename styles"""


def sort_alphanum_key(key):
    def _convert(text):
        return int(text) if text.isdigit() else text

    def _split(key):
        return re.split(r'([0-9]+)', key.filePath())

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
ROW_HEIGHT = 54.0
BOOKMARK_ROW_HEIGHT = 54.0
ASSET_ROW_HEIGHT = 84.0

MARGIN = 18.0

INDICATOR_WIDTH = 4.0
ROW_BUTTONS_HEIGHT = 36.0

WIDTH = 640.0
HEIGHT = 480.0

INLINE_ICON_SIZE = 18.0
THUMBNAIL_IMAGE_SIZE = 1024.0

BACKGROUND_SELECTED = QtGui.QColor(125, 125, 125)
SECONDARY_BACKGROUND = QtGui.QColor(80, 80, 80)
BACKGROUND = QtGui.QColor(98, 98, 98)

TEXT = QtGui.QColor(220, 220, 220)
TEXT_SELECTED = QtGui.QColor(250, 250, 250)
TEXT_DISABLED = QtGui.QColor(140, 140, 140)

TEXT_NOTE = QtGui.QColor(150, 150, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)

SEPARATOR = QtGui.QColor(50, 50, 50)
SELECTION = QtGui.QColor(100, 161, 255)
FAVOURITE = QtGui.QColor(140, 120, 233)


PrimaryFont = QtGui.QFont(u'Roboto Black')
PrimaryFont.setPointSize(9)
SecondaryFont = QtGui.QFont(u'Roboto Medium')
SecondaryFont.setPointSize(8)


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
        u'{}/rsc/fonts'.format(
            QtCore.QFileInfo(__file__).dir().path()
        )
    )
    d.setNameFilters([u'*.ttf', ])

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
                u'rsc',
                u'customStylesheet.css'
            )
        )
    )

    with open(path, 'r') as f:
        f.seek(0)
        qss = f.read()
        qss = qss.encode(encoding='UTF-8', errors='strict')
        qss = qss.format(
            fontFamily=PrimaryFont.family(),
            fontSize=9,
            BACKGROUND=u'{},{},{},{}'.format(*BACKGROUND.getRgb()),
            BACKGROUND_SELECTED=u'{},{},{},{}'.format(
                *BACKGROUND_SELECTED.getRgb()),
            SECONDARY_BACKGROUND=u'{},{},{},{}'.format(
                *SECONDARY_BACKGROUND.getRgb()),
            TEXT=u'{},{},{},{}'.format(*TEXT.getRgb()),
            SECONDARY_TEXT=u'{},{},{},{}'.format(*SECONDARY_TEXT.getRgb()),
            TEXT_DISABLED=u'{},{},{},{}'.format(*TEXT_DISABLED.getRgb()),
            TEXT_SELECTED=u'{},{},{},{}'.format(*TEXT_SELECTED.getRgb()),
            SEPARATOR=u'{},{},{},{}'.format(*SEPARATOR.getRgb()),
            FAVOURITE=u'{},{},{},{}'.format(*FAVOURITE.getRgb()),
            SELECTION=u'{},{},{},{}'.format(*SELECTION.getRgb())
        )
        widget.setStyleSheet(qss)


def cache_placeholder(path, k, height):
    ppath = QtCore.QFileInfo(u'{}/../rsc/placeholder.png'.format(__file__))
    ppath = ppath.absoluteFilePath()
    placeholder_k = u'{path}:{height}'.format(
        path=ppath,
        height=height
    )
    if placeholder_k in IMAGE_CACHE:
        IMAGE_CACHE[k] = IMAGE_CACHE[placeholder_k]
    else:
        IMAGE_CACHE[k] = _cache_placeholder(height)
    IMAGE_CACHE[u'{}:BackgroundColor'.format(
        path)] = IMAGE_CACHE[u'{}:BackgroundColor'.format(ppath)]
    return IMAGE_CACHE[k]


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

    k = u'{path}:{height}'.format(
        path=path,
        height=height
    )
    if k in IMAGE_CACHE and not overwrite:
        return IMAGE_CACHE[k]

    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return cache_placeholder(path, k, height)

    image = QtGui.QImage()
    image.load(file_info.filePath())
    if image.isNull():
        return cache_placeholder(path, k, height)

    image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
    image = resize_image(image, height)

    # Average colour
    IMAGE_CACHE[u'{path}:BackgroundColor'.format(
        path=path
    )] = get_color_average(image)
    IMAGE_CACHE[k] = image
    return IMAGE_CACHE[k]


def _cache_placeholder(height):
    height = int(height)
    path = QtCore.QFileInfo(u'{}/../rsc/placeholder.png'.format(__file__))
    path = path.absoluteFilePath()

    k = u'{path}:{height}'.format(
        path=path,
        height=height
    )

    if k in IMAGE_CACHE:
        return IMAGE_CACHE[k]

    file_info = QtCore.QFileInfo(
        u'{}/../rsc/placeholder.png'.format(__file__))
    image = QtGui.QImage()
    image.load(file_info.filePath())
    image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)

    # If the load fails, use the placeholder image
    image = resize_image(
        image,
        height
    )

    # Average colour
    IMAGE_CACHE[k] = image
    IMAGE_CACHE[u'{path}:BackgroundColor'.format(
        path=path
    )] = QtGui.QColor(0, 0, 0, 0)
    return IMAGE_CACHE[k]


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
        if ':' in k:
            elem = k.split(':')[-1]
            if 'BackgroundColor' in elem:
                IMAGE_CACHE[k] = QtGui.QColor(0,0,0,0)
            else:
                cache_placeholder(path, k, int(elem))
        # del IMAGE_CACHE[k]


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
            if image.pixelColor(x, y).alpha() < 0.01:
                continue
            r.append(image.pixelColor(x, y).red())
            g.append(image.pixelColor(x, y).green())
            b.append(image.pixelColor(x, y).blue())

    if not all([float(len(r)), float(len(g)), float(len(b))]):
        average_color = QtGui.QColor(SECONDARY_BACKGROUND)
    else:
        average_color = QtGui.QColor(
            sum(r) / float(len(r)),
            sum(g) / float(len(g)),
            sum(b) / float(len(b))
        )
    average_color.setAlpha(average_color.alpha() / 2.0)
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

    k = u'{name}:{size}:{color}'.format(
        name=name, size=size, color=u'null' if not color else color.name())

    if k in IMAGE_CACHE:
        return IMAGE_CACHE[k]

    file_info = QtCore.QFileInfo(u'{}/../rsc/{}.png'.format(__file__, name))
    if not file_info.exists():
        return QtGui.QPixmap()

    image = QtGui.QImage()
    image.load(file_info.filePath())

    if image.isNull():
        return QtGui.QPixmap()

    image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
    if color is not None:
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

        painter = QtGui.QPainter()
        painter.begin(image)
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


def byte_to_string(num, suffix=u'B'):
    """Converts a numeric byte-value to a human readable string."""
    for unit in [u'', u'K', u'M', u'G', u'T', u'P', u'E', u'Z']:
        if abs(num) < 1024.0:
            return u"%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return u"%.1f%s%s" % (num, u'Yi', suffix)


def reveal(path):
    """Reveals the specified folder in the file explorer.

    Args:
        name (str): A path to the file.

    """
    path = get_sequence_endpath(path)
    if QtCore.QSysInfo().productType() in (u'windows', u'winrt'):
        args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        return QtCore.QProcess.startDetached(u'explorer', args)
    if QtCore.QSysInfo().productType() == u'osx':
        args = [u'-e', u'tell application "Finder"', u'-e', u'activate', u'-e', u'select POSIX file "{}"'.format(
                QtCore.QDir.toNativeSeparators(path)), u'-e', u'end tell']
        return QtCore.QProcess.startDetached(u'osascript', args)
    else:
        raise NotImplementedError('{} os has not been implemented.'.format(QtCore.QSysInfo().productType()))


NoHighlightFlag = 0b000000
HeadingHighlight = 0b000001
QuoteHighlight = 0b000010
CodeHighlight = 0b000100
BoldHighlight = 0b001000
ItalicHighlight = 0b010000

HIGHLIGHT_RULES = {
    u'spaces': {
        u're': re.compile(r'([\s\t\n\r]*)', flags=re.IGNORECASE),
        u'flag': CodeHighlight
    },
    u'file_path': {
        u're': re.compile(r'([a-z]{2,5}:)?([\/\\]{2}[^\"\*\<\>\?\|]+\.[a-z0-9]{2,4})[\s\t\n\r]*', flags=re.IGNORECASE),
        u'flag': CodeHighlight
    },
    u'folder_path': {
        u're': re.compile(r'([a-z]{2,5}:)?([\/\\]{2}[^\"\*\<\>\?\|\s]+)', flags=re.IGNORECASE),
        u'flag': CodeHighlight
    },
    u'quotes': {
        u're': re.compile(r'([\"\']+[^\"\']+[\'\"]+)', flags=re.IGNORECASE),
        u'flag': CodeHighlight
    },
    u'bold': {
        u're': re.compile(r'(\*{2}|_{2})([^\*_]+)(\*{2}|_{2})', flags=re.IGNORECASE),
        u'flag': BoldHighlight
    },
    u'italicized': {
        u're': re.compile(r'([\*_]{1})([^\*_]+)([\*_]{1})', flags=re.IGNORECASE),
        u'flag': ItalicHighlight
    },
    u'heading': {
        u're': re.compile(r'^([#]{1,6})', flags=re.IGNORECASE),
        u'flag': HeadingHighlight
    },
    u'quote': {
        u're': re.compile(r'^([>]{1})', flags=re.IGNORECASE),
        u'flag': QuoteHighlight
    },
}

# def convertToHtml(text)


def get_ranges(arr, padding):
    """Examines a sequence of numbers and returnsa string representation."""
    arr = sorted(list(set(arr)))
    blocks = {}
    k = 0
    for idx, n in enumerate(arr):  # blocks
        zfill = u'{}'.format(n).zfill(padding)

        if k not in blocks:
            blocks[k] = []
        blocks[k].append(zfill)

        if idx + 1 != len(arr):
            if arr[idx + 1] != n + 1:  # break coming up
                k += 1
    return u','.join(['-'.join(sorted(list(set([blocks[k][0], blocks[k][-1]])))) for k in blocks])


def get_valid_filename(text):
    return ValidFilenameRegex.search(text)


ValidFilenameRegex = re.compile(
    r'\/([^_]{1,3})_([^_]{1,12})_([^_]{1,12})_(.{1,25})_([0-9]{3})_([^_]{1,})\.(.*)$', flags=re.IGNORECASE)
IsSequenceRegex = re.compile(r'^(.+?)(\[.*\])(.*)$', flags=re.IGNORECASE)
SequenceStartRegex = re.compile(
    r'^(.*)\[([0-9]+).*\](.*)$', flags=re.IGNORECASE)
SequenceEndRegex = re.compile(
    r'^(.*)\[.*?([0-9]+)\](.*)$', flags=re.IGNORECASE)
# If a string denotes a sequence the match should return 4 groups:
# $1[#]$3.$4  # beginning of string, sequence number, string following the sequence number, extension (without the '.')
GetSequenceRegex = re.compile(
    r'^(.*?)([0-9]+)([0-9\\/]*|[^0-9\\/]*(?=.+?))\.([^\.]{2,5})$', flags=re.IGNORECASE)


def get_sequence(text):
    """Returs the number to increment of a filename."""
    return GetSequenceRegex.search(text)


def is_collapsed(text):
    """Checks if the given path is collapsed."""
    return IsSequenceRegex.search(text)


def get_sequence_startpath(path):
    """Checks the given string and if it denotes a seuqence returns the path for
    the first item.
    """
    if not is_collapsed(path):
        return path

    match = SequenceStartRegex.search(path)
    if match:
        path = SequenceStartRegex.sub(r'\1\2\3', path)
    return path


def get_sequence_endpath(path):
    """Checks the given string and if it denotes a seuqence returns the path for
    the first item.
    """
    if not is_collapsed(path):
        return path

    match = SequenceEndRegex.search(path)
    if match:
        path = SequenceEndRegex.sub(r'\1\2\3', path)
    return path


def draw_aliased_text(painter, font, rect, text, align, color):
    """Method to draw aliased text windows, where the default antialiasing fails."""
    painter.save()

    x, y = (rect.left(), rect.top())
    elide = None
    metrics = QtGui.QFontMetrics(font)

    x = rect.left()
    y = rect.center().y() + (metrics.ascent() / 2.0)
    elide = QtCore.Qt.ElideLeft

    if QtCore.Qt.AlignLeft & align:
        elide = QtCore.Qt.ElideRight
    if QtCore.Qt.AlignRight & align:
        elide = QtCore.Qt.ElideLeft
    if QtCore.Qt.AlignHCenter & align:
        elide = QtCore.Qt.ElideMiddle

    text = metrics.elidedText(
        text,
        elide,
        rect.width())

    if QtCore.Qt.AlignLeft & align:
        x = rect.left()
    if QtCore.Qt.AlignRight & align:
        x = rect.right() - metrics.width(text)
    if QtCore.Qt.AlignHCenter & align:
        x = rect.left() + (rect.width() / 2.0) - (metrics.width(text) / 2.0)

    if QtCore.Qt.AlignTop & align:
        y = rect.top() + metrics.ascent()
    if QtCore.Qt.AlignVCenter & align:
        y = rect.center().y() + (metrics.ascent() / 2.0)
    if QtCore.Qt.AlignBottom & align:
        y = rect.bottom() - metrics.descent()

    # Making sure text fits the rectangle
    painter.setBrush(color)
    painter.setPen(QtCore.Qt.NoPen)

    path = QtGui.QPainterPath()
    path.addText(x, y, font, text)
    painter.drawPath(path)

    painter.restore()

class QSingleton(type(QtCore.QObject)):
    """Singleton metaclass for QWidgets.
    # WARNING: DONT USE, kills plugin-reload in Maya.
    Note:
        We have to supply an appropiate type object as the baseclass,
        'type' won't work. Creating type(QtWidgets.QWidget) seems to function.

    """
    _instances = {}

    def __call__(cls, *args, **kwargs):  # pylint: disable=E0213
        if cls not in cls._instances:
            cls._instances[cls] = super(
                QSingleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]



# Label LABEL_COLORS
ASSIGNED_LABELS = {}
# Thumbnail cache
IMAGE_CACHE = {}

# Property contains all the saVed label LABEL_COLORS
LABEL_COLORS = label_generator()
#
