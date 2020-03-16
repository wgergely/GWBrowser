if __name__ == '__main__':
    import os
    from PySide2 import QtWidgets
    import bookmarks.standalone as standalone
    import bookmarks.addfilewidget as addfilewidget

    app = standalone.StandaloneApp([])
    # widget = AddFileWidget(
    #     u'ma', file=r'J:\00_Jobs\test2\project_data\assets\apple\data\desk\000_apple_layout_gw_v0001.ma')
    widget = addfilewidget.AddFileWidget(
        u'ma')
    res = widget.exec_()

    if res == QtWidgets.QDialog.Accepted:
        print 'Accepted :)'
        with open(os.path.normpath(widget.filePath()), 'w') as f:
            f.write('Written ok!')
    if res == QtWidgets.QDialog.Rejected:
        print 'Rejected :('
    # app.exec_()
