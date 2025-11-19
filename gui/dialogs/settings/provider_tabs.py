#!/usr/bin/env python3
"""
LLM provider-specific tabs for the RPG game GUI.
This module provides tabs for different LLM providers.
"""

from typing import Dict, Any, List, Optional, Tuple

from PySide6.QtWidgets import (
    QFormLayout, QLineEdit)
from PySide6.QtCore import Slot

from core.utils.logging_config import get_logger
from gui.dialogs.settings.llm_provider_tab import LLMProviderTab
from gui.dialogs.settings.model_management_widget import ModelManagementWidget
from core.llm.provider_manager import ProviderType
from gui.styles.stylesheet_factory import create_line_edit_style

# Get the module logger
logger = get_logger("GUI")

class OpenAITab(LLMProviderTab):
    """Tab for OpenAI settings."""
    
    def __init__(self, parent=None):
        """Initialize the OpenAI settings tab."""
        super().__init__(parent, provider_name="OpenAI")
        
        # Add OpenAI specific properties
        self.api_key_setting_name = "api_key"
        
        # Add OpenAI specific fields
        form_layout = self.findChild(QFormLayout)
        
        # Organization field
        self.org_edit = QLineEdit()
        self.org_edit.setPlaceholderText("Organization ID (optional)")
        form_layout.insertRow(2, "Organization:", self.org_edit)
        
        # Create model management widget
        self.model_manager = ModelManagementWidget(self, ProviderType.OPENAI, "OpenAI")
        self.model_manager.models_updated.connect(self._on_models_updated)
        
        # Add model manager to the main layout
        self.main_layout.insertWidget(self.main_layout.count() - 1, self.model_manager)
        
        # Set info text
        self.info_label.setText("OpenAI's GPT models are powerful general-purpose models with varying capabilities.")
        
        # Connect signals
        self.enabled_check.toggled.connect(self._toggle_openai_fields)
        
        # Apply initial theme
        self._update_theme()

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        # Guard against premature call
        if not hasattr(self, 'org_edit'):
            return

        if palette:
            self.palette = palette
            
        # Call base class update
        super()._update_theme(self.palette)
        
        # Style specific fields
        self.org_edit.setStyleSheet(create_line_edit_style(self.palette))
        
        # Propagate to model manager
        if hasattr(self, 'model_manager'):
            self.model_manager._update_theme(self.palette)
    
    def _toggle_openai_fields(self, enabled: bool):
        """Toggle OpenAI-specific fields."""
        self.org_edit.setEnabled(enabled)
        self.model_manager.setEnabled(enabled)
        
    def _on_models_updated(self, models: List[Tuple[str, str]]):
        """Handle models updated from model manager."""
        self.models = models
    
    def set_settings(self, settings: Dict[str, Any]):
        """Set the tab settings."""
        super().set_settings(settings)
        
        # Set OpenAI-specific settings
        self.org_edit.setText(settings.get("organization", ""))
        self.org_edit.setEnabled(self.enabled_check.isChecked())
        
        # Set up models for model management widget
        available_models = settings.get("available_models", [])
        models = []
        for model in available_models:
            models.append((model, model))
            
        self.models = models
        self.model_manager.set_models(models)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get the current settings from the tab."""
        settings = super().get_settings()
        settings["organization"] = self.org_edit.text()
        model_ids = [model_id for _, model_id in self.models]
        settings["available_models"] = model_ids
        return settings


class GoogleTab(LLMProviderTab):
    """Tab for Google settings."""
    
    def __init__(self, parent=None):
        """Initialize the Google settings tab."""
        super().__init__(parent, provider_name="Google AI")
        
        # Create model management widget
        self.model_manager = ModelManagementWidget(self, ProviderType.GOOGLE, "Google AI")
        self.model_manager.models_updated.connect(self._on_models_updated)
        
        # Add model manager to the main layout
        self.main_layout.insertWidget(self.main_layout.count() - 1, self.model_manager)
        
        # Set info text
        self.info_label.setText("Google's Gemini models provide strong multilingual capabilities and state-of-the-art performance.")
        
        # Apply initial theme
        self._update_theme()

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        # Guard against premature call
        if not hasattr(self, 'model_manager'):
            return

        if palette:
            self.palette = palette
        super()._update_theme(self.palette)
        if hasattr(self, 'model_manager'):
            self.model_manager._update_theme(self.palette)
    
    def _toggle_fields(self, enabled: bool):
        """Toggle fields based on enabled state."""
        super()._toggle_fields(enabled)
        self.model_manager.setEnabled(enabled)
    
    def _on_models_updated(self, models: List[Tuple[str, str]]):
        """Handle models updated from model manager."""
        self.models = models
    
    def set_settings(self, settings: Dict[str, Any]):
        """Set the tab settings."""
        super().set_settings(settings)
        
        available_models = settings.get("available_models", [])
        models = []
        for model in available_models:
            models.append((model, model))
            
        self.models = models
        self.model_manager.set_models(models)
        
    def get_settings(self) -> Dict[str, Any]:
        """Get the current settings from the tab."""
        settings = super().get_settings()
        model_ids = [model_id for _, model_id in self.models]
        settings["available_models"] = model_ids
        return settings


class OpenRouterTab(LLMProviderTab):
    """Tab for OpenRouter settings."""
    
    def __init__(self, parent=None):
        """Initialize the OpenRouter settings tab."""
        super().__init__(parent, provider_name="OpenRouter")
        
        # Create model management widget
        self.model_manager = ModelManagementWidget(self, ProviderType.OPENROUTER, "OpenRouter")
        self.model_manager.models_updated.connect(self._on_models_updated)
        
        # Add model manager to the main layout
        self.main_layout.insertWidget(self.main_layout.count() - 1, self.model_manager)
        
        # Set info text
        self.info_label.setText("OpenRouter allows access to multiple AI models from different providers through a single API. Create an account at openrouter.ai to get started.")
        
        # Apply initial theme
        self._update_theme()

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        # Guard against premature call
        if not hasattr(self, 'model_manager'):
            return
            
        if palette:
            self.palette = palette
        super()._update_theme(self.palette)
        if hasattr(self, 'model_manager'):
            self.model_manager._update_theme(self.palette)
    
    def _toggle_fields(self, enabled: bool):
        """Toggle fields based on enabled state."""
        super()._toggle_fields(enabled)
        self.model_manager.setEnabled(enabled)
    
    def _on_models_updated(self, models: List[Tuple[str, str]]):
        """Handle models updated from model manager."""
        self.models = models
    
    def set_settings(self, settings: Dict[str, Any]):
        """Set the tab settings."""
        super().set_settings(settings)
        
        available_models = settings.get("available_models", [])
        models = []
        for model in available_models:
            models.append((model, model))
            
        self.models = models
        self.model_manager.set_models(models)
        
    def get_settings(self) -> Dict[str, Any]:
        """Get the current settings from the tab."""
        settings = super().get_settings()
        model_ids = [model_id for _, model_id in self.models]
        settings["available_models"] = model_ids
        return settings