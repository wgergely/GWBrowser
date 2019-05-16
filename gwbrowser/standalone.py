# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101
"""GWBrowser - The module responsible for launching the app in standalone mode.
"""

import sys
import os


def check_dependency(module):
    import importlib
    try:
        importlib.import_module(module)
        sys.stdout.write('# Found {}\n'.format(module))
        return True
    except ImportError as err:
        sys.stderr.write(
            '\n\n# Missing dependency: Unabled to import {}:\n# {}\n'.format(module, err))
        return False


def run():
    """This method is responsible for running GWBrowser with an import statement."""
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


if __name__ == '__main__':
    packagepath = os.path.normpath(
        os.path.join(
            sys.argv[0],
            os.pardir,
            os.pardir,
        )
    )

    sys.path.insert(0, packagepath)

    dependencies_present = True
    for module in ['GWAlembic', 'OpenImageIO', 'PySide2', 'numpy', 'gwbrowser']:
        dependencies_present = check_dependency(module)
    if not dependencies_present:
        raise ImportError('# Unable to start GWBrowser.')

    run()
    sys.exit(0)
