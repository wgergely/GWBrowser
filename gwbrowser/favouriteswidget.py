# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101

"""Classes responsible for interacting with items marked as favourites by the
user."""


import sys
import os
from PySide2 import QtWidgets, QtCore, QtGui

import gwbrowser.gwscandir as gwscandir
from gwbrowser.settings import local_settings
import gwbrowser.common as common
import gwbrowser.settings as Settings
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.fileswidget import FilesModel
from gwbrowser.delegate import FavouritesWidgetDelegate
from gwbrowser.fileswidget import FilesWidgetContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget
from gwbrowser.imagecache import ImageCache


def rsc_path(f, n):
    path = u'{}/../rsc/{}.png'.format(f, n)
    path = os.path.normpath(os.path.abspath(path))
    return path


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

        def dflags(): return (
            QtCore.Qt.ItemNeverHasChildren |
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            Settings.MarkedAsFavourite
        )
        dkey = self.data_key()
        rowsize = QtCore.QSize(common.WIDTH, common.ROW_HEIGHT)
        self._data[dkey] = {
            common.FileItem: {}, common.SequenceItem: {}}

        seqs = {}

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        if not self._parent_item:
            return
        if not all(self._parent_item):
            return

        server, job, root = self._parent_item
        bookmark = (u'{}/{}/{}'.format(server, job, root))
        placeholder_color = QtGui.QColor(0, 0, 0, 55)

        for filepath in favourites:
            file_info = QtCore.QFileInfo(filepath)
            if not file_info.exists():
                continue

            fileroot = file_info.filePath()
            if u'{}/{}/{}'.format(server, job, root) in fileroot:
                fileroot = file_info.filePath().replace(
                    u'{}/{}/{}'.format(server, job, root),
                    u''
                )
            else:
                continue

            seq = common.get_sequence(filepath)
            filename = filepath.split('/')[-1]
            ext = filename.split('.')[-1]

            if ext in (common._creative_cloud_formats + common._exports_formats + common._scene_formats):
                placeholder_image = ImageCache.instance().get(
                    rsc_path(__file__, ext), rowsize.height())
            else:
                placeholder_image = ImageCache.instance().get(
                    rsc_path(__file__, u'placeholder'), rowsize.height())

            flags = dflags()

            fname = filepath.split(u'/').pop()
            pdir = filepath.replace(fname, u'')
            entry = [f for f in gwscandir.scandir(pdir) if f.name == filename]
            if not entry:
                continue
            entry = entry[0]
            stat = entry.stat()

            idx = len(self._data[dkey][common.FileItem])
            self._data[dkey][common.FileItem][idx] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: rowsize,
                common.EntryRole: [entry,],
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
                common.SortByLastModified: stat.st_mtime,
                common.SortBySize: stat.st_size,
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
                        common.StatusRole: False,
                        common.StartpathRole: None,
                        common.EndpathRole: None,
                        common.ThumbnailRole: placeholder_image,
                        common.ThumbnailBackgroundRole: placeholder_color,
                        common.TypeRole: common.SequenceItem,
                        common.SortByName: seqpath,
                        common.SortByLastModified: -1,
                        common.SortBySize: 0,
                    }
                seqs[seqpath][common.FramesRole].append(seq.group(2))
                seqs[seqpath][common.SortBySize] += entry.stat().st_size
                seqs[seqpath][common.EntryRole].append(entry)
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
                v[common.SortByLastModified] = filepath
                v[common.SortBySize] = v[common.EntryRole][0].stat().st_size

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

    def toggle_favourite(self, index, state=None):
        """Removes the given index (and all sub-files if sequence) from favourites.

        Args:
            item (QListWidgetItem): The item to change.

        """
        if not index.isValid():
            return

        favourites = local_settings.value(u'favourites')
        favourites = favourites if favourites else []

        source_index = self.model().mapToSource(index)
        data = source_index.model().model_data()

        key = index.data(QtCore.Qt.StatusTipRole)
        collapsed = common.is_collapsed(key)
        if collapsed:
            key = collapsed.expand(ur'\1\3')

        if key in favourites:
            favourites.remove(key)
            data[source_index.row()][common.FlagsRole] = data[source_index.row(
            )][common.FlagsRole] & ~Settings.MarkedAsFavourite

            # When toggling a sequence item, we will toggle all the individual sequence items as well
            if self.model().sourceModel().data_type() == common.SequenceItem:
                m = self.model().sourceModel()
                k = m.data_key()
                t = common.FileItem
                _data = m._data[k][t]

                # Let's find the item in the model data
                for frame in data[source_index.row()][common.FramesRole]:
                    _path = data[source_index.row()][common.SequenceRole].expand(ur'\1{}\3.\4')
                    _path = _path.format(frame)
                    _index = None
                    for val in _data.itervalues():
                        if val[QtCore.Qt.StatusTipRole] == _path:
                            _index = val # Found it!
                            break
                    if _index:
                        if _index[QtCore.Qt.StatusTipRole] in favourites:
                            favourites.remove(_index[QtCore.Qt.StatusTipRole])
                        _index[common.FlagsRole] = _index[common.FlagsRole] & ~Settings.MarkedAsFavourite

        local_settings.setValue(u'favourites', sorted(list(set(favourites))))
        self.favouritesChanged.emit()
        index.model().dataChanged.emit(index, index)

    def inline_icons_count(self):
        return 2

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
            return # Won't allow dropping an item from itself

        mime = event.mimeData()
        if not mime.hasUrls():
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
                self.toggle_favourite(index)
                self.model().invalidateFilter()
                break
            if n == 1:
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
