# -*- coding: utf-8 -*-
"""`Asset config` describes the folder structure, and accepted file-types of assets.

The default values are stored in `asset_config.json` but each bookmark can be
configured independently. The custom configuration values are stored in the
bookmark's database at the `DB_KEY` column as a data dictionary

Example:

    code-block:: python

        asset_info = AssetConfig(
            u'//gw-workstation/jobs',
            u'myjob',
            u'data/assets'
        )
        asset_info.set_data(
            {
                'custom_data': {
                    'value': u'hello_world',
                    'description': u'A test description to say hi.'
                }
            }
        )
        data = asset_info.get_data()
        asset_info.get_description(u'geo')
        asset_info.dump_json(u'C:/temp/data.json')

        s = asset_info.expand_tokens(u'{asset_root}/{scene}/{prefix}_{asset}_{task}_{user}_{version}.{ext}', ext='exr')


"""
import os
import re
import getpass
import socket
import json
import string
import base64
import collections

from PySide2 import QtCore
import OpenImageIO

import bookmarks.log as log
import bookmarks.bookmark_db as bookmark_db


DB_KEY = u'asset_config'
REQUIRED_SECTIONS = (
    'FILE_NAME_PATTERNS',
    'FOLDERS',
    'FORMATS',
)

PatternData = REQUIRED_SECTIONS[0]
FolderData = REQUIRED_SECTIONS[1]
FormatData = REQUIRED_SECTIONS[2]


def update(d, default):
    for k, v in d.iteritems():
        if isinstance(v, dict):
            update(v, default[k])
        elif v:
            default[k] = v


def sort(s):
    return u', '.join(sorted(re.findall(r"[\w']+", s)))


class AssetConfig(QtCore.QObject):
    """

    """

    def __init__(self, server, job, root, parent=None):
        super(AssetConfig, self).__init__(parent=parent)

        self.server = server
        self.job = job
        self.root = root

        self.default_data = {
            'FORMATS': {},
            'FILE_NAME_PATTERNS': {},
            'FOLDERS': {}
        }
        self.data = {}

        self.init_default_data()

    def init_default_data(self):
        """Loads and verifies the default asset config values.

        """
        data = self.load_default_values()
        if not isinstance(data, dict):
            raise TypeError(u'Expected a <type \'dict\'>')

        for k in REQUIRED_SECTIONS:
            if k not in data:
                raise ValueError(
                    '`asset_config.json` is invalid: {} section is missing'.format(k))

        self.default_data = data

        # Let's load this data from OpenImageIO
        if 'OpenImageIOFormat' in self.default_data['FORMATS']:
            self.default_data['FORMATS']['OpenImageIOFormat']['value'] = sort(OpenImageIO.get_string_attribute(u'extension_list'))

        # Sort values
        for v in self.default_data['FORMATS'].itervalues():
            v['value'] = sort(v['value'])

        return self.default_data

    @staticmethod
    def load_default_values():
        """Loads the default values from the `asset_config.json` file.

        """
        try:
            path = os.path.normpath(
                __file__ + os.path.sep + os.pardir + os.path.sep + u'asset_config.json')
            with open(path, 'r') as f:
                return json.loads(f.read())
        except Exception as e:
            log.error(u'Could not load default values.')
            return {}

    def get_data(self, force=False):
        """Returns the current asset config values.

        First the default values are loaded from `asset_config.json`, then we'll
        check the database and update the data from any custom values that might
        have been changed.

        The fetched results are cached to `self.data`. To re-querry the values
        from the bookmark database, an optional `force=True` can be passed.

        """
        if not force and self.data:
            return self.data

        v = bookmark_db.get_property(
            DB_KEY,
            server=self.server,
            job=self.job,
            root=self.root
        )

        if not v:
            self.data = self.default_data.copy()
            return self.data

        try:
            v = base64.b64decode(v)
            v = json.loads(v)
        except:
            log.error(u'Error decoding config from JSON')
            raise

        # Let's udpate the default data with the data loaded from the database
        data = self.default_data.copy()
        update(v, data)

        self.data = data
        return self.data

    def set_data(self, data):
        try:
            db = bookmark_db.get_db(self.server, self.job, self.root)
        except:
            log.error(u'Could get bookmark database.')
            raise

        try:
            v = json.dumps(data, ensure_ascii=False, encoding='utf-8')
            v = base64.b64encode(v.encode('utf-8'))
        except:
            log.error(u'Could not encode data')
            raise

        db.setValue(1, DB_KEY, v, table=u'properties')
        return self.get_data(force=True)

    def dump_json(self, destination):
        """Save the current configuration as a JSON file.

        """
        file_info = QtCore.QFileInfo(destination)
        if not file_info.dir().exists():
            raise OSError('{} does not exists. Specify a valid destination.'.format(
                file_info.dir().path()
            ))

        data = self.get_data()
        try:
            json_data = json.dumps(data, sort_keys=True, indent=4)
        except:
            log.error(u'Failed to convert data to JSON.')
            raise

        with open(file_info.filePath(), 'w') as f:
            f.write(json_data)
            log.success(u'Asset folder configuration saved to {}'.format(
                file_info.filePath()))

    def get_description(self, value):
        """Utility method for returning a description of an item.

        Args:
            value (unicode):    A value, eg. 'anim'.

        """
        data = self.get_data()

        if not isinstance(value, (str, unicode)):
            raise TypeError('value must be str or unicode.')

        for _v in data.itervalues():
            for k, v in _v.iteritems():
                if 'subfolders' in v:
                    for _k_, _v_ in v['subfolders'].iteritems():
                        if value.lower() == _k_.lower():
                            return _v_['description']
                if value.lower() == k.lower():
                    return v['description']
        return u''

    def expand_tokens(
        self,
        s,
        user=getpass.getuser(),
        version=u'v001',
        host=socket.gethostname(),
        task=u'anim',
        ext=u'png',
        prefix=None,
        **_kwargs
    ):
        """Expands all valid tokens in the given string, based on the current
        asset config values.

        Invalid tokens will be marked invalid.

        Args:
            s (unicode):    The string containing tokens to be expanded.

        """
        kwargs = self.get_tokens(
            user=user,
            version=version,
            host=host,
            task=task,
            ext=ext,
            prefix=prefix,
            **_kwargs
        )

        # To avoid KeyErrors when an invalid token is passed we will replace
        # the token in question with `invalid_token`
        # via https://stackoverflow.com/questions/17215400/format-string-unused-named-arguments
        return string.Formatter().vformat(
            s,
            (),
            collections.defaultdict(lambda: u'{invalid_token}', **kwargs)
        )

    def get_tokens(self, **kwargs):
        """Building token/value mapping for the format() method.

        """
        data = self.get_data()
        tokens = {}
        for k, v in data[FolderData].iteritems():
            tokens[k] = v['value']

        tokens['server'] = self.server
        tokens['job'] = self.job
        tokens['root'] = self.root
        tokens['asset'] = self.asset

        tokens['bookmark'] = u'{}/{}/{}'.format(
            self.server,
            self.job,
            self.root
        )

        for k, v in kwargs.iteritems():
            tokens[k] = v

        # Load the manually set prefix form the database
        if 'prefix' not in kwargs or not kwargs['prefix']:
            try:
                db = bookmark_db.get_db(
                    self.server,
                    self.job,
                    self.root
                )
                prefix = db.value(1, u'prefix', table=u'properties')
                prefix = prefix if prefix else '{invalid_token}'
                tokens['prefix'] = prefix
            except:
                pass

        # The asset root token will only be available when the asset is manually
        # specified
        if 'asset' in kwargs and kwargs['asset']:
            tokens['asset_root'] = u'{}/{}/{}/{}'.format(
                self.server,
                self.job,
                self.root,
                kwargs['asset']
            )

        return tokens
