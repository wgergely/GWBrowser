# -*- coding: utf-8 -*-
"""A list of common actions.

"""
import re
import os
import subprocess
import functools

from PySide2 import QtCore, QtWidgets, QtGui

from . import settings
from . import bookmark_db
from . import common
from . import images


class Signals(QtCore.QObject):
    thumbnailUpdated = QtCore.Signal(unicode)

    # Signals used to update values in BaseModels
    bookmarkModelValueUpdated = QtCore.Signal(unicode, int, object)
    assetModelValueUpdated = QtCore.Signal(unicode, int, object)
    fileModelValueUpdated = QtCore.Signal(unicode, int, object)
    favouriteModelValueUpdated = QtCore.Signal(unicode, int, object)

    # Signal to indicate changed bookmark database values
    bookmarkValueUpdated = QtCore.Signal(unicode, unicode, object)
    assetValueUpdated = QtCore.Signal(unicode, unicode, object)
    fileValueUpdated = QtCore.Signal(unicode, unicode, object)

    # Used to indicate an item has been added or removed
    bookmarksChanged = QtCore.Signal()
    assetAdded = QtCore.Signal(unicode)
    fileAdded = QtCore.Signal(unicode)
    favouriteAdded = QtCore.Signal(unicode)

    bookmarkUpdated = QtCore.Signal(unicode)
    assetUpdated = QtCore.Signal(unicode)
    fileUpdated = QtCore.Signal(unicode)
    favouriteUpdated = QtCore.Signal(unicode)

    toggleFilterButton = QtCore.Signal()
    toggleSequenceButton = QtCore.Signal()
    toggleArchivedButton = QtCore.Signal()
    toggleSimpleButton = QtCore.Signal()
    toggleFavouritesButton = QtCore.Signal()
    toggleMakeThumbnailsButton = QtCore.Signal()

    def __init__(self, parent=None):
        super(Signals, self).__init__(parent=parent)
        self.toggleFilterButton.connect(toggle_filter_editor)
        self.toggleSequenceButton.connect(toggle_sequence)
        self.toggleArchivedButton.connect(toggle_archived_items)
        self.toggleSimpleButton.connect(toggle_simple)
        self.toggleFavouritesButton.connect(toggle_favourite_items)
        self.toggleMakeThumbnailsButton.connect(toggle_make_thumbnails)


@common.error
@common.debug
def toggle_filter_editor():
    w = instance().widget()
    if w.filter_editor.isHidden():
        w.filter_editor.open()
    else:
        w.filter_editor.done(QtWidgets.QDialog.Rejected)


@common.error
@common.debug
def toggle_sequence():
    from .lists import base
    idx = instance().stackedwidget.currentIndex()
    if idx not in (base.FileTab, base.FavouriteTab):
        return

    model = instance().widget().model().sourceModel()
    datatype = model.data_type()
    if datatype == common.FileItem:
        model.dataTypeChanged.emit(common.SequenceItem)
    else:
        model.dataTypeChanged.emit(common.FileItem)


@common.error
@common.debug
def toggle_archived_items():
    w = instance().widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsArchived)
    proxy.set_filter_flag(common.MarkedAsArchived, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsArchived, not val)

@common.error
@common.debug
def toggle_active_item():
    w = instance().widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsActive)
    proxy.set_filter_flag(common.MarkedAsActive, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsActive, not val)


@common.error
@common.debug
def toggle_favourite_items():
    w = instance().widget()
    proxy = w.model()
    val = proxy.filter_flag(common.MarkedAsFavourite)
    proxy.set_filter_flag(common.MarkedAsFavourite, not val)
    proxy.filterFlagChanged.emit(common.MarkedAsFavourite, not val)


@common.error
@common.debug
def toggle_simple():
    widget = instance().widget()
    state = not widget.buttons_hidden()

    common.SORT_WITH_BASENAME = state
    widget.set_buttons_hidden(state)

    widget.model().sourceModel().sort_data()
    widget.reset()

    widget.model().sourceModel().set_local_setting(
        settings.SortByBaseNameKey,
        state,
        key=widget.__class__.__name__,
        section=settings.UIStateSection
    )


@common.error
@common.debug
def toggle_make_thumbnails():
    widget = instance().widget()
    model = widget.model().sourceModel()
    state = not model.generate_thumbnails_enabled()
    model.set_generate_thumbnails_enabled(state)

    widget.queue_visible_indexes(
        common.ThumbnailLoaded,
        common.ThumbnailThread
    )


signals = Signals()


def selection(func):
    """Decorator function to ensure `QModelIndexes` passed to worker threads
    are in a valid state.

    """
    @functools.wraps(func)
    def func_wrapper():
        index = instance().index()
        if not index.isValid():
            return None
        return func(index)
    return func_wrapper


def instance():
    from . import main
    return main.instance()


@common.error
@common.debug
def increase_row_size():
    widget = instance().widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.row_size().height() + common.psize(20)
    if v >= images.THUMBNAIL_IMAGE_SIZE:
        return

    widget.set_row_size(v)
    widget.reset_row_layout()


@common.error
@common.debug
def decrease_row_size():
    widget = instance().widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.row_size().height() - common.psize(20)
    if v <= model.default_row_size().height():
        v = model.default_row_size().height()

    widget.set_row_size(v)
    widget.reset_row_layout()


@common.error
@common.debug
def reset_row_size():
    widget = instance().widget()
    proxy = widget.model()
    model = proxy.sourceModel()

    v = model.default_row_size().height()

    widget.set_row_size(v)
    widget.reset_row_layout()


@common.error
@common.debug
def add_bookmark():
    from .bookmark_editor import bookmark_editor_widget as editor
    widget = editor.show()
    widget.bookmarksChanged.connect(signals.bookmarksChanged)
    return widget


@common.error
@common.debug
def add_asset(server=None, job=None, root=None):
    if not all((server, job, root)):
        server = settings.active(settings.ServerKey)
        job = settings.active(settings.JobKey)
        root = settings.active(settings.RootKey)

    if not all((server, job, root)):
        return None

    from .properties import asset_properties_widget as editor
    widget = editor.show(server, job, root)
    return widget


@common.error
@common.debug
def add_file(asset=None, extension=None):
    server = settings.active(settings.ServerKey)
    job = settings.active(settings.JobKey)
    root = settings.active(settings.RootKey)

    if asset is None:
        asset = settings.active(settings.AssetKey)

    args = (server, job, root, asset)
    if not all(args):
        return None

    from .properties import file_properties_widget as editor
    widget = editor.show(
        server,
        job,
        root,
        asset,
        extension=extension
    )
    widget.itemCreated.connect(signals.fileAdded)
    return widget


@common.error
@common.debug
def add_favourite():
    raise NotImplementedError('Function not yet implemented')


@common.error
@common.debug
def edit_bookmark(server=None, job=None, root=None):
    if not all((server, job, root)):
        server = settings.active(settings.ServerKey)
        job = settings.active(settings.JobKey)
        root = settings.active(settings.RootKey)

    if not all((server, job, root)):
        return None

    from .properties import bookmark_properties_widget as editor
    widget = editor.show(server, job, root)

    widget.open()
    return widget


@common.error
@common.debug
def edit_asset(asset=None):
    server = settings.active(settings.ServerKey)
    job = settings.active(settings.JobKey)
    root = settings.active(settings.RootKey)

    if not all((server, job, root)):
        return None
    if asset is None:
        asset = settings.active(settings.AssetKey)
    if asset is None:
        return

    from .properties import asset_properties_widget as editor

    widget = editor.show(
        server,
        job,
        root,
        asset=asset
    )
    widget.valueUpdated.connect(signals.assetValueUpdated)
    widget.thumbnailUpdated.connect(signals.thumbnailUpdated)
    widget.itemUpdated.connect(signals.assetUpdated)

    return widget


@common.error
@common.debug
def edit_file(f):
    server = settings.active(settings.ServerKey)
    job = settings.active(settings.JobKey)
    root = settings.active(settings.RootKey)
    asset = settings.active(settings.AssetKey)

    if not all((server, job, root, asset)):
        return

    from .properties import file_properties_widget as editor
    widget = editor.show(
        server,
        job,
        root,
        asset,
        extension=QtCore.QFileInfo(f).suffix(),
        file=f
    )
    widget.valueUpdated.connect(signals.fileValueUpdated)
    widget.thumbnailUpdated.connect(signals.thumbnailUpdated)
    widget.itemUpdated.connect(signals.fileUpdated)
    return widget


@common.error
@common.debug
def edit_favourite(f):
    raise NotImplementedError(u'Function not yet implemented.')


@common.error
@common.debug
def show_preferences():
    from .properties import preference_properties_widget as editor
    widget = editor.show()
    return widget


@common.error
@common.debug
def show_slack():
    """Opens the Slack widget used to send messages using SlackAPI.

    """
    server = settings.active(settings.ServerKey)
    job = settings.active(settings.JobKey)
    root = settings.active(settings.RootKey)

    args = (server, job, root)
    if not all(args):
        return

    with bookmark_db.transactions(*args) as db:
        token = db.value(
            db.source(),
            u'slacktoken',
            table=bookmark_db.BookmarkTable
        )
    if token is None:
        raise RuntimeError(u'Slack is not yet configured.')

    from . import slack
    widget = slack.show(token)
    return widget


@common.error
@common.debug
def quit():
    from . import threads
    instance().statusbar.showMessage(u'Closing down...')
    instance().destroy_ui()

    threads.quit()
    bookmark_db.close()
    instance().terminated.emit()

    if common.STANDALONE:
        QtWidgets.QApplication.instance().quit()


@common.error
@common.debug
def add_item():
    from .lists import base
    idx = instance().stackedwidget.currentIndex()
    if idx == base.BookmarkTab:
        add_bookmark()
    elif idx == base.AssetTab:
        add_asset()
    elif idx == base.FileTab:
        add_file()
    elif idx == base.FavouriteTab:
        add_favourite()


@common.error
@common.debug
@selection
def edit_item(index):
    from .lists import base

    idx = instance().stackedwidget.currentIndex()
    if idx == base.BookmarkTab:
        server, job, root = index.data(common.ParentPathRole)[0:3]
        edit_bookmark(
            server=server,
            job=job,
            root=root,
        )
    elif idx == base.AssetTab:
        asset = index.data(common.ParentPathRole)[-1]
        edit_asset(asset=asset)
    elif idx == base.FileTab:
        _file = index.data(QtCore.Qt.StatusTipRole)
        edit_file(_file)
    elif idx == base.FavouriteTab:
        file = index.data(QtCore.Qt.StatusTipRole)
        edit_favourite(file)


@common.error
@common.debug
def refresh():
    w = instance().widget()
    model = w.model().sourceModel()
    model.modelDataResetRequested.emit()


@common.error
@common.debug
def toggle_flag(flag, v):
    proxy = instance().widget().model()
    proxy.set_filter_flag(flag, v)
    proxy.filterFlagChanged.emit(flag, v)


@common.error
@common.debug
def toggle_fullscreen():
    if instance().isFullScreen():
        instance().showNormal()
    else:
        instance().showFullScreen()


@common.error
@common.debug
def toggle_maximized():
    if instance().isMaximized():
        instance().showNormal()
    else:
        instance().showMaximized()


@common.error
@common.debug
def toggle_minimized():
    if instance().isMinimized():
        instance().showNormal()
    else:
        instance().showMinimized()


@common.error
@common.debug
def toggle_stays_on_top():
    if not common.STANDALONE:
        return

    from . import standalone

    w = standalone.instance()
    flags = w.windowFlags()
    state = flags & QtCore.Qt.WindowStaysOnTopHint

    settings.local_settings.setValue(
        settings.UIStateSection,
        settings.WindowAlwaysOnTopKey,
        not state
    )
    w.hide()
    w.init_window_flags()
    w.activateWindow()
    w.showNormal()


@common.error
@common.debug
def toggle_frameless():
    if not common.STANDALONE:
        return

    from . import standalone

    w = standalone.instance()
    flags = w.windowFlags()
    state = flags & QtCore.Qt.FramelessWindowHint

    settings.local_settings.setValue(
        settings.UIStateSection,
        settings.WindowFramelessKey,
        not state
    )

    w.hide()
    w.init_window_flags()
    w.update_layout()
    w.activateWindow()
    w.showNormal()


@common.error
@common.debug
def exec_instance():
    if common.get_platform() == common.PlatformWindows:
        if common.BOOKMARK_ROOT_KEY not in os.environ:
            s = u'Bookmarks does not seem to be installed correctly:\n'
            s += u'"{}" environment variable is not set'.format(
                common.BOOKMARK_ROOT_KEY)
            raise RuntimeError(s)
        p = os.environ[common.BOOKMARK_ROOT_KEY] + \
            os.path.sep + 'bookmarks.exe'
        subprocess.Popen(p)
    elif common.get_platform() == common.PlatformMacOS:
        raise NotImplementedError(u'Not yet implemented.')
    elif common.get_platform() == common.PlatformUnsupported:
        raise NotImplementedError(u'Not yet implemented.')


@common.error
@common.debug
def change_tab(idx):
    instance().topbar.listChanged.emit(idx)


@common.error
@common.debug
def next_tab():
    from .lists import base
    n = instance().stackedwidget.currentIndex()
    n += 1
    if n > (instance().stackedwidget.count() - 1):
        instance().topbar.listChanged.emit(base)
        return
    instance().topbar.listChanged.emit(n)


@common.error
@common.debug
def previous_tab():
    n = instance().stackedwidget.currentIndex()
    n -= 1
    if n < 0:
        n = instance().stackedwidget.count() - 1
        instance().topbar.listChanged.emit(n)
        return
    instance().topbar.listChanged.emit(n)


@common.error
@common.debug
def change_sorting(role, order):
    model = instance().widget().model().sourceModel()
    model.sortingChanged.emit(role, order)


@common.error
@common.debug
def toggle_sort_order():
    model = instance().widget().model().sourceModel()
    order = model.sort_order()
    role = model.sort_role()
    model.sortingChanged.emit(role, not order)


@common.error
@common.debug
@selection
def copy_selected_path(index):
    if not index.data(common.FileInfoLoaded):
        return
    if common.get_platform() == common.PlatformMacOS:
        mode = common.MacOSPath
    elif common.get_platform() == common.PlatformWindows:
        mode = common.WindowsPath
    else:
        mode = common.UnixPath
    copy_path(
        index.data(QtCore.Qt.StatusTipRole),
        mode=mode,
        first=False
    )


@common.error
@common.debug
@selection
def copy_selected_alt_path(index):
    if not index.data(common.FileInfoLoaded):
        return
    copy_path(
        index.data(QtCore.Qt.StatusTipRole),
        mode=common.UnixPath,
        first=True
    )


@common.debug
@common.error
@selection
def show_todos(index):
    from . import notes
    parent = instance().widget()
    editors = [f for f in parent.children() if isinstance(
        f, notes.TodoEditorWidget)]
    if editors:
        for editor in editors:
            editor.done(QtWidgets.QDialog.Rejected)

    source_index = parent.model().mapToSource(index)

    editor = notes.TodoEditorWidget(source_index, parent=parent)
    parent.resized.connect(editor.setGeometry)
    editor.finished.connect(editor.deleteLater)
    editor.open()


@common.debug
@common.error
@selection
def preview(index):
    """Displays a preview of the currently selected item.

    For alembic archives, this is the hierarchy of the archive file. For
    image files we'll try to load and display the image itself, and
    for any other case we will fall back to cached or default thumbnail
    images.

    """
    source = index.data(QtCore.Qt.StatusTipRole)
    source = common.get_sequence_startpath(source)
    ext = source.split(u'.').pop()

    if ext.lower() == u'abc':
        from .editors import alembic_preview
        editor = alembic_preview.AlembicPreviewWidget(source)
        instance().widget().selectionModel().currentChanged.connect(editor.close)
        instance().widget().selectionModel().currentChanged.connect(editor.deleteLater)
        editor.show()
        return

    # Let's try to open the image outright
    # If this fails, we will try and look for a saved thumbnail image,
    # and if that fails too, we will display a general thumbnail.

    # Not a readable image file...
    if images.oiio_get_buf(source):
        thumb_path = source
    else:
        server, job, root = index.data(common.ParentPathRole)[0:3]
        thumb_path = images.get_thumbnail(
            server,
            job,
            root,
            index.data(QtCore.Qt.StatusTipRole),
            get_path=True
        )
        if not thumb_path:
            return

    # Finally, we'll create and show our widget, and destroy it when the
    # selection changes
    from .editors import item_preview
    editor = item_preview.ImageViewer(thumb_path, parent=instance().widget())
    instance().widget().selectionModel().currentChanged.connect(editor.delete_timer.start)
    editor.open()


@common.debug
@common.error
@selection
def reveal_selected(index):
    reveal(index)


@common.debug
@common.error
@selection
def reveal_url(index):
    parent_path = index.data(common.ParentPathRole)
    if len(parent_path) == 3:
        table = bookmark_db.BookmarkTable
    else:
        table = bookmark_db.AssetTable

    source = u'/'.join(index.data(common.ParentPathRole))
    with bookmark_db.transactions(*index.data(common.ParentPathRole)[0:3]) as db:
        v = db.value(source, 'url1', table=table)

    if not v:
        return

    QtGui.QDesktopServices.openUrl(QtCore.QUrl(v)),


@common.debug
@common.error
@selection
def toggle_favourite(index):
    instance().widget().save_selection()
    instance().widget().toggle_item_flag(index, common.MarkedAsFavourite)
    instance().widget().update(index)
    instance().widget().model().invalidateFilter()


@common.debug
@common.error
@selection
def toggle_archived(index):
    instance().widget().save_selection()
    instance().widget().toggle_item_flag(index, common.MarkedAsArchived)
    instance().widget().update(index)
    instance().widget().model().invalidateFilter()


@common.debug
@common.error
def reveal(item):
    """Reveals an item in the file explorer.

    Args:
        item(unicode or QModelIndex): The item to show in the file manager.

    """
    if isinstance(item, (QtCore.QModelIndex, QtWidgets.QListWidgetItem)):
        path = item.data(QtCore.Qt.StatusTipRole)
    elif isinstance(item, unicode):
        path = item

    path = common.get_sequence_endpath(path)
    if common.get_platform() == common.PlatformWindows:
        if QtCore.QFileInfo(path).isFile():
            args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        elif QtCore.QFileInfo(path).isDir():
            path = os.path.normpath(os.path.abspath(path))
            args = [path, ]
        else:
            args = [u'/select,', QtCore.QDir.toNativeSeparators(path)]
        QtCore.QProcess.startDetached(u'explorer', args)

    elif common.get_platform() == common.PlatformMacOS:
        args = [
            u'-e',
            u'tell application "Finder"',
            u'-e',
            u'activate',
            u'-e',
            u'select POSIX file "{}"'.format(
                QtCore.QDir.toNativeSeparators(path)), u'-e', u'end tell']
        QtCore.QProcess.startDetached(u'osascript', args)
    elif common.get_platform() == common.PlatformUnsupported:
        raise NotImplementedError('{} is unsupported.'.format(
            QtCore.QSysInfo().productType()))


@common.debug
@common.error
def copy_path(path, mode=common.WindowsPath, first=True, copy=True):
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
        path = common.get_sequence_startpath(path)
    else:
        path = common.get_sequence_endpath(path)

    # Normalise path
    path = re.sub(ur'[\/\\]', ur'/', path,
                  flags=re.IGNORECASE | re.UNICODE).strip(u'/')

    if mode == common.WindowsPath:
        prefix = u'//' if u':' not in path else u''
    elif mode == common.UnixPath:
        prefix = u'//' if u':' not in path else u''
    elif mode == common.SlackPath:
        prefix = u'file://'
    elif mode == common.MacOSPath:
        prefix = u'smb://'
        path = path.replace(u':', u'')
    else:
        prefix = u''
    path = prefix + path
    if mode == common.WindowsPath:
        path = re.sub(ur'[\/\\]', ur'\\', path,
                      flags=re.IGNORECASE | re.UNICODE)

    if copy:
        QtGui.QClipboard().setText(path)
    return path


@common.debug
@common.error
def execute(index, first=False):
    """Given the model index, executes the index's path using
    `QDesktopServices`.

    """
    if not index.isValid():
        return
    path = index.data(QtCore.Qt.StatusTipRole)
    if first:
        path = common.get_sequence_startpath(path)
    else:
        path = common.get_sequence_endpath(path)

    url = QtCore.QUrl.fromLocalFile(path)
    QtGui.QDesktopServices.openUrl(url)


@common.debug
@common.error
def test_slack_token(token):
    from . import slack
    client = slack.SlackClient(token)
    client.verify_token(silent=False)


@common.debug
@common.error
def suggest_prefix(job):
    substrings = re.sub(ur'[\_\-\s]+', u';', job).split(u';')
    if (not substrings or len(substrings) < 2) and len(job) > 3:
        prefix = job[0:3].upper()
    else:
        prefix = u''.join([f[0] for f in substrings]).upper()
    return prefix


@common.debug
@common.error
@selection
def capture_thumbnail(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

    from .editors import thumb_capture as editor
    widget = editor.show(
        server=server,
        job=job,
        root=root,
        source=source,
        proxy=False
    )

    widget.captureFinished.connect(widget.save_image)
    model = index.model().sourceModel()
    widget.accepted.connect(
        functools.partial(model.updateIndex.emit, index)
    )


@common.debug
@common.error
@selection
def pick_thumbnail_from_file(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

    from .editors import thumb_picker as editor
    widget = editor.show(
        server=server,
        job=job,
        root=root,
        source=source
    )

    widget.fileSelected.connect(widget.save_image)
    model = index.model().sourceModel()
    widget.fileSelected.connect(lambda x: model.updateIndex.emit(index))


@common.debug
@common.error
@selection
def pick_thumbnail_from_library(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

    from .editors import thumb_library as editor
    widget = editor.show(
        server=server,
        job=job,
        root=root,
        source=source
    )
    widget.thumbnailSelected.connect(widget.save_image)
    model = index.model().sourceModel()
    widget.thumbnailSelected.connect(lambda x: model.updateIndex.emit(index))


@common.debug
@common.error
@selection
def remove_thumbnail(index):
    """Deletes a thumbnail file and the cached entries associated
    with it.

    """
    server, job, root = index.data(common.ParentPathRole)[0:3]
    source = index.data(QtCore.Qt.StatusTipRole)

    thumbnail_path = images.get_cached_thumbnail_path(
        server, job, root, source
    )
    images.ImageCache.flush(thumbnail_path)

    if QtCore.QFile(thumbnail_path).exists():
        if not QtCore.QFile(thumbnail_path).remove():
            raise RuntimeError(u'Could not remove the thumbnail')

    source_index = index.model().mapToSource(index)
    idx = source_index.row()

    data = source_index.model().model_data()[idx]
    data[common.ThumbnailLoaded] = False
    source_index.model().updateIndex.emit(source_index)


@common.error
@common.debug
def copy_properties():
    from .lists import base
    idx = instance().stackedwidget.currentIndex()
    if idx == base.BookmarkTab:
        copy_bookmark_properties()
    elif idx == base.AssetTab:
        copy_asset_properties()
    else:
        return

@common.error
@common.debug
def paste_properties():
    from .lists import base
    idx = instance().stackedwidget.currentIndex()
    if idx == base.BookmarkTab:
        paste_bookmark_properties()
    elif idx == base.AssetTab:
        paste_asset_properties()
    else:
        return


@common.error
@common.debug
@selection
def copy_bookmark_properties(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    bookmark_db.copy_properties(
        server,
        job,
        root,
        None,
        table=bookmark_db.BookmarkTable
    )


@common.error
@common.debug
@selection
def paste_bookmark_properties(index):
    server, job, root = index.data(common.ParentPathRole)[0:3]
    bookmark_db.paste_properties(
        server,
        job,
        root,
        None,
        table=bookmark_db.BookmarkTable
    )

@common.error
@common.debug
@selection
def copy_asset_properties(index):
    server, job, root, asset = index.data(common.ParentPathRole)[0:4]
    bookmark_db.copy_properties(
        server,
        job,
        root,
        asset,
        table=bookmark_db.AssetTable
    )


@common.error
@common.debug
@selection
def paste_asset_properties(index):
    server, job, root, asset = index.data(common.ParentPathRole)[0:4]
    bookmark_db.paste_properties(
        server,
        job,
        root,
        asset,
        table=bookmark_db.AssetTable
    )
