# gui/advanced_config_editor/form_views/scenarios_form.py
"""
Form view for starting scenarios configuration.
"""
import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QListWidget, QPushButton, QPlainTextEdit,
    QMessageBox, QComboBox, QDialog, QListWidgetItem, QDialogButtonBox, 
    QGroupBox, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap, QFont

from core.utils.logging_config import LogCategory, LoggingConfig
from ..custom_widgets import AutoResizingPlainTextEdit
from core.inventory.item_manager import InventoryManager
from core.inventory.item import ItemType

def create_scenarios_form_tab(parent, data, save_callback):
    """
    Create and populate the Starting Scenarios tab in form view.
    
    Args:
        parent: Parent widget
        data (dict): The scenarios data
        save_callback (callable): Function to call when saving data
        
    Returns:
        QWidget: The scenarios tab widget
    """
    LoggingConfig.setup_logging()
    logger = LoggingConfig.get_logger(__name__, LogCategory.CONFIG)    
    scenarios_tab = QWidget()
    layout = QVBoxLayout(scenarios_tab)

    # Add title and description
    layout.addWidget(QLabel("<h2>Starting Scenarios</h2>"))
    layout.addWidget(QLabel("Configure starting scenarios for different character paths and backgrounds"))
    
    # Create horizontally split layout
    split_layout = QHBoxLayout()
    
    # Left side: Tree-like selection
    selection_layout = QVBoxLayout()
    selection_layout.addWidget(QLabel("Select Path and Scenario:"))
    
    # ComboBox for paths
    path_combo = QComboBox()
    if "paths" in data:
        for path_key, path_data in data["paths"].items():
            path_combo.addItem(path_data.get("name", path_key), path_key)
    
    # List for scenarios under the selected path
    scenario_list = QListWidget()
    
    selection_layout.addWidget(path_combo)
    selection_layout.addWidget(scenario_list)
    
    # Right side: Scenario editor form
    editor_layout = QVBoxLayout()
    
    # Make form scrollable for better usability
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QScrollArea.NoFrame)
    
    form_widget = QWidget()
    form_layout = QFormLayout(form_widget)
    form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    
    name_edit = QLineEdit()
    location_edit = QLineEdit()
    district_edit = QLineEdit()
    time_edit = QLineEdit()
    
    # Description and narrative elements
    intro_edit = AutoResizingPlainTextEdit(min_lines=2, max_lines=8)
    intro_edit.setMaximumHeight(100)
    goals_edit = AutoResizingPlainTextEdit(min_lines=2, max_lines=8)
    goals_edit.setMaximumHeight(100)
    
    form_layout.addRow("Scenario Name:", name_edit)
    form_layout.addRow("Location:", location_edit)
    form_layout.addRow("District:", district_edit)
    form_layout.addRow("Starting Time:", time_edit)
    form_layout.addRow("Introduction:", intro_edit)
    form_layout.addRow("Immediate Goals:", goals_edit)
    
    # Create a group box for applicable backgrounds with clear instruction
    bg_group = QGroupBox("Applicable Backgrounds")
    bg_layout = QVBoxLayout(bg_group)
    
    bg_group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            background-color: #f0f0f0;
            border: 2px solid #aaa;
            border-radius: 5px;
            margin-top: 15px;
            padding-top: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            background-color: #f0f0f0;
        }
    """)

    # And make the instruction label more prominent
    instruction_label = QLabel(
        "IMPORTANT: Select which backgrounds can use this scenario. "
        "The scenario will only be available to characters with these backgrounds."
    )
    instruction_label.setWordWrap(True)
    instruction_label.setStyleSheet("font-style: italic; color: #d04000; font-weight: bold;")
    bg_layout.addWidget(instruction_label)
    
    # Create a container for checkboxes
    bg_container = QWidget()
    bg_container_layout = QVBoxLayout(bg_container)
    bg_container_layout.setContentsMargins(0, 0, 0, 0)
    bg_container_layout.setSpacing(2)
    
    # This dict will hold all our background checkboxes
    bg_checkboxes = {}
    
    # Add select all checkbox
    select_all_checkbox = QCheckBox("Select All")
    select_all_checkbox.setStyleSheet("font-weight: bold;")
    bg_layout.addWidget(select_all_checkbox)
    
    # Add scrollable area for backgrounds to allow many options
    bg_scroll = QScrollArea()
    bg_scroll.setWidgetResizable(True)
    bg_scroll.setWidget(bg_container)
    bg_scroll.setMaximumHeight(150)
    bg_layout.addWidget(bg_scroll)
    
    form_layout.addRow(bg_group)
    
    # Add Starting Equipment Section
    equipment_label = QLabel("<b>Starting Equipment:</b>")
    equipment_list = QListWidget()
    equipment_list.setMaximumHeight(150)
    equipment_button_layout = QHBoxLayout()
    add_equipment_btn = QPushButton("Add Item")
    remove_equipment_btn = QPushButton("Remove Item")
    equipment_button_layout.addWidget(add_equipment_btn)
    equipment_button_layout.addWidget(remove_equipment_btn)
    
    form_layout.addRow(equipment_label)
    form_layout.addRow(equipment_list)
    form_layout.addRow("", equipment_button_layout)
    
    # Add the form to the scroll area
    scroll_area.setWidget(form_widget)
    editor_layout.addWidget(scroll_area)
    
    # Item Selection Dialog Class
    class ItemSelectionDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Select Equipment")
            self.setMinimumWidth(500)
            self.layout = QVBoxLayout(self)
            
            # Create inventory manager with game config
            from core.base.config import GameConfig
            self.inventory_manager = InventoryManager(GameConfig())
            
            # Create list widget for items
            self.item_list = QListWidget()
            self.layout.addWidget(QLabel("Available Items:"))
            self.layout.addWidget(self.item_list)
            
            # Add filter by type combobox
            self.filter_layout = QHBoxLayout()
            self.filter_layout.addWidget(QLabel("Filter by Type:"))
            self.filter_combo = QComboBox()
            self.filter_combo.addItem("All Items", -1)
            self.filter_combo.addItem("Weapons", ItemType.WEAPON.value)
            self.filter_combo.addItem("Armor", ItemType.ARMOR.value)
            self.filter_combo.addItem("Accessories", ItemType.ACCESSORY.value)
            self.filter_combo.addItem("Consumables", ItemType.CONSUMABLE.value)
            self.filter_combo.addItem("Miscellaneous", ItemType.MISCELLANEOUS.value)
            self.filter_layout.addWidget(self.filter_combo)
            self.layout.addLayout(self.filter_layout)
            
            # Add dialog buttons
            self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            self.button_box.accepted.connect(self.accept)
            self.button_box.rejected.connect(self.reject)
            self.layout.addWidget(self.button_box)
            
            # Connect signals
            self.filter_combo.currentIndexChanged.connect(self.update_item_list)
            
            # Populate items
            self.update_item_list()
        
        def update_item_list(self):
            self.item_list.clear()
            filter_type = self.filter_combo.currentData()
            
            # Get all items from inventory manager
            for item_id, item in self.inventory_manager.item_database.items():
                # Apply filter if not "All Items"
                if filter_type != -1 and item.item_type.value != filter_type:
                    continue
                
                # Create list item
                list_item = QListWidgetItem(f"{item.name} ({item.item_type.name.title()})")
                list_item.setData(Qt.UserRole, item_id)
                
                # Set icon if available
                icon_path = item.icon
                if icon_path and os.path.exists(icon_path):
                    list_item.setIcon(QIcon(icon_path))
                else:
                    # Create colored placeholder
                    pixmap = QPixmap(24, 24)
                    if item.item_type == ItemType.WEAPON:
                        pixmap.fill(QColor(255, 0, 0, 180))
                    elif item.item_type == ItemType.ARMOR:
                        pixmap.fill(QColor(0, 0, 255, 180))
                    elif item.item_type == ItemType.ACCESSORY:
                        pixmap.fill(QColor(255, 215, 0, 180))
                    elif item.item_type == ItemType.CONSUMABLE:
                        pixmap.fill(QColor(0, 255, 0, 180))
                    else:
                        pixmap.fill(QColor(150, 150, 150, 180))
                    
                    list_item.setIcon(QIcon(pixmap))
                
                self.item_list.addItem(list_item)
        
        def get_selected_item_id(self):
            if self.item_list.currentItem():
                return self.item_list.currentItem().data(Qt.UserRole)
            return None
    
    # Function to add equipment to the list
    def add_equipment():
        dialog = ItemSelectionDialog(parent)
        if dialog.exec() == QDialog.Accepted:
            item_id = dialog.get_selected_item_id()
            if item_id:
                # Check if item is already in the list
                for i in range(equipment_list.count()):
                    if equipment_list.item(i).data(Qt.UserRole) == item_id:
                        QMessageBox.warning(parent, "Already Added", 
                                           "This item is already in the starting equipment.")
                        return
                
                # Add item to the list
                from core.base.config import GameConfig
                inventory_manager = InventoryManager(GameConfig())
                item = inventory_manager.item_database.get(item_id)
                if item:
                    list_item = QListWidgetItem(f"{item.name} ({item.item_type.name.title()})")
                    list_item.setData(Qt.UserRole, item_id)
                    
                    # Set icon if available
                    icon_path = item.icon
                    if icon_path and os.path.exists(icon_path):
                        list_item.setIcon(QIcon(icon_path))
                    else:
                        # Create colored placeholder
                        pixmap = QPixmap(24, 24)
                        if item.item_type == ItemType.WEAPON:
                            pixmap.fill(QColor(255, 0, 0, 180))
                        elif item.item_type == ItemType.ARMOR:
                            pixmap.fill(QColor(0, 0, 255, 180))
                        elif item.item_type == ItemType.ACCESSORY:
                            pixmap.fill(QColor(255, 215, 0, 180))
                        elif item.item_type == ItemType.CONSUMABLE:
                            pixmap.fill(QColor(0, 255, 0, 180))
                        else:
                            pixmap.fill(QColor(150, 150, 150, 180))
                        
                        list_item.setIcon(QIcon(pixmap))
                    
                    equipment_list.addItem(list_item)
    
    # Function to remove equipment from the list
    def remove_equipment():
        current_item = equipment_list.currentItem()
        if current_item:
            equipment_list.takeItem(equipment_list.row(current_item))
        else:
            QMessageBox.warning(parent, "No Selection", "Please select an item to remove.")
    
    # Connect equipment buttons
    add_equipment_btn.clicked.connect(add_equipment)
    remove_equipment_btn.clicked.connect(remove_equipment)
    
    # Function to populate backgrounds checkboxes for a path
    def populate_background_checkboxes(path_key):
        """Populate background checkboxes only for the selected path's backgrounds"""
        # Clear existing checkboxes
        for checkbox in bg_checkboxes.values():
            checkbox.setParent(None)
        bg_checkboxes.clear()
        
        # First, clear any existing widgets in the container
        for i in reversed(range(bg_container_layout.count())):
            item = bg_container_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        # We need to get ONLY the backgrounds for the selected path
        backgrounds_found = False
        path_backgrounds = []
        
        # First, try to get backgrounds from the Paths data
        if "paths" in data:
            path_data = data["paths"].get(path_key, {})
            
            # Get backgrounds directly from the path's backgrounds
            if "backgrounds" in path_data and isinstance(path_data["backgrounds"], dict):
                backgrounds_found = True
                for bg_key, bg_data in path_data["backgrounds"].items():
                    path_backgrounds.append(bg_key)
                    bg_name = bg_data.get("name", bg_key.replace("_", " ").title())
                    checkbox = QCheckBox(bg_name)
                    checkbox.setProperty("bg_key", bg_key)
                    bg_container_layout.addWidget(checkbox)
                    bg_checkboxes[bg_key] = checkbox
        
        # If no backgrounds found, check background files as a fallback
        if not backgrounds_found:
            # Look for background files associated with this path
            try:
                bg_filename = None
                if "paths" in data:
                    path_data = data["paths"].get(path_key, {})
                    if "backgrounds_file" in path_data:
                        bg_filename = path_data["backgrounds_file"]
                
                if bg_filename:
                    # Construct the path to the background file
                    bg_path = f"config/world/characters/backgrounds/{os.path.basename(bg_filename)}"
                    if os.path.exists(bg_path):
                        with open(bg_path, "r", encoding="utf-8") as f:
                            bg_data = json.load(f)
                        
                        if "backgrounds" in bg_data and isinstance(bg_data["backgrounds"], dict):
                            backgrounds_found = True
                            for bg_key, bg_info in bg_data["backgrounds"].items():
                                path_backgrounds.append(bg_key)
                                bg_name = bg_info.get("name", bg_key.replace("_", " ").title())
                                checkbox = QCheckBox(bg_name)
                                checkbox.setProperty("bg_key", bg_key)
                                bg_container_layout.addWidget(checkbox)
                                bg_checkboxes[bg_key] = checkbox
            except Exception as e:
                logger.error(f"Error loading background file: {e}")
        
        # If still no backgrounds found, try one more approach - look at existing scenarios
        if not backgrounds_found and "paths" in data:
            path_data = data["paths"].get(path_key, {})
            if "scenarios" in path_data:
                # Collect all unique background keys from all scenarios in this path
                unique_backgrounds = set()
                for scenario_key, scenario in path_data["scenarios"].items():
                    if "applicable_backgrounds" in scenario and isinstance(scenario["applicable_backgrounds"], list):
                        for bg_key in scenario["applicable_backgrounds"]:
                            unique_backgrounds.add(bg_key)
                
                if unique_backgrounds:
                    backgrounds_found = True
                    for bg_key in sorted(unique_backgrounds):
                        path_backgrounds.append(bg_key)
                        # Try to get a nicer display name
                        bg_name = bg_key.replace("_", " ").title()
                        checkbox = QCheckBox(bg_name)
                        checkbox.setProperty("bg_key", bg_key)
                        bg_container_layout.addWidget(checkbox)
                        bg_checkboxes[bg_key] = checkbox
        
        # If no backgrounds found using any approach, add a message
        if not backgrounds_found:
            no_bg_label = QLabel(f"No backgrounds found for path: {path_key}. Add backgrounds in the Paths tab first.")
            no_bg_label.setStyleSheet("color: red; font-style: italic;")
            bg_container_layout.addWidget(no_bg_label)
        else:
            # Show info about what we found
            info_label = QLabel(f"Found {len(path_backgrounds)} backgrounds for path: {path_key}")
            info_label.setStyleSheet("color: green; font-style: italic;")
            bg_container_layout.addWidget(info_label)
        
        # Enable/disable select all based on checkbox count
        select_all_checkbox.setEnabled(len(bg_checkboxes) > 0)
        
        # Force layout update
        bg_container.updateGeometry()
    
    # Handler for select all checkbox
    def on_select_all_changed(state):
        for checkbox in bg_checkboxes.values():
            checkbox.setChecked(state == Qt.Checked)
    
    select_all_checkbox.stateChanged.connect(on_select_all_changed)
    
    # Function to update scenario list when path changes
    def update_scenario_list():
        """Update the list of scenarios for the selected path with additional debugging"""
        scenario_list.clear()
        path_key = path_combo.currentData()
        
        logger.debug(f"\nUpdating scenario list for path: {path_key}")
        logger.debug(f"Data structure has 'paths'?: {'paths' in data}")
        
        if path_key and "paths" in data:
            path_data = data["paths"].get(path_key, {})
            logger.debug(f"Path data keys: {list(path_data.keys())}")
            
            if "scenarios" in path_data:
                logger.debug(f"Found {len(path_data['scenarios'])} scenarios")
                for scenario_key, scenario in path_data["scenarios"].items():
                    scenario_name = scenario.get("name", scenario_key)
                    scenario_list.addItem(scenario_name)
                    
                    # Debug info for this scenario
                    applicable = scenario.get("applicable_backgrounds", [])
                    logger.debug(f"  Scenario {scenario_name}: applicable_backgrounds={applicable}")
            else:
                logger.error("No scenarios found in path data")
        else:
            logger.error("Path key not found or 'paths' not in data")
        
        # Update backgrounds for this path - with additional debug output
        logger.debug(f"About to populate background checkboxes for path: {path_key}")
        populate_background_checkboxes(path_key)
        logger.debug(f"After populating: found {len(bg_checkboxes)} background checkboxes")
    
    # Function to load scenario details when selected
    def load_scenario_details():
        """Load scenario details when selected"""
        if not scenario_list.currentItem():
            return
            
        scenario_name = scenario_list.currentItem().text()
        path_key = path_combo.currentData()
        
        if path_key and "paths" in data:
            path_data = data["paths"].get(path_key, {})
            if "scenarios" in path_data:
                # Find scenario by name
                scenario_data = None
                scenario_key = None
                for key, entry in path_data["scenarios"].items():
                    if entry.get("name") == scenario_name:
                        scenario_data = entry
                        scenario_key = key
                        break
                
                if scenario_data:
                    # Clear equipment list
                    equipment_list.clear()
                    
                    name_edit.setText(scenario_data.get("name", ""))
                    location_edit.setText(scenario_data.get("location", ""))
                    district_edit.setText(scenario_data.get("district", ""))
                    time_edit.setText(scenario_data.get("starting_time", ""))
                    
                    # Load narrative elements
                    if "narrative_elements" in scenario_data:
                        narrative = scenario_data["narrative_elements"]
                        
                        if "introduction" in narrative:
                            if isinstance(narrative["introduction"], list):
                                intro_edit.setPlainText("\n".join(narrative["introduction"]))
                            else:
                                intro_edit.setPlainText(str(narrative["introduction"]))
                                
                        if "immediate_goals" in narrative:
                            if isinstance(narrative["immediate_goals"], list):
                                goals_edit.setPlainText("\n".join(narrative["immediate_goals"]))
                            else:
                                goals_edit.setPlainText(str(narrative["immediate_goals"]))
                    
                    # Populate background checkboxes if they aren't populated yet
                    if not bg_checkboxes:
                        populate_background_checkboxes(path_key)
                    
                    # Get applicable backgrounds for this scenario
                    applicable_backgrounds = scenario_data.get("applicable_backgrounds", [])
                    
                    # Debug info
                    logger.debug(f"Scenario {scenario_name} applicable backgrounds: {applicable_backgrounds}")
                    logger.debug(f"Available background checkboxes: {list(bg_checkboxes.keys())}")
                    
                    # Uncheck all checkboxes first
                    for checkbox in bg_checkboxes.values():
                        checkbox.setChecked(False)
                    
                    # Now check only those backgrounds that are applicable
                    for bg_key, checkbox in bg_checkboxes.items():
                        # Check if this background is in the applicable_backgrounds list
                        # We need to handle different formats (with/without underscores)
                        bg_key_lower = bg_key.lower()
                        checkbox_should_be_checked = False
                        
                        # Check if this background is in applicable_backgrounds directly
                        if bg_key in applicable_backgrounds:
                            checkbox_should_be_checked = True
                        
                        # Also check case-insensitive and with/without underscores
                        for applicable_bg in applicable_backgrounds:
                            applicable_lower = applicable_bg.lower()
                            # Check normal
                            if bg_key_lower == applicable_lower:
                                checkbox_should_be_checked = True
                                break
                            # Check with spaces converted to underscores
                            if bg_key_lower == applicable_lower.replace(" ", "_"):
                                checkbox_should_be_checked = True
                                break
                            # Check with underscores converted to spaces
                            if bg_key_lower.replace("_", " ") == applicable_lower:
                                checkbox_should_be_checked = True
                                break
                        
                        # Set the checkbox state
                        checkbox.setChecked(checkbox_should_be_checked)
                        
                        # Add visual indicator of checked status
                        if checkbox_should_be_checked:
                            checkbox.setStyleSheet("font-weight: bold; color: #006400;")  # Dark green color
                        else:
                            checkbox.setStyleSheet("")  # Reset style
                    
                    # Update select all checkbox state
                    if bg_checkboxes:
                        if all(checkbox.isChecked() for checkbox in bg_checkboxes.values()):
                            select_all_checkbox.setChecked(True)
                        else:
                            select_all_checkbox.setChecked(False)
                    
                    # Load starting equipment if present
                    if "starting_equipment" in scenario_data:
                        from core.base.config import GameConfig
                        inventory_manager = InventoryManager(GameConfig())
                        for item_id in scenario_data["starting_equipment"]:
                            item = inventory_manager.item_database.get(item_id)
                            if item:
                                list_item = QListWidgetItem(f"{item.name} ({item.item_type.name.title()})")
                                list_item.setData(Qt.UserRole, item_id)
                                
                                # Set icon if available
                                icon_path = item.icon
                                if icon_path and os.path.exists(icon_path):
                                    list_item.setIcon(QIcon(icon_path))
                                else:
                                    # Create colored placeholder
                                    pixmap = QPixmap(24, 24)
                                    if item.item_type == ItemType.WEAPON:
                                        pixmap.fill(QColor(255, 0, 0, 180))
                                    elif item.item_type == ItemType.ARMOR:
                                        pixmap.fill(QColor(0, 0, 255, 180))
                                    elif item.item_type == ItemType.ACCESSORY:
                                        pixmap.fill(QColor(255, 215, 0, 180))
                                    elif item.item_type == ItemType.CONSUMABLE:
                                        pixmap.fill(QColor(0, 255, 0, 180))
                                    else:
                                        pixmap.fill(QColor(150, 150, 150, 180))
                                    
                                    list_item.setIcon(QIcon(pixmap))
                                
                                equipment_list.addItem(list_item)
    
    # Function to add a new scenario
    def add_scenario():
        path_key = path_combo.currentData()
        if not path_key or not "paths" in data:
            QMessageBox.critical(parent, "Error", "Please select a valid path.")
            return
        
        scenario_name = name_edit.text().strip()
        if not scenario_name:
            QMessageBox.critical(parent, "Error", "Scenario name is required.")
            return
        
        # Create scenario key from name
        scenario_key = scenario_name.lower().replace(" ", "_")
        
        # Check if scenario already exists
        path_data = data["paths"].get(path_key, {})
        if "scenarios" not in path_data:
            path_data["scenarios"] = {}
        
        if scenario_key in path_data["scenarios"]:
            reply = QMessageBox.question(
                parent, 
                "Scenario Exists", 
                f"A scenario with key '{scenario_key}' already exists for this path. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Process introduction and goals as lists
        intro_text = intro_edit.toPlainText().strip()
        goals_text = goals_edit.toPlainText().strip()
        
        intro_list = [line.strip() for line in intro_text.split("\n") if line.strip()]
        goals_list = [line.strip() for line in goals_text.split("\n") if line.strip()]
        
        # Get selected applicable backgrounds
        applicable_backgrounds = []
        for bg_key, checkbox in bg_checkboxes.items():
            if checkbox.isChecked():
                applicable_backgrounds.append(bg_key)
        
        # Create scenario data
        scenario_data = {
            "name": scenario_name,
            "location": location_edit.text().strip(),
            "district": district_edit.text().strip(),
            "starting_time": time_edit.text().strip(),
            "narrative_elements": {
                "introduction": intro_list,
                "immediate_goals": goals_list
            },
            "applicable_backgrounds": applicable_backgrounds
        }
        
        # Add starting equipment if any
        equipment_items = []
        for i in range(equipment_list.count()):
            item = equipment_list.item(i)
            item_id = item.data(Qt.UserRole)
            equipment_items.append(item_id)
        
        if equipment_items:
            scenario_data["starting_equipment"] = equipment_items
        
        # Add scenario to path
        path_data["scenarios"][scenario_key] = scenario_data
        
        # Save to file
        save_callback("StartingScenarios")
        
        # Update scenarios list
        update_scenario_list()
        
        QMessageBox.information(parent, "Success", f"Scenario '{scenario_name}' added successfully.")
    
    # Function to update an existing scenario
    def update_scenario():
        if not scenario_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a scenario to update.")
            return
        
        scenario_name = scenario_list.currentItem().text()
        path_key = path_combo.currentData()
        
        if not path_key or not "paths" in data:
            QMessageBox.critical(parent, "Error", "Please select a valid path.")
            return
        
        path_data = data["paths"].get(path_key, {})
        if "scenarios" not in path_data:
            QMessageBox.critical(parent, "Error", "No scenarios found for this path.")
            return
        
        # Find scenario key
        scenario_key = None
        for key, entry in path_data["scenarios"].items():
            if entry.get("name") == scenario_name:
                scenario_key = key
                break
        
        if not scenario_key:
            QMessageBox.critical(parent, "Error", "Could not find scenario in data.")
            return
        
        # Process introduction and goals as lists
        intro_text = intro_edit.toPlainText().strip()
        goals_text = goals_edit.toPlainText().strip()
        
        intro_list = [line.strip() for line in intro_text.split("\n") if line.strip()]
        goals_list = [line.strip() for line in goals_text.split("\n") if line.strip()]
        
        # Get selected applicable backgrounds
        applicable_backgrounds = []
        for bg_key, checkbox in bg_checkboxes.items():
            if checkbox.isChecked():
                applicable_backgrounds.append(bg_key)
        
        # Validate that at least one background is selected
        if not applicable_backgrounds:
            reply = QMessageBox.question(
                parent,
                "No Backgrounds Selected",
                "You haven't selected any applicable backgrounds. This scenario won't be available to any character.\n\nContinue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Create updated scenario data
        updated_name = name_edit.text().strip()
        scenario_data = {
            "name": updated_name,
            "location": location_edit.text().strip(),
            "district": district_edit.text().strip(),
            "starting_time": time_edit.text().strip(),
            "narrative_elements": {
                "introduction": intro_list,
                "immediate_goals": goals_list
            },
            "applicable_backgrounds": applicable_backgrounds
        }
        
        # Add starting equipment if any
        equipment_items = []
        for i in range(equipment_list.count()):
            item = equipment_list.item(i)
            item_id = item.data(Qt.UserRole)
            equipment_items.append(item_id)
        
        if equipment_items:
            scenario_data["starting_equipment"] = equipment_items
        
        # Check if name changed, requiring a new key
        if updated_name != scenario_name:
            new_key = updated_name.lower().replace(" ", "_")
            
            # Check if new key would conflict
            if new_key != scenario_key and new_key in path_data["scenarios"]:
                reply = QMessageBox.question(
                    parent, 
                    "Key Conflict", 
                    f"Changing the name will create a key '{new_key}' that already exists. Continue and overwrite?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
                
            # Remove old scenario and add with new key
            del path_data["scenarios"][scenario_key]
            path_data["scenarios"][new_key] = scenario_data
        else:
            # Just update the existing scenario
            path_data["scenarios"][scenario_key] = scenario_data
        
        # Save to file
        save_callback("StartingScenarios")
        
        # Update scenarios list
        update_scenario_list()
        
        QMessageBox.information(parent, "Success", f"Scenario '{updated_name}' updated successfully.")
    
    # Function to delete a scenario
    def delete_scenario():
        if not scenario_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a scenario to delete.")
            return
        
        scenario_name = scenario_list.currentItem().text()
        path_key = path_combo.currentData()
        
        if not path_key or not "paths" in data:
            QMessageBox.critical(parent, "Error", "Please select a valid path.")
            return
        
        path_data = data["paths"].get(path_key, {})
        if "scenarios" not in path_data:
            QMessageBox.critical(parent, "Error", "No scenarios found for this path.")
            return
        
        # Find scenario key
        scenario_key = None
        for key, entry in path_data["scenarios"].items():
            if entry.get("name") == scenario_name:
                scenario_key = key
                break
        
        if not scenario_key:
            QMessageBox.critical(parent, "Error", "Could not find scenario in data.")
            return
        
        reply = QMessageBox.question(
            parent, 
            "Confirm Deletion", 
            f"Are you sure you want to delete scenario '{scenario_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        # Delete scenario
        del path_data["scenarios"][scenario_key]
        
        # Save to file
        save_callback("StartingScenarios")
        
        # Update scenarios list
        update_scenario_list()
        
        # Clear form
        name_edit.clear()
        location_edit.clear()
        district_edit.clear()
        time_edit.clear()
        intro_edit.clear()
        goals_edit.clear()
        equipment_list.clear()
        
        QMessageBox.information(parent, "Success", f"Scenario '{scenario_name}' deleted successfully.")
    
    # Add buttons
    button_layout = QHBoxLayout()
    btn_add = QPushButton("Add Scenario")
    btn_update = QPushButton("Update")
    btn_delete = QPushButton("Delete")
    
    button_layout.addWidget(btn_add)
    button_layout.addWidget(btn_update)
    button_layout.addWidget(btn_delete)
    
    editor_layout.addLayout(button_layout)

    # Add in the button_layout:
    btn_debug = QPushButton("Show Raw Data")
    button_layout.addWidget(btn_debug)

    # And add the function:
    def show_raw_data():
        """Show raw JSON data for the selected scenario"""
        if not scenario_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a scenario first.")
            return
            
        scenario_name = scenario_list.currentItem().text()
        path_key = path_combo.currentData()
        
        if path_key and "paths" in data:
            path_data = data["paths"].get(path_key, {})
            if "scenarios" in path_data:
                # Find scenario by name
                for key, entry in path_data["scenarios"].items():
                    if entry.get("name") == scenario_name:
                        # Create a dialog to show the JSON
                        dialog = QDialog(parent)
                        dialog.setWindowTitle(f"Raw Data: {scenario_name}")
                        dialog.resize(600, 400)
                        
                        layout = QVBoxLayout(dialog)
                        
                        # Text area for the JSON
                        text_edit = QPlainTextEdit()
                        text_edit.setReadOnly(False)  # Make it editable for easy copying
                        text_edit.setPlainText(json.dumps(entry, indent=2))
                        layout.addWidget(text_edit)
                        
                        # Close button
                        close_btn = QPushButton("Close")
                        close_btn.clicked.connect(dialog.accept)
                        layout.addWidget(close_btn)
                        
                        dialog.exec_()
                        return
        
        QMessageBox.warning(parent, "Not Found", "Could not find scenario data.")

    # Connect the button
    btn_debug.clicked.connect(show_raw_data)
    
    # Connect signals
    path_combo.currentIndexChanged.connect(update_scenario_list)
    scenario_list.itemClicked.connect(load_scenario_details)
    
    btn_add.clicked.connect(add_scenario)
    btn_update.clicked.connect(update_scenario)
    btn_delete.clicked.connect(delete_scenario)
    
    # Initial update of scenario list
    update_scenario_list()
    
    # Add panels to split layout
    split_layout.addLayout(selection_layout, 1)
    split_layout.addLayout(editor_layout, 2)
    
    layout.addLayout(split_layout)
    return scenarios_tab