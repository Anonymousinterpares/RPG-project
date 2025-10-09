# gui/advanced_config_editor/form_views/world_settings_form.py
"""
Form view for world settings configuration.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QPushButton, QSpinBox, QTabWidget,
    QPlainTextEdit, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt
from ..custom_widgets import AutoResizingPlainTextEdit

def create_world_settings_form_tab(parent, data, save_callback):
    """
    Create and populate the World Settings tab in form view.
    
    Args:
        parent: Parent widget
        data (dict): The world settings data
        save_callback (callable): Function to call when saving data
        
    Returns:
        QWidget: The world settings tab widget
    """
    world_tab = QWidget()
    layout = QVBoxLayout(world_tab)
    
    # Add title and description
    layout.addWidget(QLabel("<h2>World Settings</h2>"))
    layout.addWidget(QLabel("Configure fundamental world rules, history, and cultures"))
    
    # Create tabs for different world settings
    world_subtabs = QTabWidget()
    
    # History tab with normalized view
    history_tab = QWidget()
    history_layout = QVBoxLayout(history_tab)
    
    # Current Era section
    history_layout.addWidget(QLabel("<h3>Current Era</h3>"))
    
    era_form = QFormLayout()
    era_name = QLineEdit()
    era_year = QSpinBox()
    era_year.setRange(1, 10000)
    era_desc = QPlainTextEdit()
    era_desc.setMaximumHeight(100)
    
    era_form.addRow("Era Name:", era_name)
    era_form.addRow("Year:", era_year)
    era_form.addRow("Description:", era_desc)
    
    history_layout.addLayout(era_form)
    
    # Key Events section
    history_layout.addWidget(QLabel("<h3>Key Events</h3>"))
    
    events_list = QListWidget()
    events_list.setMaximumHeight(120)
    
    events_buttons = QHBoxLayout()
    add_event_btn = QPushButton("Add Event")
    edit_event_btn = QPushButton("Edit")
    remove_event_btn = QPushButton("Remove")
    
    events_buttons.addWidget(add_event_btn)
    events_buttons.addWidget(edit_event_btn)
    events_buttons.addWidget(remove_event_btn)
    
    history_layout.addWidget(events_list)
    history_layout.addLayout(events_buttons)
    
    # Event details form (shown when editing)
    event_details = QWidget()
    event_form = QFormLayout(event_details)
    
    event_name = QLineEdit()
    event_desc = QPlainTextEdit()
    event_desc.setMaximumHeight(80)
    event_impact = QPlainTextEdit()
    event_impact.setMaximumHeight(80)
    
    event_form.addRow("Event Name:", event_name)
    event_form.addRow("Description:", event_desc)
    event_form.addRow("Impact:", event_impact)
    
    event_actions = QHBoxLayout()
    save_event_btn = QPushButton("Save Event")
    cancel_event_btn = QPushButton("Cancel")
    
    event_actions.addWidget(save_event_btn)
    event_actions.addWidget(cancel_event_btn)
    
    event_form.addRow("", event_actions)
    
    # Initially hide event details
    event_details.setVisible(False)
    history_layout.addWidget(event_details)
    
    # Current World State section
    world_state_label = QLabel("<h3>Current World State</h3>")
    history_layout.addWidget(world_state_label)
    
    # Major Powers section
    history_layout.addWidget(QLabel("<b>Major Powers</b>"))
    
    powers_list = QListWidget()
    powers_list.setMaximumHeight(100)
    
    powers_buttons = QHBoxLayout()
    add_power_btn = QPushButton("Add Power")
    edit_power_btn = QPushButton("Edit")
    remove_power_btn = QPushButton("Remove")
    
    powers_buttons.addWidget(add_power_btn)
    powers_buttons.addWidget(edit_power_btn)
    powers_buttons.addWidget(remove_power_btn)
    
    history_layout.addWidget(powers_list)
    history_layout.addLayout(powers_buttons)
    
    # Conflicts section
    history_layout.addWidget(QLabel("<b>Current Conflicts</b>"))
    
    conflicts_list = QListWidget()
    conflicts_list.setMaximumHeight(100)
    
    conflicts_buttons = QHBoxLayout()
    add_conflict_btn = QPushButton("Add Conflict")
    edit_conflict_btn = QPushButton("Edit")
    remove_conflict_btn = QPushButton("Remove")
    
    conflicts_buttons.addWidget(add_conflict_btn)
    conflicts_buttons.addWidget(edit_conflict_btn)
    conflicts_buttons.addWidget(remove_conflict_btn)
    
    history_layout.addWidget(conflicts_list)
    history_layout.addLayout(conflicts_buttons)
    
    # Social Dynamics section
    history_layout.addWidget(QLabel("<b>Social Dynamics</b>"))
    
    social_form = QFormLayout()
    magic_acceptance = QLineEdit()
    class_structure = QLineEdit()
    tech_level = QLineEdit()
    
    social_form.addRow("Magic Acceptance:", magic_acceptance)
    social_form.addRow("Class Structure:", class_structure)
    social_form.addRow("Tech Level:", tech_level)
    
    history_layout.addLayout(social_form)
    
    # Magic System tab with normalized view
    rules_tab = QWidget()
    rules_layout = QVBoxLayout(rules_tab)
    
    # Magic Principles section
    rules_layout.addWidget(QLabel("<h3>Magic System</h3>"))
    
    # Energy Types
    rules_layout.addWidget(QLabel("<b>Energy Types</b>"))
    
    energy_list = QListWidget()
    energy_list.setMaximumHeight(80)
    
    energy_buttons = QHBoxLayout()
    add_energy_btn = QPushButton("Add Type")
    edit_energy_btn = QPushButton("Edit")
    remove_energy_btn = QPushButton("Remove")
    
    energy_buttons.addWidget(add_energy_btn)
    energy_buttons.addWidget(edit_energy_btn)
    energy_buttons.addWidget(remove_energy_btn)
    
    rules_layout.addWidget(energy_list)
    rules_layout.addLayout(energy_buttons)
    
    # Casting Requirements
    rules_layout.addWidget(QLabel("<b>Casting Requirements</b>"))
    
    casting_form = QFormLayout()
    focus_req = QLineEdit()
    energy_req = QLineEdit()
    knowledge_req = QLineEdit()
    
    casting_form.addRow("Focus:", focus_req)
    casting_form.addRow("Energy:", energy_req)
    casting_form.addRow("Knowledge:", knowledge_req)
    
    rules_layout.addLayout(casting_form)
    
    # Limitations
    rules_layout.addWidget(QLabel("<b>Limitations</b>"))
    
    limitations_form = QFormLayout()
    energy_depletion = QLineEdit()
    concentration = QLineEdit()
    environmental = QLineEdit()
    
    limitations_form.addRow("Energy Depletion:", energy_depletion)
    limitations_form.addRow("Concentration:", concentration)
    limitations_form.addRow("Environmental Factors:", environmental)
    
    rules_layout.addLayout(limitations_form)
    
    # World Mechanics
    rules_layout.addWidget(QLabel("<h3>World Mechanics</h3>"))
    
    # Time settings
    rules_layout.addWidget(QLabel("<b>Time</b>"))
    
    time_form = QFormLayout()
    day_cycle = QSpinBox()
    day_cycle.setRange(1, 100)
    month_length = QSpinBox()
    month_length.setRange(1, 100)
    year_length = QSpinBox()
    year_length.setRange(1, 1000)
    current_year = QSpinBox()
    current_year.setRange(1, 10000)
    
    time_form.addRow("Day Cycle (hours):", day_cycle)
    time_form.addRow("Month Length (days):", month_length)
    time_form.addRow("Year Length (days):", year_length)
    time_form.addRow("Current Year:", current_year)
    
    rules_layout.addLayout(time_form)
    
    # Load data into form fields
    if "eras" in data["WorldHistory"] and len(data["WorldHistory"]["eras"]) > 0:
        current_era_data = data["WorldHistory"]["eras"][-1]
        era_name.setText(current_era_data.get("name", ""))
        era_year.setValue(current_era_data.get("year", 1))
        era_desc.setPlainText(current_era_data.get("description", ""))
        
        # Populate key events
        for event in current_era_data.get("key_events", []):
            events_list.addItem(event.get("name", "Unnamed Event"))
    
    # Populate world state data
    if "current_state" in data["WorldHistory"]:
        state_data = data["WorldHistory"]["current_state"]
        
        # Populate major powers
        for power in state_data.get("major_powers", []):
            powers_list.addItem(power.get("name", "Unnamed Power"))
        
        # Populate conflicts
        for conflict in state_data.get("current_conflicts", []):
            conflicts_list.addItem(conflict.get("name", "Unnamed Conflict"))
        
        # Populate social dynamics
        social_dynamics = state_data.get("social_dynamics", {})
        magic_acceptance.setText(social_dynamics.get("magic_acceptance", ""))
        class_structure.setText(social_dynamics.get("class_structure", ""))
        tech_level.setText(social_dynamics.get("technological_level", ""))
    
    # Populate magic system data
    if "magic_system" in data["FundamentalRules"]:
        magic_data = data["FundamentalRules"]["magic_system"]
        
        # Populate energy types
        for energy in magic_data.get("core_principles", {}).get("energy_types", []):
            energy_list.addItem(energy.get("name", "Unnamed Energy"))
        
        # Populate casting requirements
        casting_reqs = magic_data.get("core_principles", {}).get("casting_requirements", {})
        focus_req.setText(casting_reqs.get("focus", ""))
        energy_req.setText(casting_reqs.get("energy", ""))
        knowledge_req.setText(casting_reqs.get("knowledge", ""))
        
        # Populate limitations
        limitations = magic_data.get("limitations", {})
        energy_depletion.setText(limitations.get("energy_depletion", ""))
        concentration.setText(limitations.get("concentration", ""))
        environmental.setText(limitations.get("environmental_factors", ""))
    
    # Populate world mechanics data
    if "world_mechanics" in data["FundamentalRules"]:
        mechanics = data["FundamentalRules"]["world_mechanics"]
        
        # Populate time settings
        time_settings = mechanics.get("time", {})
        day_cycle.setValue(time_settings.get("day_cycle", 24))
        month_length.setValue(time_settings.get("month_length", 30))
        year_length.setValue(time_settings.get("year_length", 360))
        current_year.setValue(time_settings.get("current_year", 2442))
    
    # Cultures tab
    cultures_tab = QWidget()
    cultures_layout = QVBoxLayout(cultures_tab)
    
    # Create better cultures view
    cultures_layout.addWidget(QLabel("<h3>Cultures</h3>"))
    
    # Split layout: cultures list on left, details on right
    cultures_split = QHBoxLayout()
    
    # Cultures list
    cultures_list = QListWidget()
    for key, culture in data["Cultures"].items():
        if isinstance(culture, dict) and "name" in culture:
            cultures_list.addItem(culture["name"])
        else:
            cultures_list.addItem(key.replace("_", " ").title())
    
    # Culture details form
    culture_details = QWidget()
    culture_form = QFormLayout(culture_details)
    
    culture_name = QLineEdit()
    culture_desc = QPlainTextEdit()
    culture_desc.setMaximumHeight(80)
    
    culture_form.addRow("Culture Name:", culture_name)
    culture_form.addRow("Description:", culture_desc)
    
    # Values section
    culture_form.addRow(QLabel("<b>Values</b>"), QWidget())
    culture_values = QListWidget()
    culture_values.setMaximumHeight(80)
    
    values_buttons = QHBoxLayout()
    add_value_btn = QPushButton("Add")
    remove_value_btn = QPushButton("Remove")
    
    values_buttons.addWidget(add_value_btn)
    values_buttons.addWidget(remove_value_btn)
    
    culture_form.addRow("", culture_values)
    culture_form.addRow("", values_buttons)
    
    # Traditions section
    culture_form.addRow(QLabel("<b>Traditions</b>"), QWidget())
    
    traditions_form = QFormLayout()
    initiation = QLineEdit()
    advancement = QLineEdit()
    research = QLineEdit()
    
    traditions_form.addRow("Initiation Ceremony:", initiation)
    traditions_form.addRow("Advancement Trials:", advancement)
    traditions_form.addRow("Research Presentations:", research)
    
    culture_form.addRow("", QWidget())  # Spacer
    for row_idx in range(traditions_form.rowCount()):
        label_item = traditions_form.itemAt(row_idx, QFormLayout.LabelRole)
        field_item = traditions_form.itemAt(row_idx, QFormLayout.FieldRole)
        if label_item and field_item:
            culture_form.addRow(label_item.widget(), field_item.widget())
    
    # Add culture buttons
    culture_buttons = QHBoxLayout()
    add_culture_btn = QPushButton("Add Culture")
    edit_culture_btn = QPushButton("Update")
    remove_culture_btn = QPushButton("Remove")
    
    culture_buttons.addWidget(add_culture_btn)
    culture_buttons.addWidget(edit_culture_btn)
    culture_buttons.addWidget(remove_culture_btn)
    
    # Connect culture selection
    def on_culture_selected():
        if not cultures_list.currentItem():
            return
            
        culture_name_text = cultures_list.currentItem().text()
        culture_data = None
        
        # Find selected culture data
        for key, entry in data["Cultures"].items():
            if isinstance(entry, dict) and entry.get("name") == culture_name_text:
                culture_data = entry
                break
            elif key.replace("_", " ").title() == culture_name_text:
                culture_data = entry
                break
        
        if not culture_data:
            return
            
        # Fill in the form
        culture_name.setText(culture_data.get("name", ""))
        culture_desc.setPlainText(culture_data.get("description", ""))
        
        # Fill values
        culture_values.clear()
        for value in culture_data.get("values", []):
            culture_values.addItem(value)
        
        # Fill traditions
        traditions = culture_data.get("traditions", {})
        initiation.setText(traditions.get("initiation_ceremony", ""))
        advancement.setText(traditions.get("advancement_trials", ""))
        research.setText(traditions.get("research_presentations", ""))
    
    cultures_list.itemClicked.connect(on_culture_selected)
    
    # Add value to culture
    def add_value():
        value, ok = QInputDialog.getText(parent, "Add Value", "Enter cultural value:")
        if ok and value.strip():
            culture_values.addItem(value.strip())
    
    # Remove value from culture
    def remove_value():
        selected = culture_values.currentItem()
        if selected:
            row = culture_values.row(selected)
            culture_values.takeItem(row)
    
    # Add culture
    def add_culture():
        name = culture_name.text().strip()
        if not name:
            QMessageBox.critical(parent, "Error", "Culture name is required.")
            return
        
        # Create key from name
        key = name.lower().replace(" ", "_")
        
        # Check if culture exists
        if key in data["Cultures"]:
            reply = QMessageBox.question(
                parent, 
                "Culture Exists", 
                f"A culture with key '{key}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Create values list
        values = []
        for i in range(culture_values.count()):
            values.append(culture_values.item(i).text())
        
        # Create traditions dict
        traditions = {
            "initiation_ceremony": initiation.text().strip(),
            "advancement_trials": advancement.text().strip(),
            "research_presentations": research.text().strip()
        }
        
        # Create culture data
        culture_data = {
            "name": name,
            "description": culture_desc.toPlainText().strip(),
            "values": values,
            "traditions": traditions
        }
        
        # Add culture
        data["Cultures"][key] = culture_data
        
        # Save to file
        save_callback("Cultures")
        
        # Update list
        cultures_list.clear()
        for key, culture in data["Cultures"].items():
            if isinstance(culture, dict) and "name" in culture:
                cultures_list.addItem(culture["name"])
            else:
                cultures_list.addItem(key.replace("_", " ").title())
        
        QMessageBox.information(parent, "Success", f"Culture '{name}' added successfully.")
    
    # Update culture
    def update_culture():
        if not cultures_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a culture to update.")
            return
        
        culture_name_text = cultures_list.currentItem().text()
        culture_key = None
        
        # Find culture key
        for key, entry in data["Cultures"].items():
            if isinstance(entry, dict) and entry.get("name") == culture_name_text:
                culture_key = key
                break
            elif key.replace("_", " ").title() == culture_name_text:
                culture_key = key
                break
        
        if not culture_key:
            QMessageBox.critical(parent, "Error", "Could not find culture in data.")
            return
        
        # Create values list
        values = []
        for i in range(culture_values.count()):
            values.append(culture_values.item(i).text())
        
        # Create traditions dict
        traditions = {
            "initiation_ceremony": initiation.text().strip(),
            "advancement_trials": advancement.text().strip(),
            "research_presentations": research.text().strip()
        }
        
        # Create updated culture data
        culture_data = {
            "name": culture_name.text().strip(),
            "description": culture_desc.toPlainText().strip(),
            "values": values,
            "traditions": traditions
        }
        
        # Update culture
        data["Cultures"][culture_key] = culture_data
        
        # Save to file
        save_callback("Cultures")
        
        # Update list
        cultures_list.clear()
        for key, culture in data["Cultures"].items():
            if isinstance(culture, dict) and "name" in culture:
                cultures_list.addItem(culture["name"])
            else:
                cultures_list.addItem(key.replace("_", " ").title())
        
        QMessageBox.information(parent, "Success", f"Culture '{culture_data['name']}' updated successfully.")
    
    # Remove culture
    def remove_culture():
        if not cultures_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a culture to remove.")
            return
        
        culture_name_text = cultures_list.currentItem().text()
        culture_key = None
        
        # Find culture key
        for key, entry in data["Cultures"].items():
            if isinstance(entry, dict) and entry.get("name") == culture_name_text:
                culture_key = key
                break
            elif key.replace("_", " ").title() == culture_name_text:
                culture_key = key
                break
        
        if not culture_key:
            QMessageBox.critical(parent, "Error", "Could not find culture in data.")
            return
        
        reply = QMessageBox.question(
            parent, 
            "Confirm Removal", 
            f"Are you sure you want to remove culture '{culture_name_text}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        # Remove culture
        del data["Cultures"][culture_key]
        
        # Save to file
        save_callback("Cultures")
        
        # Update list
        cultures_list.clear()
        for key, culture in data["Cultures"].items():
            if isinstance(culture, dict) and "name" in culture:
                cultures_list.addItem(culture["name"])
            else:
                cultures_list.addItem(key.replace("_", " ").title())
        
        # Clear form
        culture_name.clear()
        culture_desc.clear()
        culture_values.clear()
        initiation.clear()
        advancement.clear()
        research.clear()
        
        QMessageBox.information(parent, "Success", f"Culture '{culture_name_text}' removed successfully.")
    
    # Connect culture buttons
    add_value_btn.clicked.connect(add_value)
    remove_value_btn.clicked.connect(remove_value)
    
    add_culture_btn.clicked.connect(add_culture)
    edit_culture_btn.clicked.connect(update_culture)
    remove_culture_btn.clicked.connect(remove_culture)
    
    # Add to split layout
    cultures_split.addWidget(cultures_list, 1)
    cultures_split.addWidget(culture_details, 2)
    
    cultures_layout.addLayout(cultures_split)
    cultures_layout.addLayout(culture_buttons)
    
    # Add tabs to world_subtabs
    world_subtabs.addTab(history_tab, "History")
    world_subtabs.addTab(rules_tab, "Rules")
    world_subtabs.addTab(cultures_tab, "Cultures")
    
    # Add save button for all settings
    save_btn = QPushButton("Save All World Settings")
    save_btn.setMinimumHeight(40)
    save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
    
    # Connect save button
    def save_world_settings():
        try:
            # Save history data
            if "eras" in data["WorldHistory"] and len(data["WorldHistory"]["eras"]) > 0:
                current_era = data["WorldHistory"]["eras"][-1]
                current_era["name"] = era_name.text().strip()
                current_era["year"] = era_year.value()
                current_era["description"] = era_desc.toPlainText().strip()
            
            # Save world mechanics
            if "world_mechanics" not in data["FundamentalRules"]:
                data["FundamentalRules"]["world_mechanics"] = {}
            
            if "time" not in data["FundamentalRules"]["world_mechanics"]:
                data["FundamentalRules"]["world_mechanics"]["time"] = {}
            
            data["FundamentalRules"]["world_mechanics"]["time"]["day_cycle"] = day_cycle.value()
            data["FundamentalRules"]["world_mechanics"]["time"]["month_length"] = month_length.value()
            data["FundamentalRules"]["world_mechanics"]["time"]["year_length"] = year_length.value()
            data["FundamentalRules"]["world_mechanics"]["time"]["current_year"] = current_year.value()
            
            # Save to file
            save_callback("WorldHistory")
            save_callback("FundamentalRules")
            
            QMessageBox.information(parent, "Success", "World settings saved successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to save world settings: {str(e)}")
    
    save_btn.clicked.connect(save_world_settings)
    
    layout.addWidget(world_subtabs)
    layout.addWidget(save_btn)
    
    return world_tab