# -*- coding: utf-8 -*-
"""Widget used to unpack a ZIP template to a specific location.

"""
import zipfile

from PySide2 import QtCore, QtWidgets, QtGui

from . import log
from . import common
from . import common_ui
from . import images
from . import contextmenu


class TemplateContextMenu(contextmenu.BaseContextMenu):

    def __init__(self, index, parent=None):
        super(TemplateContextMenu, self).__init__(index, parent=parent)
        self.add_refresh_menu()
        if not index:
            return
        self.add_new_template_menu()

        self.add_separator()
        self.add_remove_menu()

    @contextmenu.contextmenu
    def add_remove_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'close', common.REMOVE, common.MARGIN())

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
            else:
                common_ui.ErrorBox(
                    u'Could not remove the template.',
                    u'An unknown error occured.',
                ).open()

        menu_set[u'Delete'] = {
            u'action': delete,
            u'icon': pixmap
        }

        return menu_set

    @contextmenu.contextmenu
    def add_refresh_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.MARGIN())
        add_pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN())

        try:
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
        except:
            pass
        return menu_set

    @contextmenu.contextmenu
    def add_new_template_menu(self, menu_set):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN())

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
        self._drag_in_progress = False

        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed
        )

        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.installEventFilter(self)
        self.viewport().installEventFilter(self)

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

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction

    def dropMimeData(self, index, data, action):
        if not data.hasUrls():
            return False

        if action & self.supportedDropActions():
            return False

        return True

    def copy_template(self, source):
        templates_dir = self.templates_dir_path()

        file_info = QtCore.QFileInfo(source)
        destination = u'{}/{}'.format(templates_dir, file_info.fileName())
        dest_info = QtCore.QFileInfo(destination)

        # Let's check if file exists before we copy anything...
        if dest_info.exists():
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setWindowTitle(u'A file already exists')
            mbox.setText(
                u'"{}" already exists.'.format(dest_info.fileName()))
            mbox.setInformativeText(u'Are you sure you want to override it?')
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
            mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)

            res = mbox.exec_()
            if res == QtWidgets.QMessageBox.Cancel:
                return
            elif res == QtWidgets.QMessageBox.Yes:
                QtCore.QFile.remove(destination)

        # If copied successfully, let's reload the ``TemplateListWidget``
        # contents.
        res = QtCore.QFile.copy(source, destination)
        if res:
            self.load_templates()
        else:
            log.error('Could not copy the template')
            common_ui.ErrorBox(
                u'Error saving the template.',
                u'Could not copy the template file, an unknown error occured.',
            ).open()

    def eventFilter(self, widget, event):
        if widget == self.viewport():
            if event.type() == QtCore.QEvent.DragEnter:
                if event.mimeData().hasUrls():
                    self._drag_in_progress = True
                    self.repaint()
                    event.accept()
                else:
                    event.ignore()
                return True

            if event.type() == QtCore.QEvent.DragLeave:
                self._drag_in_progress = False
                self.repaint()
                return True

            if event.type() == QtCore.QEvent.DragMove:
                if event.mimeData().hasUrls():
                    self._drag_in_progress = True
                    event.accept()
                else:
                    self._drag_in_progress = False
                    event.ignore()
                return True

            if event.type() == QtCore.QEvent.Drop:
                self._drag_in_progress = False
                self.repaint()

                for url in event.mimeData().urls():
                    p = url.toLocalFile()
                    if zipfile.is_zipfile(p):
                        self.copy_template(p)

                return True

        if widget is not self:
            return False

        if event.type() is QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)

            # painter.setBrush(QtCore.Qt.NoBrush)
            # painter.setPen(QtCore.Qt.NoPen)
            painter.setFont(common.font_db.secondary_font(
                common.SMALL_FONT_SIZE())[0])
            # painter.setOpacity(0.3)
            # painter.drawRect(self.rect())
            o = common.MEDIUM_FONT_SIZE()
            rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))

            if self._drag_in_progress:
                painter.setBrush(common.ADD)
                pen = QtGui.QPen(common.ADD)
                pen.setWidth(common.INDICATOR_WIDTH())
                painter.setPen(pen)
                painter.setOpacity(0.5)
                painter.drawRect(self.rect())
                painter.setOpacity(1.0)
            else:
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.setPen(QtGui.QColor(255, 255, 255, 100))

            painter.drawText(
                rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
                u'Select template\n(drag and drop a zip file to add)',
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
            name.replace(u' ', u'_')
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

        size = QtCore.QSize(1, common.ROW_HEIGHT() * 0.8)
        off_pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon', common.SECONDARY_BACKGROUND, common.ROW_HEIGHT() * 0.8)
        on_pixmap = images.ImageCache.get_rsc_pixmap(
            u'icon', common.ADD, common.ROW_HEIGHT() * 0.8)
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
        return QtCore.QSize(common.WIDTH() * 0.15, common.WIDTH() * 0.2)


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

            painter.setFont(common.font_db.secondary_font(
                common.SMALL_FONT_SIZE())[0])
            painter.drawRect(self.rect())
            o = common.MEDIUM_FONT_SIZE()
            rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
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
        return QtCore.QSize(common.WIDTH() * 0.15, common.WIDTH() * 0.2)


class TemplatesWidget(QtWidgets.QDialog):
    templateCreated = QtCore.Signal(unicode)

    def __init__(self, mode, parent=None):
        super(TemplatesWidget, self).__init__(parent=parent)

        common.set_custom_stylesheet(self)

        self._path = None
        self._mode = mode

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)

        self.templates_group = None
        self.template_list_widget = None
        self.template_contents_widget = None
        self.add_button = None
        self.cancel_button = None


        self.setWindowTitle(u'Create {}'.format(self.mode().title()))

        self._create_UI()
        self._connect_signals()

    def mode(self):
        return self._mode

    def path(self):
        return self._path

    def set_path(self, val):
        self._path = val

    def _create_UI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        o = common.MARGIN()

        parent = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(parent)
        parent.layout().setAlignment(QtCore.Qt.AlignCenter)
        parent.layout().setContentsMargins(o, o, o, o)
        parent.layout().setSpacing(o * 0.5)
        parent.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.scrollarea.setWidget(parent)
        self.layout().addWidget(self.scrollarea, 1)

        grp = common_ui.get_group(parent=parent)
        row = common_ui.add_row(u'Name', height=None, parent=grp)

        self.name_widget = common_ui.LineEdit(parent=row)
        self.name_widget.setFont(
            common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0])
        self.name_widget.setPlaceholderText(
            u'Enter name, eg. NEW_{}_000'.format(self.mode().upper()))
        regex = QtCore.QRegExp(ur'[a-zA-Z0-9\_\-]+')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.name_widget.setValidator(validator)

        self.add_button = common_ui.PaintedButton(
            u'Create {}'.format(self.mode()), parent=self)
        self.cancel_button = common_ui.PaintedButton(u'Cancel', parent=self)


        row.layout().addWidget(self.name_widget, 1)

        # Template Header
        self.templates_group = common_ui.get_group(parent=parent)
        row = common_ui.add_row('Template', height=None, parent=self.templates_group)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)
        splitter = QtWidgets.QSplitter(parent=parent)
        splitter.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum,
        )
        splitter.setMaximumHeight(common.WIDTH() * 0.3)
        self.template_list_widget = TemplateListWidget(
            self.mode(), parent=parent)
        self.template_contents_widget = TemplatesPreviewWidget(parent=parent)
        splitter.addWidget(self.template_list_widget)
        splitter.addWidget(self.template_contents_widget)
        splitter.setSizes([common.WIDTH() * 0.2, common.WIDTH() * 0.12])

        row.layout().addWidget(splitter, 1)

        row = common_ui.add_row(None, padding=None, parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.cancel_button, 0)
        row.layout().addWidget(self.add_button, 0)
        row.layout().addStretch(1)

    def _connect_signals(self):
        self.template_list_widget.selectionModel(
        ).selectionChanged.connect(self.itemActivated)
        self.add_button.clicked.connect(self.create_template)
        self.cancel_button.clicked.connect(lambda: self.done(QtWidgets.QDialog.Rejected))
        self.name_widget.returnPressed.connect(self.create_template)

    @QtCore.Slot()
    def create_template(self):
        """Verifies the user choices and expands the selected template to the
        currently set `path`.

        """
        h = u'Unable to create {}.'.format(self.mode().lower())
        if not self.path():
            common_ui.ErrorBox(
                h, u'Destination folder has not been set.',
            ).open()
            raise RuntimeError(h)

        file_info = QtCore.QFileInfo(self.path())
        if not file_info.exists():
            common_ui.ErrorBox(
                h, u' The destination folder "{}" does not exist.'.format(
                    file_info.filePath()),
            ).open()
            return
        if not file_info.isWritable():
            common_ui.ErrorBox(
                h, u'Destination folder "{}" is not writable!'.format(
                    file_info.filePath()),
            ).open()
            return

        if not self.name_widget.text():
            common_ui.ErrorBox(
                h, u'Enter a name and try again.',
            ).open()
            return

        file_info = file_info = QtCore.QFileInfo(
            u'{}/{}'.format(self.path(), self.name_widget.text()))

        if file_info.exists():
            common_ui.ErrorBox(
                h, u'"{}" already exists!'.format(self.name_widget.text()),
            ).open()
            return

        model = self.template_list_widget.selectionModel()
        if not model.hasSelection():
            common_ui.ErrorBox(
                h, u'Select {} folder template and try again'.format(
                    self.mode()),
            ).open()
            return

        index = model.selectedIndexes()[0]
        if not index.isValid():
            return

        source = index.data(QtCore.Qt.UserRole + 1)
        try:
            with zipfile.ZipFile(source, 'r', zipfile.ZIP_DEFLATED) as f:
                f.extractall(file_info.absoluteFilePath(),
                             members=None, pwd=None)
            self.templateCreated.emit(self.name_widget.text())
        except Exception as err:
            s = u'Error occured creating the {}:\n{}'.format(
                self.mode(), err)
            common_ui.ErrorBox(
                h, s,
            ).open()
            log.error(s)
            raise

        self.done(QtWidgets.QDialog.Accepted)


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
                            u'Select a {} template'.format(self.mode().title()))
        dialog.setWindowTitle(
            u'Select a {m} template from the list before continuing.'.format(m=self.mode().lower()))

        if not dialog.exec_():
            return

        templates_dir = self.template_list_widget.templates_dir_path()

        # Let's iterate over the selected files
        for source in dialog.selectedFiles():
            file_info = QtCore.QFileInfo(source)
            destination = u'{}/{}'.format(templates_dir, file_info.fileName())
            dest_info = QtCore.QFileInfo(destination)

            # Let's check if file exists before we copy anything...
            if dest_info.exists():
                mbox = QtWidgets.QMessageBox(parent=self)
                mbox.setIcon(QtWidgets.QMessageBox.Warning)
                mbox.setWindowTitle(u'A file already exists')
                mbox.setText(
                    u'"{}" already exists.'.format(dest_info.fileName()))
                mbox.setInformativeText(
                    u'Are you sure you want to override it?')
                mbox.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
                mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)

                res = mbox.exec_()
                if res == QtWidgets.QMessageBox.Cancel:
                    continue
                elif res == QtWidgets.QMessageBox.Yes:
                    QtCore.QFile.remove(destination)

            # If copied successfully, let's reload the ``TemplateListWidget``
            # contents.
            res = QtCore.QFile.copy(source, destination)
            if res:
                self.template_list_widget.load_templates()
            else:
                log.error(u'Could not copy the template')
                common_ui.ErrorBox(
                    u'Error saving the template.',
                    u'Could not copy the template file, an unknown error occured.',
                ).open()

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

        size = QtCore.QSize(0, common.ROW_HEIGHT() * 0.8)
        folder_pixmap = images.ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.MARGIN())
        folder_icon = QtGui.QIcon()
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Normal)
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Selected)
        folder_icon.addPixmap(folder_pixmap, QtGui.QIcon.Disabled)

        file_pixmap = images.ImageCache.get_rsc_pixmap(
            u'files', common.ADD, common.MARGIN(), opacity=0.5)
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
            item.setData(QtCore.Qt.FontRole, common.font_db.secondary_font(
                common.SMALL_FONT_SIZE())[0])
            item.setData(QtCore.Qt.DisplayRole, f)
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.template_contents_widget.addItem(item)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())
