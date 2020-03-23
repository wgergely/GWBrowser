# -*- coding: utf-8 -*-
"""**managebookmarks.py** defines ``ManageBookmarksWidget`` and the supplemetary
widgets needed to add, create and select **servers**, **jobs** and **bookmark** folders.

These three choices togethermake up a **bookmark** - an entrypoint for Bookmarks
to start browsing the contents of a job.
The path of a bookmark, unsurprisingly, is a composite of the above elements:
*server/job/bookmark folder*. Eg.: **//network_server/my_job/shots.**

"""
import re
import zipfile

from PySide2 import QtCore, QtWidgets, QtGui

import bookmarks.common as common
import bookmarks.common_ui as common_ui
from bookmarks._scandir import scandir as scandir_it
import bookmarks.images as images
from bookmarks.basecontextmenu import BaseContextMenu, contextmenu
import bookmarks.settings as settings


AddMode = 0
RemoveMode = 1


class ComboBox(QtWidgets.QComboBox):
    def __init__(self, warning_string, parent=None):
        super(ComboBox, self).__init__(parent=parent)
        self._warning_string = warning_string
        self.setView(QtWidgets.QListView(parent=self))
        self.setDuplicatesEnabled(False)
        self.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

    def paintEvent(self, event):
        if not self.count():
            painter = QtGui.QPainter()
            painter.begin(self)
            common.draw_aliased_text(
                painter,
                common.font_db.secondary_font(),
                self.rect(),
                self._warning_string,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                common.TEXT_DISABLED
            )
            painter.end()
            return
        super(ComboBox, self).paintEvent(event)


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
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'close', common.REMOVE, common.MARGIN)

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
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.MARGIN)
        add_pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN)

        parent = self.parent().parent().parent().parent()
        k = u'Import a new {} folder template...'.format(parent.mode())
        menu_set[k] = {
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
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN)

        def reveal():
            common.reveal(self.index.data(QtCore.Qt.UserRole + 1))

        menu_set[u'Show in file explorer...'] = {
            u'icon': pixmap,
            u'action': reveal,
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

    def __init__(self, mode, parent=None):
        super(TemplateListWidget, self).__init__(parent=parent)
        self._mode = mode
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed
        )
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.installEventFilter(self)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum,
        )
        self.setItemDelegate(TemplateListDelegate(parent=self))

        path = self.templates_dir_path()
        _dir = QtCore.QDir(path)
        if not _dir.exists():
            _dir.mkpath(u'.')

        self.model().dataChanged.connect(self.dataChanged)

    def eventFilter(self, widget, event):
        if widget is not self:
            return False

        if event.type() is QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)

            painter.setBrush(common.BACKGROUND)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setFont(common.font_db.secondary_font())
            painter.drawRect(self.rect())
            o = common.MEDIUM_FONT_SIZE
            rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
            painter.setPen(QtGui.QColor(255, 255, 255, 50))
            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                u'Available templates (right-click to add a new one)',
                boundingRect=self.rect(),
            )
            painter.end()
            return True

        return False

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

        size = QtCore.QSize(1, common.ROW_HEIGHT * 0.8)
        off_pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon', common.SECONDARY_BACKGROUND, common.ROW_HEIGHT * 0.8)
        on_pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon', common.ADD, common.ROW_HEIGHT * 0.8)
        icon = QtGui.QIcon()
        icon.addPixmap(off_pixmap, QtGui.QIcon.Normal)
        icon.addPixmap(on_pixmap, QtGui.QIcon.Selected)

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

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH * 0.15, common.WIDTH * 0.2)


class TemplatesPreviewWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super(TemplatesPreviewWidget, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Minimum,
        )
        self.installEventFilter(self)

    def eventFilter(self, widget, event):
        if widget is not self:
            return False
        if event.type() is QtCore.QEvent.Paint:
            if self.model().rowCount():
                return False
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(common.SECONDARY_BACKGROUND)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setFont(common.font_db.secondary_font())
            painter.drawRect(self.rect())
            o = common.MEDIUM_FONT_SIZE
            rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
            painter.setPen(QtGui.QColor(255, 255, 255, 50))
            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                u'Template preview',
                boundingRect=self.rect(),
            )
            painter.end()
            return True
        return False

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH * 0.15, common.WIDTH * 0.2)


class TemplatesWidget(QtWidgets.QGroupBox):
    templateCreated = QtCore.Signal(unicode)

    def __init__(self, mode, parent=None):
        super(TemplatesWidget, self).__init__(parent=parent)
        self._path = None
        self._mode = mode
        self.template_list_widget = None
        self.template_contents_widget = None
        self.add_button = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Maximum,
        )

        self.setWindowTitle(u'Template Browser')

        self._create_UI()
        self._connect_signals()

    def mode(self):
        return self._mode

    def path(self):
        return self._path

    def set_path(self, val):
        self._path = val

    def _create_UI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.INDICATOR_WIDTH * 2
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(None, height=common.ROW_HEIGHT * 0.8,
                                padding=None, parent=self)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)

        self.name_widget = common_ui.NameBase(parent=self)
        self.name_widget.setFont(common.font_db.primary_font())
        self.name_widget.setPlaceholderText(
            u'Enter name, eg. NEW_{}_000'.format(self.mode().upper()))
        regex = QtCore.QRegExp(ur'[a-zA-Z0-9\_\-]+')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.name_widget.setValidator(validator)
        self.add_button = common_ui.ClickableIconButton(
            u'CopyAction',
            (common.ADD, common.ADD),
            common.MARGIN * 1.2,
            description=u'Add new {}'.format(self.mode().title()),
            parent=row
        )
        row.layout().addWidget(self.name_widget, 1)
        row.layout().addSpacing(common.MARGIN)
        row.layout().addWidget(self.add_button, 0)

        # Template Header
        row = common_ui.add_row(None, height=None, padding=None, parent=self)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)
        splitter = QtWidgets.QSplitter(parent=self)
        splitter.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum,
        )
        splitter.setMaximumHeight(common.WIDTH * 0.3)
        self.template_list_widget = TemplateListWidget(
            self.mode(), parent=self)
        self.template_contents_widget = TemplatesPreviewWidget(parent=self)
        splitter.addWidget(self.template_list_widget)
        splitter.addWidget(self.template_contents_widget)
        splitter.setSizes([common.WIDTH * 0.12, common.WIDTH * 0.2])
        row.layout().addWidget(splitter, 1)

    def _connect_signals(self):
        self.template_list_widget.selectionModel(
        ).selectionChanged.connect(self.itemActivated)
        self.add_button.clicked.connect(self.create_template)
        self.name_widget.returnPressed.connect(self.create_template)

    @QtCore.Slot()
    def create_template(self):
        """Verifies the user choices and expands the selected template to the
        currently set `path`.

        """
        h = u'Unable to create {}.'.format(self.mode().lower())
        if not self.path():
            common_ui.ErrorBox(
                h, u'Destination has selected!',
                parent=self
            ).exec_()
            return

        file_info = QtCore.QFileInfo(self.path())
        if not file_info.exists():
            common_ui.ErrorBox(
                h, u'Destination folder "{}" does not exist!'.format(
                    file_info.filePath()),
                parent=self
            ).exec_()
            return
        if not file_info.isWritable():
            common_ui.ErrorBox(
                h, u'Destination folder "{}" is not writable!'.format(
                    file_info.filePath()),
                parent=self
            ).exec_()
            return

        if not self.name_widget.text():
            common_ui.ErrorBox(
                h, u'Enter a name and try again.',
                parent=self
            ).exec_()
            return

        file_info = file_info = QtCore.QFileInfo(
            u'{}/{}'.format(self.path(), self.name_widget.text()))

        if file_info.exists():
            common_ui.ErrorBox(
                h, u'"{}" already exists!'.format(self.name_widget.text()),
                parent=self
            ).exec_()
            return

        model = self.template_list_widget.selectionModel()
        if not model.hasSelection():
            common_ui.ErrorBox(
                h, u'Select {} folder template and try again'.format(
                    self.mode()),
                parent=self
            ).exec_()
            return

        index = model.selectedIndexes()[0]
        if not index.isValid():
            return

        source = index.data(QtCore.Qt.UserRole + 1)
        try:
            with zipfile.ZipFile(source, 'r', zipfile.ZIP_DEFLATED) as f:
                f.extractall(file_info.absoluteFilePath(),
                             members=None, pwd=None)
            # common.reveal(file_info.filePath())
            self.templateCreated.emit(self.name_widget.text())
        except Exception as err:
            common_ui.ErrorBox(
                h, u'Error occured creating the {}:\n{}'.format(
                    self.mode(), err),
                parent=self
            ).exec_()
            return
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
        dialog.setLabelText(QtWidgets.QFileDialog.Accept,
                            u'Select {} folder template'.format(self.mode().title()))
        dialog.setWindowTitle(
            u'Select a zip file containing the {m} folder hierarchy'.format(m=self.mode().lower()))
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

        size = QtCore.QSize(0, common.ROW_HEIGHT * 0.8)
        folder_pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN)
        folder_icon = QtGui.QIcon()
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Normal)
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Selected)
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Disabled)

        file_pixmap = images.ImageCache.get_rsc_pixmap(
            u'files', common.ADD, common.MARGIN, opacity=0.5)
        file_icon = QtGui.QIcon()
        file_icon.addPixmap(file_pixmap, QtGui.QIcon.Normal)
        file_icon.addPixmap(file_pixmap, QtGui.QIcon.Selected)
        file_icon.addPixmap(file_pixmap, QtGui.QIcon.Disabled)

        for f in index.data(QtCore.Qt.UserRole):
            if QtCore.QFileInfo(f).suffix():
                icon = file_icon
            else:
                icon = folder_icon
            item = QtWidgets.QListWidgetItem(parent=self)
            item.setData(QtCore.Qt.FontRole, common.font_db.secondary_font())
            item.setData(QtCore.Qt.DisplayRole, f)
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.template_contents_widget.addItem(item)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH * 0.3, common.WIDTH * 0.2)


class ServerEditor(QtWidgets.QWidget):
    serverAdded = QtCore.Signal(unicode)
    serverRemoved = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ServerEditor, self).__init__(parent=parent)
        self._rows = []
        self.add_server_button = None

        self._create_UI()
        self.add_rows()

    def _create_UI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().addSpacing(common.INDICATOR_WIDTH)

        row = common_ui.add_row(None, height=common.ROW_HEIGHT * 0.8,
                                padding=0, parent=self)
        self.add_server_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            common.MARGIN * 1.2,
            description=u'Add a new server',
            parent=row
        )
        self.add_server_lineeditor = QtWidgets.QLineEdit(parent=self)
        self.add_server_lineeditor.setPlaceholderText(
            u'Enter the path to the server (eg. //server/jobs)')
        self.add_server_lineeditor.returnPressed.connect(self.add_server)
        self.add_server_button.clicked.connect(self.add_server)

        row.layout().addWidget(self.add_server_button)
        row.layout().addWidget(self.add_server_lineeditor, 1)

    @QtCore.Slot()
    def add_server(self, allow_invalid=False):
        label = self.add_server_lineeditor
        if not label.text():
            return
        cservers = [f.findChild(QtWidgets.QLineEdit).text().lower()
                    for f in self._rows]
        exists = label.text().lower() in cservers

        file_info = QtCore.QFileInfo(label.text())
        if not allow_invalid and exists or not file_info.exists():
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
            row = common_ui.add_row(
                None, height=common.ROW_HEIGHT * 0.8, padding=0, parent=None)
            self.layout().insertWidget(2, row)
        else:
            row = common_ui.add_row(
                None, height=common.ROW_HEIGHT * 0.8, padding=0, parent=self)

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
            common.MARGIN * 1.2,
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


class BookmarksWidget(QtWidgets.QListWidget):
    bookmarkAdded = QtCore.Signal(tuple)
    bookmarkRemoved = QtCore.Signal(tuple)

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self._path = None
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.itemPressed.connect(self.toggle_state)
        self.installEventFilter(self)

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.Paint:
            if self.count():
                return False
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setFont(common.font_db.secondary_font())
            painter.setBrush(common.ADD)
            painter.setPen(common.TEXT_DISABLED)
            painter.drawText(
                self.rect(),
                QtCore.Qt.AlignCenter,
                'No bookmarks found.'
            )
            painter.end()
            return True
        return False

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def toggle_state(self, item):
        if item.checkState() == QtCore.Qt.Unchecked:
            item.setCheckState(QtCore.Qt.Checked)
            self.bookmarkAdded.emit(item.data(QtCore.Qt.UserRole))
        else:
            item.setCheckState(QtCore.Qt.Unchecked)
            self.bookmarkRemoved.emit(item.data(QtCore.Qt.UserRole))

    @QtCore.Slot()
    def add_bookmark_items(self, bookmarks):
        """Resets and populates the `BookmarksWidget` with QWidgetItems.

        Args:
            bookmarks (tuple): A tuple of file paths to add.

        """
        self.clear()

        if not bookmarks:
            return

        size = QtCore.QSize(1, common.ROW_HEIGHT * 0.8)
        font = common.font_db.primary_font(
            font_size=common.MEDIUM_FONT_SIZE + 1.0)

        for bookmark in bookmarks:
            file_info = QtCore.QFileInfo(bookmark)
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, file_info.fileName().upper())
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.UserRole, file_info.filePath())
            item.setData(QtCore.Qt.FontRole, font)
            item.setFlags(QtCore.Qt.ItemIsEnabled |
                          QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.addItem(item)
        self.fit_height_to_contents()

    def fit_height_to_contents(self):
        options = self.viewOptions()
        height = 0
        for n in xrange(self.count()):
            index = self.model().index(n, 0)
            height += self.itemDelegate().sizeHint(options, index).height()
        self.setFixedHeight(height)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH * 0.125, common.WIDTH * 0.0625)

    def showEvent(self, event):
        bookmarks = settings.local_settings.value(u'bookmarks')
        for n in xrange(self.count()):
            item = self.item(n)
            if item.checkState() == QtCore.Qt.Checked:
                if item.data(QtCore.Qt.UserRole).lower() not in bookmarks:
                    self.toggle_state(item)


class ManageBookmarksWidget(QtWidgets.QWidget):
    BOOKMARK_KEY = u'bookmarks'
    SERVER_KEY = u'servers'

    progressUpdate = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ManageBookmarksWidget, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setWindowFlags(QtCore.Qt.Widget)

        self.init_timer = QtCore.QTimer(parent=self)
        self.init_timer.setInterval(1000)
        self.init_timer.setSingleShot(True)
        self.init_timer.timeout.connect(self.init_server_combobox)

        self._create_UI()

        self.progressUpdate.connect(self.progress_widget.setText)
        self.progressUpdate.connect(self.progress_widget.repaint)

    def _create_UI(self):
        @QtCore.Slot()
        def toggle_server_editor():
            is_hidden = self.server_editor.isHidden()
            if is_hidden:
                self.server_editor.setHidden(False)
                if not self.templates_widget.isHidden():
                    self.add_template_button.clicked.emit()
                return

            self.server_editor.hide()
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
            if self.server_combobox.currentIndex() < 0:
                return
            is_hidden = self.templates_widget.isHidden()
            if is_hidden:
                self.templates_widget.setHidden(False)

                if not self.server_editor.isHidden():
                    self.edit_servers_button.clicked.emit()
                return

            self.templates_widget.hide()
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

        @QtCore.Slot()
        def add_new_bookmark():
            idx = self.job_combobox.currentIndex()
            if idx < 0:
                return
            path = self.job_combobox.itemData(idx, role=QtCore.Qt.UserRole)

            dialog = QtWidgets.QFileDialog(parent=self)
            dialog.setDirectory(path)
            dialog.setFileMode(QtWidgets.QFileDialog.Directory)
            dialog.setViewMode(QtWidgets.QFileDialog.List)
            dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
            dialog.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
            dialog.setLabelText(QtWidgets.QFileDialog.Accept,
                                u'Mark folder as bookmark')
            dialog.setWindowTitle(u'Add a new bookmark')
            if not dialog.exec_():
                self.init_bookmark_list(idx)
                return

            for source in dialog.selectedFiles():
                if path.lower() not in source.lower():
                    return
                QtCore.QDir(source).mkdir(u'.bookmark')
                self.init_bookmark_list(idx)

        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setSpacing(common.INDICATOR_WIDTH)
        self.layout().setContentsMargins(o, o, o, o)

        row = common_ui.add_row(u'', parent=self)
        label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'bookmark', common.SECONDARY_BACKGROUND, common.ROW_HEIGHT)
        label.setPixmap(pixmap)
        row.layout().addWidget(label, 0)
        label = common_ui.PaintedLabel(
            u' Manage Bookmarks', size=common.LARGE_FONT_SIZE, parent=self)
        row.layout().addWidget(label, 0)
        row.layout().addStretch(1)
        self.layout().addSpacing(common.MARGIN)

        self.hide_button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            common.MARGIN * 1.2,
            description=u'Hide',
            parent=row
        )
        row.layout().addWidget(self.hide_button, 0)

        grp = QtWidgets.QGroupBox(parent=self)
        QtWidgets.QVBoxLayout(grp)
        self.layout().addWidget(grp, 0)

        label = QtWidgets.QLabel(parent=self)

        o = common.MEDIUM_FONT_SIZE
        label.setContentsMargins(o, o, o, o)

        s = u'Click the plus icons to add a server, job or a bookmark \
(to toggle a bookmark simply click it).'.format(
            common.PRODUCT)

        label.setText(s)
        label.setStyleSheet(u'color: rgba({});'.format(
            common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        grp.layout().addWidget(label, 1)

        self.progress_widget = QtWidgets.QLabel(parent=self)
        self.progress_widget.setMaximumWidth(common.WIDTH * 0.5)
        # self.progress_widget.setTextFormat(QtCore.Qt.RichText)
        self.progress_widget.setAlignment(QtCore.Qt.AlignLeft)
        self.progress_widget.setTextInteractionFlags(
            QtCore.Qt.NoTextInteraction)
        self.progress_widget.setStyleSheet(
            u'color: rgba({}); font-size: {}px;'.format(
                common.rgb(common.FAVOURITE),
                common.SMALL_FONT_SIZE
            ))
        grp.layout().addWidget(self.progress_widget, 0)
        grp.layout().addSpacing(common.INDICATOR_WIDTH * 2)

        # Label
        row = QtWidgets.QGroupBox(parent=self)
        QtWidgets.QVBoxLayout(row)
        grp.layout().addWidget(row, 0)

        self.edit_servers_button = common_ui.ClickableIconButton(
            u'CopyAction',
            (common.SEPARATOR, common.SEPARATOR),
            common.MARGIN * 1.2,
            description=u'Show the job in the explorer',
            parent=row
        )
        self.reveal_server_button = common_ui.ClickableIconButton(
            u'active',
            (common.SEPARATOR, common.SEPARATOR),
            common.MARGIN * 1.2,
            description=u'Show the job in the explorer',
            parent=row
        )
        self.server_combobox = ComboBox(
            u'No servers',
            parent=self)

        _row = common_ui.add_row(
            None, padding=0, height=common.ROW_HEIGHT * 0.8, parent=row)
        label = common_ui.PaintedLabel(
            u'Servers:', size=common.MEDIUM_FONT_SIZE, color=common.SECONDARY_TEXT)
        label.setFixedWidth(common.MARGIN * 4.5)
        _row.layout().addWidget(self.edit_servers_button, 0)
        _row.layout().addSpacing(common.INDICATOR_WIDTH)
        _row.layout().addWidget(label)
        _row.layout().addWidget(self.server_combobox, 1)
        _row.layout().addWidget(self.reveal_server_button, 0)
        # Server Editor row
        self.server_editor = ServerEditor(parent=self)
        self.server_editor.setHidden(True)
        row.layout().addWidget(self.server_editor)

        # Select Job row
        row = QtWidgets.QGroupBox(parent=self)
        QtWidgets.QVBoxLayout(row)
        grp.layout().addWidget(row, 0)

        self.job_combobox = ComboBox(
            u'No jobs',
            parent=self)
        self.add_template_button = common_ui.ClickableIconButton(
            u'CopyAction',
            (common.SEPARATOR, common.SEPARATOR),
            common.MARGIN * 1.2,
            description=u'Add a new job to the current server',
            parent=row
        )
        self.reveal_job_button = common_ui.ClickableIconButton(
            u'active',
            (common.SEPARATOR, common.SEPARATOR),
            common.MARGIN * 1.2,
            description=u'Show the job in the explorer',
            parent=row
        )

        _row = common_ui.add_row(
            None, padding=0, height=common.ROW_HEIGHT * 0.8, parent=row)
        label = common_ui.PaintedLabel(
            u'Jobs:', size=common.MEDIUM_FONT_SIZE, color=common.SECONDARY_TEXT)
        label.setFixedWidth(common.MARGIN * 4.5)
        _row.layout().addWidget(self.add_template_button, 0)
        _row.layout().addSpacing(common.INDICATOR_WIDTH)
        _row.layout().addWidget(label)
        _row.layout().addWidget(self.job_combobox, 1)
        _row.layout().addWidget(self.reveal_job_button, 0)

        self.templates_widget = TemplatesWidget(u'job', parent=self)
        self.templates_widget.adjustSize()
        self.templates_widget.setHidden(True)
        row.layout().addWidget(self.templates_widget)

        # Bookmarks
        self.add_bookmark_button = common_ui.ClickableIconButton(
            u'CopyAction',
            (common.SEPARATOR, common.SEPARATOR),
            common.MARGIN * 1.2,
            description=u'Mark an existing folder `bookmarkable`',
            parent=row
        )

        row = QtWidgets.QGroupBox(parent=self)
        row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum,

        )
        QtWidgets.QVBoxLayout(row)
        grp.layout().addWidget(row, 0)

        _row = common_ui.add_row(
            None, padding=0, height=None, parent=row)
        label = common_ui.PaintedLabel(
            u'Bookmarks:', size=common.MEDIUM_FONT_SIZE, color=common.SECONDARY_TEXT)
        label.setFixedWidth(common.MARGIN * 4.5)

        self.bookmark_list = BookmarksWidget(parent=self)

        _row.layout().addWidget(self.add_bookmark_button)
        _row.layout().addSpacing(common.INDICATOR_WIDTH)
        _row.layout().addWidget(label)
        _row.layout().addWidget(self.bookmark_list)

        self.layout().addStretch(1)

        # Connect signals
        # Save server to config file and update UI
        self.server_editor.serverAdded.connect(self.add_server)
        self.server_editor.serverAdded.connect(self.init_server_combobox)
        self.server_editor.serverAdded.connect(toggle_server_editor)
        self.server_editor.serverRemoved.connect(self.remove_server)
        self.server_editor.serverRemoved.connect(self.init_server_combobox)

        self.edit_servers_button.clicked.connect(toggle_server_editor)
        self.reveal_server_button.clicked.connect(reveal_server)
        self.reveal_job_button.clicked.connect(reveal_job)
        self.add_template_button.clicked.connect(toggle_template_editor)
        self.server_combobox.currentIndexChanged.connect(
            self.init_job_combobox)
        self.server_combobox.currentIndexChanged.connect(
            lambda idx: self.templates_widget.set_path(
                self.server_combobox.itemData(idx, role=QtCore.Qt.UserRole))
        )
        self.server_combobox.currentIndexChanged.connect(
            lambda idx: settings.local_settings.setValue(
                u'{}/server_selection'.format(self.__class__.__name__), idx)
        )
        self.server_combobox.currentIndexChanged.connect(
            lambda idx: self.templates_widget.update)

        self.templates_widget.templateCreated.connect(toggle_template_editor)
        self.templates_widget.templateCreated.connect(job)

        self.job_combobox.currentIndexChanged.connect(
            self.init_bookmark_list)
        self.job_combobox.currentIndexChanged.connect(
            lambda idx: settings.local_settings.setValue(
                u'{}/job_selection'.format(self.__class__.__name__), idx)
        )

        self.add_bookmark_button.clicked.connect(add_new_bookmark)

        # Add/remove bookmarks
        def _toggle_bookmark(root, mode):
            idx = self.server_combobox.currentIndex()
            server = self.server_combobox.itemData(
                idx, role=QtCore.Qt.DisplayRole)
            idx = self.job_combobox.currentIndex()
            job = self.job_combobox.itemData(idx, role=QtCore.Qt.DisplayRole)

            if not all((server, job)):
                return
            root = root.lower().replace(
                u'{}/{}'.format(server, job).lower(),
                u''
            ).strip(u'/')
            if not all((server, job, root)):
                return

            if mode == AddMode:
                self.save_bookmark(
                    server, job, root, add_config_dir=True)
            if mode == RemoveMode:
                self.remove_saved_bookmark(server, job, root)

        self.bookmark_list.bookmarkAdded.connect(
            lambda s: _toggle_bookmark(s, AddMode))
        self.bookmark_list.bookmarkRemoved.connect(
            lambda s: _toggle_bookmark(s, RemoveMode))

    @staticmethod
    def key(*args):
        def r(s): return re.sub(ur'[\\]+', u'/',
                                s, flags=re.UNICODE | re.IGNORECASE)
        k = u'/'.join([r(f).rstrip(u'/') for f in args]).lower().rstrip(u'/')
        return k

    def get_saved_servers(self):
        def sep(s):
            return re.sub(
                ur'[\\]', u'/', s, flags=re.UNICODE | re.IGNORECASE)
        val = settings.local_settings.value(self.SERVER_KEY)
        if not val:
            return []
        if isinstance(val, (str, unicode)):
            return [val, ]
        return sorted([sep(f).lower() for f in val])

    def add_server(self, val):
        s = self.get_saved_servers()
        if val.lower() in s:
            return False
        s.append(val.lower())
        settings.local_settings.setValue(self.SERVER_KEY, list(set(s)))
        settings.local_settings.sync()
        return True

    def remove_server(self, val):
        s = self.get_saved_servers()
        if val.lower() in s:
            s.remove(val.lower())
        settings.local_settings.setValue(self.SERVER_KEY, list(set(s)))

    def _get_saved_bookmarks(self):
        val = settings.local_settings.value(self.BOOKMARK_KEY)
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

    def save_bookmark(self, server, job, root, add_config_dir=True):
        if not all((server, job, root)):
            return

        k = self.key(server, job, root)
        if add_config_dir:
            if not QtCore.QDir(k).mkpath(u'.bookmark'):
                print u'# Error: Could not add "{}/.bookmark"'.format(k)

        d = self._get_saved_bookmarks()
        d[k] = {
            u'server': unicode(server).encode(u'utf-8'),
            u'job':  unicode(job).encode(u'utf-8'),
            u'root':  unicode(root).encode(u'utf-8')
        }
        settings.local_settings.setValue(self.BOOKMARK_KEY, d)

    def remove_saved_bookmark(self, server, job, root):
        k = self.key(server, job, root)
        d = self._get_saved_bookmarks()
        if k in d:
            del d[k]
        settings.local_settings.setValue(self.BOOKMARK_KEY, d)

    @QtCore.Slot()
    def init_server_combobox(self):
        def _select_first_enabled():
            for n in xrange(self.server_combobox.count()):
                index = self.server_combobox.model().index(n, 0)
                if not index.flags() & QtCore.Qt.ItemIsEnabled:
                    continue
                self.server_combobox.setCurrentIndex(n)
                break

        # We don't want to emit `currentIndexChanged` signals whilst loading
        self.server_combobox.blockSignals(True)

        n = 0
        current_text = self.server_combobox.currentText()
        idx = self.server_combobox.currentIndex()

        self.server_combobox.clear()

        for k in self.get_saved_servers():
            pixmap = images.ImageCache.get_rsc_pixmap(
                u'server', common.TEXT, common.ROW_HEIGHT * 0.8)
            pixmap_selected = images.ImageCache.get_rsc_pixmap(
                u'server', common.ADD, common.ROW_HEIGHT * 0.8)
            icon = QtGui.QIcon()
            icon.addPixmap(pixmap, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Selected)

            self.server_combobox.addItem(icon, k.upper(), userData=k)
            item = self.server_combobox.model().item(n)
            self.server_combobox.setItemData(
                n, QtCore.QSize(0, common.ROW_HEIGHT * 0.8), QtCore.Qt.SizeHintRole)
            item.setData(common.TEXT, role=QtCore.Qt.TextColorRole)
            item.setData(common.BACKGROUND, role=QtCore.Qt.BackgroundColorRole)

            if not QtCore.QFileInfo(k).exists():
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(common.TEXT_DISABLED,
                             role=QtCore.Qt.TextColorRole)
                item.setData(common.SECONDARY_BACKGROUND,
                             role=QtCore.Qt.BackgroundColorRole)
                # item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                _pixmap = images.ImageCache.get_rsc_pixmap(
                    u'close', common.REMOVE, common.ROW_HEIGHT * 0.8)
                self.server_combobox.setItemIcon(
                    n, QtGui.QIcon(_pixmap))
            n += 1

        self.server_combobox.setCurrentIndex(-1)

        # Restoring the server selection from the saved value
        idx = settings.local_settings.value(
            u'{}/server_selection'.format(self.__class__.__name__))
        idx = 0 if idx is None else int(idx)
        idx = idx if idx < self.server_combobox.count() else 0
        idx = idx if idx >= 0 else 0
        self.server_combobox.setCurrentIndex(idx)

        # We wont signal chages unless the selection has actually changed
        self.server_combobox.blockSignals(False)
        if self.server_combobox.currentText() != current_text:
            self.server_combobox.currentIndexChanged.emit(idx)

    @QtCore.Slot(int)
    def init_job_combobox(self, idx):
        current_text = self.job_combobox.currentText()

        self.job_combobox.blockSignals(True)
        self.job_combobox.clear()

        if idx < 0:
            return

        server = self.server_combobox.itemData(
            idx, role=QtCore.Qt.UserRole)

        if not server:
            return

        file_info = QtCore.QFileInfo(server)
        if not file_info.exists():
            self.job_combobox.blockSignals(False)
            common_ui.ErrorBox(
                u'Error.', u'"{}" does not exist'.format(server),
                parent=self
            ).exec_()
            return
        if not file_info.isReadable():
            self.job_combobox.blockSignals(False)
            common_ui.ErrorBox(
                u'Error.', u'"{}" is not readable'.format(server),
                parent=self
            ).exec_()
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

            pixmap_off = images.ImageCache.get_rsc_pixmap(
                u'folder', common.SECONDARY_TEXT, common.ROW_HEIGHT * 0.8)
            pixmap_on = images.ImageCache.get_rsc_pixmap(
                u'folder', common.ADD, common.ROW_HEIGHT * 0.8)
            icon = QtGui.QIcon()
            icon.addPixmap(pixmap_off, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_on, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_off, QtGui.QIcon.Disabled)

            self.job_combobox.addItem(
                icon, entry.name.upper(), userData=entry.path.replace(u'\\', u'/'))
            item = self.job_combobox.model().item(n)
            self.job_combobox.setItemData(n, QtCore.QSize(
                0, common.ROW_HEIGHT * 0.8), QtCore.Qt.SizeHintRole)
            item.setData(common.TEXT, role=QtCore.Qt.TextColorRole)
            item.setData(common.BACKGROUND, role=QtCore.Qt.BackgroundColorRole)

            if not is_valid:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(common.TEXT_DISABLED,
                             role=QtCore.Qt.TextColorRole)
                item.setData(common.SECONDARY_BACKGROUND,
                             role=QtCore.Qt.BackgroundColorRole)
                _pixmap = images.ImageCache.get_rsc_pixmap(
                    u'close', common.REMOVE, common.ROW_HEIGHT * 0.8)
                self.job_combobox.setItemIcon(n, QtGui.QIcon(_pixmap))
            n += 1

        self.job_combobox.setCurrentIndex(-1)

        # Restoring the server selection from the saved value
        idx = settings.local_settings.value(
            u'{}/job_selection'.format(self.__class__.__name__))
        idx = 0 if idx is None else int(idx)
        idx = idx if idx < self.job_combobox.count() else 0
        idx = idx if idx >= 0 else 0
        self.job_combobox.setCurrentIndex(idx)

        self.job_combobox.blockSignals(False)
        if self.job_combobox.currentText() != current_text:
            self.job_combobox.currentIndexChanged.emit(idx)

    def get_bookmark_dirs(self, path, count, limit, arr):
        """Recursive scanning function for finding the bookmark folders
        inside the given path.

        """
        count += 1
        if count > limit:
            return arr

        try:
            it = scandir_it(path)
        except:
            return

        self.progressUpdate.emit(
            u'<span>Scanning for Bookmarks, please wait...</span><br><span>{}</span>'.format(path))
        QtWidgets.QApplication.instance().processEvents(
            QtCore.QEventLoop.ExcludeUserInputEvents)

        for entry in it:
            if not entry.is_dir():
                continue
            path = entry.path.replace(u'\\', u'/')
            if [f for f in arr if f in path]:
                continue

            if entry.name.lower() == u'.bookmark':
                arr.append(u'/'.join(path.split(u'/')[:-1]))
            self.get_bookmark_dirs(path, count, limit, arr)

        self.progressUpdate.emit(u'')
        return sorted(arr)

    @QtCore.Slot(int)
    def init_bookmark_list(self, idx):

        self.bookmark_list.blockSignals(True)

        self.bookmark_list.clear()
        path = self.job_combobox.itemData(idx, role=QtCore.Qt.UserRole)
        dirs = self.get_bookmark_dirs(path, -1, 4, [])
        self.bookmark_list.add_bookmark_items(dirs)

        saved_bookmarks = self.get_saved_bookmarks()
        for n in xrange(self.bookmark_list.count()):
            item = self.bookmark_list.item(n)
            if item.data(QtCore.Qt.UserRole).lower() in saved_bookmarks:
                item.setCheckState(QtCore.Qt.Checked)

        self.bookmark_list.blockSignals(False)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH * 0.5, common.HEIGHT * 0.5)

    def showEvent(self, event):
        self.init_timer.start()


class Bookmarks(QtWidgets.QScrollArea):
    def __init__(self, parent=None):
        super(Bookmarks, self).__init__(parent=parent)

        common.set_custom_stylesheet(self)
        self.setWidget(ManageBookmarksWidget(parent=self))
        self.setWidgetResizable(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum,
        )

        self.setWindowTitle(u'Manage Bookmarks')
        self.widget().hide_button.clicked.connect(self.hide)

    def showEvent(self, event):
        self.setFocus(QtCore.Qt.PopupFocusReason)


if __name__ == '__main__':
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])
    widget = Bookmarks()
    widget.show()
    app.exec_()
