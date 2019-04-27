from PySide2 import QtWidgets, QtCore, QtGui

from gwbrowser.settings import local_settings

import gwbrowser.common as common
from gwbrowser.fileswidget import FilesWidget
from gwbrowser.fileswidget import FilesModel
from gwbrowser.fileswidget import FilesWidgetDelegate
from gwbrowser.fileswidget import FilesWidgetContextMenu
from gwbrowser.baselistwidget import BaseInlineIconWidget


class FavouritesModel(FilesModel):

    def __initdata__(self):
        """The model-data is simply based on the saved favourites."""
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

        server, job, root, asset = self._parent_item
        location = self.data_key()
        location_path = ('{}/{}/{}/{}/{}'.format(
            server, job, root, asset, location
        ))

        __c = 0
        for filepath in favourites:
            fileroot = filepath.replace(location_path, '')
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

            if filepath in favourites:
                flags = flags | MarkedAsFavourite

            if activefile:
                if activefile in filepath:
                    flags = flags | MarkedAsActive

            idx = len(self._data[dkey][common.FileItem])
            self._data[dkey][common.FileItem][idx] = {
                QtCore.Qt.DisplayRole: filename,
                QtCore.Qt.EditRole: filename,
                QtCore.Qt.StatusTipRole: filepath,
                QtCore.Qt.ToolTipRole: filepath,
                QtCore.Qt.SizeHintRole: rowsize,
                common.FlagsRole: flags,
                common.ParentRole: (server, job, root, asset, location, fileroot),
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
                    if key in favourites:
                        flags = flags | MarkedAsFavourite

                    seqs[seqpath] = {
                        QtCore.Qt.DisplayRole: seqname,
                        QtCore.Qt.EditRole: seqname,
                        QtCore.Qt.StatusTipRole: seqpath,
                        QtCore.Qt.ToolTipRole: seqpath,
                        QtCore.Qt.SizeHintRole: rowsize,
                        common.FlagsRole: flags,
                        common.ParentRole: (server, job, root, asset, location, fileroot),
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
                if filepath in favourites:
                    flags = flags | MarkedAsFavourite

                if activefile:
                    if activefile in filepath:
                        flags = flags | MarkedAsActive

                v[common.FlagsRole] = flags

            elif len(v[common.FramesRole]) == 0:
                v[common.TypeRole] = common.FileItem
            else:
                if activefile:
                    _firsframe = v[common.SequenceRole].expand(r'\1{}\3.\4')
                    _firsframe = _firsframe.format(min(v[common.FramesRole]))
                    if activefile in _firsframe:
                        v[common.FlagsRole] = v[common.FlagsRole] | MarkedAsActive
            self._data[dkey][common.SequenceItem][idx] = v
        self.endResetModel()



class FavouritesWidget(FilesWidget):

    def __init__(self, parent=None):
        super(FilesWidget, self).__init__(parent=parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setWindowTitle(u'Files')
        self.setAutoScroll(True)

        self.setItemDelegate(FilesWidgetDelegate(parent=self))
        self.context_menu_cls = FilesWidgetContextMenu
        self.set_model(FavouritesModel(parent=self))

        self._index_timer = QtCore.QTimer()
        self._index_timer.setInterval(1000)
        self._index_timer.setSingleShot(False)
        self._index_timer.timeout.connect(self.initialize_visible_indexes)

        self.model().sourceModel().modelAboutToBeReset.connect(
            self.reset_thread_worker_queues)
        self.model().modelAboutToBeReset.connect(self.reset_thread_worker_queues)
        self.model().layoutAboutToBeChanged.connect(self.reset_thread_worker_queues)

        # self.model().layoutChanged.connect(self.initialize_visible_indexes)
        self.model().modelAboutToBeReset.connect(self._index_timer.stop)
        self.model().modelReset.connect(self._index_timer.start)


m = FavouritesModel()

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = FavouritesWidget()
    widget.show()
    app.exec_()
