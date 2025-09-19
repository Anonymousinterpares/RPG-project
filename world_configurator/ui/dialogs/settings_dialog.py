"""
Settings dialog for the World Configurator Tool.
"""

import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QTabWidget, QWidget,
    QCheckBox, QComboBox, QSpinBox, QFileDialog
)
import os
from utils.file_manager import get_config_dir, load_json, save_json

from ui.dialogs.base_dialog import BaseDialog

logger = logging.getLogger("world_configurator.ui.dialogs.settings")

class SettingsDialog(BaseDialog):
    """
    Dialog for editing application settings.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the dialog.
        
        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # General tab
        self.general_tab = QWidget()
        self.tab_widget.addTab(self.general_tab, "General")
        
        general_layout = QVBoxLayout(self.general_tab)
        
        # Game path setting
        game_path_layout = QHBoxLayout()
        game_path_layout.addWidget(QLabel("Game Path:"))
        
        self.game_path_edit = QLineEdit()
        game_path_layout.addWidget(self.game_path_edit)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_game_path)
        game_path_layout.addWidget(self.browse_btn)
        
        general_layout.addLayout(game_path_layout)
        
        # Projects folder setting
        projects_path_layout = QHBoxLayout()
        projects_path_layout.addWidget(QLabel("Projects Folder:"))
        
        self.projects_path_edit = QLineEdit()
        projects_path_layout.addWidget(self.projects_path_edit)
        
        self.browse_projects_btn = QPushButton("Browse...")
        self.browse_projects_btn.clicked.connect(self._browse_projects_path)
        projects_path_layout.addWidget(self.browse_projects_btn)
        
        general_layout.addLayout(projects_path_layout)
        
        # Auto-save settings
        self.autosave_check = QCheckBox("Enable Auto-Save")
        general_layout.addWidget(self.autosave_check)
        
        autosave_interval_layout = QHBoxLayout()
        autosave_interval_layout.addWidget(QLabel("Auto-Save Interval (minutes):"))
        
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        self.autosave_interval_spin.setValue(5)
        autosave_interval_layout.addWidget(self.autosave_interval_spin)
        
        general_layout.addLayout(autosave_interval_layout)
        
        # Add spacer to fill remaining space
        general_layout.addStretch()
        
        # Advanced tab
        self.advanced_tab = QWidget()
        self.tab_widget.addTab(self.advanced_tab, "Advanced")
        
        advanced_layout = QVBoxLayout(self.advanced_tab)
        
        # Logging level setting
        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(QLabel("Logging Level:"))
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        log_level_layout.addWidget(self.log_level_combo)
        
        advanced_layout.addLayout(log_level_layout)
        
        # Add spacer to fill remaining space
        advanced_layout.addStretch()

        # LLM tab
        from llm.providers_registry import ProviderRegistry
        from llm.settings import load_llm_settings, save_llm_settings, LLMSettings
        self.llm_tab = QWidget()
        self.tab_widget.addTab(self.llm_tab, "LLM")
        llm_layout = QVBoxLayout(self.llm_tab)
        
        self.provider_combo = QComboBox()
        self.model_combo = QComboBox()
        self.api_key_edit = QLineEdit(); self.api_key_edit.setEchoMode(QLineEdit.Password)
        
        reg = ProviderRegistry(); reg.load()
        providers = reg.list_providers()
        self.provider_combo.addItems(providers)
        
        saved = load_llm_settings()
        
        def _on_provider_changed():
            self.model_combo.clear()
            prov = self.provider_combo.currentText()
            models = reg.list_models_for(prov)
            self.model_combo.addItems([m.get("id", "") for m in models])
            # Load per-provider key
            key = saved.provider_keys.get(prov, "") if saved else ""
            self.api_key_edit.setText(key)
        self.provider_combo.currentTextChanged.connect(_on_provider_changed)
        
        # Initialize from saved
        if saved.provider and saved.provider in providers:
            self.provider_combo.setCurrentText(saved.provider)
        else:
            if providers:
                self.provider_combo.setCurrentIndex(0)
        _on_provider_changed()
        if saved.model:
            self.model_combo.setCurrentText(saved.model)
        
        llm_layout.addLayout(self._form_row("Provider:", self.provider_combo))
        llm_layout.addLayout(self._form_row("Model:", self.model_combo))
        llm_layout.addLayout(self._form_row("API Key:", self.api_key_edit))
        llm_layout.addStretch()

        # NPC Generation tab (Developer)
        self.npc_tab = QWidget()
        self.tab_widget.addTab(self.npc_tab, "NPC Generation")
        npc_layout = QVBoxLayout(self.npc_tab)

        # Mode
        self.npc_mode_combo = QComboBox()
        self.npc_mode_combo.addItems(["families", "legacy"])  # order: prefer new system
        npc_layout.addLayout(self._form_row("Generation Mode:", self.npc_mode_combo))

        # Difficulty and Encounter options populated from generation_rules.json
        self.npc_difficulty_combo = QComboBox()
        self.npc_encounter_combo = QComboBox()
        self._populate_generation_options()
        npc_layout.addLayout(self._form_row("Default Difficulty:", self.npc_difficulty_combo))
        npc_layout.addLayout(self._form_row("Default Encounter Size:", self.npc_encounter_combo))
        npc_layout.addStretch()

        # Initialize values from game/system config
        self._load_npc_generation_settings()
        
        # Buttons
        buttons = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_all)
        self.save_btn.setDefault(True)
        
        buttons.addWidget(self.cancel_btn)
        buttons.addStretch()
        buttons.addWidget(self.save_btn)
        
        layout.addLayout(buttons)
    
    def _form_row(self, label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(widget)
        return row
    
    def _populate_generation_options(self) -> None:
        """Load difficulty and encounter keys from npc/generation_rules.json."""
        try:
            cfg_dir = get_config_dir()
            rules_path = os.path.join(cfg_dir, "npc", "generation_rules.json")
            rules = load_json(rules_path) or {}
            scaling = rules.get("scaling", {}) or {}
            diffs = list((scaling.get("difficulty", {}) or {}).keys())
            encs = list((scaling.get("encounter_size", {}) or {}).keys())
            # Reasonable defaults if empty
            if not diffs:
                diffs = ["story", "normal", "hard", "expert"]
            if not encs:
                encs = ["solo", "pack", "mixed"]
            self.npc_difficulty_combo.clear(); self.npc_difficulty_combo.addItems(diffs)
            self.npc_encounter_combo.clear(); self.npc_encounter_combo.addItems(encs)
        except Exception as e:
            logger.warning(f"Failed to load generation rules options: {e}")
            self.npc_difficulty_combo.clear(); self.npc_difficulty_combo.addItems(["normal"])
            self.npc_encounter_combo.clear(); self.npc_encounter_combo.addItems(["solo"])    
    
    def _load_npc_generation_settings(self) -> None:
        """Initialize UI from system_config.json and game_config.json."""
        try:
            cfg_dir = get_config_dir()
            # system
            sys_path = os.path.join(cfg_dir, "system_config.json")
            sys_data = load_json(sys_path) or {}
            mode = (sys_data.get("npc_generation_mode") or "legacy")
            if mode not in ["families", "legacy"]:
                mode = "legacy"
            self.npc_mode_combo.setCurrentText(mode)
            # game
            game_path = os.path.join(cfg_dir, "game_config.json")
            game_data = load_json(game_path) or {}
            diff = (game_data.get("difficulty") or "normal")
            enc = (game_data.get("encounter_size") or "solo")
            # If values not in options, leave current selection
            if self.npc_difficulty_combo.findText(diff) >= 0:
                self.npc_difficulty_combo.setCurrentText(diff)
            if self.npc_encounter_combo.findText(enc) >= 0:
                self.npc_encounter_combo.setCurrentText(enc)
        except Exception as e:
            logger.warning(f"Failed to load NPC generation settings: {e}")
    
    def _browse_game_path(self):
        """Open file dialog to select the game path."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Game Directory", self.game_path_edit.text()
        )
        if directory:
            self.game_path_edit.setText(directory)
    
    def _browse_projects_path(self):
        """Open file dialog to select the projects folder."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Projects Directory", self.projects_path_edit.text()
        )
        if directory:
            self.projects_path_edit.setText(directory)
    
    def _save_all(self) -> None:
        # Persist LLM settings
        from llm.settings import save_llm_settings, load_llm_settings, LLMSettings
        # Fill api_base from provider registry if available
        from llm.providers_registry import ProviderRegistry
        reg = ProviderRegistry(); reg.load()
        info = reg.provider_info(self.provider_combo.currentText()) or {}
        current_provider = self.provider_combo.currentText()
        # Load existing and update per-provider keys
        existing = load_llm_settings()
        provider_keys = existing.provider_keys or {}
        provider_keys[current_provider] = self.api_key_edit.text()
        s = LLMSettings(
            provider=current_provider,
            model=self.model_combo.currentText(),
            api_key=self.api_key_edit.text(),
            api_base=info.get("api_base"),
            provider_keys=provider_keys,
        )
        save_llm_settings(s)

        # Persist NPC generation settings to game/system config
        try:
            cfg_dir = get_config_dir()
            # system_config.json
            sys_path = os.path.join(cfg_dir, "system_config.json")
            sys_data = load_json(sys_path) or {}
            sys_data["npc_generation_mode"] = self.npc_mode_combo.currentText()
            save_json(sys_data, sys_path)
            # game_config.json
            game_path = os.path.join(cfg_dir, "game_config.json")
            game_data = load_json(game_path) or {}
            game_data["difficulty"] = self.npc_difficulty_combo.currentText()
            game_data["encounter_size"] = self.npc_encounter_combo.currentText()
            save_json(game_data, game_path)
        except Exception as e:
            logger.error(f"Failed to save NPC generation settings: {e}")

        self.accept()
    
    def get_settings(self) -> dict:
        """
        Get the settings selected by the user.
        
        Returns:
            A dictionary of settings.
        """
        return {
            "game_path": self.game_path_edit.text(),
            "projects_path": self.projects_path_edit.text(),
            "autosave": self.autosave_check.isChecked(),
            "autosave_interval": self.autosave_interval_spin.value(),
            "log_level": self.log_level_combo.currentText()
        }
