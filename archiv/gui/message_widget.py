# /gui/message_widget.py
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import QTimer, Qt
import re, markdown

class MessageWidget(QWidget):
    def __init__(self, sender: str, text_color: str, parent=None):
        super().__init__(parent)
        self.sender = sender
        self.text_color = text_color
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 4, 0, 4)
        self.layout.setSpacing(0)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        self.label.setStyleSheet(f"color: {self.text_color}; background: transparent;")
        self.layout.addWidget(self.label)
        
        # Initialize timer properly
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_text)
        self.gradual_interval = 67
        self.full_html = ""
        self.tokens = []
        self.token_index = 0

    def setMessage(self, message: str, gradual: bool = True):
        # Clean up the message formatting
        message = message.replace('**', '')  # Remove markdown asterisks
        
        # Handle paragraph spacing
        if '\n' in message:
            paragraphs = message.split('\n')
            formatted_paragraphs = []
            for p in paragraphs:
                if p.strip():  # If paragraph is not empty
                    formatted_paragraphs.append(f'<p style="margin: 4px 0px;">{p}</p>')
            message = ''.join(formatted_paragraphs)
        
        # Add sender prefix
        if self.sender.lower() == "gamemaster":
            prefix = '<b>GameMaster:</b> '
        elif self.sender.lower() == "context":
            prefix = '<b>Context:</b> '
        else:
            prefix = f'<b>{self.sender}:</b> '

        self.full_html = prefix + message
        
        if gradual:
            self._prepare_tokens(self.full_html)
            self.token_index = 0
            self.label.setText("")
            self.timer.start(self.gradual_interval)
        else:
            self.label.setText(self.full_html)

    def _prepare_tokens(self, html: str):
        # Tokenize HTML into tags and words
        import re
        pattern = re.compile(r'(<[^>]+>)')
        self.tokens = []
        parts = pattern.split(html)
        for part in parts:
            if not part:
                continue
            if part.startswith("<") and part.endswith(">"):
                self.tokens.append(part)
            else:
                # Split text into words preserving spaces
                words = re.findall(r'\S+\s*', part)
                self.tokens.extend(words)

    def _update_text(self):
        if self.token_index < len(self.tokens):
            token = self.tokens[self.token_index]
            self.token_index += 1
            current = self.label.text()
            self.label.setText(current + token)
            self.adjustSize()  # recalc height
            self.autoScroll()  # scroll the output container so bottom is visible
        else:
            self.timer.stop()

    def autoScroll(self):
        """
        Traverse up the parent chain to find a widget with a verticalScrollBar
        and set its value to maximum.
        """
        p = self.parent()
        while p:
            if hasattr(p, "verticalScrollBar"):
                try:
                    scrollBar = p.verticalScrollBar()
                    scrollBar.setValue(scrollBar.maximum())
                except Exception:
                    pass
                break
            p = p.parent()

    def resizeEvent(self, event):
        # Constrain label width to parent's width minus a fixed margin (adjust as needed)
        if self.parent():
            self.label.setMaximumWidth(self.parent().width() - 10)
        super().resizeEvent(event)