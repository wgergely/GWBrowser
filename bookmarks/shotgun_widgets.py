# -*- coding: utf-8 -*-
"""The widget used to add a new asset (eg. a shot) to a bookmark.

See `addbookmarks.TemplatesWidget` for more information, the main widget
responsible for listing, saving and expanding zip template files.

"""
import _scandir
from PySide2 import QtWidgets, QtCore, QtGui

import bookmarks.common as common
import bookmarks.log as log
import bookmarks.images as images
import bookmarks.common_ui as common_ui
import bookmarks.shotgun as shotgun
import bookmarks.bookmark_db as bookmark_db
import bookmarks.settings as settings


_create_shot_task_instance = None
_link_assets_instance = None


SHOTGUN_TYPES = (
    u'Asset',
    u'Sequence',
    u'Shot',
)


class TaskNode(QtCore.QObject):
    def __init__(self, data, parentNode=None, parent=None):
        super(TaskNode, self).__init__(parent=parent)
        self.data = data
        self._children = []
        self._parentNode = parentNode

        if parentNode:
            parentNode.addChild(self)

    @property
    def name(self):
        if self.data is None:
            return 'rootNode'
        return self.data['name']

    @property
    def fullname(self):
        if self.data is None:
            return 'rootNode'
        return self.data['name']

    def removeSelf(self):
        """Removes itself from the parent's children."""
        if self.parentNode:
            if self in self.parentNode.children:
                idx = self.parentNode.children.index(self)
                del self.parentNode.children[idx]

    def removeChild(self, child):
        """Remove the given node from the children."""
        if child in self.children:
            idx = self.children.index(child)
            del self.children[idx]

    def addChild(self, child):
        """Add a child node."""
        self.children.append(child)

    @property
    def children(self):
        """Children of the node."""
        return self._children

    @property
    def childCount(self):
        """Children of the this node."""
        return len(self._children)

    @property
    def parentNode(self):
        """Parent of this node."""
        return self._parentNode

    @parentNode.setter
    def parentNode(self, node):
        self._parentNode = node

    def getChild(self, row):
        """Child at the provided index/row."""
        if row < self.childCount:
            return self.children[row]
        return None

    @property
    def row(self):
        """Row number of this node."""
        if self.parentNode:
            return self.parentNode.children.index(self)
        return None


class TaskModel(QtCore.QAbstractItemModel):
    """Simple tree model to browse the data-structure of the alembic."""

    def __init__(self, name, node, parent=None):
        super(TaskModel, self).__init__(parent=parent)
        self._name = name
        self._rootNode = node
        self._originalRootNode = node

    @property
    def rootNode(self):
        """ The current root node of the model """
        return self._rootNode

    @rootNode.setter
    def rootNode(self, node):
        """ The current root node of the model """
        self._rootNode = node

    @property
    def originalRootNode(self):
        """ The original root node of the model """
        return self._originalRootNode

    def rowCount(self, parent):
        """Row count."""
        if not parent.isValid():
            parentNode = self.rootNode
        else:
            parentNode = parent.internalPointer()
        return parentNode.childCount

    def columnCount(self, parent):  # pylint: disable=W0613
        """Column count."""
        return 1

    def parent(self, index):
        """The parent of the node."""
        node = index.internalPointer()
        if not node:
            return QtCore.QModelIndex()

        parentNode = node.parentNode

        if not parentNode:
            return QtCore.QModelIndex()
        elif parentNode == self.rootNode:
            return QtCore.QModelIndex()
        elif parentNode == self.originalRootNode:
            return QtCore.QModelIndex()

        return self.createIndex(parentNode.row, 0, parentNode)

    def index(self, row, column, parent):
        """Returns a QModelIndex()."""
        if not parent.isValid():
            parentNode = self.rootNode
        else:
            parentNode = parent.internalPointer()

        childItem = parentNode.getChild(row)
        if not childItem:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, childItem)

    def data(self, index, role):  # pylint: disable=W0613
        """Name data."""
        if not index.isValid():
            return None

        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            if node.data['type'] == 'Task':
                return node.data['name']
            if node.data['type'] == 'Step':
                return u'{}:  {}'.format(node.data['type'], node.data['name'])

        if role == QtCore.Qt.DecorationRole:
            if node.data['type'] == 'Task':
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'favourite', common.ADD, common.MARGIN())
                icon = QtGui.QIcon(pixmap)
                return icon
            if node.data['type'] == 'Step':
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'shotgun', None, common.MARGIN())
                icon = QtGui.QIcon(pixmap)
                return icon

        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(0, common.ROW_HEIGHT())
        return None

    def flags(self, index, parent=QtCore.QModelIndex()):
        node = index.internalPointer()
        if node.data['type'] == 'Task':
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if node.data['type'] == 'Step':
            return QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled


    def headerData(self, section, orientation, role):  # pylint: disable=W0613
        """Static header data."""
        return 'Name'

    def createIndexFromNode(self, node):
        """ Creates a QModelIndex based on a Node """
        if not node.parentNode:
            return QtCore.QModelIndex()

        if node not in node.parentNode.children:
            raise ValueError('Node\'s parent doesn\'t contain the node.')

        idx = node.parentNode.children.index(node)
        return self.createIndex(idx, 0, node)


class TaskTree(QtWidgets.QTreeView):

    def __init__(self, parent=None):
        super(TaskTree, self).__init__(parent=parent)
        self.data = None

        self.setHeaderHidden(False)
        self.setSortingEnabled(False)
        self.setItemsExpandable(True)
        self.setRootIsDecorated(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def set_data(self, data):
        self.data = data
        node = self.data_to_nodes()
        model = TaskModel('Tasks', node)
        self.setModel(model)
        self.set_root_node(model.rootNode)
        self.expandAll()

    def data_to_nodes(self):
        """Builds the internalPointer structure needed to represent the alembic archive."""
        def _get_children(node):
            for data in node.data['tasks']:
                node = TaskNode(data, parentNode=node)
                _get_children(node)

        rootNode = TaskNode(None)

        _data = {}
        for d in self.data:
            if d['step'] is not None:
                _data[d['step']['name']] = {
                    'name': d['step']['name'],
                    'id': d['step']['id'],
                    'type': d['step']['type'],
                    'tasks': [],
                }
                _data[d['step']['name']]['tasks'].append({
                    'name': d['content'],
                    'id': d['id'],
                    'type': d['type'],
                    'tasks': []
                })
            else:
                _data[d['content']] = {
                    'name': d['content'],
                    'id': d['id'],
                    'type': d['type'],
                    'tasks': []
                }
        ks = sorted(_data.keys())
        for k in ks:
            node = TaskNode(_data[k], parentNode=rootNode)
            _get_children(node)

        return rootNode

    def set_root_node(self, node):
        """ Sets the given Node as the root """
        if not node.children:
            return

        index = self.model().createIndexFromNode(node)
        if not index.isValid():
            return

        self.setRootIndex(index)
        self.model().rootNode = node

        index = self.model().createIndexFromNode(self.model().rootNode)
        self.setCurrentIndex(index)

    def reset_root_node(self):
        """Resets the root node to the initial node."""
        node = self.model().originalRootNode
        index = self.model().createIndex(0, 0, node)
        self.setRootIndex(index)
        self.setCurrentIndex(index)
        self.model().rootNode = self.model().originalRootNode

    def keyPressEvent(self, event):
        event.ignore()


class CreateShotTaskVersion(QtWidgets.QDialog):
    """Widget used to add a new version to a task.

    """
    def __init__(self, path, parent=None):
        global _create_shot_task_instance
        _create_shot_task_instance = self

        super(CreateShotTaskVersion, self).__init__(parent=parent)
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
        settings.local_settings.setValue(u'shotgun/user', text)

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
        self.task_picker = TaskTree(parent=self)
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
        row = common_ui.add_row(u'Select task', height=common.HEIGHT() * 0.6, parent=grp)
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

    @QtCore.Slot()
    def init_values(self):
        try:
            project_id = bookmark_db.get_property(u'shotgun_id')
            if project_id is None:
                raise RuntimeError('Project ID is not set.')

            sg_id = bookmark_db.get_property(u'shotgun_id', asset_property=True)
            if sg_id is None:
                raise RuntimeError('ID is not set.')
            sg_type = bookmark_db.get_property(u'shotgun_type')
            if sg_type is None:
                raise RuntimeError('Shotgun entity type is not set.')

            domain = bookmark_db.get_property(u'shotgun_domain')
            script_name = bookmark_db.get_property(u'shotgun_scriptname')
            api_key = bookmark_db.get_property(u'shotgun_api_key')

            # Get task data

            with shotgun.init_sg(domain, script_name, api_key) as _:
                data = shotgun.find_tasks(
                    sg_type,
                    sg_id
                )
                users = shotgun.find_users()
            if not data:
                raise RuntimeError(u'Could not find any tasks for ID {}'.format(sg_id))
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
                        self.user_picker.addItem(user['name'], userData=user['id'])
                    elif 'id' in user:
                        name = 'HumanUser{}'.format(user['id'])
                        self.user_picker.addItem(name, userData=user['id'])
                    else:
                        continue


                self.user_picker.blockSignals(False)
                prev = settings.local_settings.value(u'shotgun/user')
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
        except Exception as e:
            common_ui.ErrorBox('An error occured', unicode(e)).open()
            log.error('An error occured.')
            raise

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

            task_id = node.data['id']
            code = self.name_editor.text()
            if not code:
                common_ui.MessageBox(u'Name not entered.', u'').open()
                return

            description = self.description_editor.text()
            path_to_movie = self.path_to_movie_editor.text()
            path_to_frames = self.path_to_frames_editor.text()
            if not any((path_to_movie, path_to_frames)):
                common_ui.MessageBox(u'You must provide either a path to a movie or a path to a frame file.', u'').open()
                return
            user = self.user_picker.currentData()
            if not user:
                common_ui.MessageBox(u'Select a user before continuing.', u'').open()
                return

            domain = bookmark_db.get_property(u'shotgun_domain')
            script_name = bookmark_db.get_property(u'shotgun_scriptname')
            api_key = bookmark_db.get_property(u'shotgun_api_key')

            with shotgun.init_sg(domain, script_name, api_key):
                p = common_ui.MessageBox(u'Adding version...', u'Should not take too long!')
                p.open()

                QtWidgets.QApplication.instance().processEvents()
                try:
                    entity = shotgun.add_shot_version(
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


class PickShotCombobox(QtWidgets.QComboBox):
    """Shotgun shot picker."""

    def __init__(self, parent=None):
        super(PickShotCombobox, self).__init__(parent=parent)
        self.setMinimumWidth(common.WIDTH() * 0.5)
        self.setFixedHeight(common.ROW_HEIGHT() * 1)

    @QtCore.Slot()
    def load_projects(self):
        """Loads the list of available projects from the shotgun server."""
        with shotgun.init_sg(
            self.parent().domain,
            self.parent().script_name,
            self.parent().api_key,
        ):
            items = shotgun.find_projects()
            for item in sorted(items, key=lambda x: x['name']):
                self.addItem(
                    item[u'name'],
                    userData=item[u'id']
                )
        self._decorate()

    @QtCore.Slot()
    def load_entities(self):
        """Loads the list of available items from the shotgun server."""
        with shotgun.init_sg(
            self.parent().domain,
            self.parent().script_name,
            self.parent().api_key,
        ):
            try:
                items = shotgun.find_entities(
                    self.parent().sg_type,
                    self.parent().project_id
                )
            except Exception as e:
                common_ui.ErrorBox('Could not load shotgun data.', unicode(e)).open()
                log.error('find_entities() failed.')
                raise

            for item in sorted(items, key=lambda x: x[u'code']):
                self.addItem(
                    item[u'code'].upper(),
                    userData=item[u'id']
                )
        self._decorate()

    def _decorate(self):
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', None, common.MARGIN() * 2)
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            self.model().setData(
                index,
                QtCore.QSize(common.ROW_HEIGHT() * 0.66, common.ROW_HEIGHT() * 0.66),
                QtCore.Qt.SizeHintRole,
            )
            self.model().setData(
                index,
                QtGui.QIcon(pixmap),
                QtCore.Qt.DecorationRole,
            )

    @QtCore.Slot()
    def select_candidate(self):
        """Try and select an item from the list matching the local asset's name."""
        name = self.parent().local_asset.lower()
        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if name.lower() in index.data(QtCore.Qt.DisplayRole).lower():
                self.setCurrentIndex(n)
                return




class LinkToShotgunWidget(QtWidgets.QDialog):
    """Allows the user to select a shotgun item from a dropdown menu.

    """
    linkRequested = QtCore.Signal(unicode, int)

    def __init__(self, local_asset, sg_type, domain, script_name, api_key, project_id=None, parent=None):
        super(LinkToShotgunWidget, self).__init__(parent=parent)
        self.sg_type = sg_type
        self.local_asset = local_asset

        self.domain = domain
        self.script_name = script_name
        self.api_key = api_key
        self.project_id = project_id

        self.picker = None
        self.link_button = None

        self.init_timer = QtCore.QTimer(parent=self)
        self.init_timer.setInterval(250)
        self.init_timer.setSingleShot(True)

        self._create_UI()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.link_button.clicked.connect(self.action)

        if self.sg_type == 'Project':
            self.init_timer.timeout.connect(self.picker.load_projects)
        elif self.sg_type.lower() in ('sequence', 'shot', 'asset'):
            self.init_timer.timeout.connect(self.picker.load_entities)
        self.init_timer.timeout.connect(self.picker.select_candidate)

    def _create_UI(self):
        common.set_custom_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN() * 2
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(None, parent=self)

        label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(
            'shotgun', None, common.MARGIN() * 2)
        label.setPixmap(pixmap)
        row.layout().addWidget(label, 0)

        label = common_ui.PaintedLabel(
            u'Link {} to Shotgun'.format(self.local_asset))
        row.layout().addWidget(label, 0)

        self.picker = PickShotCombobox(parent=self)
        self.link_button = common_ui.PaintedButton(u'Link with Shotgun')

        self.layout().addWidget(self.picker, 1)
        self.layout().addStretch(1)
        self.layout().addWidget(self.link_button)

    def showEvent(self, event):
        self.init_timer.start()

    @QtCore.Slot()
    def action(self):
        id = self.picker.currentData()
        name = self.picker.currentText()
        self.linkRequested.emit(name, id)
        self.done(0)


class LinkAssets(QtWidgets.QDialog):

    def __init__(self, assets, parent=None):
        global _link_assets_instance
        _link_assets_instance = self

        super(LinkAssets, self).__init__(parent=parent)

        self.group = None
        self.scrollarea = None
        self.assets = {}

        self.load_timer = QtCore.QTimer(parent=self)
        self.load_timer.setSingleShot(True)
        self.load_timer.setInterval(250)

        for asset in assets:
            self.assets[asset.lower()] = None

        self._create_UI()
        self._connect_signals()

    def _create_UI(self):
        self.link_button = common_ui.PaintedButton(u'Link with Shotgun')
        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)

        QtWidgets.QVBoxLayout()

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

        def add_asset(k, parent):
            k = k.lower()
            row = common_ui.add_row(k.upper(), parent=parent)
            self.assets[k] = QtWidgets.QComboBox(parent=self)
            self.assets[k].addItem(u'Select...', userData=None)
            row.layout().addWidget(self.assets[k], 1)


        _add_title(u'shotgun', u'Link with Shotgun', self)
        o *= 0.5
        self.group = common_ui.get_group(parent=self)
        self.group.layout().setSpacing(0)
        self.group.layout().setContentsMargins(o, o, o, o)

        for k in sorted(self.assets.keys()):
            add_asset(k, self.group)

        self.layout().addWidget(self.scrollarea)
        self.scrollarea.setWidget(self.group)
        self.layout().addWidget(self.link_button)

    def _connect_signals(self):
        self.link_button.clicked.connect(self.action)
        self.load_timer.timeout.connect(self.init_data)

    @QtCore.Slot()
    def action(self):
        """Set selected values to the database.

        """
        server = settings.ACTIVE[u'server']
        job = settings.ACTIVE[u'job']
        root = settings.ACTIVE[u'root']

        if not all(
            (server, job, root)
        ):
            s = u'Active bookmark not set'
            common_ui.ErrorBox(
                s, u''
            ).open()
            log.error(s)
            raise RuntimeError(s)


        db = bookmark_db.get_db(server, job, root)
        with db.transactions():
            for k in self.assets:
                k = k.lower()
                if self.assets[k].currentData() is None:
                    continue

                shotgun_id = self.assets[k].currentData(role=QtCore.Qt.UserRole)
                shotgun_type = self.assets[k].currentData(role=QtCore.Qt.UserRole + 1)
                shotgun_name = self.assets[k].currentData(role=QtCore.Qt.UserRole + 2)

                if not all((
                    shotgun_id is not None,
                    shotgun_type is not None,
                    shotgun_name is not None,
                )):
                    continue

                _k = u'/'.join((server, job, root, k))
                db.setValue(_k, u'shotgun_id', shotgun_id)
                db.setValue(_k, u'shotgun_type', shotgun_type)
                db.setValue(_k, u'shotgun_name', shotgun_name)


        self.done(QtWidgets.QDialog.Accepted)

    def init_data(self):
        """Loads data from shotgun an maps it to the UI."""
        try:
            domain = bookmark_db.get_property(u'shotgun_domain')
            if domain is None:
                raise RuntimeError('Shotgun Domain not set')

            script_name = bookmark_db.get_property(u'shotgun_scriptname')
            if script_name is None:
                raise RuntimeError('Shotgun Script Name not set')

            api_key = bookmark_db.get_property(u'shotgun_api_key')
            if api_key is None:
                raise RuntimeError('Shotgun API Key not set')

            project_id = bookmark_db.get_property(u'shotgun_id')
            if project_id is None:
                raise RuntimeError('Project ID is not set.')

        except Exception as e:
            common_ui.ErrorBox(
                u'A required Shotgun information was not found.',
                u'You can enter the missing information on the Bookmark\'s property page.' + '\n' + unicode(e)
            ).open()
            log.error('An error occured.')
            raise


        def key(x):
            if 'name' in x:
                return x['name']
            if 'code' in x:
                return x['code']
            return x['id']

        # Let's build our data
        # We will wrap all the reuired entities into a single QT5 model
        model = QtGui.QStandardItemModel()
        item = QtGui.QStandardItem(u'Select...')
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        model.appendRow(item)

        for sg_type in (u'Shot', u'Sequence', u'Asset'):
            with shotgun.init_sg(domain, script_name, api_key):
                item = QtGui.QStandardItem(u'------------' + sg_type + u's' + u'------------')
                item.setFlags(QtCore.Qt.NoItemFlags)
                model.appendRow(item)

                items = []
                try:
                    items = shotgun.find_entities(sg_type, project_id)
                except Exception as e:
                    common_ui.ErrorBox('Could not load shotgun data.', unicode(e)).open()
                    log.error('find_entities() failed.')

                    item = QtGui.QStandardItem('    Error loading ' + sg_type + 's')
                    item.setFlags(QtCore.Qt.NoItemFlags)
                    model.appendRow(item)

                    continue

                if not items:
                    continue

                items = sorted(items, key=key)
                for sg_item in items:
                    if 'name' in sg_item:
                        k = sg_item['name']
                    elif 'code' in sg_item:
                        k = sg_item['code']
                    else:
                        k = '{}{}'.format(
                            sg_item['type'],
                            sg_item['id']
                        )
                    item = QtGui.QStandardItem()
                    item.setData(k.upper(), role=QtCore.Qt.DisplayRole)
                    item.setData(sg_item['id'], role=QtCore.Qt.UserRole)
                    item.setData(sg_item['type'], role=QtCore.Qt.UserRole + 1)
                    item.setData(k, role=QtCore.Qt.UserRole + 2)
                    item.setData(
                        QtCore.QSize(common.ROW_HEIGHT() * 0.66, common.ROW_HEIGHT() * 0.66),
                        role=QtCore.Qt.SizeHintRole
                    )
                    item.setFlags(
                        QtCore.Qt.ItemIsEnabled |
                        QtCore.Qt.ItemIsSelectable |
                        QtCore.Qt.ItemNeverHasChildren
                    )
                    model.appendRow(item)

        # Let's apply the model to the QCombobox choices
        for k in self.assets:
            self.assets[k.lower()].setModel(model)

        # Auto select appropiate items
        for k in self.assets:
            k = k.lower()
            model = self.assets[k].model()
            for n in xrange(model.rowCount()):
                item = model.item(n, 0)
                name = item.data(QtCore.Qt.DisplayRole)
                if k in name.lower():
                    self.assets[k].setCurrentText(name)
                    break


    def showEvent(self, event):
        self.load_timer.start()

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())


if __name__ == '__main__':
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])
    w = CreateShotTaskVersion(
        u'//aka03/pjct01/frills/data/shot/060_0060/captures/frl_060_0060_block_gw_v0003/frl_060_0060_block_gw_v0003.1001.png'
    )
    w.open()
    app.exec_()
