"""This modules defines the widget used to add a new asset to a bookmark."""

import gwbrowser.managebookmarks as managebookmarks
from PySide2 import QtWidgets, QtCore, QtGui
import gwbrowser.common as common
import gwbrowser.common_ui as common_ui
from gwbrowser.imagecache import ImageCache

BUTTON_SIZE = 20
ROW_HEIGHT = 28


class AddAssetWidget(QtWidgets.QDialog):

    def __init__(self, path, parent=None):
        super(AddAssetWidget, self).__init__(parent=parent)
        self.templates_widget = None
        self.createUI()
        self.templates_widget.set_path(path)

        self.hide_button.clicked.connect(self.close)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(u'Add asset: {}'.format(path))
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self.templates_widget.templateCreated.connect(self.popup)

    @QtCore.Slot(unicode)
    def popup(self, v):
        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Success')
        mbox.setText(u'Successully added asset "{}" to {}'.format(v, self.templates_widget.path()))
        mbox.exec_()

    def createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(u'', parent=self)
        label = QtWidgets.QLabel()
        pixmap = ImageCache.get_rsc_pixmap(
            u'assets', common.SECONDARY_BACKGROUND, 32.0)
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
        o = 6
        rect = self.rect().marginsRemoved(QtCore.QMargins(o,o,o,o))
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.BACKGROUND)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawRoundedRect(rect, o, o)
        painter.end()

    def sizeHint(self):
        return QtCore.QSize(460, 360)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = AddAssetWidget('C:/tmp')
    w.exec_()
