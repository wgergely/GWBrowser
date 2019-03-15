from PySide2 import QtWidgets
from browser.bookmarkswidget import BookmarksWidget
from browser.assetwidget import AssetWidget

app = QtWidgets.QApplication([])
b = BookmarksWidget()
b.setFixedWidth(500)
b.show()
b.move(50, 50)

a = AssetWidget()
a.setFixedWidth(500)
a.show()
a.move(600, 50)

b.model().sourceModel().modelReset.connect(
    lambda: a.model().sourceModel().set_active(b.model().sourceModel().active_index()))
b.model().sourceModel().modelReset.connect(
    a.model().sourceModel().__resetdata__)

b.model().sourceModel().activeChanged.connect(
    a.model().sourceModel().set_active)
b.model().sourceModel().activeChanged.connect(
    lambda x: a.model().sourceModel().__resetdata__())


app.processEvents()
b.model().sourceModel().modelDataResetRequested.emit()

app.exec_()
