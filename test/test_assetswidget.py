if __name__ == '__main__':
    from PySide2 import QtWidgets
    import bookmarks.standalone as standalone
    import bookmarks.assetswidget as assetswidget
    import bookmarks.common as common
    common.DEBUG_ON = True

    app = standalone.StandaloneApp([])
    l = common.LogView()
    f = assetswidget.AssetsWidget()
    f.model().sourceModel().parent_path = (
        u'//gw-workstation/jobs',
        u'EXAMPLE_JOB',
        u'project_data/shots',
    )
    f.model().sourceModel().modelDataResetRequested.emit()

    w = QtWidgets.QWidget()
    QtWidgets.QHBoxLayout(w)
    w.layout().addWidget(f)
    w.layout().addWidget(l)
    w.show()
    common.set_custom_stylesheet(w)

    app.exec_()
