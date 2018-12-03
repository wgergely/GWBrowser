# -*- coding: utf-8 -*-
"""Standalone runner."""
# pylint: disable=E1101, C0103, R0913, I1101

import sys
from PySide2 import QtWidgets, QtGui, QtCore

from mayabrowser.toolbar import MayaBrowserWidget

import logging
from multiprocessing import Process
import os
import sys
import tempfile


class SingleInstanceException(BaseException):
    pass


class SingleInstance(object):
    """Class that can be instantiated only once per machine."""

    def __init__(self, lockfile):
        self.initialized = False
        self.lockfile = lockfile

        logger.debug("SingleInstance lockfile: " + self.lockfile)
        if sys.platform == 'win32':
            try:
                # file already exists, we try to remove (in case previous
                # execution was interrupted)
                if os.path.exists(self.lockfile):
                    print os.path.exists(self.lockfile)
                    os.unlink(self.lockfile)
                self.fd = os.open(
                    self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except OSError:
                type, e, tb = sys.exc_info()
                if e.errno == 13:
                    logger.error(
                        "Another instance is already running, quitting.")
                    raise SingleInstanceException()
                print(e.errno)
                raise
        else:  # non Windows
            import fcntl
            self.fp = open(self.lockfile, 'w')
            self.fp.flush()
            try:
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                logger.warning(
                    "Another instance is already running, quitting.")
                raise SingleInstanceException()
        self.initialized = True

    def __del__(self):
        if not self.initialized:
            return
        try:
            if sys.platform == 'win32':
                if hasattr(self, 'fd'):
                    os.close(self.fd)
                    os.unlink(self.lockfile)
            else:
                import fcntl
                fcntl.lockf(self.fp, fcntl.LOCK_UN)
                # os.close(self.fp)
                if os.path.isfile(self.lockfile):
                    os.unlink(self.lockfile)
        except Exception as e:
            if logger:
                logger.warning(e)
            else:
                print("Unloggable error: %s" % e)
            sys.exit(-1)


logger = logging.getLogger("tendo.singleton")
logger.addHandler(logging.StreamHandler())


class StandaloneApp(QtWidgets.QApplication):
    MODEL_ID = u'browser_standalone'

    def __init__(self, args):
        super(StandaloneApp, self).__init__(args)
        self.setApplicationName('Browser')
        self.set_model_id()

        path = u'{}/{}.loc'
        tempdir = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.TempLocation)
        path = path.format(tempdir, StandaloneApp.MODEL_ID)

        try:
            SingleInstance(lockfile=path)
            self.exec_()
        except SingleInstanceException:
            sys.exit(-1)


    def exec_(self):
        widget = MayaBrowserWidget()
        widget.move(50, 50)
        widget.show()
        super(StandaloneApp, self).exec_()

    def set_model_id(self):
        """https://github.com/cztomczak/cefpython/issues/395"""
        if "win32" in sys.platform:
            import ctypes
            from ctypes.wintypes import HRESULT
            PCWSTR = ctypes.c_wchar_p
            AppUserModelID = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
            AppUserModelID.argtypes = [PCWSTR]
            AppUserModelID.restype = HRESULT
            # An identifier that is globally unique for all apps running on Windows
            hresult = AppUserModelID(self.MODEL_ID)
            assert hresult == 0, "SetCurrentProcessExplicitAppUserModelID failed"


if __name__ == '__main__':
    StandaloneApp(sys.argv)
