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


__instance = None

class CreateTaskVersion(QtWidgets.QDialog):
    """Widget used to create a new version.

    """

    def __init__(self, path, parent=None):
        global __instance
        __instance = self

        super(CreateTaskVersion, self).__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        if not path:
            log.error('Path not specified.')
            raise RuntimeError('Path not specified.')

        self.setWindowTitle(u'Shotgun: Add Task Version')

        self.path = path
        self.sequence_path = None
        self.movie_path = None

        self.task_picker = None
        self.name_editor = None
        self.description_editor = None
        self.path_to_movie_editor = None
        self.path_to_frames_editor = None
        self.path_to_movie_picker = None
        self.path_to_frames_picker = None
        self.add_button = None
        self.user_picker = None

        self.init_timer = QtCore.QTimer(parent=self)
        self.init_timer.setSingleShot(True)
        self.init_timer.setInterval(250)

        self._create_UI()
        self._connect_signals()

    def _connect_signals(self):
        self.init_timer.timeout.connect(self.init_values)
        self.add_button.clicked.connect(self.action)
        self.path_to_movie_picker.clicked.connect(self.pick_movie)
        self.path_to_frames_picker.clicked.connect(self.pick_frame)
        self.user_picker.currentTextChanged.connect(self.save_current)

    @QtCore.Slot()
    def save_current(self, text):
        settings.local_settings.setValue(
            settings.UIStateSection,
            settings.SGUserKey,
            text
        )

    @QtCore.Slot()
    def pick_movie(self):
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(u'Movies (*.mp4 *.mov)')
        dialog.setDirectory(QtCore.QFileInfo(self.path).path())
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(
            QtWidgets.QFileDialog.Accept,
            u'Select a movie files'
        )
        dialog.setWindowTitle(u'A movie to add')
        if not dialog.exec_():
            return
        for source in dialog.selectedFiles():
            self.path_to_movie_editor.setText(source)
            return

    def pick_frame(self):
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(u'Frames (*.jpg *.jpeg *.png)')
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setDirectory(QtCore.QFileInfo(self.path).path())
        dialog.setLabelText(
            QtWidgets.QFileDialog.Accept,
            u'Select a frame file'
        )
        dialog.setWindowTitle(u'A frame to add')
        if not dialog.exec_():
            return
        for source in dialog.selectedFiles():
            seq = common.get_sequence(source)
            if seq:
                source = u'{}{}{}.{}'.format(
                    seq.group(1),
                    u'#' * len(seq.group(2)),
                    seq.group(3),
                    seq.group(4)
                )
            self.path_to_frames_editor.setText(source)
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
        self.description_editor.setPlaceholderText('My Latest quicktime')
        self.name_editor = common_ui.LineEdit(parent=self)
        self.name_editor.setPlaceholderText('MYSHOT_v001.mp4')
        self.path_to_movie_editor = common_ui.LineEdit(parent=self)
        self.path_to_movie_editor.setPlaceholderText(u'/path/to/shot.mp4')
        self.path_to_frames_editor = common_ui.LineEdit(parent=self)
        self.path_to_frames_editor.setPlaceholderText(u'/path/to/shot.#.jpg')
        self.path_to_movie_picker = common_ui.PaintedButton(u'Pick')
        self.path_to_frames_picker = common_ui.PaintedButton(u'Pick')
        self.add_button = common_ui.PaintedButton(u'Create Version')
        self.user_picker = QtWidgets.QComboBox(parent=self)
        self.user_picker.setFixedHeight(height * 0.66)

        _add_title(u'shotgun', u'Add a Task Version to Shot', self)
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
        row = common_ui.add_row(
            u'Select task', height=common.HEIGHT() * 0.6, parent=grp)
        row.layout().addWidget(self.task_picker)

        grp = common_ui.get_group(parent=self)
        row = common_ui.add_row(u'Version Name', parent=grp)
        row.layout().addWidget(self.name_editor)
        row = common_ui.add_row(u'Description', parent=grp)
        row.layout().addWidget(self.description_editor)

        row = common_ui.add_row(u'Path to movie', parent=grp)
        row.layout().addWidget(self.path_to_movie_editor, 1)
        row.layout().addWidget(self.path_to_movie_picker)
        row = common_ui.add_row(u'Path to frames', parent=grp)
        row.layout().addWidget(self.path_to_frames_editor, 1)
        row.layout().addWidget(self.path_to_frames_picker)
        row = common_ui.add_row(u'Add version as', parent=grp)
        row.layout().addWidget(self.user_picker, 1)

        self.layout().addStretch(1)
        self.layout().addWidget(self.add_button, 1)

    @common.error
    @QtCore.Slot()
    def init_values(self):
        project_id = bookmark_db.get_property(u'shotgun_id')
        if project_id is None:
            raise RuntimeError('Project ID is not set.')

        sg_id = bookmark_db.get_property(
            u'shotgun_id', asset_property=True)
        if sg_id is None:
            raise RuntimeError('ID is not set.')
        entity_type = bookmark_db.get_property(
            u'shotgun_type', asset_property=True)
        if entity_type is None:
            raise RuntimeError('Shotgun entity type is not set.')

        domain = bookmark_db.get_property(u'shotgun_domain')
        script = bookmark_db.get_property(u'shotgun_scriptname')
        key = bookmark_db.get_property(u'shotgun_key')

        # Get task data

        with shotgun.connection(domain, script, key) as _:
            data = shotgun.find_tasks(
                entity_type,
                sg_id
            )
            users = shotgun.find_users()
        if not data:
            raise RuntimeError(
                u'Could not find any tasks for ID {}'.format(sg_id))
        self.task_picker.set_data(data)

        if users:
            self.user_picker.blockSignals(True)

            try:
                users = sorted(users, key=lambda x: x['name'])
            except:
                pass

            try:
                users = sorted(users, key=lambda x: x['id'])
            except:
                pass

            self.user_picker.addItem(u'Select name...', userData=None)

            for user in users:
                if 'name' in user:
                    self.user_picker.addItem(
                        user['name'], userData=user['id'])
                elif 'id' in user:
                    name = 'HumanUser{}'.format(user['id'])
                    self.user_picker.addItem(name, userData=user['id'])
                else:
                    continue

            self.user_picker.blockSignals(False)
            prev = settings.local_settings.value(
                settings.UIStateSection,
                settings.SGUserKey
            )
            if prev:
                self.user_picker.setCurrentText(prev)

        # Path
        path = common.get_sequence_startpath(self.path)
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            raise RuntimeError(u'Path does not exist')
        seq = common.get_sequence(path)

        if not seq:
            name = file_info.baseName().strip('.').strip('_')
            self.name_editor.setText(name)
            if 'mp4' in path.lower() or 'mov' in path.lower():
                self.path_to_movie_editor.setText(path)
            if 'jpg' in path.lower() or 'jpeg' in path.lower() or 'png' in path.lower():
                self.path_to_frames.setText(path)
            return

        frames = []
        movs = []
        for entry in _scandir.scandir(file_info.path()):
            path = entry.path.replace(u'\\', u'/')
            if not seq.group(1).lower() in path.lower():
                continue
            _seq = common.get_sequence(path)
            if not _seq:
                continue
            if _seq.group(4).lower() in (u'mp4', u'mov'):
                movs.append(path)
            if _seq.group(4).lower() in (u'jpg', u'png', 'jpeg'):
                frames.append(path)

        name = file_info.baseName().strip('.').strip('_')
        self.name_editor.setText(name)
        if frames:
            seq = common.get_sequence(frames[0])
            path_to_frames = u'{}{}{}.{}'.format(
                seq.group(1),
                u'#' * len(seq.group(2)),
                seq.group(3),
                seq.group(4)
            )
            self.path_to_frames_editor.setText(path_to_frames)

        if movs:
            if movs:
                self.path_to_movie_editor.setText(movs[0])

    @QtCore.Slot()
    def action(self):
        try:
            project_id = bookmark_db.get_property(u'shotgun_id')
            if project_id is None:
                raise RuntimeError('Project ID is not set.')

            sg_id = bookmark_db.get_property(
                u'shotgun_id', asset_property=True)
            if sg_id is None:
                raise RuntimeError('ID is not set.')

            if not self.task_picker.selectionModel().hasSelection():
                common_ui.MessageBox(
                    u'Select a task before continuing.', u'').open()
                return

            index = self.task_picker.selectionModel().currentIndex()
            if not index.isValid():
                common_ui.MessageBox(
                    u'Select a task before continuing.', u'').open()
                return
            node = index.internalPointer()

            task_id = node.data['id']
            code = self.name_editor.text()
            if not code:
                common_ui.MessageBox(u'Name not entered.', u'').open()
                return

            description = self.description_editor.text()
            path_to_movie = self.path_to_movie_editor.text()
            path_to_frames = self.path_to_frames_editor.text()
            if not any((path_to_movie, path_to_frames)):
                common_ui.MessageBox(
                    u'You must provide either a path to a movie or a path to a frame file.', u'').open()
                return
            user = self.user_picker.currentData()
            if not user:
                common_ui.MessageBox(
                    u'Select a user before continuing.', u'').open()
                return

            domain = bookmark_db.get_property(u'shotgun_domain')
            script = bookmark_db.get_property(u'shotgun_scriptname')
            key = bookmark_db.get_property(u'shotgun_key')

            with shotgun.init_sg(domain, script, key):
                p = common_ui.MessageBox(
                    u'Adding version...', u'Should not take too long!')
                p.open()

                QtWidgets.QApplication.instance().processEvents()
                try:
                    entity = shotgun.add_version(
                        project_id,
                        sg_id,
                        task_id,
                        code,
                        description,
                        path_to_movie,
                        path_to_frames,
                        user
                    )
                except Exception as e:
                    common_ui.ErrorBox(u'Error.', unicode(e)).open()
                    log.error(u'Error adding new version')
                    raise
                finally:
                    p.close()

                url = u'{}/detail/Version/{}'.format(domain, entity['id'])
                QtGui.QDesktopServices.openUrl(url)

        except Exception as e:
            common_ui.ErrorBox(u'Could not add version.', unicode(e)).open()
            log.error('An error occured.')
            raise

    def showEvent(self, event):
        self.init_timer.start()

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 0.8, common.HEIGHT() * 1.2)
