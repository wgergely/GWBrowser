# -*- coding: utf-8 -*-
"""Slacker is a lightweight wrapper used to send messages using SlackClient,
Slack's python API library.

Slack Token
-----------

You will have to create a new Slack App and install it to your workspace. This
should generate the OAuth token needed by Bookmarks.

Scopes
------

The Slack App requires the `users:read` and
`chat:write` scopes to function. To send messages to channels
the bot is not part of add `chat:write.public`.
Scopes `channels:read` and `groups:read` are needed to list the available
slack channels.

See http://api.slack.com/apps for more information.


"""
import urllib2
import slackclient

from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common
from . import common_ui
from . import images
from . import settings
from .bookmark_editor import list_widget


IdRole = QtCore.Qt.UserRole + 1
ThumbnailHashRole = IdRole + 1
ThumbnailUrlRole = ThumbnailHashRole + 1

instance = None
CLIENTS = {}



def show(token):
    global instance
    if instance is not None and instance.token == token:
        instance.open()
        instance.raise_()
        return

    instance = SlackWidget(token)
    instance.open()
    return instance


def get_client(token):
    if token in CLIENTS:
        return CLIENTS[token]

    CLIENTS[token] = SlackClient(token)
    return CLIENTS[token]


def response_error(response, silent=False):
    if not isinstance(response, dict):
        raise TypeError(
            'Invalid response type. Expected <type `dict`>, got {}'.format(type(response)))

    if 'ok' not in response:
        raise KeyError('Key `ok` missing in response')

    if response['ok']:
        return

    label = u'An error occured.'
    details = u''
    if 'error' in response:
        details += u'Error: {}\n'.format(response['error'])
    if 'error' in response and 'needed' in response:
        details += u'Required: {}\n'.format(response['needed'])
    if 'error' in response and 'provided' in response:
        details += u'Provided: {}\n'.format(response['provided'])

    s = u'Maybe a required scope is missing?\nError: "{}"'.format(
        response[u'error'])

    if not silent:
        common_ui.ErrorBox(label, details).open()
    log.error(details)
    raise ValueError(details)


class OverlayWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(OverlayWidget, self).__init__(parent=parent)
        self._text = u'Loading...'

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )

        self.message_timer = QtCore.QTimer(parent=self)
        self.message_timer.setSingleShot(True)
        self.message_timer.setInterval(2000)
        self.message_timer.timeout.connect(lambda: self.setText(u''))

    @QtCore.Slot(unicode)
    def setText(self, text):
        self.setGeometry(self.parent().rect())
        self.raise_()

        self._text = text
        self.update()

        QtWidgets.QApplication.instance().processEvents()

        if text:
            self.message_timer.start()

    def paintEvent(self, event):
        if not self._text:
            return

        painter = QtGui.QPainter()
        painter.begin(self)
        o = common.MARGIN()
        o = 0
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))

        painter.setBrush(common.SEPARATOR)
        painter.setPen(QtCore.Qt.NoPen)

        painter.setOpacity(0.5)
        painter.drawRoundedRect(
            rect, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())
        painter.setOpacity(1.0)

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(common.TEXT)
        painter.setFont(common.font_db.primary_font(
            common.MEDIUM_FONT_SIZE())[0])

        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            self._text
        )
        painter.end()

    def showEvent(self, event):
        self.setGeometry(self.parent().rect())



class SlackClient(slackclient.SlackClient):
    """Customized SlackClient used by bookmarks to send and receive massages.

    """

    def __init__(self, token):
        super(SlackClient, self).__init__(token)
        if not isinstance(token, (str, unicode)):
            raise TypeError(
                u'Wrong type. Expected <type `unicode`>, got {}'.format(type(token)))

    def verify_token(self, silent=False):
        """Tests the slack token and the permissions needed to send messages to
        channels.

        Using the Conversations API,the app requires any `channels:read` and/or
        `groups:read` to get channel lists.

        Addittionally, `chat.write` and `users.read` are *required* to send messages.

        Raises:
            ValueError:     When the any problems with the token.

        """
        auth_test_response = self.api_call(u'auth.test')
        response_error(auth_test_response, silent=silent)
        if 'user_id' in auth_test_response:
            response = self.api_call(
                'users.info', user=auth_test_response['user_id'])
            response_error(response, silent=silent)
            response = self.api_call(
                'users.list', user=auth_test_response['user_id'])
            response_error(response, silent=silent)

        response = self.api_call(u'conversations.list')
        response_error(response, silent=silent)

        title = u'Slack API Token seems to be working fine.'
        details = u''
        if 'url' in auth_test_response:
            details += 'URL: {}\n'.format(auth_test_response['url'])
        if 'team' in auth_test_response:
            details += 'Team: {}\n'.format(auth_test_response['team'])
        if not silent:
            common_ui.OkBox(title, details).open()

    def get_url(self):
        response = self.api_call(u'auth.test')
        response_error(response)
        if 'url' not in response:
            raise KeyError('Key `url` is missing from response.')
        return response['url']

    @staticmethod
    def _get_profiles(response, silent):
        if not response['ok']:
            s = u'Maybe a required scope is missing?\nError: "{}"'.format(
                response[u'error'])
            if 'needed' in response:
                s += '\nScope needed: "{}"'.format(response['needed'])
            log.error(s)
            if not silent:
                common_ui.ErrorBox(u'Slack Token Error.', s).open()
            raise ValueError(s)

        _profiles = []
        for member in response['members']:
            if member[u'deleted']:
                continue
            if member[u'is_app_user']:
                continue
            if member[u'is_bot']:
                continue
            _profiles.append(member)
        return _profiles

    def get_user_profiles(self, silent=False):
        """Returns all available profiles in the workspace associated with the
        token. Make sure scope `users.read` is available for the token.

        Raises:
            ValueError:     If the token is invalid or missing a required scope.

        """
        method = u'users.list'
        limit = 20
        profiles = []

        # Getting the user-list in segments as per the Slack API documentation
        # `limit` sets the number of entries to get with each call
        response = self.api_call(method, limit=limit)
        profiles += self._get_profiles(response, silent)

        while response['response_metadata']['next_cursor']:
            app = QtWidgets.QApplication.instance()
            if app:
                app.processEvents()

            response = self.api_call(
                method, limit=limit, cursor=response['response_metadata']['next_cursor'])

            profiles += self._get_profiles(response, silent)

        return profiles

    def get_channels(self, silent=False):
        """Returns all conversations and groups.

        """
        response = self.api_call(
            u'conversations.list',
            exclude_archived=True,
            types='public_channel,private_channel'
        )

        if not response['ok']:
            s = u'Maybe a required scope is missing?\nError: "{}"'.format(
                response[u'error'])
            if 'needed' in response:
                s += '\nScope needed: "{}"'.format(response['needed'])
            log.error(s)
            if not silent:
                common_ui.ErrorBox(u'Slack Token Error.', s).open()
            raise ValueError(s)

        channels = []
        for channel in response['channels']:
            if channel['is_archived']:
                continue
            if u'is_channel' in channel:
                if channel['is_channel']:
                    channels.append(channel)
            if u'is_group' in channel:
                if channel['is_group']:
                    channels.append(channel)
        return channels

    def send_message(self, channel, text):
        """Send a message using SlackClient.

        """
        text = text.replace(u'&', u'&amp')
        # text = text.replace(u'<', u'&lt')
        # text = text.replace(u'>', u'&gt')
        response = self.api_call(
            'chat.postMessage',
            channel=channel,
            text=text,
            mrkdwn=True,
            unfurl_media=True,
            unfurl_links=True,
            link_names=True,
        )

        if not response[u'ok']:
            log.error(u'Failed to send message')
            common_ui.ErrorBox(
                u'Could not send message',
                response['error']
            ).open()
            raise RuntimeError(response[u'error'])


class UsersModel(QtCore.QAbstractItemModel):
    """Model used to store the available profiles.

    """
    modelDataResetRequested = QtCore.Signal()

    def __init__(self, token, parent=None):
        super(UsersModel, self).__init__(parent=parent)
        self.token = token
        self._row_size = QtCore.QSize(1, common.ROW_HEIGHT())

        self.INTERNAL_USER_DATA = common.DataDict()
        self.modelDataResetRequested.connect(self.__initdata__)

    def __initdata__(self):
        self.beginResetModel()

        self.INTERNAL_USER_DATA = common.DataDict()
        client = get_client(self.token)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'slack',
            common.SECONDARY_TEXT,
            self._row_size.height()
        )
        icon = QtGui.QIcon()
        icon.addPixmap(pixmap)

        # Channels
        try:
            channels = client.get_channels()
            for channel in sorted(channels, key=lambda x: x['name']):
                idx = len(self.INTERNAL_USER_DATA)
                self.INTERNAL_USER_DATA[idx] = common.DataDict({
                    QtCore.Qt.DisplayRole: u'Channel:  ' + channel['name'],
                    QtCore.Qt.DecorationRole: icon,
                    QtCore.Qt.SizeHintRole: self._row_size,
                    QtCore.Qt.FontRole: common.font_db.primary_font(font_size=common.SMALL_FONT_SIZE())[0],
                    IdRole: channel[u'id'],
                    ThumbnailHashRole: None,
                    ThumbnailUrlRole: None,
                })
        except Exception as e:
            log.error(u'Could not get channels.\n{}'.format(e))

        try:
            profiles = client.get_user_profiles()
            for profile in sorted(profiles, key=self.get_pretty_name):
                idx = len(self.INTERNAL_USER_DATA)
                self.INTERNAL_USER_DATA[idx] = common.DataDict({
                    QtCore.Qt.DisplayRole: self.get_pretty_name(profile),
                    QtCore.Qt.DecorationRole: icon,
                    QtCore.Qt.SizeHintRole: self._row_size,
                    QtCore.Qt.FontRole: common.font_db.primary_font(font_size=common.SMALL_FONT_SIZE())[0],
                    IdRole: profile[u'id'],
                    ThumbnailHashRole: profile[u'profile']['avatar_hash'],
                    ThumbnailUrlRole: profile[u'profile']['image_32'],
                })
                index = self.index(idx, 0)
                self.get_icon(index)
        except Exception as e:
            log.error('Could not get profiles.\n{}'.format(e))

        self.endResetModel()

    def columnCount(self, index, parent=QtCore.QModelIndex()):
        return 2

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.INTERNAL_USER_DATA)

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return
        if index.row() not in self.INTERNAL_USER_DATA:
            return
        self.INTERNAL_USER_DATA[index.row()][role] = data
        self.dataChanged.emit(index, index)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.row() not in self.INTERNAL_USER_DATA:
            return None
        if role not in self.INTERNAL_USER_DATA[index.row()]:
            return None
        return self.INTERNAL_USER_DATA[index.row()][role]

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """Bog-standard index creator."""
        return self.createIndex(row, 0, parent=parent)

    def parent(self, index):
        return QtCore.QModelIndex()

    def get_pretty_name(self, member):
        """Returns a pretty name for the given member.

        """
        p = member['profile']
        d = u'display_name'
        f = u'first_name'
        l = u'last_name'
        r = u'real_name'

        if all((d in p, f in p, l in p)):
            if all((p[d], p[f], p[l])):
                name = u'{} ({} {})'.format(
                    p[d], p[f], p[l])
            elif p[d]:
                name = p[d]
            elif all((p[f], p[l])):
                name = u'{} {}'.format(
                    p[f], p[l])
        else:
            if d in p:
                name = p[d]
            elif f in p and not l in p:
                name = p[f]
            elif f in p and l in p:
                name = u'{} {}'.format(
                    p[f], p[l])

        if not name and r in p:
            name = p[r]
        return name

    @QtCore.Slot(QtCore.QModelIndex)
    def get_icon(self, index):
        """Downloads and sets the icon for the given index."""
        if not index.isValid():
            return

        try:
            url = index.data(ThumbnailUrlRole)
            response = urllib2.urlopen(url)
        except Exception as e:
            log.error('Could not save thumbnail:\n{}'.format(e))
            return

        # Cache directory
        cache_dir_path = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        cache_dir_path = u'{}/{}/slack'.format(cache_dir_path, common.PRODUCT)

        cache_file_path = u'{}/{}.png'.format(
            cache_dir_path,
            index.data(ThumbnailHashRole)
        )

        # Let's check if the thumbnail has already been cached and if not, download it.
        if not QtCore.QFileInfo(cache_file_path).exists():
            QtCore.QDir(cache_dir_path).mkpath('.')

            with open(cache_file_path, 'wb') as f:
                f.write(response.read())

        image = images.oiio_get_qimage(cache_file_path)
        if not image:
            return
        if image.isNull():
            return

        if image.isNull():
            return

        icon = QtGui.QIcon()
        pixmap = QtGui.QPixmap.fromImage(image)
        icon.addPixmap(pixmap, QtGui.QIcon.Normal)
        icon.addPixmap(pixmap, QtGui.QIcon.Active)
        self.setData(index, icon, role=QtCore.Qt.DecorationRole)


class UsersWidget(QtWidgets.QListView):
    def __init__(self, token, parent=None):
        super(UsersWidget, self).__init__(parent=parent)

        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setViewMode(QtWidgets.QListView.ListMode)
        self.setSpacing(0)
        self.setUniformItemSizes(True)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)

        # Models
        proxy_model = QtCore.QSortFilterProxyModel(parent=self)
        proxy_model.setFilterRole(QtCore.Qt.DisplayRole)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setModel(proxy_model)
        model = UsersModel(token, parent=self)
        proxy_model.setSourceModel(model)

        # Custom delegate
        self.setItemDelegate(list_widget.ListWidgetDelegate(parent=self))

        self.clicked.connect(self.save_selection)
        self.selectionModel().currentChanged.connect(self.save_selection)
        self.model().modelReset.connect(self.restore_selection)

    @QtCore.Slot(QtCore.QModelIndex)
    def save_selection(self, index):
        v = index.data(QtCore.Qt.DisplayRole)
        settings.local_settings.setValue(
            settings.UIStateSection,
            settings.SlackUserKey,
            v
        )

    @QtCore.Slot()
    def restore_selection(self):
        v = settings.local_settings.value(
            settings.UIStateSection,
            settings.SlackUserKey,
        )

        if v is None:
            return

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if index.data(QtCore.Qt.DisplayRole).lower() == v.lower():
                self.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.setCurrentIndex(index)
                self.scrollTo(
                    index, QtWidgets.QAbstractItemView.PositionAtCenter)


class SlackWidget(QtWidgets.QDialog):
    def __init__(self, token, parent=None):
        super(SlackWidget, self).__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        self.token = token

        self._initialized = False

        self.initialize_timer = QtCore.QTimer(parent=self)
        self.initialize_timer.setInterval(1000)
        self.initialize_timer.setSingleShot(True)

        self.overlay = OverlayWidget(parent=self)

        self.send_button = None
        self.users_widget = None

        self.setWindowTitle(u'Slack Message')

        self._create_UI()
        self._connect_signals()

    def _create_UI(self):
        height = common.ROW_HEIGHT()

        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        self.channel_button = common_ui.PaintedButton(
            u'View Online', parent=self)

        self.users_group = common_ui.get_group(parent=self)
        self.message_group = common_ui.get_group(vertical=False, parent=self)

        self.send_button = common_ui.PaintedButton(u'Send', parent=self)
        self.user_filter = common_ui.LineEdit(parent=self)
        self.user_filter.setAlignment(
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.user_filter.setPlaceholderText(u'Search...')
        self.users_widget = UsersWidget(self.token, parent=self)

        self.message_widget = QtWidgets.QTextEdit(parent=self)
        self.message_widget.setStyleSheet(
            u'QTextEdit {{border-radius: {}px;}}'.format(
                common.MARGIN() * 0.33,
            )
        )
        self.message_widget.setMaximumHeight(common.ROW_HEIGHT() * 3)
        self.message_widget.setObjectName(u'SlackMessageBox')

        self.message_widget.document().setDocumentMargin(common.MARGIN() * 0.5)
        self.message_widget.setPlaceholderText(
            u'Enter a message to send...')
        self.message_widget.setAcceptRichText(False)
        self.message_widget.moveCursor(QtGui.QTextCursor.End)

        self.message_group.layout().addWidget(self.message_widget, 1)
        self.message_group.layout().addWidget(self.send_button, 0)

        row = common_ui.add_row(None, height=height, parent=self.users_group)
        row.layout().addWidget(self.channel_button, 0)
        row.layout().addWidget(self.user_filter, 1)
        self.users_group.layout().addWidget(self.users_widget, 1)

    def _connect_signals(self):
        self.initialize_timer.timeout.connect(self.initialize)

        self.send_button.clicked.connect(self.send_message)
        self.send_button.clicked.connect(
            lambda: self.overlay.setText(u'Message sent.'))
        self.channel_button.clicked.connect(self.open_url)

        self.user_filter.textChanged.connect(
            self.users_widget.model().setFilterFixedString)

    def append_message(self, v):
        self.message_widget.setFocus()
        self.message_widget.moveCursor(QtGui.QTextCursor.End)
        self.message_widget.insertPlainText(u'\n{}'.format(v))
        t = self.message_widget.toPlainText().strip()
        self.message_widget.setText(t)

    def clear_message(self):
        self.message_widget.setPlainText(u'')

    @QtCore.Slot()
    def send_message(self):
        """Sends a message using the SlackClient API.

        """
        if not self.users_widget.selectionModel().hasSelection():
            return

        index = self.users_widget.selectionModel().currentIndex()
        if not index.isValid():
            return

        if not self.message_widget.toPlainText():
            return

        message = self.message_widget.toPlainText()
        channel_id = index.data(IdRole)

        client = get_client(self.token)
        client.send_message(
            channel_id,
            message
        )
        self.message_widget.clear()

    @QtCore.Slot()
    def initialize(self):
        self.overlay.setText(u'Loading data...')
        source_model = self.users_widget.model().sourceModel()
        source_model.modelDataResetRequested.emit()
        self._initialized = True

    def showEvent(self, event):
        if not self._initialized:
            self.initialize_timer.start()

    @QtCore.Slot()
    def open_url(self):
        client = get_client(self.token)
        url = client.get_url()
        QtGui.QDesktopServices.openUrl(url)
