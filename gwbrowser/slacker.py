# -*- coding: utf-8 -*-
from PySide2 import QtWidgets,QtGui,QtCore
import uuid
from gwbrowser import common
from gwbrowser.common_ui import add_row, add_label, add_line_edit, PaintedButton, PaintedLabel
from slackclient import SlackClient
from gwbrowser.imagecache import oiio_make_thumbnail
from gwbrowser.settings import local_settings
from gwbrowser.imagecache import ImageCache


IdRole = 4096
EmailRole = 4097
TeamRole = 4098
ImageDownloaderRole = 4099


class Slacker(QtCore.QObject):

    def __init__(self, api_token, member_id, parent=None):
        super(Slacker, self).__init__(parent=parent)
        self.api_token = api_token
        self.member_id = member_id
        self.__connection__ = SlackClient(api_token)

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

    def message(self, channel, text):
        text = text.replace(u'&', u'&amp')
        # text = text.replace(u'<', u'&lt')
        # text = text.replace(u'>', u'&gt')
        response = self.__connection__.api_call(
            "chat.postMessage",
            channel=channel,
            text=text,
            mrkdwn=True,
            unfurl_media=True,
            unfurl_links=True,
            as_user=False,
            link_names=True
        )

        if not response[u'ok']:
            raise RuntimeError(response[u'error'])



class ImageDownloader(QtCore.QObject):
    """Utility class to download an image from a url. Used by the drag and drop operations."""

    def __init__(self, url, idx, parent=None):
        super(ImageDownloader, self).__init__(parent=parent)
        self.url = QtCore.QUrl(url)
        self.idx = idx
        self.manager = QtNetwork.QNetworkAccessManager(parent=self)
        self.request = QtNetwork.QNetworkRequest(self.url)
        self.request.setAttribute(QtNetwork.QNetworkRequest.FollowRedirectsAttribute, True)
        self.reply = None
        self.manager.finished.connect(
            lambda reply: self.set_image(self.idx, reply.readAll()))

    def get(self):
        self.reply = self.manager.get(self.request)
        if self.reply.error() != QtNetwork.QNetworkReply.NoError:
            print '# Error getting the resource for {}'.format(self.reply.url())

    def set_image(self, idx, data, save_cache=False):
        """Saves the downloaded data as an image."""
        if self.reply.error() != QtNetwork.QNetworkReply.NoError:
            return

        file_name = self.reply.url().fileName()
        format = file_name.split(u'.').pop()

        # Cache directory
        temp = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.TempLocation)
        temp = u'{}/gwbrowser/temp'.format(temp)
        cache_file_path = u'{}/source_{}'.format(temp, file_name)
        QtCore.QDir(temp).mkpath('.')

        _file = QtCore.QFile(cache_file_path)
        _file.open(QtCore.QIODevice.WriteOnly)
        if not _file.isOpen():
            print u'Could not open {}'.format(cache_file_path)
        if _file.write(data) == -1:
            print u'Could not write image to {}'.format(cache_file_path)
        _file.close()

        dest = u'{}/{}.png'.format(temp, file_name.replace(u'.', u''))
        oiio_make_thumbnail(
            QtCore.QModelIndex(),
            source=cache_file_path,
            dest=dest,
            dest_size=32.0,
        )

        # image = QtGui.QImage()
        # loaded = image.loadFromData(data, format=format)
        image = QtGui.QImage(dest, format=u'png')
        image = ImageCache.resize_image(image, 24.0)
        # icon = QtGui.QIcon(pixmap)


        self.parent()._data[idx][QtCore.Qt.DecorationRole] = image
        index = self.parent().index(idx, 0)
        self.parent().dataChanged.emit(index, index)


class UsersModel(QtCore.QAbstractItemModel):
    modelDataResetRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super(UsersModel, self).__init__(parent=parent)
        self._data = {}
        self.slacker = Slacker(
            local_settings.value(u'preferences/IntegrationSettings/slack_token'),
            local_settings.value(u'preferences/IntegrationSettings/slack_member_id'),
            parent=self
        )
        self._connectSignals()

    def _connectSignals(self):
        self.modelDataResetRequested.connect(self.__initdata__)

    def __initdata__(self):
        self.beginResetModel()
        profiles = self.slacker.profiles()
        self._data = {}

        row_size = QtCore.QSize(1, 28.0)
        for profile in sorted(profiles, key=lambda x: self.get_name(x)):
            if u'email' not in profile:
                continue

            idx = len(self._data)
            self._data[idx] = {
                QtCore.Qt.DisplayRole: self.get_name(profile),
                QtCore.Qt.DecorationRole: QtGui.QIcon(),
                QtCore.Qt.SizeHintRole: row_size,
                QtCore.Qt.StatusTipRole: profile[u'email'],
                QtCore.Qt.ToolTipRole: profile[u'email'],
                QtCore.Qt.ForegroundRole: QtGui.QBrush(common.SECONDARY_TEXT),
                QtCore.Qt.BackgroundRole: QtGui.QBrush(common.BACKGROUND),
                QtCore.Qt.FontRole: common.SecondaryFont,
                IdRole: profile[u'id'],
                EmailRole: profile[u'email'],
                TeamRole: profile[u'team'],
                ImageDownloaderRole: ImageDownloader(profile[u'image_32'], idx, parent=self),
            }
        self.endResetModel()

    def columnCount(self, index, parent=QtCore.QModelIndex()):
        return 2

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._data)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role not in self._data[index.row()]:
            return None
        return self._data[index.row()][role]

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """Bog-standard index creator."""
        return self.createIndex(row, 0, parent=parent)

    def parent(self, index):
        return QtCore.QModelIndex()

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


class UsersWidget(QtWidgets.QListView):
    def __init__(self, parent=None):
        super(UsersWidget, self).__init__(parent=parent)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setViewMode(QtWidgets.QListView.ListMode)
        self.setMinimumWidth(150)

        proxy_model = QtCore.QSortFilterProxyModel(parent=self)
        proxy_model.setFilterRole(QtCore.Qt.DisplayRole)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setModel(proxy_model)
        self.setSpacing(1)
        self.setUniformItemSizes(True)
        proxy_model.setSourceModel(UsersModel(parent=self))

        self.clicked.connect(self.save_selection)
        self.selectionModel().currentChanged.connect(self.save_selection)
        self.model().modelReset.connect(self.restore_selection)
        self.setStyleSheet("""
QListView {{
    icon-size: 24px;
    padding: 1px;
}}
QListView::item {{
    background: rgba(150,150,150,30);
    border-left: 4px solid rgba(0,0,0,0);
}}
QListView::item:hover {{
    color: white;
    background: gray;
}}
QListView::item:selected {{
    border-left: 4px solid rgba({});
    color: white;
    background: gray;
}}
        """.format(common.rgb(common.REMOVE)))

    @QtCore.Slot(QtCore.QModelIndex)
    def save_selection(self, index):
        v = index.data(QtCore.Qt.DisplayRole)
        cls = self.__class__.__name__
        k = u'widgets/{}/selection'.format(cls)
        local_settings.setValue(k, v)

    @QtCore.Slot()
    def restore_selection(self):
        cls = self.__class__.__name__
        k = u'widgets/{}/selection'.format(cls)
        v = local_settings.value(k)

        for n in xrange(self.model().rowCount()):
            index = self.model().index(n, 0)
            if index.data(QtCore.Qt.DisplayRole).lower() == v.lower():
                self.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                self.setCurrentIndex(index)
                self.scrollTo(
                    index, QtWidgets.QAbstractItemView.PositionAtCenter)


class SlackMessageWidget(QtWidgets.QSplitter):
    def __init__(self, parent=None):
        super(SlackMessageWidget, self).__init__(parent=parent)
        self.__initialized = False

        self.slack_message = u''
        self.message_widget = None
        self.users_widget = None
        self.send_button = None

        self.initialize_timer = QtCore.QTimer(parent=self)
        self.initialize_timer.setSingleShot(True)
        self.initialize_timer.setInterval(800)
        self.initialize_timer.timeout.connect(self.initialize)

        self.setOrientation(QtCore.Qt.Vertical)
        self.setWindowTitle(u'Send a message with Slack')

        self._createUI()
        self._connectSignals()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        o = common.MARGIN / 2.0

        top_widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(top_widget)
        top_widget.layout().setContentsMargins(o,o,o,o)
        top_widget.layout().setSpacing(o)

        row = add_row(u'', parent=top_widget)
        label = QtWidgets.QLabel()
        pixmap = ImageCache.get_rsc_pixmap(u'slack', common.TEXT, 32.0)
        label.setPixmap(pixmap)
        row.layout().addWidget(label, 0)
        label = PaintedLabel(u'Slack Message', size=common.LARGE_FONT_SIZE, parent=self)
        row.layout().addWidget(label, 0)
        row.layout().addStretch(1)

        self.message_widget = QtWidgets.QTextEdit(parent=self)
        self.message_widget.setPlaceholderText(u'Enter the message you want to send via Slack and select the user below...')
        self.message_widget.setAcceptRichText(False)
        self.message_widget.moveCursor(QtGui.QTextCursor.End)

        top_widget.layout().addWidget(self.message_widget, 0)

        bottom_widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(bottom_widget)
        bottom_widget.layout().setContentsMargins(o,o,o,o)
        bottom_widget.layout().setSpacing(o)
        self.addWidget(top_widget)

        row = add_row(u'', parent=bottom_widget)
        label = PaintedLabel(u'Direct Messages', parent=row)
        row.layout().addWidget(label, 0)

        self.user_filter = QtWidgets.QLineEdit(parent=self)
        self.user_filter.setPlaceholderText(u'Search...')
        self.user_filter.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignRight)
        row.layout().addStretch(1)
        row.layout().addWidget(self.user_filter)

        self.users_widget = UsersWidget(parent=self)
        bottom_widget.layout().addWidget(self.users_widget)

        bottom_widget.layout().addSpacing(common.MARGIN)
        row = add_row(u'', parent=bottom_widget)
        self.send_button = PaintedButton(u'Send')
        row.layout().addWidget(self.send_button)

        self.addWidget(top_widget)
        self.addWidget(bottom_widget)

    def _connectSignals(self):
        self.send_button.pressed.connect(self.send_message)
        self.user_filter.textChanged.connect(self.users_widget.model().setFilterFixedString)

    def showEvent(self, event):
        self.initialize_timer.start()
        self.message_widget.setFocus()

    @QtCore.Slot()
    def initialize(self):
        if self.__initialized:
            return

        source_model = self.users_widget.model().sourceModel()
        self.users_widget.selectionModel().blockSignals(True)
        source_model.modelDataResetRequested.emit()
        for n in source_model._data:
            source_model._data[n][ImageDownloaderRole].get()
        self.users_widget.selectionModel().blockSignals(False)

        self.__initialized = True

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
        if not self.message_widget.toPlainText():
            return

        index = self.users_widget.selectionModel().currentIndex()
        channel_id = index.data(IdRole)

        try:
            slacker = self.users_widget.model().sourceModel().slacker
            message = self.message_widget.toPlainText()
            if slacker.member_id:
                message = u'<@{}>:\n{}'.format(slacker.member_id, message)
            slacker.message(
              channel_id,
              message
            )
        except:
            raise

        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Slack: Message sent')
        username = self.users_widget.selectionModel().currentIndex().data(QtCore.Qt.DisplayRole)
        mbox.setText(
            u'Successfully messaged {}'.format(username)
        )
        mbox.setInformativeText(
            u'Do you want to send a message to another user?')
        mbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        mbox.setDefaultButton(QtWidgets.QMessageBox.No)

        res = mbox.exec_()

        if res == QtWidgets.QMessageBox.Yes:
            return
        self.parent().parent().listcontrolwidget.listChanged.emit(2)
        self.message_widget.setPlainText(u'')



if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = SlackMessageWidget()
    w.show()
    app.exec_()
