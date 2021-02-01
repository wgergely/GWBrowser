# -*- coding: utf-8 -*-
"""A list of common actions.

"""
import re
import os
import subprocess
import functools

from PySide2 import QtCore, QtWidgets, QtGui

from .. import settings
from .. import bookmark_db
from .. import common
from .. import threads
from .. import images

from . import shotgun


@common.debug
@common.error
def link_bookmark_entity(sg_properties):
    from ..shotgun.link_widget import LinkBookmarkWidget as editor
    widget = editor.show_editor(sg_properties)
    return widget


@common.debug
@common.error
def link_asset_entity(sg_properties):
    from ..shotgun.link_widget import LinkAssetWidget as editor
    widget = editor.show_editor(sg_properties)
    if not widget:
        return None
    return widget


@common.error
@common.debug
def upload_thumbnail(sg_properties, thumbnail_path):
    """Uploads an item thumbnail to shotgun.

    """
    if not shotgun.is_valid(sg_properties):
        return

    asset = sg_properties[settings.AssetKey]

    if asset is None:
        entity_type = sg_properties[shotgun.SGBookmarkEntityType]
        entity_id = sg_properties[shotgun.SGBookmarkEntityID]
    else:
        entity_type = sg_properties[shotgun.SGAssetEntityType]
        entity_id = sg_properties[shotgun.SGAssetEntityID]


    with shotgun.connection(sg_properties) as sg:
        sg.upload_thumbnail(
            entity_type,
            entity_id,
            thumbnail_path
        )

    from .. import common_ui
    from .. import log
    common_ui.OkBox(u'Shotgun thumbnail updated.').open()
    log.success(u'Thumbnail updated.')


def bookmark_configuration_changed(server, job, root):
    """Used to update BaseModels when the Shotgun configuration changes.

    """
    k = common.SGConfiguredRole

    v = shotgun.get_properties(server, job, root, None)
    domain = all((v[shotgun.SGDomain], v[shotgun.SGKey], v[shotgun.SGScript]))
    bookmark_entity = all((v[shotgun.SGBookmarkEntityType], v[shotgun.SGBookmarkEntityID], v[shotgun.SGBookmarkEntityName]))
    source = u'/'.join((server, job, root))

    from .. import actions
    from .. import main
    from ..lists import base

    if domain and bookmark_entity:
        actions.signals.bookmarkModelValueUpdated.emit(source, k, True)
    else:
        actions.signals.bookmarkModelValueUpdated.emit(source, k, False)

    # When a bookmark is disabled, all subsequent assets have to be
    # deactivated as well.
    widget = main.instance().stackedwidget.widget(base.AssetTab)
    model = widget.model().sourceModel()
    parent_path = model.parent_path()

    if not parent_path:
        return

    if server != parent_path[0]:
        return
    if job != parent_path[1]:
        return
    if root != parent_path[2]:
        return

    data = model.model_data()
    if not data:
        return

    with bookmark_db.transactions(server, job, root) as db:
        for idx, v in data.iteritems():
            sg_properties = shotgun.get_properties(server, job, root, v[common.ParentPathRole][3], db=db)
            v[k] = shotgun.is_valid(sg_properties)
            model.updateRow.emit(idx)

def asset_configuration_changed(server, job, root, asset):
    """Used to update BaseModels when the Shotgun configuration changes.

    """
    k = common.SGConfiguredRole

    v = shotgun.get_properties(server, job, root, asset)
    domain = all((v[shotgun.SGDomain], v[shotgun.SGKey], v[shotgun.SGScript]))
    bookmark_entity = all((v[shotgun.SGBookmarkEntityType], v[shotgun.SGBookmarkEntityID], v[shotgun.SGBookmarkEntityName]))
    asset_entity = all((v[shotgun.SGAssetEntityType], v[shotgun.SGAssetEntityID], v[shotgun.SGAssetEntityName]))
    source = u'/'.join((server, job, root, asset))

    from .. import actions
    if domain and bookmark_entity and asset_entity:
        actions.signals.assetModelValueUpdated.emit(source, k, True)
        return
    actions.signals.assetModelValueUpdated.emit(source, k, False)





@common.debug
@common.error
def show_add_shot_task_widget(sg_properties, path):
    from . import task_version
    w = task_version.CreateTaskVersion(sg_properties, path)
    w.open()


@common.debug
@common.error
def show_publish_widget(sg_properties, path):
    from . import task_publish
    w = task_publish.CreateTaskPublish(sg_properties, path)
    w.open()


@common.debug
@common.error
def test_shotgun_connection(sg_properties):
    with shotgun.connection(sg_properties) as sg:
        sg.find_projects()

        info = u''
        for k, v in sg.info().iteritems():
            info += u'{}: {}'.format(k, v)
            info += u'\n'

    from .. import common_ui
    common_ui.MessageBox(
        u'Successfully connected to Shotgun.',
        info
    ).open()

    return True
