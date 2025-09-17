# gui/dialogs/game_over_dialog.py
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPalette

class GameOverDialog(QDialog):
    """Dialog displayed when the player is defeated."""

    # Signals for button clicks
    new_game_requested = Signal()
    load_game_requested = Signal()
    load_last_save_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Game Over")
        self.setModal(True) # Block interaction with main window
        self.setMinimumSize(400, 250)
        # Remove close button, force choice via buttons
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint | Qt.FramelessWindowHint)

        # --- Styling ---
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(30, 30, 30, 0.95); /* Dark semi-transparent background */
                border: 2px solid #8B0000; /* Dark red border */
                border-radius: 15px;
            }
            QLabel#GameOverTitle {
                color: #DC143C; /* Crimson red */
                font-size: 48px;
                font-weight: bold;
                qproperty-alignment: 'AlignCenter';
                padding: 20px;
            }
            QLabel#GameOverReason {
                color: #E0E0E0; /* Light gray */
                font-size: 16px;
                qproperty-alignment: 'AlignCenter';
                padding-bottom: 20px;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: 1px solid #777777;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #666666;
                border: 1px solid #999999;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QPushButton#LoadLastSaveButton {
                background-color: #4CAF50; /* Green for emphasis */
            }
            QPushButton#LoadLastSaveButton:hover {
                background-color: #66BB69;
            }
             QPushButton#LoadLastSaveButton:pressed {
                background-color: #3B8C3E;
            }
        """)

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignCenter)

        # Title Label
        title_label = QLabel("GAME OVER")
        title_label.setObjectName("GameOverTitle")
        main_layout.addWidget(title_label, 0, Qt.AlignCenter)

        # Reason Label (optional, can be set externally)
        self.reason_label = QLabel("You have been defeated!")
        self.reason_label.setObjectName("GameOverReason")
        main_layout.addWidget(self.reason_label, 0, Qt.AlignCenter)

        # Button Layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setAlignment(Qt.AlignCenter) # Center buttons horizontally

        self.new_game_button = QPushButton("New Game")
        self.load_game_button = QPushButton("Load Game")
        self.load_last_save_button = QPushButton("Load Last Save")
        self.load_last_save_button.setObjectName("LoadLastSaveButton")

        button_layout.addWidget(self.new_game_button)
        button_layout.addWidget(self.load_game_button)
        button_layout.addWidget(self.load_last_save_button)

        main_layout.addLayout(button_layout)

        # --- Connections ---
        self.new_game_button.clicked.connect(self._on_new_game)
        self.load_game_button.clicked.connect(self._on_load_game)
        self.load_last_save_button.clicked.connect(self._on_load_last_save)

    def set_reason(self, reason: str):
        """Set the reason text displayed below GAME OVER."""
        self.reason_label.setText(reason)

    def _on_new_game(self):
        self.new_game_requested.emit()
        self.accept() # Close the dialog

    def _on_load_game(self):
        self.load_game_requested.emit()
        self.accept() # Close the dialog

    def _on_load_last_save(self):
        self.load_last_save_requested.emit()
        self.accept() # Close the dialog

    # --- Optional: Centering on Show ---
    def showEvent(self, event):
        """Center the dialog when shown."""
        super().showEvent(event)
        if self.parent():
            parent_rect = self.parent().geometry()
            self.move(parent_rect.center() - self.rect().center())