import functools
from PySide2 import QtWidgets, QtCore, QtGui

import bookmarks.asset_config.asset_config as config
import bookmarks.common as common
import bookmarks.common_ui as common_ui
import bookmarks.images as images


class AssetConfigEditor(QtWidgets.QWidget):

    def __init__(self, server, job, root, parent=None):
        super(AssetConfigEditor, self).__init__(parent=parent)
        self.current_data = {}
        self.changed_data = {}

        self.scrollarea = None
        self.config = config.AssetConfig(
            server,
            job,
            root,
            parent=self
        )

        self._create_ui()
        self._connect_signals()


    def _add_title(self, icon, label, parent, color=None):
        o = common.MARGIN()
        h = common.ROW_HEIGHT()
        row = common_ui.add_row(u'', parent=parent)
        _label = QtWidgets.QLabel(parent=parent)
        pixmap = images.ImageCache.get_rsc_pixmap(icon, color, h * 0.7)
        _label.setPixmap(pixmap)
        row.layout().addWidget(_label, 0)
        label = common_ui.PaintedLabel(
            label,
            size=common.MEDIUM_FONT_SIZE(),
            parent=self
        )
        row.layout().addWidget(label, 0)
        row.layout().addStretch(1)
        parent.layout().addSpacing(o * 0.5)

    def _create_ui(self):
        common.set_custom_stylesheet(self)

        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        h = common.ROW_HEIGHT()
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o)

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)

        parent = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(parent)
        parent.layout().setAlignment(QtCore.Qt.AlignCenter)
        parent.layout().setContentsMargins(o, o, o, o)
        parent.layout().setSpacing(o)
        self.scrollarea.setWidget(parent)

        self.layout().addWidget(self.scrollarea)

        data = self.data()
        for section in config.REQUIRED_SECTIONS:
            if section not in data:
                continue

            maingroup = common_ui.get_group(margin=o * 0.5, parent=parent)
            self._add_title(
                u'settings',
                section.replace('_', ' ').title(),
                maingroup,
                color=common.SECONDARY_BACKGROUND
            )

            for k, v in data[section].iteritems():
                _grp = common_ui.get_group(parent=maingroup)
                row = common_ui.add_row(k, height=h, parent=_grp)
                editor = common_ui.LineEdit(parent=row)

                # Text changed signal
                editor.setText(v['value'])
                key = u'{}/{}/value'.format(section, k)
                self.current_data[key] = v['value']
                editor.textChanged.connect(
                    functools.partial(self.text_changed, key, editor))

                row.layout().addWidget(editor)

                if 'description' in v:
                    common_ui.add_description(v['description'], label=u' ', parent=_grp)

                if 'filter' in v:
                    row = common_ui.add_row('File formats', height=h, parent=_grp)
                    editor = common_ui.LineEdit(parent=row)

                    editor.setText(v['filter'])
                    key = u'{}/{}/filter'.format(section, k)
                    self.current_data[key] = v['filter']
                    editor.textChanged.connect(
                        functools.partial(self.text_changed, key, editor))

                    row.layout().addWidget(editor)

                if 'subfolders' in v:
                    row = common_ui.add_row(u'Subfolders', height=None, parent=_grp)
                    grp__ = common_ui.get_group(parent=row)

                    for _k, _v in v['subfolders'].iteritems():
                        row = common_ui.add_row(_k, height=h, parent=grp__)
                        editor = common_ui.LineEdit(parent=row)

                        editor.setText(_v['value'])
                        key = u'{}/{}/subfolders/{}/value'.format(section, k, _k)
                        self.current_data[key] = _v['value']
                        editor.textChanged.connect(
                            functools.partial(self.text_changed, key, editor))

                        row.layout().addWidget(editor)

                        if 'description' in _v:
                            common_ui.add_description(_v['description'], label=u' ', parent=grp__)

    @QtCore.Slot(unicode)
    @QtCore.Slot(unicode)
    @QtCore.Slot(QtWidgets.QWidget)
    def text_changed(self, key, editor, v):
        """Slot responsible for marking an entry as changed.

        """
        if v != self.current_data[key]:
            self.changed_data[key] = v
            editor.setStyleSheet('color: rgba({});'.format(common.rgb(common.ADD)))
            return

        if key in self.changed_data:
            del self.changed_data[key]
        editor.setStyleSheet('color: rgba({});'.format(common.rgb(common.TEXT)))

    @QtCore.Slot()
    def save_changes(self):
        """Save values to the bookmark database.

        We'll only save values that have been changed.

        """
        data = {}

        for k in self.changed_data:
            v = data
            keys = k.split('/')

            while keys:
                _k = keys.pop(0)

                if not keys:
                    v[_k] = self.changed_data[k]
                    break

                if _k not in v:
                    v[_k] = {}
                v = v[_k]

        self.config.set_data(data)



    def data(self, force=False):
        return self.config.get_data(force=force)

    def _connect_signals(self):
        pass


import bookmarks.standalone as standalone
app = standalone.StandaloneApp([])
w = AssetConfigEditor(
    u'//gw-workstation/jobs',
    u'AKA_national_geographic',
    u'data/edit',
)
w.show()
app.exec_()
