import sys
import os
from PySide2 import QtCore

import browser.common as common


def add_bin_dir():
    import browser
    file_info = QtCore.QFileInfo(u'{}/../bin'.format(browser.__file__))
    path = QtCore.QDir.toNativeSeparators(file_info.absoluteFilePath())

    os.environ['PATH'] = '{};{}'.format(path, os.environ['PATH'])
    return file_info


def generate_thumbnail(path):
    bin_dir = add_bin_dir()
    program = '{}/vips.exe'.format(bin_dir.absoluteFilePath())
    program = '"{}"'.format(QtCore.QDir.toNativeSeparators(program))

    process = QtCore.QProcess()
    process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
    process.setProgram(program)
    process.setArguments(['im_printdesc', path])
    # process.setArguments(['-help',])
    process.start()

    if process.waitForStarted():
        sys.stdout.write('# Browser: Thumbnail process started\n')
    process.waitForFinished(-1)
    sys.stdout.write('# Browser: Thumbnail process finished\n')

    print process.readAllStandardOutput()
    return process


exr = 'C:/temp/32L.exr'
print generate_thumbnail(exr)
