# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101

"""Classes responsible for interacting with items marked as favourites by the
user."""


import sys
import os
from PySide2 import QtWidgets, QtCore, QtGui

from gwbrowser.settings import local_settings
import gwbrowser.common as common
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.fileswidget import FilesModel
from gwbrowser.delegate import FavouritesWidgetDelegate
from gwbrowser.fileswidget import FilesWidgetContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.imagecache import ImageCache


class FavouritesWidgetContextMenu(FilesWidgetContextMenu):
    def __init__(self, index, parent=None):
        super(FilesWidgetContextMenu, self).__init__(index, parent=parent)
        # Adding persistent actions

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

    def __initdata__(self):
        """The model-data is simply based on the saved favourites - but
        we're only displaying the items that are associated with the current
        bookmark.

        """
        def rsc_path(f, n):
            path = u'{}/../rsc/{}.png'.format(f, n)
            path = os.path.normpath(os.path.abspath(path))
            return path

        def dflags(): return (
            QtCore.Qt.ItemNeverHasChildren |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable
        )
        dkey = self.data_key()
        rowsize = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)
        self._data[dkey] = {
            common.FileItem: {}, common.SequenceItem: {}}

        seqs = {}

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        server, job, root = self._parent_item
        bookmark = ('{}/{}/{}'.format(server, job, root))
        placeholder_color = QtGui.QColor(0, 0, 0, 55)

        __c = 0
        for filepath in favourites:
            if bookmark not in filepath:
                continue

            if not QtCore.QFileInfo(filepath).exists():
                continue

            fileroot = filepath.replace(bookmark, '')
            fileroot = '/'.join(fileroot.split('/')[:-1]).strip('/')

            seq = common.get_sequence(filepath)
            filename = filepath.split('/')[-1]
            ext = filename.split('.')[-1]
            if ext in (common._creative_cloud_formats + common._exports_formats + common._scene_formats):
                placeholder_image = ImageCache.instance().get(
                    rsc_path(__file__, ext), rowsize.height())
            else:
                placeholder_image = ImageCache.instance().get(
                    rsc_path(__file__, 'placeholder'), rowsize.height())

            flags = dflags()

            idx = len(self._data[dkey][common.FileItem])
            self._data[dkey][common.FileItem][idx] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: rowsize,
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, fileroot),
                common.DescriptionRole: u'',
                common.TodoCountRole: 0,
                common.FileDetailsRole: u'',
                common.SequenceRole: seq,
                common.FramesRole: [],
                common.StatusRole: False,
                common.StartpathRole: None,
                common.EndpathRole: None,
                common.ThumbnailRole: placeholder_image,
                common.ThumbnailBackgroundRole: placeholder_color,
                common.TypeRole: common.FileItem,
                common.SortByName: filepath,
                common.SortByLastModified: filepath,
                common.SortBySize: filepath,
            }

            # If the file in question is a sequence, we will also save a reference
            # to it in `self._model_data[location][True]` dictionary.
            if seq:
                seqpath = u'{}[0]{}.{}'.format(
                    seq.group(1), seq.group(3), seq.group(4))

                if seqpath not in seqs:  # ... and create it if it doesn't exist
                    seqname = seqpath.split(u'/')[-1]

                    flags = dflags()
                    key = u'{}{}.{}'.format(
                        seq.group(1), seq.group(3), seq.group(4))

                    seqs[seqpath] = {
                        QtCore.Qt.DisplayRole: seqname,
                        QtCore.Qt.EditRole: seqname,
                        QtCore.Qt.StatusTipRole: seqpath,
                        QtCore.Qt.ToolTipRole: seqpath,
                        QtCore.Qt.SizeHintRole: rowsize,
                        common.FlagsRole: flags,
                        common.ParentRole: (server, job, root, fileroot),
                        common.DescriptionRole: u'',
                        common.TodoCountRole: 0,
                        common.FileDetailsRole: u'',
                        common.SequenceRole: seq,
                        common.FramesRole: [],
                        common.StatusRole: False,
                        common.StartpathRole: None,
                        common.EndpathRole: None,
                        common.ThumbnailRole: placeholder_image,
                        common.ThumbnailBackgroundRole: placeholder_color,
                        common.TypeRole: common.SequenceItem,
                        common.SortByName: seqpath,
                        common.SortByLastModified: seqpath,
                        common.SortBySize: seqpath,
                    }
                seqs[seqpath][common.FramesRole].append(seq.group(2))
            else:
                seqs[filepath] = self._data[dkey][common.FileItem][idx]

        # Casting the sequence data onto the model
        for v in seqs.itervalues():
            idx = len(self._data[dkey][common.SequenceItem])
            # A sequence with only one element is not a sequence!
            if len(v[common.FramesRole]) == 1:
                filepath = v[common.SequenceRole].expand(r'\1{}\3.\4')
                filepath = filepath.format(v[common.FramesRole][0])
                filename = filepath.split(u'/')[-1]
                v[QtCore.Qt.DisplayRole] = filename
                v[QtCore.Qt.EditRole] = filename
                v[QtCore.Qt.StatusTipRole] = filepath
                v[QtCore.Qt.ToolTipRole] = filepath
                v[common.TypeRole] = common.FileItem
                v[common.SortByName] = filepath
                v[common.SortByLastModified] = filepath
                v[common.SortBySize] = filepath

                flags = dflags()
                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem
            self._data[dkey][common.SequenceItem][idx] = v
        self.endResetModel()


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
        super(FilesWidget, self).__init__(parent=parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

        self.setWindowTitle(u'Favourites')
        self.setAutoScroll(True)

        self.setItemDelegate(FavouritesWidgetDelegate(parent=self))
        self.context_menu_cls = FavouritesWidgetContextMenu
        self.set_model(FavouritesModel(parent=self))

        self._index_timer = QtCore.QTimer()
        self._index_timer.setInterval(1000)
        self._index_timer.setSingleShot(False)
        self._index_timer.timeout.connect(self.initialize_visible_indexes)

        self.model().sourceModel().modelAboutToBeReset.connect(
            self.reset_thread_worker_queues)
        self.model().modelAboutToBeReset.connect(self.reset_thread_worker_queues)
        self.model().layoutAboutToBeChanged.connect(self.reset_thread_worker_queues)

        self.model().modelAboutToBeReset.connect(self._index_timer.stop)
        self.model().modelReset.connect(self._index_timer.start)

        self.indicatorwidget = DropIndicatorWidget(parent=self)
        self.indicatorwidget.hide()


    def inline_icons_count(self):
        return 1

    def check_accept(self, mime):
        """Check if the item about to be dropped is valid."""
        bookmark = self.model().sourceModel()._parent_item
        bookmark = u'/'.join(self.model().sourceModel()._parent_item)

        if mime.hasUrls():
            urls = mime.urls()
            if all([(bookmark in QtCore.QFileInfo(f.toLocalFile()).filePath()) for f in urls]):
                return True
        return False

    def dragEnterEvent(self, event):
        if event.source() == self:
            return

        if self.check_accept(event.mimeData()):
            self.indicatorwidget.show()
            return event.accept()
        self.indicatorwidget.hide()

    def dragLeaveEvent(self, event):
        self.indicatorwidget.hide()

    def dragMoveEvent(self, event):
        if self.check_accept(event.mimeData()):
            event.accept()

    def dropEvent(self, event):
        self.indicatorwidget.hide()

        if event.source() == self:
            return

        mime = event.mimeData()
        if not self.check_accept(mime):
            return

        event.accept()

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        for url in mime.urls():
            path = QtCore.QFileInfo(url.toLocalFile()).filePath()
            if path not in favourites:
                favourites.append(path)
        local_settings.setValue(u'favourites', sorted(list(set(favourites))))
        self.model().sourceModel().modelDataResetRequested.emit()

    def mousePressEvent(self, event):
        if not isinstance(event, QtGui.QMouseEvent):
            return
        return super(BaseInlineIconWidget, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Inline-button methods are triggered here."""
        if not isinstance(event, QtGui.QMouseEvent):
            self.reset_multitoggle()
            return None

        index = self.indexAt(event.pos())
        rect = self.visualRect(index)

        if self.viewport().width() < 360.0:
            return super(QtWidgets.QListWidget, self).mouseReleaseEvent(event)

        for n in xrange(self.inline_icons_count()):
            _, bg_rect = self.itemDelegate().get_inline_icon_rect(
                rect, common.INLINE_ICON_SIZE, n)

            if not bg_rect.contains(event.pos()):
                continue

            if n == 0:
                common.reveal(index.data(QtCore.Qt.StatusTipRole))
                break

    def eventFilter(self, widget, event):
        super(FilesWidget, self).eventFilter(widget, event)
        if widget is not self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            # Let's paint the icon of the current mode
            painter = QtGui.QPainter()
            painter.begin(self)
            pixmap = ImageCache.get_rsc_pixmap(
                'favourite', QtGui.QColor(0, 0, 0, 10), 128)
            rect = pixmap.rect()
            rect.moveCenter(self.rect().center())
            painter.drawPixmap(rect, pixmap, pixmap.rect())
            painter.end()
            return True
        return False

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FavouritesWidget()
    widget.show()
    app.exec_()
