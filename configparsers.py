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
import sys
import ctypes
from ConfigParser import ConfigParser

from PySide2 import QtCore

# Flags
NoFlag = 0
MarkedAsArchived = 0b100000000
MarkedAsFavourite = 0b1000000000
MarkedAsActive = 0b10000000000


# ConfigParser is an old-style class!
class UnicodeConfigParser(object, ConfigParser):
    """Unicode capable ConfigParser."""
    SECTIONS = []

    def __init__(self, path):
        ConfigParser.__init__(self)
        self.path = path
        self.add_default_sections()

    def write(self, fp):
        """Patching ConfigParser to read/write unicode text."""
        if self._defaults:
            fp.write(u'[{}]\n'.format('DEFAULT'))
            for (key, value) in self._defaults.items():
                s = u'{key} = {value}\n'
                fp.write(s.format(key=key, value=str(
                    value).replace('\n', '\n\t')))
            fp.write(u'\n')
        for section in self._sections:
            fp.write(u'[{}]\n'.format(section))
            for (key, value) in self._sections[section].items():
                if key == '__name__':
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    key = ' = '.join(
                        (key, str(value).decode('utf-8').replace('\n', '\n\t')))
                fp.write(u'{}\n'.format(key))
            fp.write(u'\n')

    @staticmethod
    def getConfigPath(path):
        """Method to get the path of the ini file.
        Make sure to overwrite this in the subclass.

        """
        raise NotImplementedError(
            'getConfigPath() has to be overwritten in the subclass.')

    @staticmethod
    def set_hidden(path, hide=True):
        """Windows-only method to set the visibility of a file."""
        if sys.platform != 'win32':
            return

        path = os.path.normpath(path)
        if not os.path.isfile(path):
            return
        FILE_ATTRIBUTE_HIDDEN = 0x02
        FILE_ATTRIBUTE_NORMAL = 0x80

        ret = ctypes.windll.kernel32.SetFileAttributesW(
            ur'{}'.format(path),
            FILE_ATTRIBUTE_HIDDEN if hide else FILE_ATTRIBUTE_NORMAL
        )
        if not ret:
            raise ctypes.WinError()

    def read_ini(self):
        """Reads the default ini file into the parser object."""
        with open(self.getConfigPath(self.path), 'r') as f:
            f.seek(0)
            self.readfp(f)

    def write_ini(self):
        """Reads the default ini file into the parser object."""
        # https://stackoverflow.com/questions/13215716/ioerror-errno-13-permission-denied-when-trying-to-open-hidden-file-in-w-mod

        # Cannot write a hidden file, hence setting it as normal before writing.
        self.set_hidden(self.getConfigPath(self.path), hide=False)
        with open(self.getConfigPath(self.path), 'w') as f:
            self.write(f)
        self.set_hidden(self.getConfigPath(self.path))

    def add_default_sections(self):
        """Populates the ConfigParse with the default sections."""
        for section in self.SECTIONS:
            if not self.has_section(section):
                self.add_section(section)

    def _get_option(self, section, option, val):
        """Private convenience method to set an option."""
        if self.has_option(section, option):
            return self.get(section, option)
        self.set(section, option, '{}'.format(val))
        return self.get(section, option)


class Settings():
    """Module used to store application specific settings"""


class LocalSettings(QtCore.QSettings):
    """A custom ConfigParser object responsible for setting and getting
    workstation-specific settings.

    Attributes:
        server (str):       The path to the server
        job (str):          The name of the current job. (Currently this is the name of the job folder.)
        root (str):         This is the location of the folder where the maya asset folders are located.

    """
    SECTIONS = ['activejob', 'favourites', 'mayawidget']

    def __init__(self, parent=None):
        """Reads the ini if exists, otherwise sets server,job and root to `None`."""
        super(LocalSettings, self).__init__(
            QtCore.QSettings.SystemScope,
            'Glassworks',
            'Browser',
            parent=parent
        )
        self.setDefaultFormat(QtCore.QSettings.NativeFormat)


class CustomConfig(UnicodeConfigParser):
    """Baseclass for the Asset- and FileConfigs."""

    SECTIONS = ['properties', ]

    def __init__(self, path):
        super(CustomConfig, self).__init__(path)
        file_info = QtCore.QFileInfo(self.getConfigPath(self.path))
        if file_info.exists():
            self.read_ini()

    @property
    def description(self):
        """The description, or `note` of the item."""
        return self._get_option('properties', 'description', '')

    @description.setter
    def description(self, val):
        self.set(
            'properties',
            'description',
            '{}'.format(val.lstrip().rstrip())
        )

    @property
    def archived(self):
        """Archived property: marked items can be hidden from our list."""
        val = self._get_option('properties', 'archived', 0)
        if (val == 1) or (val is True) or (val == 'True') or (val == '1'):
            return True
        return False

    @archived.setter
    def archived(self, val):
        self.set('properties', 'archived', '{}'.format(val))


class AssetConfig(CustomConfig):
    """Reads and writes Maya asset properties."""

    def __init__(self, path):
        super(AssetConfig, self).__init__(path)

    @staticmethod
    def getConfigPath(path):
        """Returns the configuration file path."""
        fileInfo = QtCore.QFileInfo(path)
        return '{}/.config.ini'.format(fileInfo.filePath())

    @staticmethod
    def getThumbnailPath(path):
        """Returns the path to the asset's thumbnail."""
        fileInfo = QtCore.QFileInfo(path)
        return '{}/.thumbnail.png'.format(fileInfo.filePath())


class FileConfig(CustomConfig):
    """Reads and writes maya scene properties."""

    @staticmethod
    def getConfigPath(path):
        """Returns the path to the configuration file."""
        fileInfo = QtCore.QFileInfo(path)
        return '{}/.{}.ini'.format(
            fileInfo.path(),
            fileInfo.fileName()
        )

    @staticmethod
    def getThumbnailPath(path):
        fileInfo = QtCore.QFileInfo(path)
        return '{}/.{}.png'.format(
            fileInfo.path(),
            fileInfo.fileName()
        )


local_settings = LocalSettings()
"""An instance of the local configuration created when loading this module."""
