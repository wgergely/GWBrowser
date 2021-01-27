# -*- coding: utf-8 -*-
"""Classes responsible for viewing and editing items marked as favourites.

"""
import uuid
import _scandir
import zipfile

from PySide2 import QtWidgets, QtCore, QtGui


from .. import log
from .. import common
from .. import common_ui
from .. import bookmark_db
from .. import images
from .. import threads
from .. import settings
from .. import contextmenu
from .. import actions

from . import delegate
from . import files


FavouriteFileFormat = u'favourites'


def create_temp_dir():
    server, job, root = _parent_path()
    path = u'{}/{}/{}/.bookmark'.format(server, job, root)
    _dir = QtCore.QDir(path)
    if _dir.exists():
        return
    _dir.mkpath(u'.')


def _parent_path():
    """A parent path used to save favourites.

    """
    return (
        QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        common.PRODUCT,
        u'local'
    )


class FavouritesWidgetContextMenu(contextmenu.BaseContextMenu):
    def setup(self):
        self.control_favourites_menu()
        if self.index.isValid():
            self.remove_favourite_menu()
            self.separator()
            self.reveal_item_menu()
            self.copy_menu()
        self.separator()
        self.sort_menu()
        self.collapse_sequence_menu()
        self.separator()
        self.refresh_menu()


class FavouritesModel(files.FilesModel):
    """The model responsible for displaying the saved favourites."""

    queue_type = threads.FavouriteInfoQueue
    thumbnail_queue_type = threads.FavouriteThumbnailQueue

    def __init__(self, parent=None):
        super(FavouritesModel, self).__init__(parent=parent)
        create_temp_dir()

    def local_settings_key(self):
        return u'/'.join(_parent_path())

    def parent_path(self):
        return _parent_path() + (u'.',)

    def _entry_iterator(self, path):
        """We're using the saved keys to find and return the DirEntries
        corresponding to the saved favourites.

        """
        favourites = settings.local_settings.get_favourites()

        d = []

        for k in favourites:
            file_info = QtCore.QFileInfo(k)
            _path = file_info.path()

            if not QtCore.QFileInfo(_path).exists():
                continue

            for entry in _scandir.scandir(_path):
                path = entry.path.replace(u'\\', u'/')
                if path == k:
                    d.append(entry)
                    continue
                _k = common.proxy_path(path)
                if k == _k:
                    d.append(entry)

        for entry in d:
            yield entry

    def task(self):
        return u'.'


class DropIndicatorWidget(QtWidgets.QWidget):
    """Widgets responsible for drawing an overlay."""

    def __init__(self, parent=None):
        super(DropIndicatorWidget, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        """Paints the indicator area."""
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.FAVOURITE)
        pen.setWidth(common.INDICATOR_WIDTH())
        painter.setPen(pen)
        painter.setBrush(common.FAVOURITE)
        painter.setOpacity(0.35)
        painter.drawRect(self.rect())
        painter.setOpacity(1.0)
        common.draw_aliased_text(
            painter,
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0],
            self.rect(),
            u'Drop to add bookmark',
            QtCore.Qt.AlignCenter,
            common.FAVOURITE
        )
        painter.end()

    def show(self):
        """Shows and sets the size of the widget."""
        self.setGeometry(self.parent().geometry())
        super(DropIndicatorWidget, self).show()


class FavouritesWidget(files.FilesWidget):
    """The widget responsible for showing all the items marked as favourites."""
    SourceModel = FavouritesModel
    Delegate = delegate.FavouritesWidgetDelegate
    ContextMenu = FavouritesWidgetContextMenu

    def __init__(self, parent=None):
        super(FavouritesWidget, self).__init__(parent=parent)
        self.indicatorwidget = DropIndicatorWidget(parent=self)
        self.indicatorwidget.hide()

        self.setWindowTitle(u'Favourites')

        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        self.reset_timer = QtCore.QTimer(parent=self)
        self.reset_timer.setInterval(10)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(
            self.model().sourceModel().modelDataResetRequested)

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return True

    def inline_icons_count(self):
        return 3

    def toggle_item_flag(self, index, flag, state=None):
        super(FavouritesWidget, self).toggle_item_flag(
            index, common.MarkedAsFavourite, state=False)
        self.reset_timer.start()

    def dragEnterEvent(self, event):
        if event.source() == self:
            return

        if event.mimeData().hasUrls():
            self.indicatorwidget.show()
            return event.accept()
        self.indicatorwidget.hide()

    def dragLeaveEvent(self, event):
        self.indicatorwidget.hide()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        """Event responsible for adding the dropped file to the favourites."""
        self.indicatorwidget.hide()

        if event.source() == self:
            return  # Won't allow dropping an item from itself

        mime = event.mimeData()
        if not mime.hasUrls():
            return

        event.accept()

        items = []
        for url in mime.urls():
            file_info = QtCore.QFileInfo(url.toLocalFile())
            path = file_info.filePath()

            # This is a saved favourite template file
            if file_info.suffix() == FavouriteFileFormat:
                self.import_favourites(source=path)
                continue

            # Here we should check if the dropped item is sequence.
            seq = common.get_sequence(path)
            if not seq:
                k = path
            else:
                frames = 0
                for entry in _scandir.scandir(file_info.dir().path()):
                    p = entry.path.replace(u'\\', u'/')
                    if seq.group(1) in p and seq.group(3) in p:
                        frames += 1
                    if frames >= 2:
                        break
                if frames > 1:
                    k = common.proxy_path(path)
                else:
                    k = path
            items.append(k)

        settings.local_settings.add_favourites(items)

    def get_hint_string(self):
        model = self.model().sourceModel()
        if not model.rowCount():
            return u'You didn\'t add any files yet.'

    @staticmethod
    def export_favourites():
        """Saves the cuurent list favourites.

        The saved data will be packaged into a zip archive to include the item's
        description and thumbnail.

        """
        try:
            res = QtWidgets.QFileDialog.getSaveFileName(
                caption=u'Select where to save your favourites',
                filter=u'*.favourites',
                dir=QtCore.QStandardPaths.writableLocation(
                    QtCore.QStandardPaths.HomeLocation),
            )
            destination, _ = res
            if not destination:
                return

            favourites = settings.local_settings.get_favourites()
            server, job, root = _parent_path()
            db = bookmark_db.get_db(server, job, root)
            zip_path = u'{}/{}/{}/{}.zip'.format(server, job, root, uuid.uuid4())

            # Make sure the temp folder exists
            QtCore.QFileInfo(zip_path).dir().mkpath(u'.')

            with zipfile.ZipFile(zip_path, 'a') as z:
                # Adding thumbnail to zip
                for favourite in favourites:
                    thumbnail_path = images.get_thumbnail_path(
                        server,
                        job,
                        root,
                        favourite
                    )
                    file_info = QtCore.QFileInfo(thumbnail_path)
                    if not file_info.exists():
                        continue
                    z.write(file_info.filePath(), file_info.fileName())
                z.writestr(FavouriteFileFormat, u'\n'.join(favourites))

            file_info = QtCore.QFileInfo(zip_path)
            if not file_info.exists():
                raise RuntimeError(
                    u'Unexpected error occured: could not find the favourites file')

            QtCore.QDir().rename(file_info.filePath(), destination)
            if not QtCore.QFileInfo(destination).exists():
                raise RuntimeError(
                    u'Unexpected error occured: could not find the favourites file')
            actions.reveal(destination)

        except Exception as e:
            common_ui.ErrorBox(
                u'Could not save the favourites.',
                u'{}'.format(e)
            ).open()
            log.error(u'Exporting favourites failed.')
            raise

    @staticmethod
    def import_favourites(source=None):
        """Import a previously exported favourites file.

        Args:
            source (unicode): Path to a file. Defaults to `None`.

        """
        try:
            if not isinstance(source, unicode):
                res = QtWidgets.QFileDialog.getOpenFileName(
                    caption=u'Select the favourites file to import',
                    filter=u'*.favourites'
                    # options=QtWidgets.QFileDialog.ShowDirsOnly
                )
                source, _ = res
                if not source:
                    return

            create_temp_dir()

            with zipfile.ZipFile(source) as zip:
                namelist = zip.namelist()

                if FavouriteFileFormat not in namelist:
                    s = u'The favourites list is missing from the archive.'
                    common_ui.ErrorBox(
                        u'Invalid ".favourites" file',
                        s,
                    ).open()
                    log.error(s)
                    raise RuntimeError(s)

                with zip.open(FavouriteFileFormat) as f:
                    favourites = f.readlines()
                    favourites = [unicode(f).strip() for f in favourites]

                server, job, root = _parent_path()

                for favourite in favourites:
                    thumbnail_path = images.get_thumbnail_path(
                        server,
                        job,
                        root,
                        favourite
                    )
                    file_info = QtCore.QFileInfo(thumbnail_path)
                    if file_info.fileName() in namelist:
                        dest = u'{}/{}/{}/.bookmark'.format(server, job, root)
                        zip.extract(file_info.fileName(), dest)

                settings.local_settings.add_favourites(favourites)

        except Exception as e:
            common_ui.ErrorBox(
                u'Could not import the favourites.',
                u'{}'.format(e)
            ).open()
            log.error(u'Import favourites failed.')
            raise

    @staticmethod
    def clear_favourites():
        """Clear the list of saved items.

        """
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

        settings.local_settings.clear_favourites()
