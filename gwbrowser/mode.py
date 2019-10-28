# -*- coding: utf-8 -*-
"""
"""
import os
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
            path = entry.path.replace(u'\\', u'/')
            if not path.endswith(u'.lock'):
                continue
            pid = path.strip(u'.lock').split(u'_').pop()
            pid = int(pid)
            if pid not in psutil.pids():
                QtCore.QFile(path).remove()
        return func(*args, **kwargs)
    return func_wrapper


def file_path():
    """The path to this session's lock-file."""
    return u'{tmp}/gwbrowser/gwbrowser_session_{pid}.lock'.format(
        tmp=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.TempLocation),
        pid=os.getpid()
    )


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
        path = entry.path.replace(u'\\', u'/')
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
