# gui/advanced_config_editor/form_views/races_form.py
"""
Form view for races configuration.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QListWidget, QPushButton, QSpinBox,
    QMessageBox
)
from PySide6.QtCore import Qt

def create_races_form_tab(parent, data, save_callback):
    """
    Create and populate the Races tab in form view.
    
    Args:
        parent: Parent widget
        data (dict): The races data
        save_callback (callable): Function to call when saving data
        
    Returns:
        QWidget: The races tab widget
    """
    races_tab = QWidget()
    layout = QVBoxLayout(races_tab)
    
    # Add title and description
    layout.addWidget(QLabel("<h2>Races</h2>"))
    layout.addWidget(QLabel("Configure playable races in your game world"))
    
    # Create list widget to show available races
    races_list = QListWidget()
    for key, race in data.items():
        races_list.addItem(race.get("name", key))
    
    # Add form controls for editing selected race
    form_layout = QFormLayout()
    
    name_edit = QLineEdit()
    desc_edit = parent.custom_widgets.AutoResizingPlainTextEdit()
    desc_edit.setMaximumHeight(100)
    
    form_layout.addRow("Race Name:", name_edit)
    form_layout.addRow("Description:", desc_edit)
    
    # Add stats layout for race modifiers
    stats_layout = QGridLayout()
    stat_fields = {}
    for i, stat in enumerate(["STR", "AGI", "CON", "INT", "WIS", "CHA"]):
        row, col = i // 3, i % 3
        stats_layout.addWidget(QLabel(f"{stat}:"), row, col*2)
        
        stat_spin = QSpinBox()
        stat_spin.setRange(-5, 5)
        stat_spin.setValue(0)
        stats_layout.addWidget(stat_spin, row, col*2+1)
        stat_fields[stat] = stat_spin
    
    # Add buttons
    button_layout = QHBoxLayout()
    btn_add = QPushButton("Add Race")
    btn_update = QPushButton("Update")
    btn_delete = QPushButton("Delete")
    
    button_layout.addWidget(btn_add)
    button_layout.addWidget(btn_update)
    button_layout.addWidget(btn_delete)
    
    # Connect functions for races list
    def on_race_selected():
        if not races_list.currentItem():
            return
            
        race_name = races_list.currentItem().text()
        race_data = None
        
        # Find race by name
        for key, race_entry in data.items():
            if race_entry.get("name") == race_name:
                race_data = race_entry
                break
                
        if race_data:
            name_edit.setText(race_data.get("name", ""))
            desc_edit.setPlainText(race_data.get("description", ""))
            
            # Set stat modifiers
            stats = race_data.get("stat_modifiers", {})
            for stat, spin in stat_fields.items():
                spin.setValue(stats.get(stat, 0))
    
    races_list.itemClicked.connect(on_race_selected)
    
    # Add handler for "Add Race" button
    def add_new_race():
        race_name = name_edit.text().strip()
        if not race_name:
            QMessageBox.warning(parent, "Missing Data", "Race name is required.")
            return
        
        # Create race key from name
        race_key = race_name.lower().replace(" ", "_")
        
        # Check if race already exists
        if race_key in data:
            reply = QMessageBox.question(
                parent, 
                "Race Exists", 
                f"A race with key '{race_key}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Create race data
        race_data = {
            "name": race_name,
            "description": desc_edit.toPlainText().strip(),
            "stat_modifiers": {stat: spin.value() for stat, spin in stat_fields.items() if spin.value() != 0}
        }
        
        # Add to data
        data[race_key] = race_data
        
        # Save to file
        save_callback("Races")
        
        # Update list
        races_list.clear()
        for key, race in data.items():
            races_list.addItem(race.get("name", key))
        
        QMessageBox.information(parent, "Success", f"Race '{race_name}' added successfully.")
    
    # Add handler for "Update" button
    def update_race():
        if not races_list.currentItem():
            QMessageBox.warning(parent, "No Selection", "Please select a race to update.")
            return
        
        race_name = races_list.currentItem().text()
        race_key = None
        
        # Find race key by name
        for key, race_entry in data.items():
            if race_entry.get("name") == race_name:
                race_key = key
                break
        
        if not race_key:
            QMessageBox.warning(parent, "Error", "Could not find race in data.")
            return
        
        # Update race data
        race_data = data[race_key]
        race_data["name"] = name_edit.text().strip()
        race_data["description"] = desc_edit.toPlainText().strip()
        race_data["stat_modifiers"] = {stat: spin.value() for stat, spin in stat_fields.items() if spin.value() != 0}
        
        # Save to file
        save_callback("Races")
        
        # Update list
        races_list.clear()
        for key, race in data.items():
            races_list.addItem(race.get("name", key))
        
        QMessageBox.information(parent, "Success", f"Race '{race_data['name']}' updated successfully.")
    
    # Add handler for "Delete" button
    def delete_race():
        if not races_list.currentItem():
            QMessageBox.warning(parent, "No Selection", "Please select a race to delete.")
            return
        
        race_name = races_list.currentItem().text()
        race_key = None
        
        # Find race key by name
        for key, race_entry in data.items():
            if race_entry.get("name") == race_name:
                race_key = key
                break
        
        if not race_key:
            QMessageBox.warning(parent, "Error", "Could not find race in data.")
            return
        
        reply = QMessageBox.question(
            parent, 
            "Confirm Deletion", 
            f"Are you sure you want to delete race '{race_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        # Delete race
        del data[race_key]
        
        # Save to file
        save_callback("Races")
        
        # Update list
        races_list.clear()
        for key, race in data.items():
            races_list.addItem(race.get("name", key))
        
        # Clear form
        name_edit.clear()
        desc_edit.clear()
        for spin in stat_fields.values():
            spin.setValue(0)
        
        QMessageBox.information(parent, "Success", f"Race '{race_name}' deleted successfully.")
    
    # Connect button handlers
    btn_add.clicked.connect(add_new_race)
    btn_update.clicked.connect(update_race)
    btn_delete.clicked.connect(delete_race)
    
    # Assemble the layout
    main_layout = QHBoxLayout()
    main_layout.addWidget(races_list, 1)
    
    form_widget = QWidget()
    form_layout_main = QVBoxLayout(form_widget)
    form_layout_main.addLayout(form_layout)
    
    stats_widget = QWidget()
    stats_widget.setLayout(stats_layout)
    form_layout_main.addWidget(stats_widget)
    form_layout_main.addLayout(button_layout)
    
    main_layout.addWidget(form_widget, 2)
    
    layout.addLayout(main_layout)
    return races_tab