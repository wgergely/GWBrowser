import sys
import traceback

from functools import wraps


def maya(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        import maya.mel
        import maya.standalone
        from PySide2 import QtWidgets

        app = QtWidgets.QApplication.instance()

        if not app:
            app = QtWidgets.QApplication([])

        maya.standalone.initialize()

        try:
            res = func(*args, **kwargs)
            app.exec_()
        except Exception:
            sys.stderr.write(u'{}'.format(traceback.print_exc()))
        finally:
            maya.standalone.uninitialize()

    return func_wrapper


@maya
def test():
    import gwbrowser.context.mayabrowserwidget as mayabrowserwidget
    mayabrowserwidget.show()
    import maya.cmds as cmds
    c = cmds.polyCube()
    cmds.set(c)


test()
