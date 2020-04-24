# -*- coding: utf-8 -*-
"""The widget used to add a new asset (eg. a shot) to a bookmark.

See `managebookmarks.TemplatesWidget` for more information, the main widget
responsible for listing, saving and expanding zip template files.

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
from PySide2 import QtWidgets, QtCore

import bookmarks.managebookmarks as managebookmarks
import bookmarks.common as common
import bookmarks.common_ui as common_ui
import bookmarks.images as images


_widget_instance = None


class AddAssetWidget(QtWidgets.QDialog):
    """Widget used to create a new asset in a specified folder.

    Args:
        path (unicode): Destination path for the new assets.

    """

    def __init__(self, server, job, root, parent=None):
        global _widget_instance
        _widget_instance = self

        super(AddAssetWidget, self).__init__(parent=parent)
        if not parent:
            common.set_custom_stylesheet(self)

        self.server = server
        self.job = job
        self.root = root

        self.templates_widget = None
        self._create_UI()

        bookmark = u'{}/{}/{}'.format(server, job, root)
        self.templates_widget.set_path(bookmark)

        self.hide_button.clicked.connect(self.close)
        self.setWindowTitle(u'Add a new asset')

        self.templates_widget.templateCreated.connect(self.popup)

    @QtCore.Slot(unicode)
    def popup(self, v):
        common_ui.OkBox(
            u'Successully created "{}"'.format(v),
            u'',
        ).open()

    def _create_UI(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(u'', parent=self)
        self.hide_button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            common.MARGIN(),
            description=u'Hide',
            parent=row
        )

        bookmark = u'{}/{}/{}'.format(self.server, self.job, self.root)
        source = images.get_thumbnail_path(
            self.server,
            self.job,
            self.root,
            bookmark
        )

        pixmap = images.ImageCache.get_pixmap(source, row.height())
        if not pixmap:
            source = images.get_placeholder_path(
                bookmark, fallback=u'thumb_bookmark_gray')
            pixmap = images.ImageCache.get_pixmap(source, row.height())

        if pixmap:
            thumbnail = QtWidgets.QLabel(parent=self)
            thumbnail.setPixmap(pixmap)
            row.layout().addWidget(thumbnail, 0)
            row.layout().addSpacing(o * 0.5)

        text = u'{}  |  {}'.format(
            self.job.upper(), self.root.upper())
        label = common_ui.PaintedLabel(
            text, size=common.LARGE_FONT_SIZE())

        row.layout().addWidget(label)
        row.layout().addStretch(1)
        row.layout().addWidget(self.hide_button, 0)

        # *****************************************

        self.templates_widget = managebookmarks.TemplatesWidget(
            u'asset', parent=self)
        self.layout().addWidget(self.templates_widget, 1)

        s = u'Independent of the template, basic <span style="color:rgba({ADD});">mode</span> and \
<span style="color:rgba({ADD});">task</span> are defined in \
<span style="color:rgba({H});">Preferences -> Default Paths</span>. \
Ideally, both the template and the preferences should define the same folders.'.format(
            ADD=common.rgb(common.ADD),
            H=common.rgb(common.TEXT_SELECTED),
        )
        common_ui.add_description(s, label='hint', parent=self)
        self.layout().addStretch(1)

    def sizeHint(self):
        """Custom size hint"""
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())
