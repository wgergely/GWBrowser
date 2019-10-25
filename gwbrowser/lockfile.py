# -*- coding: utf-8 -*-
"""
"""
import os, base64
import time
from PySide2 import QtCore


def generate_id():
    return unicode(base64.b64encode(os.urandom(16)) + u'{}'.format(time.time()))

temp = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.TempLocation)
temp = u'{}/gwbrowser'.format(temp)
QtCore.QDir(temp).mkpath(u'.')
lock_path = u'{}/gwbrowser.lock'.format(temp)


def create_lockfile(id):
    """Creates a lockfile and saves the current the given id inside.

    Returns False if the lock exists already, `True` when the file is created
    successfully.

    """
    file_info = QtCore.QFileInfo(lock_path)
    if file_info.exists():
        print u'# GWBrowser: Lock exists already, skipping.'
        return False
    try:
        with open(lock_path, 'w') as f:
            f.write(id)
            print u'# GWBrowser: Lockfile created.'
            return True
    except:
        print u'# GWBrowser: Could not create the lockfile.'
        return False

def get_id():
    file_info = QtCore.QFileInfo(lock_path)

    if not file_info.exists():
        print u'# GWBrowser: Lockfile does not exist.'
        return u''

    with open(lock_path, 'r') as f:
        data = f.read()
        if not data:
            print u'# GWBrowser: Lockfile does not contain id data.'
            return u''
        return data

def lock(id, force=False):
    """Locks the current session."""
    if force:
        # We will forcefully re-set the lockfile
        if QtCore.QFile(lock_path).remove():
            print u'# GWBrowser: Lockfile removed.'
    if create_lockfile(id):
        return True
    if get_id() == id:
        return True
    return False


def unlock(id):
    if get_id() == id:
        # We won't unlock if we were the ones locking in the first place
        print u'# GWBrowser: Did not unlock.'
        return False
    if QtCore.QFile(lock_path).remove():
        print u'# GWBrowser: Lockfile removed.'


# get_id()
# id = generate_id()
# l = lock(id, force=True)
# id = generate_id()
# unlock(id)
