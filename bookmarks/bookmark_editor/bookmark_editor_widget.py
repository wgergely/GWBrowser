# -*- coding: utf-8 -*-
"""The main Bookmark Editor widget.

The editor is used to add or remove bookmarks from the bookmark list.
The widget is also responsible for editing the list of servers and jobs that
will contain the bookmarks.

The definitions for the server, job and bookmark editor editors are found
in the `bookmark_editor` submodule.

"""
import functools

from PySide2 import QtCore, QtWidgets

from .. import common
from .. import settings
from .. import common_ui

from . import server_widget
from . import job_widget
from . import bookmark_widget



instance = None

def close():
    global instance
    if instance is None:
        return
    instance.close()
    instance.deleteLater()
    instance = None


def show():
    global instance

    close()
    instance = BookmarkEditorWidget()
    instance.open()
    return instance



class BookmarkEditorWidget(QtWidgets.QDialog):
    """The main editor used to add or remove bookmarks, jobs and servers.

    """
    bookmarksChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(BookmarkEditorWidget, self).__init__(
            parent=parent,
            f=QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint
        )

        self.server_widget = None
        self.server_add_button = None
        self.job_widget = None
        self.job_add_button = None
        self.bookmark_widget = None
        self.bookmark_add_button = None

        self.setObjectName(u'BookmarksEditorWidget')
        self.setWindowTitle(u'Bookmark Editor')

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)

        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        _o = common.INDICATOR_WIDTH()
        main_row = common_ui.get_group(vertical=False, parent=self, margin=0)
        main_row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        main_row.layout().setSpacing(common.INDICATOR_WIDTH())
        main_row.layout().setContentsMargins(_o, _o, _o, _o)
        main_row.setObjectName(u'AddBookmarkWidget')

        row = common_ui.get_group(
            parent=main_row, margin=common.MARGIN() * 0.5)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        label = common_ui.PaintedLabel(
            settings.ServerKey.title(),
            color=common.TEXT_DISABLED
        )

        _row = common_ui.add_row(None, height=common.MARGIN(), parent=row)
        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)

        self.server_widget = server_widget.ServerListWidget(parent=row)
        self.server_add_button = common_ui.ClickableIconButton(
            u'CopyAction',
            (common.ADD, common.ADD),
            common.MARGIN(),
            u'Add a new server',
            parent=_row
        )
        _row.layout().addWidget(self.server_add_button)
        row.layout().addWidget(self.server_widget, 1)

        row = common_ui.get_group(
            parent=main_row, margin=common.MARGIN() * 0.5)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        label = common_ui.PaintedLabel(settings.JobKey.title(), color=common.TEXT_DISABLED)

        self.job_widget = job_widget.JobListWidget(parent=self)
        self.job_add_button = common_ui.ClickableIconButton(
            u'CopyAction',
            (common.ADD, common.ADD),
            common.MARGIN(),
            u'Add a new server',
            parent=self
        )
        _row = common_ui.add_row(None, height=common.MARGIN(), parent=row)
        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        _row.layout().addWidget(self.job_add_button)
        row.layout().addWidget(self.job_widget, 1)

        row = common_ui.get_group(
            parent=main_row, margin=common.MARGIN() * 0.5)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        label = common_ui.PaintedLabel(u'Bookmark', color=common.TEXT_DISABLED)

        self.bookmark_widget = bookmark_widget.BookmarkListWidget(parent=self)
        self.bookmark_add_button = common_ui.ClickableIconButton(
            u'CopyAction',
            (common.ADD, common.ADD),
            common.MARGIN(),
            u'Add a new server',
            parent=self
        )
        _row = common_ui.add_row(None, height=common.MARGIN(), parent=row)
        _row.layout().addWidget(label, 0)
        _row.layout().addStretch(1)
        _row.layout().addWidget(self.bookmark_add_button)
        row.layout().addWidget(self.bookmark_widget, 1)

        row = common_ui.add_row(None, parent=self)
        self.done_button = common_ui.PaintedButton(
            u'Done',
            parent=self
        )
        self.done_button.setFixedHeight(common.ROW_HEIGHT())
        row.layout().addWidget(self.done_button, 1)

    @QtCore.Slot(QtWidgets.QWidget)
    @QtCore.Slot(bool)
    def set_hidden(self, widget, v, *args, **kwargs):
        if not v:
            widget.setHidden(True)
        else:
            widget.setHidden(False)

    def _connect_signals(self):
        self.server_widget.serverChanged.connect(
            functools.partial(self.set_hidden, self.job_widget.parent()))
        self.server_widget.serverChanged.connect(
            functools.partial(self.set_hidden, self.job_add_button.parent()))
        self.server_widget.serverChanged.connect(
            functools.partial(self.set_hidden, self.bookmark_widget.parent()))
        self.server_widget.serverChanged.connect(
            functools.partial(self.set_hidden, self.bookmark_add_button.parent()))

        self.job_widget.jobChanged.connect(
            functools.partial(self.set_hidden, self.bookmark_widget.parent()))
        self.job_widget.jobChanged.connect(
            functools.partial(self.set_hidden, self.bookmark_add_button.parent()))

        self.server_widget.serverChanged.connect(
            self.job_widget.server_changed)
        self.job_widget.jobChanged.connect(self.bookmark_widget.job_changed)

        self.server_add_button.clicked.connect(self.server_widget.add)
        self.job_add_button.clicked.connect(self.job_widget.add)
        self.bookmark_add_button.clicked.connect(self.bookmark_widget.add)

        self.bookmark_widget.bookmarkAdded.connect(settings.local_settings.save_bookmark)
        self.bookmark_widget.bookmarkRemoved.connect(settings.local_settings.remove_bookmark)

        # self.bookmark_widget.loaded.connect(self.bookmarksChanged)
        self.bookmark_widget.bookmarkAdded.connect(self.bookmarksChanged)
        self.bookmark_widget.bookmarkRemoved.connect(self.bookmarksChanged)

        self.done_button.clicked.connect(self.close)
        # self.finished.connect(self.bookmarksChanged)
