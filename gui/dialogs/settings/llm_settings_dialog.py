#!/usr/bin/env python3
"""
LLM settings dialog for the RPG game GUI.
This module provides a dialog for configuring LLM settings.
"""

import os
import json
from typing import Optional
import shutil
from datetime import datetime

from PySide6.QtWidgets import (
    QTabWidget, QMessageBox, QPushButton
)
from PySide6.QtCore import Slot

from core.llm.provider_manager import ProviderType, get_provider_manager
from core.llm.llm_manager import get_llm_manager

from core.llm.settings_manager import get_settings_manager
from core.utils.logging_config import get_logger
from gui.dialogs.settings.base_settings_dialog import BaseSettingsDialog
from gui.dialogs.settings.llm_general_tab import LLMGeneralTab
from gui.dialogs.settings.provider_tabs import OpenAITab, GoogleTab, OpenRouterTab
from gui.dialogs.settings.anthropic_tab import AnthropicTab
from gui.dialogs.settings.agent_setup_tab import AgentSetupTab
from gui.styles.stylesheet_factory import create_main_tab_widget_style, create_styled_button_style
from gui.styles.theme_manager import get_theme_manager

# Get the module logger
logger = get_logger("GUI")

class LLMSettingsDialog(BaseSettingsDialog):
    """Dialog for configuring LLM settings."""
    
    def __init__(self, parent=None):
        """Initialize the LLM settings dialog."""
        super().__init__(parent, title="LLM Settings")
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        # Get provider manager
        self.provider_manager = get_provider_manager()
        
        # Get LLM manager
        self.llm_manager = get_llm_manager()

        # Get settings manager
        self.settings_manager = get_settings_manager()

        # Load settings using SettingsManager
        self.provider_settings = self.settings_manager.get_provider_settings()
        self.base_settings = self.settings_manager.get_llm_settings()

        # Set up the UI
        self._setup_ui()
        
        # Populate the UI with settings
        self._populate_settings()
        
        # Apply initial theme
        self._update_theme()

        # Wire UI sounds for LLM Settings dialog
        try:
            from gui.utils.ui_sfx import map_container
            map_container(self, click_kind='dropdown', tab_kind='tab_click', dropdown_kind='dropdown')
        except Exception:
            pass

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        # Guard against premature call from BaseDialog.__init__
        if not hasattr(self, 'tab_widget'):
            return

        if palette:
            self.palette = palette
        
        # Call base class update first
        super()._update_theme(self.palette)
        
        colors = self.palette['colors']

        # Style tab widget
        self.tab_widget.setStyleSheet(create_main_tab_widget_style(self.palette))
        
        # Style buttons
        button_style = create_styled_button_style(self.palette)
        self.test_button.setStyleSheet(button_style)
        
        # Danger button style for reset (overrides standard styled button)
        danger_style = f"""
            QPushButton {{
                background-color: {colors['accent_negative']};
                color: {colors['text_bright']};
                border: 1px solid {colors['border_dark']};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {colors['accent_negative_light']};
            }}
            QPushButton:pressed {{
                background-color: {colors['state_pressed']};
            }}
        """
        self.reset_button.setStyleSheet(danger_style)
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.general_tab = LLMGeneralTab()
        self.openai_tab = OpenAITab()
        self.google_tab = GoogleTab()
        self.anthropic_tab = AnthropicTab()
        self.openrouter_tab = OpenRouterTab()
        self.agent_setup_tab = AgentSetupTab()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.openai_tab, "OpenAI")
        self.tab_widget.addTab(self.google_tab, "Google")
        self.tab_widget.addTab(self.anthropic_tab, "Anthropic")
        self.tab_widget.addTab(self.openrouter_tab, "OpenRouter")
        self.tab_widget.addTab(self.agent_setup_tab, "Agent Setup")
        
        # Add tab widget to main layout
        self.main_layout.addWidget(self.tab_widget)
        
        # Create reset button
        self.reset_button = QPushButton("Reset to Default")
        # Styling handled in _update_theme
        self.reset_button.clicked.connect(self._reset_settings)
        
        # Create test button
        self.test_button = QPushButton("Test Connections")
        self.test_button.clicked.connect(self._test_connections)
        
        # Add buttons to left side
        self.add_left_button(self.test_button)
        self.add_left_button(self.reset_button)
        
        # Add button layout
        self.add_button_layout()

    def _populate_settings(self):
        """Populate the UI with current settings."""
        # Always refresh settings from disk because model widgets may seed defaults on init
        self.provider_settings = self.settings_manager.get_provider_settings()
        self.base_settings = self.settings_manager.get_llm_settings()

        # Populate general settings
        self.general_tab.set_settings(self.base_settings)
        
        # Populate provider settings (freshly loaded)
        self.openai_tab.set_settings(self.provider_settings.get("openai", {}))
        self.google_tab.set_settings(self.provider_settings.get("google", {}))
        self.anthropic_tab.set_settings(self.provider_settings.get("anthropic", {}))
        self.openrouter_tab.set_settings(self.provider_settings.get("openrouter", {}))
    
    def _reset_settings(self):
        """Reset settings to default."""
        # Ask for confirmation
        result = QMessageBox.question(
            self, 
            "Reset Settings", 
            "Are you sure you want to reset all LLM settings to default?\n\nThis will remove all API keys and custom configurations.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        try:
            # --- Removed QSettings clear ---
            # self.qsettings.clear()

            # Reset config files
            config_dir = os.path.join("config", "llm")
            
            # Create backup of current config
            backup_dir = os.path.join(config_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup providers.json if it exists
            providers_file = os.path.join(config_dir, "providers.json")
            if os.path.exists(providers_file):
                backup_file = os.path.join(backup_dir, f"providers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                shutil.copy2(providers_file, backup_file)
                logger.info(f"Backed up providers.json to {backup_file}")
            
            # Backup base_config.json if it exists
            base_file = os.path.join(config_dir, "base_config.json")
            if os.path.exists(base_file):
                backup_file = os.path.join(backup_dir, f"base_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                shutil.copy2(base_file, backup_file)
                logger.info(f"Backed up base_config.json to {backup_file}")
            
            # Create default provider settings file
            default_providers = {
                "openai": {
                    "api_key": "",
                    "organization": "",
                    "api_base": "https://api.openai.com/v1",
                    "default_model": "gpt-4o-mini",
                    "available_models": [
                        "gpt-4.1-nano",
                        "gpt-4.1-mini",
                        "gpt-4.1",
                        "gpt-5-mini",
                        "gpt-4o",
                        "gpt-4o-mini"
                    ],
                    "enabled": True
                },
                "google": {
                    "api_key": "",
                    "default_model": "gemini-2.0-flash",
                    "available_models": [
                        "gemini-2.5-flash-preview-05-20",
                        "gemini-2.5-flash",
                        "gemini-2.0-flash",
                        "gemini-2.0-flash-lite"
                    ],
                    "enabled": True
                },
                "openrouter": {
                    "api_key": "",
                    "api_base": "https://openrouter.ai/api/v1",
                    "default_model": "mistralai/mistral-small-3.1-24b-instruct:free",
                    "available_models": [
                        "deepseek/deepseek-v3-base:free",
                        "google/gemini-2.5-pro-exp-03-25:free",
                        "meta-llama/llama-4-maverick:free",
                        "deepseek/deepseek-r1-0528:free",
                        "mistralai/mistral-small-3.1-24b-instruct:free",
                        "meta-llama/llama-4-scout:free",
                        "nvidia/llama-3.1-nemotron-nano-8b-v1:free",
                        "openrouter/quasar-alpha:free",
                        "moonshotai/kimi-vl-a3b-thinking:free",
                        "qwen/qwen2.5-vl-3b-instruct:free"
                    ],
                    "enabled": True
                },
                "anthropic": {
                    "api_key": "",
                    "api_base": "https://api.anthropic.com",
                    "default_model": "claude-3-5-haiku-latest",
                    "available_models": [
                        "claude-3-5-haiku-latest",
                        "claude-3-7-sonnet-latest",
                        "claude-sonnet-4-20250514-v1:0"
                    ],
                    "enabled": True
                }
            }

            with open(providers_file, 'w', encoding='utf-8') as f:
                json.dump(default_providers, f, indent=4)
            
            # Create default base settings file
            default_base = {
                "default_provider_type": "OPENAI",
                "default_temperature": 0.7,
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "retry_delay_seconds": 2,
                "run_diagnostics_on_start": False,
                "log_prompts": True,
                "log_completions": True,
                "cost_tracking_enabled": True
            }
            
            with open(base_file, 'w', encoding='utf-8') as f:
                json.dump(default_base, f, indent=4)

            # Reload settings using SettingsManager
            self.provider_settings = self.settings_manager.get_provider_settings()
            self.base_settings = self.settings_manager.get_llm_settings()

            # Repopulate UI
            self._populate_settings()
            
            # Show success message
            QMessageBox.information(
                self,
                "Settings Reset",
                "LLM settings have been reset to default values.\nPrevious settings were backed up in the config/llm/backup directory."
            )
            
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while resetting settings: {str(e)}"
            )
    
    def _test_connections(self):
        """Test LLM connections."""
        try:
            # Save current settings temporarily
            self.save_settings(show_success=False)
            
            # Reinitialize provider manager
            self.provider_manager = get_provider_manager()
            
            # Run diagnostics
            diagnostics = self.llm_manager.run_llm_diagnostics()
            
            # Build results message
            message = f"LLM Diagnostics: {diagnostics['status']}\n\n"
            
            for provider_name, provider_result in diagnostics.get("providers", {}).items():
                status = provider_result.get("status", "unknown")
                status_text = "✓ Success" if status == "success" else "✗ Failed"
                
                message += f"{provider_name}: {status_text}\n"
                
                if status == "success":
                    model = provider_result.get("model", "unknown")
                    message += f"  Model: {model}\n"
                    message += f"  Response: {provider_result.get('response_content', '')[:50]}...\n"
                else:
                    message += f"  Error: {provider_result.get('error', 'Unknown error')}\n"
                
                message += "\n"
            
            # Show results
            QMessageBox.information(
                self,
                "Connection Test Results",
                message
            )
            
        except Exception as e:
            logger.error(f"Error testing connections: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while testing connections: {str(e)}"
            )
    
    def save_settings(self, show_success=True) -> bool:
        """Save settings to configuration files and QSettings.
        
        Args:
            show_success: Whether to show a success message
            
        Returns:
            True if settings were saved successfully, False otherwise
        """
        try:
            # Get settings from UI
            
            # Get settings from UI
            base_settings = self.general_tab.get_settings()
            
            # Get provider settings
            provider_settings = {
                "openai": self.openai_tab.get_settings(),
                "anthropic": self.anthropic_tab.get_settings(),
                "google": self.google_tab.get_settings(),
                "openrouter": self.openrouter_tab.get_settings()
            }
            
            # Save agent settings (This saves agent JSON files via SettingsManager)
            self.agent_setup_tab.save_settings()

            # --- Removed saving provider settings to QSettings ---
            # Provider settings are now saved directly to providers.json
            # by the ModelManagementWidget and provider tabs via SettingsManager.
            # The loop below updates the ProviderManager instance, which relies
            # on SettingsManager having already saved the JSON.

            # Save base settings using SettingsManager
            if self.settings_manager.update_llm_settings(base_settings):
                logger.info("Successfully saved base LLM settings to JSON.")
            else:
                logger.error("Failed to save base LLM settings to JSON.")
                # Optionally raise an error or show a specific message

            # --- Removed saving base settings to QSettings ---
            # self.qsettings.beginGroup("base")
            # for key, value in base_settings.items():
            #     self.qsettings.setValue(key, value)
            # self.qsettings.endGroup()

            # Update provider manager (This updates the in-memory state of the manager)
            for provider_type_name, provider_name in [
                (ProviderType.OPENAI, "openai"),
                (ProviderType.GOOGLE, "google"),
                (ProviderType.OPENROUTER, "openrouter")
            ]:
                # Update provider settings
                if provider_name in provider_settings:
                    self.provider_manager.update_provider_settings(
                        provider_type_name, 
                        provider_settings[provider_name]
                    )
            
            # Set LLM enabled state (if explicitly toggled)
            from core.base.engine import get_game_engine
            engine = get_game_engine()
            if "llm_enabled" in base_settings:
                engine.set_llm_enabled(base_settings["llm_enabled"])
            
            # Ensure live agents pick up new provider/model settings immediately
            try:
                engine.reload_llm_settings()
            except Exception as e:
                logger.error(f"Error reloading LLM agent settings: {e}")
            
            # Show success message
            if show_success:
                QMessageBox.information(
                    self,
                    "Settings Saved",
                    "LLM settings have been saved successfully."
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            
            if show_success:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while saving settings: {str(e)}"
                )
            
            return False


# For testing
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from core.utils.logging_config import setup_logging
    
    # Set up logging
    setup_logging()
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create dialog
    dialog = LLMSettingsDialog()
    
    # Show dialog
    dialog.exec()
