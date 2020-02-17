# -*- coding: utf-8 -*-
"""
"""
import os
import re
import psutil
from functools import wraps
import gwbrowser.gwscandir as gwscandir
import gwbrowser.common as common
from PySide2 import QtCore


def prune(func):
    """Decorator removes stale lock-files from the GWBrowser's temp folder."""
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        lockfile_info = QtCore.QFileInfo(file_path())
        for entry in gwscandir.scandir(lockfile_info.path()):
            if entry.is_dir():
                continue

            match = re.match(ur'session_[0-9]+\.lock', entry.name.lower())
            if not match:
                continue

            path = entry.path
            pid = path.strip(u'.lock').split(u'_').pop()
            pid = int(pid)
            if pid not in psutil.pids():
                QtCore.QFile(path).remove()
        return func(*args, **kwargs)
    return func_wrapper


def file_path():
    """The path to this session's lock-file."""
    path = u'{}/{}/session_{}.lock'.format(
        QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        common.PRODUCT,
        os.getpid()
    )
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        file_info.dir().mkpath(u'.')
    return file_info.filePath()


@prune
def touch():
    """Creates a lockfile based on the current process' PID."""
    lockfile_info = QtCore.QFileInfo(file_path())
    lockfile_info.dir().mkpath(u'.')
    with open(file_path(), 'w+'):
        pass


@prune
def save():
    """Saves the current solo mode to the lockfile.

    This is to inform any new instances of GWBrowser that they need to start in
    solo mode if the a instance with a non-solo mode is already running.

    """
    lockfile_info = QtCore.QFileInfo(file_path())
    lockfile_info.dir().mkpath(u'.')
    with open(file_path(), 'w+') as f:
        f.write(u'{}'.format(int(CURRENT_MODE)))


@prune
def get_mode():
    lockfile_info = QtCore.QFileInfo(file_path())
    for entry in gwscandir.scandir(lockfile_info.path()):
        if entry.is_dir():
            continue
        path = entry.path
        if not path.endswith(u'.lock'):
            continue
        with open(path, 'r') as f:
            data = f.read()
        try:
            data = int(data.strip())
            if data == common.SynchronisedMode:
                return common.SoloMode
        except:
            pass
    return common.SynchronisedMode

CURRENT_MODE = get_mode()
