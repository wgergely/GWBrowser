from PySide2 import QtWidgets

class ListHeaderWidget(QtWidgets.QWidget):
    def __

class ListWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ListWidget, self).__init__(parent=parent)

        self.header_widget = None
        self.list_widget = None

        self.createUI()
        self._addItems()

    def createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.header_widget = QtWidgets.QLabel('Hello world.')
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
