from PySide2 import QtWidgets
from browser.bookmarkswidget import BookmarksWidget
from browser.assetwidget import AssetWidget
from browser.fileswidget import FilesWidget

app = QtWidgets.QApplication([])

b = BookmarksWidget()
b.setFixedWidth(500)
b.show()
b.move(50, 50)

a = AssetWidget()
a.setFixedWidth(500)
a.show()
a.move(600, 50)

f = FilesWidget()
f.setFixedWidth(500)
f.show()
f.move(1150, 50)

b.model().sourceModel().modelReset.connect(
    lambda: a.model().sourceModel().set_active(b.model().sourceModel().active_index()))
b.model().sourceModel().modelReset.connect(
    a.model().sourceModel().__resetdata__)

b.model().sourceModel().activeChanged.connect(
    a.model().sourceModel().set_active)
b.model().sourceModel().activeChanged.connect(
    lambda x: a.model().sourceModel().__resetdata__())


a.model().sourceModel().modelReset.connect(
    lambda: f.model().sourceModel().set_active(a.model().sourceModel().active_index()))
a.model().sourceModel().modelReset.connect(
    f.model().sourceModel().__resetdata__)

a.model().sourceModel().activeChanged.connect(
    f.model().sourceModel().set_active)
a.model().sourceModel().activeChanged.connect(
    lambda x: f.model().sourceModel().__resetdata__())

a.model().sourceModel().activeChanged.connect(
    lambda: f.model().sourceModel().set_data_key(None))
a.model().sourceModel().activeChanged.connect(
    lambda: f.model().sourceModel().set_data_type(None))

# def _debug(model):
#     print model
#     data = model.model_data()
#     print len(data)
#     print a.model().sourceModel().active_index()
#
# a.model().sourceModel().modelReset.connect(lambda: _debug(f.model().sourceModel()))


app.processEvents()
b.model().sourceModel().modelDataResetRequested.emit()

app.exec_()
