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

Sequence-recognition
    The regexes we're using to validate file-names are aslo defined here.
    `get_sequence` is the regex method that checks if a filename can be incremented.
    For instance, it will understand sequences with the `v` prefix, eg v001, v002,
    but works without the prefix as well. Eg. 001, 002.

    Also, in the case of a filename like `_myfile_v001_freelance_v002.c4d_` ``002``
    will be the prevailing sequence number.
    Likewise, in the case of _myfile_v001_freelance_v002.0001.c4d_ the sequence
    number understood will be ``0001``.

"""

import os
import re

from PySide2 import QtGui, QtCore, QtWidgets



SERVERS = [
    {u'path': u'//gordo/jobs', u'nickname': u'Gordo'},
    {u'path': u'//sloth/jobs', u'nickname': u'Sloth'},
    {u'path': u'//localhost/c$/temp', u'nickname': u'Local Drive'},
]

ASSET_IDENTIFIER = u'workspace.mel'
"""When with the given name is present in the root of a folder, it will be
considered an ``assets``."""


ScenesFolder = u'scenes'
ExportsFolder = u'exports'
RendersFolder = u'renders'
TexturesFolder = u'textures'


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


def get_oiio_namefilters(as_array=False):
    """Gets all accepted formats from the oiio build as a namefilter list.
    Use the return value on the QFileDialog.setNameFilters() method.

    """
    import browser.modules  # pylint: disable=E0401
    import oiio.OpenImageIO as oiio

    formatlist = oiio.get_string_attribute("extension_list").split(';')
    namefilters = []
    arr = []
    for exts in formatlist:
        exts = exts.split(':')
        _exts = exts[1].split(',')
        e = ['*.{}'.format(f) for f in _exts]
        namefilter = '{} files ({})'.format(exts[0].upper(), ' '.join(e))

        namefilters.append(namefilter)
        for _e in _exts:
            arr.append(_e)
    if as_array:
        return arr

    e = ['*.{}'.format(f) for f in arr]
    namefilters.insert(0, 'All files ({})'.format(' '.join(e)))
    return namefilters

_creative_cloud_formats = (
    u'psd',
    u'psb',
    u'aep',
    u'ai',
    u'eps',
    u'prproj',
    u'ppj',
    u'psq',
    u'fla',
    u'xfl',
)
_exports_formats = (
    u'abc', # Alembic
    u'obj',
    u'fbx',
    u'bgeo', # Houdini
    u'geo', # Houdini
    u'sim', # Houdini
    u'vdb', # OpenVDB cache file
    u'rs', # Redshift cache file
    u'ass', # Arnold
)
_scene_formats = (
    u'ma',
    u'mb',
    u'c4d',
    u'hud',
    u'nk',
    u'rv'
)
_oiio_formats = tuple(get_oiio_namefilters(as_array=True))

NameFilters = {
    ExportsFolder: _exports_formats,
    ScenesFolder: _creative_cloud_formats + _scene_formats + _oiio_formats,
    RendersFolder: _oiio_formats,
    TexturesFolder: _oiio_formats,
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
SequenceRole = 1030 # SRE Match object
FramesRole = 1031 # List of frame names
StatusRole = 1032
StartpathRole = 1033
EndpathRole = 1034
ThumbnailRole = 1035
ThumbnailPathRole = 1036
ThumbnailBackgroundRole = 1037
DefaultThumbnailRole = 1038
DefaultThumbnailBackgroundRole = 1039
TypeRole = 1040

SortByName = 2048
SortByLastModified = 2049
SortBySize = 2050

FileItem = 1100
SequenceItem = 1200
AssetItem = 1300
BookmarkItem = 1400

LowerCase = 0
UpperCase = 1
"""Filename styles"""


def sort_alphanum_key(key):
    def _convert(text):
        return int(text) if text.isdigit() else text

    def _split(key):
        return re.split(r'([0-9]+)', key.filePath())

    return [_convert(f) for f in _split(key)]



alphanum = re.compile(r'([0-9]+)', flags=re.IGNORECASE)
# re_natural = re.compile('[0-9]+|[^0-9]+')
def namekey(s):
    # return [(1, int(c)) if c.isdigit() else (0, c.lower()) for c in re_natural.findall(s)] + [s]
    return [(int(f) if f.isdigit() else f) for f in alphanum.split(s)]

def sort_last_modified_key(key):
    return key.lastModified().toMSecsSinceEpoch()


def sort_size_key(key):
    return key.size()


sort_keys = {
    SortByName: sort_alphanum_key,
    SortByLastModified: sort_last_modified_key,
    SortBySize: sort_size_key,
}
"""These are the methods/keys used to sort lists."""



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
    d.setNameFilters((u'*.ttf',))

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
        raise NotImplementedError('{} os has not been implemented.'.format(
            QtCore.QSysInfo().productType()))


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


def get_ranges(arr, padding):
    """Given an array of numbers the method will return a string representation.

    Args:
        arr (list):       An array of numbers
        padding (int):    The number of leading zeros before the number.

    """
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


ValidFilenameRegex = re.compile(
    r'\/([^_]{1,3})_([^_]{1,12})_([^_]{1,12})_(.{1,25})_([0-9]{3})_([^_]{1,})\.(.*)$', flags=re.IGNORECASE)
IsSequenceRegex = re.compile(r'^(.+?)(\[.*\])(.*)$', flags=re.IGNORECASE)
SequenceStartRegex = re.compile(
    r'^(.*)\[([0-9]+).*\](.*)$', flags=re.IGNORECASE)
SequenceEndRegex = re.compile(
    r'^(.*)\[.*?([0-9]+)\](.*)$', flags=re.IGNORECASE)
GetSequenceRegex = re.compile(
    r'^(.*?)([0-9]+)([0-9\\/]*|[^0-9\\/]*(?=.+?))\.([^\.]{2,5})$', flags=re.IGNORECASE)


def get_valid_filename(text):
    """This method will check if the given text conforms Browser's enforced
    filenaming convention.

    A valid ``match`` object if true, ``None`` if the text is invalid.

    Match:
        group(1):   The job's short name, between 1 and 3 characters.
        group(2):   The current asset-name, between 1 and 12 characters.
        group(3):   The current asset mode, eg. 'animation', between 1 and 12 characters.
        group(4):   The custom descirption of the file, between 1-25 characters.
        group(5):   The file's version. Has to be exactly 3 characters.
        group(6):   The name of the user.
        group(7):   The file's extension (without the '.')

    Returns:
        A valid ``match`` object if true, ``None`` if the text is invalid.

    """
    return ValidFilenameRegex.search(text)


def get_sequence(text):
    """This method will check if the given text contains a sequence element.

    In Browser's terms, a sequence is an file that has a valid number element
    that can be inremented.
    There can only be `one` number element - it will always be the number at the
    end of the file-name, closest to the extension.

    Match:
        group(1):   All the character `before` the sequence.
        group(2):   The sequence number.
        group(3):   All the characters after the sequence number.

    Returns:
        A valid ``match`` object if true or ``None`` if the text doesn't contain
        a number.

    """
    return GetSequenceRegex.search(text)


def is_collapsed(text):
    """In Browser's terminology, a `collapsed` item is a name that represents a
    sequence. Sequence are annoted by a series of numbers contained inside a bracket.

    Eg.: `[001-050]`

    Match:
        group(1):   All the character `before` the sequence marker.
        group(2):   The sequence marker (eg. `[1-50]`).
        group(3):   All the characters after the sequence marker.

    Returns:
        A valid ``match`` object if true or ``None`` if the text doesn't is not
        a collapsed sequence.

    """
    return IsSequenceRegex.search(text)


def get_sequence_startpath(path):
    """Checks the given string and if it denotes a seuqence returns the path for
    the first file.

    """
    if not is_collapsed(path):
        return path

    match = SequenceStartRegex.search(path)
    if match:
        path = SequenceStartRegex.sub(r'\1\2\3', path)
    return path


def get_sequence_endpath(path):
    """Checks the given string and if it denotes a seuqence returns the path for
    the last file.

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

    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

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
    width = metrics.width(text)

    if QtCore.Qt.AlignLeft & align:
        x = rect.left()
    if QtCore.Qt.AlignRight & align:
        x = rect.right() - width
    if QtCore.Qt.AlignHCenter & align:
        x = rect.left() + (rect.width() / 2.0) - (width / 2.0)

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
    return width


def find_largest_file(index):
    """Finds the sequence's largest file from sequence filepath.
    The largest files of the sequence will probably hold enough visual information
    to be used a s thumbnail image. :)

    """
    p = index.data(QtCore.Qt.StatusTipRole).split(u'/')
    p.pop()
    p = u'/'.join(p)

    dir_ = QtCore.QDir(p)
    dir_.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
    f = index.data(SequenceRole).expand(r'\1{}\3.\4')
    f = f.format(u'?' * (len(index.data(FramesRole)[-1])))
    f = f.split('/')[-1]
    dir_.setNameFilters((f,))
    return max(dir_.entryInfoList(), key=lambda f: f.size()).filePath()

    # return max(dir_.entryInfoList(), key=lambda f: f.size()).filePath()
