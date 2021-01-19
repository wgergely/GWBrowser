# -*- coding: utf-8 -*-
"""Tree view and model used to display Shotgun Steps and Tasks.

"""
from PySide2 import QtWidgets, QtCore, QtGui

from .. import common
from .. import images
from . import shotgun


__instance = None


class TaskNode(QtCore.QObject):
    """Utility class use by the TaskModel tree model.

    """

    def __init__(self, data, parentNode=None, parent=None):
        super(TaskNode, self).__init__(parent=parent)
        self.data = data
        self._children = []
        self._parentNode = parentNode

        if parentNode:
            parentNode.addChild(self)

    @property
    def name(self):
        if self.data is None:
            return 'rootNode'
        return self.data['name']

    @property
    def fullname(self):
        if self.data is None:
            return 'rootNode'
        return self.data['name']

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


class TaskModel(QtCore.QAbstractItemModel):
    """Tree model used to list Shotgun Steps and Tasks.

    """

    def __init__(self, name, node, parent=None):
        super(TaskModel, self).__init__(parent=parent)
        self._name = name
        self._rootNode = node
        self._originalRootNode = node

    @property
    def rootNode(self):
        """The current root node of the model.

        """
        return self._rootNode

    @rootNode.setter
    def rootNode(self, node):
        """The current root node of the model.

        """
        self._rootNode = node

    @property
    def originalRootNode(self):
        """The original root node of the model.

        """
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
            if node.data['type'] == shotgun.TaskEntity:
                return node.data['name']
            if node.data['type'] == shotgun.StepEntity:
                return u'{}:  {}'.format(node.data['type'], node.data['name'])

        if role == QtCore.Qt.DecorationRole:
            if node.data['type'] == shotgun.TaskEntity:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'favourite', common.ADD, common.MARGIN())
                icon = QtGui.QIcon(pixmap)
                return icon
            if node.data['type'] == shotgun.StepEntity:
                pixmap = images.ImageCache.get_rsc_pixmap(
                    u'shotgun', None, common.MARGIN())
                icon = QtGui.QIcon(pixmap)
                return icon

        if role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(0, common.ROW_HEIGHT())
        return None

    def flags(self, index, parent=QtCore.QModelIndex()):
        node = index.internalPointer()
        if node.data['type'] == shotgun.TaskEntity:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if node.data['type'] == shotgun.StepEntity:
            return QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled

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


class TaskTree(QtWidgets.QTreeView):
    """Tree view used to display the current Shotgun Steps and Tasks.

    """

    def __init__(self, parent=None):
        super(TaskTree, self).__init__(parent=parent)
        self.data = None

        self.setHeaderHidden(False)
        self.setSortingEnabled(False)
        self.setItemsExpandable(True)
        self.setRootIsDecorated(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def set_data(self, data):
        self.data = data
        node = self.data_to_nodes()
        model = TaskModel(u'Tasks', node)
        self.setModel(model)
        self.set_root_node(model.rootNode)
        self.expandAll()

    def data_to_nodes(self):
        """Builds the internalPointer structure needed to represent the data hierarchy."""
        def _get_children(node):
            for data in node.data['tasks']:
                node = TaskNode(data, parentNode=node)
                _get_children(node)

        rootNode = TaskNode(None)

        _data = {}
        for d in self.data:
            if d['step'] is not None:
                _data[d['step']['name']] = {
                    'name': d['step']['name'],
                    'id': d['step']['id'],
                    'type': d['step']['type'],
                    'tasks': [],
                }
                _data[d['step']['name']]['tasks'].append({
                    'name': d['content'],
                    'id': d['id'],
                    'type': d['type'],
                    'tasks': []
                })
            else:
                _data[d['content']] = {
                    'name': d['content'],
                    'id': d['id'],
                    'type': d['type'],
                    'tasks': []
                }
        ks = sorted(_data.keys())
        for k in ks:
            node = TaskNode(_data[k], parentNode=rootNode)
            _get_children(node)

        return rootNode

    def set_root_node(self, node):
        """Sets the given Node as the root.

        """
        if not node.children:
            return

        index = self.model().createIndexFromNode(node)
        if not index.isValid():
            return

        self.setRootIndex(index)
        self.model().rootNode = node

        index = self.model().createIndexFromNode(self.model().rootNode)
        self.setCurrentIndex(index)

    def reset_root_node(self):
        """Resets the root node to the initial node.

        """
        node = self.model().originalRootNode
        index = self.model().createIndex(0, 0, node)
        self.setRootIndex(index)
        self.setCurrentIndex(index)
        self.model().rootNode = self.model().originalRootNode

    def keyPressEvent(self, event):
        event.ignore()
