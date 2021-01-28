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


class Signals(QtCore.QObject):
    bookmarkLinked = QtCore.Signal(int, unicode)


signals = Signals()



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
def link_bookmark_entity(sg_properties):
    from ..shotgun import link_project_widget as editor
    widget = editor.show(sg_properties)
    widget.entitySelected.connect(signals.bookmarkLinked)
    return widget


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


@common.error
@common.debug
def upload_thumbnail(sg_properties, path):
    """Private slot used to upload the current thumbnail to shotgun.

    """
    with shotgun.connection(sg_properties) as sg:
        sg.upload_thumbnail(path)

    from .. import common_ui
    from .. import log
    common_ui.OkBox(u'Shotgun thumbnail updated.', u'').open()
    log.success(u'Thumbnail updated.')


def update_shotgun_configured(parent_paths, db, data):
    if len(parent_paths) == 3:
        sg_properties = shotgun.get_properties(
            server=parent_paths[0],
            job=parent_paths[1],
            root=parent_paths[2],
            asset=None,
            db=db
        )
    if len(parent_paths) == 4:
        sg_properties = shotgun.get_properties(
            server=parent_paths[0],
            job=parent_paths[1],
            root=parent_paths[2],
            asset=parent_paths[3],
            db=db
        )

    if len(parent_paths) == 3 or len(parent_paths) == 4:
        data[common.SGConfiguredRole] = shotgun.is_valid(sg_properties)
