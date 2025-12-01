#!/usr/bin/env python3
"""
Agent setup tab for the RPG game GUI.
This module provides a tab for configuring which LLM provider and model to use for each agent.
"""
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
    QDoubleSpinBox, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Slot

from core.llm.provider_manager import ProviderType, get_provider_manager
from core.llm.settings_manager import get_settings_manager
from core.utils.logging_config import get_logger
from gui.styles.theme_manager import get_theme_manager
from gui.styles.stylesheet_factory import create_dialog_style, create_styled_button_style

# Get the module logger
logger = get_logger("GUI")

class AgentSetupDialog(QDialog):
    """Dialog for configuring an agent's LLM settings."""
    
    def __init__(self, parent=None, agent_name: str = "", agent_settings: Dict[str, Any] = None):
        """Initialize the dialog."""
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        self.agent_name = agent_name
        self.agent_settings = agent_settings or {}
        self.provider_manager = get_provider_manager()
        self.settings_manager = get_settings_manager()
        
        self.setWindowTitle(f"Configure {agent_name.capitalize()} Agent")
        self.setMinimumWidth(450)
        
        # 1. Setup UI first (creates self.provider_combo)
        self._setup_ui()
        
        # 2. Populate settings (uses self.provider_combo)
        self._populate_settings()
        
        # 3. Apply theme
        self._update_theme()

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        # Apply dialog style
        self.setStyleSheet(create_dialog_style(self.palette))
        
        colors = self.palette['colors']
        
        # Style labels
        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"color: {colors['text_primary']};")
            
        # Style inputs
        input_style = f"""
            background-color: {colors['bg_dark']};
            color: {colors['text_bright']};
            border: 1px solid {colors['border_dark']};
            border-radius: 4px;
            padding: 5px;
        """
        
        # Apply to each input type separately to avoid findChildren TypeError
        for widget_type in (QComboBox, QSpinBox, QDoubleSpinBox):
            for widget in self.findChildren(widget_type):
                widget.setStyleSheet(input_style)

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Provider dropdown
        self.provider_combo = QComboBox()
        self._populate_providers()
        form_layout.addRow("Provider:", self.provider_combo)
        
        # Model dropdown
        self.model_combo = QComboBox()
        form_layout.addRow("Model:", self.model_combo)
        
        # Temperature setting
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 1.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(2)
        form_layout.addRow("Temperature:", self.temperature_spin)
        
        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 8000)
        self.max_tokens_spin.setSingleStep(100)
        form_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 120)
        self.timeout_spin.setSingleStep(5)
        form_layout.addRow("Timeout (seconds):", self.timeout_spin)
        
        # Connect signals
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Add layouts
        layout.addLayout(form_layout)
        layout.addWidget(button_box)
    
    def _populate_providers(self):
        """Populate the providers dropdown."""
        self.provider_combo.clear()
        
        # Get available providers
        available_providers = self.provider_manager.get_available_providers()
        
        # Add each provider to the dropdown
        for provider in available_providers:
            self.provider_combo.addItem(provider.name.capitalize(), provider.name)
        
        # Add a placeholder if no providers are available
        if not available_providers:
            self.provider_combo.addItem("No providers available", "")
    
    def _on_provider_changed(self, index):
        """Handle provider selection change."""
        self.model_combo.clear()
        
        # Get selected provider type
        if index < 0:
            self.model_combo.addItem("Select a provider first", "")
            return
        
        provider_name = self.provider_combo.itemData(index)
        
        # Handle None or empty provider name
        if not provider_name:
            self.model_combo.addItem("Invalid provider", "")
            return
            
        try:
            provider_type = ProviderType[provider_name]
            
            # Get available models for this provider
            models = self.settings_manager.get_available_models(provider_type)
            
            # Add models to the dropdown
            for model in models:
                self.model_combo.addItem(model, model)
            
            # Add a placeholder if no models are available
            if not models:
                self.model_combo.addItem("No models available", "")
                
        except (KeyError, ValueError):
            logger.error(f"Invalid provider type: {provider_name}")
            self.model_combo.addItem("Error loading models", "")
    
    def _populate_settings(self):
        """Populate the dialog with current settings."""
        # Set provider
        provider_type_str = self.agent_settings.get("provider_type", "OPENAI")
        
        # Check if provider_type_str is None and provide a default
        if provider_type_str is None:
            provider_type_str = "OPENAI"
        
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider_type_str:
                self.provider_combo.setCurrentIndex(i)
                break
        
        # Model will be populated by _on_provider_changed
        
        # Make sure to call provider change handler to populate the model dropdown
        self._on_provider_changed(self.provider_combo.currentIndex())
        
        # If we have a specific model, select it
        model = self.agent_settings.get("model", "")
        if model:
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == model:
                    self.model_combo.setCurrentIndex(i)
                    break
        
        # Set other settings
        self.temperature_spin.setValue(self.agent_settings.get("temperature", 0.7))
        self.max_tokens_spin.setValue(self.agent_settings.get("max_tokens", 1000))
        self.timeout_spin.setValue(self.agent_settings.get("timeout_seconds", 30))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get the settings from the dialog."""
        # Get provider type
        provider_index = self.provider_combo.currentIndex()
        provider_type_str = self.provider_combo.itemData(provider_index)
        
        # Get model
        model_index = self.model_combo.currentIndex()
        model = self.model_combo.itemData(model_index)
        
        # Build settings dictionary
        settings = {
            "provider_type": provider_type_str,
            "model": model,
            "temperature": self.temperature_spin.value(),
            "max_tokens": self.max_tokens_spin.value(),
            "timeout_seconds": self.timeout_spin.value(),
        }
        
        return settings


class AgentSetupTab(QWidget):
    """Tab for configuring agent LLM settings."""
    
    def __init__(self, parent=None):
        """Initialize the agent setup tab."""
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        self.settings_manager = get_settings_manager()
        self.provider_manager = get_provider_manager()
        
        # Store agent settings
        self.agent_settings = {}
        
        self._setup_ui()
        self._load_agent_settings()
        
        # Apply initial theme
        self._update_theme()

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        
        # Style description label
        self.description_label.setStyleSheet(f"color: {colors['text_secondary']};")
        
        # Style table
        self.agents_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {colors['bg_dark']};
                color: {colors['text_bright']};
                gridline-color: {colors['border_dark']};
                border: 1px solid {colors['border_dark']};
            }}
            QHeaderView::section {{
                background-color: {colors['bg_medium']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_dark']};
                padding: 4px;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
        """)
        
        # Re-style buttons inside the table
        button_style = create_styled_button_style(self.palette)
        for i in range(self.agents_table.rowCount()):
            widget = self.agents_table.cellWidget(i, 4)
            if isinstance(widget, QPushButton):
                widget.setStyleSheet(button_style)
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Description
        self.description_label = QLabel(
            "Configure which LLM provider and model to use for each agent in the game. "
            "Each agent can use a different provider and model configuration."
        )
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)
        
        # Agents table
        self.agents_table = QTableWidget()
        self.agents_table.setColumnCount(5)
        self.agents_table.setHorizontalHeaderLabels([
            "Agent", "Provider", "Model", "Temperature", "Configure"
        ])
        
        # Set table properties
        header = self.agents_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        # Use Fixed for the button column to ensure it respects width
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        
        # Set default row height to accommodate buttons
        self.agents_table.verticalHeader().setDefaultSectionSize(50)
        
        layout.addWidget(self.agents_table)
    
    def _load_agent_settings(self):
        """Load agent settings and populate the table."""
        # Clear the table
        self.agents_table.setRowCount(0)
        
        # Get available agents
        agents = self.settings_manager.list_available_agents()
        
        # Populate table
        for i, agent_name in enumerate(agents):
            # Get agent settings
            settings = self.settings_manager.get_agent_settings(agent_name)
            self.agent_settings[agent_name] = settings
            
            # Add row
            self.agents_table.insertRow(i)
            self.agents_table.setRowHeight(i, 50) # Explicitly set row height
            
            # Agent name
            name_item = QTableWidgetItem(agent_name.capitalize())
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.agents_table.setItem(i, 0, name_item)
            
            # Provider
            provider_type_str = settings.get("provider_type", "OPENAI")
            if provider_type_str is None:
                provider_type_str = "OPENAI"
            provider_item = QTableWidgetItem(provider_type_str.capitalize())
            provider_item.setFlags(provider_item.flags() & ~Qt.ItemIsEditable)
            self.agents_table.setItem(i, 1, provider_item)
            
            # Model
            model = settings.get("model", "default")
            model_item = QTableWidgetItem(model)
            model_item.setFlags(model_item.flags() & ~Qt.ItemIsEditable)
            self.agents_table.setItem(i, 2, model_item)
            
            # Temperature
            temp = settings.get("temperature", 0.7)
            temp_item = QTableWidgetItem(f"{temp:.2f}")
            temp_item.setFlags(temp_item.flags() & ~Qt.ItemIsEditable)
            self.agents_table.setItem(i, 3, temp_item)
            
            # Configure button
            self.agents_table.setCellWidget(i, 4, self._create_configure_button(agent_name))
            
        # Set fixed width for the Configure column
        self.agents_table.setColumnWidth(4, 120)
    
    def _create_configure_button(self, agent_name: str) -> QPushButton:
        """Create a configure button for an agent."""
        button = QPushButton("Configure")
        # Apply style immediately
        button.setStyleSheet(create_styled_button_style(self.palette))
        # Fix height to fit nicely in row
        button.setFixedHeight(30) 
        button.clicked.connect(lambda: self._configure_agent(agent_name))
        return button
    
    def _configure_agent(self, agent_name: str) -> None:
        """Open the agent configuration dialog."""
        # Get agent settings
        settings = self.agent_settings.get(agent_name, {})
        
        # Create and show the dialog
        dialog = AgentSetupDialog(self, agent_name, settings)
        
        if dialog.exec():
            # Get updated settings
            updated_settings = dialog.get_settings()
            
            # Update in-memory settings
            self.agent_settings[agent_name] = updated_settings
            
            # Save settings to disk
            success = self.settings_manager.update_agent_settings(agent_name, updated_settings)
            
            if success:
                logger.info(f"Updated settings for agent {agent_name}")
            else:
                logger.error(f"Failed to update settings for agent {agent_name}")
            
            # Reload table
            self._load_agent_settings()
    
    def save_settings(self) -> bool:
        """Save all agent settings."""
        success = True
        
        for agent_name, settings in self.agent_settings.items():
            # Save settings to disk
            result = self.settings_manager.update_agent_settings(agent_name, settings)
            
            if not result:
                success = False
                logger.error(f"Failed to save settings for agent {agent_name}")
        
        return success