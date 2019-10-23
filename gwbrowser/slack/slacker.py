# -*- coding: utf-8 -*-
from PySide2 import QtWidgets,QtGui,QtCore, QtNetwork
import uuid
from gwbrowser import common
from gwbrowser.common_ui import add_row, add_label, add_line_edit, PaintedButton, PaintedLabel
from slackclient import SlackClient

from gwbrowser.settings import local_settings


class Slacker(QtCore.QObject):
    SLACK_AUTH_TOKEN = local_settings.value(u'slack_access_token')
    # SLACK_AUTH_TOKEN = 'xoxb-4397889867-789355634130-G5H6xCX01Ag4NcRSOfJX5FoQ'

    def __init__(self, parent=None):
        super(Slacker, self).__init__(parent=parent)
        self.__connection__ = SlackClient(self.SLACK_AUTH_TOKEN)

    def profiles(self):
        response = self.__connection__.api_call("users.list")
        if not response['ok']:
            raise RuntimeError(response['error'])

        profiles = []
        for member in response[u'members']:
            if member[u'deleted']:
                continue
            if member[u'is_app_user']:
                continue
            if member[u'is_bot']:
                continue
            profile = member[u'profile']
            profile[u'id'] = member[u'id']
            profiles.append(profile)

        return profiles


class ImageDownloader(QtCore.QObject):
    """Utility class to download an image from a url. Used by the drag and drop operations."""

    def __init__(self, url, item, parent=None):
        super(ImageDownloader, self).__init__(parent=parent)
        self.url = QtCore.QUrl(url)
        self.item = item
        self.manager = QtNetwork.QNetworkAccessManager(parent=self)
        self.request = QtNetwork.QNetworkRequest(self.url)
        self.request.setAttribute(QtNetwork.QNetworkRequest.FollowRedirectsAttribute, True)
        self.reply = None
        # self.request.setMaximumRedirectsAllowed(10)
        self.manager.finished.connect(
            lambda reply: self.set_image(self.item, reply.readAll()))

    def get(self):
        self.reply = self.manager.get(self.request)
        if self.reply.error() != QtNetwork.QNetworkReply.NoError:
            print '# Error getting the resource for {}'.format(self.reply.url())

    def set_image(self, item, data, save_cache=False):
        """Saves the downloaded data as an image."""
        if self.reply.error() != QtNetwork.QNetworkReply.NoError:
            return

        file_name = self.reply.url().fileName()
        format = file_name.split(u'.').pop()

        if save_cache:
            # Cache directory
            cache_file_path = u'{}/{}'.format(temp, file_name)
            temp = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.TempLocation)
            temp = u'{}/gwbrowser/temp'.format(temp)
            QtCore.QDir(temp).mkpath('.')

            _file = QtCore.QFile(cache_file_path)
            _file.open(QtCore.QIODevice.WriteOnly)
            if not _file.isOpen():
                print u'Could not open {}'.format(cache_file_path)
            if _file.write(data) == -1:
                print u'Could not write image to {}'.format(cache_file_path)
            _file.close()

        image = QtGui.QImage()
        loaded = image.loadFromData(data, format=format)
        pixmap = QtGui.QPixmap()
        pixmap = pixmap.fromImage(image)
        icon = QtGui.QIcon(pixmap)
        item.setData(QtCore.Qt.DecorationRole, icon)


class UsersWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super(UsersWidget, self).__init__(parent=parent)
        self.slacker = Slacker(parent=self)
        self.add_users()

    def get_name(self, profile):
        if all((u'display_name' in profile, u'first_name' in profile, u'last_name' in profile)):
            if all((profile[u'display_name'], profile[u'first_name'], profile[u'last_name'])):
                name = u'{} ({} {})'.format(profile[u'display_name'], profile[u'first_name'], profile[u'last_name'])
            elif profile[u'display_name']:
                name = profile[u'display_name']
            elif all((profile[u'first_name'], profile[u'last_name'])):
                name = u'{} {}'.format(profile[u'first_name'], profile[u'last_name'])
        else:
            if u'display_name' in profile:
                name = profile[u'display_name']
            elif u'first_name' in profile and not u'last_name' in profile:
                name = profile[u'first_name']
            elif u'first_name' in profile and u'last_name' in profile:
                name = u'{} {}'.format(profile[u'first_name'], profile[u'last_name'])
        if not name and u'real_name' in profile:
            name = profile[u'real_name']
        return name

    def add_users(self):
        profiles = self.slacker.profiles()
        for profile in sorted(profiles, key=lambda x: self.get_name(x)):
            item = QtWidgets.QListWidgetItem()
            name = self.get_name(profile)
            item.getter = ImageDownloader(profile[u'image_72'], item, parent=self)
            item.setData(QtCore.Qt.DisplayRole, name)
            item.setData(QtCore.Qt.DecorationRole, QtGui.QIcon())
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(1, 32))
            item.setData(QtCore.Qt.UserRole, profile[u'id'])
            self.addItem(item)

        self.model()


class MessageWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MessageWidget, self).__init__(parent=parent)
        self.users_widget = None
        self.ok_button = None
        self.cancel_button = None

        self.get_timer = QtCore.QTime(parent=self)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._createUI()
        self._connectSignals()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o,o,o,o)
        self.layout().setSpacing(o)

        # text = u'Send a message on Slack'
        # label = PaintedLabel(text, color=common.TEXT, size=common.MEDIUM_FONT_SIZE, parent=self)
        # self.layout().addWidget(label)

        label = PaintedLabel(u'Send message', size=common.LARGE_FONT_SIZE, parent=self)
        self.layout().addWidget(label, 0)
        edit = QtWidgets.QTextEdit(parent=self)
        self.layout().addWidget(edit, 0)

        self.layout().addSpacing(common.MARGIN)
        label = PaintedLabel(u'Direct Messages', parent=self)
        self.layout().addWidget(label, 0)
        self.users_widget = UsersWidget(parent=self)
        self.layout().addWidget(self.users_widget, 1)

        row = add_row('', parent=self)
        self.ok_button = PaintedButton('Send')
        self.cancel_button = PaintedButton('Cancel')
        row.layout().addWidget(self.ok_button)
        row.layout().addWidget(self.cancel_button)

    def _connectSignals(self):
        self.ok_button.pressed.connect(self.close)
        self.cancel_button.pressed.connect(self.close)

    def sizeHint(self):
        return QtCore.QSize(640, 480)

    def showEvent(self, event):
        for n in xrange(self.users_widget.count()):
            item = self.users_widget.item(n)
            item.getter.get()

app = QtWidgets.QApplication([])
w = MessageWidget()
w.show()
app.exec_()
