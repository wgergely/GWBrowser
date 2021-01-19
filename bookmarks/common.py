# -*- coding: utf-8 -*-
"""Common methods and variables used across the project.

File sequences are recognised using regexes defined in this module. See
:func:`.get_valid_filename`, :func:`.get_sequence`, :func:`.is_collapsed`,
:func:`.get_sequence_startpath`,  :func:`.get_ranges` for more information.

"""
import subprocess
import functools
import traceback
import inspect
import time
import os
import sys
import re
import zipfile
import hashlib
import weakref
import _scandir

from PySide2 import QtGui, QtCore, QtWidgets
import OpenImageIO


SERVERS = []

font_db = None  # Must be set before bookmarks is initialized
STANDALONE = True  # The current mode of bookmarks
PRODUCT = u'Bookmarks'
ABOUT_URL = ur'https://github.com/wgergely/bookmarks'

BOOKMARK_ROOT_DIR = u'.bookmark'
BOOKMARK_ROOT_KEY = 'BOOKMARKS_ROOT'

SynchronisedMode = 0
SoloMode = 1
"""Enum used to indicate the mode. When syncronised mode is on, the active path
selections will be syncronised across DCCs and desktop instances."""

# Flags
MarkedAsArchived =  0b1000000000
MarkedAsFavourite = 0b10000000000
MarkedAsActive =    0b100000000000
"""Custom Item flags."""

InfoThread = 0
ThumbnailThread = 1
"""Thread types."""

MAXITEMS = 999999
"""The maximum number of items a model is allowed to load."""

SEQPROXY = u'[0]'
""""""


def error(func):
    """Decorator to create a menu set."""
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            from . import common_ui
            from . import log

            info = sys.exc_info()
            if all(info):
                e = u''.join(traceback.format_exception(*info))
            else:
                e = u''
            if QtWidgets.QApplication.instance():
                common_ui.ErrorBox(u'An error occured.', e).open()
            log.error(e)
            raise
    return func_wrapper


def debug(func):
    """Decorator to create a menu set."""
    DEBUG_MESSAGE = u'{trace}(): Executed in {time} secs.'
    DEBUG_SEPARATOR = ' --> '

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        from . import log
        try:
            if log.LOG_DEBUG:
                t = time.time()
            return func(*args, **kwargs)
        finally:
            if args and hasattr(args[0], '__class__'):
                funcname = '{}.{}'.format(
                    args[0].__class__,
                    func.func_name
                )
            else:
                funcname = func.func_name

            if log.LOG_DEBUG:
                trace = []
                for frame in reversed(inspect.stack()):
                    if frame[3] == '<module>':
                        continue
                    mod = inspect.getmodule(frame[0]).__name__
                    _funcname = '{}.{}'.format(mod, frame[3])
                    trace.append(_funcname)
                trace.append(funcname)

                log.debug(
                    DEBUG_MESSAGE.format(
                        trace=DEBUG_SEPARATOR.join(trace),
                        time=time.time() - t
                    )
                )

    return func_wrapper



def toggle_on_top(window, v):
    """Sets the WindowStaysOnTopHint for the window.

    """
    from . import settings
    settings.local_settings.setValue(
        settings.UIStateSection,
        settings.WindowAlwaysOnTopKey,
        not v
    )
    flags = window.windowFlags()
    window.hide()

    if flags & QtCore.Qt.WindowStaysOnTopHint:
        flags = flags & ~QtCore.Qt.WindowStaysOnTopHint
    else:
        flags = flags | QtCore.Qt.WindowStaysOnTopHint
    window.setWindowFlags(flags)
    window.showNormal()
    window.activateWindow()

def toggle_frameless(window, v):
    """Sets the WindowStaysOnTopHint for the window.

    """
    from . import settings
    settings.local_settings.setValue(
        settings.UIStateSection,
        settings.WindowFramelessKey,
        not v
    )

    flags = window.windowFlags()
    window.hide()

    if flags & QtCore.Qt.FramelessWindowHint:
        flags = flags & ~QtCore.Qt.FramelessWindowHint
        o = 0
    else:
        flags = flags | QtCore.Qt.FramelessWindowHint
        o = INDICATOR_WIDTH()

    window._frameless = not v
    window.setAttribute(QtCore.Qt.WA_NoSystemBackground, on=not v)
    window.setAttribute(QtCore.Qt.WA_TranslucentBackground, on=not v)
    window.layout().setContentsMargins(o, o, o, o)
    window.headerwidget.setHidden(v)
    window.headerwidget.setDisabled(v)
    window.setWindowFlags(flags)
    window.showNormal()
    window.activateWindow()



def get_oiio_namefilters():
    """Gets all accepted formats from the oiio build as a namefilter list.
    Use the return value on the QFileDialog.setNameFilters() method.

    """
    extension_list = OpenImageIO.get_string_attribute('extension_list')
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

    allfiles = [u'*.{}'.format(f) for f in arr]
    allfiles = u' '.join(allfiles)
    allfiles = u'All files ({})'.format(allfiles)
    namefilters.insert(0, allfiles)
    return u';;'.join(namefilters)


# Extending the
FlagsRole = QtCore.Qt.UserRole + 1
ParentPathRole = FlagsRole + 1
DescriptionRole = ParentPathRole + 1
TodoCountRole = DescriptionRole + 1
FileDetailsRole = TodoCountRole + 1
SequenceRole = FileDetailsRole + 1  # SRE Match object
FramesRole = SequenceRole + 1  # List of frame names
FileInfoLoaded = FramesRole + 1
ThumbnailLoaded = FileInfoLoaded + 1
StartpathRole = ThumbnailLoaded + 1
EndpathRole = StartpathRole + 1
TypeRole = EndpathRole + 1
EntryRole = TypeRole + 1
IdRole = EntryRole + 1
SortByNameRole = IdRole + 1
SortByLastModifiedRole = SortByNameRole + 1
SortBySizeRole = SortByLastModifiedRole + 1
TextSegmentRole = SortBySizeRole + 1
"""Model data roles."""

FileItem = 1100
SequenceItem = 1200
"""Model data types."""

SORT_WITH_BASENAME = False

IsSequenceRegex = re.compile(
    ur'^(.+?)(\[.*\])(.*)$', flags=re.IGNORECASE | re.UNICODE)
SequenceStartRegex = re.compile(
    ur'^(.*)\[([0-9]+).*\](.*)$',
    flags=re.IGNORECASE | re.UNICODE)
SequenceEndRegex = re.compile(
    ur'^(.*)\[.*?([0-9]+)\](.*)$',
    flags=re.IGNORECASE | re.UNICODE)
GetSequenceRegex = re.compile(
    ur'^(.*?)([0-9]+)([0-9\\/]*|[^0-9\\/]*(?=.+?))\.([^\.]{1,})$',
    flags=re.IGNORECASE | re.UNICODE)

WindowsPath = 0
UnixPath = WindowsPath + 1
SlackPath = UnixPath + 1
MacOSPath = SlackPath + 1

PrimaryFontRole = 0
SecondaryFontRole = PrimaryFontRole + 1
MetricsRole = SecondaryFontRole + 1


def get_platform():
    """Returns the name of the current platform.

    Returns:
        unicode: *mac* or *win*, depending on the platform.

    Raises:
        NotImplementedError: If the current platform is not supported.

    """
    ptype = QtCore.QSysInfo().productType().lower()
    if ptype in (u'darwin', u'osx', u'macos'):
        return u'mac'
    if u'win' in ptype:
        return u'win'
    raise NotImplementedError(
        u'The platform "{}" is not supported'.format(ptype))


UI_SCALE = 1.0
"""The global UI scale value. Depending on context, this should correspond to
any UI scaling set in the host DCC. In standalone mode the app factors in the
current DPI scaling and scales the UI accordingly."""

THUMBNAIL_IMAGE_SIZE = 512.0
THUMBNAIL_FORMAT = u'png'

cursor = QtGui.QCursor()


if get_platform() == u'mac':
    DPI = 96.0
else:
    DPI = 72.0


def SMALL_FONT_SIZE(): return int(psize(11.0))  # 8.5pt@72dbpi


def MEDIUM_FONT_SIZE(): return int(psize(12.0))  # 9pt@72dpi


def LARGE_FONT_SIZE(): return int(psize(16.0))  # 12pt@72dpi


def ROW_HEIGHT(): return int(psize(34.0))


def BOOKMARK_ROW_HEIGHT(): return int(psize(40.0))


def ASSET_ROW_HEIGHT(): return int(psize(64.0))


def ROW_SEPARATOR(): return int(psize(1.0))


def MARGIN(): return int(psize(18.0))


def INDICATOR_WIDTH(): return int(psize(4.0))


def WIDTH(): return int(psize(640.0))


def HEIGHT(): return int(psize(480.0))



BACKGROUND_SELECTED = QtGui.QColor(140, 140, 140)
SECONDARY_BACKGROUND = QtGui.QColor(60, 60, 60)
BACKGROUND = QtGui.QColor(80, 80, 80)

TEXT = QtGui.QColor(220, 220, 220)
TEXT_SELECTED = QtGui.QColor(250, 250, 250)
TEXT_DISABLED = QtGui.QColor(140, 140, 140)

TEXT_NOTE = QtGui.QColor(150, 150, 255)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)

SEPARATOR = QtGui.QColor(45, 45, 45)
FAVOURITE = QtGui.QColor(107, 135, 165)
REMOVE = QtGui.QColor(219, 114, 114)
ADD = QtGui.QColor(90, 200, 155)
THUMBNAIL_BACKGROUND = SEPARATOR

TRANSPARENT = QtGui.QColor(0, 0, 0, 0)


def psize(n):
    """Returns a scaled UI value.
    All UI values are assumed to be in `pixels`.

    """
    return (float(n) * (float(DPI) / 72.0)) * float(UI_SCALE)


HASH_DATA = {}


def get_hash(key):
    """Calculate md5 hash for a file path.

    The resulting hash is used by the ImageCache. local settings and BookmarkDB to store
    associated data.

    Args:
        key (unicode): A unicode string to calculate a md5 hash for.
        server (unicode): The name of the server.

    Returns:
        str: Value of the calculated md5 hexadecimal digest as a `str`.

    """
    if not isinstance(key, unicode):
        raise TypeError(
            u'Expected <type \'unicode\'>, got {}'.format(type(key)))

    if key in HASH_DATA:
        return HASH_DATA[key]

    # Path must not contain backslashes
    if u'\\' in key:
        key = key.replace(u'\\', u'/')

    # The hash key is server agnostic. We'll check the key against all saved
    # servers and remove it if found in the key.
    s = [f for f in SERVERS if f in key]
    if s:
        s = s[0]
        l = len(s)
        if key[:l] == s:
            key = key[l:]

    key = key.encode('utf-8')
    if key in HASH_DATA:
        return HASH_DATA[key]

    # Otherwise, we calculate, save and return the digest
    HASH_DATA[key] = hashlib.md5(key).hexdigest()
    return HASH_DATA[key]


def proxy_path(v):
    """Encompasses the logic used to associate preferences with items.

    Sequence items need a generic key to save values as the sequence notation
    might change as files are added/removed to image seuquences. Any `FileItem`
    will use their file path as the key and SequenceItems will use `[0]` in place
    of their frame-range notation.

    Args:
        v (QModelIndex, dict or unicode): Data dict, index or filepath string.

    Returns:
        unicode: The key used to store the items information in the local
        preferences and the bookmarks database.

    """
    if isinstance(v, weakref.ref):
        v = v()[QtCore.Qt.StatusTipRole]
    if isinstance(v, dict):
        v = v[QtCore.Qt.StatusTipRole]
    elif isinstance(v, QtCore.QModelIndex):
        v = v.data(QtCore.Qt.StatusTipRole)
    elif isinstance(v, unicode):
        pass
    else:
        from . import log
        s = u'Invalid type. Expected `<type \'unicode\'>'
        log.error(s)
        raise ValueError(s)

    collapsed = is_collapsed(v)
    if collapsed:
        return collapsed.group(1) + SEQPROXY + collapsed.group(3)
    seq = get_sequence(v)
    if seq:
        return seq.group(1) + SEQPROXY + seq.group(3) + u'.' + seq.group(4)
    return v


def rgb(color):
    """Returns an rgba string representation of the given color.

    Args:
        color (QtGui.QColor): The `QColor` to convert.

    Returns:
        unicode: The string representation of the color./

    """
    return u'{},{},{},{}'.format(*color.getRgb())


def get_username():
    """Get the name of the currently logged-in user."""
    n = QtCore.QFileInfo(os.path.expanduser(u'~')).fileName()
    n = re.sub(ur'[^a-zA-Z0-9]*', u'', n, flags=re.IGNORECASE | re.UNICODE)
    return n


def qlast_modified(n): return QtCore.QDateTime.fromMSecsSinceEpoch(n * 1000)


def namekey(s):
    """Utility function used for alphanumerically sorting filenames.

    """
    if SORT_WITH_BASENAME:
        s = s.split(u'/').pop()  # order by filename
    elif len(s.split(u'/')) > 1:
        s = u'Ω' + s
    return [int(f) if f.isdigit() else f for f in s]


def move_widget_to_available_geo(widget):
    """Moves the widget inside the available screen geomtery, if any of the
    edges fall outside of it.

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


def set_custom_stylesheet(widget):
    """Applies the app's custom stylesheet to the given widget."""
    from . import images

    path = os.path.normpath(
        os.path.abspath(
            os.path.join(
                __file__,
                os.pardir,
                u'rsc',
                u'stylesheet.css'
            )
        )
    )
    with open(path, 'r') as f:
        f.seek(0)
        qss = f.read()
        qss = qss.encode(encoding='UTF-8', errors='strict')

    try:
        qss = qss.format(
            PRIMARY_FONT=font_db.primary_font(MEDIUM_FONT_SIZE())[0].family(),
            SECONDARY_FONT=font_db.secondary_font(
                SMALL_FONT_SIZE())[0].family(),
            SMALL_FONT_SIZE=int(SMALL_FONT_SIZE()),
            MEDIUM_FONT_SIZE=int(MEDIUM_FONT_SIZE()),
            LARGE_FONT_SIZE=int(LARGE_FONT_SIZE()),
            RADIUS=int(INDICATOR_WIDTH() * 1.5),
            RADIUS_SM=int(INDICATOR_WIDTH()),
            SCROLLBAR_SIZE=int(INDICATOR_WIDTH() * 2),
            SCROLLBAR_MINHEIGHT=int(MARGIN() * 5),
            ROW_SEPARATOR=int(ROW_SEPARATOR()),
            MARGIN=int(MARGIN()),
            CONTEXT_MENU_HEIGHT=int(MARGIN() * 1.5),
            CONTEXT_MENU_PADDING=int(MARGIN() * 0.333),
            ROW_HEIGHT=int(ROW_HEIGHT()),
            BACKGROUND=rgb(BACKGROUND),
            BACKGROUND_SELECTED=rgb(BACKGROUND_SELECTED),
            SECONDARY_BACKGROUND=rgb(SECONDARY_BACKGROUND),
            TEXT=rgb(TEXT),
            SECONDARY_TEXT=rgb(SECONDARY_TEXT),
            TEXT_DISABLED=rgb(TEXT_DISABLED),
            TEXT_SELECTED=rgb(TEXT_SELECTED),
            ADD=rgb(ADD),
            REMOVE=rgb(REMOVE),
            SEPARATOR=rgb(SEPARATOR),
            FAVOURITE=rgb(FAVOURITE),
            BRANCH_CLOSED=images.ImageCache.get_rsc_pixmap(
                u'branch_closed', None, None, get_path=True),
            BRANCH_OPEN=images.ImageCache.get_rsc_pixmap(
                u'branch_open', None, None, get_path=True),
            CHECKED=images.ImageCache.get_rsc_pixmap(
                u'check', None, None, get_path=True),
            UNCHECKED=images.ImageCache.get_rsc_pixmap(
                u'close', None, None, get_path=True),
        )
    except KeyError as err:
        from . import log
        msg = u'Looks like there might be an error in the stylesheet file: {}'.format(
            err)
        log.error(msg)
        raise KeyError(msg)
    widget.setStyleSheet(qss)


def reveal(path):
    """Reveals the specified folder in the file explorer.

    Args:
        name(unicode): A path to the file.

    """
    path = get_sequence_endpath(path)
    if get_platform() == u'win':
        if QtCore.QFileInfo(path).isFile():
            args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        elif QtCore.QFileInfo(path).isDir():
            path = os.path.normpath(os.path.abspath(path))
            args = [path,]
        else:
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


def copy_path(path, mode=WindowsPath, first=True, copy=True):
    """Copy a file path to the clipboard.

    The path will be conformed to the given `mode` (eg. forward slashes
    converted to back-slashes for `WindowsPath`).

    Args:
        path (unicode): Description of parameter `path`.
        mode (int):     Any of `WindowsPath`, `UnixPath`, `SlackPath` or
                        `MacOSPath`. Defaults to `WindowsPath`.
        first (bool):   If `True` copy the first item of a sequence.
        copy (bool):    If copy is false the converted path won't be copied to
                        the clipboard. Defaults to `True`.

    Returns:
        unicode: The converted path.

    """
    if first:
        path = get_sequence_startpath(path)
    else:
        path = get_sequence_endpath(path)

    # Normalise path
    path = re.sub(ur'[\/\\]', ur'/', path,
                  flags=re.IGNORECASE | re.UNICODE).strip(u'/')

    if mode == WindowsPath:
        prefix = u'//' if u':' not in path else u''
    elif mode == UnixPath:
        prefix = u'//' if u':' not in path else u''
    elif mode == SlackPath:
        prefix = u'file://'
    elif mode == MacOSPath:
        prefix = u'smb://'
        path = path.replace(u':', u'')
    else:
        prefix = u''
    path = prefix + path
    if mode == WindowsPath:
        path = re.sub(ur'[\/\\]', ur'\\', path,
                      flags=re.IGNORECASE | re.UNICODE)

    if copy:
        QtGui.QClipboard().setText(path)

        from . import log
        log.success(u'Copied {}'.format(path))

    return path


@QtCore.Slot(QtCore.QModelIndex)
def execute(index, first=False):
    """Given the model index, executes the index's path using `QDesktopServices`."""
    if not index.isValid():
        return
    path = index.data(QtCore.Qt.StatusTipRole)
    if first:
        path = get_sequence_startpath(path)
    else:
        path = get_sequence_endpath(path)

    url = QtCore.QUrl.fromLocalFile(path)
    QtGui.QDesktopServices.openUrl(url)


def get_sequence(s):
    """Check if the given text contains a sequence element.

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
        s (unicode): A file path.

    Returns:
        group 1 (SRE_Match):    All the characters **before** the sequence number.
        group 2 (SRE_Match):    The sequence number, as a string.
        group 3 (SRE_Match):    All the characters **after** the sequence number up until the file extensions.
        group 4 (SRE_Match):    The file extension **without** the '.' dot.

    .. code-block:: python

       s = u'job_sh010_animation_v002_wgergely.c4d'
       m = get_sequence(s)
       if m:
           prefix = match.group(1)
           sequence_number = match.group(2)
           suffix = match.group(3)
           extension = match.group(4)

    Returns:
        ``SRE_Match``: ``None`` if the text doesn't contain a number or an ``SRE_Match`` object.

    """
    if not isinstance(s, unicode):
        raise ValueError(
            u'Expected <type \'unicode\'>, got {}'.format(type(s)))
    if is_collapsed(s):
        raise RuntimeError(
            'Cannot extract sequence number from collapsed items.')
    return GetSequenceRegex.search(s)


def is_collapsed(s):
    """Check for the presence of the bracket-enclosed sequence markers.

    When Bookmarks is displaying a sequence of files as a single item,
    the item is *collapsed*. Every collapsed item contains a start and an end number
    enclosed in brackets. For instance: ``image_sequence_[001-233].png``

    Args:
        s (unicode): A file path.

    Returns:
        group 1 (SRE_Match):    All the characters **before** the sequence marker.
        group 2 (SRE_Match):    The sequence marker(eg. ``[01-50]``), as a string.
        group 3 (SRE_Match):    All the characters **after** the sequence marker.

    .. code-block:: python

       filename = 'job_sh010_animation_[001-299]_wgergely.png'
       m = is_collapsed(filename)
       if m:
           prefix = match.group(1) # 'job_sh010_animation_'
           sequence_string = match.group(2) # '[001-299]'
           suffix = match.group(3) # '_wgergely.png'

    Returns:
        ``SRE_Match``: If the given name is indeed collpased it returns a ``SRE_Match`` object, otherwise ``None``.

    """
    if not isinstance(s, unicode):
        raise ValueError(
            u'Expected <type \'unicode\'>, got {}'.format(type(s)))
    return IsSequenceRegex.search(s)


def get_sequence_startpath(path):
    """Checks the given string and if it denotes a seuqence returns the path for
    the first file.

    Args:
        s (unicode): A collapsed sequence name.

    Returns:
        unicode: The path to the first file of the sequence.

    """
    if not isinstance(path, unicode):
        raise ValueError(
            u'Expected <type \'unicode\'>, got {}'.format(type(path)))

    if not is_collapsed(path):
        return path

    match = SequenceStartRegex.search(path)
    if match:
        path = SequenceStartRegex.sub(ur'\1\2\3', path)
    return path


def get_sequence_endpath(path):
    """Checks the given string and if it denotes a seuqence returns the path for
    the last file.

    Args:
        s (unicode): A collapsed sequence name.

    Returns:
        unicode: The path to the last file of the sequence.

    """
    if not isinstance(path, unicode):
        raise ValueError(
            u'Expected <type \'unicode\'>, got {}'.format(type(path)))

    if not is_collapsed(path):
        return path

    match = SequenceEndRegex.search(path)
    if match:
        path = SequenceEndRegex.sub(ur'\1\2\3', path)
    return path


def get_sequence_paths(index):
    """Given the index, returns a tuple of filenames referring to the
    individual sequence items.

    Args:
        index (QtCore.QModelIndex): A listview index.

    """
    path = index.data(QtCore.Qt.StatusTipRole)
    if not is_collapsed(path):
        return path

    sequence_paths = []
    for frame in index.data(FramesRole):
        seq = index.data(SequenceRole)
        seq = seq.group(1) + frame + seq.group(3) + u'.' + seq.group(4)
        sequence_paths.append(seq)
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
    from .lists import delegate
    painter.save()

    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)

    elide = None
    metrics = QtGui.QFontMetrics(font)

    elide = QtCore.Qt.ElideLeft
    if QtCore.Qt.AlignLeft & align:
        elide = QtCore.Qt.ElideRight
    if QtCore.Qt.AlignRight & align:
        elide = QtCore.Qt.ElideLeft
    if QtCore.Qt.AlignHCenter & align:
        elide = QtCore.Qt.ElideMiddle

    text = metrics.elidedText(
        u'{}'.format(text),
        elide,
        rect.width() * 1.01)
    width = metrics.width(text)

    if QtCore.Qt.AlignLeft & align:
        x = rect.left()
    if QtCore.Qt.AlignRight & align:
        x = rect.right() - width
    if QtCore.Qt.AlignHCenter & align:
        x = rect.left() + (rect.width() * 0.5) - (width * 0.5)

    y = rect.center().y() + (metrics.ascent() * 0.5) - (metrics.descent() * 0.5)

    # Making sure text fits the rectangle
    painter.setBrush(color)
    painter.setPen(QtCore.Qt.NoPen)

    path = delegate.get_painter_path(x, y, font, text)
    painter.drawPath(path)

    painter.restore()
    return width


@error
@debug
def exec_instance():
    """Starts a new instance of Bookmarks."""
    if BOOKMARK_ROOT_KEY not in os.environ:
        s = u'Bookmarks does not seem to be installed correctly:\n'
        s += u'"{}" environment variable is not set'.format(BOOKMARK_ROOT_KEY)
        raise RuntimeError(s)

    if get_platform() == u'win':
        p = os.environ[BOOKMARK_ROOT_KEY] + \
            os.path.sep + 'bookmarks.exe'
        subprocess.Popen(p)
    else:
        raise NotImplementedError(u'Not yet implemented.')


class FontDatabase(QtGui.QFontDatabase):
    """Utility class for loading and getting the application's custom fonts.

    """
    CACHE = {
        PrimaryFontRole: {},
        SecondaryFontRole: {},
        MetricsRole: {},
    }

    def __init__(self, parent=None):
        if not QtWidgets.QApplication.instance():
            raise RuntimeError(
                'FontDatabase must be created after a QApplication was initiated.')
        super(FontDatabase, self).__init__(parent=parent)

        self._metrics = {}
        self.add_custom_fonts()

    def add_custom_fonts(self):
        """Load the fonts used by Bookmarks to the font database.

        """
        if u'bmRobotoMedium' in self.families():
            return

        p = u'{}/../rsc/fonts'.format(__file__)
        p = os.path.normpath(os.path.abspath(p))

        if not os.path.isdir(p):
            raise OSError('{} could not be found'.format(p))

        for entry in _scandir.scandir(p):
            if not entry.name.endswith(u'ttf'):
                continue
            idx = self.addApplicationFont(entry.path)
            if idx < 0:
                raise RuntimeError(
                    u'Failed to add required font to the application')
            family = self.applicationFontFamilies(idx)
            if not family:
                raise RuntimeError(
                    u'Failed to add required font to the application')

    def primary_font(self, font_size):
        """The primary font used by the application."""
        if font_size in self.CACHE[PrimaryFontRole]:
            return self.CACHE[PrimaryFontRole][font_size]
        font = self.font(u'bmRobotoBold', u'Bold', font_size)
        if font.family() != u'bmRobotoBold':
            raise RuntimeError(
                u'Failed to add required font to the application')
        font.setPixelSize(font_size)
        metrics = QtGui.QFontMetrics(font)
        self.CACHE[PrimaryFontRole][font_size] = (font, metrics)
        return self.CACHE[PrimaryFontRole][font_size]

    def secondary_font(self, font_size=SMALL_FONT_SIZE()):
        """The secondary font used by the application."""
        if font_size in self.CACHE[SecondaryFontRole]:
            return self.CACHE[SecondaryFontRole][font_size]
        font = self.font(u'bmRobotoMedium', u'Medium', font_size)
        if font.family() != u'bmRobotoMedium':
            raise RuntimeError(
                u'Failed to add required font to the application')
        font.setPixelSize(font_size)
        metrics = QtGui.QFontMetrics(font)
        self.CACHE[SecondaryFontRole][font_size] = (font, metrics)
        return self.CACHE[SecondaryFontRole][font_size]


class DataDict(dict):
    """Subclassed dict type for weakref compatibility."""
    pass
