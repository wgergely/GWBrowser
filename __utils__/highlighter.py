# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903
"""Highligther dev."""

import re
from PySide2 import QtWidgets, QtCore, QtGui

import mayabrowser.common as common


class Highlighter(QtGui.QSyntaxHighlighter):
    """Class responsible for highlighting urls"""

    def highlightBlock(self, text):
        """Custom stlyes are applied here."""
        """The highlighting cases are defined in the common module.
        In general we're tying to replicate the ``Markdown`` syntax rendering.

        Args:
            case (str): HIGHLIGHT_RULES dicy key.
            text (str): The text to assess.

        Returns:
            tuple: int, int, int

        """
        start = 0
        end = len(text)

        flags = common.NoHighlightFlag
        for case in common.HIGHLIGHT_RULES:
            match = u''
            search = common.HIGHLIGHT_RULES[case]['re'].search(text)
            if not search:
                continue

            flags = flags | common.HIGHLIGHT_RULES[case]['flag']
            for group in search.groups():
                if not group:
                    continue
                group = u'{}'.format(group)
                group.encode('utf-8')
                match += group

            if not match:
                continue

            match.rstrip()
            start = text.find(match)
            end = len(match)

            char_format = QtGui.QTextCharFormat()
            char_format.setFont(self.document().defaultFont())

            if flags == common.NoHighlightFlag:
                self.setFormat(start, end, char_format)

            if flags & common.HeadingHighlight:
                char_format.setFontWeight(QtGui.QFont.Bold)
                char_format.setFontPointSize(self.document().defaultFont().pointSizeF() + 8 + (6 - len(match)))
                char_format.setFontCapitalization(QtGui.QFont.AllUppercase)
                if len(match) > 1:
                    char_format.setUnderlineStyle(QtGui.QTextCharFormat.SingleUnderline)
                    char_format.setFontPointSize(self.document().defaultFont().pointSizeF() + 4)
                self.setFormat(0, len(text), char_format)


            if flags & common.QuoteHighlight:
                char_format.setForeground(QtGui.QColor(100,100,100))
                char_format.setBackground(QtGui.QColor(230,230,230))
                self.setFormat(0, len(text), char_format)


            if flags & common.CodeHighlight:
                char_format.setFontWeight(QtGui.QFont.Bold)
                char_format.setForeground(common.FAVOURITE)
                self.setFormat(start, end, char_format)
            if flags & common.BoldHighlight:
                char_format.setFontWeight(QtGui.QFont.Bold)
                self.setFormat(start, end, char_format)
            if flags & common.ItalicHighlight:
                char_format.setFontItalic(True)
                self.setFormat(start, end, char_format)

        return



MARKDOWN_TEST_STRING = """
# Heading level 1
## Heading level 2
### Heading level 3
#### Heading level 4
##### Heading level 5
###### Heading level 6

Heading level 1
===============

Heading level 2
---------------

I just love **bold text**.
I just love __bold text__.
Love**is**bold

Italicized text is the *cat's meow*.
Italicized text is the _cat's meow_.
A*cat*meow

This text is ***really important***.
This text is ___really important___.
This text is __*really important*__.
This text is **_really important_**.

> Dorothy followed her through many of the beautiful rooms in her castle.

This is a file path: file://test/file path.exe
This is a file path: file://test/file path.exe -this is a dope thing!
This is a file path: "file://test/file path.exe"
This is a file path: "file://test/file path.exe" -this is a dope thing!
This is a file path: file://test/file path.exe
This is a file path: file://test/file path.exe -this is a dope thing!

This is a file path: smb://test/file path.exe
This is a file path: smb://test/file path.exe -this is a dope thing!
This is a file path: "smb://test/file path.exe"
This is a file path: "smb://test/file path.exe" -this is a dope thing!
This is a file path: smb://test/filepath.exe
This is a file path: smb://test/filepath.exe -this is a dope thing!

This is a file path: //test/file path.exe
This is a file path: //test/file path.exe -this is a dope thing!
This is a file path: "//test/file path.exe"
This is a file path: "//test/file path.exe" -this is a dope thing!
This is a file path: //test/filepath.exe
This is a file path: //test/filepath.exe -this is a dope thing!

This is a file path: \\\\test\\file path.exe
This is a file path: \\\\test\\file path.exe -this is a dope thing!
This is a file path: \"\\\\test\\file path.exe"
This is a file path: \"\\\\test\\file path.exe" -this is a dope thing!
This is a file path: \\\\test\\file path.exe
This is a file path: \\\\test\\file path.exe -this is a dope thing!



This is a folder path: file://test/file
This is a folder path: file://test/file -this is a dope thing!
This is a folder path: "file://test/file"
This is a folder path: "file://test/file" -this is a dope thing!
This is a folder path: file://test/filepath.exe
This is a folder path: file://test/filepath.exe -this is a dope thing!

This is a folder path: smb://test/file
This is a folder path: smb://test/file -this is a dope thing!
This is a folder path: "smb://test/file"
This is a folder path: "smb://test/file" -this is a dope thing!
This is a folder path: smb://test/file
This is a folder path: smb://test/file  -this is a dope thing!

This is a folder path: //test/file
This is a folder path: //test/file -this is a dope thing!
This is a folder path: "//test/file"
This is a folder path: "//test/file" -this is a dope thing!
This is a folder path: //test/filepath.exe
This is a folder path: //test/filepath.exe -this is a dope thing!

This is a folder path: \\\\test\\file
This is a folder path: \\\\test\\file -this is a dope thing!
This is a folder path: \"\\\\test\\file"
This is a folder path: \"\\\\test\\file" -this is a dope thing!
This is a folder path: \\\\test\\file path.exe
This is a folder path: \\\\test\\file path.exe -this is a dope thing!

ANd this is just a normal string.
"""


app = QtWidgets.QApplication([])
editor = QtWidgets.QTextEdit()
editor.document().setPlainText(MARKDOWN_TEST_STRING)
editor.setFixedHeight(800)
editor.setFixedWidth(600)
highlighter = Highlighter(editor.document())
highlighter.rehighlight()

editor.show()
app.exec_()
