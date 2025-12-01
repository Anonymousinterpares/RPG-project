#!/usr/bin/env python3
"""
Anthropic provider tab for the RPG game GUI.
This module provides a tab for configuring Anthropic LLM provider settings.
"""

from typing import Dict, Any, List, Tuple

from core.utils.logging_config import get_logger
from gui.dialogs.settings.llm_provider_tab import LLMProviderTab
from gui.dialogs.settings.model_management_widget import ModelManagementWidget
from core.llm.provider_manager import ProviderType

# Get the module logger
logger = get_logger("GUI")

class AnthropicTab(LLMProviderTab):
    """Tab for Anthropic settings."""
    
    def __init__(self, parent=None):
        """Initialize the Anthropic settings tab."""
        super().__init__(parent, provider_name="Anthropic")
        
        # Create model management widget
        self.model_manager = ModelManagementWidget(self, ProviderType.ANTHROPIC, "Anthropic")
        self.model_manager.models_updated.connect(self._on_models_updated)
        
        # Add model manager to the main layout
        self.main_layout.insertWidget(self.main_layout.count() - 1, self.model_manager)
        
        # Set info text
        self.info_label.setText("Anthropic's Claude models provide thoughtful, creative, and reliable AI assistant capabilities.")
    
    def _toggle_fields(self, enabled: bool):
        """Toggle fields based on enabled state."""
        super()._toggle_fields(enabled)
        self.model_manager.setEnabled(enabled)
    
    def _on_models_updated(self, models: List[Tuple[str, str]]):
        """Handle models updated from model manager.
        
        Args:
            models: List of (display_name, value) tuples
        """
        # Just store the models
        self.models = models
    
    def set_settings(self, settings: Dict[str, Any]):
        """Set the tab settings."""
        super().set_settings(settings)
        
        # Set up models for model management widget
        available_models = settings.get("available_models", [])
        models = []
        for model in available_models:
            # Use the model ID as the display name as well
            models.append((model, model))
            
        # Set models in model manager
        self.model_manager.set_models(models)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get the current settings from the tab."""
        settings = super().get_settings()
        
        # Add models
        model_ids = [model_id for _, model_id in self.models]
        settings["available_models"] = model_ids
        
        return settings
