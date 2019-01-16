# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Module defines the QListWidget items used to browse the projects and the files
found by the collector classes.

"""

from PySide2 import QtWidgets


class MetadataExplorer(QtWidgets.QWidget):
    """Custom utility widget to inspect mime data for drop operations."""

    def __init__(self, parent=None):
        super(MetadataExplorer, self).__init__(parent=parent)
        self.label = None
        self._createUI()
        self.setAcceptDrops(True)
        self.setWindowTitle('MetadataExplorer')

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.label = QtWidgets.QTextEdit()
        self.label.dragEnterEvent = self.dragEnterEvent
        self.label.dropEvent = self.dropEvent
        self.layout().addWidget(self.label, 1)
        self.setMinimumWidth(500)
        self.setMinimumHeight(800)

    def unpack_mime_data(self, mime):
        """Draws the mime data."""
        self.label.clear()
        for mimetype in mime.formats():
            if not mimetype:
                continue
            byte_array = mime.data(mimetype)
            # mimetype = mimetype.encode('utf-8', 'ignore')

            # FORMAT
            self.label.setText(
                u'{}\n\n\n\n{}'.format(self.label.toPlainText(), mimetype)
            )
            try:
                # Data
                self.label.setText(
                    u'{}\n{}'.format(self.label.toPlainText(), byte_array)
                )
            except:
                # Data
                self.label.setText(
                    u'{}\n{}'.format(self.label.toPlainText(), '<Unable to display>')
                )

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        event.accept()
        self.unpack_mime_data(event.mimeData())

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = MetadataExplorer()
    widget.show()
    app.exec_()
