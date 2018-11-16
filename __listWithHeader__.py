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
        self.modefilter = None

        self._createUI()
        self._connectSignals()
        self.sortingorder.addItem('Name')
        self.sortingorder.addItem('Date modified')
        self.sortingorder.addItem('Size')
        self.modefilter.addItem('Layout')
        self.modefilter.addItem('Animation')
        self.modefilter.addItem('Render')


    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setSpacing(6)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.sortingorder = QtWidgets.QComboBox()
        self.modefilter = QtWidgets.QComboBox()

        self.layout().addWidget(self.sortingorder)
        self.layout().addStretch()
        self.layout().addWidget(QtWidgets.QLabel('Filter:'))
        self.layout().addWidget(self.modefilter)

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

        self.header_widget = ListHeaderWidget()
        self.list_widget = QtWidgets.QListWidget()
        self.layout().addWidget(self.header_widget)
        self.layout().addWidget(self.list_widget)
        for item in self.children():
            print item
            break

    def _addItems(self):
        for n in xrange(10):
            self.addItem(QtWidgets.QListWidgetItem('Item {}'.format(n + 1)))

    def addItem(self, *args, **kwargs):
        self.list_widget.addItem(*args, **kwargs)


app = QtWidgets.QApplication([])
widget = ListWidget()
widget.show()


app.exec_()
