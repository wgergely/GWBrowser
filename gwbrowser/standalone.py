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

        sys.stdout.write('# Starting Standalone app...\n')
        app = gwbrowser.standalonewidgets.StandaloneApp(sys.argv)
        sys.stdout.write('# Making window...\n')
        widget = gwbrowser.standalonewidgets.StandaloneBrowserWidget()
        widget.show()
        app.exec_()
        raise SystemExit(0)
    except Exception as err:
        try:
            import traceback
            from PySide2 import QtWidgets
            app = QtWidgets.QApplication([])
            res = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                u'Could not start GWBrowser',
                u'An error occured starting GWBrowser :(\n\n{}\n\n{}'.format(
                    err, traceback.format_exc()),
                QtWidgets.QMessageBox.Ok)
            return res.exec_()
        except Exception as err:
            raise RuntimeError(
                '# An error occured starting GWBrowser:\n{}'.format(err))
        finally:
            raise SystemExit(0)
    finally:
        raise SystemExit(0)


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
    for module in ['OpenImageIO', 'PySide2', 'numpy', 'gwbrowser']:
        dependencies_present = check_dependency(module)
    if not dependencies_present:
        raise ImportError('# Unable to start GWBrowser.')

    res = run()
    sys.stdout.write('Browser exited with code {}'.format(res))
