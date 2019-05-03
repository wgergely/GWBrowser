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
    The regexes we're` using to validate file-names are aslo defined here.
    `get_sequence` is the regex method that checks if a filename can be incremented.
    For instance, it will understand sequences with the `v` prefix, eg v001, v002,
    but works without the prefix as well. Eg. 001, 002.

    Also, in the case of a filename like `_myfile_v001_freelance_v002.c4d_` ``002``
    will be the prevailing sequence number.
    Likewise, in the case of _myfile_v001_freelance_v002.0001.c4d_ the sequence
    number understood will be ``0001``.

"""


import os
import sys
import re

from PySide2 import QtGui, QtCore, QtWidgets


default_server = u'sloth'
legacy_server = u'gordo'
default_username = u'render'
default_password = u'render'

osx = QtCore.QSysInfo().productType().lower() in (u'darwin', u'osx', u'macos')
windows = QtCore.QSysInfo().productType().lower() in (u'windows', u'winrt')

local = {True: u'/jobs', False: u'//localhost/c$/jobs'}
sloth = {True: '/Volumes/jobs', False: u'//{}/jobs'.format(default_server)}
gordo = {True: '/Volumes/jobs', False: u'//{}/jobs'.format(legacy_server)}

SERVERS = [
    {u'path': gordo[osx], u'nickname': u'Gordo (Legacy)'},
    {u'path': sloth[osx], u'nickname': u'Sloth'},
    {u'path': local[osx], u'nickname': u'Local Jobs'},
]

ASSET_IDENTIFIER = u'workspace.mel'
"""When with the given name is present in the root of a folder, it will be
considered an ``assets``."""


# Cache files
ExportsFolder = u'exports'
ExportsFolderDescription = u'Persistent caches shared between scenes and assets (eg. animation caches)'

CacheFolder = u'cache'
CacheFolderDescription = u'Temporary and discardable files only, use "{}" for caches to keep'.format(ExportsFolder.upper())

TempFolder = u'tmp'
TempFolderDescription = u'Used by the system, don\'t save files here'

ModelsFolder = u'models'
ModelsFolderDescription = u'Obsolete, use "{}" instead'.format(ExportsFolder.upper())

# Important folders
CompScriptsFolder = u'comp_scripts'
CompScriptsDescription = u'Compositing (eg. Houdini) scene files'

CompsFolder = u'comps'
CompsDescription = u'Composited prerenders and final image renders'

ScenesFolder = u'scenes'
ScenesFolderDescription = u'2D and 3D scene, project files'

RendersFolder = u'renders'
RendersFolderDescription  = u'2D and 3D render passes and layers'

TexturesFolder = u'textures'
TexturesFolderDescription  = u'Textures used by the 2D and 3D projects'

# Reference folders
ArtworkFolder = u'artwork'
ArtworkFolderDescription = u'2D design- and style-frames'

ReferenceFolder = u'reference'
ReferenceFolderDescription = u'Generic references'

PhotosFolder = u'photos'
PhotosFolderDescription = u'Obsolete, use "{}" instead'.format(ReferenceFolder)

CapturesFolder = u'viewport_captures'
CapturesFolderDescription = u'Animation work-in-progress takes'

MiscFolderDescription = u'A generic asset folder'

ASSET_FOLDERS = {
    ArtworkFolder: ArtworkFolderDescription,
    CacheFolder: CacheFolderDescription,
    CapturesFolder: CapturesFolderDescription,
    CompScriptsFolder: CompScriptsDescription,
    CompsFolder: CompsDescription,
    ExportsFolder: ExportsFolderDescription,
    ModelsFolder: ModelsFolderDescription,
    PhotosFolder: PhotosFolderDescription,
    ReferenceFolder: ReferenceFolderDescription,
    RendersFolder: RendersFolderDescription,
    ScenesFolder: ScenesFolderDescription,
    TempFolder: TempFolderDescription,
    TempFolder: TempFolderDescription,
    TexturesFolder: TexturesFolderDescription,
    u'misc': MiscFolderDescription,
}


# Sizes
ROW_HEIGHT = 46.0
BOOKMARK_ROW_HEIGHT = 54.0
ASSET_ROW_HEIGHT = 84.0

# Font scaling seems at best random given platform differences.
# Programmatically scaling might fix matters...
SMALL_FONT_SIZE = 8.0
MEDIUM_FONT_SIZE = 9.0
LARGE_FONT_SIZE = 12.0

pscale = 1.0

def psize(n): return n * 1.5 if osx else n * pscale


"""On macosx the font size seem to be smaller - using this function we
can scale the fonts to an acceptable size. I haven't figured out
where the difference comes from."""

MARGIN = 18.0

INDICATOR_WIDTH = 4.0
ROW_BUTTONS_HEIGHT = 36.0

WIDTH = 640.0
HEIGHT = 480.0

INLINE_ICON_SIZE = 18.0
THUMBNAIL_IMAGE_SIZE = 1024.0

BACKGROUND_SELECTED = QtGui.QColor(140, 140, 140)
SECONDARY_BACKGROUND = QtGui.QColor(80, 80, 80)
BACKGROUND = QtGui.QColor(98, 98, 98)

TEXT = QtGui.QColor(220, 220, 220)
TEXT_SELECTED = QtGui.QColor(250, 250, 250)
TEXT_DISABLED = QtGui.QColor(140, 140, 140)

TEXT_NOTE = QtGui.QColor(150, 150, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)

SEPARATOR = QtGui.QColor(45, 45, 45)
SELECTION = QtGui.QColor(140, 120, 233)
FAVOURITE = QtGui.QColor(140, 120, 233)

PrimaryFont = QtGui.QFont(u'Roboto Black')
PrimaryFont.setPointSize(MEDIUM_FONT_SIZE)
SecondaryFont = QtGui.QFont(u'Roboto Medium')
SecondaryFont.setPointSize(SMALL_FONT_SIZE)


def get_oiio_extensions():
    """Returns a list of extension OpenImageIO is capable of reading."""
    import OpenImageIO.OpenImageIO as OpenImageIO

    extensions = []
    for f in OpenImageIO.get_string_attribute("extension_list").split(';'):
        extensions = extensions + f.split(':')[-1].split(',')
    return list(set(extensions))


def get_oiio_namefilters(as_array=False):
    """Gets all accepted formats from the oiio build as a namefilter list.
    Use the return value on the QFileDialog.setNameFilters() method.

    """
    import OpenImageIO.OpenImageIO as OpenImageIO

    formatlist = OpenImageIO.get_string_attribute("extension_list").split(';')
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
)
_exports_formats = (
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
)
_scene_formats = (
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
)
_oiio_formats = tuple(get_oiio_namefilters(as_array=True))
_all_formats = list(_creative_cloud_formats) + list(_scene_formats) + \
    list(_oiio_formats) + list(_exports_formats)

NameFilters = {
    ExportsFolder: _all_formats,
    ScenesFolder: _all_formats,
    RendersFolder: _all_formats,
    TexturesFolder: _all_formats,
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
SequenceRole = 1030  # SRE Match object
FramesRole = 1031  # List of frame names
StatusRole = 1032
StartpathRole = 1033
EndpathRole = 1034
ThumbnailRole = 1035
ThumbnailPathRole = 1036
ThumbnailBackgroundRole = 1037
DefaultThumbnailRole = 1038
DefaultThumbnailBackgroundRole = 1039
TypeRole = 1040
AssetCountRole = 1041

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


def _add_custom_fonts(families=_families):
    """Adds custom fonts to the application."""

    path = u'{}/../rsc/fonts'.format(__file__)
    path = os.path.normpath(os.path.abspath(path))
    d = QtCore.QDir(path)
    d.setNameFilters((u'*.ttf',))

    for f in d.entryInfoList(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot):
        idx = QtGui.QFontDatabase.addApplicationFont(f.absoluteFilePath())
        family = QtGui.QFontDatabase.applicationFontFamilies(idx)
        if family not in families:
            families.append(family)


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
    if windows:
        args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        return QtCore.QProcess.startDetached(u'explorer', args)

    if osx:
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

def mount(path):
    """Mounts the server in macosx if it isn't mounted already.

    Args:
        name (str): A path to the file.

    """
    path = get_sequence_endpath(path)
    if windows:
        args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        return QtCore.QProcess.startDetached(u'explorer', args)

    if osx:
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
    ur'\/([^_]{1,3})_([^_]{1,12})_(.{1,25})_([0-9]{3})_([^_]{1,})\.(.*)$',
    flags=re.IGNORECASE | re.UNICODE)
IsSequenceRegex = re.compile(r'^(.+?)(\[.*\])(.*)$', flags=re.IGNORECASE | re.UNICODE)
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
        group(2):   The current asset-name, between 1 and 12 characters.
        # group(3):   The current asset mode, eg. 'animation', between 1 and 12 characters.
        group(3):   The custom description of the file, between 1-25 characters.
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
        seqpath = index.data(SequenceRole).expand(r'\1{}\3.\4')
        sequence_paths.append(seqpath.format(frame))
    return sequence_paths




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
    f = index.data(SequenceRole).expand(ur'\1{}\3.\4')
    f = f.format(u'?' * (len(index.data(FramesRole)[-1])))
    f = f.split('/')[-1]
    dir_.setNameFilters((f,))
    return max(dir_.entryInfoList(), key=lambda f: f.size()).filePath()


def mount(server=default_server, username=default_username, password=default_password):
    """Mounts the server in macosx if it isn't mounted already. The password
    abd

    """
    if windows:
        return

    if osx:
        for d in QtCore.QStorageInfo.mountedVolumes():
            if d.rootPath().lower() == u'/volumes/jobs':
                return # the server is already mounted
        args = [u'-e', u'mount volume "smb://{username}:{password}@{server}/jobs/"'.format(
            server=server,
            username=username,
            password=password
        )]
        process = QtCore.QProcess()
        process.start(u'osascript', args)
        process.waitForFinished(-1)
        while True:
            for d in QtCore.QStorageInfo.mountedVolumes():
                if d.rootPath().lower() == u'/volumes/jobs':
                    return # the server is mounted and available
        return

    raise NotImplementedError('{} os has not been implemented.'.format(
        QtCore.QSysInfo().productType()))


def file_iterator(path):
    """Platform dependent file iterator."""
    if osx:
        import scandir
        it = scandir.walk(path, followlinks=False)
        for root, directories, files in it:
            for f in files:
                try:
                    root = unicode(root, 'utf-8')
                    f = unicode(f, 'utf-8')
                    path = u'{}/{}'.format(root, f)
                except TypeError:
                    path = u'{}/{}'.format(root, f)
                yield path

    if windows:
        itdir = QtCore.QDir(path)
        itdir.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        itdir.setSorting(QtCore.QDir.Unsorted)

        it = QtCore.QDirIterator(
            itdir, flags=QtCore.QDirIterator.Subdirectories)

        while it.hasNext():
            yield it.next()


WindowsPath = 0
UnixPath = 1
SlackPath = 2
MacOSPath = 3


def copy_path(index, mode=WindowsPath, first=True):
    """Copies the given path to the clipboard."""
    path = index.data(QtCore.Qt.StatusTipRole)
    if first:
        path = get_sequence_startpath(path)
    else:
        path = get_sequence_endpath(path)

    if mode == WindowsPath:
        pserver = index.data(ParentRole)[0]
        server = sloth[not osx]
        server = gordo[not osx] if legacy_server in pserver else server
        server = local[not osx] if 'localhost' in pserver else server

        path = path.replace(pserver, server)
        path = re.sub(ur'[\/\\]', ur'\\', path)
        QtGui.QClipboard().setText(path)
        return path

    if mode == UnixPath:
        pserver = index.data(ParentRole)[0]
        server = sloth[not osx]
        server = gordo[not osx] if legacy_server in pserver else server
        server = local[not osx] if 'localhost' in pserver else server

        path = path.replace(pserver, server)
        path = re.sub(ur'[\/\\]', ur'/', path)
        QtGui.QClipboard().setText(path)
        return path

    if mode == SlackPath:
        path = QtCore.QUrl().fromLocalFile(path).toString()
        QtGui.QClipboard().setText(path)
        return path

    if mode == MacOSPath:
        pserver = index.data(ParentRole)[0]
        server = sloth[osx]
        server = gordo[osx] if legacy_server in pserver else server
        server = local[osx] if pserver.startswith('/jobs') else server

        path = path.replace(pserver, server)
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
