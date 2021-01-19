# -*- coding: utf-8 -*-
"""Shotgun RV commands module.

"""
import subprocess
from PySide2 import QtCore

from . import common
from . import log
from . import settings


@common.error
@common.debug
def push(path):
    """Uses `rvpush` to view a given footage."""

    rv_path = settings.local_settings.value(
        settings.SettingsSection, settings.RVKey)
    if not rv_path:
        s = u'Shotgun RV not found:\n'
        s += u'To push footage to RV, set RV\'s path in Preferences.'
        raise RuntimeError(s)

    rv_info = QtCore.QFileInfo(rv_path)
    if not rv_info.exists():
        s = u'Invalid Shotgun RV path set.\n'
        s += u'Make sure the currently set RV path is valid and try again!'
        raise RuntimeError(s)

    if common.get_platform() == u'win':
        rv_push_path = u'{}/rvpush.exe'.format(rv_info.path())
        if QtCore.QFileInfo(rv_push_path).exists():
            cmd = u'"{RV}" -tag {PRODUCT} url \'rvlink:// -reuse 1 -inferSequence -l -play -fps 25 -fullscreen -nofloat -lookback 0 -nomb \"{PATH}\"\''.format(
                RV=rv_push_path,
                PRODUCT=common.PRODUCT,
                PATH=path
            )
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            subprocess.Popen(cmd, startupinfo=startupinfo)
            log.success(u'Footage sent to RV.')
            log.success(u'Command used:')
            log.success(cmd)
    else:
        s = u'Function not yet implemented on this platform.'
        raise NotImplementedError(s)
