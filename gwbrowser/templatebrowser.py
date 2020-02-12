# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets, QtGui
import zipfile
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
import gwbrowser.common as common
import gwbrowser.common_ui as common_ui
from gwbrowser.imagecache import ImageCache
from gwbrowser.addfilewidget import NameBase


class TemplateContextMenu(BaseContextMenu):

    def __init__(self, index, parent=None):
        super(TemplateContextMenu, self).__init__(index, parent=parent)
        self.add_refresh_menu()
        if not index:
            return
        self.add_new_template_menu()

        self.add_separator()
        self.add_remove_menu()

    @contextmenu
    def add_remove_menu(self, menu_set):
        pixmap = ImageCache.get_rsc_pixmap(
            u'close', common.REMOVE, common.INLINE_ICON_SIZE)

        @QtCore.Slot()
        def delete():
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setWindowTitle(u'Delete template')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            mbox.setDefaultButton(QtWidgets.QMessageBox.No)
            mbox.setText(u'Are you sure you want to delete this template?')
            res = mbox.exec_()

            if res == QtWidgets.QMessageBox.No:
                return
            if QtCore.QFile.remove(self.index.data(QtCore.Qt.UserRole + 1)):
                self.parent().load_templates()

        menu_set[u'Delete'] = {
            u'action': delete,
            u'icon': pixmap
        }

        return menu_set

    @contextmenu
    def add_refresh_menu(self, menu_set):
        pixmap = ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        add_pixmap = ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.INLINE_ICON_SIZE)

        parent = self.parent().parent().parent().parent()
        menu_set[u'Import a new {} template...'.format(parent.mode())] = {
            u'action': parent.add_new_template,
            u'icon': add_pixmap
        }

        menu_set[u'Refresh'] = {
            u'action': self.parent().load_templates,
            u'icon': pixmap
        }
        return menu_set

    @contextmenu
    def add_new_template_menu(self, menu_set):
        pixmap = ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)

        menu_set[u'Show in file explorer...'] = {
            u'icon': pixmap,
            u'action': lambda: common.reveal(self.index.data(QtCore.Qt.UserRole + 1)),
        }
        return menu_set


class ZipListDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ZipListDelegate, self).__init__(parent=parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent=parent)
        editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        editor.setStyleSheet(u'padding: 0px; margin: 0px; border-radius: 0px;')
        validator = QtGui.QRegExpValidator(parent=editor)
        validator.setRegExp(QtCore.QRegExp(ur'[\_\-a-zA-z0-9]+'))
        editor.setValidator(validator)
        return editor


class ZipListWidget(QtWidgets.QListWidget):
    ROW_SIZE = 28

    def __init__(self, mode, parent=None):
        super(ZipListWidget, self).__init__(parent=parent)
        self._mode = mode
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed |
            QtWidgets.QAbstractItemView.SelectedClicked
        )
        self.model().dataChanged.connect(self.dataChanged)
        self.setItemDelegate(ZipListDelegate(parent=self))

        path = self.templates_dir_path()
        _dir = QtCore.QDir(path)
        if not _dir.exists():
            _dir.mkpath(u'.')

    def mode(self):
        return self._mode

    @QtCore.Slot()
    def dataChanged(self, index, bottomRight, vector, roles=None):
        oldpath = index.data(QtCore.Qt.UserRole + 1)
        oldname = QtCore.QFileInfo(oldpath).baseName()
        name = index.data(QtCore.Qt.DisplayRole)
        name = name.replace(u'.zip', u'')

        newpath = u'{}/{}.zip'.format(
            self.templates_dir_path(),
            name
        )
        if QtCore.QFile.rename(oldpath, newpath):
            self.model().setData(index, name, QtCore.Qt.DisplayRole)
            self.model().setData(index, newpath, QtCore.Qt.UserRole + 1)
        else:
            self.model().setData(index, oldname, QtCore.Qt.DisplayRole)
            self.model().setData(index, oldpath, QtCore.Qt.UserRole + 1)

    def load_templates(self):
        self.clear()
        dir_ = QtCore.QDir(self.templates_dir_path())
        dir_.setNameFilters([u'*.zip', ])

        size = QtCore.QSize(1, self.ROW_SIZE)
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom', common.SECONDARY_BACKGROUND, self.ROW_SIZE)
        icon = QtGui.QIcon(pixmap)

        for f in dir_.entryList():
            if u'zip' not in f.lower():
                continue
            item = QtWidgets.QListWidgetItem(parent=self)
            item.setData(QtCore.Qt.DisplayRole, f.replace(u'.zip', u''))
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)

            path = u'{}/{}'.format(dir_.path(), f)
            with zipfile.ZipFile(path) as zip:
                namelist = [f.strip(u'/') for f in sorted(zip.namelist())]
                item.setData(QtCore.Qt.UserRole, namelist)
                item.setData(QtCore.Qt.UserRole + 1, path)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)

    def templates_dir_path(self):
        path = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        path = u'{}/{}/{}_templates'.format(path, common.PRODUCT, self.mode())
        return path

    def showEvent(self, event):
        self.load_templates()

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = TemplateContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()


class TemplatesWidget(QtWidgets.QGroupBox):
    templateCreated = QtCore.Signal()
    ROW_SIZE = 24

    def __init__(self, mode, parent=None):
        super(TemplatesWidget, self).__init__(parent=parent)
        self._path = None
        self._mode = mode
        self.ziplist_widget = None
        self.zipcontents_widget = None
        self.add_button = None

        self.setWindowTitle(u'Template Browser')

        self._createUI()
        self._connectSignals()

    def mode(self):
        return self._mode

    def path(self):
        return self._path

    def set_path(self, val):
        self._path = val

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        # Name
        row = common_ui.add_row(u'{} name'.format(self.mode().title()), padding=None, parent=self)
        self.name_widget = NameBase(parent=self)
        self.name_widget.set_transparent()
        self.name_widget.setFont(common.PrimaryFont)
        self.name_widget.setPlaceholderText('Enter the name here...')
        regex = QtCore.QRegExp(ur'[a-zA-Z0-9\_\-]+')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.name_widget.setValidator(validator)
        row.layout().addWidget(self.name_widget, 1)
        self.add_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            self.ROW_SIZE,
            description=u'Add new {}'.format(self.mode().title()),
            parent=row
        )
        row.layout().addWidget(self.add_button)

        # Template Header
        row = common_ui.add_row(u'Select template', height=None, padding=None, parent=self)
        splitter = QtWidgets.QSplitter(parent=self)
        self.ziplist_widget = ZipListWidget(self.mode(), parent=self)
        self.ziplist_widget.setMinimumHeight(120)
        self.zipcontents_widget = QtWidgets.QListWidget(parent=self)
        splitter.addWidget(self.ziplist_widget)
        splitter.addWidget(self.zipcontents_widget)
        splitter.setSizes([60, 30])

        row.layout().addWidget(splitter, 1)
        self.layout().addStretch(1)

    def _connectSignals(self):
        self.ziplist_widget.selectionModel().selectionChanged.connect(self.itemActivated)
        self.add_button.clicked.connect(self.create_template)

    @QtCore.Slot()
    def create_template(self):
        """Verifies the user choices and expands the selected template to the
        currently set `path`.

        """
        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Error')
        mbox.setIcon(QtWidgets.QMessageBox.Warning)
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
        mbox.setFixedWidth(500)
        mbox.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        if not self.path():
            mbox.setText(
                u'Unable to create {}.'.format(self.mode().lower()))
            mbox.setInformativeText(
                u'The parent path has not yet been set.')
            return mbox.exec_()

        file_info = QtCore.QFileInfo(self.path())
        if not file_info.exists():
            mbox.setText(
                u'Unable to create {}.'.format(self.mode().lower()))
            mbox.setInformativeText(
                u'The root "{}" does not exist.'.format(file_info.filePath()))
            return mbox.exec_()

        if not self.name_widget.text():
            mbox.setText(
                u'Must enter a name before adding an asset.')
            self.name_widget.setFocus()
            return mbox.exec_()

        file_info = file_info = QtCore.QFileInfo(
            u'{}/{}'.format(self.path(), self.name_widget.text()))

        if file_info.exists():
            mbox.setText(
                u'Unable to create {}.'.format(self.mode().lower()))
            mbox.setInformativeText(
                u'"{}" already exists.'.format(self.name_widget.text()))
            return mbox.exec_()

        model = self.ziplist_widget.selectionModel()
        if not model.hasSelection():
            mbox.setText(
                u'Must select a {} template before adding'.format(self.mode()))
            return mbox.exec_()

        index = model.selectedIndexes()[0]
        if not index.isValid():
            return

        source = index.data(QtCore.Qt.UserRole + 1)
        try:
            with zipfile.ZipFile(source, 'r', zipfile.ZIP_DEFLATED) as f:
                f.extractall(file_info.absoluteFilePath(), members=None, pwd=None)
            common.reveal(file_info.filePath())
            self.templateCreated.emit()
        except Exception as err:
            mbox.setText(u'An error occured when creating the {}'.format(self.mode()))
            mbox.setInformativeText('{}'.format(err))
            return mbox.exec_()
        finally:
            self.name_widget.setText(u'')

    @QtCore.Slot()
    def add_new_template(self):
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilters([u'*.zip', ])
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(QtWidgets.QFileDialog.Accept, u'Select {} Template'.format(self.mode().title()))
        dialog.setWindowTitle(u'Select a zip file containing the {m} folder hierarchy'.format(m=self.mode().lower()))
        if not dialog.exec_():
            return

        templates_dir = self.ziplist_widget.templates_dir_path()
        for source in dialog.selectedFiles():
            file_info = QtCore.QFileInfo(source)
            destination = u'{}/{}'.format(templates_dir, file_info.fileName())
            res = QtCore.QFile.copy(source, destination)
            if res:
                self.ziplist_widget.load_templates()

    @QtCore.Slot()
    def itemActivated(self, selectionList):
        self.zipcontents_widget.clear()
        if not selectionList:
            return
        index = selectionList.first().topLeft()
        if not index.isValid():
            return

        size = QtCore.QSize(0, self.ROW_SIZE)
        folder_pixmap = ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        folder_icon = QtGui.QIcon(folder_pixmap)
        file_pixmap = ImageCache.get_rsc_pixmap(
            u'files', common.ADD, common.INLINE_ICON_SIZE)
        file_icon = QtGui.QIcon(file_pixmap)

        for f in index.data(QtCore.Qt.UserRole):
            if QtCore.QFileInfo(f).suffix():
                icon = file_icon
            else:
                icon = folder_icon
            item = QtWidgets.QListWidgetItem(parent=self)
            item.setData(QtCore.Qt.FontRole, common.SecondaryFont)
            item.setData(QtCore.Qt.DisplayRole, f)
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.zipcontents_widget.addItem(item)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = TemplatesWidget(u'job')
    w.set_path(u'C:/tmp')
    w.show()
    app.exec_()
