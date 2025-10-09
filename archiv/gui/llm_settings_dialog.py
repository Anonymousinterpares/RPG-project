# gui/llm_settings_dialog.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QLineEdit, QPushButton, QTabWidget, 
                               QWidget, QFormLayout, QDoubleSpinBox, QSpinBox, 
                               QCheckBox, QGroupBox, QMessageBox, QListWidget,
                               QListWidgetItem, QInputDialog)
from PySide6.QtCore import Qt, Signal
import os
import json
import sys
from typing import Dict, Any, List, Optional
from core.llm.provider_manager import ProviderManager, ModelInfo

class ModelListWidget(QListWidget):
    """Widget to display and manage model list for a provider"""
    
    modelChanged = Signal()
    
    def __init__(self, provider_manager: ProviderManager, provider_name: str, parent=None):
        super().__init__(parent)
        self.provider_manager = provider_manager
        self.provider_name = provider_name
        self.update_model_list()
        
    def update_model_list(self):
        """Update the model list for the selected provider"""
        self.clear()
        models = self.provider_manager.get_models_for_provider(self.provider_name)
        for model in models:
            item = QListWidgetItem(f"{model.name} ({model.id})")
            item.setData(Qt.UserRole, model.id)
            if model.is_default:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setText(f"{model.name} ({model.id}) [DEFAULT]")
            self.addItem(item)

class ProviderConfigWidget(QWidget):
    """Widget to configure a specific LLM provider"""
    
    configChanged = Signal()
    
    def __init__(self, provider_manager: ProviderManager, provider_name: str, parent=None):
        super().__init__(parent)
        self.provider_manager = provider_manager
        self.provider_name = provider_name
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Provider status
        status_layout = QHBoxLayout()
        self.enabled_checkbox = QCheckBox("Enabled")
        provider_config = self.provider_manager.get_provider_config(self.provider_name)
        if provider_config:
            self.enabled_checkbox.setChecked(provider_config.is_enabled)
        self.enabled_checkbox.toggled.connect(self.on_enabled_toggled)
        
        default_button = QPushButton("Set as Default")
        default_button.clicked.connect(self.on_set_default)
        
        verify_button = QPushButton("Verify API Key")
        verify_button.clicked.connect(self.on_verify_api)
        
        status_layout.addWidget(self.enabled_checkbox)
        status_layout.addWidget(default_button)
        status_layout.addWidget(verify_button)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
        
        # API configuration
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout(api_group)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Enter API key")
        
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("Enter base URL (optional)")
        
        # Load current values
        if provider_config:
            self.api_key_edit.setText(provider_config.api_key)
            if provider_config.base_url:
                self.base_url_edit.setText(provider_config.base_url)
        
        api_layout.addRow("API Key:", self.api_key_edit)
        api_layout.addRow("Base URL:", self.base_url_edit)
        
        save_api_button = QPushButton("Save API Settings")
        save_api_button.clicked.connect(self.on_save_api)
        api_layout.addRow("", save_api_button)
        
        layout.addWidget(api_group)
        
        # Models configuration
        models_group = QGroupBox("Models")
        models_layout = QVBoxLayout(models_group)
        
        self.model_list = ModelListWidget(self.provider_manager, self.provider_name)
        self.model_list.modelChanged.connect(self.configChanged)
        
        models_layout.addWidget(self.model_list)
        
        # Model action buttons
        model_buttons_layout = QHBoxLayout()
        
        add_model_button = QPushButton("Add Model")
        add_model_button.clicked.connect(self.on_add_model)
        
        remove_model_button = QPushButton("Remove Model")
        remove_model_button.clicked.connect(self.on_remove_model)
        
        set_default_model_button = QPushButton("Set as Default")
        set_default_model_button.clicked.connect(self.on_set_default_model)
        
        model_buttons_layout.addWidget(add_model_button)
        model_buttons_layout.addWidget(remove_model_button)
        model_buttons_layout.addWidget(set_default_model_button)
        
        models_layout.addLayout(model_buttons_layout)
        
        layout.addWidget(models_group)
        layout.addStretch()
    
    def on_enabled_toggled(self, checked):
        """Handle provider enabled/disabled toggle"""
        self.provider_manager.set_provider_enabled(self.provider_name, checked)
        self.configChanged.emit()
    
    def on_set_default(self):
        """Set this provider as default"""
        self.provider_manager.set_default_provider(self.provider_name)
        self.configChanged.emit()
        QMessageBox.information(self, "Default Provider", 
                                f"{self.provider_name} has been set as the default provider.")
    
    def on_verify_api(self):
        """Verify API key by making a test request"""
        import asyncio
        
        # First save current API settings
        self.on_save_api()
        
        # Create a dialog to show verification status
        msg = QMessageBox(self)
        msg.setWindowTitle("Verifying API Key")
        msg.setText("Testing connection to API...")
        msg.setStandardButtons(QMessageBox.NoButton)
        msg.show()
        
        # Run verification asynchronously
        async def verify():
            result = await self.provider_manager.verify_client(self.provider_name)
            return result
        
        # Create a new event loop and run the verification
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(verify())
            
            # Close the dialog
            msg.close()
            
            # Show result
            if result:
                QMessageBox.information(self, "API Verification", 
                                       f"Successfully connected to {self.provider_name} API.")
            else:
                QMessageBox.warning(self, "API Verification", 
                                    f"Failed to connect to {self.provider_name} API. Please check your API key and settings.")
        except Exception as e:
            msg.close()
            QMessageBox.critical(self, "API Verification Error", 
                                f"Error verifying API: {str(e)}")
        finally:
            loop.close()
    
    def on_save_api(self):
        """Save API configuration"""
        api_key = self.api_key_edit.text()
        base_url = self.base_url_edit.text()
        
        self.provider_manager.update_provider_api_key(self.provider_name, api_key)
        self.provider_manager.update_provider_base_url(self.provider_name, base_url)
        
        self.configChanged.emit()
    
    def on_add_model(self):
        """Add a new model to the provider"""
        model_id, ok = QInputDialog.getText(self, "Add Model", "Model ID:")
        if ok and model_id:
            model_name, ok = QInputDialog.getText(self, "Add Model", "Model Name:")
            if ok and model_name:
                # Get context length
                context_length, ok = QInputDialog.getInt(self, "Add Model", 
                                                        "Context Length:", 4096, 1024, 1000000, 1024)
                if ok:
                    # Create model info
                    model_info = ModelInfo(
                        id=model_id,
                        name=model_name,
                        provider=self.provider_name,
                        context_length=context_length,
                        description="Custom model added by user",
                        is_available=True,
                        is_default=False,
                        parameters={"temperature": 0.7, "max_tokens": 1000}
                    )
                    
                    # Add to provider
                    success = self.provider_manager.add_model_to_provider(self.provider_name, model_info)
                    if success:
                        self.model_list.update_model_list()
                        self.configChanged.emit()
                    else:
                        QMessageBox.warning(self, "Add Model", 
                                           f"Failed to add model {model_id}. It may already exist.")
    
    def on_remove_model(self):
        """Remove selected model from provider"""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Remove Model", "Please select a model to remove.")
            return
        
        selected_item = selected_items[0]
        model_id = selected_item.data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "Remove Model", 
                                    f"Are you sure you want to remove {model_id}?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success = self.provider_manager.remove_model_from_provider(self.provider_name, model_id)
            if success:
                self.model_list.update_model_list()
                self.configChanged.emit()
            else:
                QMessageBox.warning(self, "Remove Model", 
                                   f"Failed to remove model {model_id}.")
    
    def on_set_default_model(self):
        """Set selected model as default for provider"""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Set Default Model", "Please select a model to set as default.")
            return
        
        selected_item = selected_items[0]
        model_id = selected_item.data(Qt.UserRole)
        
        success = self.provider_manager.set_default_model_for_provider(self.provider_name, model_id)
        if success:
            self.model_list.update_model_list()
            self.configChanged.emit()
        else:
            QMessageBox.warning(self, "Set Default Model", 
                               f"Failed to set {model_id} as default model.")

class AgentConfigWidget(QWidget):
    """Widget to configure a specific agent's LLM settings"""
    
    configChanged = Signal()
    
    def __init__(self, provider_manager: ProviderManager, agent_type: str, parent=None):
        super().__init__(parent)
        self.provider_manager = provider_manager
        self.agent_type = agent_type
        self.agent_config = self.provider_manager.get_agent_config(agent_type)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Provider selection
        self.provider_combo = QComboBox()
        for provider_name in self.provider_manager.get_enabled_providers():
            self.provider_combo.addItem(provider_name)
        
        # Set current provider
        current_provider = self.agent_config.get("provider")
        if current_provider:
            index = self.provider_combo.findText(current_provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
        
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        form_layout.addRow("Provider:", self.provider_combo)
        
        # Model selection
        self.model_combo = QComboBox()
        self.update_model_list()
        
        # Set current model
        current_model = self.agent_config.get("model")
        if current_model:
            index = self.model_combo.findData(current_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        
        form_layout.addRow("Model:", self.model_combo)
        
        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(self.agent_config.get("temperature", 0.7))
        form_layout.addRow("Temperature:", self.temperature_spin)
        
        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(50, 10000)
        self.max_tokens_spin.setSingleStep(50)
        self.max_tokens_spin.setValue(self.agent_config.get("max_tokens", 1000))
        form_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        # Add form layout
        layout.addLayout(form_layout)
        
        # Save button
        save_button = QPushButton("Save Configuration")
        save_button.clicked.connect(self.on_save_config)
        layout.addWidget(save_button)
        
        layout.addStretch()
    
    def update_model_list(self):
        """Update model list based on selected provider"""
        self.model_combo.clear()
        provider_name = self.provider_combo.currentText()
        if provider_name:
            models = self.provider_manager.get_models_for_provider(provider_name)
            for model in models:
                self.model_combo.addItem(f"{model.name}", model.id)
    
    def on_provider_changed(self, provider_name):
        """Handle provider selection change"""
        self.update_model_list()
    
    def on_save_config(self):
        """Save agent configuration"""
        provider_name = self.provider_combo.currentText()
        model_id = self.model_combo.currentData()
        temperature = self.temperature_spin.value()
        max_tokens = self.max_tokens_spin.value()
        
        self.agent_config = {
            "provider": provider_name,
            "model": model_id,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        success = self.provider_manager.save_agent_config(self.agent_type, self.agent_config)
        if success:
            self.configChanged.emit()
            QMessageBox.information(self, "Configuration Saved", 
                                   f"Configuration for {self.agent_type} has been saved.")
        else:
            QMessageBox.warning(self, "Save Failed", 
                               f"Failed to save configuration for {self.agent_type}.")

class LLMSettingsDialog(QDialog):
    """Dialog for configuring LLM settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LLM Settings")
        self.resize(800, 600)
        self.provider_manager = ProviderManager()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create providers tab
        self.providers_tab = QTabWidget()
        
        # Add provider tabs
        for provider_name in self.provider_manager.get_all_providers():
            provider_widget = ProviderConfigWidget(self.provider_manager, provider_name)
            provider_widget.configChanged.connect(self.on_config_changed)
            self.providers_tab.addTab(provider_widget, provider_name)
        
        # Create agents tab
        self.agents_tab = QTabWidget()
        
        # Add agent tabs
        agent_types = ["narrator", "rule_checker", "context_evaluator"]
        for agent_type in agent_types:
            agent_widget = AgentConfigWidget(self.provider_manager, agent_type)
            agent_widget.configChanged.connect(self.on_config_changed)
            self.agents_tab.addTab(agent_widget, agent_type.replace("_", " ").title())
        
        # Add tabs to main tab widget
        self.tab_widget.addTab(self.providers_tab, "Providers")
        self.tab_widget.addTab(self.agents_tab, "Agents")
        
        layout.addWidget(self.tab_widget)
        
        # Add buttons
        buttons_layout = QHBoxLayout()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.close_button)
        
        layout.addLayout(buttons_layout)
    
    def on_config_changed(self):
        """Handle configuration changes"""
        # This is called when any provider or agent config is changed
        # We could trigger a reload of LLM clients here if needed
        pass