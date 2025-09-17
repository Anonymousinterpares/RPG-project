#!/usr/bin/env python3
"""
Model management widget for LLM settings.

This module provides a widget for adding, removing, and modifying
available LLM models for each provider.
"""

import logging
import os
import json
from typing import List, Dict, Any, Callable, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal

from core.llm.provider_manager import ProviderType, get_provider_manager
from core.llm.settings_manager import get_settings_manager

# Get the module logger
logger = logging.getLogger("GUI")

class AddEditModelDialog(QDialog):
    """Dialog for adding or editing a model."""
    
    def __init__(self, parent=None, edit_data: Optional[Tuple[str, str]] = None):
        """Initialize the dialog.
        
        Args:
            parent: Parent widget.
            edit_data: Tuple of (display_name, model_id) if editing, None if adding.
        """
        super().__init__(parent)
        
        self.edit_data = edit_data
        self.setWindowTitle("Add Model" if not edit_data else "Edit Model")
        self.setMinimumWidth(350)
        
        self._setup_ui()
        
        if edit_data:
            self._populate_edit_data(edit_data)
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Form layout for inputs
        form_layout = QFormLayout()
        
        # Model display name field
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Display name shown in UI")
        form_layout.addRow("Display Name:", self.name_edit)
        
        # Model ID/Value field
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Actual model ID/name used in API calls")
        form_layout.addRow("Model ID:", self.value_edit)
        
        # Add help text
        help_label = QLabel(
            "Note: Model ID should match the exact identifier expected by the API. "
            "For example: 'gpt-4o' for OpenAI or 'gemini-2.0-flash' for Google."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666; font-style: italic; font-size: 10px;")
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Add layouts to main layout
        layout.addLayout(form_layout)
        layout.addWidget(help_label)
        layout.addWidget(button_box)
    
    def _populate_edit_data(self, edit_data: Tuple[str, str]):
        """Populate the dialog with data for editing."""
        display_name, model_id = edit_data
        self.name_edit.setText(display_name)
        self.value_edit.setText(model_id)
    
    def get_model_data(self) -> Tuple[str, str]:
        """Get the model data entered by the user.
        
        Returns:
            Tuple of (display_name, model_id).
        """
        return (self.name_edit.text(), self.value_edit.text())


class ModelManagementWidget(QWidget):
    """Widget for managing LLM models for a provider."""
    
    # Signal emitted when models are updated
    models_updated = Signal(list)  # List of (display_name, model_id) tuples
    
    def __init__(self, parent=None, provider_type: ProviderType = None, provider_name: str = "Provider"):
        """Initialize the widget.
        
        Args:
            parent: Parent widget.
            provider_type: The type of provider.
            provider_name: Human-readable name of the provider.
        """
        super().__init__(parent)
        
        self.provider_type = provider_type
        self.provider_name = provider_name
        self.settings_manager = get_settings_manager()
        self.provider_manager = get_provider_manager()
        
        # Current models list [(display_name, model_id), ...]
        self.models = []
        
        self._setup_ui()
        self._load_models()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box
        group_box = QGroupBox(f"{self.provider_name} Models")
        group_layout = QVBoxLayout(group_box)
        
        # Description
        description = QLabel(f"Manage available models for {self.provider_name}:")
        description.setWordWrap(True)
        group_layout.addWidget(description)
        
        # List and buttons layout
        list_buttons_layout = QHBoxLayout()
        
        # Model list
        self.model_list = QListWidget()
        self.model_list.setMinimumHeight(150)
        self.model_list.itemSelectionChanged.connect(self._handle_selection_changed)
        list_buttons_layout.addWidget(self.model_list)
        
        # Buttons layout
        buttons_layout = QVBoxLayout()
        
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._handle_add)
        
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self._handle_edit)
        self.edit_button.setEnabled(False)
        
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._handle_remove)
        self.remove_button.setEnabled(False)
        
        self.set_default_button = QPushButton("Set Default")
        self.set_default_button.clicked.connect(self._handle_set_default)
        self.set_default_button.setEnabled(False)
        
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.remove_button)
        buttons_layout.addWidget(self.set_default_button)
        buttons_layout.addStretch()
        
        list_buttons_layout.addLayout(buttons_layout)
        
        # Default model info
        self.default_model_label = QLabel("Default model: None")
        
        # Add widgets to layout
        group_layout.addLayout(list_buttons_layout)
        group_layout.addWidget(self.default_model_label)
        
        # Add group box to main layout
        layout.addWidget(group_box)
    
    def _load_models(self):
        """Load models from settings."""
        if not self.provider_type:
            return
        
        # Get provider settings
        settings = self.settings_manager.get_provider_settings(self.provider_type)
        available_models = settings.get("available_models", [])
        default_model = settings.get("default_model", "")

        # Seed from master models if empty/missing
        if not available_models:
            try:
                master_path = os.path.join("config", "llm", "models.json")
                if os.path.exists(master_path):
                    with open(master_path, "r", encoding="utf-8") as f:
                        master = json.load(f)
                    provider_map = {
                        ProviderType.OPENAI: "openai",
                        ProviderType.GOOGLE: "google",
                        ProviderType.OPENROUTER: "openrouter",
                        ProviderType.ANTHROPIC: "anthropic"
                    }
                    key = provider_map.get(self.provider_type)
                    if key and key in master:
                        seed = [m.get("id") for m in master[key] if isinstance(m, dict) and m.get("id")]
                        if seed:
                            available_models = seed
                            # Persist the seed so it sticks
                            self.settings_manager.update_provider_settings(
                                self.provider_type, {"available_models": available_models}
                            )
                            logger.info(f"Seeded {self.provider_name} models from master list: {len(seed)} items")
            except Exception as e:
                logger.warning(f"Could not seed models from master list: {e}")
        
        # Clear current models
        self.models = []
        self.model_list.clear()
        
        # Simple case: just model IDs in the list
        if all(isinstance(model, str) for model in available_models):
            for model_id in available_models:
                # Use the model ID as display name too
                self.models.append((model_id, model_id))
                item = QListWidgetItem(model_id)
                item.setData(Qt.UserRole, model_id)
                self.model_list.addItem(item)
        
        # Update default model label
        if default_model:
            self.default_model_label.setText(f"Default model: {default_model}")
        else:
            self.default_model_label.setText("Default model: None")
    
    def _handle_selection_changed(self):
        """Handle selection change in the model list."""
        selected = self.model_list.selectedItems()
        has_selection = len(selected) > 0
        
        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)
        self.set_default_button.setEnabled(has_selection)
    
    def _handle_add(self):
        """Handle add button click."""
        dialog = AddEditModelDialog(self)
        if dialog.exec():
            display_name, model_id = dialog.get_model_data()
            
            # Validate input
            if not display_name or not model_id:
                QMessageBox.warning(self, "Invalid Input", "Both display name and model ID are required.")
                return
            
            # Check for duplicates
            for _, existing_id in self.models:
                if existing_id == model_id:
                    QMessageBox.warning(
                        self, 
                        "Duplicate Model", 
                        f"A model with ID '{model_id}' already exists."
                    )
                    return
            
            # Add to list
            self.models.append((display_name, model_id))
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, model_id)
            self.model_list.addItem(item)
            
            # Update settings
            self._save_models()
    
    def _handle_edit(self):
        """Handle edit button click."""
        selected = self.model_list.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        display_name = item.text()
        model_id = item.data(Qt.UserRole)
        
        dialog = AddEditModelDialog(self, (display_name, model_id))
        if dialog.exec():
            new_display_name, new_model_id = dialog.get_model_data()
            
            # Validate input
            if not new_display_name or not new_model_id:
                QMessageBox.warning(self, "Invalid Input", "Both display name and model ID are required.")
                return
            
            # Check for duplicates if model ID changed
            if new_model_id != model_id:
                for _, existing_id in self.models:
                    if existing_id == new_model_id:
                        QMessageBox.warning(
                            self, 
                            "Duplicate Model", 
                            f"A model with ID '{new_model_id}' already exists."
                        )
                        return
            
            # Update list
            index = self.model_list.row(item)
            self.models[index] = (new_display_name, new_model_id)
            
            item.setText(new_display_name)
            item.setData(Qt.UserRole, new_model_id)
            
            # Update settings
            self._save_models()
    
    def _handle_remove(self):
        """Handle remove button click."""
        selected = self.model_list.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        display_name = item.text()
        model_id = item.data(Qt.UserRole)
        
        # Confirm removal
        result = QMessageBox.question(
            self,
            "Remove Model",
            f"Are you sure you want to remove the model '{display_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Check if it's the default model
        provider_settings = self.settings_manager.get_provider_settings(self.provider_type)
        default_model = provider_settings.get("default_model", "")
        
        if model_id == default_model:
            result = QMessageBox.question(
                self,
                "Remove Default Model",
                f"This model is currently set as the default model. "
                f"If you remove it, you'll need to select a new default model. "
                f"Do you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
        
        # Remove from list
        index = self.model_list.row(item)
        self.model_list.takeItem(index)
        self.models.pop(index)
        
        # Update settings
        self._save_models()
        
        # Reset default model if needed
        if model_id == default_model and self.models:
            self._set_default_model(self.models[0][1])  # Use first model as default
    
    def _handle_set_default(self):
        """Handle set default button click."""
        selected = self.model_list.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        model_id = item.data(Qt.UserRole)
        
        self._set_default_model(model_id)
    
    def _set_default_model(self, model_id: str):
        """Set the default model.
        
        Args:
            model_id: The model ID to set as default.
        """
        if not self.provider_type:
            return
        
        # Update settings
        self.settings_manager.update_provider_settings(
            self.provider_type,
            {"default_model": model_id}
        )
        
        # Update UI
        self.default_model_label.setText(f"Default model: {model_id}")
        
        logger.info(f"Set default model for {self.provider_name} to {model_id}")
    
    def _save_models(self):
        """Save the current models to settings."""
        if not self.provider_type:
            return
        
        # Extract model IDs
        model_ids = [model_id for _, model_id in self.models]
        
        # Update settings
        self.settings_manager.update_provider_settings(
            self.provider_type,
            {"available_models": model_ids}
        )
        
        # Emit signal
        self.models_updated.emit(self.models)
        
        logger.info(f"Updated models for {self.provider_name}: {model_ids}")
    
    def set_models(self, models: List[Tuple[str, str]]):
        """Set the models list.
        
        Args:
            models: List of (display_name, model_id) tuples.
        """
        self.models = models.copy()
        self.model_list.clear()
        
        for display_name, model_id in self.models:
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, model_id)
            self.model_list.addItem(item)
        
        # Notify listeners so parent tabs keep their internal state in sync
        self.models_updated.emit(self.models)
