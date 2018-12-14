# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""Config file reader for maya assets.

The ConfigParser allows setting comments and custom properties
for individual scene files or assets.

Attributes:
    archived (bool):            The status of the current item.
    description (str):          The description of the current item.

To retrieve the config file path, or the associated thumbnail you can use
getConfigPath() or getThumbnailPath().

"""

import os
import re
import sys
from ConfigParser import ConfigParser

from PySide2 import QtCore

import mayabrowser.common as common

# Flags
NoFlag = 0
MarkedAsArchived = 0b100000000
MarkedAsFavourite = 0b1000000000
MarkedAsActive = 0b10000000000

COMPANY = 'Glassworks'
APPLICATION = 'Browser'


class LocalSettings(QtCore.QSettings):
    """Used to store all user-specific settings, such as list of favourites,
    widget settings and filter modes.

    """
    def __init__(self, parent=None):
        super(LocalSettings, self).__init__(
            QtCore.QSettings.UserScope,
            COMPANY,
            APPLICATION,
            parent=parent
        )
        self.setDefaultFormat(QtCore.QSettings.NativeFormat)

    def value(self, *args, **kwargs):
        val = super(LocalSettings, self).value(*args, **kwargs)
        if not val:
            return None
        if isinstance(val, basestring):
            if val.lower() == 'true':
                return True
            elif val.lower() == 'false':
                return False
            elif val.lower() == 'none':
                return None
        return val

class AssetSettings(QtCore.QSettings):
    """Stores the settings
    Attributes:
        name (str):         The file-name.
        job (str):          The name of the current job. (Currently this is the name of the job folder.)
        root (str):         This is the location of the folder where the maya asset folders are located.

    """
    SECTIONS = ['activejob', 'favourites', 'mayawidget']


    def __init__(self, path, parent=None):
        self._path = path

        super(AssetSettings, self).__init__(
            self.ini_path(),
            QtCore.QSettings.IniFormat,
            parent=parent
        )
        self.setFallbacksEnabled(False)

    def ini_path(self):
        file_info = QtCore.QFileInfo(self._path)
        path = '{}/.browser/{}'.format(file_info.path(), re.sub(r'[\.]+', '_', file_info.fileName()))
        return r'{}.conf'.format(path)

    def thumbnail_path(self):
        file_info = QtCore.QFileInfo(self._path)
        path = '{}/.browser/{}'.format(file_info.path(), re.sub(r'[\.]+', '_', file_info.fileName()))
        return r'{}.png'.format(path)

    def value(self, *args, **kwargs):
        val = super(AssetSettings, self).value(*args, **kwargs)
        if not val:
            return None
        if isinstance(val, basestring):
            if val.lower() == 'true':
                return True
            elif val.lower() == 'false':
                return False
            elif val.lower() == 'none':
                return None
        return val



local_settings = LocalSettings()
"""An instance of the local configuration created when loading this module."""

if __name__ == '__main__':

    setting = AssetSettings('//gordo/jobs/tkwwbk_8077/build/2d_hair')
    # setting.setValue('description/description', 'Test note')
    print setting.value('description/description')
