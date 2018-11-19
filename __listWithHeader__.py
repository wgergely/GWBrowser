# -*- coding: utf-8 -*-
"""
Customized QMenu for displaying context menus based on action-set dictionaries.
"""

# pylint: disable=E1101, C0103, R0913, I1101
from PySide2 import QtWidgets


class ListHeaderWidget(QtWidgets.QWidget):
    """The custom header used for the list widget.

    Continss the file sorting sortingorder, mode filters and info label."""

    def __init__(self, parent=None):
        super(ListHeaderWidget, self).__init__(parent=parent)
        self.sortingorder = None
        self.modewidget = None

        self._createUI()
        self._connectSignals()
        self.sortingorder.addItem('Name')
        self.sortingorder.addItem('Date modified')
        self.sortingorder.addItem('Size')


    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setSpacing(6)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.sortingorder = QtWidgets.QComboBox()
        self.modewidget = ModeWidget()
        self.modewidget.add_modes(['mode1', 'mode2'])

        self.layout().addWidget(self.sortingorder)
        self.layout().addStretch()
        self.layout().addWidget(self.modewidget)

    def _connectSignals(self):
        pass

class ModeWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(ModeWidget,self).__init__(parent=parent)
        self.setSizeAdjustPolicy(QtWidgets.QFontComboBox.AdjustToContents)
        self.setStyleSheet(
            """\
            QComboBox {\
                font-family: "Roboto Black";\
                color: rgb(184, 181, 230);\
                background-color: rgb(104, 101, 170);\
                margin: 3;\
                padding: 3 6;\
                border-width: 1px;\
                border-style: none;\
                border-radius: 4px;\
            }\
            QComboBox:on, QComboBox:hover {\
                color: rgb(230, 230, 230);\
                background-color: rgb(104, 101, 170);\
            }\
            QComboBox::drop-down {\
                background-color: transparent;\
                width: 0px;\
                height: 0px;\
                padding:0px;\
                margin:0px;\
                border-width: 0px;\
                border-style: none;\
                border-radius: 0px;\
            }\
            """

        )
        self._connectSignals()

    def add_modes(self, modes):
        for mode in modes:
            self.addItem(mode)

    def _connectSignals(self):
        pass

class ListWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ListWidget, self).__init__(parent=parent)

        self.header_widget = None
        self.list_widget = None

        self.createUI()
        self._addItems()

    def createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.list_widget = QtWidgets.QListWidget()
        self.header_widget = ListHeaderWidget(parent=self.list_widget.viewport())
        # self.layout().addWidget(self.header_widget)
        self.layout().addWidget(self.list_widget)
        # self.header_widget()
        self.header_widget.show()

    def _addItems(self):
        for n in xrange(10):
            self.addItem(QtWidgets.QListWidgetItem('Item {}'.format(n + 1)))

    def addItem(self, *args, **kwargs):
        self.list_widget.addItem(*args, **kwargs)


app = QtWidgets.QApplication([])
widget = ListWidget()
widget.show()
app.exec_()
