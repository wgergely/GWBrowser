# -*- coding: utf-8 -*-
"""The widget used to add a new asset (eg. a shot) to a bookmark.

See `addbookmarks.TemplatesWidget` for more information, the main widget
responsible for listing, saving and expanding zip template files.

"""
import _scandir

from PySide2 import QtWidgets, QtCore, QtGui

from .. import common
from .. import log
from .. import images
from .. import common_ui
from .. import bookmark_db
from .. import settings
from . import shotgun
from . import task_tree


instance = None


class CreateTaskPublish(QtWidgets.QDialog):
    """Widget used to add a new version to a task.

    """
    def __init__(self, sg_properties, path, parent=None):
        global instance
        instance = self

        super(CreateTaskPublish, self).__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        self.setWindowTitle(u'Shotgun: Publish File')

        self.path = path
        self.sg_properties = sg_properties

        self.task_picker = None
        self.name_editor = None
        self.description_editor = None
        self.version_editor = None
        self.path_to_file_editor = None
        self.add_button = None
        self.user_picker = None
        self.storage_picker = None
        self.type_picker = None

        self.init_timer = QtCore.QTimer(parent=self)
        self.init_timer.setSingleShot(True)
        self.init_timer.setInterval(250)

        self._create_UI()
        self._connect_signals()

    def _connect_signals(self):
        self.init_timer.timeout.connect(self.init_values)
        self.add_button.clicked.connect(self.action)

        self.path_to_file_picker.clicked.connect(self.pick_file)
        self.user_picker.currentTextChanged.connect(
            lambda s: settings.local_settings.setValue(
                settings.UIStateSection,
                settings.SGUserKey,
                s
            ))
        self.storage_picker.currentTextChanged.connect(
            lambda s: settings.local_settings.setValue(
                settings.UIStateSection,
                settings.SGStorageKey,
                s
            ))
        self.type_picker.currentTextChanged.connect(
            lambda s: settings.local_settings.setValue(
                settings.UIStateSection,
                settings.SGTypeKey,
                s
            ))

    @QtCore.Slot()
    def pick_file(self):
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(u'All files (*.*)')
        dialog.setDirectory(QtCore.QFileInfo(self.path).path())
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(
            QtWidgets.QFileDialog.Accept,
            u'Select file'
        )
        dialog.setWindowTitle(u'Select a file to publish')
        if not dialog.exec_():
            return
        for source in dialog.selectedFiles():
            self.path_to_file_editor.setText(source)
            return

    def _create_UI(self):
        o = common.MARGIN()
        height = common.ROW_HEIGHT()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        def _add_title(icon, label, parent, color=None):
            row = common_ui.add_row(u'', parent=parent)
            _label = QtWidgets.QLabel(parent=self)
            pixmap = images.ImageCache.get_rsc_pixmap(icon, color, height)
            _label.setPixmap(pixmap)
            row.layout().addWidget(_label, 0)
            label = common_ui.PaintedLabel(
                label,
                size=common.MEDIUM_FONT_SIZE(),
                parent=self
            )
            row.layout().addWidget(label, 0)
            row.layout().addStretch(1)
            parent.layout().addSpacing(o * 0.5)

        project = bookmark_db.get_property(u'shotgun_name')
        project = project if project else u''
        shot = bookmark_db.get_property(u'shotgun_name', asset_property=True)
        shot = shot if shot else u''

        if not all((project, shot)):
            self.setDisabled(True)

        project_hint = common_ui.PaintedLabel(project, parent=self)
        asset_hint = common_ui.PaintedLabel(shot, parent=self)
        self.task_picker = task_tree.TaskTree(parent=self)
        self.task_picker.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self.description_editor = common_ui.LineEdit(parent=self)
        self.description_editor.setPlaceholderText('My latest file')
        self.name_editor = common_ui.LineEdit(parent=self)
        self.name_editor.setPlaceholderText('file_v001.ma')
        self.version_editor = common_ui.LineEdit(parent=self)
        self.version_editor.setPlaceholderText('Version')
        self.path_to_file_editor = common_ui.LineEdit(parent=self)
        self.path_to_file_editor.setPlaceholderText(u'/path/to/file_v001.ma')
        self.path_to_file_picker = common_ui.PaintedButton(u'Pick')
        self.add_button = common_ui.PaintedButton(u'Publish File')
        self.user_picker = QtWidgets.QComboBox(parent=self)
        self.user_picker.setFixedHeight(height * 0.66)
        self.storage_picker = QtWidgets.QComboBox(parent=self)
        self.storage_picker.setFixedHeight(height * 0.66)
        self.type_picker = QtWidgets.QComboBox(parent=self)
        self.type_picker.setFixedHeight(height * 0.66)

        _add_title(u'shotgun', u'Publish File to Shotgun', self)
        o *= 0.5
        grp = common_ui.get_group(parent=self)
        grp.layout().setSpacing(0)
        grp.layout().setContentsMargins(o, o, o, o)

        row = common_ui.add_row('Project', parent=grp)
        row.layout().addWidget(project_hint)
        row.layout().addStretch(1)
        row = common_ui.add_row('Shot', parent=grp)
        row.layout().addWidget(asset_hint)
        row.layout().addStretch(1)

        grp = common_ui.get_group(parent=self)
        grp.layout().setSpacing(o)
        grp.layout().setContentsMargins(o, o, o, o)
        row = common_ui.add_row(u'Select task', height=common.HEIGHT() * 0.6, parent=grp)
        row.layout().addWidget(self.task_picker)

        grp = common_ui.get_group(parent=self)
        row = common_ui.add_row(u'Publish Name', parent=grp)
        row.layout().addWidget(self.name_editor)
        row = common_ui.add_row(u'Description', parent=grp)
        row.layout().addWidget(self.description_editor)
        row = common_ui.add_row(u'Version', parent=grp)
        row.layout().addWidget(self.version_editor)

        row = common_ui.add_row(u'Path to file', parent=grp)
        row.layout().addWidget(self.path_to_file_editor, 1)
        row.layout().addWidget(self.path_to_file_picker)
        row = common_ui.add_row(u'Add version as', parent=grp)
        row.layout().addWidget(self.user_picker, 1)
        row = common_ui.add_row(u'Select type', parent=grp)
        row.layout().addWidget(self.type_picker, 1)
        row = common_ui.add_row(u'Select storage', parent=grp)
        row.layout().addWidget(self.storage_picker, 1)

        self.layout().addStretch(1)
        self.layout().addWidget(self.add_button, 1)

    @common.error
    @common.debug
    def init_values(self):
        if not shotgun.is_valid(self.sg_properties):
            raise RuntimeError('Shotgun not configured properly.')

        server = self.sg_properties[settings.ServerKey]
        job = self.sg_properties[settings.JobKey]
        root = self.sg_properties[settings.RootKey]

        with shotgun.connection(server, job, root) as sg:
            try:
                tasks = sg.find_tasks(
                    self.sg_properties[shotgun.SGAssetEntityType],
                    self.sg_properties[shotgun.SGAssetEntityID],
                )
                self._add_tasks(tasks)
                self._restore_previous_task()
            except:
                log.error('Failed to get Shotgun tasks')

            try:
                users = sg.find_users()
                self._add_users(users)
                self._restore_previous_user()
            except:
                log.error('Failed to get Shotgun users')

            try:
                storage = sg.find_storage()
                self._add_users(storage)
                self._restore_previous_storage()
            except:
                storage = []
                log.error('Failed to get Shotgun storage')

            try:
                types = sg.find_published_file_types()
            except:
                types = []
                log.error('Failed to get Shotgun published file types')

    def _add_tasks(self, tasks):
        self.task_picker.blockSignals(True)
        try:
            self.task_picker.set_data(tasks)
        finally:
            self.task_picker.blockSignals(False)

    def _restore_previous_task(self):
        pass

    def _add_users(self, users):
        if not users:
            return

        self.user_picker.blockSignals(True)
        try:
            self.user_picker.addItem(u'Select name...', userData=None)
            try:
                users = sorted(users, key=lambda x: x[shotgun.NameColumn])
            except:
                try:
                    users = sorted(users, key=lambda x: x[shotgun.IdColumn])
                except:
                    pass

            for user in users:
                if shotgun.NameColumn in user:
                    self.user_picker.addItem(user['name'], userData=user[shotgun.IdColumn])
                elif shotgun.IdColumn in user:
                    name = 'HumanUser{}'.format(user[shotgun.IdColumn])
                    self.user_picker.addItem(name, userData=user[shotgun.IdColumn])
                else:
                    continue
        finally:
            self.user_picker.blockSignals(False)

    def _restore_previous_user(self):
        prev = settings.local_settings.value(
            settings.UIStateSection,
            settings.SGUserKey
        )
        if prev:
            self.user_picker.setCurrentText(prev)

    def _add_storage(self, storage):
        if not storage:
            return

        self.storage_picker.blockSignals(True)
        try:
            self.storage_picker.addItem(u'Select Local Storage...', userData=None)
            try:
                storage = sorted(storage, key=lambda x: x[shotgun.CodeColumn])
            except:
                try:
                    storage = sorted(storage, key=lambda x: x[shotgun.IdColumn])
                except:
                    pass

            for store in storage:
                name = None
                if 'code' in store:
                    name = store['code']
                elif 'description' in store:
                    name = store['description']
                elif shotgun.IdColumn in store:
                    name = u'LocalStorage{}'.format(store[shotgun.IdColumn])
                else:
                    continue
                if not name:
                    continue
                self.storage_picker.addItem(name, userData=store[shotgun.IdColumn])
        finally:
            self.storage_picker.blockSignals(False)

    def _restore_previous_storage(self):
        prev = settings.local_settings.value(
            settings.UIStateSection,
            settings.SGStorageKey
        )
        if prev:
            self.storage_picker.setCurrentText(prev)
        self.storage_picker.addItem(u'Error loading storage list', userData=None)

    def _add_types(self, types):
        if not types:
            return

        self.type_picker.blockSignals(True)
        try:
            self.type_picker.addItem(u'Select type...', userData=None)
            try:
                types = sorted(types, key=lambda x: x[shotgun.CodeColumn])
            except:
                try:
                    types = sorted(types, key=lambda x: x[shotgun.IdColumn])
                except:
                    pass

            for _type in types:
                name = None
                if shotgun.CodeColumn in _type:
                    name = _type[shotgun.CodeColumn]
                elif 'short_name' in _type:
                    name = _type['short_name']
                elif shotgun.IdColumn in _type:
                    name = u'PublishedFileType{}'.format(_type[shotgun.IdColumn])
                if not name:
                    continue
                self.type_picker.addItem(name, userData=_type[shotgun.IdColumn])
        finally:
            self.type_picker.blockSignals(False)

    def _restore_previous_type(self):
        v = settings.local_settings.value(
            settings.UIStateSection,
            settings.SGTypeKey
        )
        if not v:
            return
        self.type_picker.setCurrentText(v)

    def _init_sequence(self):
        # Path
        if common.is_collapsed(self.path):
            path = common.get_sequence_endpath(self.path)
        else:
            path = self.path

        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            raise RuntimeError(u'Path does not exist')

        self.path_to_file_editor.setText(path)

        seq = common.get_sequence(self.path)
        if not seq:
            name = file_info.baseName().strip('.').strip('_')
            version = '0'
        else:
            version = seq.group(2)
            name = u'{}_{}'.format(
                seq.group(1).strip('.').strip('_').strip(' '),
                seq.group(3).strip('.').strip('_').strip(' '),
            )
            name = QtCore.QFileInfo(name).baseName().strip('.').strip('_')

        # Strip version indicator
        name = name.strip('.').strip('_').rstrip('_v')

        self.name_editor.setText(name)
        self.version_editor.setText(version)

    @QtCore.Slot()
    def action(self):
        try:
            project_id = bookmark_db.get_property(u'shotgun_id')
            if project_id is None:
                raise RuntimeError('Project ID is not set.')

            sg_id = bookmark_db.get_property(u'shotgun_id', asset_property=True)
            if sg_id is None:
                raise RuntimeError('ID is not set.')

            if not self.task_picker.selectionModel().hasSelection():
                common_ui.MessageBox(u'Select a task before continuing.', u'').open()
                return

            index = self.task_picker.selectionModel().currentIndex()
            if not index.isValid():
                common_ui.MessageBox(u'Select a task before continuing.', u'').open()
                return
            node = index.internalPointer()

            task_id = node.data[shotgun.IdColumn]
            code = self.name_editor.text()
            if not code:
                common_ui.MessageBox(u'Name not entered.', u'').open()
                return

            path = self.path_to_file_editor.text()
            if not path:
                common_ui.MessageBox(u'Path not entered.', u'').open()
                return

            version = self.version_editor.text()
            if not version:
                common_ui.MessageBox(u'Version not entered.', u'').open()
                return

            description = self.description_editor.text()

            user_id = self.user_picker.currentData()
            storage_id = self.storage_picker.currentData()
            type_id = self.type_picker.currentData()
            # if not user:
            #     common_ui.MessageBox(u'User not selected.', u'').open()
            #     return
            # if not storage:
            #     common_ui.MessageBox(u'Storage not selected.', u'').open()
            #     return
            # if not type:
            #     common_ui.MessageBox(u'Type not selected.', u'').open()
            #     return

            domain = bookmark_db.get_property(u'shotgun_domain')
            script = bookmark_db.get_property(u'shotgun_scriptname')
            key = bookmark_db.get_property(u'shotgun_key')

            with shotgun.init_sg(domain, script, key):
                p = common_ui.MessageBox(u'Publishing file...', u'Should not take too long!')
                p.open()

                QtWidgets.QApplication.instance().processEvents()
                try:
                    entity = shotgun.add_publishedfile(
                        project_id,
                        sg_id,
                        task_id,
                        storage_id,
                        type_id,
                        code,
                        description,
                        path,
                        version,
                        user_id
                    )
                except Exception as e:
                    common_ui.ErrorBox(u'Error.', unicode(e)).open()
                    log.error(u'Error adding new version')
                    raise
                finally:
                    p.close()

                url = u'{}/detail/PublishedFile/{}'.format(domain, entity[shotgun.IdColumn])
                QtGui.QDesktopServices.openUrl(url)

        except Exception as e:
            common_ui.ErrorBox(u'Could not publish.', unicode(e)).open()
            log.error('An error occured.')
            raise

    def showEvent(self, event):
        self.init_timer.start()

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 0.8, common.HEIGHT() * 1.2)
