"""
Export dialog for the World Configurator Tool.
"""

import logging
from typing import Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QCheckBox, QLabel,
    QPushButton, QHBoxLayout, QGroupBox
)

from ui.dialogs.base_dialog import BaseDialog

logger = logging.getLogger("world_configurator.ui.dialogs.export")

class ExportDialog(BaseDialog):
    """
    Dialog for exporting project to the game.
    """

    def __init__(self, parent=None):
        """
        Initialize the dialog.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)

        self.setWindowTitle("Export to Game")
        self.setMinimumWidth(400)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        # Main layout
        layout = QVBoxLayout(self)

        # Add description
        description = QLabel(
            "This will export the world configuration to the game's configuration directory. "
            "Select the components you want to export:"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Components group box
        components_group = QGroupBox("Components")
        self.components_layout = QVBoxLayout(components_group)

        # Component checkboxes
        self.chk_cultures = QCheckBox("Cultures")
        self.chk_cultures.setChecked(True)
        self.components_layout.addWidget(self.chk_cultures)

        self.chk_races = QCheckBox("Races")
        self.chk_races.setChecked(True)
        self.components_layout.addWidget(self.chk_races)

        self.chk_classes = QCheckBox("Classes")
        self.chk_classes.setChecked(True)
        self.components_layout.addWidget(self.chk_classes)

        self.chk_skills = QCheckBox("Skills") # NEW
        self.chk_skills.setChecked(True)
        self.components_layout.addWidget(self.chk_skills)

        # Item categories - NEW
        self.item_checkboxes: Dict[str, QCheckBox] = {}
        from ..editors.item_editor_panel import ITEM_CATEGORIES as ITEM_CATS_FOR_EXPORT # Use the same source
        for cat_name in ITEM_CATS_FOR_EXPORT.keys():
            chk = QCheckBox(cat_name)
            chk.setChecked(True)
            self.components_layout.addWidget(chk)
            self.item_checkboxes[cat_name] = chk


        self.chk_locations = QCheckBox("Locations")
        self.chk_locations.setChecked(True)
        self.components_layout.addWidget(self.chk_locations)

        # Location defaults (culture mix)
        self.chk_location_defaults = QCheckBox("Culture Mix Defaults (Locations)")
        self.chk_location_defaults.setChecked(True)
        self.components_layout.addWidget(self.chk_location_defaults)

        self.chk_history = QCheckBox("World History")
        self.chk_history.setChecked(True)
        self.components_layout.addWidget(self.chk_history)

        self.chk_rules = QCheckBox("Fundamental Rules")
        self.chk_rules.setChecked(True)
        self.components_layout.addWidget(self.chk_rules)

        self.chk_origins = QCheckBox("Origins")
        self.chk_origins.setChecked(True)
        self.components_layout.addWidget(self.chk_origins)

        self.chk_quests = QCheckBox("Quests")
        self.chk_quests.setChecked(True)
        self.components_layout.addWidget(self.chk_quests)

        self.chk_magic_systems = QCheckBox("Magic Systems")
        self.chk_magic_systems.setChecked(True)
        self.components_layout.addWidget(self.chk_magic_systems)

        self.chk_names = QCheckBox("Names")
        self.chk_names.setChecked(True)
        self.components_layout.addWidget(self.chk_names)
        
        self.chk_variants = QCheckBox("NPC Variants")
        self.chk_variants.setChecked(True)
        self.components_layout.addWidget(self.chk_variants)

        layout.addWidget(components_group)

        # Select all/none buttons
        select_buttons = QHBoxLayout()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        select_buttons.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self._select_none)
        select_buttons.addWidget(self.select_none_btn)

        layout.addLayout(select_buttons)

        # Buttons
        buttons = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.accept)
        self.export_btn.setDefault(True)

        buttons.addWidget(self.cancel_btn)
        buttons.addStretch()
        buttons.addWidget(self.export_btn)

        layout.addLayout(buttons)
        
    def _select_all(self):
        """Select all components."""
        self.chk_cultures.setChecked(True)
        self.chk_races.setChecked(True)
        self.chk_classes.setChecked(True)
        self.chk_skills.setChecked(True) # NEW
        for chk_item_cat in self.item_checkboxes.values(): # NEW
            chk_item_cat.setChecked(True)
        self.chk_locations.setChecked(True)
        self.chk_location_defaults.setChecked(True)
        self.chk_history.setChecked(True)
        self.chk_rules.setChecked(True)
        self.chk_origins.setChecked(True)
        self.chk_quests.setChecked(True)
        self.chk_magic_systems.setChecked(True)
        self.chk_names.setChecked(True)
        self.chk_variants.setChecked(True)

    def _select_none(self):
        """Deselect all components."""
        self.chk_cultures.setChecked(False)
        self.chk_races.setChecked(False)
        self.chk_classes.setChecked(False)
        self.chk_skills.setChecked(False) # NEW
        for chk_item_cat in self.item_checkboxes.values(): # NEW
            chk_item_cat.setChecked(False)
        self.chk_locations.setChecked(False)
        self.chk_location_defaults.setChecked(False)
        self.chk_history.setChecked(False)
        self.chk_rules.setChecked(False)
        self.chk_origins.setChecked(False)
        self.chk_quests.setChecked(False)
        self.chk_magic_systems.setChecked(False)
        self.chk_names.setChecked(False)
        self.chk_variants.setChecked(False)

    def get_export_options(self) -> dict:
        """
        Get the export options selected by the user.

        Returns:
            A dictionary of export options.
        """
        options = {
            "cultures": self.chk_cultures.isChecked(),
            "races": self.chk_races.isChecked(),
            "classes": self.chk_classes.isChecked(),
            "skills": self.chk_skills.isChecked(), # NEW
            "locations": self.chk_locations.isChecked(),
            "location_defaults": self.chk_location_defaults.isChecked(),
            "history": self.chk_history.isChecked(),
            "rules": self.chk_rules.isChecked(),
            "origins": self.chk_origins.isChecked(),
            "quests": self.chk_quests.isChecked(),
            "magic_systems": self.chk_magic_systems.isChecked(),
            "names": self.chk_names.isChecked(),
            "variants": self.chk_variants.isChecked(),
        }
        # Add item categories to options - NEW
        from ..editors.item_editor_panel import ITEM_CATEGORIES as ITEM_CATS_FOR_EXPORT_GET
        for cat_key_export, _ in ITEM_CATS_FOR_EXPORT_GET.items():

            if cat_key_export == "Starting Items":
                options["items_origin"] = self.item_checkboxes[cat_key_export].isChecked()
            elif cat_key_export == "Weapon Templates":
                options["items_weapons"] = self.item_checkboxes[cat_key_export].isChecked()
            elif cat_key_export == "Armor Templates":
                options["items_armor"] = self.item_checkboxes[cat_key_export].isChecked()
            elif cat_key_export == "Consumable Templates":
                options["items_consumables"] = self.item_checkboxes[cat_key_export].isChecked()
            elif cat_key_export == "Miscellaneous Templates":
                options["items_misc"] = self.item_checkboxes[cat_key_export].isChecked()
            # Add more mappings if there are other item categories

        return options