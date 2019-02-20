# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""__init__ responsible for making the package's modules folder available
for the os.env and sys.path."""

import sys
import os
import browser
from PySide2 import QtCore

# OpenImageIO libs
file_info = QtCore.QFileInfo(u'{}/../modules/oiio'.format(browser.__file__))
path = QtCore.QDir.toNativeSeparators(file_info.absoluteFilePath())
os.environ['PATH'] = '{};{}'.format(path, os.environ['PATH'])

# Numpy
path = QtCore.QFileInfo(u'{}/../modules'.format(browser.__file__))
path = QtCore.QDir.toNativeSeparators(path.absoluteFilePath())
sys.path.insert(0, path)

path = QtCore.QFileInfo(u'{}/../modules/bin'.format(browser.__file__))
path = QtCore.QDir.toNativeSeparators(path.absoluteFilePath())
os.environ['PATH'] = '{};{}'.format(path, os.environ['PATH'])
