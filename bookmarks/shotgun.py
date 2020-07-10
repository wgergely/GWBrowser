"""
Bookmarks' Shotgun integration methods.
https://developer.shotgunsoftware.com/python-api/reference.html
"""
import contextlib
import functools
import shotgun_api3

from PySide2 import QtCore

import bookmarks.common_ui as common_ui
import bookmarks.log as log


_instance = None


def sg_connection(func):
    """Check the Shotgun connection."""
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        if _instance is None:
            raise RuntimeError('init_sg() was never called.')
        return func(_instance, *args, **kwargs)
    return func_wrapper


@contextlib.contextmanager
def init_sg(
    domain,
    script_name,
    api_key,
):
    global _instance
    try:
        sg = shotgun_api3.Shotgun(
            domain,
            script_name=script_name,
            api_key=api_key
        )
        sg.connect()

        _instance = sg
        yield sg
    except:
        _instance = None
        raise
    finally:
        if _instance is not None:
            _instance.close()
        _instance = None


@sg_connection
def find_projects(sg):
    """Get all projects on Shotgun"""
    fields = ['id', 'name']
    return sg.find(
        'Project',
        [],
        fields
    )


@sg_connection
def find_project(sg, project):
    """Find a project based on the project's name."""
    if _instance is None:
        raise RuntimeError('init_sg() was never called.')
    v = sg.find_one(
        'Project',
        [
            [u'name', u'is', project],
        ],
        [u'id', u'name', u'type']
    )
    return v


@sg_connection
def find_entities(sg, sg_entity, project_id):
    """List all elements associated with the given project.

    """
    if _instance is None:
        raise RuntimeError('init_sg() was never called.')
    v = sg.find(
        sg_entity,
        [
            ["project.Project.id", "is", int(project_id)],
        ],
        [u'id', u'code', u'type', 'sg_cut_duration', 'sg_cut_in', 'sg_cut_out'],
    )
    return v


@sg_connection
def find_tasks(sg, sg_type, id):
    filters = [
        ['entity', 'is', {'type': sg_type, 'id': int(id)}],
    ]
    data = sg.find(
        u'Task',
        filters,
        [u'id', 'content', 'step'],
    )
    return data


@sg_connection
def add_version(
    sg,
    project_id,
    shot_id,
    task_id,
    code,
    description,
    path_to_movie,
    path_to_frames,
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
        entity = sg.create('Version', data)
        log.success(u'Version successfully created.')
    except Exception as e:
        s = u'Failed to create new version.'
        common_ui.ErrorBox(s, unicode(e)).open()
        log.error(s)
        raise

    def _upload_movie(version_id):
        return sg.upload(
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


@sg_connection
def add_publishedfile(
    sg,
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
        data['published_file_type'] = {'type': 'PublishedFileType', 'id': int(type_id)}

    if storage_id is not None:
        data['path_cache_storage'] = {'type': 'LocalStorage', 'id': int(storage_id)}

    try:
        entity = sg.create('PublishedFile', data)
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


@sg_connection
def find_users(sg):
    return sg.find('HumanUser', [], ['id', 'type', 'name'])

@sg_connection
def find_storage(sg):
    return sg.find('LocalStorage', [], ['id', 'type', 'code', 'description', 'linux_path', 'mac_path', 'windows_path'])

@sg_connection
def find_published_file_types(sg):
    return sg.find('PublishedFileType', [], ['id', 'type', 'code', 'short_name'])
