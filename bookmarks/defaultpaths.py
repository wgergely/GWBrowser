# -*- coding: utf-8 -*-
"""Contains information about the file structure of an asset.

Each asset is made up of a series of `task folders`. All folders located in the
root of the asset is considered a `task folder` and should correspond to data
types and/or a different stage of an asset's production cycle.

A list of some arbitary task folders are defined by `TASK_FOLDERS`. Bookmarks
can suggest save locations for files depending their extension and mode, defined
by `SCENE_FOLDERS` and `EXPORT_FOLDERS`.

When saving, names are generated based on the value of `FILE_NAME_PATTERN`.

`FORMAT_FILTERS` contains the list of valid extensions for each `task folder`.
It is used, for instance, by the `FilesModel` to ignore invalid extensions - eg.
to make sure that the `render` folder does not contain scene files, etc.

"""
import re
import OpenImageIO
from . import settings


def sort(s):
    return u','.join(sorted(re.findall(r"[\w']+", s)))


NoFilter = 0
SceneFilter = 0b10000000
OpenImageIOFilter = 0b01000000
ExportFilter = 0b00100000
MiscFilter = 0b00010000
AdobeFilter = 0b00001000

FORMAT_FILTERS = {
    SceneFilter: {
        u'name': u'SceneFilter',
        u'description': u'Scene file formats',
        u'default': sort(u'c4d,hud,hip,hiplc,hipnc,ma,mb,nk,nk~,mocha,rv,autosave'),
        u'value': None,
    },
    OpenImageIOFilter: {
        u'name': u'OpenImageIOFilter',
        u'description': u'Image formats understood by OpenImageIO',
        u'default': sort(OpenImageIO.get_string_attribute(u'extension_list')),
        u'value': None,
    },
    ExportFilter: {
        u'name': u'ExportFilter',
        u'description': u'CG cache formats',
        u'default': sort(u'abc,ass,bgeo,fbx,geo,ifd,obj,rs,sc,sim,vdb,usd,usda,usdc,usdz'),
        u'value': None,
    },
    MiscFilter: {
        u'name': u'MiscFilter',
        u'description': u'Miscellaneous file formats',
        u'default': sort(u'txt,pdf,zip,rar,exe,app,m4v,m4a,mov,mp4'),
        u'value': None,
    },
    AdobeFilter: {
        u'name': u'AdobeFilter',
        u'description': u'Adobe Creative Cloud scene formats',
        u'default': sort(u'aep,ai,eps,fla,ppj,prproj,psb,psd,psq,xfl'),
        u'value': None,
    },
}
"""Defines a list of file extensions, a description and the search filter
associated with the list."""


TASK_FOLDERS = {
    u'export': {
        u'value': None,
        u'default': u'export',
        u'description': u'Alembic, FBX, OBJ and other CG caches',
        u'filter': SceneFilter | OpenImageIOFilter | ExportFilter | MiscFilter | AdobeFilter,
    },
    u'data': {
        u'value': None,
        u'default': u'data',
        u'description': u'Temporary and system files',
        u'filter': SceneFilter | OpenImageIOFilter | ExportFilter | MiscFilter | AdobeFilter,
    },
    u'reference': {
        u'value': None,
        u'default': u'reference',
        u'description': u'Asset references',
        u'filter': SceneFilter | OpenImageIOFilter | ExportFilter | MiscFilter | AdobeFilter,
    },
    u'render': {
        u'value': None,
        u'default': u'render',
        u'description': u'2D and 3D renders',
        u'filter': OpenImageIOFilter,
    },
    u'scene': {
        u'value': None,
        u'default': u'scene',
        u'description': u'2D and 3D projects and scenes',
        u'filter': SceneFilter | AdobeFilter,
    },
    u'final': {
        u'value': None,
        u'default': u'final',
        u'description': u'Comps and final renders',
        u'filter': OpenImageIOFilter,
    },
    u'image': {
        u'value': None,
        u'default': u'image',
        u'description': u'2D and 3D textures',
        u'filter': OpenImageIOFilter,
    },
    u'other': {
        u'value': None,
        u'default': u'other',
        u'description': u'Miscellaneous files',
        u'filter': NoFilter,
    },
}
"""A list of common task folders and the list of extensions we accept."""

SCENE_FOLDERS = {
    u'anim': {
        u'value': None,
        u'default': u'{scene}/anim',
        u'description': u'2D and 3D animation scenes'
    },
    u'fx': {
        u'value': None,
        u'default': u'{scene}/fx',
        u'description': u'FX scenes'
    },
    u'sfx': {
        u'value': None,
        u'default': u'{scene}/audio',
        u'description': u'Sound and music scenes'
    },
    u'comp': {
        u'value': None,
        u'default': u'{scene}/comp',
        u'description': u'Compositing scenes'
    },
    u'block': {
        u'value': None,
        u'default': u'{scene}/block',
        u'description': u'Layout, animatic and blocking scenes'
    },
    u'layout': {
        u'value': None,
        u'default': u'{scene}/layout',
        u'description': u'Layout, animatic and blocking scenes'
    },
    u'track': {
        u'value': None,
        u'default': u'{scene}/tracking',
        u'description': u'Motion tracking scenes'
    },
    u'look': {
        u'value': None,
        u'default': u'{scene}/look',
        u'description': u'Lighting & visual development scenes'
    },
    u'model': {
        u'value': None,
        u'default': u'{scene}/model',
        u'description': u'Modeling & sculpting scenes'
    },
    u'rig': {
        u'value': None,
        u'default': u'{scene}/rig',
        u'description': u'Rigging and other technical scenes'
    },
    u'render': {
        u'value': None,
        u'default': u'{scene}/render',
        u'description': u'Render scenes'
    }
}
"""A list of common scene folders used by the file saver to save scene files."""


EXPORT_FOLDERS = {
    u'abc': {
        u'value': None,
        u'default': u'{export}/abc',
        u'description': u'Alembic caches'
    },
    u'obj': {
        u'value': None,
        u'default': u'{export}/obj',
        u'description': u'OBJ caches'
    },
    u'fbx': {
        u'value': None,
        u'default': u'{export}/fbx',
        u'description': u'FBX caches'
    },
    u'ass': {
        u'value': None,
        u'default': u'{export}/ass',
        u'description': u'ASS (Arnold) caches'
    },
    u'usd': {
        u'value': None,
        u'default': u'{export}/usd',
        u'description': u'USD caches'
    },
}
"""A list of common cache folders and the list of extensions we accept."""


FILE_NAME_PATTERN = u'{folder}/{prefix}_{asset}_{mode}_{custom}_{user}_{version}.{ext}'
"""Used by the file saver to generate a new valid file name."""


def get_description(item):
    """Returns the description associated with the given key."""
    if isinstance(item, (str, unicode)):
        item = item.lower()

    for items in (
        FORMAT_FILTERS,
        TASK_FOLDERS,
        SCENE_FOLDERS,
        EXPORT_FOLDERS
    ):
        for k, v in items.iteritems():
            if isinstance(k, (str, unicode)):
                k = k.lower()
            if item == k:
                return v['description']
    return u''


def load_saved_values():
    """Load and set value values stored in `local_settings`."""
    global FORMAT_FILTERS
    global TASK_FOLDERS
    global SCENE_FOLDERS
    global EXPORT_FOLDERS
    global FILE_NAME_PATTERN

    for idx, ITEM in enumerate(
        (FORMAT_FILTERS,  # 0
         TASK_FOLDERS,  # 1
         SCENE_FOLDERS,  # 2
         EXPORT_FOLDERS)  # 3
    ):
        for k in ITEM:
            val = settings.local_settings.value(
                u'defaultpaths/{0}/{1}'.format(idx, k))
            if isinstance(val, (str, unicode)) and val:
                ITEM[k][u'value'] = expand_tokens(val)
            else:
                ITEM[k][u'value'] = expand_tokens(ITEM[k][u'default'])

        val = settings.local_settings.value(u'defaultpaths/filenamepattern')
        if isinstance(val, (str, unicode)) and val:
            FILE_NAME_PATTERN = val


def expand_tokens(s):
    """Expand any expandable tokens in the current values."""
    return s.format(
        export=TASK_FOLDERS[u'export'][u'value'],
        data=TASK_FOLDERS[u'data'][u'value'],
        reference=TASK_FOLDERS[u'reference'][u'value'],
        render=TASK_FOLDERS[u'render'][u'value'],
        scene=TASK_FOLDERS[u'scene'][u'value'],
        final=TASK_FOLDERS[u'final'][u'value'],
        image=TASK_FOLDERS[u'image'][u'value'],
        other=TASK_FOLDERS[u'other'][u'value'],
    )


def can_accept_extension(ext, task_folder):
    """Checks if the given `extension` can be accepted by `task folder`.

    Args:
        ext (unicode): A file extension.
        task_folder (unicode): A folder name.

    Returns:
        bool: True if the extension is valid.

    """
    task_folder = task_folder.lower()
    task_folder = next(
        (TASK_FOLDERS[f] for f in TASK_FOLDERS if f == task_folder), None)

    # If there's no filter is defined for `task_folder` accept all extensions
    if task_folder is None:
        return True

    for flag in FORMAT_FILTERS:
        if task_folder[u'filter'] & flag:
            if FORMAT_FILTERS[flag][u'value'] == u'*':
                return True
            if ext.lower() in FORMAT_FILTERS[flag][u'value']:
                return True

    return False


def get_task_folder_extensions(task_folder):
    """Get all valid extensions for the given task folder."""
    task_folder = task_folder.lower()
    flag = next(
        (v['filter']
         for v in TASK_FOLDERS.values() if v[u'value'] == task_folder),
        None
    )
    if not flag:
        return None
    return frozenset(get_extensions(flag))


def get_extensions(flag):
    global FORMAT_FILTERS

    e = []
    for f in FORMAT_FILTERS:
        if not (f & flag):
            continue
        if not isinstance(FORMAT_FILTERS[f][u'value'], (str, unicode)):
            continue
        e += FORMAT_FILTERS[f][u'value'].split(u',')
    return sorted(e)


def save_value(data, key, value):
    """Saves the given data/key/value to `local_settings`."""
    idx = None
    if data == FILE_NAME_PATTERN:
        settings.local_settings.setValue(
            u'defaultpaths/filenamepattern', value)

    if data == FORMAT_FILTERS:
        idx = 0
    elif data == TASK_FOLDERS:
        idx = 1
    elif data == SCENE_FOLDERS:
        idx = 2
    elif data == EXPORT_FOLDERS:
        idx = 3

    if idx is None:
        return

    settings.local_settings.setValue(
        u'defaultpaths/{}/{}'.format(idx, key), value)
    data[key][u'value'] = sort(value)


load_saved_values()
