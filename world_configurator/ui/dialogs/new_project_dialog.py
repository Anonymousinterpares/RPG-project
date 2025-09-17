"""
New project dialog for the World Configurator Tool.
"""

import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QMessageBox
)

from ui.dialogs.base_dialog import BaseDialog

logger = logging.getLogger("world_configurator.ui.dialogs.new_project")

class NewProjectDialog(BaseDialog):
    """
    Dialog for creating a new project.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the dialog.
        
        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        
        self.setWindowTitle("New Project")
        self.setMinimumWidth(400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Form layout
        form = QFormLayout()
        
        # Project name field
        self.name_edit = QLineEdit("New World")
        self.name_edit.selectAll()
        form.addRow("Project Name:", self.name_edit)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.create_btn = QPushButton("Create")
        self.create_btn.clicked.connect(self._on_create)
        self.create_btn.setDefault(True)
        
        buttons.addWidget(self.cancel_btn)
        buttons.addStretch()
        buttons.addWidget(self.create_btn)
        
        layout.addLayout(buttons)
    
    def _on_create(self):
        """Handle the Create button click."""
        project_name = self.name_edit.text().strip()
        
        if not project_name:
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Please enter a project name."
            )
            return
        
        # Accept the dialog
        self.accept()
    
    def get_project_name(self) -> str:
        """
        Get the project name entered by the user.
        
        Returns:
            The project name.
        """
        return self.name_edit.text().strip()
