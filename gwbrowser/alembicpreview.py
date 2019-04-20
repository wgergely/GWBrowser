# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0201


"""Widget responsible for displaying the contents of an alembic file."""


import sys

from PySide2 import QtCore, QtWidgets, QtGui

import alembic.alembic as alembic
import gwbrowser.common as common



class AlembicNode(QtCore.QObject):
    """Small wrapper around the iobject hierarchy to display it in a QTreeView."""

    def __init__(self, iobject=None, parentNode=None, parent=None):
        super(AlembicNode, self).__init__(parent=parent)

        self.iobject = iobject
        self._children = []
        self._parentNode = parentNode

        if parentNode:
            parentNode.addChild(self)

    @property
    def name(self):
        """The name of this node."""
        props = self.iobject.getProperties()
        props.getNumProperties()
        name = self.iobject.getName()
        name = u'{} ({})'.format(
            self.iobject.getName(), props.getPropertyHeader(0))
        return name

    @property
    def fullname(self):
        """The name of this node."""
        if not self.iobject:
            return 'rootNode'
        return self.iobject.getFullName()

    def removeSelf(self):
        """Removes itself from the parent's children."""
        if self.parentNode:
            if self in self.parentNode.children:
                idx = self.parentNode.children.index(self)
                del self.parentNode.children[idx]

    def removeChild(self, child):
        """Remove the given node from the children."""
        if child in self.children:
            idx = self.children.index(child)
            del self.children[idx]

    def addChild(self, child):
        """Add a child node."""
        self.children.append(child)

    @property
    def children(self):
        """Children of the node."""
        return self._children

    @property
    def childCount(self):
        """Children of the this node."""
        return len(self._children)

    @property
    def parentNode(self):
        """Parent of this node."""
        return self._parentNode

    @parentNode.setter
    def parentNode(self, node):
        self._parentNode = node

    def getChild(self, row):
        """Child at the provided index/row."""
        if row < self.childCount:
            return self.children[row]
        return None

    @property
    def row(self):
        """Row number of this node."""
        if self.parentNode:
            return self.parentNode.children.index(self)
        return None


class AlembicModel(QtCore.QAbstractItemModel):
    """Simple tree model to browse the data-structure of the alembic."""

    def __init__(self, node, parent=None):
        super(AlembicModel, self).__init__(parent=parent)
        self._rootNode = node
        self._originalRootNode = node

    @property
    def rootNode(self):
        """ The current root node of the model """
        return self._rootNode

    @rootNode.setter
    def rootNode(self, node):
        """ The current root node of the model """
        self._rootNode = node

    @property
    def originalRootNode(self):
        """ The original root node of the model """
        return self._originalRootNode

    def rowCount(self, parent):
        """Row count."""
        if not parent.isValid():
            parentNode = self.rootNode
        else:
            parentNode = parent.internalPointer()
        return parentNode.childCount

    def columnCount(self, parent):  # pylint: disable=W0613
        """Column count."""
        return 1

    def parent(self, index):
        """The parent of the node."""
        node = index.internalPointer()
        if not node:
            return QtCore.QModelIndex()

        parentNode = node.parentNode

        if not parentNode:
            return QtCore.QModelIndex()
        elif parentNode == self.rootNode:
            return QtCore.QModelIndex()
        elif parentNode == self.originalRootNode:
            return QtCore.QModelIndex()

        return self.createIndex(parentNode.row, 0, parentNode)

    def index(self, row, column, parent):
        """Returns a QModelIndex()."""
        if not parent.isValid():
            parentNode = self.rootNode
        else:
            parentNode = parent.internalPointer()

        childItem = parentNode.getChild(row)
        if not childItem:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, childItem)

    def data(self, index, role):  # pylint: disable=W0613
        """Name data."""
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return node.name
        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(300, 28)

    def headerData(self, section, orientation, role):  # pylint: disable=W0613
        """Static header data."""
        return 'Name'

    def createIndexFromNode(self, node):
        """ Creates a QModelIndex based on a Node """
        if not node.parentNode:
            return QtCore.QModelIndex()

        if node not in node.parentNode.children:
            raise ValueError('Node\'s parent doesn\'t contain the node.')

        idx = node.parentNode.children.index(node)
        return self.createIndex(idx, 0, node)


class AlembicView(QtWidgets.QTreeView):
    def __init__(self, path, parent=None):
        super(AlembicView, self).__init__(parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )

        if not QtCore.QFileInfo(path).exists():
            return
        self._abc = alembic.Abc.IArchive(path)
        node = self.alembic_to_nodes()
        model = AlembicModel(node)
        self.setModel(model)
        self.setRootNode(model.rootNode)
        self.expandAll()

        self.setHeaderHidden(False)
        # self.header().setSortIndicatorShown(False)
        self.setSortingEnabled(False)
        self.setItemsExpandable(False)
        self.setRootIsDecorated(False)

        self.setStyleSheet("""
QWidget {{
	border-width: 0px;
	border: none;
	margin: 0px;
	padding: 0px;
	outline: 0;
    font-size: {MEDIUM_FONT_SIZE}pt;
    font-family: "{PRIMARY_FONT}";
}}
QTreeView {{
    padding: 12px;
    background-color: rgba(100,100,100,150);
    color: rgba(255,255,255,250);
    show-decoration-selected: 0;
}}

QTreeView::item {{
    background: rgba(78,78,78,255);
    border: none;
    padding-left: 12px;
}}

QTreeView::item:hover {{
    background: rgba(150,150,150,255);
    border: none;
}}

QTreeView::item:selected {{
    background: rgba(150,150,150,255);
    color: rgba(250,250,250,250);
}}

QTreeView::item:selected:active {{
    background: rgba(180,180,180,255);
}}

QTreeView::item:selected:!active {{
    background: rgba(180,180,180,255);
}}

QTreeView::branch {{
    background: rgba(78,78,78,255);
}}
QTreeView::branch:hover {{
    background: rgba(78,78,78,255);
}}

        """.format(
            MEDIUM_FONT_SIZE=common.MEDIUM_FONT_SIZE,
            PRIMARY_FONT=common.PrimaryFont.family()

        ))

        self.setFixedWidth(1024)
        self.setFixedHeight(1024)

    def alembic_to_nodes(self):
        """Builds the internal node-structure needed to make the alembic model."""
        def _get_children(node):
            for idx in xrange(node.iobject.getNumChildren()):
                child = node.iobject.getChild(idx)
                nnode = AlembicNode(child, parentNode=node)
                _get_children(nnode)

        rootNode = AlembicNode('rootNode')

        if not self._abc.valid():
            return rootNode

        node = AlembicNode(self._abc.getTop(), parentNode=rootNode)

        # Info
        _get_children(node)
        return rootNode

    @property
    def expandedNodes(self):
        """Currently expanded nodes."""
        return self._expandedNodes

    @property
    def selectedNode(self):
        """The node associated with the tree-view selection."""
        index = next((f for f in self.selectedIndexes()), None)
        if not index:
            return None
        return index.internalPointer()

    def setRootNode(self, node):
        """ Sets the given Node as the root """
        if not node.children:
            return

        index = self.model().createIndexFromNode(node)
        if not index.isValid():
            return

        self.setRootIndex(index)
        self.model().rootNode = node

        index = self.model().createIndexFromNode(self.model().rootNode)
        self.setCurrentIndex(index)

    def resetRootNode(self):
        """Resets the root node to the initial node."""
        node = self.model().originalRootNode
        index = self.model().createIndex(0, 0, node)
        self.setRootIndex(index)
        self.setCurrentIndex(index)
        self.model().rootNode = self.model().originalRootNode

    def alembic_to_plaintext(self, abc):
        """Parses the alembic structure and returns a string representation of it."""
        def _get_children(parent, text, numchildren):
            if not parent.valid():
                return text

            for idx in xrange(numchildren):
                child = parent.getChild(idx)
                childnumchildren = child.getNumChildren()
                name = child.getName().split(':')[-1]
                if idx != (numchildren - 1):
                    if childnumchildren:
                        text += u'├── {}/\n|   '.format(name)
                    else:
                        text += u' └── {}/\n'.format(name)
                else:
                    if childnumchildren:
                        text += u'└── {}\n   '.format(name)
                    else:
                        text += u' └── {}\n'.format(name)
                text = _get_children(child, text, child.getNumChildren())
            return text
        if not abc.valid():
            return u'{} is not valid.'.format(abc)

        text = u'{}/\n'.format(QtCore.QFileInfo(abc.getName()).fileName())
        text = _get_children(abc.getTop(), text,
                             abc.getTop().getNumChildren())
        return text.encode('utf-8')


def get_alembic_thumbnail(path):
    """Renders the alembic structure as a QImage."""
    widget = AlembicView(path)
    pixmap = QtGui.QPixmap(1024, 1024)
    painter = QtGui.QPainter()
    painter.begin(pixmap)
    widget.render(painter, widget.rect().topLeft(), widget.rect())
    painter.end()

    return widget


if __name__ == '__main__':
    path = r'\\sloth\jobs\audible_8100\films\vignettes\shots\AU_dragon_lady\exports\abc\head_from_rig_v005.abc'
    app = QtWidgets.QApplication([])
    widget = AlembicView(path)
    # widget.show()

    pixmap = QtGui.QPixmap(1024, 1024)
    painter = QtGui.QPainter()
    painter.begin(pixmap)
    widget.render(painter, widget.rect().topLeft(), widget.rect())
    painter.end()

    label = QtWidgets.QLabel()
    label.setFixedWidth(1024)
    label.setFixedHeight(1024)
    label.setPixmap(pixmap)
    label.show()
    app.exec_()
