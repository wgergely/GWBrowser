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

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import urllib2
from slackclient import SlackClient

from PySide2 import QtWidgets, QtGui, QtCore

import bookmarks.log as log
import bookmarks.common as common
import bookmarks.common_ui as common_ui
import bookmarks.images as images
import bookmarks.settings as settings


IdRole = QtCore.Qt.UserRole + 1
ThumbnailHashRole = IdRole + 1
ThumbnailUrlRole = ThumbnailHashRole + 1


instance = None


class Client(SlackClient):
    """The Slack client used to send messages.

    """

    def __init__(self, token):
        super(Client, self).__init__(token)
        # 'url' and 'user_id' can be used to tell us more about the Slack bot or app
        self._response = {}

    def verify_token(self, silent=False):
        """Tests the slack token and the permissions needed to send messages to
        channels.

        Using the Conversations API,the app requires any `channels:read` and/or
        `groups:read` to get channel lists.

        Addittionally, `chat.write` and `users.read` are *required* to send messages.

        """
        # Checking the token's validity
        response = self.api_call(u'auth.test')
        if not response['ok']:
            s = u'Maybe a required scope is missing?.\nError: "{}"'.format(
                response[u'error'])
            log.error(s)
            if not silent:
                common_ui.ErrorBox(u'Slack Token Error.', s).open()
            raise ValueError(s)
        self._response = response

        # Check if we can read channels
        response = self.api_call(u'conversations.list')
        if not response['ok']:
            s = u'Maybe a required scope is missing?\nError: "{}"'.format(
                response[u'error'])
            log.error(s)
            if not silent:
                common_ui.ErrorBox(u'Slack Token Error.', s).open()
            raise ValueError(s)

        # Checking users scope
        for method in ('users.info', 'users.list'):
            response = self.api_call(method, user=self._response['user_id'])
            if not response['ok']:
                s = u'Maybe a required scope is missing?\nError: "{}"'.format(
                    response[u'error'])
                if 'needed' in response:
                    s += '\nScope needed: "{}"'.format(response['needed'])
                log.error(s)
                if not silent:
                    common_ui.ErrorBox(u'Slack Token Error.', s).open()
                raise ValueError(s)

    def get_user_profiles(self, silent=False):
        """Returns all available profiles in the workspace associated with the
        token. Make sure scope `users.read` is available for the token.

        Raises:
            ValueError:     If the token is invalid or missing scope.

        """
        def _get_profiles(response):
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

        method = u'users.list'
        limit = 20
        profiles = []

        # Getting the user-list in segments as per the Slack API documentation
        # `limit` sets the number of entries to get with each call
        response = self.api_call(method, limit=limit)
        profiles += _get_profiles(response)
        while response['response_metadata']['next_cursor']:
            response = self.api_call(
                method, limit=limit, cursor=response['response_metadata']['next_cursor'])
            profiles += _get_profiles(response)

        return profiles

    def get_channels(self, silent=False):
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
        """Send message using slackclient.

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
    row_size = QtCore.QSize(1, common.ROW_HEIGHT() * 0.8)

    def __init__(self, token, parent=None):
        super(UsersModel, self).__init__(parent=parent)
        self.client = Client(token)

        self.INTERNAL_USER_DATA = common.DataDict()
        self.modelDataResetRequested.connect(self.__initdata__)

    def __initdata__(self):
        self.beginResetModel()

        self.INTERNAL_USER_DATA = common.DataDict()
        channels = self.client.get_channels()
        profiles = self.client.get_user_profiles()

        # Channels
        try:
            for channel in sorted(channels, key=lambda x: x['name']):
                idx = len(self.INTERNAL_USER_DATA)
                self.INTERNAL_USER_DATA[idx] = common.DataDict({
                    QtCore.Qt.DisplayRole: u'Channel:  ' + channel['name'],
                    QtCore.Qt.DecorationRole: QtGui.QIcon(),
                    QtCore.Qt.SizeHintRole: self.row_size,
                    QtCore.Qt.FontRole: common.font_db.primary_font(font_size=common.SMALL_FONT_SIZE())[0],
                    IdRole: channel[u'id'],
                    ThumbnailHashRole: None,
                    ThumbnailUrlRole: None,
                })
        except Exception as e:
            log.error(u'Could not get channels.')

        try:
            for profile in sorted(profiles, key=self.get_pretty_name):
                idx = len(self.INTERNAL_USER_DATA)
                self.INTERNAL_USER_DATA[idx] = common.DataDict({
                    QtCore.Qt.DisplayRole: self.get_pretty_name(profile),
                    QtCore.Qt.DecorationRole: QtGui.QIcon(),
                    QtCore.Qt.SizeHintRole: self.row_size,
                    QtCore.Qt.FontRole: common.font_db.primary_font(font_size=common.SMALL_FONT_SIZE())[0],
                    IdRole: profile[u'id'],
                    ThumbnailHashRole: profile[u'profile']['avatar_hash'],
                    ThumbnailUrlRole: profile[u'profile']['image_32'],
                })
                index = self.index(idx, 0)
                self.get_icon(index)
        except Exception as e:
            log.error('Could not get profiles')

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
            log.error('Could not save thumbnail')
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
        #
        # self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        # self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        # self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        proxy_model = QtCore.QSortFilterProxyModel(parent=self)
        proxy_model.setFilterRole(QtCore.Qt.DisplayRole)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setModel(proxy_model)
        model = UsersModel(token, parent=self)
        proxy_model.setSourceModel(model)

        self.clicked.connect(self.save_selection)
        self.selectionModel().currentChanged.connect(self.save_selection)
        self.model().modelReset.connect(self.restore_selection)

    @QtCore.Slot(QtCore.QModelIndex)
    def save_selection(self, index):
        v = index.data(QtCore.Qt.DisplayRole)
        cls = self.__class__.__name__
        k = u'widgets/{}/selection'.format(cls)
        settings.local_settings.setValue(k, v)

    @QtCore.Slot()
    def restore_selection(self):
        cls = self.__class__.__name__
        k = u'widgets/{}/selection'.format(cls)
        v = settings.local_settings.value(k)

        if not v:
            return

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if index.data(QtCore.Qt.DisplayRole).lower() == v.lower():
                self.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.setCurrentIndex(index)
                self.scrollTo(
                    index, QtWidgets.QAbstractItemView.PositionAtCenter)


class MessageWidget(QtWidgets.QSplitter):
    def __init__(self, token, parent=None):
        super(MessageWidget, self).__init__(parent=parent)
        self.token = token

        self.slack_message = u''
        self.message_widget = None
        self.users_widget = None

        self.setOrientation(QtCore.Qt.Horizontal)
        self.setWindowTitle(u'Send Message')
        # self.setStyleSheet('border: 1px solid rgba(0,0,0,50);')

        self._create_UI()
        self._connect_signals()

    def _create_UI(self):
        o = 0
        top_widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(top_widget)
        top_widget.layout().setContentsMargins(o, o, o, o)
        top_widget.layout().setSpacing(0)
        self.addWidget(top_widget)

        self.message_widget = QtWidgets.QTextEdit(parent=self)
        _o = common.MARGIN()
        self.message_widget.document().setDocumentMargin(_o)
        self.message_widget.setPlaceholderText(
            u'Enter a message to send...')
        self.message_widget.setAcceptRichText(False)
        self.message_widget.moveCursor(QtGui.QTextCursor.End)

        top_widget.layout().addWidget(self.message_widget, 0)

        bottom_widget = QtWidgets.QWidget(parent=self)
        o = common.MARGIN() * 0.5
        height = common.ROW_HEIGHT()
        QtWidgets.QVBoxLayout(bottom_widget)
        bottom_widget.layout().setContentsMargins(o, 0, o, 0)
        bottom_widget.layout().setSpacing(0)

        row = common_ui.add_row(u'', height=height, parent=bottom_widget)
        row.layout().setAlignment(QtCore.Qt.AlignBottom)
        label = common_ui.PaintedLabel(
            u'Channels & Direct Messages', parent=self)
        row.layout().addWidget(label, 0)

        row = common_ui.add_row(u'', height=height, parent=bottom_widget)
        row.layout().setAlignment(QtCore.Qt.AlignBottom)

        self.user_filter = common_ui.LineEdit(parent=self)
        self.user_filter.setAlignment(
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.user_filter.setPlaceholderText(u'Search...')
        row.layout().addWidget(self.user_filter, 1)

        self.users_widget = UsersWidget(self.token, parent=self)

        bottom_widget.layout().addWidget(self.users_widget)

        self.addWidget(bottom_widget)
        self.addWidget(top_widget)

        self.setSizes([common.WIDTH() * 0.08, common.WIDTH() * 0.2])

    def _connect_signals(self):
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
        client = self.users_widget.model().sourceModel().client

        client.send_message(channel_id, message)

        common_ui.OkBox(
            u'Sent!',
            u'Message sent to "{}".'.format(index.data(QtCore.Qt.DisplayRole)),
        ).open()


class SlackWidget(QtWidgets.QDialog):
    def __init__(self, token, parent=None):
        super(SlackWidget, self).__init__(parent=parent)
        self._initialized = False
        self.initialize_timer = QtCore.QTimer(parent=self)
        self.initialize_timer.setInterval(1000)
        self.initialize_timer.setSingleShot(True)

        self.overlay = LoadingWidget(parent=self)

        self.message_widget = None
        self.send_button = None
        self.token = token

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.Widget)

        self._create_UI()
        self._connect_signals()

    def _create_UI(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(common.INDICATOR_WIDTH())

        height = common.ROW_HEIGHT() * 0.7
        row = common_ui.add_row(None, height=height, padding=None, parent=self)

        self.channel_button = common_ui.ClickableIconButton(
            u'slack',
            (common.TEXT, common.TEXT),
            height,
        )
        label = common_ui.PaintedLabel(
            u'Send Message', size=common.LARGE_FONT_SIZE(), parent=row)
        label.setFixedHeight(height)
        self.hide_button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            height,
            parent=row
        )

        row.layout().addWidget(label, 0)
        row.layout().addStretch(1)
        row.layout().addWidget(self.channel_button, 0)
        row.layout().addWidget(self.hide_button, 0)

        self.message_widget = MessageWidget(self.token, parent=self)
        self.layout().addSpacing(o * 0.5)
        self.layout().addWidget(self.message_widget)

        self.send_button = common_ui.PaintedButton(u'Send', parent=self)
        self.layout().addSpacing(o)
        self.layout().addWidget(self.send_button)
        self.layout().addSpacing(o * 0.5)

    @QtCore.Slot()
    def initialize(self):
        source_model = self.message_widget.users_widget.model().sourceModel()
        source_model.modelDataResetRequested.emit()
        self.overlay.deleteLater()
        self.overlay = None
        self._initialized = True

    def showEvent(self, event):
        self.message_widget.setFocus()
        if not self._initialized:
            self.overlay.setGeometry(self.geometry())
            pos = self.geometry().topLeft()
            pos = self.mapToGlobal(pos)
            self.overlay.move(pos)
            self.overlay.show()
            self.initialize_timer.start()

    def _connect_signals(self):
        self.initialize_timer.timeout.connect(self.initialize)

        self.send_button.clicked.connect(self.message_widget.send_message)
        self.channel_button.clicked.connect(self.open_url)
        self.hide_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))

    @QtCore.Slot()
    def open_url(self):
        client = self.message_widget.users_widget.model().sourceModel().client
        if not client._response:
            return
        QtGui.QDesktopServices.openUrl(client._response['url'])

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(common.BACKGROUND)
        o = common.MARGIN() * 0.3
        painter.setOpacity(0.95)
        painter.drawRoundedRect(
            self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o)), common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())
        painter.end()


class LoadingWidget(QtWidgets.QWidget):
    """..."""
    textChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(LoadingWidget, self).__init__(parent=parent)
        self._text = u'Loading...'
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self.textChanged.connect(self.setText)

    @QtCore.Slot(unicode)
    def setText(self, text):
        self._text = text
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        o = common.MARGIN()
        o = 0
        rect = self.rect().marginsRemoved(QtCore.QMargins(o,o,o,o))

        painter.setBrush(common.SEPARATOR)
        painter.setPen(QtCore.Qt.NoPen)

        painter.setOpacity(0.5)
        painter.drawRoundedRect(rect, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())
        painter.setOpacity(1.0)

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(common.TEXT)
        painter.setFont(common.font_db.primary_font(common.MEDIUM_FONT_SIZE())[0])

        painter.drawText(
            rect,
            QtCore.Qt.AlignCenter,
            self._text
        )
        painter.end()



if __name__ == '__main__':
    common.DEBUG_ON = True
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])
    w = SlackWidget(None, None)
    w.show()
    app.exec_()
