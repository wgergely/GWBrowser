# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""This is a simple
"""

import sys


def ensure_dependency(module):
    import importlib
    try:
        importlib.import_module(module)
        sys.stdout.write('# Found {}\n'.format(module))
        return True
    except ImportError as err:
        sys.stderr.write(
            '\n\n# Missing dependency: Unabled to import {}:\n# {}\n'.format(module, err))
        return False


def exec_():
    """The main method used to launch ``GWBrowser`` as a standalone PySide2
    application.

    """
    for module in [u'GWAlembic', u'OpenImageIO', u'PySide2', u'numpy', u'gwbrowser']:
        if not ensure_dependency(module):
            raise ImportError(
                'The "{}" module is needed by GWBrowser to run but it could not be imported.')

    try:
        from PySide2 import QtCore
        import gwbrowser.standalonewidgets
        app = gwbrowser.standalonewidgets.StandaloneApp([])
        widget = gwbrowser.standalonewidgets.StandaloneBrowserWidget()
        widget.show()
        return sys.exit(app.exec_())
    except Exception as err:
        import traceback
        from PySide2 import QtWidgets
        app = QtWidgets.QApplication([])
        res = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Warning,
            u'Could not start GWBrowser',
            u'An error occured starting GWBrowser :(\n\n{}\n\n{}'.format(
                err, traceback.format_exc()),
            QtWidgets.QMessageBox.Ok)
        return sys.exit(res.exec_())
