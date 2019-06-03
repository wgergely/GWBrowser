# -*- coding: utf-8 -*-
"""Module used to define common variables and methods used across the project.

Global Variables
    The studio wide servers are defined here. These are hard-coded
    variables that will depend on the context the program is used.
    Make sure to customize these settings depending on your environment.

    ``ASSET_IDENTIFIER`` is the file needed to be present to understand a folder
    as an ``asset``. At Glassworks we're using the maya project structure so this is
    a ``workspace.mel`` file.

    ``Assets`` are directory structures compartmentalizing data. ``Browser``
    is implemeted to read any folder but the primary folders are
    ``scene``, ``cache`` (exports) and ``render`` folders.

    Depending on your setup these folders might have different names you can
    customize them here. ``Browser`` will assume all of these folder reside in the
    root of the ``asset`` folder.

Sequence-recognition
    The regexes we're using to validate file-names are also defined here.

    ``get_sequence`` is the regex method that checks if a filename can be incremented.
    For instance, it will understand sequences with the `v` prefix, eg v001, v002,
    but works without the prefix as well. Eg. 001, 002.
    In the case of a filename like `_myfile_v001_freelance_v002.c4d_` ``002``
    will be the prevailing sequence number.
    Likewise, in _myfile_v001_freelance_v002.0001.c4d_ the sequence
    number understood will be ``0001`` not v002.

"""


import os
import sys
import re
import zipfile

from PySide2 import QtGui, QtCore, QtWidgets
import OpenImageIO.OpenImageIO as OpenImageIO

import gwbrowser.gwscandir as gwscandir


# Flags
MarkedAsArchived = 0b1000000000
MarkedAsFavourite = 0b10000000000
MarkedAsActive = 0b100000000000

COMPANY = u'Glassworks'
PRODUCT = u'GWBrowser'


def platform():
    """Returns the name of the current platform.

    Returns:
        unicode: *mac* or *win*, depending on the platform.

    Raises:        NotImplementedError: If the current platform is not *mac* or *win*.

    """
    ptype = QtCore.QSysInfo().productType().lower()
    if ptype in (u'darwin', u'osx', u'macos'):
        return u'mac'
    if u'win' in ptype:
        return u'win'
    raise NotImplementedError(
        u'The platform "{}" is not supported'.format(ptype))


class Server(object):
    """This is wrapper class to store the list of available servers."""

    __servers = {
        u'main': {
            u'mac': u'smb://GW-WORKSTATION/jobs',
            u'win': u'//GW-WORKSTATION/jobs',
            u'description': u'The main jobs folder'
        },
        u'backup': {
            u'mac': u'smb://GW-WORKSTATION/jobs-archive',
            u'win': u'//GW-WORKSTATION/jobs-archive',
            u'description': u'The backup of the main jobs folder'
        },
        u'local': {
            u'mac': u'/jobs',
            u'win': u'//GW-WORKSTATION/jobs-local',
            u'description': u'Local jobs folder on SSD'
        },
    }

    def __init__(self):
        pass

    @classmethod
    def get_server_platform_name(cls, name, platform):
        """Returns the name of the server for another platform"""
        it = cls.__servers.itervalues()
        val = [v for v in it if [f for f in v.itervalues() if f.endswith(name)]]
        return val[0][platform]

    @classmethod
    def main(cls):
        """The path to the primary server.
        This is where all active jobs are stored.

        """
        return cls.__servers[u'main'][platform()]

    @classmethod
    def backup(cls):
        """The path to the backup server.
        This is where all active job backup are stored.

        """
        return cls.__servers[u'backup'][platform()]

    @classmethod
    def local(cls):
        """This is a local copy of the jobs folder. Useful to take advantage
        when needing quick access to storage using the local SSD drive.

        """
        return cls.__servers['local'][platform()]

    @classmethod
    def servers(cls):
        """Returns all available servers."""
        arr = []
        for v in cls.__servers.itervalues():
            arr.append({u'path': v[platform()],
                        u'description': v[u'description']})
        arr = sorted(arr, key=lambda x: x[u'path'])
        return arr


ASSET_IDENTIFIER = u'workspace.mel'
"""When with the given name is present in the root of a folder, it will be
considered an ``asset``."""


FTHREAD_COUNT = 2
"""The number of threads used by the ``FilesWidget`` to get file - information."""

ITHREAD_COUNT = 4
"""The number of threads used by the ``ImageCache`` to perform generate thumbnails."""

LTHREAD_COUNT = 1
"""The number of threads used by the ``DataKeyModel`` get folder file - counts."""

FTIMER_INTERVAL = 1000

ExportsFolder = u'exports'
CacheFolder = u'cache'
TempFolder = u'tmp'
ModelsFolder = u'models'
CompScriptsFolder = u'comp_scripts'
CompsFolder = u'comps'
ScenesFolder = u'scenes'
RendersFolder = u'renders'
TexturesFolder = u'textures'
ArtworkFolder = u'artwork'
ReferenceFolder = u'reference'
PhotosFolder = u'photos'
CapturesFolder = u'viewport_captures'

ASSET_FOLDERS = {
    ArtworkFolder: u'2D design- and style-frames',
    CacheFolder: u'Temporary and discardable files only, use "{}" for persistent files'.format(ExportsFolder.upper()),
    CapturesFolder: u'Animation work-in-progress takes',
    CompScriptsFolder: u'Compositing projects (eg. Nuke, After Effects scenes)',
    CompsFolder: u'Composited prerenders and final image renders',
    ExportsFolder: u'Persistent caches shared between scenes and assets (eg. animation caches)',
    ModelsFolder: u'Obsolete, use "{}" instead'.format(ExportsFolder.upper()),
    PhotosFolder: u'Obsolete, use "{}" instead'.format(ReferenceFolder),
    ReferenceFolder: u'Generic references',
    RendersFolder: u'2D and 3D render passes and layers',
    ScenesFolder: u'2D and 3D scene, project files',
    TempFolder: u'Used by the system, don\'t save files here',
    TexturesFolder: u'Textures used by the 2D and 3D projects',
    u'misc': u'',
}

# Sizes
ROW_HEIGHT = 46.0
BOOKMARK_ROW_HEIGHT = 54.0
ASSET_ROW_HEIGHT = 84.0
CONTROL_HEIGHT = 38.0
ROW_SEPARATOR = 1.0

INLINE_ICONS_MIN_WIDTH = 640.0

# Font scaling seems at best random given platform differences.
# Programmatically scaling might fix matters...
SMALL_FONT_SIZE = 8.0
MEDIUM_FONT_SIZE = 9.0
LARGE_FONT_SIZE = 12.0

pscale = 1.0
"""The global font scale value. Not implemeted yet."""


def psize(n):
    """On macosx the font size seem to be smaller given the same point size....
    Sadly I have to use this function to scale the fonts to an acceptable size.
    I haven't figured out where the difference comes from or what the differences
    refers to. Difference of dpi...?

    """
    return n * 1.5 if platform() == u'mac' else n * pscale


MARGIN = 18.0

INDICATOR_WIDTH = 4.0
ROW_BUTTONS_HEIGHT = 36.0

WIDTH = 640.0
HEIGHT = 480.0

INLINE_ICON_SIZE = 18.0
THUMBNAIL_IMAGE_SIZE = 1024.0

BACKGROUND_SELECTED = QtGui.QColor(140, 140, 140)
SECONDARY_BACKGROUND = QtGui.QColor(70, 70, 70)
BACKGROUND = QtGui.QColor(88, 88, 88)
THUMBNAIL_BACKGROUND = QtGui.QColor(0, 0, 0, 55)

TEXT = QtGui.QColor(220, 220, 220)
TEXT_SELECTED = QtGui.QColor(250, 250, 250)
TEXT_DISABLED = QtGui.QColor(140, 140, 140)

TEXT_NOTE = QtGui.QColor(150, 150, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)

SEPARATOR = QtGui.QColor(45, 45, 45)
FAVOURITE = QtGui.QColor(120, 110, 200)
SELECTION = FAVOURITE

PrimaryFont = QtGui.QFont(u'Roboto Black')
PrimaryFont.setPointSize(MEDIUM_FONT_SIZE)
SecondaryFont = QtGui.QFont(u'Roboto Medium')
SecondaryFont.setPointSize(SMALL_FONT_SIZE)


def get_oiio_extensions():
    """Returns a list of extension OpenImageIO is capable of reading."""
    extensions = []
    for f in OpenImageIO.get_string_attribute("extension_list").split(';'):
        extensions = extensions + f.split(':')[-1].split(',')
    return frozenset(extensions)


def get_oiio_namefilters(as_array=False):
    """Gets all accepted formats from the oiio build as a namefilter list.
    Use the return value on the QFileDialog.setNameFilters() method.

    """
    extension_list = OpenImageIO.get_string_attribute("extension_list")
    namefilters = []
    arr = []
    for exts in extension_list.split(u';'):
        exts = exts.split(u':')
        _exts = exts[1].split(u',')
        e = [u'*.{}'.format(f) for f in _exts]
        namefilter = u'{} files ({})'.format(exts[0].upper(), u' '.join(e))
        namefilters.append(namefilter)
        for _e in _exts:
            arr.append(_e)
    if as_array:
        return arr

    allfiles = [u'*.{}'.format(f) for f in arr]
    allfiles = u' '.join(allfiles)
    allfiles = 'All files ({})'.format(allfiles)
    namefilters.insert(0, allfiles)
    return u';;'.join(namefilters)


creative_cloud_formats = [
    u'aep',
    u'ai',
    u'eps',
    u'fla',
    u'ppj',
    u'prproj',
    u'psb',
    u'psd',
    u'psq',
    u'xfl',
]
exports_formats = [
    u'abc',  # Alembic
    u'ass',  # Arnold
    u'bgeo',  # Houdini
    u'fbx',
    u'geo',  # Houdini
    u'obj',
    u'rs',  # Redshift cache file
    u'sim',  # Houdini
    u'sc',  # Houdini
    u'vdb',  # OpenVDB cache file
    u'ifd',  # Houdini
]
scene_formats = [
    u'c4d',
    u'hud',
    u'hip',
    u'ma',
    u'mb',
    u'nk',
    u'nk~',
    u'mocha',
    u'rv',
    u'autosave'
]
misc_formats = [
    u'pdf',
    u'zip',
    u'm4v',
    u'm4a',
    u'mov',
    u'mp4',
]
oiio_formats = get_oiio_namefilters(as_array=True)
all_formats = frozenset(
    scene_formats +
    oiio_formats +
    exports_formats +
    creative_cloud_formats +
    misc_formats
)

NameFilters = {
    ExportsFolder: all_formats,
    ScenesFolder: all_formats,
    RendersFolder: all_formats,
    TexturesFolder: all_formats,
}
"""A list of expected file - formats associated with the location."""


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
SequenceRole = 1030  # SRE Match object
FramesRole = 1031  # List of frame names
FileInfoLoaded = 1032
FileThumbnailLoaded = 1033
StartpathRole = 1034
EndpathRole = 1035
ThumbnailRole = 1036
ThumbnailPathRole = 1037
ThumbnailBackgroundRole = 1038
DefaultThumbnailRole = 1039
DefaultThumbnailBackgroundRole = 1040
TypeRole = 1041
AssetCountRole = 1042
EntryRole = 1043

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


FilterTextRegex = re.compile(ur'[^0-9\.\#\-\_\/a-zA-Z]+')
"""This is the valid string accepted by the filter editor."""


def namekey(s, _nsre=re.compile('([0-9]+)')):
    """Key function used to sort alphanumeric filenames."""
    return [int(text) if text.isdigit() else text.lower()
            for text in _nsre.split(s)]


def move_widget_to_available_geo(widget):
    """Moves the widget inside the available screen geomtery, if any of the edges
    fall outside.

    """
    app = QtWidgets.QApplication.instance()
    if widget.window():
        screenID = app.desktop().screenNumber(widget.window())
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


_families = []


def _add_custom_fonts():
    """Adds custom fonts to the application."""
    global _families
    if _families:
        return

    path = u'{}/../rsc/fonts'.format(__file__)
    path = os.path.normpath(os.path.abspath(path))
    d = QtCore.QDir(path)
    d.setNameFilters((u'*.ttf',))

    entries = d.entryInfoList(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)

    for f in entries:
        idx = QtGui.QFontDatabase.addApplicationFont(f.absoluteFilePath())
        family = QtGui.QFontDatabase.applicationFontFamilies(idx)
        if family[0].lower() not in _families:
            _families.append(family[0].lower())


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
            PRIMARY_FONT=PrimaryFont.family(),
            SECONDARY_FONT=SecondaryFont.family(),
            SMALL_FONT_SIZE=psize(SMALL_FONT_SIZE),
            MEDIUM_FONT_SIZE=psize(MEDIUM_FONT_SIZE),
            LARGE_FONT_SIZE=psize(LARGE_FONT_SIZE),
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
    """Converts a numeric byte - value to a human readable string."""
    for unit in [u'', u'K', u'M', u'G', u'T', u'P', u'E', u'Z']:
        if abs(num) < 1024.0:
            return u"%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return u"%.1f%s%s" % (num, u'Yi', suffix)


def reveal(path):
    """Reveals the specified folder in the file explorer.

    Args:
        name(str): A path to the file.

    """
    path = get_sequence_endpath(path)
    if platform() == u'win':
        args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        return QtCore.QProcess.startDetached(u'explorer', args)

    if platform() == u'mac':
        args = [
            u'-e',
            u'tell application "Finder"',
            u'-e',
            u'activate',
            u'-e',
            u'select POSIX file "{}"'.format(
                QtCore.QDir.toNativeSeparators(path)), u'-e', u'end tell']
        return QtCore.QProcess.startDetached(u'osascript', args)

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
        u're': re.compile(
            ur'([\s\t\n\r]*)',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': CodeHighlight
    },
    u'file_path': {
        u're': re.compile(
            ur'([a-z]{2,5}:)?([\/\\]{2}[^\"\*\<\>\?\|]+\.[a-z0-9]{2,4})[\s\t\n\r]*',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': CodeHighlight
    },
    u'folder_path': {
        u're': re.compile(
            ur'([a-z]{2,5}:)?([\/\\]{2}[^\"\*\<\>\?\|\s]+)',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': CodeHighlight
    },
    u'quotes': {
        u're': re.compile(
            ur'([\"\']+[^\"\']+[\'\"]+)',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': CodeHighlight
    },
    u'bold': {
        u're': re.compile(
            ur'(\*{2}|_{2})([^\*_]+)(\*{2}|_{2})',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': BoldHighlight
    },
    u'italicized': {
        u're': re.compile(
            ur'([\*_]{1})([^\*_]+)([\*_]{1})',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': ItalicHighlight
    },
    u'heading': {
        u're': re.compile(
            ur'^([#]{1,6})',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': HeadingHighlight
    },
    u'quote': {
        u're': re.compile(
            ur'^([>]{1})',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': QuoteHighlight
    },
}


def get_ranges(arr, padding):
    """Given an array of numbers the method will return a string representation.

    Args:
        arr(list):       An array of numbers
        padding(int):    The number of leading zeros before the number.

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
    ur'\/([^_]{1,3})_([^_]{1,12})_(.{1,25})_([0-9]{3})_([^_]{1,})\.(.*)$',
    flags=re.IGNORECASE | re.UNICODE)
IsSequenceRegex = re.compile(
    r'^(.+?)(\[.*\])(.*)$', flags=re.IGNORECASE | re.UNICODE)
SequenceStartRegex = re.compile(
    ur'^(.*)\[([0-9]+).*\](.*)$',
    flags=re.IGNORECASE | re.UNICODE)
SequenceEndRegex = re.compile(
    ur'^(.*)\[.*?([0-9]+)\](.*)$',
    flags=re.IGNORECASE | re.UNICODE)
GetSequenceRegex = re.compile(
    ur'^(.*?)([0-9]+)([0-9\\/]*|[^0-9\\/]*(?=.+?))\.([^\.]{2,5})$',
    flags=re.IGNORECASE | re.UNICODE)


def get_valid_filename(text):
    """This method will check if the given text conforms Browser's enforced
    filenaming convention.

    A valid ``match`` object if true, ``None`` if the text is invalid.

    Match:
        group(1):   The job's short name, between 1 and 3 characters.
        group(2):   The current asset - name, between 1 and 12 characters.
        # group(3):   The current asset mode, eg. 'animation', between 1 and 12 characters.
        group(3):   The custom description of the file, between 1 - 25 characters.
        group(4):   The file's version. Has to be exactly 3 characters.
        group(5):   The name of the user.
        group(6):   The file's extension (without the '.')

    Returns:
        A valid ``match`` object if true, ``None`` if the text is invalid.

    """
    return ValidFilenameRegex.search(text)


def get_sequence(text):
    """This method will check if the given text contains a sequence element.

    In Browser's terms, a sequence is an file that has a valid number element
    that can be inremented.
    There can only be `one` number element - it will always be the number at the
    end of the file - name, closest to the extension.

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

    Eg.: `[001 - 050]`

    Match:
        group(1):   All the character `before` the sequence marker.
        group(2):   The sequence marker(eg. `[1 - 50]`).
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
        path = SequenceStartRegex.sub(ur'\1\2\3', path)
    return path


def get_sequence_endpath(path):
    """Checks the given string and if it denotes a seuqence returns the path for
    the last file.

    """
    if not is_collapsed(path):
        return path

    match = SequenceEndRegex.search(path)
    if match:
        path = SequenceEndRegex.sub(ur'\1\2\3', path)
    return path


def get_sequence_paths(index):
    """Given the index, returns a tuple of filenames referring to the
    individual sequence items.

    """
    path = index.data(QtCore.Qt.StatusTipRole)
    if not is_collapsed(path):
        return path

    sequence_paths = []
    for frame in index.data(FramesRole):
        seqpath = index.data(SequenceRole).expand(ur'\1{}\3.\4')
        sequence_paths.append(seqpath.format(frame))
    return sequence_paths


def draw_aliased_text(painter, font, rect, text, align, color):
    """Allows drawing aliased text using *QPainterPath*. This is a slow to calculate
    but ensures the rendered text looks *smooth* (on Windows espcially, I noticed a lot of
    aliasing issues). We're also eliding the given text to the width of the given
    rectangle.

    Args:
        painter (QPainter):         The active painter.
        font (QFont):               The font to use to paint.
        rect (QRect):               The rectangle to fit the text in.
        text (unicode):             The text to paint.
        align (Qt.AlignmentFlag):   The alignment flags.
        color (QColor):             The color to use.

    Returns:
        int: The width of the drawn text in pixels.

    """
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
        rect.width() + 2)
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
    to be used a s thumbnail image.: )

    """
    entries = index.data(EntryRole)
    if not entries:
        if index.data(TypeRole) == SequenceItem:
            return index.data(SequenceRole).expand(
                ur'\1{}\3.\4'.format(index.data(FramesRole)[0]))
        else:
            return index.data(QtCore.Qt.StatusTipRole)

    def key(x): return x.stat().st_size
    entry = max(index.data(EntryRole), key=key)
    return entry.path.replace(u'\\', u'/')


def mount():
    """Mounts the server in macosx if it isn't mounted already."""
    if platform() == u'win':
        return

    if platform() == u'mac':
        mountpoint = u'/volumes/{}'.format(Server.main().split(u'/').pop())

        for d in QtCore.QStorageInfo.mountedVolumes():
            if d.rootPath().lower() == mountpoint:
                return  # the server is already mounted

        args = [u'-e', u'mount volume "{}"'.format(Server.main())]
        process = QtCore.QProcess()
        process.start(u'osascript', args)
        process.waitForFinished(-1)

        # We will wait here until the drive is available to use...
        while True:
            for d in QtCore.QStorageInfo.mountedVolumes():
                if d.rootPath().lower() == mountpoint:
                    return
        return

    raise NotImplementedError('{} os has not been implemented.'.format(
        QtCore.QSysInfo().productType()))


WindowsPath = 0
UnixPath = 1
SlackPath = 2
MacOSPath = 3


def copy_path(index, mode=WindowsPath, first=True):
    """Copies the given path to the clipboard. We have to do some magic here
    for the copied paths to be fully qualified."""
    current_parent = index.data(ParentRole)[0]
    path = index.data(QtCore.Qt.StatusTipRole)
    if first:
        path = get_sequence_startpath(path)
    else:
        path = get_sequence_endpath(path)

    if mode == WindowsPath:
        path = path.replace(
            current_parent,
            Server.get_server_platform_name(current_parent, 'win'))
        path = re.sub(ur'[\/\\]', ur'\\', path)
        QtGui.QClipboard().setText(path)
        return

    if mode == UnixPath:
        path = path.replace(
            current_parent,
            Server.get_server_platform_name(current_parent, 'mac'))
        path = re.sub(ur'[\/\\]', ur'/', path)
        QtGui.QClipboard().setText(path)
        return path

    if mode == SlackPath:
        path = QtCore.QUrl().fromLocalFile(path).toString()
        QtGui.QClipboard().setText(path)
        return path

    if mode == MacOSPath:
        path = path.replace(
            current_parent,
            Server.get_server_platform_name(current_parent, 'mac'))
        path = re.sub(ur'[\/\\]', ur'/', path)
        QtGui.QClipboard().setText(path)
        return path


@QtCore.Slot(QtCore.QModelIndex)
def execute(index, first=False):
    """Given the model index, executes the index's path using QDesktopServices."""
    if not index.isValid():
        return
    path = index.data(QtCore.Qt.StatusTipRole)
    if first:
        path = get_sequence_startpath(path)
    else:
        path = get_sequence_endpath(path)

    url = QtCore.QUrl.fromLocalFile(path)
    QtGui.QDesktopServices.openUrl(url)


enc = sys.getfilesystemencoding()


def walk(top, topdown=True, onerror=None, followlinks=False):
    """This is a modified version using the C based _scandir module for iterating through
    directories. The code is taken from the scandir module but here forcing the code to
    use the _scandir(gwscandir) iterator on all platforms.

    Returns:
        tuple(
            path(unicode),
            folders(DirEntries),
            files(DirEntries)
        )

    """
    try:
        top = unicode(top, 'utf-8')
    except TypeError:
        try:
            top = top.decode(enc)
        except:
            pass
    dirs = []
    nondirs = []

    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.
    try:
        scandir_it = gwscandir.scandir(top)
    except OSError as error:
        if onerror is not None:
            onerror(error)
        return

    while True:
        try:
            try:
                entry = next(scandir_it)
            except StopIteration:
                break
        except OSError as error:
            if onerror is not None:
                onerror(error)
            return

        try:
            is_dir = entry.is_dir()
        except OSError:
            # If is_dir() raises an OSError, consider that the entry is not
            # a directory, same behaviour than os.path.isdir().
            is_dir = False

        if is_dir:
            dirs.append(entry)
        else:
            nondirs.append(entry)

        if not topdown and is_dir:
            # Bottom-up: recurse into sub-directory, but exclude symlinks to
            # directories if followlinks is False
            if followlinks:
                walk_into = True
            else:
                try:
                    is_symlink = entry.is_symlink()
                except OSError:
                    # If is_symlink() raises an OSError, consider that the
                    # entry is not a symbolic link, same behaviour than
                    # os.path.islink().
                    is_symlink = False
                walk_into = not is_symlink

            if walk_into:
                for entry in walk(entry.path, topdown, onerror, followlinks):
                    yield entry

    # Yield before recursion if going top down
    if topdown:
        yield top, dirs, nondirs

        # Recurse into sub-directories
        for direntry in dirs:
            new_path = u'%s/%s' % (top, direntry.name)
            for entry in walk(new_path, topdown, onerror, followlinks):
                yield entry
    else:
        yield top, dirs, nondirs


def rsc_path(f, n):
    """Helper function to retrieve a resource - file item"""
    path = u'{}/../rsc/{}.png'.format(f, n)
    path = os.path.normpath(os.path.abspath(path))
    return path


def ubytearray(ustring):
    """Helper function to convert a unicode string to a QByteArray object."""
    if not isinstance(ustring, unicode):
        raise TypeError('The provided string has to be a unicode string')
    # We convert the string to a hex array
    hstr = [r'\x{}'.format(f.encode('hex')) for f in ustring.encode('utf-8')]
    return QtCore.QByteArray.fromHex(''.join(hstr))


def clean_filter_text(filter_text):
    """This method will output a `clean`, readable version of the filter text."""
    if not filter_text:
        filter_text = u''
    else:
        filter_text = re.sub(u'\[\\\S\\\s\]\*', u' ', filter_text)
        filter_text = re.sub(ur'[\\]+', '', filter_text)
        filter_text = FilterTextRegex.sub(u' ', filter_text)
        filter_text = re.sub(ur'\s', u' ', filter_text)
    return filter_text


def regexify_filter_text(filter_text):
    """Replaces whitespaces with catch - all regex search elements."""
    filter_text = FilterTextRegex.sub(u' ', filter_text)
    filter_text = re.sub(ur'\s\s*', u' ', filter_text)
    filter_text = re.sub(ur'\s', ur'[\S\s]*', filter_text)
    return filter_text


def create_asset_template(source, dest, overwrite=False):
    """Responsible for adding the files and folders of the given source to the
    given zip - file.

    """
    if not overwrite:
        if QtCore.QFileInfo(dest).exists():
            raise RuntimeError('{} exists already'.format(dest))

    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source):
            for d in dirs:
                arcname = os.path.join(root, d).replace(source, u'.')
                zipf.write(os.path.join(root, d), arcname=arcname)
            for f in files:
                arcname = os.path.join(root, f).replace(source, u'.')
                zipf.write(os.path.join(root, f), arcname=arcname)


MayaAssetTemplate = 1024
ProjectTemplate = 2048


AssetTypes = {
    MayaAssetTemplate: u'MayaAsset',
    ProjectTemplate: u'Project',
}


def create_asset_from_template(name, basepath, template):
    """Creates a new asset with the given name.

    The asset is a zip - archive containing the folder - structure. We can define
    multiple asset - types. These are defined in the ``common.AssetTypes`` variable.

    """
    template_info = QtCore.QFileInfo(
        u'{}/../templates/{}.zip'.format(__file__, AssetTypes[template]))
    if not template_info.exists():
        raise RuntimeError(
            u'The "{}.zip" template file could not be located.'.format(AssetTypes[template]))

    dest_info = QtCore.QDir(u'{}/{}'.format(basepath, name))
    if not dest_info.exists():
        res = QtCore.QDir(basepath).mkdir(name)
        if not res:
            raise RuntimeError(u'An error occured creating the asset folders.')
    with zipfile.ZipFile(template_info.absoluteFilePath(), 'r', zipfile.ZIP_DEFLATED) as f:
        f.extractall(dest_info.absolutePath(), members=None, pwd=None)


# create_asset('asset1', ur'C:\dev\maya', template=MayaAsset)
