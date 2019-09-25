# -*- coding: utf-8 -*-
"""Classes responsible for interacting with items marked as favourites by the
user.

"""

import os
import functools
from PySide2 import QtWidgets, QtCore, QtGui

from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
from gwbrowser.settings import local_settings

from gwbrowser.basecontextmenu import BaseContextMenu
from gwbrowser.baselistwidget import initdata
from gwbrowser.delegate import FavouritesWidgetDelegate
from gwbrowser.fileswidget import FilesModel
from gwbrowser.fileswidget import FilesWidget

def rsc_path(f, n):
    path = u'{}/../rsc/{}.png'.format(f, n)
    path = os.path.normpath(os.path.abspath(path))
    return path


class FavouritesWidgetContextMenu(BaseContextMenu):
    def __init__(self, index, parent=None):
        super(BaseContextMenu, self).__init__(parent=parent)
        self.index = index

        self.add_remove_favourite_menu()

        if index.isValid():
            self.add_thumbnail_menu()

        self.add_separator()

        if index.isValid():
            self.add_reveal_item_menu()
            self.add_copy_menu()

        self.add_separator()

        self.add_sort_menu()
        self.add_collapse_sequence_menu()

        self.add_separator()

        self.add_refresh_menu()


class FavouritesModel(FilesModel):
    """The model responsible for displaying the saved favourites."""

    def __init__(self, parent=None):
        super(FavouritesModel, self).__init__(threads=0, parent=parent)

    @property
    def generate_thumbnails(self):
        return False

    @generate_thumbnails.setter
    def generate_thumbnails(self, val):
        pass

    @initdata
    def __initdata__(self):
        """The model-data is simply based on the saved favourites - but
        we're only displaying the items that are associated with the current
        bookmark.

        """
        def dflags(): return (
            QtCore.Qt.ItemNeverHasChildren |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            common.MarkedAsFavourite
        )

        if not self._parent_item:
            return
        if not all(self._parent_item):
            return

        dkey = self.data_key()
        rowsize = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)

        # It is quicker to cache these here...
        default_thumbnail_image = ImageCache.get(
            common.rsc_path(__file__, u'favourite_sm'),
            rowsize.height() - common.ROW_SEPARATOR)
        folder_thumbnail_image = ImageCache.get(
            common.rsc_path(__file__, u'folder_sm2'),
            rowsize.height() - common.ROW_SEPARATOR)
        default_background_color = QtGui.QColor(0, 0, 0, 0)

        thumbnails = {}
        defined_thumbnails = set(
            common.creative_cloud_formats +
            common.exports_formats +
            common.scene_formats +
            common.misc_formats
        )
        for ext in defined_thumbnails:
            thumbnails[ext] = ImageCache.get(
                common.rsc_path(__file__, ext), rowsize.height())

        self._data[dkey] = {
            common.FileItem: {}, common.SequenceItem: {}}

        seqs = {}

        favourites = local_settings.value(u'favourites')
        favourites = [f.lower() for f in favourites] if favourites else []

        # When a favourite is saved there's a superflous key saved for sequence items
        # we don't want to display. Removing these here:
        if favourites:
            superfluous = set()
            for f in favourites:
                seq = common.get_sequence(f)
                if seq:
                    superfluous.add(seq.expand(ur'\1\3.\4'))
            favourites = [f for f in favourites if f not in superfluous]
        sfavourites = set(favourites)

        # server, job, root = self._parent_item
        server = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.TempLocation)
        job = 'gwbrowser'
        root = 'favourites'

        for filepath in sfavourites:
            fileroot = filepath

            seq = common.get_sequence(filepath)
            filename = filepath.split(u'/')[-1]

            _, ext = os.path.splitext(filename)
            ext = ext.strip('.')

            if not ext:
                placeholder_image = folder_thumbnail_image
                sortbyname = u'~{}'.format(filename)
            else:
                if ext in defined_thumbnails:
                    placeholder_image = thumbnails[ext]
                else:
                    placeholder_image = default_thumbnail_image
                sortbyname = filename

            flags = dflags()

            idx = len(self._data[dkey][common.FileItem])

            self._data[dkey][common.FileItem][idx] = {
                QtCore.Qt.DisplayRole: filename if ext else filepath,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: rowsize,
                common.EntryRole: [],
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, fileroot),
                common.DescriptionRole: filepath if ext else '',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: seq,
                common.FramesRole: [],
                common.FileInfoLoaded: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                #
                common.FileThumbnailLoaded: False,
                common.DefaultThumbnailRole: default_thumbnail_image,
                common.DefaultThumbnailBackgroundRole: default_background_color,
                common.ThumbnailPathRole: None,
                common.ThumbnailRole: placeholder_image,
                common.ThumbnailBackgroundRole: default_background_color,
                #
                common.TypeRole: common.FileItem,
                common.SortByName: sortbyname,
                # Favourites don't have modified and size attributes
                common.SortByLastModified: len(sortbyname),
                common.SortBySize: len(sortbyname),
            }

            # If the file in question is a sequence, we will also save a reference
            # to it in `self._model_data[location][True]` dictionary.
            if seq:
                try:
                    seqpath = u'{}[0]{}.{}'.format(
                        unicode(seq.group(1), 'utf-8'),
                        unicode(seq.group(3), 'utf-8'),
                        unicode(seq.group(4), 'utf-8'))
                except TypeError:
                    seqpath = u'{}[0]{}.{}'.format(
                        seq.group(1),
                        seq.group(3),
                        seq.group(4))

                if seqpath not in seqs:  # ... and create it if it doesn't exist
                    seqname = seqpath.split(u'/')[-1]
                    flags = dflags()
                    try:
                        key = u'{}{}.{}'.format(
                            unicode(seq.group(1), 'utf-8'),
                            unicode(seq.group(3), 'utf-8'),
                            unicode(seq.group(4), 'utf-8'))
                    except TypeError:
                        key = u'{}{}.{}'.format(
                            seq.group(1),
                            seq.group(3),
                            seq.group(4))

                    flags = dflags()
                    key = u'{}{}.{}'.format(
                        seq.group(1), seq.group(3), seq.group(4))

                    seqs[seqpath] = {
                        QtCore.Qt.DisplayRole: seqname,
                        QtCore.Qt.EditRole: seqname,
                        QtCore.Qt.StatusTipRole: seqpath,
                        QtCore.Qt.ToolTipRole: seqpath,
                        QtCore.Qt.SizeHintRole: rowsize,
                        common.EntryRole: [],
                        common.FlagsRole: flags,
                        common.ParentRole: (server, job, root, fileroot, ),
                        common.DescriptionRole: u'',
                        common.TodoCountRole: 0,
                        common.FileDetailsRole: u'',
                        common.SequenceRole: seq,
                        common.FramesRole: [],
                        common.FileInfoLoaded: False,
                        #
                        common.FileThumbnailLoaded: False,
                        common.DefaultThumbnailRole: default_thumbnail_image,
                        common.DefaultThumbnailBackgroundRole: default_background_color,
                        common.ThumbnailPathRole: None,
                        common.ThumbnailRole: placeholder_image,
                        common.ThumbnailBackgroundRole: default_background_color,
                        #
                        common.TypeRole: common.SequenceItem,
                        common.SortByName: seqpath,
                        common.SortByLastModified: len(seqpath),
                        common.SortBySize: len(seqpath),
                    }
                seqs[seqpath][common.FramesRole].append(seq.group(2))
            else:
                seqs[filepath] = self._data[dkey][common.FileItem][idx]

        # Casting the sequence data onto the model
        for v in seqs.itervalues():
            idx = len(self._data[dkey][common.SequenceItem])
            # A sequence with only one element is not a sequence!
            if len(v[common.FramesRole]) == 1:
                filepath = v[common.SequenceRole].expand(ur'\1{}\3.\4')
                filepath = filepath.format(v[common.FramesRole][0])
                filename = filepath.split(u'/')[-1]
                v[QtCore.Qt.DisplayRole] = filename
                v[QtCore.Qt.EditRole] = filename
                v[QtCore.Qt.StatusTipRole] = filepath
                v[QtCore.Qt.ToolTipRole] = filepath
                v[common.TypeRole] = common.FileItem
                v[common.SortByName] = filepath
                v[common.SortByLastModified] = len(filepath)
                v[common.SortBySize] = len(filepath)

                flags = dflags()
                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem
            self._data[dkey][common.SequenceItem][idx] = v


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

    def __init__(self, parent=None):
        super(FavouritesWidget, self).__init__(parent=parent)
        self.setWindowTitle(u'Favourites')
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        # Context menu, delegate, model...
        self.context_menu_cls = FavouritesWidgetContextMenu
        self.setItemDelegate(FavouritesWidgetDelegate(parent=self))
        self.set_model(FavouritesModel(parent=self))

        # Timer
        self.index_update_timer = QtCore.QTimer(parent=self)
        self.index_update_timer.setInterval(common.FTIMER_INTERVAL)
        self.index_update_timer.setSingleShot(False)
        self.index_update_timer.timeout.connect(self.initialize_visible_indexes)


        # We're stopping the index timer when the model is loading.
        self.model().modelAboutToBeReset.connect(self.index_update_timer.stop)
        self.model().modelReset.connect(self.index_update_timer.start)
        self.model().layoutAboutToBeChanged.connect(self.index_update_timer.stop)
        self.model().layoutChanged.connect(self.index_update_timer.start)

        # For performance's sake...
        self.verticalScrollBar().sliderPressed.connect(
            self.index_update_timer.stop)
        self.verticalScrollBar().sliderReleased.connect(
            self.index_update_timer.start)

        self.indicatorwidget = DropIndicatorWidget(parent=self)
        self.indicatorwidget.hide()

    def buttons_hidden(self):
        """Returns the visibility of the inline icon buttons."""
        return True

    def inline_icons_count(self):
        return 0

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
        favourites = local_settings.value(u'favourites')
        favourites = [f.lower() for f in favourites] if favourites else []

        for url in mime.urls():
            path = QtCore.QFileInfo(url.toLocalFile()).filePath()
            if path.lower() not in favourites:
                favourites.append(path.lower())
        local_settings.setValue(u'favourites', sorted(list(set(favourites))))
        self.favouritesChanged.emit()

    def mouseReleaseEvent(self, event):
        """Inline-button methods are triggered here."""
        if not isinstance(event, QtGui.QMouseEvent):
            return None
        return super(QtWidgets.QListView, self).mouseReleaseEvent(event)

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


if __name__ == '__main__':
    a = QtWidgets.QApplication([])
    w = FavouritesWidget()
    w.show()
    a.exec_()
