# -*- coding: utf-8 -*-
"""Version checking.

Version control is done using GitHub's REST API.

"""

import os
import requests
from packaging import version
from requests.exceptions import ConnectTimeout, ConnectionError

from PySide2 import QtWidgets, QtCore, QtGui

import gwbrowser
import gwbrowser.common as common


URL = u'https://api.github.com/repos/wgergely/GWBrowser/releases'

QtCore.Slot()
def get_latest_release():
    """Check the latest release tag on Github and compares it with the current
    version number.

    """

    # First let's check if there's a valid internet connection
    try:
        r = requests.get(u'https://dns.google', timeout=5.0)
    except ConnectTimeout:
        raise ConnectTimeout(u'# Internet connection seems to be down.')
    except ConnectionError:
        raise

    # Fetching the tag data from Github
    try:
        r = requests.get(URL, timeout=5.0)

    except ConnectTimeout as err:
        mbox = QtWidgets.QMessageBox()
        mbox.setWindowTitle(u'Could not check for updates')
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Ok)
        mbox.setText(u'An error occured connecting to the server.')
        mbox.setInformativeText(u'{}'.format(err))
        mbox.exec_()
        return
    except ConnectionError as err:
        mbox = QtWidgets.QMessageBox()
        mbox.setWindowTitle(u'Could not check for updates')
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Ok)
        mbox.setText(u'An error occured connecting to the server.')
        mbox.setInformativeText(u'{}'.format(err))
        mbox.exec_()
        return

    if not (200 <= r.status_code <= 300):
        raise ConnectionError(u'# Error {}. "{}" {}'.format(r.status_code, URL, r.reason))

    json = r.json()
    tags = [(version.parse(f[u'tag_name']).release, f) for f in json]

    # Getting the latest version
    latest = max(tags, key=lambda x: x[0])
    current_version = version.parse(gwbrowser.__version__)
    latest_version = version.parse(latest[1][u'tag_name'])

    # We're good and there's not need to update
    if current_version >= latest_version:
        mbox = QtWidgets.QMessageBox()
        mbox.setWindowTitle(u'No update needed')
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Ok)
        mbox.setText(u'GWBrowser {} is up-to-date.'.format(gwbrowser.__version__))
        mbox.exec_()

    mbox = QtWidgets.QMessageBox()
    mbox.setWindowTitle(u'A new update is available')
    mbox.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    mbox.setStandardButtons(
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    mbox.setText(u'There is a new version of GWBrowser available.')
    mbox.setText(
        u'Your current version is {} and the latest available version is {}.\nDo you want to download the new version?'.format(current_version, latest_version))
    res = mbox.exec_()

    if res == QtWidgets.QMessageBox.No:
        QtGui.QDesktopServices.openUrl(latest[1]['html_url'])
        return

    # Getting the packages...
    downloads_folder = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.DownloadLocation)

    progress_widget = QtWidgets.QProgressDialog(u'Downloading installer...', u'Cancel download', 0, 0)
    progress_widget.setWindowTitle(u'Downloading...')
    progress_widget.setWindowFlags(QtCore.Qt.FramelessWindowHint)

    # On windows, we will download the asset to the user downloads folder
    if common.get_platform() == u'win':
        asset = next((f for f in latest[1][u'assets'] if f[u'name'].endswith(u'exe')), None)

        # We will check if a file exists already...
        file_info = QtCore.QFileInfo(u'{}/{}'.format(downloads_folder, asset['name']))

        # Rename our download if the file exists already
        if file_info.exists():
            idx = 1
            _file_info = QtCore.QFileInfo(
                u'{}/{} ({}).{}'.format(
                    file_info.path(),
                    file_info.completeBaseName(),
                    idx,
                    file_info.completeSuffix(),
                )
            )
            while _file_info.exists():
                idx += 1
            file_info = _file_info
        file_path = os.path.abspath(os.path.normpath(file_info.absoluteFilePath()))

        with open(file_path, 'wb') as f:
            response = requests.get(asset[u'browser_download_url'], stream=True)
            total_length = response.headers.get('content-length')

            if total_length is None: # no content length header
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
            for data in response.iter_content(chunk_size=4096):
                QtWidgets.QApplication.instance().processEvents()
                if progress_widget.wasCanceled():
                    return
                current_length += len(data)
                f.write(data)
                progress_widget.setValue((float(current_length) / float(total_length)) * 100)
            progress_widget.close()

        if not QtCore.QProcess.startDetached(file_info.filePath(), []):
            mbox = QtWidgets.QMessageBox()
            mbox.setWindowTitle(u'Error occured.')
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Ok)
            mbox.setText(u'Could not open the installer.')
            mbox.exec_()

            common.reveal(file_info.filePath())
        # url = QtCore.QUrl.fromLocalFile(file_info.absoluteFilePath())
        # QtGui.QDesktopServices.openUrl(url)
        return

    elif common.get_platform() == u'mac':
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(URL))
        return


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    get_latest_release()
    app.exec_()
