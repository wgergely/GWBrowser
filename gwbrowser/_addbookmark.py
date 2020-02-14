# -*- coding: utf-8 -*-
"""
"""
import re
import sys
import zipfile

from PySide2 import QtCore, QtWidgets, QtGui

import gwbrowser.common as common
import gwbrowser.common_ui as common_ui
from gwbrowser.gwscandir import scandir as scandir_it
from gwbrowser.imagecache import ImageCache
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.addfilewidget import NameBase


BUTTON_SIZE = 20
ROW_HEIGHT = 28


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
        menu_set[u'Import a new {} folder template...'.format(parent.mode())] = {
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


class TemplateListDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(TemplateListDelegate, self).__init__(parent=parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent=parent)
        editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        editor.setStyleSheet(u'padding: 0px; margin: 0px; border-radius: 0px;')
        validator = QtGui.QRegExpValidator(parent=editor)
        validator.setRegExp(QtCore.QRegExp(ur'[\_\-a-zA-z0-9]+'))
        editor.setValidator(validator)
        return editor


class TemplateListWidget(QtWidgets.QListWidget):
    ROW_SIZE = 28

    def __init__(self, mode, parent=None):
        super(TemplateListWidget, self).__init__(parent=parent)
        self._mode = mode
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed |
            QtWidgets.QAbstractItemView.SelectedClicked
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum,

        )
        self.model().dataChanged.connect(self.dataChanged)
        self.setItemDelegate(TemplateListDelegate(parent=self))
        self.setStyleSheet(u'background-color: rgba({})'.format(common.rgb(common.BACKGROUND)))

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


class TemplatesWidget(QtWidgets.QWidget):
    templateCreated = QtCore.Signal(unicode)
    ROW_SIZE = 24

    def __init__(self, mode, parent=None):
        super(TemplatesWidget, self).__init__(parent=parent)
        self._path = None
        self._mode = mode
        self.template_list_widget = None
        self.template_contents_widget = None
        self.add_button = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred,
        )
        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_in = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setDuration(500)

        self.fade_out = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.setDuration(200)
        self.fade_out.finished.connect(self.hide)

        self.setWindowTitle(u'Template Browser')

        self._createUI()
        self._connectSignals()

    def showEvent(self, event):
        self.fade_in.start()

    def mode(self):
        return self._mode

    def path(self):
        return self._path

    def set_path(self, val):
        self._path = val

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.INDICATOR_WIDTH * 2
        self.layout().setContentsMargins(0, o, 0, o)
        self.layout().setSpacing(o)
        # Name
        label = common_ui.PaintedLabel(
            u'Add {}'.format(self.mode()),
            color=common.TEXT,
            size=common.MEDIUM_FONT_SIZE + 2.0
        )
        self.layout().addWidget(label)
        row = common_ui.add_row(None, height=ROW_HEIGHT, padding=None, parent=self)
        row.layout().setContentsMargins(0,0,0,0)
        row.layout().setSpacing(0)

        # Label
        label = common_ui.PaintedLabel(
            u'Select {} folder template'.format(self.mode()),
            color=common.SECONDARY_TEXT,
            size=common.MEDIUM_FONT_SIZE
        )
        self.layout().addSpacing(common.INDICATOR_WIDTH)
        self.layout().addWidget(label)

        self.name_widget = NameBase(parent=self)
        self.name_widget.set_transparent()
        self.name_widget.setFont(common.PrimaryFont)
        self.name_widget.setPlaceholderText(u'Enter name...')
        regex = QtCore.QRegExp(ur'[a-zA-Z0-9\_\-]+')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.name_widget.setValidator(validator)
        self.add_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            BUTTON_SIZE,
            description=u'Add new {}'.format(self.mode().title()),
            parent=row
        )
        row.layout().addWidget(self.add_button, 0)
        row.layout().addWidget(self.name_widget, 1)

        # Template Header
        row = common_ui.add_row(None, height=None, padding=None, parent=self)
        row.layout().setContentsMargins(0,0,0,0)
        row.layout().setSpacing(0)
        splitter = QtWidgets.QSplitter(parent=self)
        splitter.setOrientation(QtCore.Qt.Vertical)
        splitter.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum,
        )
        splitter.setMaximumHeight(200)
        self.template_list_widget = TemplateListWidget(self.mode(), parent=self)
        self.template_list_widget.setMinimumHeight(80)
        self.template_list_widget.setMaximumHeight(160)
        self.template_contents_widget = QtWidgets.QListWidget(parent=self)
        splitter.addWidget(self.template_list_widget)
        splitter.addWidget(self.template_contents_widget)
        splitter.setStretchFactor(0, 0.5)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([80,120])
        row.layout().addWidget(splitter, 1)

    def _connectSignals(self):
        self.template_list_widget.selectionModel().selectionChanged.connect(self.itemActivated)
        self.add_button.clicked.connect(self.create_template)
        self.name_widget.returnPressed.connect(self.create_template)

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

        model = self.template_list_widget.selectionModel()
        if not model.hasSelection():
            mbox.setText(
                u'Must select a {} folder template before adding'.format(self.mode()))
            return mbox.exec_()

        index = model.selectedIndexes()[0]
        if not index.isValid():
            return

        source = index.data(QtCore.Qt.UserRole + 1)
        try:
            with zipfile.ZipFile(source, 'r', zipfile.ZIP_DEFLATED) as f:
                f.extractall(file_info.absoluteFilePath(), members=None, pwd=None)
            # common.reveal(file_info.filePath())
            self.templateCreated.emit(self.name_widget.text())
        except Exception as err:
            mbox.setText(u'An error occured when creating the {}'.format(self.mode()))
            mbox.setInformativeText('{}'.format(err))
            return mbox.exec_()
        finally:
            self.name_widget.setText(u'')

    @QtCore.Slot()
    def add_new_template(self):
        """Prompts the user to pick a new `*.zip` file containing a template
        directory structure.

        The template is copied to ``[appdata]/[product]/[mode]_templates/*.zip``
        folder.

        """
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilters([u'*.zip', ])
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(QtWidgets.QFileDialog.Accept, u'Select {} folder template'.format(self.mode().title()))
        dialog.setWindowTitle(u'Select a zip file containing the {m} folder hierarchy'.format(m=self.mode().lower()))
        if not dialog.exec_():
            return

        templates_dir = self.template_list_widget.templates_dir_path()
        # Let's iterate over the selected files
        for source in dialog.selectedFiles():
            file_info = QtCore.QFileInfo(source)
            destination = u'{}/{}'.format(templates_dir, file_info.fileName())
            res = QtCore.QFile.copy(source, destination)

            # If copied successfully, let's reload the ``TemplateListWidget``
            # contents.
            if res:
                self.template_list_widget.load_templates()

    @QtCore.Slot()
    def itemActivated(self, selectionList):
        """Slot called when a template was selected by the user.

        It will load and display the contents of the zip file in the
        `template_contents_widget`.

        Args:
            selectionList (QItemSelection): A QItemSelection instance of QModelIndexes.

        """
        self.template_contents_widget.clear()
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
            self.template_contents_widget.addItem(item)


class ServerEditor(QtWidgets.QWidget):
    serverAdded = QtCore.Signal(unicode)
    serverRemoved = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ServerEditor, self).__init__(parent=parent)
        self._rows = []
        self.add_server_button = None

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_in = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setDuration(500)

        self.fade_out = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.setDuration(200)
        self.fade_out.finished.connect(self.hide)

        self.createUI()
        self.add_rows()

    def showEvent(self, event):
        self.fade_in.start()

    def createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().addSpacing(common.INDICATOR_WIDTH)

        row = common_ui.add_row(None, height=ROW_HEIGHT, padding=0, parent=self)
        self.add_server_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            BUTTON_SIZE,
            description=u'Add a new server',
            parent=row
        )
        self.add_server_label = QtWidgets.QLineEdit(parent=self)
        self.add_server_label.setPlaceholderText(u'Path to the server, eg. //server/jobs')
        self.add_server_label.returnPressed.connect(self.add_server)
        self.add_server_button.clicked.connect(self.add_server)

        row.layout().addWidget(self.add_server_button)
        row.layout().addWidget(self.add_server_label, 1)

    @QtCore.Slot()
    def add_server(self):
        label = self.add_server_label
        if not label.text():
            return
        cservers = [f.findChild(QtWidgets.QLineEdit).text().lower() for f in self._rows]
        exists = label.text().lower() in cservers

        file_info = QtCore.QFileInfo(label.text())
        if exists or not file_info.exists():
            color = common.REMOVE
            label.setStyleSheet(
                u'color: rgba({})'.format(common.rgb(color)))
            return

        server = file_info.absoluteFilePath()
        label.setText(u'')
        color = common.ADD
        label = self.add_row(server, insert=True)
        label.setReadOnly(True)
        label.setText(server)

        # Notify the main widget that the UI has been updated
        self.serverAdded.emit(server)
        return


    def add_row(self, server, insert=False):
        """"""
        @QtCore.Slot()
        def _remove_server():
            if row in self._rows:
                self._rows.remove(row)
            row.deleteLater()
            self.update()

        if insert:
            # id 1 might be the QGraphicsOpacityEffect?
            row = common_ui.add_row(None, height=ROW_HEIGHT, padding=0, parent=None)
            self.layout().insertWidget(2, row)
        else:
            row = common_ui.add_row(None, height=ROW_HEIGHT, padding=0, parent=self)

        if row not in self._rows:
            if insert:
                self._rows.insert(0, row)
            else:
                self._rows.append(row)

        label = QtWidgets.QLineEdit(parent=self)
        label.setText(server)
        label.setReadOnly(True)
        label.setStyleSheet(
            u'background-color: rgba(0,0,0,20);color: rgba(255,255,255,100);')
        button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            BUTTON_SIZE,
            description=u'Remove this server',
            parent=self
        )
        button.clicked.connect(_remove_server)
        button.clicked.connect(lambda: self.serverRemoved.emit(label.text()))
        row.layout().addWidget(button)
        row.layout().addWidget(label)

        return label


    def add_rows(self):
        for server in self.parent().get_saved_servers():
            self.add_row(server=server)


class JobEditor(QtWidgets.QGroupBox):
    def __init__(self, parent=None):
        super(JobEditor, self).__init__(parent=parent)


class BookmarksWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self._path = None
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.setStyleSheet(u'background-color: rgba({})'.format(common.rgb(common.BACKGROUND)))

    @QtCore.Slot()
    def add_bookmark_items(self, bookmarks):
        """Resets and populates the `BookmarksWidget` with QWidgetItems.

        Args:
            bookmarks (tuple): A tuple of file paths to add.

        """
        self.clear()

        if not bookmarks:
            return

        size = QtCore.QSize(1, ROW_HEIGHT)
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSizeF(font.pointSizeF() + 1.0)

        for bookmark in bookmarks:
            file_info = QtCore.QFileInfo(bookmark)
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, file_info.fileName().upper())
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.UserRole, file_info.filePath())
            item.setData(QtCore.Qt.FontRole, font)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.addItem(item)


class AddBookmarksWidget(QtWidgets.QWidget):
    BOOKMARK_KEY = u'bookmarks'
    SERVER_KEY = u'servers'

    def __init__(self, parent=None):
        super(AddBookmarksWidget, self).__init__(parent=parent)
        self._settings = self._init_settings()
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred,
        )
        self._createUI()
        self.init_server_combobox()

    def _createUI(self):
        @QtCore.Slot()
        def toggle_server_editor():
            is_hidden = self.server_editor.isHidden()
            if is_hidden:
                self.server_editor.setHidden(False)
                if not self.templates_widget.isHidden():
                    self.add_template_button.clicked.emit()
                return

            self.server_editor.fade_out.start()
            self.init_server_combobox()

        @QtCore.Slot()
        def reveal_job():
            idx = self.job_combobox.currentIndex()
            if idx < 0:
                return
            _data = self.job_combobox.itemData(
                idx, role=QtCore.Qt.UserRole
            )
            common.reveal(_data)

        @QtCore.Slot()
        def reveal_server():
            idx = self.server_combobox.currentIndex()
            if idx < 0:
                return
            _data = self.server_combobox.itemData(
                idx, role=QtCore.Qt.UserRole
            )
            common.reveal(_data)

        @QtCore.Slot()
        def toggle_template_editor():
            is_hidden = self.templates_widget.isHidden()
            if is_hidden:
                self.templates_widget.setHidden(False)

                if not self.server_editor.isHidden():
                    self.edit_servers_button.clicked.emit()
                return

            self.templates_widget.fade_out.start()
            self.init_job_combobox(self.server_combobox.currentIndex())

        @QtCore.Slot()
        def job(s):
            # Re-populate the
            server_idx = self.server_combobox.currentIndex()
            self.init_job_combobox(server_idx)
            # Find and select the newly added template
            for n in xrange(self.job_combobox.count()):
                d = self.job_combobox.itemData(n, role=QtCore.Qt.DisplayRole)
                if s.lower().strip() == d.lower().strip():
                    self.job_combobox.setCurrentIndex(n)
                    return


        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.INDICATOR_WIDTH * 2
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(o, o, o, o)

        # Server row
        # Label
        label = common_ui.PaintedLabel(u'Servers', size=common.MEDIUM_FONT_SIZE + 2.0)
        self.layout().addWidget(label)

        row = QtWidgets.QGroupBox(parent=self)
        QtWidgets.QVBoxLayout(row)
        self.layout().addWidget(row)

        self.edit_servers_button = common_ui.ClickableIconButton(
            u'add',
            (common.SECONDARY_TEXT, common.SECONDARY_TEXT),
            BUTTON_SIZE,
            description=u'Show the job in the explorer',
            parent=row
        )
        self.reveal_server_button = common_ui.ClickableIconButton(
            u'folder',
            (common.SECONDARY_TEXT, common.SECONDARY_TEXT),
            BUTTON_SIZE,
            description=u'Show the job in the explorer',
            parent=row
        )
        self.server_combobox = QtWidgets.QComboBox(parent=self)
        self.server_combobox.setView(QtWidgets.QListView(parent=self.server_combobox))
        self.server_combobox.setStyleSheet(u'background-color: transparent;')
        self.server_combobox.setDuplicatesEnabled(False)
        self.server_combobox.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.server_combobox.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        _row = common_ui.add_row(None, padding=0, height=ROW_HEIGHT, parent=row)
        _row.layout().addWidget(self.edit_servers_button, 0)
        _row.layout().addWidget(self.server_combobox, 1)
        _row.layout().addWidget(self.reveal_server_button, 0)

        # Server Editor row
        self.server_editor = ServerEditor(parent=self)
        self.server_editor.setHidden(True)
        row.layout().addWidget(self.server_editor)

        # Select Job row
        # Label
        label = common_ui.PaintedLabel(u'Jobs', size=common.MEDIUM_FONT_SIZE + 2.0)
        self.layout().addWidget(label)

        row = QtWidgets.QGroupBox(parent=self)
        QtWidgets.QVBoxLayout(row)
        self.layout().addWidget(row)

        self.job_combobox = QtWidgets.QComboBox(parent=self)
        self.job_combobox.setView(QtWidgets.QListView(parent=self.job_combobox))
        self.job_combobox.setStyleSheet(u'background-color: transparent;')
        self.job_combobox.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.job_combobox.setDuplicatesEnabled(False)
        self.job_combobox.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.add_template_button = common_ui.ClickableIconButton(
            u'add',
            (common.SECONDARY_TEXT, common.SECONDARY_TEXT),
            BUTTON_SIZE,
            description=u'Add a new job to the current server',
            parent=row
        )
        self.reveal_job_button = common_ui.ClickableIconButton(
            u'folder',
            (common.SECONDARY_TEXT, common.SECONDARY_TEXT),
            BUTTON_SIZE,
            description=u'Show the job in the explorer',
            parent=row
        )
        _row = common_ui.add_row(None, padding=0,height=ROW_HEIGHT, parent=row)
        _row.layout().addWidget(self.add_template_button, 0)
        _row.layout().addWidget(self.job_combobox, 1)
        _row.layout().addWidget(self.reveal_job_button, 0)

        self.templates_widget = TemplatesWidget(u'job', parent=self)
        self.templates_widget.setHidden(True)
        self.bookmark_list = BookmarksWidget(parent=self)
        row.layout().addWidget(self.templates_widget)

        # Bookmarks
        # Label
        label = common_ui.PaintedLabel(u'Bookmarks', size=common.MEDIUM_FONT_SIZE + 2.0)
        self.layout().addWidget(label)

        row = QtWidgets.QGroupBox(parent=self)
        QtWidgets.QVBoxLayout(row)

        row.layout().addWidget(self.bookmark_list)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum,

        )
        self.layout().addWidget(row)
        self.layout().addStretch(1)

        # Connections

        # Save server to config file and update UI
        self.server_editor.serverAdded.connect(self.add_server)
        self.server_editor.serverAdded.connect(self.init_server_combobox)
        self.server_editor.serverRemoved.connect(self.remove_server)
        self.server_editor.serverRemoved.connect(self.init_server_combobox)

        self.edit_servers_button.clicked.connect(toggle_server_editor)
        self.reveal_server_button.clicked.connect(reveal_server)
        self.reveal_job_button.clicked.connect(reveal_job)
        self.add_template_button.clicked.connect(toggle_template_editor)
        self.server_combobox.currentIndexChanged.connect(
            self.init_job_combobox)
        self.server_combobox.currentIndexChanged.connect(
            lambda idx: self.templates_widget.set_path(self.server_combobox.itemData(idx, role=QtCore.Qt.UserRole))
            )
        self.server_combobox.currentIndexChanged.connect(
            lambda idx: self.templates_widget.update)

        # Hide jobs
        self.templates_widget.templateCreated.connect(toggle_template_editor)
        self.templates_widget.templateCreated.connect(job)
        self.job_combobox.currentIndexChanged.connect(
            self.init_bookmark_list)

    def _init_settings(self):
        p = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        p = u'{}/{}/settings.ini'.format(p, common.PRODUCT)
        if not QtCore.QFileInfo(p).dir().mkpath(u'.'):
            raise RuntimeError(u'Failed to create "settings.ini"')
        return QtCore.QSettings(p,QtCore.QSettings.IniFormat, parent=self)

    @staticmethod
    def key(*args):
        def r(s): return re.sub(ur'[\\]+', u'/',
                                s, flags=re.UNICODE | re.IGNORECASE)
        k = u'/'.join([r(f).rstrip(u'/') for f in args]).lower().rstrip(u'/')
        return k

    def get_saved_servers(self):
        def r(s):
            return re.sub(
                ur'[\\]', u'/', s, flags=re.UNICODE | re.IGNORECASE)
        val = self._settings.value(self.SERVER_KEY)
        if not val:
            return []
        if isinstance(val, unicode):
            return [val.encode(u'utf-8').lower(), ]
        return sorted([r(f).encode(u'utf-8').lower() for f in val])

    def add_server(self, val):
        s = self.get_saved_servers()
        if val.lower() in s:
            return False
        s.append(val.lower())
        self._settings.setValue(self.SERVER_KEY, list(set(s)))
        return True

    def remove_server(self, val):
        s = self.get_saved_servers()
        if val.lower() in s:
            s.remove(val.lower())
        self._settings.setValue(self.SERVER_KEY, list(set(s)))

    def _get_saved_bookmarks(self):
        val = self._settings.value(self.BOOKMARK_KEY)
        if not val:
            return {}
        return val

    def get_saved_bookmarks(self):
        def r(s): return re.sub(ur'[\\]', u'/',
                                s, flags=re.UNICODE | re.IGNORECASE)
        d = {}
        for k, v in self._get_saved_bookmarks().iteritems():
            d[k.encode(u'utf-8')] = {}
            for _k, _v in v.iteritems():
                d[k.encode(u'utf-8')][_k] = r(_v.encode(u'utf-8'))
        return d

    def save_bookmark(self, server, job, bookmark_folder, add_config_dir=True):
        k = self.key(server, job, bookmark_folder)
        if add_config_dir:
            if not QtCore.QDir(k).mkpath(u'.bookmark'):
                print u'# Error: Could not add "{}/.bookmark"'.format(k)

        d = self._get_saved_bookmarks()
        d[k] = {
            u'server': unicode(server).encode(u'utf-8'),
            u'job':  unicode(job).encode(u'utf-8'),
            u'bookmark_folder':  unicode(bookmark_folder).encode(u'utf-8')
        }
        self._settings.setValue(self.BOOKMARK_KEY, d)

    def remove_saved_bookmark(self, server, job, bookmark_folder):
        k = self.key(server, job, bookmark_folder)
        d = self._get_saved_bookmarks()
        if k in d:
            del d[k]
        self._settings.setValue(self.BOOKMARK_KEY, d)

    @QtCore.Slot()
    def init_server_combobox(self):
        n = 0
        idx = self.server_combobox.currentIndex()

        self.server_combobox.clear()
        for k in self.get_saved_servers():
            pixmap = ImageCache.get_rsc_pixmap(
                u'server', common.TEXT, ROW_HEIGHT)
            pixmap_selected = ImageCache.get_rsc_pixmap(
                u'server', common.ADD, ROW_HEIGHT)
            icon = QtGui.QIcon()
            icon.addPixmap(pixmap, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Selected)

            self.server_combobox.addItem(icon, k.upper(), userData=k)
            item = self.server_combobox.model().item(n)
            self.server_combobox.setItemData(
                n, QtCore.QSize(0, ROW_HEIGHT), QtCore.Qt.SizeHintRole)
            item.setData(common.TEXT, role=QtCore.Qt.TextColorRole)
            item.setData(common.BACKGROUND, role=QtCore.Qt.BackgroundColorRole)

            if not QtCore.QFileInfo(k).exists():
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(common.TEXT_DISABLED,
                             role=QtCore.Qt.TextColorRole)
                item.setData(common.SECONDARY_BACKGROUND,
                             role=QtCore.Qt.BackgroundColorRole)
                # item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                _pixmap = ImageCache.get_rsc_pixmap(
                    u'close', common.REMOVE, ROW_HEIGHT)
                self.server_combobox.setItemIcon(
                    n, QtGui.QIcon(_pixmap))
            n += 1

        if idx >= 0:
            self.server_combobox.setCurrentIndex(idx)
        else:
            for n in xrange(self.server_combobox.count()):
                index = self.server_combobox.model().index(n, 0)
                if index.flags() & QtCore.Qt.ItemIsEnabled:
                    self.server_combobox.setCurrentIndex(n)
                    break

    @QtCore.Slot(int)
    def init_job_combobox(self, idx):
        self.job_combobox.clear()

        if idx < 0:
            return

        server = self.server_combobox.itemData(
            idx, role=QtCore.Qt.UserRole)

        file_info = QtCore.QFileInfo(server)
        if not file_info.exists():
            self.show_warning('"{}" does not exist'.format(server))
            return
        if not file_info.isReadable():
            self.show_warning('"{}" is not readable'.format(server))
            return

        n = 0
        for entry in scandir_it(server):
            if not entry.is_dir():
                continue
            # Let's explicitly check read access by trying to get the
            # files inside the folder
            is_valid = False
            try:
                next(scandir_it(entry.path))
                is_valid = True
            except StopIteration:
                is_valid = True
            except OSError:
                is_valid = False

            file_info = QtCore.QFileInfo(entry.path)
            if file_info.isHidden():
                continue

            pixmap = ImageCache.get_rsc_pixmap(
                u'folder', common.TEXT, ROW_HEIGHT)
            icon = QtGui.QIcon(pixmap)

            self.job_combobox.addItem(
                icon, entry.name.upper(), userData=entry.path.replace(u'\\', '/'))
            item = self.job_combobox.model().item(n)
            self.job_combobox.setItemData(n, QtCore.QSize(
                0, ROW_HEIGHT), QtCore.Qt.SizeHintRole)
            item.setData(common.TEXT, role=QtCore.Qt.TextColorRole)
            item.setData(common.BACKGROUND, role=QtCore.Qt.BackgroundColorRole)

            if not is_valid:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(common.TEXT_DISABLED,
                             role=QtCore.Qt.TextColorRole)
                item.setData(common.SECONDARY_BACKGROUND,
                             role=QtCore.Qt.BackgroundColorRole)
                # item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                _pixmap = ImageCache.get_rsc_pixmap(
                    u'close', common.REMOVE, ROW_HEIGHT)
                self.job_combobox.setItemIcon(n, QtGui.QIcon(_pixmap))
            n += 1

    @QtCore.Slot(int)
    def init_bookmark_list(self, idx):
        path = self.job_combobox.itemData(idx, role=QtCore.Qt.UserRole)

        for entry in scandir_it(path):
            if not entry.is_dir():
                continue
            print entry
        # self.bookmark_list.add_bookmark_items(bookmarks)

    def show_warning(self, text):
        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Warning')
        mbox.setIcon(QtWidgets.QMessageBox.Warning)
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
        mbox.setText(text)
        mbox.exec_()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    widget = QtWidgets.QScrollArea()
    widget.setWidgetResizable(True)
    widget.setWidget(AddBookmarksWidget(parent=widget))
    # widget =
    widget.show()
    app.exec_()
