# gui/advanced_config_editor/custom_widgets.py
"""
Custom widgets for the advanced configuration editor.
"""
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Qt

class AutoResizingPlainTextEdit(QPlainTextEdit):
    """
    A QPlainTextEdit that automatically resizes its height based on content.
    """
    def __init__(self, parent=None, min_lines=2, max_lines=10):
        super().__init__(parent)
        self.min_lines = min_lines
        self.max_lines = max_lines
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.document().contentsChanged.connect(self.updateHeight)
        self.updateHeight()

    def updateHeight(self):
        """
        Update the widget's height based on the document content.
        """
        fm = self.fontMetrics()
        line_height = fm.lineSpacing()
        doc_height = self.document().size().height() * line_height
        min_height = self.min_lines * line_height + 10
        max_height = self.max_lines * line_height + 10
        new_height = int(doc_height + 10)
        if new_height < min_height:
            new_height = min_height
        elif new_height > max_height:
            new_height = max_height
        self.setFixedHeight(new_height)
        if (doc_height + 10) > max_height:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)