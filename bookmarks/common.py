# -*- coding: utf-8 -*-
"""Common methods and variables used across the project.

File sequences are recognised using regexes defined in this module. See
:func:`.get_valid_filename`, :func:`.get_sequence`, :func:`.is_collapsed`,
:func:`.get_sequence_startpath`,  :func:`.get_ranges` for more information.

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import os
import re
import zipfile
import hashlib

from PySide2 import QtGui, QtCore, QtWidgets
import OpenImageIO

import bookmarks._scandir as _scandir


font_db = None # Must be set before bookmarks is initialized
STANDALONE = True  # The current mode of bookmarks
PRODUCT = u'Bookmarks'
ABOUT_URL = ur'https://gergely-wootsch.com/bookmarks'


SynchronisedMode = 0
SoloMode = 1
"""Enum used to indicate the mode. When syncronised mode is on, the active path
selections will be syncronised across DCCs and desktop instances."""


# Flags
MarkedAsArchived = 0b1000000000
MarkedAsFavourite = 0b10000000000
MarkedAsActive = 0b100000000000
"""Custom Item flags."""

InfoThread = 0
BackgroundInfoThread = 1
ThumbnailThread = 2
"""Thread types."""


def get_oiio_namefilters():
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
AssetCountRole = IdRole + 1
SortByNameRole = AssetCountRole + 1
SortByLastModifiedRole = SortByNameRole + 1
SortBySizeRole = SortByLastModifiedRole + 1
TextSegmentRole = SortBySizeRole + 1

FileItem = 1100
SequenceItem = 1200

SORT_WITH_BASENAME = False


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

WindowsPath = 0
UnixPath = 1
SlackPath = 2
MacOSPath = 3


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


THUMBNAIL_IMAGE_SIZE = 512.0
THUMBNAIL_FORMAT = u'png'


def psize(n):
    """There is a platform difference between font sizes on OSX and Win platforms.
    As defined sizes refer to appearance on Windows platforms, as this is
    where development happened so we'll scale values on MacOSX.

    """
    return (float(n) * (float(DPI) / 72.0)) * float(UI_SCALE)


HASH_DATA = {}


def get_hash(key, server=None):
    """MD5 hash of a string.

    The passed value is usually a file path and the resulting hash is used by
    the ImageCache and BookmarkDB to store associated data. If `key` is not
    unicode, it will be returned without modification.

    Args:
        key (unicode): A unicode string to calculate a md5 hash for.

    Returns:
        str: Value of the calculated md5 hexadecimal digest.

    """
    # Let's check wheter the key has already been saved
    if server is None and key in HASH_DATA:
        return HASH_DATA[key]

    if isinstance(key, int):
        return key

    if not isinstance(key, (unicode)):
        raise TypeError(
            u'Expected <type \'unicode\'>, got {}'.format(type(key)))

    # Sanitize the key and remove the server
    key = key.lower()
    if u'\\' in key:
        key = key.replace(u'\\', u'/')
    if server:
        server = server.lower()
        server = server.replace(u'\\', u'/')
        if key.startswith(server):
            key = key[len(server):]
    key = key.encode('utf-8')

    # ...and return it if already created
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
    if isinstance(v, dict):
        k = v[QtCore.Qt.StatusTipRole]

        if v[TypeRole] == FileItem:
            return k

        m = v[SequenceRole]
        if not m:
            return k

        return m.group(1) + u'[0]' + m.group(3) + u'.' + m.group(4)

    if isinstance(v, QtCore.QModelIndex):
        k = v.data(QtCore.Qt.StatusTipRole)

        if v.data(TypeRole) == FileItem:
            return k

        m = v.data(SequenceRole)
        if not m:
            return k
        return m.group(1) + u'[0]' + m.group(3) + u'.' + m.group(4)

    if not (isinstance, unicode):
        import bookmarks.log as log
        s = u'Invalid type. Expected `<type \'unicode\'>'
        log.error(s)
        raise ValueError(s)

    m = is_collapsed(v)
    if m:
        return m.group(1) + u'[0]' + m.group(3)

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
    n = QtCore.QFileInfo(os.path.expanduser(u'~')).fileName()
    n = re.sub(ur'[^a-zA-Z0-9]*', u'', n, flags=re.IGNORECASE | re.UNICODE)
    return n


def create_temp_dir():
    server, job, root = get_favourite_parent_paths()
    path = u'{}/{}/{}/.bookmark'.format(server, job, root)
    _dir = QtCore.QDir(path)
    if _dir.exists():
        return
    _dir.mkpath(u'.')


def get_favourite_parent_paths():
    server = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.GenericDataLocation)
    job = u'{}'.format(PRODUCT)
    root = u'local'
    return server, job, root


def export_favourites():
    """Saves all favourites including the descriptions and the thumbnails."""
    try:
        import uuid
        import bookmarks.settings as settings
        import bookmarks.bookmark_db as bookmark_db

        res = QtWidgets.QFileDialog.getSaveFileName(
            caption=u'Select where to save your favourites',
            filter=u'*.favourites',
            dir=QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.HomeLocation),
        )
        destination, _ = res
        if not destination:
            return

        favourites = settings.local_settings.favourites()
        server, job, root = get_favourite_parent_paths()
        db = bookmark_db.get_db(server, job, root)
        zip_path = u'{}/{}/{}/{}.zip'.format(server, job, root, uuid.uuid4())

        # Make sure the temp folder exists
        QtCore.QFileInfo(zip_path).dir().mkpath(u'.')

        with zipfile.ZipFile(zip_path, 'a') as z:
            # Adding thumbnail to zip
            for favourite in favourites:
                file_info = QtCore.QFileInfo(db.thumbnail_path(favourite))
                if not file_info.exists():
                    continue
                z.write(file_info.filePath(), file_info.fileName())
            z.writestr(u'favourites', u'\n'.join(favourites))

        file_info = QtCore.QFileInfo(zip_path)
        if not file_info.exists():
            raise RuntimeError(
                u'Unexpected error occured: could not find the favourites file')

        QtCore.QDir().rename(file_info.filePath(), destination)
        if not QtCore.QFileInfo(destination).exists():
            raise RuntimeError(
                u'Unexpected error occured: could not find the favourites file')
        reveal(destination)

    except Exception as e:
        import bookmarks.log as log
        import bookmarks.common_ui as common_ui
        common_ui.ErrorBox(
            u'Could not save the favourites.',
            u'{}'.format(e)
        ).open()
        log.error(u'Exporting favourites failed.')
        raise


def import_favourites(source=None):
    try:
        import bookmarks.settings as settings
        import bookmarks.bookmark_db as bookmark_db

        if not isinstance(source, unicode):
            res = QtWidgets.QFileDialog.getOpenFileName(
                caption=u'Select the favourites file to import',
                filter=u'*.favourites'
                # options=QtWidgets.QFileDialog.ShowDirsOnly
            )
            source, _ = res
            if not source:
                return

        current_favourites = settings.local_settings.favourites()
        create_temp_dir()

        with zipfile.ZipFile(source) as zip:
            namelist = zip.namelist()
            namelist = [f.lower() for f in namelist]

            if u'favourites' not in namelist:
                import bookmarks.log as log
                import bookmarks.common_ui as common_ui
                s = u'The favourites list is missing from the archive.'
                common_ui.ErrorBox(
                    u'Invalid ".favourites" file',
                    s,
                ).open()
                log.error(s)
                raise RuntimeError(s)

            with zip.open(u'favourites') as f:
                favourites = f.readlines()
                favourites = [unicode(f).strip().lower() for f in favourites]

            server, job, root = get_favourite_parent_paths()
            db = bookmark_db.get_db(server, job, root)
            for favourite in favourites:
                file_info = QtCore.QFileInfo(db.thumbnail_path(favourite))
                if file_info.fileName().lower() in namelist:
                    dest = u'{}/{}/{}/.bookmark'.format(server, job, root)
                    zip.extract(file_info.fileName(), dest)

                if favourite not in current_favourites:
                    current_favourites.append(favourite)

            current_favourites = sorted(list(set(current_favourites)))
            settings.local_settings.setValue(u'favourites', current_favourites)

    except Exception as e:
        import bookmarks.log as log
        import bookmarks.common_ui as common_ui
        common_ui.ErrorBox(
            u'Could not import the favourites.',
            u'{}'.format(e)
        ).open()
        log.error(u'Import favourites failed.')
        raise


def clear_favourites():
    import bookmarks.settings as settings
    mbox = QtWidgets.QMessageBox()
    mbox.setWindowTitle(u'Clear favourites')
    mbox.setText(
        u'Are you sure you want to remove all of your favourites?'
    )
    mbox.setStandardButtons(
        QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
    mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)

    mbox.exec_()
    if mbox.result() == QtWidgets.QMessageBox.Cancel:
        return

    settings.local_settings.setValue(u'favourites', [])


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


def qlast_modified(n): return QtCore.QDateTime.fromMSecsSinceEpoch(n * 1000)


def namekey(s):
    """Key function used to sort alphanumeric filenames."""
    if SORT_WITH_BASENAME:
        s = s.split(u'/').pop()  # order by filename
    else:
        n = len(s.split(u'/'))
        s = ((u'Ω' * (n - 1)) + s)  # order by number of subfolders, then name
    return [int(f) if f.isdigit() else f for f in s]


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


def set_custom_stylesheet(widget):
    """Applies the custom stylesheet to the given widget."""
    import bookmarks.images as images

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

    try:
        qss = qss.format(
            PRIMARY_FONT=font_db.primary_font(MEDIUM_FONT_SIZE()).family(),
            SECONDARY_FONT=font_db.secondary_font(SMALL_FONT_SIZE()).family(),
            SMALL_FONT_SIZE=int(SMALL_FONT_SIZE()),
            MEDIUM_FONT_SIZE=int(MEDIUM_FONT_SIZE()),
            LARGE_FONT_SIZE=int(LARGE_FONT_SIZE()),
            RADIUS=int(INDICATOR_WIDTH() * 1.5),
            RADIUS_SM=int(INDICATOR_WIDTH()),
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
                u'branch_open', None, None, get_path=True)
        )
    except KeyError as err:
        import bookmarks.log as log
        msg = u'Looks like there might be an error in the css file: {}'.format(
            err)
        log.error(msg)
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
        zfill = unicode(n).zfill(padding)

        if k not in blocks:
            blocks[k] = []
        blocks[k].append(zfill)

        if idx + 1 != len(arr):
            if arr[idx + 1] != n + 1:  # break coming up
                k += 1
    return u','.join([u'-'.join(sorted(list(set([blocks[k][0], blocks[k][-1]])))) for k in blocks])


def is_valid_filename(text):
    """This method will check if the given text conforms Browser's enforced
    filenaming convention.

    The returned SRE.Match object will contain the groups descripbed below.

    .. code-block:: python

       f = u'000_pr_000_layout_gw_v0006.ma'
       match = get_valid_filename(f)
       match.groups()

    Args:
        group1 (SRE_Match object):        "000" - prefix name.
        group2 (SRE_Match object):        "pr_000" - asset name.
        group3 (SRE_Match object):        "layout" - mode name.
        group4 (SRE_Match object):        "gw" - user name.
        group5 (SRE_Match object):        "0006" - version without the 'v' prefix.
        group6 (SRE_Match object):        "ma" - file extension without the '.'.

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
       match = get_sequence(filename)
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

    When Bookmarks is displaying a sequence of files as a single item,
    the item is *collapsed*. Every collapsed item contains a start and an end number
    enclosed in brackets. For instance: ``image_sequence_[001-233].png``

    Args:
        group 1 (SRE_Match):    All the characters **before** the sequence marker.
        group 2 (SRE_Match):    The sequence marker(eg. ``[01-50]``), as a string.
        group 3 (SRE_Match):    All the characters **after** the sequence marker.

    .. code-block:: python

       filename = 'job_sh010_animation_[001-299]_wgergely.png'
       match = get_sequence(filename)
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

    path = QtGui.QPainterPath()
    path.addText(x, y, font, text)
    painter.drawPath(path)

    painter.restore()
    return width


def copy_path(path, mode=WindowsPath, first=True, copy=True):
    """Copies a path to the clipboard after converting it to `mode`.

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

        import bookmarks.log as log
        log.success(u'Copied {}'.format(path))

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
    try:
        it = _scandir.scandir(path=path)
    except OSError:
        return

    while True:
        try:
            try:
                entry = next(it)
            except StopIteration:
                break
        except OSError:
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


def push_to_rv(path):
    """Uses `rvpush` to view a given footage."""
    import subprocess
    import bookmarks.log as log
    import bookmarks.common_ui as common_ui
    import bookmarks.settings as settings

    def get_preference(k): return settings.local_settings.value(
        u'preferences/{}'.format(k))

    rv_path = get_preference(u'rv_path')
    if not rv_path:
        common_ui.MessageBox(
            u'Shotgun RV not found.',
            u'To push footage to RV, set RV\'s path in Preferences.'
        ).open()
        log.error(u'RV not set')
        return

    rv_info = QtCore.QFileInfo(rv_path)
    if not rv_info.exists():
        common_ui.ErrorBox(
            u'Invalid Shotgun RV path set.',
            u'Make sure the currently set RV path is valid and try again!'
        ).open()
        log.error(u'Invalid RV path set')
        return

    if get_platform() == u'win':
        rv_push_path = u'{}/rvpush.exe'.format(rv_info.path())
        if QtCore.QFileInfo(rv_push_path).exists():
            cmd = u'"{RV}" -tag {PRODUCT} url \'rvlink:// -reuse 1 -inferSequence -l -play -fps 25 -fullscreen -nofloat -lookback 0 -nomb "{PATH}"\''.format(
                RV=rv_push_path,
                PRODUCT=PRODUCT,
                PATH=path
            )
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            subprocess.Popen(cmd, startupinfo=startupinfo)
            log.success(u'Footage sent to RV.')
            log.success(u'Command used:')
            log.success(cmd)
    else:
        common_ui.ErrorBox(
            u'Pushing to RV not yet implemented on this platform.',
            u'Sorry about this. Send me an email if you\'d like to see this work soon!'
        ).open()
        log.error(u'Function not implemented')
        return


class FontDatabase(QtGui.QFontDatabase):

    def __init__(self, parent=None):
        if not QtWidgets.QApplication.instance():
            raise RuntimeError(
                'FontDatabase must be created after a QApplication was initiated.')
        super(FontDatabase, self).__init__(parent=parent)

        self._fonts = {}
        self._metrics = {}
        self.add_custom_fonts()

    def add_custom_fonts(self):
        """Adds our custom fonts to the QApplication.
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
        """Returns the primary font used by the application"""
        k = u'bmRobotoBold' + unicode(font_size)
        if k in self._fonts:
            return self._fonts[k]

        self._fonts[k] = self.font(u'bmRobotoBold', u'Bold', font_size)
        self._fonts[k].setPixelSize(font_size)

        if self._fonts[k].family() != u'bmRobotoBold':
            raise RuntimeError(
                u'Failed to add required font to the application')
        return self._fonts[k]

    def secondary_font(self, font_size=SMALL_FONT_SIZE()):
        k = u'bmRobotoMedium' + unicode(font_size)
        if k in self._fonts:
            return self._fonts[k]

        self._fonts[k] = self.font(u'bmRobotoMedium', u'Medium', font_size)
        self._fonts[k].setPixelSize(font_size)

        if self._fonts[k].family() != u'bmRobotoMedium':
            raise RuntimeError(
                u'Failed to add required font to the application')
        return self._fonts[k]

    def header_font(self, font_size=MEDIUM_FONT_SIZE() * 1.5):
        k = u'bmRobotoBlack' + unicode(float(font_size))
        if k in self._fonts:
            return self._fonts[k]

        self._fonts[k] = self.font(u'bmRobotoBlack', u'Black', font_size)
        if self._fonts[k].family() != u'bmRobotoBlack':
            raise RuntimeError(
                u'Failed to add required font to the application')
        return self._fonts[k]


class DataDict(dict):
    """Subclassed dict type for weakref compatibility."""
    pass
