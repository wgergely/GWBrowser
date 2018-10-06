# -*- coding: utf-8 -*-
"""Config file reader for maya projects.

The ConfigParser allows setting comments and custom properties
for individual scene files or projects.

Attributes:
    archived (bool):            The status of the current item.
    description (str):          The description of the current item.

To retrieve the config file path, or the associated thumbnail you can use
getConfigPath() or getThumbnailPath().

"""
# pylint: disable=E1101, C0103, R0913, I1101

import os
import sys
import ctypes
from ConfigParser import ConfigParser

from PySide2 import QtCore

# Flags
NoFlag = 0
MarkedAsArchived = 1
MarkedAsFavourite = 2


class UnicodeConfigParser(object, ConfigParser):  # ConfigParser is an old-style class!
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
                fp.write(s.format(key=key, value=str(value).replace('\n', '\n\t')))
            fp.write(u'\n')
        for section in self._sections:
            fp.write(u'[{}]\n'.format(section))
            for (key, value) in self._sections[section].items():
                if key == '__name__':
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    key = ' = '.join((key, str(value).decode('utf-8').replace('\n', '\n\t')))
                fp.write(u'{}\n'.format(key))
            fp.write(u'\n')

    @staticmethod
    def getConfigPath(path):
        """Method to get the path of the ini file.
        Make sure to overwrite this in the subclass.

        """
        raise NotImplementedError('getConfigPath() has to be overwritten in the subclass.')

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


class LocalConfig(UnicodeConfigParser):
    """A custom ConfigParser object responsible for setting and getting
    workstation-specific settings.

    Attributes:
        server (str):       The path to the server
        job (str):          The name of the current job. (Currently this is the name of the job folder.)
        root (str):         This is the location of the folder where the maya project folders are located.

    """
    SECTIONS = ['activejob', 'favourites', 'mayawidget']

    def __init__(self, path=None):
        super(LocalConfig, self).__init__(path)

        if QtCore.QFileInfo(self.getConfigPath(path)).exists():
            self.read_ini()
        else:
            self.server = None
            self.job = None
            self.root = None
            self.write_ini()

    @staticmethod
    def getConfigPath(path):
        """Returns the path to the configuration file."""
        return '{}/browser_maya_config.ini'.format(QtCore.QDir.tempPath())

    def is_favourite(self, val):
        """Returns wheter the given file-name is set as a 'favourite'."""
        key = val.replace('.', '_').replace(' ', '')
        return self.has_option('favourites', key)

    def set_favourite(self, val):
        """Marks the name of the scene as favourite."""
        key = val.replace('.', '_').replace(' ', '')
        self.set('favourites', key, None)
        self.write_ini()

    def remove_favourite(self, val):
        """Removes a previously marked item from the favourites."""
        key = val.replace('.', '_').replace(' ', '')
        self.remove_option('favourites', key)
        self.write_ini()

    @property
    def server(self):
        """The currently set server path."""
        if self.has_option('activejob', 'server'):
            opt = self.get('activejob', 'server')
            if opt != 'None':
                return opt
            return None
        return None

    @server.setter
    def server(self, val):
        self.set('activejob', 'server', '{}'.format(val))
        self.write_ini()

    @property
    def job(self):
        """The currently set job name."""
        if self.has_option('activejob', 'job'):
            opt = self.get('activejob', 'job')
            if opt != 'None':
                return opt
            return None
        return None

    @job.setter
    def job(self, val):
        self.set('activejob', 'job', '{}'.format(val))
        self.write_ini()

    @property
    def root(self):
        """The currently set relative project root folder path."""
        if self.has_option('activejob', 'root'):
            opt = self.get('activejob', 'root')
            if opt != 'None':
                return opt
            return None
        return None

    @root.setter
    def root(self, val):
        self.set('activejob', 'root', '{}'.format(val))
        self.write_ini()

    @property
    def show_favourites_project_mode(self):
        """The saved show favourite projects mode."""
        opt = self._get_option(
            'mayawidget',
            'show_favourites_project_mode',
            False
        )
        return False if opt.lower() == 'false' else True

    @show_favourites_project_mode.setter
    def show_favourites_project_mode(self, val):
        self.set('mayawidget', 'show_favourites_project_mode', '{}'.format(val))
        self.write_ini()

    @property
    def show_archived_project_mode(self):
        """The saved show archived projects mode."""
        opt = self._get_option(
            'mayawidget', 'show_archived_project_mode', False)
        return False if opt.lower() == 'false' else True

    @show_archived_project_mode.setter
    def show_archived_project_mode(self, val):
        self.set('mayawidget', 'show_archived_project_mode', '{}'.format(val))
        self.write_ini()

    @property
    def show_favourites_file_mode(self):
        """The saved show favourite files mode."""
        opt = self._get_option(
            'mayawidget', 'show_favourites_file_mode', False)
        return False if opt.lower() == 'false' else True

    @show_favourites_file_mode.setter
    def show_favourites_file_mode(self, val):
        self.set('mayawidget', 'show_favourites_file_mode', '{}'.format(val))
        self.write_ini()

    @property
    def show_archived_file_mode(self):
        """The saved show archived files mode."""
        opt = self._get_option('mayawidget', 'show_archived_file_mode', False)
        return False if opt.lower() == 'false' else True

    @show_archived_file_mode.setter
    def show_archived_file_mode(self, val):
        self.set('mayawidget', 'show_archived_file_mode', '{}'.format(val))
        self.write_ini()

    @property
    def sort_file_mode(self):
        """The saved file sorting mode."""
        opt = self._get_option('mayawidget', 'sort_file_mode', 0)
        return int(opt)

    @sort_file_mode.setter
    def sort_file_mode(self, val):
        self.set('mayawidget', 'sort_file_mode', '{}'.format(val))
        self.write_ini()

    @property
    def reverse_file_mode(self):
        """The saved list order mode."""
        opt = self._get_option('mayawidget', 'reverse_file_mode', False)
        return False if opt.lower() == 'false' else True

    @reverse_file_mode.setter
    def reverse_file_mode(self, val):
        self.set('mayawidget', 'reverse_file_mode', '{}'.format(val))
        self.write_ini()

    @property
    def current_filter(self):
        """The currenty set filter.

        When a filter is set only the files inside that folder are collected.
        Setting it to '/' will collect all the files.
        """
        return self._get_option('mayawidget', 'current_filter', '/')

    @current_filter.setter
    def current_filter(self, val):
        self.set('mayawidget', 'current_filter', '{}'.format(val))
        self.write_ini()

    def clear_history(self):
        """Clears the history from the local configuration file."""
        self._get_option('activejob', 'history', '')
        self.set('activejob', 'history', '')
        self.write_ini()

    @property
    def history(self):
        """Returns the history of configuration values set.

        The string is stored the following format:
            'server1,job1,root1; server2,job2,root2;'

        """
        history = self._get_option('activejob', 'history', '')
        history = history.split(';')

        if not history:
            return []

        array = []
        for setting in history:
            array.append(setting.split(','))

        return array

    def append_to_history(self, server, job, root):
        """Adds an item to the history.

        Args:
            server (str):       The path to the server.
            job (str):          The name of the job.
            root (str):         The name of the root folder.

        """

        array = self._get_option('activejob', 'history', '').split(';')
        array.append('{},{},{}'.format(server, job, root))
        array = sorted(list(set(array))) # reving duplicate items

        string = ''
        for item in array:
            string += item
            string += ';'

        string = string.rstrip(';').lstrip(';')

        self.set('activejob', 'history', '{}'.format(string))
        self.write_ini()

    @property
    def project_scenes_folder(self):
        """The name of the ``scenes`` folder inside the project folder."""
        return self._get_option('activejob', 'project_scenes_folder', 'scenes')

    @project_scenes_folder.setter
    def project_scenes_folder(self, val):
        self.set('activejob', 'project_scenes_folder', '{}'.format(val))
        self.write_ini()

    @property
    def project_renders_folder(self):
        """The name of the ``renders`` folder inside the project folder."""
        return self._get_option('activejob', 'project_renders_folder', 'renders')

    @project_renders_folder.setter
    def project_renders_folder(self, val):
        self.set('activejob', 'project_renders_folder', '{}'.format(val))
        self.write_ini()


class CustomConfig(UnicodeConfigParser):
    """Baseclass for the Project- and FileConfigs."""

    SECTIONS = ['properties',]

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


class ProjectConfig(CustomConfig):
    """Reads and writes Maya project properties."""

    def __init__(self, path):
        super(ProjectConfig, self).__init__(path)

    @staticmethod
    def getConfigPath(path):
        """Returns the configuration file path."""
        fileInfo = QtCore.QFileInfo(path)
        return '{}/.config.ini'.format(fileInfo.filePath())

    @staticmethod
    def getThumbnailPath(path):
        """Returns the path to the project's thumbnail."""
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


local_config = LocalConfig()
"""An instance of the local configuration created when loading this module."""
