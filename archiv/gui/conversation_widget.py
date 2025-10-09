# gui/conversation_widget.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt, QTimer, QSize
from gui.message_widget import MessageWidget

class ConversationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)  # No margins here since SafeZoneContainer handles them
        self.layout.setSpacing(10)
        self.setLayout(self.layout)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def addMessage(self, message_widget):
        self.layout.addWidget(message_widget)
        self.adjustSize()
        QTimer.singleShot(0, self.autoScroll)

    def clearMessages(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def removeLastMessage(self):
        count = self.layout.count()
        if count > 0:
            item = self.layout.takeAt(count - 1)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def autoScroll(self):
        parent = self.parent()
        while parent and not isinstance(parent, QScrollArea):
            parent = parent.parent()
        if isinstance(parent, QScrollArea):
            vsb = parent.verticalScrollBar()
            vsb.setValue(vsb.maximum())

    def sizeHint(self):
        return QSize(600, 400)  # Adjust these values based on your needs

    def saveState(self):
        """Save current conversation widget state"""
        messages = []
        layout = self.layout()  # Get the layout object without calling it
        for i in range(layout.count()):
            message_widget = layout.itemAt(i).widget()
            if message_widget:
                messages.append({
                    'sender': message_widget.sender,
                    'color': message_widget.color,
                    'message': message_widget.message
                })
        return messages

    def restoreState(self, state):
        """Restore conversation widget state"""
        self.clearMessages()
        for message_data in state:
            widget = MessageWidget(message_data['sender'], message_data['color'], self.parent())
            widget.setMessage(message_data['message'], gradual=False)
            self.addMessage(widget)