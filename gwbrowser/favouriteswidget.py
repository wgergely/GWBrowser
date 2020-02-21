# -*- coding: utf-8 -*-
"""Classes responsible for interacting with items marked as favourites by the
user.

"""

import os
from PySide2 import QtWidgets, QtCore, QtGui

from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
import gwbrowser.settings as settings_

import gwbrowser.delegate as delegate
from gwbrowser.gwscandir import scandir as scandir_it
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.baselistwidget import initdata
from gwbrowser.delegate import FilesWidgetDelegate
from gwbrowser.fileswidget import FilesModel
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.baselistwidget import validate_index

from gwbrowser.threads import BaseThread
from gwbrowser.threads import Unique

from gwbrowser.fileswidget import validate_index
from gwbrowser.fileswidget import FileInfoWorker
from gwbrowser.fileswidget import SecondaryFileInfoWorker
from gwbrowser.fileswidget import FileThumbnailWorker


def rsc_path(f, n):
    path = u'{}/../rsc/{}.png'.format(f, n)
    path = os.path.normpath(os.path.abspath(path))
    return path


class FavouriteInfoWorker(FileInfoWorker):
    """We will check if the favou."""
    queue = Unique(999999)
    indexes_in_progress = []

    @staticmethod
    @validate_index
    @QtCore.Slot(QtCore.QModelIndex)
    def process_index(index, exists=True):
        FileInfoWorker.process_index(index, exists=exists)


class SecondaryFavouriteInfoWorker(SecondaryFileInfoWorker):
    """Worker associated with the ``FavouritesModel``."""
    queue = Unique(999999)
    indexes_in_progress = []


class FavouriteThumbnailWorker(FileThumbnailWorker):
    """Worker associated with the ``FavouritesModel``."""
    queue = Unique(999999)
    indexes_in_progress = []


class FavouriteInfoThread(BaseThread):
    """Thread controller associated with the ``FavouritesModel``."""
    Worker = FavouriteInfoWorker


class SecondaryFavouriteInfoThread(BaseThread):
    """Thread controller associated with the ``FavouritesModel``."""
    Worker = SecondaryFavouriteInfoWorker


class FavouriteThumbnailThread(BaseThread):
    """Thread controller associated with the ``FavouritesModel``."""
    Worker = FavouriteThumbnailWorker


class FavouritesWidgetContextMenu(BaseContextMenu):
    def __init__(self, index, parent=None):
        super(FavouritesWidgetContextMenu, self).__init__(index, parent=parent)
        self.index = index

        self.add_control_favourites_menu()
        self.add_separator()

        if index.isValid():
            self.add_remove_favourite_menu()
            self.add_separator()
            #
            self.add_separator()
            #
            self.add_reveal_item_menu()
            self.add_copy_menu()
        #
        self.add_separator()
        #
        self.add_sort_menu()
        self.add_collapse_sequence_menu()
        #
        self.add_separator()
        #
        self.add_refresh_menu()


class FavouritesModel(FilesModel):
    """The model responsible for displaying the saved favourites."""
    InfoThread = FavouriteInfoThread
    SecondaryInfoThread = SecondaryFavouriteInfoThread
    ThumbnailThread = FavouriteThumbnailThread

    def __init__(self, parent=None):
        super(FavouritesModel, self).__init__(parent=parent)
        common.create_temp_dir()
        self.parent_path = common.get_favourite_parent_paths() + (u'.',)

    def data_key(self):
        return u'.'

    def _entry_iterator(self, path):
        """We're using the saved keys to find and return the DirEntries
        corresponding to the saved favourites.

        """
        favourites = settings_.local_settings.favourites()
        sfavourites = set(favourites)

        d = []

        for k in favourites:
            file_info = QtCore.QFileInfo(k)
            for entry in scandir_it(file_info.path()):
                path = entry.path.replace(u'\\', u'/').lower()
                if path == k:
                    d.append(entry)
                    continue
                seq = common.get_sequence(path)
                if seq:
                    _k = seq.group(1) + u'[0]' + seq.group(3) + u'.' + seq.group(4)
                else:
                    _k = path
                _k = _k.lower()
                if k == _k:
                    d.append(entry)
        for entry in d:
            yield entry


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
        pen.setWidth(common.INDICATOR_WIDTH)
        painter.setPen(pen)
        painter.setBrush(common.FAVOURITE)
        painter.setOpacity(0.35)
        painter.drawRect(self.rect())
        painter.setOpacity(1.0)
        common.draw_aliased_text(
            painter, common.PrimaryFont, self.rect(), 'Drop to add bookmark', QtCore.Qt.AlignCenter, common.FAVOURITE)
        painter.end()

    def show(self):
        """Shows and sets the size of the widget."""
        self.setGeometry(self.parent().geometry())
        super(DropIndicatorWidget, self).show()


class FavouritesWidget(FilesWidget):
    """The widget responsible for showing all the items marked as favourites."""
    SourceModel = FavouritesModel
    Delegate = FilesWidgetDelegate
    ContextMenu = FavouritesWidgetContextMenu

    def __init__(self, parent=None):
        super(FavouritesWidget, self).__init__(parent=parent)
        self.indicatorwidget = DropIndicatorWidget(parent=self)
        self.indicatorwidget.hide()
        self.setStyleSheet('margin: 4px;padding: 4px;border:solid 1px black;')
        self.setWindowTitle(u'Favourites')
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def set_model(self, *args):
        print '!'
        super(FavouritesWidget, self).set_model(*args)
        self.favouritesChanged.connect(self.model().sourceModel().modelDataResetRequested)

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return True
    #
    def inline_icons_count(self):
        return 3

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
        favourites = settings_.local_settings.favourites()

        for url in mime.urls():
            file_info = QtCore.QFileInfo(url.toLocalFile())
            path = file_info.filePath().lower()

            if file_info.suffix().lower() == u'gwb':
                with open(path, 'r') as f:
                    paths = f.readlines()
                    paths = [f.rstrip() for f in paths]

                    for v in paths:
                        if v.lower() not in favourites:
                            favourites.append(v.lower())

            seq = common.get_sequence(path)
            if seq:
                k = seq.group(1) + u'[0]' + seq.group(3) + '.' + seq.group(4)
            else:
                k = path
            favourites.append(k)
        settings_.local_settings.setValue(u'favourites', sorted(list(set(favourites))))
        self.favouritesChanged.emit()

    def eventFilter(self, widget, event):
        """Custom event filter used to paint the background icon."""
        if widget is not self:
            return False

        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                u'favourite', QtGui.QColor(0, 0, 0, 20), 180)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True

        return super(FavouritesWidget, self).eventFilter(widget, event)

    def showEvent(self, event):
        super(FavouritesWidget, self).showEvent(event)
        self.model().sourceModel().modelDataResetRequested.emit()

if __name__ == '__main__':
    a = QtWidgets.QApplication([])
    w = FavouritesWidget()
    w.show()
    a.exec_()
