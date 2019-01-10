# -*- coding: utf-8 -*-
"""
Customized QMenu for displaying context menus based on action-set dictionaries.
"""

# pylint: disable=E1101, C0103, R0913, I1101
from PySide2 import QtWidgets, QtGui, QtCore


class Actions(QtWidgets.QMenu):
    """A custom QMenu."""

    def __init__(self, parent=None):
        super(Actions, self).__init__(parent=parent)
        self.setToolTipsVisible(True)
        self.add_actions()

    def showEvent(self, event):
        """Clipping the action text to fit the size of the widget upon showing."""
        for action in self.actions():
            if not action.text():
                continue

            metrics = QtGui.QFontMetrics(self.font())
            text = metrics.elidedText(
                action.text(),
                QtCore.Qt.ElideMiddle,
                self.width() - 32 - 10 # padding set in the stylesheet
            )
            action.setText(text)

    def add_actions(self):
        """Abstract method to be overriden in the subclass."""
        raise NotImplementedError('add_actions() is abstract.')

    def add_action_set(self, action_set):
        """This action populates the menu using the action-set dictionaries,
        and it automatically connects the action with a corresponding method based
        on the method's name.

        The following keys are implemented:
            disabled (bool):        Sets wheter the item is disabled.
            tip (str):              The description of the action.
            checkable (bool):       Sets wheter the item is checkable.
            checked (bool):         The state of the checkbox.

        Raises:
            NotImplementedError: When no corresponding method is found.

        """
        for k in action_set:
            if '<separator>' in k:
                self.addSeparator()
                continue

            a = self.addAction(k)

            if 'disabled' in action_set[k]:
                if action_set[k]['disabled']:
                    a.setDisabled(True)
                    continue

            attr = ''.join(k.replace(' ', '_').split()).lower()
            if not hasattr(self, attr):
                s = '{}: \'{}\' is defined in the action set, but no corresponding method found.'
                raise NotImplementedError(
                    s.format(self.__class__.__name__, attr))

            if 'tip' in action_set[k]:
                self.setStatusTip(action_set[k]['tip'])
                self.setToolTip(action_set[k]['tip'])

            if 'checkable' in action_set[k]:
                a.setCheckable(action_set[k]['checkable'])
            if 'checked' in action_set[k]:
                a.setChecked(action_set[k]['checked'])

            a.triggered.connect(getattr(self, attr))
