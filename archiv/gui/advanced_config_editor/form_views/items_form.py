# gui/advanced_config_editor/form_views/items_form.py
"""
Form view for items configuration.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QListWidget, QPushButton, QSpinBox, QDoubleSpinBox,
    QMessageBox, QComboBox, QGroupBox
)
from PySide6.QtCore import Qt
import json
import os
from pathlib import Path

def create_items_form_tab(parent, save_callback):
    """
    Create and populate the Items tab in form view.
    
    Args:
        parent: Parent widget
        save_callback (callable): Function to call when saving data
        
    Returns:
        QWidget: The items tab widget
    """
    items_tab = QWidget()
    layout = QVBoxLayout(items_tab)
    
    # Add title and description
    layout.addWidget(QLabel("<h2>Item Management</h2>"))
    layout.addWidget(QLabel("Configure game items with their properties and stats"))
    
    # Split view: item list on left, details on right
    split_layout = QHBoxLayout()
    
    # Left: Item list with category filter
    left_panel = QWidget()
    left_layout = QVBoxLayout(left_panel)
    
    # Category filter
    filter_layout = QHBoxLayout()
    filter_layout.addWidget(QLabel("Filter by Type:"))
    type_filter = QComboBox()
    type_filter.addItem("All Items")
    for item_type in ["weapon", "armor", "accessory", "consumable", "quest", "miscellaneous"]:
        type_filter.addItem(item_type.capitalize())
    filter_layout.addWidget(type_filter)
    left_layout.addLayout(filter_layout)
    
    # Item list
    left_layout.addWidget(QLabel("Available Items:"))
    item_list = QListWidget()
    left_layout.addWidget(item_list)
    
    # Load items
    item_data = {}
    config_dir = "config"  # Default config directory
    try:
        items_path = Path(f"{config_dir}/items")
        if not items_path.exists():
            items_path.mkdir(parents=True, exist_ok=True)
            
        for file_path in items_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if "items" in data and isinstance(data["items"], list):
                    for item in data["items"]:
                        if "id" in item and "name" in item:
                            item_data[item["id"]] = item
                            item_list.addItem(item["name"])
            except Exception as e:
                parent.logger.error(f"Error loading items from {file_path}: {e}")
    except Exception as e:
        parent.logger.error(f"Error loading item files: {e}")
    
    # Right: Item details form
    right_panel = QWidget()
    right_layout = QVBoxLayout(right_panel)
    right_layout.addWidget(QLabel("Item Details:"))
    
    form_layout = QFormLayout()
    
    # Basic properties
    item_id = QLineEdit()
    item_name = QLineEdit()
    item_type = QComboBox()
    for item_type_name in ["weapon", "armor", "accessory", "consumable", "quest", "miscellaneous"]:
        item_type.addItem(item_type_name.capitalize())
        
    item_rarity = QComboBox()
    for rarity in ["common", "uncommon", "rare", "epic", "legendary", "mythic"]:
        item_rarity.addItem(rarity.capitalize())
    
    item_weight = QDoubleSpinBox()
    item_weight.setRange(0.0, 100.0)
    item_weight.setSingleStep(0.1)
    
    item_value = QSpinBox()
    item_value.setRange(0, 1000000)
    item_value.setSingleStep(10)
    
    item_description = parent.custom_widgets.AutoResizingPlainTextEdit(min_lines=2, max_lines=6)
    
    form_layout.addRow("Item ID:", item_id)
    form_layout.addRow("Name:", item_name)
    form_layout.addRow("Type:", item_type)
    form_layout.addRow("Rarity:", item_rarity)
    form_layout.addRow("Weight:", item_weight)
    form_layout.addRow("Value:", item_value)
    form_layout.addRow("Description:", item_description)
    
    # Equipment specific
    equipment_group = QGroupBox("Equipment Properties")
    equipment_layout = QFormLayout(equipment_group)
    
    equipment_slot = QComboBox()
    for slot in ["head", "neck", "shoulders", "chest", "back", "left_wrist", "right_wrist", "finger",
                "waist", "legs", "feet", "one_hand", "two_hand"]:
        equipment_slot.addItem(slot.replace("_", " ").title())
    
    durability = QSpinBox()
    durability.setRange(0, 1000)
    durability.setSingleStep(10)
    
    max_durability = QSpinBox()
    max_durability.setRange(0, 1000)
    max_durability.setSingleStep(10)
    
    equipment_layout.addRow("Equipment Slot:", equipment_slot)
    equipment_layout.addRow("Durability:", durability)
    equipment_layout.addRow("Max Durability:", max_durability)
    
    # Stats modifiers section
    stats_group = QGroupBox("Stat Modifiers")
    stats_layout = QGridLayout(stats_group)
    
    stat_fields = {}
    stat_names = ["STR", "AGI", "CON", "INT", "WIS", "CHA", 
                "Physical Defense", "Magic Defense", "Damage"]
    
    for i, stat in enumerate(stat_names):
        row, col = i // 3, i % 3
        stats_layout.addWidget(QLabel(f"{stat}:"), row, col*2)
        
        spin = QSpinBox()
        spin.setRange(-20, 20)
        spin.setValue(0)
        stats_layout.addWidget(spin, row, col*2+1)
        stat_fields[stat] = spin
    
    # Add form layouts
    right_layout.addLayout(form_layout)
    right_layout.addWidget(equipment_group)
    right_layout.addWidget(stats_group)
    
    # Add buttons
    button_layout = QHBoxLayout()
    btn_add = QPushButton("Add New Item")
    btn_update = QPushButton("Update Item")
    btn_delete = QPushButton("Delete Item")
    button_layout.addWidget(btn_add)
    button_layout.addWidget(btn_update)
    button_layout.addWidget(btn_delete)
    right_layout.addLayout(button_layout)
    
    # Connect signals
    def load_item_details():
        if not item_list.currentItem():
            return
            
        selected_name = item_list.currentItem().text()
        selected_item = None
        
        for item in item_data.values():
            if item.get("name") == selected_name:
                selected_item = item
                break
                
        if not selected_item:
            return
        
        # Load basic properties
        item_id.setText(selected_item.get("id", ""))
        item_name.setText(selected_item.get("name", ""))
        
        # Find index for item type
        type_index = item_type.findText(selected_item.get("item_type", "").capitalize())
        if type_index >= 0:
            item_type.setCurrentIndex(type_index)
            
        # Find index for rarity
        rarity_index = item_rarity.findText(selected_item.get("rarity", "").capitalize())
        if rarity_index >= 0:
            item_rarity.setCurrentIndex(rarity_index)
            
        item_weight.setValue(float(selected_item.get("weight", 0.0)))
        item_value.setValue(int(selected_item.get("value", 0)))
        item_description.setPlainText(selected_item.get("description", ""))
        
        # Equipment properties
        if selected_item.get("equipment_slot"):
            equipment_group.setVisible(True)
            slot_index = equipment_slot.findText(selected_item.get("equipment_slot", "").replace("_", " ").title())
            if slot_index >= 0:
                equipment_slot.setCurrentIndex(slot_index)
                
            durability.setValue(selected_item.get("durability", 0) or 0)
            max_durability.setValue(selected_item.get("max_durability", 0) or 0)
        else:
            equipment_group.setVisible(False)
            
        # Stats
        for stat_name, spin in stat_fields.items():
            spin.setValue(0)  # Reset first
            
        for stat in selected_item.get("stats", []):
            stat_name = stat.get("name")
            if stat_name in stat_fields:
                stat_fields[stat_name].setValue(int(stat.get("value", 0)))
    
    item_list.itemClicked.connect(load_item_details)
    
    # Filter by type function
    def filter_items_by_type():
        item_list.clear()
        filter_text = type_filter.currentText()
        
        for item in item_data.values():
            if filter_text == "All Items" or item.get("item_type", "").capitalize() == filter_text:
                item_list.addItem(item.get("name", "Unknown"))
    
    type_filter.currentIndexChanged.connect(filter_items_by_type)
    
    # Add item function
    def add_new_item():
        # Validate inputs
        if not item_id.text() or not item_name.text():
            QMessageBox.warning(parent, "Missing Data", "Item ID and Name are required.")
            return
            
        # Prepare item data
        item_type_value = item_type.currentText().lower()
        new_item = {
            "id": item_id.text(),
            "name": item_name.text(),
            "item_type": item_type_value,
            "rarity": item_rarity.currentText().lower(),
            "weight": item_weight.value(),
            "value": item_value.value(),
            "description": item_description.toPlainText(),
            "icon": f"images/items/{item_type_value}/{item_id.text()}.png",
            "stats": []
        }
        
        # Add equipment properties if visible
        if equipment_group.isVisible():
            new_item["equipment_slot"] = equipment_slot.currentText().lower().replace(" ", "_")
            new_item["durability"] = durability.value() if durability.value() > 0 else None
            new_item["max_durability"] = max_durability.value() if max_durability.value() > 0 else None
        
        # Add stats if not zero
        for stat_name, spin in stat_fields.items():
            if spin.value() != 0:
                new_item["stats"].append({
                    "name": stat_name,
                    "value": spin.value(),
                    "is_percentage": False  # Default to false
                })
        
        # Set known properties
        new_item["known_properties"] = {stat["name"]: True for stat in new_item["stats"]}
        
        # Set stackable to False by default
        new_item["stackable"] = False
        
        # Add to data
        item_data[new_item["id"]] = new_item
        
        # Save to file
        try:
            # Create item type directory if it doesn't exist
            items_base_path = Path("config/items")
            items_base_path.mkdir(parents=True, exist_ok=True)
            
            # Decide storage method based on item type
            save_individual = QMessageBox.question(
                parent, "Save Method", 
                "How would you like to save this item?\n\n"
                "Yes: Save as individual file (recommended for production)\n"
                "No: Add to categorized collection file",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes
            
            if save_individual:
                # Save as individual file
                item_filename = f"{new_item['id']}.json"
                item_filepath = items_base_path / item_filename
                
                with open(item_filepath, 'w', encoding='utf-8') as f:
                    json.dump(new_item, f, indent=2)
                
                parent.logger.info(f"Saved item '{new_item['name']}' to individual file: {item_filepath}")
            else:
                # Save to category file
                category_filename = f"{item_type_value}_items.json"
                category_filepath = items_base_path / category_filename
                
                if category_filepath.exists():
                    with open(category_filepath, 'r', encoding='utf-8') as f:
                        category_data = json.load(f)
                else:
                    category_data = {"items": []}
                
                # Check if item already exists in category file
                found = False
                for i, item in enumerate(category_data["items"]):
                    if item.get("id") == new_item["id"]:
                        category_data["items"][i] = new_item
                        found = True
                        break
                
                if not found:
                    category_data["items"].append(new_item)
                
                # Save back to category file
                with open(category_filepath, 'w', encoding='utf-8') as f:
                    json.dump(category_data, f, indent=2)
                
                parent.logger.info(f"Added item '{new_item['name']}' to category file: {category_filepath}")
            
            # Make sure the images directory exists
            item_image_dir = Path(f"images/items/{item_type_value}")
            item_image_dir.mkdir(parents=True, exist_ok=True)
            
            QMessageBox.information(parent, "Success", f"Item '{new_item['name']}' added successfully.")
            
            # Refresh list
            item_list.addItem(new_item["name"])
                
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to save item: {str(e)}")
    
    btn_add.clicked.connect(add_new_item)
    
    # Update item function
    def update_item():
        if not item_list.currentItem():
            QMessageBox.warning(parent, "No Selection", "Please select an item to update.")
            return
            
        selected_name = item_list.currentItem().text()
        selected_id = None
        
        for item_id, item in item_data.items():
            if item.get("name") == selected_name:
                selected_id = item_id
                break
                
        if not selected_id:
            return
            
        # Get the item ID from text field (fix for the AttributeError)
        new_item_id = item_id.text() if hasattr(item_id, 'text') else str(item_id)
            
        # Create updated item data
        updated_item = {
            "id": new_item_id,
            "name": item_name.text(),
            "item_type": item_type.currentText().lower(),
            "rarity": item_rarity.currentText().lower(),
            "weight": item_weight.value(),
            "value": item_value.value(),
            "description": item_description.toPlainText(),
            "icon": item_data[selected_id].get("icon", f"images/items/{item_type.currentText().lower()}/{new_item_id}.png"),
            "stats": []
        }
        
        # Add equipment properties if visible
        if equipment_group.isVisible():
            updated_item["equipment_slot"] = equipment_slot.currentText().lower().replace(" ", "_")
            updated_item["durability"] = durability.value() if durability.value() > 0 else None
            updated_item["max_durability"] = max_durability.value() if max_durability.value() > 0 else None
        
        # Add stats if not zero
        for stat_name, spin in stat_fields.items():
            if spin.value() != 0:
                updated_item["stats"].append({
                    "name": stat_name,
                    "value": spin.value(),
                    "is_percentage": False
                })
        
        # Preserve known properties if possible
        updated_item["known_properties"] = item_data[selected_id].get("known_properties", {})
        
        # Preserve stackable flag
        updated_item["stackable"] = item_data[selected_id].get("stackable", False)
        
        # Update data
        item_data[selected_id] = updated_item
        
        # Save to file
        try:
            # Create item type directory if it doesn't exist
            items_base_path = Path("config/items")
            items_base_path.mkdir(parents=True, exist_ok=True)
            item_type_value = updated_item["item_type"]
            
            # Check if the item exists in a collection file
            found_in_collection = False
            collection_file_path = None
            
            for file_path in Path(config_dir).glob("items/*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        
                    if "items" in file_data:
                        for i, item in enumerate(file_data["items"]):
                            if item.get("id") == selected_id:
                                # Found it in a collection file
                                found_in_collection = True
                                collection_file_path = file_path
                                break
                                
                    if found_in_collection:
                        break
                        
                except Exception as e:
                    parent.logger.error(f"Error checking item in {file_path}: {e}")
            
            # Check if the item exists as an individual file
            individual_file_path = items_base_path / f"{selected_id}.json"
            found_as_individual = individual_file_path.exists()
            
            save_method = None
            
            # If found in both places or not found anywhere, ask how to save
            if (found_in_collection and found_as_individual) or (not found_in_collection and not found_as_individual):
                save_individual = QMessageBox.question(
                    parent, "Save Method", 
                    "How would you like to save this updated item?\n\n"
                    "Yes: Save as individual file (recommended for production)\n"
                    "No: Add to categorized collection file",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes
                
                if save_individual:
                    save_method = "individual"
                else:
                    save_method = "collection"
            else:
                # Use the method where it was found
                save_method = "individual" if found_as_individual else "collection"
            
            # Save according to chosen method
            if save_method == "individual":
                # Save as individual file
                individual_file_path = items_base_path / f"{updated_item['id']}.json"
                with open(individual_file_path, 'w', encoding='utf-8') as f:
                    json.dump(updated_item, f, indent=2)
                
                # If it was previously in a collection, remove it
                if found_in_collection and collection_file_path:
                    with open(collection_file_path, 'r', encoding='utf-8') as f:
                        collection_data = json.load(f)
                    
                    for i, item in enumerate(collection_data["items"]):
                        if item.get("id") == selected_id:
                            collection_data["items"].pop(i)
                            break
                    
                    with open(collection_file_path, 'w', encoding='utf-8') as f:
                        json.dump(collection_data, f, indent=2)
                
                parent.logger.info(f"Updated item '{updated_item['name']}' as individual file: {individual_file_path}")
            else:
                # Save to category file
                category_filename = f"{item_type_value}_items.json"
                category_filepath = items_base_path / category_filename
                
                if category_filepath.exists():
                    with open(category_filepath, 'r', encoding='utf-8') as f:
                        category_data = json.load(f)
                else:
                    category_data = {"items": []}
                
                # Update or add to collection
                found = False
                for i, item in enumerate(category_data["items"]):
                    if item.get("id") == updated_item["id"]:
                        category_data["items"][i] = updated_item
                        found = True
                        break
                
                if not found:
                    category_data["items"].append(updated_item)
                
                # Save to category file
                with open(category_filepath, 'w', encoding='utf-8') as f:
                    json.dump(category_data, f, indent=2)
                
                # If it was previously an individual file, delete it
                if found_as_individual:
                    individual_file_path.unlink(missing_ok=True)
                
                parent.logger.info(f"Updated item '{updated_item['name']}' in category file: {category_filepath}")
            
            # Make sure the images directory exists
            item_image_dir = Path(f"images/items/{item_type_value}")
            item_image_dir.mkdir(parents=True, exist_ok=True)
                    
            QMessageBox.information(parent, "Success", f"Item '{updated_item['name']}' updated successfully.")
            
            # Refresh list
            filter_items_by_type()
                
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update item: {str(e)}")
    
    btn_update.clicked.connect(update_item)
    
    # Delete item function
    def delete_item():
        if not item_list.currentItem():
            QMessageBox.warning(parent, "No Selection", "Please select an item to delete.")
            return
            
        selected_name = item_list.currentItem().text()
        selected_id = None
        
        for item_id, item in item_data.items():
            if item.get("name") == selected_name:
                selected_id = item_id
                break
                
        if not selected_id:
            return
            
        reply = QMessageBox.question(
            parent, "Confirm Deletion", 
            f"Are you sure you want to delete item '{selected_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # Remove from data
        if selected_id in item_data:
            del item_data[selected_id]
            
        # Save to file
        try:
            # Find which file contains this item
            found = False
            for file_path in Path(config_dir).glob("items/*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        
                    if "items" in file_data:
                        for i, item in enumerate(file_data["items"]):
                            if item.get("id") == selected_id:
                                # Found it, remove
                                file_data["items"].pop(i)
                                found = True
                                break
                                
                    if found:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(file_data, f, indent=2)
                        break
                        
                except Exception as e:
                    parent.logger.error(f"Error deleting item in {file_path}: {e}")
                    
            if found:
                QMessageBox.information(parent, "Success", f"Item '{selected_name}' deleted successfully.")
            else:
                QMessageBox.warning(parent, "Not Found", f"Item '{selected_name}' not found in any config file.")
                
            # Refresh list
            filter_items_by_type()
                
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete item: {str(e)}")
    
    btn_delete.clicked.connect(delete_item)
    
    # Add loading event handler for equipment visibility
    def update_equipment_visibility():
        item_type_text = item_type.currentText().lower()
        equipment_group.setVisible(item_type_text in ["weapon", "armor", "accessory"])
    
    item_type.currentIndexChanged.connect(update_equipment_visibility)
    
    # Initial update
    update_equipment_visibility()
    
    # Add panels to split layout
    split_layout.addWidget(left_panel, 1)
    split_layout.addWidget(right_panel, 2)
    
    layout.addLayout(split_layout)
    return items_tab