# -*- coding: utf-8 -*-
"""Shotgun connection methods.
https://developer.shotgunsoftware.com/python-api/reference.html

"""
import sys
import contextlib
import functools
import traceback

import shotgun_api3

from PySide2 import QtCore, QtWidgets

from .. import bookmark_db
from .. import settings
from .. import common
from .. import common_ui
from .. import log


ProjectEntity = u'Project'
AssetEntity = u'Asset'
SequenceEntity = u'Sequence'
ShotEntity = u'Shot'
TaskEntity = u'Task'
StepEntity = u'Step'
UserEntity = u'HumanUser'
StorageEntity = u'LocalStorage'
PublishedFileTypeEntity = u'PublishedFileType'

IdColumn = u'id'
TypeColumn = u'type'
DescriptionColumn = u'description'

NameColumn = u'name'
CodeColumn = u'code'

VisibleColumn = u'visible'

CutDurationColumn = u'cut_duration'
CutInColumn = u'cut_in'
CutOutColumn = u'cut_out'
SGCutDurationColumn = u'sg_cut_duration'
SGCutInColumn = u'sg_cut_in'
SGCutOutColumn = u'sg_cut_out'

ContentColumn = u'content'
StepColumn = u'step'

IdRole = QtCore.Qt.UserRole + 1
TypeRole = IdRole + 1
NameRole = TypeRole + 1
CutDurationRole = NameRole + 1
CutInRole = CutDurationRole + 1
CutOutRole = CutInRole + 1
DescriptionRole = CutOutRole + 1


SGDomain = QtCore.Qt.UserRole + 1
SGKey = SGDomain + 1
SGScript = SGKey + 1

SGBookmarkEntityType = SGScript + 1
SGBookmarkEntityName = SGBookmarkEntityType + 1
SGBookmarkEntityID = SGBookmarkEntityName + 1

SGAssetEntityType = SGBookmarkEntityID + 1
SGAssetEntityName = SGAssetEntityType + 1
SGAssetEntityID = SGAssetEntityName + 1


SGProperties = {
    settings.ServerKey: None,
    settings.JobKey: None,
    settings.RootKey: None,
    settings.AssetKey: None,

    SGDomain: None,
    SGKey: None,
    SGScript: None,

    SGBookmarkEntityType: None,
    SGBookmarkEntityName: None,
    SGBookmarkEntityID: None,

    SGAssetEntityType: None,
    SGAssetEntityName: None,
    SGAssetEntityID: None,
}


ENTITY_URL = u'{domain}/detail/{shotgun_type}/{shotgun_id}'

DB_KEYS = {
    u'shotgun_id': {
        'type': bookmark_db.TABLES[bookmark_db.AssetTable]['shotgun_id']['type'],
        'role': IdRole,
        'columns': (IdColumn, ),
    },
    u'shotgun_type': {
        'type': bookmark_db.TABLES[bookmark_db.AssetTable]['shotgun_type']['type'],
        'role': TypeRole,
        'columns': (TypeColumn, ),
    },
    u'shotgun_name': {
        'type': bookmark_db.TABLES[bookmark_db.AssetTable]['shotgun_name']['type'],
        'role': NameRole,
        'columns': (NameColumn, CodeColumn),
    },
    u'cut_duration': {
        'type': bookmark_db.TABLES[bookmark_db.AssetTable]['cut_duration']['type'],
        'role': CutDurationRole,
        'columns': (CutDurationColumn, SGCutDurationColumn),
    },
    u'cut_in': {
        'type': bookmark_db.TABLES[bookmark_db.AssetTable]['cut_in']['type'],
        'role': CutInRole,
        'columns': (CutInColumn, SGCutInColumn),
    },
    u'cut_out': {
        'type': bookmark_db.TABLES[bookmark_db.AssetTable]['cut_out']['type'],
        'role': CutOutRole,
        'columns': (CutOutColumn, SGCutOutColumn),
    },
}


__SG_CONNECTIONS = {}

connecting_message = None


def columns():
    columns = ()
    for v in DB_KEYS.values():
        columns += v['columns']
    return list(set((columns)))


class Signals(QtCore.QObject):
    connectionAttemptStarted = QtCore.Signal()
    connectionSuccessful = QtCore.Signal()
    connectionFailed = QtCore.Signal(unicode)
    connectionClosed = QtCore.Signal()

    def __init__(self, parent=None):
        super(Signals, self).__init__(parent=parent)
        self._connect_signals()

    def _connect_signals(self):
        self.connectionAttemptStarted.connect(self.show_connecting_message)
        self.connectionSuccessful.connect(self.hide_connecting_message)
        self.connectionFailed.connect(self.hide_connecting_message)
        self.connectionClosed.connect(self.hide_connecting_message)

        self.connectionFailed.connect(self.show_error_message)

    def show_error_message(self, v):
        common_ui.ErrorBox(
            u'Shotgun encountered an error.',
            v
        ).open()

    def show_connecting_message(self):
        global connecting_message
        connecting_message = common_ui.MessageBox(u'Connecting to Shotgun...', no_buttons=True)
        connecting_message.open()
        QtWidgets.QApplication.instance().processEvents()

    def hide_connecting_message(self):
        try:
            connecting_message.hide()
            QtWidgets.QApplication.instance().processEvents()
        except:
            pass


signals = Signals()


def name_key(entity):
    """Returns the name of the given entity.

    Args:
        entity (dict):  A shotgun entity.

    Returns:
        unicode:    The entity's name.

    """
    if not isinstance(entity, dict):
        return u'Unknown entity'

    def has(column):
        return column in entity and entity[column] is not None

    if has(NameColumn):
        return entity[NameColumn]
    if has(CodeColumn):
        return entity[CodeColumn]
    if has(TypeColumn) and has(IdColumn):
        return u'{}{}'.format(
            entity[TypeColumn],
            entity[IdColumn],
        )
    if has(IdColumn):
        return u'Unknown Entity{}'.format(
            entity[IdColumn],
        )
    return u'Unknown entity'


def get_urls(sg_properties):
    """Returns a list of available urls based on the sg_properties provided.

    Returns:
        list:   A list of urls.

    """
    if not sg_properties[SGDomain]:
        return []

    urls = []
    urls.append(sg_properties[SGDomain])
    if all((sg_properties[SGBookmarkEntityID], sg_properties[SGBookmarkEntityType])):
        urls.append(
            ENTITY_URL.format(
                domain=sg_properties[SGDomain],
                shotgun_type=sg_properties[SGBookmarkEntityType],
                shotgun_id=sg_properties[SGBookmarkEntityID]
            )
        )
    if all((sg_properties[SGAssetEntityID], sg_properties[SGAssetEntityType])):
        urls.append(
            ENTITY_URL.format(
                domain=sg_properties[SGDomain],
                shotgun_type=sg_properties[SGAssetEntityType],
                shotgun_id=sg_properties[SGAssetEntityID]
            )
        )
    return urls


def is_valid(sg_properties, connection_only=False):
    if sg_properties is None:
        sg_properties = get_properties()

    if not all([sg_properties[k] for k in (SGDomain, SGKey, SGScript)]):
        return False
    if connection_only:
        return True
    if not all([sg_properties[k] for k in (SGBookmarkEntityType, SGBookmarkEntityName, SGBookmarkEntityID)]):
        return False
    if not sg_properties[settings.AssetKey]:
        return True
    if not all([sg_properties[k] for k in (SGAssetEntityType, SGAssetEntityName, SGAssetEntityID)]):
        return False
    return True


@common.debug
@common.error
def get_properties(server, job, root, asset, db=None):
    """Returns all saved Shotgun properties in the specified
    bookmark database.

    Args:
        server (unicode): The name of the `server`.
        job (unicode): The name of the `job`.
        root (unicode): The name of the `root`.
        asset (unicode): The name of the `asset`. Defaults to None.

    Returns:
        dict: A series of key/value pairs.

    """
    from .. import settings
    if not all((server, job, root)):
        return SGProperties.copy()

    sg_properties = SGProperties.copy()
    sg_properties[settings.ServerKey] = server
    sg_properties[settings.JobKey] = job
    sg_properties[settings.RootKey] = root

    if db is None:
        with bookmark_db.transactions(server, job, root) as db:
            sg_properties = _load_properties(db, asset, sg_properties)
    else:
        sg_properties = _load_properties(db, asset, sg_properties)
    return sg_properties


def _load_properties(db, asset, sg_properties):
    t = bookmark_db.BookmarkTable
    s = db.source()
    sg_properties[SGDomain] = db.value(s, 'shotgun_domain', table=t)
    sg_properties[SGKey] = db.value(s, 'shotgun_api_key', table=t)
    sg_properties[SGScript] = db.value(s, 'shotgun_scriptname', table=t)

    sg_properties[SGBookmarkEntityType] = db.value(s, 'shotgun_type', table=t)
    sg_properties[SGBookmarkEntityID] = db.value(s, 'shotgun_id', table=t)
    sg_properties[SGBookmarkEntityName] = db.value(s, 'shotgun_name', table=t)

    if not asset:
        return sg_properties

    t = bookmark_db.AssetTable
    s = db.source(asset)
    sg_properties[settings.AssetKey] = asset
    sg_properties[SGAssetEntityType] = db.value(s, 'shotgun_type', table=t)
    sg_properties[SGAssetEntityID] = db.value(s, 'shotgun_id', table=t)
    sg_properties[SGAssetEntityName] = db.value(s, 'shotgun_name', table=t)
    return sg_properties


@contextlib.contextmanager
def connection(sg_properties):
    """Context manager for connecting to Shotgun using an API Script.

    The context manager will connect to shotgun on entering and close the
    connection when exiting.

    Args:
        sg_properties (dict): The shotgun properties saved in the bookmark database.

    Yields:
        SGScriptConnection: A connected shotgun connection instance

    """
    if not is_valid(sg_properties, connection_only=True):
        s = u'Bookmark not yet configured to use Shotgun. You must enter a valid domain name, script name and api key before connecting.'
        signals.connectionFailed.emit(s)

    try:
        sg = _get_sg(
            sg_properties[SGDomain],
            sg_properties[SGScript],
            sg_properties[SGKey]
        )
        signals.connectionAttemptStarted.emit()
        sg.connect()
        signals.connectionSuccessful.emit()
        yield sg
    except Exception as e:
        # info = sys.exc_info()
        # if all(info):
        #     e = u''.join(traceback.format_exception(*info))
        # else:
        #     e = u''
        signals.connectionFailed.emit(u'{}'.format(e))
        raise
    else:
        sg.close()
        signals.connectionClosed.emit()


def _get_sg(*args):
    """Method for retrieving a thread specific `SGScriptConnection` instance,
    backed by a cache.

    Note:
        User authentication is not implemented currently.

    Args:
        domain (unicode): The base url or domain where the shotgun server is located.
        script (unicode): A valid Shotgun API Script's name.
        key (unicode):  A valid Shotgun Script's API Key.

    """
    for arg in args:
        if not isinstance(arg, unicode):
            raise TypeError(
                u'Expected <type \'unicode\'>, got {}'.format(type(arg)))

    key = _get_thread_key(*args)

    if key in __SG_CONNECTIONS:
        return __SG_CONNECTIONS[key]

    try:

        sg = SGScriptConnection(*args)
        __SG_CONNECTIONS[key] = sg
        return __SG_CONNECTIONS[key]
    except Exception as e:
        __SG_CONNECTIONS[key] = None
        if key in __SG_CONNECTIONS:
            del __SG_CONNECTIONS[key]
        log.error(e)
        raise


def _get_thread_key(*args):
    t = unicode(repr(QtCore.QThread.currentThread()))
    return u'/'.join(args) + t



class SGScriptConnection(shotgun_api3.Shotgun):
    """Customised `shotgun_api3.Shotgun` class used to authenticate via
    Shotgun API Scripts.

    Use the `connection()` context manager for retrieving the instance.

    """

    def __init__(self, domain, script, key, parent=None):
        super(SGScriptConnection, self).__init__(
            domain,
            script_name=script,
            api_key=key,
            login=None,
            password=None,
            connect=False,
            convert_datetimes_to_utc=True,
            http_proxy=None,
            ensure_ascii=False,
            ca_certs=None,
            sudo_as_login=None,
            session_token=None,
            auth_token=None
        )

        self.schema = {}

    def connect(self):
        self._get_schema()
        super(SGScriptConnection, self).connect()

    def _get_schema(self):
        if self.schema:
            return self.schema
        else:
            for entity_type in (
                ProjectEntity,
                AssetEntity,
                SequenceEntity,
                ShotEntity,
                TaskEntity,
                UserEntity,
                StorageEntity,
                PublishedFileTypeEntity
            ):
                self.schema[entity_type] = self.schema_field_read(
                    entity_type, field_name=None, project_entity=None)
        return self.schema

    def find_projects(self, columns=[IdColumn, NameColumn, u'visible', u'is_template', u'is_demo', u'is_template_project', 'archived']):
        """Get all active projects from Shotgun.

        """
        entities = self.find(ProjectEntity, [], columns)
        if not entities:
            return []

        _entities = []
        for entity in entities:
            if 'is_demo' in entity and entity['is_demo'] == True:
                continue
            if 'is_template_project' in entity and entity['is_template_project']:
                continue
            if 'visible' in entity and not entity['visible']:
                continue
            if 'archived' in entity and entity['archived']:
                continue
            if 'is_template' in entity and entity['is_template']:
                continue
            _entities.append(entity)
        return _entities

    def find_project(self, project_name, columns=[IdColumn, NameColumn]):
        """Find a Shotgun project using its name.

        Args:
            project_name (unicode): Project's name.

        Returns:
            list: A shotgun entity, or `None` if not found.

        """
        if not isinstance(project_name, unicode):
            raise TypeError(
                u'Invalid type, expected <type \'unicode\'>, got {}'.format(type(project_name)))

        _filter = [NameColumn, 'is', project_name]
        data = self.find_one(ProjectEntity, [_filter, ], columns)
        if not data:
            data = []
        return data

    def find_entities(self, project_id, entity_type, columns=[IdColumn, CodeColumn, TypeColumn, CutDurationColumn, CutInColumn, CutOutColumn]):
        """Find all entries in a project of the specified entity type.

        Args:
            project_id (type): Description of parameter `project_id`.
            entity_type (type): Description of parameter `entity_type`. Defaults to ShotEntity.

        Returns:
            list: A list of Shotgun entities, or `None` is not found.

        """
        if not isinstance(entity_type, unicode):
            raise TypeError(
                u'Invalid entity type, expected <type \'unicode\'>, got {}'.format(type(entity_type)))
        if not isinstance(project_id, int):
            raise TypeError(
                u'Invalid ID type, expected <type \'int\'>, got {}'.format(type(project_id)))

        _filter = ['project.Project.id', 'is', project_id]
        data = self.find(entity_type, [_filter, ], columns)
        if not data:
            data = []
        return data

    def find_tasks(self, entity_id, entity_type, columns=[IdColumn, ContentColumn, StepColumn]):
        """Find tasks associated with a given shotgun entity.

        """
        _filter = [u'entity', u'is', {u'type': entity_type, u'id': entity_id}]
        data = self.find(TaskEntity, [_filter, ], columns)
        if not data:
            data = []
        return data

    def find_users(self, columns=[IdColumn, TypeColumn, NameColumn]):
        data = self.find(UserEntity, [], columns)
        if not data:
            data = []
        return data

    def find_storage(self, columns=[IdColumn, TypeColumn, CodeColumn, u'description', u'linux_path', u'mac_path', u'windows_path']):
        data = self.find(StorageEntity, [], columns)
        if not data:
            data = []
        return data

    def find_published_file_types(self, columns=[IdColumn, TypeColumn, CodeColumn, u'short_name']):
        data = self.find(PublishedFileTypeEntity, [], columns)
        if not data:
            data = []
        return data

    def add_version(
        self,
        project_id,
        shot_id,
        task_id,
        code,
        description,
        path_to_movie,
        path_to_frames,
        user,
    ):
        """Adds a new version associated with a shot and task.

        """
        if project_id is None:
            raise RuntimeError('Shotgun Project ID is not set.')
        if shot_id is None:
            raise RuntimeError('Shotgun Shot ID is not set.')
        if task_id is None:
            raise RuntimeError('Shotgun Task ID is not set.')

        data = {
            'project': {'type': 'Project', 'id': int(project_id)},
            'code': code,
            'description': description,
            'sg_path_to_movie': path_to_movie,
            'sg_path_to_frames': path_to_frames,
            'sg_status_list': 'rev',
            'entity': {'type': 'Shot', 'id': int(shot_id)},
            'sg_task': {'type': 'Task', 'id': int(task_id)},
            'user': {'type': 'HumanUser', 'id': int(user)}
        }
        # 'user': {'type': 'HumanUser', 'id': 165} }
        try:
            entity = self.create('Version', data)
            log.success(u'Version successfully created.')
        except Exception as e:
            s = u'Failed to create new version.'
            common_ui.ErrorBox(s, unicode(e)).open()
            log.error(s)
            raise

        def _upload_movie(version_id):
            return self.upload(
                'Version',
                version_id,
                path_to_movie.replace(u'\\', u'/'),
                field_name='sg_uploaded_movie',
                display_name=QtCore.QFileInfo(path_to_movie).fileName(),
            )

        attachment_id = None
        if QtCore.QFileInfo(path_to_movie).exists():
            try:
                attachment_id = _upload_movie(entity['id'])
                common_ui.SuccessBox(u'Movie successfully uploaded.').open()
                log.success(u'Movie successfully uploaded.')
            except:
                try:
                    attachment_id = _upload_movie(entity['id'])
                except Exception as e:
                    s = u'Failed to upload attachment.'
                    common_ui.ErrorBox(s, unicode(e)).open()
                    log.error(s)
                    raise

        feedback = u'The version id is {}'.format(entity['id'])
        if attachment_id:
            feedback += '\nSuccesfully uploaded attachment id {}'.format(
                attachment_id)
        common_ui.OkBox(
            u'Version succesfully added.',
            u'The version id is {}'.format(entity['id'])
        ).open()

        return entity

    def add_publishedfile(
        self,
        project_id,
        shot_id,
        task_id,
        storage_id,
        type_id,
        code,
        description,
        path,
        version,
        user,
    ):
        """Used to add a new reviable version associated with a shot and task.

        The reviewable should in an ideal world be linked with a PublishFile
        entity.
        """

        if project_id is None:
            raise RuntimeError('Shotgun Project ID is not set.')
        if shot_id is None:
            raise RuntimeError('Shotgun Shot ID is not set.')
        if task_id is None:
            raise RuntimeError('Shotgun Task ID is not set.')

        data = {
            'project': {'type': 'Project', 'id': int(project_id)},
            'code': code,
            'name': code,
            'description': description,
            'path': {'url': QtCore.QUrl.fromLocalFile(path).url()},
            'path_cache': path,
            'sg_status_list': 'wtg',
            'entity': {'type': 'Shot', 'id': int(shot_id)},
            'task': {'type': 'Task', 'id': int(task_id)},
        }

        if user is not None:
            data['created_by'] = {'type': 'HumanUser', 'id': int(user)}

        if version is not None:
            try:
                data['version_number'] = int(version)
            except:
                pass

        if type_id is not None:
            data['published_file_type'] = {
                'type': 'PublishedFileType', 'id': int(type_id)}

        if storage_id is not None:
            data['path_cache_storage'] = {
                'type': 'LocalStorage', 'id': int(storage_id)}

        try:
            entity = self.create('PublishedFile', data)
            log.success(u'File successfully published.')
        except Exception as e:
            s = u'Failed to publish file.'
            common_ui.ErrorBox(s, unicode(e)).open()
            log.error(s)
            raise

        common_ui.OkBox(
            u'Version succesfully added.',
            u'The version id is {}'.format(entity['id'])
        ).open()
        return entity
