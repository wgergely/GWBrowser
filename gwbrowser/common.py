# -*- coding: utf-8 -*-
"""The ``common.py`` module is used to define variables and methods used
across the GWBrowser project.

GWBrowser is intended to be used in a networked environment.
Users users have the ability to define a **primary**, **backup** and
a **local** paths to store assets and bookmarks.

Access to the saved paths are provided by the :class:`.Server` object. The actual
configuration values are stored in the ``templates/server.conf`` configuration
file.

Job and assets templates
########################

*Assets* are directory structures used to compartmentalize files and folders.
The template files used to generate jobs and assets are stored in
``gwbrowser/templates`` folder.

The asset folder definitions should correspond to the folders stored in the
template file - including the folder descriptions. See ``ASSET_FOLDERS``.

Sequences
#########

A core aspect of GWBrowser is the ability to group sequentially numbered
files into a single item (eg. image sequences).

Sequences are recognised via **regex** functions defined here. See
:func:`.get_valid_filename`, :func:`.get_sequence`, :func:`.is_collapsed`,
:func:`.get_sequence_startpath`,  :func:`.get_ranges` for the wrapper functions.

"""

import os
import sys
import re
import zipfile
import ConfigParser

from PySide2 import QtGui, QtCore, QtWidgets
import OpenImageIO


import gwbrowser._scandir as gwscandir

# Flags
MarkedAsArchived = 0b1000000000
MarkedAsFavourite = 0b10000000000
MarkedAsActive = 0b100000000000

COMPANY = u'GWBrowser'
PRODUCT = u'GWBrowser'
SLACK_URL = ur'https://gwbcn.slack.com/'
ABOUT_URL = ur'https://gergely-wootsch.com/gwbrowser-about'


SynchronisedMode = 0
SoloMode = 1


def create_temp_dir():
    server, job, root = get_favourite_parent_paths()
    path = u'{}/{}/{}/.browser'.format(server, job, root)
    _dir = QtCore.QDir(path)
    if _dir.exists():
        return
    _dir.mkpath(u'.')

def get_favourite_parent_paths():
    server = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.TempLocation)
    job = u'gwbrowser'
    root = u'favourites'
    return server, job, root


def save_favourites():
    """Saves all favourites including the descriptions and the thumbnails."""
    import uuid
    from gwbrowser.settings import local_settings
    from gwbrowser.settings import AssetSettings

    res = QtWidgets.QFileDialog.getSaveFileName(
        caption=u'Select where to save your favourites items',
        filter=u'*.gwb',
        dir=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.HomeLocation),
        options=QtWidgets.QFileDialog.ShowDirsOnly
    )
    destination, ext = res
    if not destination:
        return

    favourites = local_settings.value(u'favourites')
    favourites = [f.lower() for f in favourites] if favourites else []

    server = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.TempLocation)
    job = u'gwbrowser'
    root = u'favourites'
    zip_path = u'{}/{}/{}/{}.zip'.format(server, job, root, uuid.uuid4())

    # Make sure the temp folder exists
    QtCore.QFileInfo(zip_path).dir().mkpath(u'.')

    with zipfile.ZipFile(zip_path, 'a') as z:
        for favourite in favourites:
            settings = AssetSettings(
                QtCore.QModelIndex(),
                server=server,
                job=job,
                root=root,
                filepath=favourite
            )
            file_info = QtCore.QFileInfo(settings.thumbnail_path())
            if not file_info.exists():
                continue
            z.write(file_info.filePath(), file_info.fileName())
            file_info = QtCore.QFileInfo(settings.config_path())
            if not file_info.exists():
                continue
            z.write(file_info.filePath(), file_info.fileName())
        z.writestr(u'favourites', u'\n'.join(favourites))

    file_info = QtCore.QFileInfo(zip_path)
    if not file_info.exists():
        raise RuntimeError(u'Unexpected error, could not find the favrouites file')

    QtCore.QDir().rename(file_info.filePath(), destination)
    if not QtCore.QFileInfo(destination).exists():
        raise RuntimeError(u'Unexpected error, could not find the favrouites file')
    reveal(destination)


def import_favourites():
    from gwbrowser.settings import local_settings
    from gwbrowser.settings import AssetSettings

    res = QtWidgets.QFileDialog.getOpenFileName(
        caption=u'Select the favourites file to import',
        filter='*.gwb',
        options=QtWidgets.QFileDialog.ShowDirsOnly
    )
    source, ext = res
    if not source:
        return

    current_favourites = local_settings.value(u'favourites')
    current_favourites = [f.lower() for f in current_favourites] if current_favourites else []

    create_temp_dir()

    with zipfile.ZipFile(source) as zip:
        namelist = zip.namelist()
        if u'favourites' not in namelist:
            mbox = QtWidgets.QMessageBox()
            mbox.setWindowTitle(u'Invalid ".gwb" file')
            mbox.setText(u'This file does not seem to be valid, sorry!')
            mbox.setInformativeText(u'The favourites list is missing from the archive.')
            return mbox.exec_()

        with zip.open(u'favourites') as f:
            favourites = f.readlines()
            favourites = [f.strip() for f in favourites]

        for favourite in favourites:
            server, job, root = get_favourite_parent_paths()
            settings = AssetSettings(
                server=server,
                job=job,
                root=root,
                filepath=favourite
            )

            file_info = QtCore.QFileInfo(settings.thumbnail_path())
            if file_info.fileName() in namelist:
                dest = u'{}/{}/{}/.browser'.format(server, job, root, file_info.fileName())
                zip.extract(file_info.fileName(), dest)

            file_info = QtCore.QFileInfo(settings.config_path())
            if file_info.fileName() in namelist:
                dest = u'{}/{}/{}/.browser'.format(server, job, root, file_info.fileName())
                zip.extract(file_info.fileName(), dest)

            if favourite not in current_favourites:
                current_favourites.append(favourite)

        current_favourites = sorted(list(set(current_favourites)))
        local_settings.setValue(u'favourites', current_favourites)


def clear_favourites():
    from gwbrowser.settings import local_settings
    mbox = QtWidgets.QMessageBox()
    mbox.setWindowTitle(u'Clear favourites')
    mbox.setText(
        u'Are you sure you want to reset your favourites?'.format(
            Server.primary())
    )
    mbox.setInformativeText(
        u'The action is not undoable.')
    mbox.setStandardButtons(
        QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
    mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)

    res = mbox.exec_()
    if mbox.result() == QtWidgets.QMessageBox.Cancel:
        return

    local_settings.setValue(u'favourites', [])


def get_platform():
    """Returns the name of the current platform.

    Returns:
        unicode: *mac* or *win*, depending on the platform.

    Raises:        NotImplementedError: If the current platform is not supported.

    """
    ptype = QtCore.QSysInfo().productType().lower()
    if ptype in (u'darwin', u'osx', u'macos'):
        return u'mac'
    if u'win' in ptype:
        return u'win'
    raise NotImplementedError(
        u'The platform "{}" is not supported'.format(ptype))


class Server(object):
    """A utility class providing the platform-specific locations of
    the ``primary``, ``backup``, and ``local`` servers.

    Note:
        The server values are stored in an external configuration file boundled
        with GWBrowser found at ``templates/server.conf``. However, a copy of
        this configuration file is deployed at installation-time to the
        ~/Documents/GWBrowser folder where GWBrowser will expect to find and
        load it.

    """

    @classmethod
    def config_path(cls):
        """Returns the path to ``server.conf``."""
        datadir = next(f for f in QtCore.QStandardPaths.standardLocations(
            QtCore.QStandardPaths.DocumentsLocation))
        path = u'{}/{}/servers.conf'.format(datadir, PRODUCT)
        path = os.path.normpath(path)
        path = os.path.abspath(path)
        return path

    @classmethod
    def conf(cls):
        parser = ConfigParser.RawConfigParser()
        parser.read(cls.config_path())
        return parser

    @classmethod
    def get_server_platform_name(cls, server, platf):
        """Returns the name of the server for a specified platform.

        Used mostly by the copy function to get a platform accurate path.

        """
        parser = cls.conf()
        d = {}
        for section in parser.sections():
            d[section] = {}
            for key, val in parser.items(section):
                if key not in ('mac', 'win'):
                    continue
                val = val.replace(u'\\', u'/').rstrip(u'/').lower()
                if not val:
                    continue
                d[section][key] = u'{}/'.format(val)

        it = d.itervalues()
        for v in it:
            if not v:
                continue
            for f in v.itervalues():
                if server in f.lower():
                    return v[platf.lower()]
        return None

    @classmethod
    def _get(cls, section):
        o = get_platform()
        parser = cls.conf()
        if not parser.has_section(section):
            return None
        if not parser.has_option(section, o):
            return None
        return cls.conf().get(section, o)

    @classmethod
    def primary(cls):
        """The path to the primary server.
        This is where all active jobs are stored.

        """
        return cls._get('primary')

    @classmethod
    def backup(cls):
        """The path to the backup server.
        This is where all active job backup are stored.

        """
        return cls._get('backup')

    @classmethod
    def local(cls):
        """This is a local copy of the jobs folder. Useful to take advantage
        when needing quick access to storage using the local SSD drive.

        """
        return cls._get('local')

    @classmethod
    def servers(cls, get_all=False):
        """Returns all available servers."""
        arr = []
        parser = cls.conf()
        d = {}
        for section in parser.sections():
            d[section] = {}
            for key, val in parser.items(section):
                d[section][key] = val
        for v in d.itervalues():
            if get_all:
                if not any((v['win'], v['mac'])):
                    continue
                arr.append({u'path': v['win'], u'platform': u'win',
                            u'description': v[u'description']})
                arr.append({u'path': v['mac'],  u'platform': u'mac',
                            u'description': v[u'description']})
            else:
                platform = get_platform()
                if not v[platform]:
                    continue
                if not v[platform]:
                    continue
                arr.append({u'path': v[platform], u'platform': platform,
                            u'description': v[u'description']})
        arr = sorted(arr, key=lambda x: x[u'path'])
        return arr


ASSET_IDENTIFIER = u'workspace.mel'
"""``ASSET_IDENTIFIER`` is the file needed for GWBrowser to understand a folder
as an asset. We're using the maya project structure as our asset-base so this is
a **workspace.mel** file in our case. The file resides in the root of the asset
directory."""


FTHREAD_COUNT = 1
"""The number of threads used by the ``FilesWidget`` to get file - information."""

LTHREAD_COUNT = 1
"""The number of threads used by the ``DataKeyModel`` to count files."""

FTIMER_INTERVAL = 800  # 1.0 sec
"""The frequency of querrying lists to load file and thumbnail info"""


ALEMBIC_EXPORT_PATH = u'{workspace}/{exports}/abc/{set}/{set}_v001.abc'
CAPTURE_PATH = u'viewport_captures/animation'
FFMPEG_COMMAND = u'-loglevel info -hide_banner -y -framerate {framerate} -start_number {start} -i "{source}" -c:v libx264 -crf 25 -vf format=yuv420p -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" "{dest}"'

ExportsFolder = u'exports'
DataFolder = u'data'
ReferenceFolder = u'references'
RendersFolder = u'renders'
ScenesFolder = u'scenes'
ScriptsFolder = u'scripts'
TexturesFolder = u'textures'

ASSET_FOLDERS = {
    ExportsFolder: u'User exported animation, object and simulation cache files',
    DataFolder: u'System exported caches files',
    ReferenceFolder: u'Files used for research, reference',
    RendersFolder: u'Images rendered by the scene files',
    ScenesFolder: u'Project files for all 2D and 3D scenes',
    ScriptsFolder: u'Technical dependencies',
    TexturesFolder: u'Textures used by the 2D/3D projects',
    u'misc': u'',
}

# Sizes
ROW_HEIGHT = 34.0
BOOKMARK_ROW_HEIGHT = 42.0
ASSET_ROW_HEIGHT = 78.0
CONTROL_HEIGHT = 34.0
ROW_SEPARATOR = 1.0

INLINE_ICONS_MIN_WIDTH = 320.0

# Font scaling seems at best random given platform differences.
# Programmatically scaling might fix matters...
SMALL_FONT_SIZE = 7.5
MEDIUM_FONT_SIZE = 8.5
LARGE_FONT_SIZE = 12.0

pscale = 1.0
"""The global font scale value. Not implemeted yet."""


def psize(n):
    """On macosx the font size seem to be smaller given the same point size....
    Sadly I have to use this function to scale the fonts to an acceptable size.
    I haven't figured out where the difference comes from or what the differences
    refers to. Difference of dpi...?

    """
    return n * 1.5 if get_platform() == u'mac' else n * pscale


def rgb(color):
    """Returns an rgba string representation of the given color.

    Args:
        color (QtGui.QColor): The `QColor` to convert.

    Returns:
        unicode: The string representation of the color./

    """
    return u'{},{},{},{}'.format(*color.getRgb())


MARGIN = 20.0

INDICATOR_WIDTH = 4.0
ROW_BUTTONS_HEIGHT = 36.0

WIDTH = 640.0
HEIGHT = 480.0

INLINE_ICON_SIZE = 18.0
THUMBNAIL_IMAGE_SIZE = 840.0

BACKGROUND_SELECTED = QtGui.QColor(140, 140, 140)
SECONDARY_BACKGROUND = QtGui.QColor(70, 70, 70)
BACKGROUND = QtGui.QColor(95, 95, 95)
THUMBNAIL_BACKGROUND = SECONDARY_BACKGROUND

TEXT = QtGui.QColor(220, 220, 220)
TEXT_SELECTED = QtGui.QColor(250, 250, 250)
TEXT_DISABLED = QtGui.QColor(140, 140, 140)

TEXT_NOTE = QtGui.QColor(150, 150, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)

SEPARATOR = QtGui.QColor(50, 50, 50)
FAVOURITE = QtGui.QColor(107, 126, 180)
REMOVE = QtGui.QColor(219, 114, 114)
ADD = QtGui.QColor(90, 200, 155)

PrimaryFont = QtGui.QFont(u'Roboto Black')
PrimaryFont.setPointSizeF(MEDIUM_FONT_SIZE)
SecondaryFont = QtGui.QFont(u'Roboto Medium')
SecondaryFont.setPointSizeF(SMALL_FONT_SIZE)


def qlast_modified(n): return QtCore.QDateTime.fromMSecsSinceEpoch(n * 1000)


def get_oiio_extensions():
    """Returns a list of extension OpenImageIO is capable of reading."""
    extensions = []
    for f in OpenImageIO.get_string_attribute(u'extension_list').split(u';'):
        extensions = extensions + f.split(u':')[-1].split(u',')
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
    allfiles = u'All files ({})'.format(allfiles)
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
ParentPathRole = 1026
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
SettingsRole = 1044

SortByName = 2048
SortByLastModified = 2049
SortBySize = 2050

FileItem = 1100
SequenceItem = 1200

LowerCase = 0
UpperCase = 1
"""Filename styles"""


FilterTextRegex = re.compile(ur'[^0-9\.\#\-\_\/a-zA-Z]+')
"""This is the valid string accepted by the filter editor."""

SORT_WITH_BASENAME = False


def namekey(s):
    """Key function used to sort alphanumeric filenames."""
    if SORT_WITH_BASENAME:
        return [int(f) if f.isdigit() else f for f in s.split('/').pop().lower()]
    return [int(f) if f.isdigit() else f for f in s.strip('/').lower()]


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
    from gwbrowser.imagecache import ImageCache
    with open(path, 'r') as f:
        f.seek(0)
        qss = f.read()
        qss = qss.encode(encoding='UTF-8', errors='strict')

        try:
            qss = qss.format(
                PRIMARY_FONT=PrimaryFont.family(),
                SECONDARY_FONT=SecondaryFont.family(),
                SMALL_FONT_SIZE=psize(SMALL_FONT_SIZE),
                MEDIUM_FONT_SIZE=psize(MEDIUM_FONT_SIZE),
                LARGE_FONT_SIZE=psize(LARGE_FONT_SIZE),
                BACKGROUND=rgb(BACKGROUND),
                BACKGROUND_SELECTED=rgb(BACKGROUND_SELECTED),
                SECONDARY_BACKGROUND=rgb(SECONDARY_BACKGROUND),
                TEXT=rgb(TEXT),
                SECONDARY_TEXT=rgb(SECONDARY_TEXT),
                TEXT_DISABLED=rgb(TEXT_DISABLED),
                TEXT_SELECTED=rgb(TEXT_SELECTED),
                SEPARATOR=rgb(SEPARATOR),
                FAVOURITE=rgb(FAVOURITE),
                BRANCH_CLOSED=ImageCache.get_rsc_pixmap(
                    u'branch_closed', None, None, get_path=True),
                BRANCH_OPEN=ImageCache.get_rsc_pixmap(
                    u'branch_open', None, None, get_path=True)
            )
        except KeyError as err:
            msg = u'Looks like there might be an error in the css file: {}'.format(
                err)
            raise KeyError(msg)
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
    if get_platform() == u'win':
        args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        return QtCore.QProcess.startDetached(u'explorer', args)

    if get_platform() == u'mac':
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
PathHighlight = 0b100000

HIGHLIGHT_RULES = {
    u'url': {
        u're': re.compile(
            ur'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': PathHighlight
    },
    u'spaces': {
        u're': re.compile(
            ur'([\s\t\n\r]*)',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': CodeHighlight
    },
    u'file_path': {
        u're': re.compile(
            ur'/^(?:(?:https?|ftp):\/\/)(?:\S+(?::\S*)?@)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:\/[^\s]*)?$/',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': PathHighlight
    },
    u'folder_path': {
        u're': re.compile(
            ur'([a-z]{2,5}:)?([\/\\]{2}[^\"\*\<\>\?\|\s]+)',
            flags=re.IGNORECASE | re.UNICODE),
        u'flag': PathHighlight
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
    """Given an array of numbers the method will return a string representation of
    the ranges contained in the array.

    Args:
        arr(list):       An array of numbers.
        padding(int):    The number of leading zeros before the number.

    Returns:
        unicode: A string representation of the given array.

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
    return u','.join([u'-'.join(sorted(list(set([blocks[k][0], blocks[k][-1]])))) for k in blocks])


ValidFilenameRegex = re.compile(
    ur'^.*([a-zA-Z0-9]+?)\_(.*)\_(.+?)\_([a-zA-Z0-9]+)\_v([0-9]{1,4})\.([a-zA-Z0-9]+$)',
    flags=re.IGNORECASE | re.UNICODE)
IsSequenceRegex = re.compile(
    ur'^(.+?)(\[.*\])(.*)$', flags=re.IGNORECASE | re.UNICODE)
SequenceStartRegex = re.compile(
    ur'^(.*)\[([0-9]+).*\](.*)$',
    flags=re.IGNORECASE | re.UNICODE)
SequenceEndRegex = re.compile(
    ur'^(.*)\[.*?([0-9]+)\](.*)$',
    flags=re.IGNORECASE | re.UNICODE)
GetSequenceRegex = re.compile(
    ur'^(.*?)([0-9]+)([0-9\\/]*|[^0-9\\/]*(?=.+?))\.([^\.]{2,5})$',
    flags=re.IGNORECASE | re.UNICODE)


def is_valid_filename(text):
    """This method will check if the given text conforms Browser's enforced
    filenaming convention.

    The returned SRE.Match object will contain the groups descripbed below.

    .. code-block:: python

       f = u'000_pr_000_layout_gw_v0006.ma'
       match = common.get_valid_filename(f)
       if match:
           path = match.expand(ur'\\1\\2\\3\\4\\5.\\6')

    Args:
        group 1(SRE_Match object):        "000" - prefix name.
        group 2(SRE_Match object):        "pr_000" - asset name.
        group 3(SRE_Match object):        "layout" - mode name.
        group 4(SRE_Match object):        "gw" - user name.
        group 5(SRE_Match object):        "0006" - version without the 'v' prefix.
        group 6(SRE_Match object):        "ma" - file extension without the '.'.

    Returns:
        SRE_Match: A ``SRE_Match`` object if the filename is valid, otherwise ``None``

    """
    return ValidFilenameRegex.search(text)


def get_sequence(text):
    """This method will check if the given text contains a sequence element.

    Strictly speaking, a sequence is any file that has a valid number element.
    There can only be **one** incrementable element - it will always be the
    number closest to the end.

    The regex will understand sequences with the `v` prefix, eg *v001*, *v002*,
    but works without the prefix as well. Eg. **001**, **002**. In the case of a
    filename like ``job_sh010_animation_v002.c4d`` **002** will be the
    prevailing sequence number, ignoring the number in the extension.

    Likewise, in ``job_sh010_animation_v002.0001.c4d`` the sequence number will
    be **0001**, and not 010 or 002.

    Args:
        group 1 (SRE_Match):    All the characters **before** the sequence number.
        group 2 (SRE_Match):    The sequence number, as a string.
        group 3 (SRE_Match):    All the characters **after** the sequence number.

    .. code-block:: python

       filename = 'job_sh010_animation_v002_wgergely.c4d'
       match = common.get_sequence(filename)
       if match:
           prefix = match.group(1) # 'job_sh010_animation_v'
           sequence_number = match.group(2) # '002'
           suffix = match.group(3) # '_wgergely.c4d'

    Returns:
        ``SRE_Match``: ``None`` if the text doesn't contain a number or an ``SRE_Match`` object.

    """
    return GetSequenceRegex.search(text)


def is_collapsed(text):
    """This method will check for the presence of the bracket-enclosed sequence markers.

    When GWBrowser is displaying a sequence of files as a single item,
    the item is *collapsed*. Every collapsed item contains a start and an end number
    enclosed in brackets. For instance: ``image_sequence_[001-233].png``

    Args:
        group 1 (SRE_Match):    All the characters **before** the sequence marker.
        group 2 (SRE_Match):    The sequence marker(eg. ``[01-50]``), as a string.
        group 3 (SRE_Match):    All the characters **after** the sequence marker.

    .. code-block:: python

       filename = 'job_sh010_animation_[001-299]_wgergely.png'
       match = common.get_sequence(filename)
       if match:
           prefix = match.group(1) # 'job_sh010_animation_'
           sequence_string = match.group(2) # '[001-299]'
           suffix = match.group(3) # '_wgergely.png'

    Returns:
        ``SRE_Match``: If the given name is indeed collpased it returns a ``SRE_Match`` object, otherwise ``None``.

    """
    return IsSequenceRegex.search(text)


def get_sequence_startpath(path):
    """If the given path refers to a collapsed item, it will get the name of the
    the first item in the sequence. In the case of **[0-99]**, the first item is
    **0**.

    Returns:
        ``unicode``: The name of the first element in the sequence.

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
    """Allows drawing aliased text using *QPainterPath*.

    This is a slow to calculate but ensures the rendered text looks *smooth* (on
    Windows espcially, I noticed a lot of aliasing issues). We're also eliding
    the given text to the width of the given rectangle.

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

    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)

    x, y = (rect.left(), rect.top())
    elide = None
    metrics = QtGui.QFontMetricsF(font)

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
    return entry.path


def mount():
    """Mounts the server in macosx if it isn't mounted already."""
    # No need to do anything in windows
    if get_platform() == u'win':
        return

    if get_platform() == u'mac':
        mountpoint = u'/volumes/{}'.format(Server.primary()).split(u'/').pop()

        for d in QtCore.QStorageInfo.mountedVolumes():
            if d.rootPath().lower() == mountpoint.lower():
                return  # the server is already mounted and we're good to go

        if QtWidgets.QApplication.instance():
            mbox = QtWidgets.QMessageBox()
            mbox.setWindowTitle(u'Server no mounted')
            mbox.setText(
                u'Could not find {} - it probably is not mounted.'.format(
                    Server.primary())
            )
            mbox.setInformativeText(
                u'Primary ({}) server is not mounted. Make sure to mount it before launching GWBrowser.')
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Ok
            )


WindowsPath = 0
UnixPath = 1
SlackPath = 2
MacOSPath = 3


def copy_path(index, mode=WindowsPath, first=True):
    """Copies the given path to the clipboard. We have to do some magic here
    for the copied paths to be fully qualified."""
    server = index.data(ParentPathRole)[0]
    path = index.data(QtCore.Qt.StatusTipRole)
    if first:
        path = get_sequence_startpath(path)
    else:
        path = get_sequence_endpath(path)

    win_server = Server.get_server_platform_name(server, u'win')
    mac_server = Server.get_server_platform_name(server, u'mac')

    if not win_server:
        file_path = index.data(QtCore.Qt.StatusTipRole)
        for server in Server.servers(get_all=True):
            if server[u'platform'] != 'win':
                continue
            if file_path.startswith(server['path']):
                win_server = Server.get_server_platform_name(
                    server[u'path'], u'win')
                server = server[u'path']
                break

    if not mac_server:
        file_path = index.data(QtCore.Qt.StatusTipRole)
        for server in Server.servers(get_all=True):
            if server[u'platform'] != 'win':
                continue
            if file_path.startswith(server['path']):
                mac_server = Server.get_server_platform_name(
                    server[u'path'], u'mac')
                server = server[u'path']
                break

    if not any((win_server, mac_server)):
        QtGui.QClipboard().setText(path)
        print '# Copied {}'.format(path)
        return path

    win_server = win_server.rstrip('/')
    mac_server = mac_server.rstrip('/')

    if mode == WindowsPath:
        if server.lower() in path.lower():
            path = path.replace(server, win_server)
        path = re.sub(ur'[\/\\]', ur'\\', path)
        QtGui.QClipboard().setText(path)
        print '# Copied {}'.format(path)
        return

    if mode == UnixPath:
        path = re.sub(ur'[\/\\]', ur'/', path)
        QtGui.QClipboard().setText(path)
        print '# Copied {}'.format(path)
        return path

    if mode == SlackPath:
        path = QtCore.QUrl().fromLocalFile(path).toString()
        QtGui.QClipboard().setText(path)
        print '# Copied {}'.format(path)
        return path

    if mode == MacOSPath:
        if server.lower() in path.lower():
            path = path.replace(server, mac_server)
        path = re.sub(ur'[\/\\]', ur'/', path)
        QtGui.QClipboard().setText(path)
        print '# Copied {}'.format(path)
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



def walk(path):
    """This is a custom generator expression using scandir's `walk`.
    We're using the C module for performance's sake without python-native
    fallbacks. The method yields each found DirEntry.

    The used _scandir module itself is customized to contain the addittional
    ``DirEntry.relativepath(unicode: basepath)`` method and ``DirEntry.dirpath``
    attribute.

    Yields:
        DirEntry:   A ctype class.

    """
    # MacOS/Windows encoding error workaround
    try:
        top = unicode(path, u'utf-8')
    except TypeError:
        try:
            top = top.decode(sys.getfilesystemencoding())
        except:
            pass

    try:
        it = gwscandir.scandir(path=path)
    except OSError as error:
        return

    while True:
        try:
            try:
                entry = next(it)
            except StopIteration:
                break
        except OSError as error:
            return

        try:
            is_dir = entry.is_dir()
        except OSError:
            is_dir = False

        if not is_dir:
            yield entry

        try:
            is_symlink = entry.is_symlink()
        except OSError:
            is_symlink = False
        if not is_symlink:
            for entry in walk(entry.path):
                yield entry


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
    MayaAssetTemplate: u'Asset',
    ProjectTemplate: u'Job',
}


def create_asset_from_template(name, basepath, template):
    """Creates a new asset with the given name.

    An asset is a zip-archive containing the pre-defined folder structure for
    jobs and assets. The available asset types are defined in the
    ``common.AssetTypes`` variable.

    Args:
        name (unicode):         The name of the asset to create.
        basepath (unicode):     The path the asset should be saved to.
        template (unicode):     The name of the template file *without* the zip extension.

    """
    datadir = next(f for f in QtCore.QStandardPaths.standardLocations(
        QtCore.QStandardPaths.DocumentsLocation))
    template_info = QtCore.QFileInfo(
        u'{}/{}/{}.zip'.format(datadir, PRODUCT, AssetTypes[template]))
    if not template_info.exists():
        mbox = QtWidgets.QMessageBox()
        mbox.setWindowTitle(u'Error creating asset')
        mbox.setText('The template file could not be located.')
        mbox.setInformativeText(
            'Make sure the Asset.zip and Job.zip files exist and are valid.\n\nTemplate must be placed here:\n{}'.format(template_info.filePath()))
        mbox.exec_()
        raise RuntimeError(
            u'The "{}.zip" template file could not be located.'.format(AssetTypes[template]))

    dest_info = QtCore.QDir(u'{}/{}'.format(basepath, name))
    if not dest_info.exists():
        res = QtCore.QDir(basepath).mkdir(name)
        if not res:
            raise RuntimeError(u'An error occured creating the asset folders.')
    with zipfile.ZipFile(template_info.absoluteFilePath(), 'r', zipfile.ZIP_DEFLATED) as f:
        f.extractall(dest_info.absolutePath(), members=None, pwd=None)


def push_to_rv(path):
    """Pushes the given given path to RV."""
    import subprocess
    from gwbrowser.settings import local_settings
    def get_preference(k): return local_settings.value(
        u'preferences/IntegrationSettings/{}'.format(k))

    def alert():
        mbox = QtWidgets.QMessageBox()
        mbox.setWindowTitle(u'RV not set')
        mbox.setText(u'Could not push to RV:\nRV was not found.')
        mbox.setIcon(QtWidgets.QMessageBox.Warning)
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
        mbox.exec_()

    rv_path = get_preference(u'rv_path')
    if not rv_path:
        alert()
        return

    rv_info = QtCore.QFileInfo(rv_path)
    if not rv_info.exists():
        alert()
        return

    if get_platform() == u'win':
        rv_push_path = u'{}/rvpush.exe'.format(rv_info.path())
        if QtCore.QFileInfo(rv_push_path).exists():
            cmd = u'"{}" -tag GWBrowser set "{}"'.format(rv_push_path, path)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            subprocess.Popen(cmd, startupinfo=startupinfo)

create_temp_dir()
