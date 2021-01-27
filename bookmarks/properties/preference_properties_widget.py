# -*- coding: utf-8 -*-
"""Preferences widget used to set Application-wide preferences.

"""
import functools

from PySide2 import QtWidgets, QtCore

from .. import settings
from .. import common
from .. import common_ui
from .. import actions
from . import base
from . import preference_properties_widgets



instance = None


def close():
    global instance
    if instance is None:
        return
    instance.close()
    instance.deleteLater()
    instance = None


def show(server, job, root, asset, extension=None):
    global instance
    close()
    instance = PreferencesWidget()
    instance.open()
    return instance



SECTIONS = {
    0: {
        'name': u'Basic Settings',
        'icon': u'icon',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': u'Interface Scale',
                    'key': settings.UIScaleKey,
                    'validator': None,
                    'widget': preference_properties_widgets.ScaleWidget,
                    'placeholder': u'',
                    'description': u'Scales Bookmark\'s interface by the specified amount.\nUseful for high-dpi displays if the text is too small to read.\n\nTakes effect the next time Bookmarks is launched.',
                },
            },
            1: {
                0: {
                    'name': u'Shotgun RV',
                    'key': settings.RVKey,
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Path to RV, eg. "C:/apps/rv.exe"',
                    'description': u'Path to the RV executable.\n\nIf specified compatible media can be previewed in RV.',
                    'button': u'Pick',
                    'button2': u'Reveal'
                },
                1: {
                    'name': u'FFMpeg',
                    'key': settings.FFMpegKey,
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Path to FFMpeg, eg. "C:/apps/ffmpeg.exe"',
                    'description': u'Path to the FFMpeg executable.\n\nIf specified, bookmarks can convert images sequences using FFMpeg.',
                    'button': u'Pick',
                    'button2': u'Reveal'
                },
            },
        },
    },
    1: {
        'name': u'About',
        'icon': None,
        'color': common.SECONDARY_TEXT,
        'groups': {
            0: {
                0: {
                    'name': u'Update',
                    'key': None,
                    'validator': None,
                    'widget': None,
                    'placeholder': u'',
                    'description': u'Check for new versions.',
                    'button': u'Check for Update'
                },
                1: {
                    'name': u'About',
                    'key': None,
                    'validator': None,
                    'widget': preference_properties_widgets.AboutWidget,
                    'placeholder': u'',
                    'description': u'Bookmarks version.',
                },
            },
        },
    },
    2: {
        'name': u'Shortcuts',
        'icon': None,
        'color': common.SECONDARY_TEXT,
        'groups': {
            0: {
                0: {
                    'name': u'',
                    'key': None,
                    'validator': None,
                    'widget': preference_properties_widgets.ShortcutsViewer,
                    'placeholder': u'Path to RV, eg. "C:/apps/rv.exe"',
                    'description': u'Path to the RV executable.\n\nIf specified compatible media can be previewed in RV.',
                },
            },
        },
    },
    3: {
        'name': u'Maya',
        'icon': u'maya',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': u'Instance Syncing',
                    'key': settings.InstanceSyncKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable Instance Syncing'),
                    'placeholder': None,
                    'description': u'{} instances are syncronised by default.\n\nFor example, when an asset is activated other app instances\nwith will also activate the same asset.'.format(common.PRODUCT),
                    'help': u'{} instances are syncronised by default.\n\nFor example, when an asset is activated other app instances\nwith will also activate the same asset.'.format(common.PRODUCT),
                },
                1: {
                    'name': u'Set Workspaces',
                    'key': settings.WorkspaceSyncKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable Workspace Syncing'),
                    'placeholder': None,
                    'description': u'Enable/disable setting workspaces in Maya.\nIf enabled, {} will override workspaces set by Maya\'s Set Project.'.format(common.PRODUCT),
                    'help': u'Enable/disable setting workspaces in Maya.\nIf enabled, {} will override workspaces set by Maya\'s Set Project.'.format(common.PRODUCT),
                },
                2: {
                    'name': u'Workspace Warning',
                    'key': settings.WorksapceWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable Workspace Warnings'),
                    'placeholder': None,
                    'description': u'Enable/disable the warning shown when the\ncurrent Workspace is changed by {}.'.format(common.PRODUCT),
                    'help': u'Enable/disable the warning shown when the\ncurrent Workspace is changed by {}.'.format(common.PRODUCT),
                },
                3: {
                    'name': u'Save Warning',
                    'key': settings.SaveWarningsKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Disable Save Warnings'),
                    'placeholder': None,
                    'description': u'Saving files outside the current workspace will show a warning dialog. Default is "off".',
                    'help': u'Saving files outside the current workspace will show a warning dialog. Default is "off".',
                },
                4: {
                    'name': u'Push Capture',
                    'key': settings.PushCaptureToRVKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Don\'t Open Captures with RV'),
                    'placeholder': None,
                    'description': u'Disable pushing captures to RV.',
                    'help': u'Disable pushing captures to RV.',
                },
                5: {
                    'name': u'Show Captures',
                    'key': settings.RevealCaptureKey,
                    'validator': None,
                    'widget': functools.partial(QtWidgets.QCheckBox, u'Don\'t Reveal Captures'),
                    'placeholder': None,
                    'description': u'Disable revealing captures in the file explorer.',
                    'help': u'Disable revealing captures in the file explorer.',
                },
            },
        },
    },
}


class PreferencesWidget(base.PropertiesWidget):
    def __init__(self, parent=None):
        super(PreferencesWidget, self).__init__(
            SECTIONS,
            None,
            None,
            None,
            db_table=None,
            fallback_thumb=u'settings_sm',
            parent=parent
        )

    @common.error
    @common.debug
    def init_data(self, *args, **kwargs):
        self.thumbnail_editor.setDisabled(True)

        for section in SECTIONS.itervalues():
            for _section in section.itervalues():
                if not isinstance(_section, dict):
                    continue
                for group in _section.itervalues():
                    if not isinstance(group, dict):
                        continue
                    for row in group.itervalues():
                        if 'key' not in row or not row['key']:
                            continue
                        if not hasattr(self, row['key'] + '_editor'):
                            continue

                        editor = getattr(self, row['key'] + '_editor')
                        v = settings.local_settings.value(
                            settings.SettingsSection,
                            row['key'],
                        )
                        self.current_data[row['key']] = v

                        if v is not None:
                            editor.blockSignals(True)
                            if hasattr(editor, 'setCheckState') and v is not None:
                                editor.setCheckState(QtCore.Qt.CheckState(v))
                            elif hasattr(editor, 'setText') and v is not None:
                                editor.setText(v)
                            elif hasattr(editor, 'setCurrentText') and v is not None:
                                editor.setCurrentText(v)
                            editor.blockSignals(False)

                        self._connect_editor(row['key'], None, editor)

    @common.error
    @common.debug
    def save_changes(self, *args, **kwargs):
        for k, v in self.changed_data.iteritems():
            settings.local_settings.setValue(settings.SettingsSection, k, v)
        return True

    @common.error
    @common.debug
    @QtCore.Slot()
    def update_button_clicked(self, *args, **kwargs):
        import bookmarks.versioncontrol.versioncontrol as versioncontrol
        versioncontrol.check()

    @common.error
    @common.debug
    @QtCore.Slot()
    def RVPath_button_clicked(self, *args, **kwargs):
        self._pick_file(settings.RVKey)

    @common.error
    @common.debug
    @QtCore.Slot()
    def RVPath_button2_clicked(self, *args, **kwargs):
        editor = getattr(self, settings.RVKey + '_editor')
        if not editor.text():
            return
        actions.reveal(editor.text())

    @common.error
    @common.debug
    @QtCore.Slot()
    def FFMpegPath_button_clicked(self, *args, **kwargs):
        self._pick_file(settings.FFMpegKey)

    @common.error
    @common.debug
    @QtCore.Slot()
    def FFMpegPath_button2_clicked(self, *args, **kwargs):
        editor = getattr(self, settings.FFMpegKey + '_editor')
        if not editor.text():
            return
        actions.reveal(editor.text())

    def _pick_file(self, k):
        editor = getattr(self, k + '_editor')
        _bin = k.replace(u'Path', u'')
        _filter = u'{}.exe'.format(_bin) if common.get_platform() == u'win' else u'*.*'
        res = QtWidgets.QFileDialog.getOpenFileName(
            caption=u'Select {} Executable...'.format(_bin),
            filter=_filter,
            dir=u'/'
        )
        path, _ = res
        if not path:
            return
        editor.setText(path)
