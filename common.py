# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903


"""Module for defining common variables and methods across the project.

Defines the default sizes for widgets and the default colour template.
It also contains the methods used to set our custom stylesheet.

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
"""Default values for the server have to be hard-coded.
Make sure to customize these settings depending on your environment."""

ASSET_IDENTIFIER = 'workspace.mel'
"""When with the given name is present in the root of a folder, it will be
considered an ``assets``."""

ASSET_FOLDERS = {
    'exports': 'exports',
    'scenes': 'scenes',
    'renders': 'renders'
}
"""``Assets`` are directory structures compartmentalizing data. ``Browser``
is designed to read and annote ``scene``, ``cache`` (exports) and
``rendere`` files.

Depending on your setup these folder might have different names you can
customize here. Browser will assume all of these folder reside in the root of
the ``asset`` folder.
"""

# Extending the
PathRole = 0x02000  # Role used to store FileInfo items
"""Special role used to store QFileInfo objects."""
DescriptionRole = 0x03000  # Role used to store FileInfo items
"""Special role used to store QFileInfo objects."""
TodoCountRole = 0x04000  # Role used to store FileInfo items
"""Special role used to store the count of todos."""
FileDetailsRole = 0x05000  # Role used to store FileInfo items
"""Special role used to store the count of todos."""
FileModeRole = 0x06000  # Role used to store FileInfo items
"""Special role used to store the count of todos."""


"""Item sorting flags"""
SortByName = 0
SortByLastModified = 1
SortByLastCreated = 2
SortBySize = 3


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

# Sizes
MARGIN = 18.0
ROW_HEIGHT = 54.0

BOOKMARK_ROW_HEIGHT = 54.0
ASSET_ROW_HEIGHT = 84.0
FILE_ROW_HEIGHT = 72.0

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
THUMBNAIL_BACKGROUND = QtGui.QColor(77, 77, 77)
THUMBNAIL_IMAGE_BACKGROUND = QtGui.QColor(30, 30, 30)

TEXT = QtGui.QColor(220, 220, 220)
TEXT_SELECTED = QtGui.QColor(255, 255, 255)
TEXT_DISABLED = QtGui.QColor(130, 130, 130)

TEXT_NOTE = QtGui.QColor(150, 150, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)
TEXT_WARNING = SECONDARY_TEXT

SEPARATOR = QtGui.QColor(58, 58, 58)

SELECTION = QtGui.QColor(100, 161, 255)
FAVOURITE = QtGui.QColor(233, 89, 92)
ARCHIVED_OVERLAY = QtGui.QColor(68, 68, 68, 150)

PRIMARY_FONT = 0
SECONDARY_FONT = 1
TERCIARY_FONT = 2


def get_thumbnail_pixmap(path, opacity=1.0, size=(ROW_BUTTONS_HEIGHT)):
    """Loads the given file as a QPixmap.


    Args:
        path (str):        The path to the image-file to load.
        opacity (float):   Transparency value between 1.0 and 0.0.
        size (int):        Size of the image.

    Returns:
        QPixmap: The loaded image as a QPixmap.

    """
    file_ = QtCore.QFileInfo(path)
    if not file_.exists():
        return QtGui.QPixmap()

    image = QtGui.QImage()
    image.load(file_.filePath())

    if image.isNull():
        return QtGui.QPixmap()

    image = resize_image(image, size)
    pixmap = QtGui.QPixmap()
    pixmap.convertFromImage(image)

    # Setting transparency
    image = QtGui.QImage(
        pixmap.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(image)
    painter.setOpacity(opacity)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    pixmap = QtGui.QPixmap()
    pixmap.convertFromImage(image)

    return pixmap


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
            fontFamily='Roboto',
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
            SELECTION='{},{},{},{}'.format(*SELECTION.getRgb())
        )
        widget.setStyleSheet(qss)



# Label colors
ASSIGNED_LABELS = {}
# Thumbnail cache
IMAGE_CACHE = {}


def cache_image(path, height, overwrite=False):
    """Saves the image at the path to the image cache. The cached images are
    stored in the IMAGE_CACHE dictionary.

    If the loading the image fails, we'll automatically use

    We're also saving an average of colour to be used as the background when the
    image is not squarical.

    Args:
        path (str):    Path to the image file.
        height (int):  Description of parameter `height`.

    Returns:
        type: Description of returned object.

    """
    path = QtCore.QFileInfo(path)
    path = path.filePath()

    k = '{path}:{height}'.format(
        path=path,
        height=height
    )

    if k in IMAGE_CACHE and not overwrite:
        return

    image = QtGui.QImage()
    image.load(path)

    # If the load fails, use the placeholder image
    if image.isNull():
        image.load(PLACEHOLDER)
        image = resize_image(
            image,
            height
        )
    else:
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

        colors = label_generator()
        next(colors)

    Yields:         QtCore.QColor

    """
    arr = []
    for n in xrange(999):
        if n % 2 == 0:
            a = [190, 89, 92]
        else:
            a = [92, 89, 190]
        v = 15
        arr.append([
            random.randint(a[0] - v, a[0] + v),
            random.randint(a[1] - v, a[1] + v),
            random.randint(a[2] - v, a[2] + v)
        ])
    for color in arr:
        yield QtGui.QColor(*color)


colors = label_generator()


def get_label(k):
    """Returns the QColor for the given key.

    Args:
        k (str):    The key, eg. the name of a folder.

    Raises:         StopIterationrError: When out of labels.
    Returns:        QColor.

    """
    global colors
    if k.lower() not in ASSIGNED_LABELS:
        ASSIGNED_LABELS[k.lower()] = next(colors)
    return ASSIGNED_LABELS[k.lower()]


def revert_labels():
    global colors
    global ASSIGNED_LABELS
    ASSIGNED_LABELS = {}
    colors = label_generator()


def _custom_thumbnail():
    """The path to the custom thumbnail."""
    return os.path.join(
        __file__,
        os.pardir,
        'thumbnails/custom_thumbnail.png'
    )


def _maya_thumbnail():
    """The path to the custom thumbnail."""
    return os.path.join(
        __file__,
        os.pardir,
        'thumbnails/maya.png'
    )


CUSTOM_THUMBNAIL = _custom_thumbnail()
PLACEHOLDER = _maya_thumbnail()


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


def get_rsc_pixmap(name, color, size):
    """Loads a rescoure image and returns it as a re-sized and coloured QPixmap.

    Args:
        name (str): Name of the resource without the extension.
        color (QColor): The colour of the icon.
        size (int): The size of pixmap.

    Returns:
        QPixmap: The loaded image

    """
    path = QtCore.QFileInfo(__file__)
    path = path.dir()
    path = '{}/rsc/{}.png'.format(path.path(), name)

    file_ = QtCore.QFileInfo(path)
    if not file_.exists():
        return QtGui.QPixmap()

    image = QtGui.QImage(file_.filePath())
    image.load(path)

    if image.isNull():
        return QtGui.QPixmap()

    k = '{name}:{size}:{color}'.format(
        name=name, size=size, color=color.name())
    if k in IMAGE_CACHE:
        return IMAGE_CACHE[k]

    painter = QtGui.QPainter()
    painter.begin(image)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    painter.setBrush(QtGui.QBrush(color))
    painter.drawRect(image.rect())
    painter.end()

    image = resize_image(image, size)
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
    """Reveal the given path in the file manager."""
    url = QtCore.QUrl.fromLocalFile(path)
    QtGui.QDesktopServices.openUrl(url)


class LocalContext(object):
    """Calls to the unavailable methods are directed here when not loading from Maya."""

    def __init__(self, *args, **kwargs):
        super(LocalContext, self).__init__()
        self.args = args
        self.kwargs = kwargs

    def workspace(self, *args, **kwargs):
        return None

    def file(self, *args, **kwargs):
        return None


try:
    import maya.cmds as cmds  # pylint: disable=E0401
    import maya.OpenMayaUI as OpenMayaUI  # pylint: disable=E0401
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin  # pylint: disable=E0401
    import shiboken2  # pylint: disable=E0401
except ImportError:
    cmds = LocalContext()
    OpenMayaUI = LocalContext()
    MayaQWidgetDockableMixin = LocalContext
    shiboken2 = LocalContext()
