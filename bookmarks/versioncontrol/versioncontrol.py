# -*- coding: utf-8 -*-
"""Version checking.

Version control is done using GitHub's REST API.

"""

from __future__ import absolute_import, division

import sys
import os
import urllib2
import socket
import json

from PySide2 import QtWidgets, QtCore

import bookmarks
import bookmarks.versioncontrol.version as version
import bookmarks.common as common
import bookmarks.common_ui as common_ui


URL = u'https://api.github.com/repos/wgergely/Bookmarks/releases'
responses = {
    100: ('Continue', 'Request received, please continue'),
    101: ('Switching Protocols',
          'Switching to new protocol; obey Upgrade header'),

    200: ('OK', 'Request fulfilled, document follows'),
    201: ('Created', 'Document created, URL follows'),
    202: ('Accepted',
          'Request accepted, processing continues off-line'),
    203: ('Non-Authoritative Information', 'Request fulfilled from cache'),
    204: ('No Content', 'Request fulfilled, nothing follows'),
    205: ('Reset Content', 'Clear input form for further input.'),
    206: ('Partial Content', 'Partial content follows.'),

    300: ('Multiple Choices',
          'Object has several resources -- see URI list'),
    301: ('Moved Permanently', 'Object moved permanently -- see URI list'),
    302: ('Found', 'Object moved temporarily -- see URI list'),
    303: ('See Other', 'Object moved -- see Method and URL list'),
    304: ('Not Modified',
          'Document has not changed since given time'),
    305: ('Use Proxy',
          'You must use proxy specified in Location to access this '
          'resource.'),
    307: ('Temporary Redirect',
          'Object moved temporarily -- see URI list'),

    400: ('Bad Request',
          'Bad request syntax or unsupported method'),
    401: ('Unauthorized',
          'No permission -- see authorization schemes'),
    402: ('Payment Required',
          'No payment -- see charging schemes'),
    403: ('Forbidden',
          'Request forbidden -- authorization will not help'),
    404: ('Not Found', 'Nothing matches the given URI'),
    405: ('Method Not Allowed',
          'Specified method is invalid for this server.'),
    406: ('Not Acceptable', 'URI not available in preferred format.'),
    407: ('Proxy Authentication Required', 'You must authenticate with '
          'this proxy before proceeding.'),
    408: ('Request Timeout', 'Request timed out; try again later.'),
    409: ('Conflict', 'Request conflict.'),
    410: ('Gone',
          'URI no longer exists and has been permanently removed.'),
    411: ('Length Required', 'Client must specify Content-Length.'),
    412: ('Precondition Failed', 'Precondition in headers is false.'),
    413: ('Request Entity Too Large', 'Entity is too large.'),
    414: ('Request-URI Too Long', 'URI is too long.'),
    415: ('Unsupported Media Type', 'Entity body in unsupported format.'),
    416: ('Requested Range Not Satisfiable',
          'Cannot satisfy request range.'),
    417: ('Expectation Failed',
          'Expect condition could not be satisfied.'),

    500: ('Internal Server Error', 'Server got itself in trouble'),
    501: ('Not Implemented',
          'Server does not support this operation'),
    502: ('Bad Gateway', 'Invalid responses from another server/proxy.'),
    503: ('Service Unavailable',
          'The server cannot process the request due to a high load'),
    504: ('Gateway Timeout',
          'The gateway server did not receive a timely response'),
    505: ('HTTP Version Not Supported', 'Cannot fulfill request.'),
}


socket.setdefaulttimeout(5)

QtCore.Slot()


def check():
    """Checks the latest release tag on Github and compares it with the current
    version number.

    """

    # First let's check if there's a valid internet connection
    try:
        r = urllib2.urlopen(u'http://google.com', timeout=5)
    except urllib2.URLError:
        common_ui.ErrorBox(
            u'Could not check version',
            u'Internet connection seems to be down.',
            parent=self
        ).exec_()
        common.Log.error(u'Internet connection seems to be down.')
        return
    except socket.timeout:
        common_ui.ErrorBox(
            u'Could not check version',
            u'Connection has timed out.',
            parent=self
        ).exec_()
        common.Log.error(u'Connection has timed out.')
        return

    try:
        r = urllib2.urlopen(URL, timeout=5)
        data = r.read()
    except urllib2.URLError as err:
        common_ui.ErrorBox(
            u'Could not check version',
            u'{}'.format(err)
        ).exec_()
        common.Log.error(u'Error checking the version.')
        return
    except socket.timeout as err:
        common_ui.ErrorBox(
            u'Could not check version',
            u'{}'.format(err)
        ).exec_()
        common.Log.error(u'Error checking the version.')
        return
    except RuntimeError as err:
        common_ui.ErrorBox(
            u'Could not check version',
            u'{}'.format(err)
        ).exec_()
        common.Log.error(u'Error checking the version.')
        return

    code = r.getcode()
    if not (200 <= code <= 300):
        common_ui.ErrorBox(
            u'Could not check version',
            u'# Error {}. "{}" {}'.format(code, URL, responses[code])
        ).exec_()
        common.Log.error(u'# Error {}. "{}" {}'.format(
            code, URL, responses[code]))
        return

    # Convert json to dict
    try:
        data = json.loads(data)
    except Exception as err:
        common_ui.ErrorBox(
            u'Could not check version',
            'Error occured loading the server response.\n{}'.format(err)
        ).exec_()
        common.Log.error(u'# Error {}. "{}" {}'.format(
            code, URL, responses[code]))
        return

    tags = [(version.parse(f[u'tag_name']).release, f) for f in data]

    # Getting the latest version
    latest = max(tags, key=lambda x: x[0])
    current_version = version.parse(bookmarks.__version__)
    latest_version = version.parse(latest[1][u'tag_name'])

    # We're good and there's not need to update
    if current_version >= latest_version:
        common_ui.OkBox(
            u'Already up-to-date!',
            u''
        ).exec_()
        return

    mbox = QtWidgets.QMessageBox()
    mbox.setWindowTitle(u'A new update is available')
    mbox.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    mbox.setStandardButtons(
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    mbox.setText(u'There is a new version of Bookmarks available.')
    mbox.setText(
        u'Your current version is {} and the latest available version is {}.\nDo you want to download the new version?'.format(current_version, latest_version))
    res = mbox.exec_()

    if res == QtWidgets.QMessageBox.No:
        return

    # Getting the packages...
    downloads_folder = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.DownloadLocation)

    progress_widget = QtWidgets.QProgressDialog(
        u'Downloading installer...', u'Cancel download', 0, 0)
    progress_widget.setWindowTitle(u'Downloading...')
    progress_widget.setWindowFlags(QtCore.Qt.FramelessWindowHint)

    # On windows, we will download the asset to the user downloads folder
    if common.get_platform() == u'win':
        asset = next(
            (f for f in latest[1][u'assets'] if f[u'name'].endswith(u'exe')), None)
    if common.get_platform() == u'mac':
        asset = next(
            (f for f in latest[1][u'assets'] if f[u'name'].endswith(u'zip')), None)

    # We will check if a file exists already...
    file_info = QtCore.QFileInfo(
        u'{}/{}'.format(downloads_folder, asset['name']))
    _file_info = file_info

    # Rename our download if the file exists already
    idx = 0
    while _file_info.exists():
        idx += 1
        _file_info = QtCore.QFileInfo(
            u'{}/{} ({}).{}'.format(
                file_info.path(),
                file_info.completeBaseName(),
                idx,
                file_info.completeSuffix(),
            )
        )
    file_info = _file_info
    file_path = os.path.abspath(os.path.normpath(file_info.absoluteFilePath()))

    with open(file_path, 'wb') as f:
        response = urllib2.urlopen(asset[u'browser_download_url'], timeout=5)
        total_length = response.headers['content-length']

        if total_length is None:  # no content length header
            progress_widget.setMaximum(0)
            progress_widget.forceShow()
            QtWidgets.QApplication.instance().processEvents()
            f.write(response.content)
            progress_widget.close()
            return
        else:
            progress_widget.setMaximum(100)

        current_length = 0
        progress_widget.forceShow()

        while True:
            QtWidgets.QApplication.instance().processEvents()
            data = response.read(4096)
            if not data:
                break
            if not progress_widget.wasCanceled():
                current_length += len(data)
                f.write(data)
                progress_widget.setValue(
                    (float(current_length) / float(total_length)) * 100)
            else:
                f.close()
                if os.path.exists(file_path):
                    os.remove(file_path)

    if not progress_widget.wasCanceled():
        import subprocess
        cmd = u'"{}"'.format(file_path)
        subprocess.Popen(cmd)
        common.reveal(file_path)

    progress_widget.close()
    progress_widget.deleteLater()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    check()
