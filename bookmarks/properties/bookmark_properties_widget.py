# -*- coding: utf-8 -*-
"""Settings window for editing bookmark properties.

Used to edit data in the bookmark database (see \'bookmark_db.py\'). The database
stores information about the bookmark's default \'width\', \'height\', \'frame rate\'
and connectivity information, such as \'Slack\' and \'Shotgun\' tokens.

Usage:

    widget = BookmarkPropertiesWidget(
        u'//my_server/jobs', u'my_job', u'my/root/folder'
    ).open()


"""
import functools
import re

from PySide2 import QtCore, QtGui, QtWidgets

from .. import log
from .. import common
from .. import common_ui
from .. import bookmark_db
from . import base
from . import asset_config_widget


instance = None

def close():
    global instance
    if instance is None:
        return
    instance.close()
    instance.deleteLater()
    instance = None


def show(server, job, root):
    global instance
    close()
    instance = BookmarkPropertiesWidget(
        server,
        job,
        root,
    )
    instance.open()
    return instance


SECTIONS = {
    0: {
        'name': u'Basic Settings',
        'icon': u'',
        'color': common.SECONDARY_BACKGROUND,
        'groups': {
            0: {
                0: {
                    'name': u'Prefix',
                    'key': u'prefix',
                    'validator': base.textvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Custom prefix, eg. \'MYB\'',
                    'description': u'A short name of the bookmark (or job) used when saving files.\n\nEg. \'MYB_sh0010_anim_v001.ma\' where \'MYB\' is the prefix specified here.',
                    'button': u'Suggest'
                },
            },
            1: {
                0: {
                    'name': u'Description',
                    'key': u'description',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'A short description, eg. \'Character assets\'',
                    'description': u'A description of this bookmark, eg. \'Character assets\'.',
                },
            },
            2: {
                0: {
                    'name': u'Framerate',
                    'key': u'framerate',
                    'validator': base.floatvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Framerate, eg. \'23.976\'',
                    'description': u'The framerate of the bookmark, eg, \'25.0\'.\n\nUsed by Bookmarks to control the format of scenes inside hosts, eg. Maya.'
                },
                1: {
                    'name': u'Width',
                    'key': 'width',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Width in pixels',
                    'description': u'The output width in pixels, eg. \'1920\''
                },
                2: {
                    'name': u'Height',
                    'key': u'height',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Height in pixels',
                    'description': u'The output height in pixels, eg. \'1080\''
                },
                3: {
                    'name': u'Default Start Frame',
                    'key': u'startframe',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Start frame, eg. \'1001\'',
                    'description': u'A default start frame for all subsequent assets.\n\nThis can be useful when the project has a custom start frame, eg. \'1001\' instead of \'1\' or \'0\'.',
                },
                4: {
                    'name': u'Default Duration',
                    'key': u'duration',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Duration, eg. \'150\'',
                    'description': u'The default duration of an asset in frames, eg. \'150\'',
                },
            },
            3: {
                'identifier': {
                    'name': u'Asset Identifier',
                    'key': u'identifier',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'A file name, eg. \'workspace.mel\'',
                    'description': u'Only folders containing the file specified above will be read as assets.\n\nUsing the default Maya Workspace the identifier normally is \'workspace.mel\', however any other arbitary file can be used as long it is present in the root of an asset folder.\n\nWhen left empty all folders in the bookmark will be read.',
                    'help': u'Only folders containing the file specified here will be read as assets.\nUsing the default Maya Workspace the identifier normally is \'workspace.mel\', however any other arbitary file can be used as long it is present in the root of an asset folder.\n\nWhen left empty, all folders in the bookmark will be interpeted as assets.',
                }
            }
        }
    },
    1: {
        'name': u'Slack',
        'icon': u'slack_color',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': u'OAuth Token',
                    'key': u'slacktoken',
                    'validator': None,
                    'protect': True,
                    'widget': common_ui.LineEdit,
                    'description': u'A valid Slack App OAuth token',
                    'placeholder': u'xoxb-01234567890-0123456',
                    'help':  u'Paste a valid <a href="{slack_api_url}">{start}Slack App OAuth token{end}</a> above (usually starting with {start}xoxb{end}).\n\nMake sure the app has {start}users:read{end} and {start}chat:write{end} scopes enabled. To send messages to channels the bot is not part of, add {start}chat:write.public{end}. Scopes {start}channels:read{end} and {start}groups:read{end} are needed to list available Slack Channels.\n\nSee <a href="{slack_api_url}">{start}Slack API{end}</a> for more information. '.format(slack_api_url=base.SLACK_API_URL, **base.span),
                    'button': u'Visit',
                    'button2': u'Verify',
                }
            }
        }
    },
    2: {
        'name': u'Shotgun Connection',
        'icon': u'shotgun',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': u'Domain',
                    'key': u'shotgun_domain',
                    'validator': base.domainvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Domain, eg. https://mystudio.shotgunstudio.com',
                    'description': u'The domain, including http:// or https://, used by shotgun. Eg. \'https://mystudio.shotgunstudio.com\'',
                    'button': u'Visit',
                    'button2': u'Verify'
                },
                1: {
                    'name': u'Script Name',
                    'key': u'shotgun_scriptname',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'my-sg-script',
                    'description': u'A name of a Shotgun Script.',
                },
                2: {
                    'name': u'API Key',
                    'key': u'shotgun_api_key',
                    'validator': None,
                    'protect': True,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'abcdefghijklmno3bqr*1',
                    'description': u'A Shotgun Script API Key, eg. \'abcdefghijklmno3bqr*1\'.\n\nA valid script has to be set up for your ogranisation for Bookmarks to be able to connect to Shotgun. Consult the Shotgun documentation for details on how to set this up.',
                    'help': u'Make sure Shotgun has a valid API Script set up. This can be done from the Shotgun Admin - Scripts option.',
                },
            },
        },
    },
    3: {
        'name': u'Shotgun Entity',
        'icon': u'shotgun',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': u'Link',
                    'key': u'link',
                    'validator': None,
                    'widget': None,
                    'placeholder': None,
                    'description': u'Link with Shotgun',
                    'button': u'Link',
                },
                1: {
                    'name': u'Type',
                    'key': u'shotgun_type',
                    'validator': base.intvalidator,
                    'widget': functools.partial(base.ShotgunTypeWidget, base.ShotgunTypeWidget.ProjectTypes),
                    'placeholder': None,
                    'description': u'Select a Shotgun type',
                },
                2: {
                    'name': u'ID',
                    'key': u'shotgun_id',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Shotgun Project ID, eg. \'774\'',
                    'description': u'The Shotgun ID number this bookmark is associated with. Eg. \'774\'. You can find your project\'s ID number using the \'Find Shotgun ID\' button, via the shotgun API, or Shotgun website.\'',
                },
                3: {
                    'name': u'Name',
                    'key': u'shotgun_name',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Shotgun project name, eg. \'MyProject\'',
                    'description': u'The Shotgun project name',
                },
            }
        }
    },
    4: {
        'name': u'URLs',
        'icon': u'',
        'color': common.SECONDARY_BACKGROUND,
        'groups': {
            0: {
                0: {
                    'name': u'Primary',
                    'key': u'url1',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': u'A custom url of the bookmarks, eg. https://sheets.google.com/123',
                    'button': u'Visit',
                },
                1: {
                    'name': u'Secondary',
                    'key': u'url2',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': u'A custom url of the bookmarks, eg. https://sheets.google.com/123',
                    'button': u'Visit',
                }
            }
        }
    },
    5: {
        'name': u'Database',
        'icon': u'',
        'color': common.SECONDARY_BACKGROUND,
        'groups': {
            0: {
                0: {
                    'name': u'Created on:',
                    'key': u'created',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': 'The time the database was created',
                    'description': u'The time the database was created',
                },
                1: {
                    'name': u'Created by user:',
                    'key': u'user',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'The user the database was created by',
                    'description': u'The user the database was created by',
                },
                2: {
                    'name': u'Created by host:',
                    'key': u'host',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'The user the database was created by',
                    'description': u'The user the database was created by',
                },
                3: {
                    'name': u'Bookmark Server:',
                    'key': u'server',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': 'The bookmark\'s original server',
                    'description': u'The bookmark\'s original server',
                },
                4: {
                    'name': u'Bookmark Job:',
                    'key': u'job',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': 'The bookmark\'s original job',
                    'description': u'The bookmark\'s original job',
                },
                5: {
                    'name': u'Bookmark Root:',
                    'key': u'root',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': 'The bookmark\'s original job',
                    'description': u'The bookmark\'s original job',
                },
            }
        }
    }
}


class BookmarkPropertiesWidget(base.PropertiesWidget):
    """The widget containing all the UI elements used to edit
    Bookmark properties, such as frame rate, resolution and Shotgun properties.

    Usage:
        Initialize with the server, job, root name, eg:

        widget = BookmarkPropertiesWidget(
            '//my-server/jobs', 'my_job', 'my/root/folder'
        ).open()

    """

    def __init__(self, server, job, root, parent=None):
        super(BookmarkPropertiesWidget, self).__init__(
            SECTIONS,
            server,
            job,
            root,
            asset=None,
            db_table=bookmark_db.BookmarkTable,
            fallback_thumb=u'thumb_bookmark_gray',
            parent=parent
        )

        self.asset_config_editor = None
        self._add_asset_config()

    def db_source(self):
        return u'{}/{}/{}'.format(self.server, self.job, self.root)

    def init_data(self):
        self._init_db_data()

    def save_changes(self):
        try:
            self._save_db_data()
            v = self.description_editor.text()
            self.valueUpdated.emit(self.db_source(), common.DescriptionRole, v)
        except:
            s = u'Could not save properties to the database.'
            log.error(s)
            common_ui.ErrorBox('Error', s).open()
            return False

        try:
            self.asset_config_editor.save_changes()
        except:
            s = u'Could not save asset config to the database.'
            log.error(s)
            common_ui.ErrorBox('Error', s).open()
            return False

        try:
            self.thumbnail_editor.save_image()
            self.thumbnailUpdated.emit(self.db_source())
        except:
            s = u'Failed to save the thumbnail.'
            log.error(s)
            common_ui.ErrorBox('Error', s).open()
            return False

        self.itemUpdated.emit(self.db_source())
        return True

    def _add_asset_config(self):
        parent = self.scrollarea.widget()
        self.asset_config_editor = asset_config_widget.AssetConfigEditor(
            self.server,
            self.job,
            self.root,
            parent=parent
        )
        parent.layout().addWidget(self.asset_config_editor, 1)

    @QtCore.Slot()
    def prefix_button_clicked(self):
        """Suggest a prefix based on the job's name.

        """
        k = 'prefix'
        if not hasattr(self, k + '_editor'):
            return

        substrings = re.sub(ur'[\_\-\s]+', u';', self.job).split(u';')

        prefix = u''
        if (not substrings or len(substrings) < 2) and len(self.job) > 3:
            prefix = self.job[0:3].upper()
        else:
            prefix = u''.join([f[0] for f in substrings]).upper()

        getattr(self, k + '_editor').setText(prefix)
        getattr(self, k + '_editor').textEdited.emit(prefix)

    @QtCore.Slot()
    def slacktoken_button_clicked(self):
        QtGui.QDesktopServices.openUrl(base.SLACK_API_URL)

    @QtCore.Slot()
    def slacktoken_button2_clicked(self):
        """Verifies the entered Slack API token.

        """
        k = 'slacktoken'
        if not hasattr(self, k + '_editor'):
            return

        v = getattr(self, k + '_editor').text()
        if not v:
            return

        try:
            from .. import slack
        except ImportError as err:
            common_ui.ErrorBox(
                u'Could not import SlackClient',
                u'The Slack API python module was not loaded:\n{}'.format(err),
            ).open()
            log.error('Slack: import error.')
            raise
        except:
            raise

        client = slack.SlackClient(v)
        client.verify_token(silent=False)

    def link_button_clicked(self):
        if self._db_table is not None:
            self.save_changes()
        self.show_link_entity_widget()

    @QtCore.Slot()
    def shotgun_domain_button_clicked(self):
        """Opens the shotgun base domain in the browser.

        """
        k = u'shotgun_domain'
        if not hasattr(self, k + '_editor'):
            return
        v = getattr(self, k + '_editor').text()
        if v:
            QtGui.QDesktopServices.openUrl(v)

    def _get_name(self):
        return self.job

    def _get_shotgun_attrs(self):
        """Returns the properties needed to connect to shotgun.

        """
        k = u'shotgun_domain'
        if not hasattr(self, k + '_editor'):
            return None, None, None
        domain = getattr(self, k + '_editor').text()

        k = u'shotgun_api_key'
        if not hasattr(self, k + '_editor'):
            return None, None, None
        key = getattr(self, k + '_editor').text()

        k = u'shotgun_scriptname'
        if not hasattr(self, k + '_editor'):
            return None, None, None
        script = getattr(self, k + '_editor').text()

        if not all((domain, key, script)):
            common_ui.ErrorBox(
                u'Missing value.',
                u'Must enter a valid domain, script name and API key.'
            ).open()
            raise RuntimeError(u'Missing value.')

        return domain, key, script

    @QtCore.Slot()
    def shotgun_domain_button2_clicked(self):
        """Check the validity of the Shotgun token.

        """
        from ..shotgun import shotgun

        domain, key, script = self._get_shotgun_attrs()
        with shotgun.connection(None, None, None, domain=domain, script=script, key=key) as sg:
            sg.find_projects()

            info = u''
            for k, v in sg.info().iteritems():
                info += u'{}: {}'.format(k, v)
                info += u'\n'

            common_ui.MessageBox(
                u'Successfully connected to Shotgun.',
                info
            ).open()

    @QtCore.Slot()
    def url1_button_clicked(self):
        k = 'url1'
        if not hasattr(self, k + '_editor'):
            return
        v = getattr(self, k + '_editor').text()
        if not v:
            return
        QtGui.QDesktopServices.openUrl(v)

    @QtCore.Slot()
    def url2_button_clicked(self):
        k = 'url2'
        if not hasattr(self, k + '_editor'):
            return
        v = getattr(self, k + '_editor').text()
        if not v:
            return
        QtGui.QDesktopServices.openUrl(v)
