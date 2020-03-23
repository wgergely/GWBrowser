# -*- coding: utf-8 -*-
"""The module for defining the AddAssetWidget widget.
The widget is used to add a new asset (eg. a shot) to a bookmark.

"""
from PySide2 import QtWidgets, QtCore, QtGui

import bookmarks.managebookmarks as managebookmarks
import bookmarks.common as common
import bookmarks.common_ui as common_ui
import bookmarks.images as images

BUTTON_SIZE = common.INLINE_ICON_SIZE
ROW_HEIGHT = common.ROW_HEIGHT


class AddAssetWidget(QtWidgets.QDialog):
    def __init__(self, path, parent=None):
        super(AddAssetWidget, self).__init__(parent=parent)
        self.templates_widget = None
        self._create_UI()
        self.templates_widget.set_path(path)

        self.hide_button.clicked.connect(self.close)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(u'Add asset: {}'.format(path))
        self.setWindowFlags(QtCore.Qt.Widget)

        self.templates_widget.templateCreated.connect(self.popup)

    @QtCore.Slot(unicode)
    def popup(self, v):
        common_ui.OkBox(
            u'Successully created "{}"'.format(v),
            u'',
            parent=self
        ).exec_()

    def _create_UI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(u'', parent=self)
        label = QtWidgets.QLabel()
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'assets', common.SECONDARY_BACKGROUND, common.ROW_HEIGHT)
        label.setPixmap(pixmap)
        row.layout().addWidget(label, 0)
        label = common_ui.PaintedLabel(
            u' Add Asset', color=common.TEXT, size=common.LARGE_FONT_SIZE, parent=self)
        row.layout().addWidget(label, 0)
        row.layout().addStretch(1)

        self.hide_button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            BUTTON_SIZE,
            description=u'Hide',
            parent=row
        )
        row.layout().addWidget(self.hide_button, 0)

        self.templates_widget = managebookmarks.TemplatesWidget(
            u'asset', parent=self)
        self.layout().addWidget(self.templates_widget, 1)
        self.layout().addStretch(1)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        o = common.INDICATOR_WIDTH
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(common.ROW_SEPARATOR)
        painter.setPen(pen)
        painter.setBrush(common.BACKGROUND)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setOpacity(0.9)
        painter.drawRoundedRect(rect, common.INDICATOR_WIDTH, common.INDICATOR_WIDTH)
        painter.end()

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH, common.HEIGHT)


if __name__ == '__main__':
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])
    w = AddAssetWidget(None)
    w.exec_()
