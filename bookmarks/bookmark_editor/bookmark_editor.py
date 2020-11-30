"""Widget used to view the list of jobs on a server.

"""
import re

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import settings
from .. import images
from .. import common_ui
from .. import listbookmarks
from . import server
from . import job
from . import bookmark


def key(*args):
    def r(s): return re.sub(ur'[\\]+', u'/',
                            s, flags=re.UNICODE | re.IGNORECASE)
    k = u'/'.join([r(f).rstrip(u'/') for f in args]).rstrip(u'/')
    return k


@QtCore.Slot(unicode)
@QtCore.Slot(unicode)
@QtCore.Slot(unicode)
def save_bookmark(server, job, root):
    """Saves the given bookmark to the local settings.

    """
    settings.local_settings.sync()
    d = settings.local_settings.value(u'bookmarks')
    k = key(server, job, root)
    d[k] = {
        u'server': unicode(server).encode(u'utf-8'),
        u'job':  unicode(job).encode(u'utf-8'),
        u'root':  unicode(root).encode(u'utf-8')
    }
    settings.local_settings.setValue(u'bookmarks', d)


@QtCore.Slot(unicode)
@QtCore.Slot(unicode)
@QtCore.Slot(unicode)
def remove_bookmark(server, job, root):
    """Remove the bookmark from the local settings.

    """
    settings.local_settings.sync()
    d = settings.local_settings.value(u'bookmarks')
    k = key(server, job, root)
    if k in d:
        del d[k]
    settings.local_settings.setValue(u'bookmarks', d)


class BookmarksWidget(listbookmarks.BookmarksWidget):
    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)

    def buttons_hidden(self):
        return False

    def contextMenuEvent(self, event):
        return


class BookmarkEditorWidget(QtWidgets.QDialog):
    bookmarksChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(BookmarkEditorWidget, self).__init__(parent=parent)
        self._create_UI()
        self._connect_signals()

        self.server_widget = None
        self.server_add_button = None
        self.job_widget = None
        self.job_add_button = None
        self.bookmark_widget = None
        self.bookmark_add_button = None
        self.bookmarks_widget = None

        self.setObjectName(u'BookmarksEditorWidget')
        self.setWindowTitle(u'Bookmark Editor')

    def _create_UI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)

        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        row = common_ui.add_row(None, parent=self)
        label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'bookmark', common.SECONDARY_BACKGROUND, common.ROW_HEIGHT())
        label.setPixmap(pixmap)
        row.layout().addWidget(label, 0)
        label = common_ui.PaintedLabel(
            u'Bookmark Editor', size=common.LARGE_FONT_SIZE(), parent=self)
        row.layout().addWidget(label, 0)
        row.layout().addStretch(1)
        self.layout().addSpacing(common.MARGIN() * 0.5)

        # main_row = row = common_ui.add_row(None, height=None, padding=None, parent=self)
        main_row = common_ui.get_group(vertical=False, parent=self)
        main_row.setObjectName(u'AddBookmarkWidget')
        main_row.setStyleSheet(
            u'QGroupBox#AddBookmarkWidget {{background-color: rgba({});}}'.format(
                common.rgb(common.SECONDARY_BACKGROUND))
        )

        row = common_ui.add_row(None, vertical=True,
                                height=None, padding=None, parent=main_row)
        label = common_ui.PaintedLabel(u'Servers', color=common.TEXT_DISABLED)
        self.server_widget = server.ServerListWidget(parent=self)
        self.server_add_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            common.MARGIN(),
            u'Add a new server',
            parent=self
        )
        _row = common_ui.add_row(None, height=common.MARGIN(), parent=row)
        _row.layout().addWidget(self.server_add_button)
        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        row.layout().addWidget(self.server_widget, 1)

        row = common_ui.add_row(None, vertical=True,
                                height=None, padding=None, parent=main_row)
        label = common_ui.PaintedLabel(u'Jobs', color=common.TEXT_DISABLED)
        self.job_widget = job.JobListWidget(parent=self)
        self.job_add_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            common.MARGIN(),
            u'Add a new server',
            parent=self
        )
        _row = common_ui.add_row(None, height=common.MARGIN(), parent=row)
        _row.layout().addWidget(self.job_add_button)
        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        row.layout().addWidget(self.job_widget, 1)

        row = common_ui.add_row(None, vertical=True,
                                height=None, padding=None, parent=main_row)
        label = common_ui.PaintedLabel(
            u'Bookmarks', color=common.TEXT_DISABLED)
        self.bookmark_widget = bookmark.BookmarkListWidget(parent=self)
        self.bookmark_add_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            common.MARGIN(),
            u'Add a new server',
            parent=self
        )
        _row = common_ui.add_row(None, height=common.MARGIN(), parent=row)
        _row.layout().addWidget(self.bookmark_add_button)
        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        row.layout().addWidget(self.bookmark_widget, 1)

        row = common_ui.get_group(parent=self)
        row.setObjectName(u'bookmarkContainerWidget')
        row.setStyleSheet(
            u'QGroupBox#bookmarkContainerWidget {{background-color: rgba({});}}'.format(
                common.rgb(common.SECONDARY_BACKGROUND))
        )
        row.setMinimumHeight(common.HEIGHT() * 0.5)

        o = common.MARGIN() * 0.5
        row.layout().setContentsMargins(o, o, o, o)
        self.bookmarks_widget = BookmarksWidget(parent=self)
        row.layout().addWidget(self.bookmarks_widget, 1)

        row = common_ui.add_row(None, parent=self)
        self.done_button = common_ui.PaintedButton(
            u'Done',
            parent=self
        )
        row.layout().addStretch(1)
        row.layout().addWidget(self.done_button)

    def _connect_signals(self):
        self.server_widget.serverChanged.connect(
            self.job_widget.server_changed)
        self.job_widget.jobChanged.connect(self.bookmark_widget.job_changed)

        self.server_add_button.clicked.connect(self.server_widget.add)
        self.job_add_button.clicked.connect(self.job_widget.add)
        self.bookmark_add_button.clicked.connect(self.bookmark_widget.add)

        model = self.bookmarks_widget.model().sourceModel()
        self.bookmarksChanged.connect(model.modelDataResetRequested)

        self.bookmark_widget.loaded.connect(self.bookmarksChanged)

        self.bookmark_widget.bookmarkAdded.connect(save_bookmark)
        self.bookmark_widget.bookmarkRemoved.connect(remove_bookmark)

        self.bookmark_widget.bookmarkAdded.connect(self.bookmarksChanged)
        self.bookmark_widget.bookmarkRemoved.connect(self.bookmarksChanged)

        self.done_button.clicked.connect(self.close)
        self.finished.connect(self.bookmarksChanged)
