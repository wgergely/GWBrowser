# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903
"""Module for storingcommon variables and methods across the project.

Defines the default sizes for widgets and the default colour template.
It also contains the methods used to set our custom stylesheet.
"""

import os
import sys
import random
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


QtCore.Qt.PathRole = 0x0200  # Role used to store FileInfo items
"""Special Role used to store QFileInfo objects."""

MARGIN = 18
ROW_HEIGHT = 54

BOOKMARK_ROW_HEIGHT = 54
ASSET_ROW_HEIGHT = 84

WIDTH = 640
HEIGHT = 480

ROW_BUTTONS_HEIGHT = 24
STACKED_WIDGET_HEIGHT = 640
ROW_FOOTER_HEIGHT = 18

FAVORUITE_SELECTED = QtGui.QColor(250, 250, 100)
FAVORUITE = QtGui.QColor(235, 235, 68)

BACKGROUND_SELECTED = QtGui.QColor(128, 128, 128)
SECONDARY_BACKGROUND = QtGui.QColor(80, 80, 80)
BACKGROUND = QtGui.QColor(98, 98, 98)

THUMBNAIL_BACKGROUND_SELECTED = QtGui.QColor(85, 85, 85)
THUMBNAIL_BACKGROUND = QtGui.QColor(77, 77, 77)
THUMBNAIL_IMAGE_BACKGROUND = QtGui.QColor(30, 30, 30)

TEXT = QtGui.QColor(220, 220, 220)
TEXT_SELECTED = QtGui.QColor(255, 255, 255)
TEXT_NOTE = QtGui.QColor(150, 150, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)
TEXT_DISABLED = QtGui.QColor(100, 100, 100)
TEXT_WARNING = SECONDARY_TEXT

SEPARATOR = QtGui.QColor(58, 58, 58)
SELECTION = QtGui.QColor(100, 161, 255)
ARCHIVED_OVERLAY = QtGui.QColor(68, 68, 68, 150)

LABEL1_SELECTED = QtGui.QColor(102, 173, 125)
LABEL1 = QtGui.QColor(82, 153, 105)
LABEL1_TEXT = QtGui.QColor(162, 233, 185)

THUMBNAIL_IMAGE_SIZE = 1024


def get_thumbnail_pixmap(path, opacity=1, size=(ROW_BUTTONS_HEIGHT)):
    """Returns a pixmap of the input path."""
    from mayabrowser.delegate import ThumbnailEditor

    image = QtGui.QImage()
    image.load(path)
    image = ThumbnailEditor.smooth_copy(image, size)
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


def label_generator():
    """Generates QColors from an array of RGB values.

    Example:

    .. code-block:: python
        :linenos:

        colors = label_generator()
        next(colors)

    Yields:         QtCore.QColor

    """
    colors = []
    for n in xrange(50):
        a = [104, 101, 170]
        v = 20
        colors.append([
            random.randint(a[0] - v, a[0] + v),
            random.randint(a[1] - v, a[1] + v),
            random.randint(a[2] - v, a[2] + v)
        ])
    for color in colors:
        yield QtGui.QColor(*color)


colors = label_generator()


def get_label(k):
    """Returns the QColor for the given key.

    Args:
        k (str):    The key, eg. the name of a folder.

    Raises:         StopIterationrError: When out of labels.
    Returns:        QColor.

    """
    if k.lower() not in ASSIGNED_LABELS:
        ASSIGNED_LABELS[k.lower()] = next(colors)
    return ASSIGNED_LABELS[k.lower()]


def revert_labels():
    ASSIGNED_LABELS = {}

    global colors
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
        sum(r)/float(len(r)),
        sum(g)/float(len(g)),
        sum(b)/float(len(b))
    )
    return average_color

def count_assets(path):
    """Returns the number of assets inside the given folder."""
    dir = QtCore.QDir(path)
    dir.setFilter(
        QtCore.QDir.NoDotAndDotDot |
        QtCore.QDir.Dirs |
        QtCore.QDir.NoSymLinks |
        QtCore.QDir.Readable
    )

    # Counting the number assets found
    count = 0
    for file_info in dir.entryInfoList():
        dir = QtCore.QDir(file_info.filePath())
        dir.setFilter(QtCore.QDir.Files)
        dir.setNameFilters((ASSET_IDENTIFIER,))
        if dir.entryInfoList():
            count += 1
    return count


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
