"""Preferences"""


from PySide2 import QtCore, QtGui, QtWidgets
import gwbrowser.common as common


class SectionSwitcherWidget(QtWidgets.QListWidget):
    """Widget responsible for selecting the preferences sections."""
    sections = (
        {'name': u'servers settings', 'description': 'Server preferences'},
        {'name': u'options', 'description': 'Various application options'},
    )

    def __init__(self, parent=None):
        super(SectionSwitcherWidget, self).__init__(parent=parent)

        for s in self.sections:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, s['name'].title())
            item.setData(common.DescriptionRole, s[u'description'])
            item.setData(QtCore.Qt.StatusTipRole, s['name'].title())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                common.WIDTH, common.INLINE_ICON_SIZE))
            self.addItem(item)

    def sizeHint(self):
        return QtCore.QSize(200, 640)


class SectionsWidget(QtWidgets.QStackedWidget):

    def __init__(self, parent=None):
        super(SectionsWidget, self).__init__(parent=parent)



class PreferencesWidget(QtWidgets.QWidget):
    """The main preferences widget."""

    def __init__(self, parent=None):
        super(PreferencesWidget, self).__init__(parent=parent)
        self.setWindowTitle('GWBrowser Preferences')

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentMargins(o,o,o,o)


    def _connectSignals(self):
        pass



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = SectionsWidget()
    widget.show()
    app.exec_()
