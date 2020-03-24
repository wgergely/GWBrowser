# -*- coding: utf-8 -*-
import urllib2
from slackclient import SlackClient

from PySide2 import QtWidgets, QtGui, QtCore

from bookmarks import common
import bookmarks.common_ui as common_ui
import bookmarks.settings as settings


IdRole = 4096
EmailRole = 4097
TeamRole = 4098
ImageDownloaderRole = 4099


class Slacker(QtCore.QObject):
    def __init__(self, api_token, parent=None):
        super(Slacker, self).__init__(parent=parent)
        self.slack_client = SlackClient(api_token)
        try:
            response = self.slack_client.api_call(u'auth.test')
            if not response['ok']:
                common.Log.error(response[u'error'])
            self._is_valid = response[u'ok']
        except Exception:
            common.Log.error(u'Slacker failed to connect')
            self._is_valid = False

    def isValid(self):
        return self._is_valid

    def profiles(self):
        response = self.slack_client.api_call(u'users.list')
        if not response['ok']:
            return []

        profiles = []
        for member in response[u'members']:
            if member[u'deleted']:
                continue
            if member[u'is_app_user']:
                continue
            if member[u'is_bot']:
                continue
            profile = member[u'profile']
            profile[IdRole] = member[u'id']
            profiles.append(profile)
        return profiles

    def message(self, channel, text):
        text = text.replace(u'&', u'&amp')
        # text = text.replace(u'<', u'&lt')
        # text = text.replace(u'>', u'&gt')
        response = self.slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            text=text,
            mrkdwn=True,
            unfurl_media=True,
            unfurl_links=True,
            link_names=True
        )

        if not response[u'ok']:
            # common.Log.
            raise RuntimeError(response[u'error'])


class UsersModel(QtCore.QAbstractItemModel):
    modelDataResetRequested = QtCore.Signal()

    def __init__(self, token, parent=None):
        super(UsersModel, self).__init__(parent=parent)
        self.INTERNAL_USER_DATA = {}
        self.slacker = Slacker(token, parent=self)
        self._connect_signals()

    def _connect_signals(self):
        self.modelDataResetRequested.connect(self.__initdata__)

    def __initdata__(self):
        self.beginResetModel()
        profiles = self.slacker.profiles()
        self.INTERNAL_USER_DATA = {}

        row_size = QtCore.QSize(1, common.ROW_HEIGHT() * 0.8)
        for profile in sorted(profiles, key=lambda x: self.get_name(x)):
            if u'email' not in profile:
                continue

            idx = len(self.INTERNAL_USER_DATA)
            self.INTERNAL_USER_DATA[idx] = {
                QtCore.Qt.DisplayRole: self.get_name(profile),
                QtCore.Qt.DecorationRole: QtGui.QIcon(),
                QtCore.Qt.SizeHintRole: row_size,
                QtCore.Qt.StatusTipRole: profile[u'email'],
                QtCore.Qt.ToolTipRole: profile[u'email'],
                QtCore.Qt.ForegroundRole: QtGui.QBrush(common.SECONDARY_TEXT),
                QtCore.Qt.BackgroundRole: QtGui.QBrush(common.BACKGROUND),
                QtCore.Qt.FontRole: common.font_db.secondary_font(),
                IdRole: profile[IdRole],
                EmailRole: profile[u'email'],
                TeamRole: profile[u'team'],
            }
            # self.set_icon(profile[u'image_32'], idx)
        self.endResetModel()

    def set_icon(self, url, idx, parent=None):
        try:
            response = urllib2.urlopen(url)
            file_name = QtCore.QUrl(response.geturl()).fileName()
            format = file_name.split(u'.').pop()
        except:
            return

        # Cache directory
        temp = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        temp = u'{}/{}/slack'.format(temp, common.PRODUCT)
        cache_file_path = u'{}/source_{}'.format(temp, file_name)
        QtCore.QDir(temp).mkpath('.')

        with open(cache_file_path, 'wb') as f:
            f.write(response.read())

        image = QtGui.QPixmap(cache_file_path, format=format)
        if not image.isNull():
            icon = QtGui.QIcon(image)
            self.INTERNAL_USER_DATA[idx][QtCore.Qt.DecorationRole] = icon

    def columnCount(self, index, parent=QtCore.QModelIndex()):
        return 2

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.INTERNAL_USER_DATA)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role not in self.INTERNAL_USER_DATA[index.row()]:
            return None
        return self.INTERNAL_USER_DATA[index.row()][role]

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """Bog-standard index creator."""
        return self.createIndex(row, 0, parent=parent)

    def parent(self, index):
        return QtCore.QModelIndex()

    def get_name(self, profile):
        if all((u'display_name' in profile, u'first_name' in profile, u'last_name' in profile)):
            if all((profile[u'display_name'], profile[u'first_name'], profile[u'last_name'])):
                name = u'{} ({} {})'.format(
                    profile[u'display_name'], profile[u'first_name'], profile[u'last_name'])
            elif profile[u'display_name']:
                name = profile[u'display_name']
            elif all((profile[u'first_name'], profile[u'last_name'])):
                name = u'{} {}'.format(
                    profile[u'first_name'], profile[u'last_name'])
        else:
            if u'display_name' in profile:
                name = profile[u'display_name']
            elif u'first_name' in profile and not u'last_name' in profile:
                name = profile[u'first_name']
            elif u'first_name' in profile and u'last_name' in profile:
                name = u'{} {}'.format(
                    profile[u'first_name'], profile[u'last_name'])
        if not name and u'real_name' in profile:
            name = profile[u'real_name']
        return name


class UsersWidget(QtWidgets.QListView):
    def __init__(self, token, parent=None):
        super(UsersWidget, self).__init__(parent=parent)
        self.token = token

        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setViewMode(QtWidgets.QListView.ListMode)
        self.setSpacing(0)
        self.setUniformItemSizes(True)

        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.installEventFilter(self)
        self.set_model()
        self._connect_signals()

    def _connect_signals(self):
        self.clicked.connect(self.save_selection)
        self.selectionModel().currentChanged.connect(self.save_selection)
        self.model().modelReset.connect(self.restore_selection)

    def set_model(self):
        proxy_model = QtCore.QSortFilterProxyModel(parent=self)
        proxy_model.setFilterRole(QtCore.Qt.DisplayRole)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setModel(proxy_model)

        model = UsersModel(self.token, parent=self)
        proxy_model.setSourceModel(model)

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

    def eventFilter(self, widget, event):
        if widget != self:
            return False
        if event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(common.SECONDARY_TEXT)
            o = common.MARGIN() * 0.5
            rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
            text = u'To send messages add a valid Slack API Token to the bookmark \
(select the bookmark tab and click the preferences icon).' if not self.token else u''
            text = u'Invalid Slack API Token' if not self.model(
            ).sourceModel().slacker.isValid() else text
            painter.drawText(
                rect,
                QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                text
            )
            painter.end()
            return True
        return False


class MessageWidget(QtWidgets.QSplitter):
    def __init__(self, token, parent=None):
        super(MessageWidget, self).__init__(parent=parent)
        self.token = token

        self.slack_message = u''
        self.message_widget = None
        self.users_widget = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setOrientation(QtCore.Qt.Horizontal)
        self.setWindowTitle(u'Send Slack Message')

        self._create_UI()
        self._connect_signals()

    def _create_UI(self):
        o = 0
        top_widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(top_widget)
        top_widget.layout().setContentsMargins(o, o, o, o)
        top_widget.layout().setSpacing(0)
        self.addWidget(top_widget)

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.message_widget = QtWidgets.QTextEdit(parent=self)
        self.message_widget.setPlaceholderText(
            u'Enter a message to send...')
        self.message_widget.setAcceptRichText(False)
        self.message_widget.moveCursor(QtGui.QTextCursor.End)

        top_widget.layout().addWidget(self.message_widget, 0)

        bottom_widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(bottom_widget)
        bottom_widget.layout().setContentsMargins(o, o, o, o)
        bottom_widget.layout().setSpacing(o)

        row = common_ui.add_row(u'', parent=bottom_widget)
        bottom_widget.layout().addSpacing(common.MARGIN())

        self.user_filter = common_ui.NameBase(parent=self, transparent=True)
        self.user_filter.setPlaceholderText(u'Search...')
        self.user_filter.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.user_filter)

        self.users_widget = UsersWidget(self.token, parent=self)
        bottom_widget.layout().addWidget(self.users_widget)

        self.addWidget(top_widget)
        self.addWidget(bottom_widget)

        if not self.token or not self.users_widget.model().sourceModel().slacker.isValid():
            self.message_widget.setDisabled(True)
            self.user_filter.setDisabled(True)
            self.setSizes([0, 1])
        else:
            self.setSizes([common.WIDTH() * 0.15, common.WIDTH() * 0.08])

    def _connect_signals(self):
        self.user_filter.textChanged.connect(
            self.users_widget.model().setFilterFixedString)

    def showEvent(self, event):
        self.initialize()
        self.message_widget.setFocus()

    @QtCore.Slot()
    def initialize(self):
        source_model = self.users_widget.model().sourceModel()
        if source_model:
            self.users_widget.selectionModel().blockSignals(True)
            source_model.modelDataResetRequested.emit()
            self.users_widget.selectionModel().blockSignals(False)

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
            slacker.message(channel_id, message)
        except Exception as err:
            common_ui.ErrorBox(
                u'Error sending the message.',
                u'{}'.format(err),
                parent=self
            )
            common.Log.error(u'Failed to send message.')
            return

        username = self.users_widget.selectionModel().currentIndex().data(
            QtCore.Qt.DisplayRole)
        common_ui.OkBox(
            u'Message sent',
            u'Sent to: "{}"'.format(username),
            parent=self
        ).exec_()


class SlackWidget(QtWidgets.QDialog):
    def __init__(self, url, token, parent=None):
        super(SlackWidget, self).__init__(parent=parent)
        self.message_widget = None
        self.send_button = None
        self.token = token
        self.url = url

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.Widget)
        self._create_UI()
        self._connect_signals()

    def _create_UI(self):
        common.set_custom_stylesheet(self)
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
            u'Slack Message', size=common.LARGE_FONT_SIZE(), parent=row)
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
        self.layout().addWidget(self.message_widget)

        self.send_button = common_ui.PaintedButton(u'Send', parent=self)
        self.layout().addSpacing(o)
        self.layout().addWidget(self.send_button)
        self.layout().addSpacing(o)

        if not self.token or not self.message_widget.users_widget.model().sourceModel().slacker.isValid():
            self.send_button.setDisabled(True)

    def _connect_signals(self):
        self.send_button.clicked.connect(self.message_widget.send_message)
        self.channel_button.clicked.connect(self.open_url)
        self.hide_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))

    @QtCore.Slot()
    def open_url(self):
        if not self.url:
            return
        QtGui.QDesktopServices.openUrl(self.url)

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


if __name__ == '__main__':
    common.DEBUG_ON = True
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])
    w = SlackWidget(None, None)
    w.show()
    app.exec_()
