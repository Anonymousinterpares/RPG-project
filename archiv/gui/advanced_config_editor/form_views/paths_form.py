# gui/advanced_config_editor/form_views/paths_form.py
"""
Form view for paths configuration.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QListWidget, QPushButton, QDialog,
    QMessageBox
)
from PySide6.QtCore import Qt
from ..custom_widgets import AutoResizingPlainTextEdit
from ..entry_editor import EntryEditorDialog
from ..schemas import PATH_SCHEMA, BACKGROUND_SCHEMA, validate_entry

def create_paths_form_tab(parent, paths_data, backgrounds_data, save_callback):
    """
    Create and populate the Paths tab in form view.
    
    Args:
        parent: Parent widget
        paths_data (dict): The paths data
        backgrounds_data (dict): The backgrounds data
        save_callback (callable): Function to call when saving data
        
    Returns:
        QWidget: The paths tab widget
    """
    paths_tab = QWidget()
    layout = QVBoxLayout(paths_tab)
    
    # Add title and description
    layout.addWidget(QLabel("<h2>Character Paths</h2>"))
    layout.addWidget(QLabel("Configure character paths and their associated backgrounds"))
    
    # Create list widget to show available paths
    paths_list = QListWidget()
    for key, path in paths_data.items():
        paths_list.addItem(path.get("name", key))
    
    # Add form controls for editing selected path
    form_layout = QFormLayout()
    
    name_edit = QLineEdit()
    desc_edit = AutoResizingPlainTextEdit(min_lines=2, max_lines=10)
    desc_edit.setMaximumHeight(100)
    bg_file_edit = QLineEdit()
    advantages_edit = AutoResizingPlainTextEdit(min_lines=2, max_lines=10)
    advantages_edit.setMaximumHeight(80)
    challenges_edit = AutoResizingPlainTextEdit(min_lines=2, max_lines=10)
    challenges_edit.setMaximumHeight(80)
    
    form_layout.addRow("Path Name:", name_edit)
    form_layout.addRow("Description:", desc_edit)
    form_layout.addRow("Background File:", bg_file_edit)
    form_layout.addRow("Starting Advantages:", advantages_edit)
    form_layout.addRow("Common Challenges:", challenges_edit)
    
    # Background list section
    bg_layout = QVBoxLayout()
    bg_label = QLabel("Backgrounds in this Path:")
    bg_list = QListWidget()
    bg_list.setMaximumHeight(150)
    
    bg_layout.addWidget(bg_label)
    bg_layout.addWidget(bg_list)
    
    # Add buttons
    button_layout = QHBoxLayout()
    btn_add = QPushButton("Add Path")
    btn_update = QPushButton("Update")
    btn_delete = QPushButton("Delete")
    
    btn_add_bg = QPushButton("Add Background")
    btn_edit_bg = QPushButton("Edit Background")
    
    button_layout.addWidget(btn_add)
    button_layout.addWidget(btn_update)
    button_layout.addWidget(btn_delete)
    
    bg_button_layout = QHBoxLayout()
    bg_button_layout.addWidget(btn_add_bg)
    bg_button_layout.addWidget(btn_edit_bg)
    
    # Connect functions for paths list
    def on_path_selected():
        if not paths_list.currentItem():
            return
            
        path_name = paths_list.currentItem().text()
        path_data = None
        path_key = None
        
        # Find path by name
        for key, data in paths_data.items():
            if data.get("name") == path_name:
                path_data = data
                path_key = key
                break
                
        if path_data:
            name_edit.setText(path_data.get("name", ""))
            desc_edit.setPlainText(path_data.get("description", ""))
            bg_file_edit.setText(path_data.get("backgrounds_file", ""))
            
            # Format advantages and challenges as newline-separated lists
            advantages = path_data.get("starting_advantages", [])
            if isinstance(advantages, list):
                advantages_edit.setPlainText("\n".join(advantages))
            else:
                advantages_edit.setPlainText(str(advantages))
                
            challenges = path_data.get("common_challenges", [])
            if isinstance(challenges, list):
                challenges_edit.setPlainText("\n".join(challenges))
            else:
                challenges_edit.setPlainText(str(challenges))
            
            # Populate backgrounds list
            bg_list.clear()
            backgrounds = path_data.get("backgrounds", {})
            for bg_key, bg_data in backgrounds.items():
                bg_list.addItem(bg_data.get("name", bg_key))
    
    def add_new_path():
        """Add a new path"""
        path_name = name_edit.text().strip()
        if not path_name:
            QMessageBox.critical(parent, "Error", "Path name is required.")
            return
        
        # Create path key from name
        path_key = path_name.lower().replace(" ", "_")
        
        # Check if path already exists
        if path_key in paths_data:
            reply = QMessageBox.question(
                parent, 
                "Path Exists", 
                f"A path with key '{path_key}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Process advantages and challenges
        advantages_text = advantages_edit.toPlainText().strip()
        challenges_text = challenges_edit.toPlainText().strip()
        
        advantages = [adv.strip() for adv in advantages_text.split('\n') if adv.strip()]
        challenges = [chl.strip() for chl in challenges_text.split('\n') if chl.strip()]
        
        # Create path data
        path_data = {
            "name": path_name,
            "description": desc_edit.toPlainText().strip(),
            "backgrounds_file": bg_file_edit.text().strip(),
            "starting_advantages": advantages,
            "common_challenges": challenges,
            "backgrounds": {} if path_key not in paths_data else paths_data[path_key].get("backgrounds", {})
        }
        
        # Validate entry
        valid, msg = validate_entry(path_data, PATH_SCHEMA)
        if not valid:
            QMessageBox.critical(parent, "Validation Error", msg)
            return
        
        # Add to data
        paths_data[path_key] = path_data
        
        # Save to file
        save_callback("Paths")
        
        # Update list
        paths_list.clear()
        for key, path in paths_data.items():
            paths_list.addItem(path.get("name", key))
        
        QMessageBox.information(parent, "Success", f"Path '{path_name}' added successfully.")
    
    def update_path():
        """Update the selected path"""
        if not paths_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a path to update.")
            return
        
        path_name = paths_list.currentItem().text()
        path_key = None
        
        # Find path key by name
        for key, data in paths_data.items():
            if data.get("name") == path_name:
                path_key = key
                break
        
        if not path_key:
            QMessageBox.critical(parent, "Error", "Could not find path in data.")
            return
        
        # Process advantages and challenges
        advantages_text = advantages_edit.toPlainText().strip()
        challenges_text = challenges_edit.toPlainText().strip()
        
        advantages = [adv.strip() for adv in advantages_text.split('\n') if adv.strip()]
        challenges = [chl.strip() for chl in challenges_text.split('\n') if chl.strip()]
        
        # Create updated path data
        path_data = paths_data[path_key]
        path_data["name"] = name_edit.text().strip()
        path_data["description"] = desc_edit.toPlainText().strip()
        path_data["backgrounds_file"] = bg_file_edit.text().strip()
        path_data["starting_advantages"] = advantages
        path_data["common_challenges"] = challenges
        
        # Validate entry
        valid, msg = validate_entry(path_data, PATH_SCHEMA)
        if not valid:
            QMessageBox.critical(parent, "Validation Error", msg)
            return
        
        # Save to file
        save_callback("Paths")
        
        # Update list
        paths_list.clear()
        for key, path in paths_data.items():
            paths_list.addItem(path.get("name", key))
        
        QMessageBox.information(parent, "Success", f"Path '{path_data['name']}' updated successfully.")
    
    def delete_path():
        """Delete the selected path"""
        if not paths_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a path to delete.")
            return
        
        path_name = paths_list.currentItem().text()
        path_key = None
        
        # Find path key by name
        for key, data in paths_data.items():
            if data.get("name") == path_name:
                path_key = key
                break
        
        if not path_key:
            QMessageBox.critical(parent, "Error", "Could not find path in data.")
            return
        
        reply = QMessageBox.question(
            parent, 
            "Confirm Deletion", 
            f"Are you sure you want to delete path '{path_name}'? This will also delete all associated backgrounds.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        # Delete path
        del paths_data[path_key]
        
        # Save to file
        save_callback("Paths")
        
        # Update list
        paths_list.clear()
        for key, path in paths_data.items():
            paths_list.addItem(path.get("name", key))
        
        # Clear form
        name_edit.clear()
        desc_edit.clear()
        bg_file_edit.clear()
        advantages_edit.clear()
        challenges_edit.clear()
        bg_list.clear()
        
        QMessageBox.information(parent, "Success", f"Path '{path_name}' deleted successfully.")
    
    def add_background():
        """Add a new background to the selected path"""
        if not paths_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a path first.")
            return
        
        path_name = paths_list.currentItem().text()
        path_key = None
        
        # Find path key by name
        for key, data in paths_data.items():
            if data.get("name") == path_name:
                path_key = key
                break
        
        if not path_key:
            QMessageBox.critical(parent, "Error", "Could not find path in data.")
            return
        
        # Open background editor dialog
        editor = EntryEditorDialog("Background", parent=parent)
        if editor.exec() == QDialog.Accepted:
            bg_data = editor.get_entry_data()
            
            # Validate background data
            valid, msg = validate_entry(bg_data, BACKGROUND_SCHEMA)
            if not valid:
                QMessageBox.critical(parent, "Validation Error", msg)
                return
            
            # Add path reference
            bg_data["path"] = path_key
            
            # Generate key from name
            bg_key = bg_data["name"].lower().replace(" ", "_")
            
            # Check if background already exists
            if "backgrounds" in paths_data[path_key] and bg_key in paths_data[path_key]["backgrounds"]:
                reply = QMessageBox.question(
                    parent, 
                    "Background Exists", 
                    f"A background with key '{bg_key}' already exists for this path. Overwrite?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            # Ensure backgrounds dict exists
            if "backgrounds" not in paths_data[path_key]:
                paths_data[path_key]["backgrounds"] = {}
            
            # Add background to path
            paths_data[path_key]["backgrounds"][bg_key] = bg_data
            
            # Also add to backgrounds data
            backgrounds_data[bg_key] = bg_data
            
            # Save to file
            save_callback("Paths")
            
            # Update backgrounds list
            bg_list.clear()
            for bg_key, bg_data in paths_data[path_key]["backgrounds"].items():
                bg_list.addItem(bg_data.get("name", bg_key))
            
            QMessageBox.information(parent, "Success", f"Background '{bg_data['name']}' added successfully.")
    
    def edit_background():
        """Edit the selected background"""
        if not paths_list.currentItem() or not bg_list.currentItem():
            QMessageBox.critical(parent, "Error", "Please select a path and background to edit.")
            return
        
        path_name = paths_list.currentItem().text()
        bg_name = bg_list.currentItem().text()
        
        path_key = None
        bg_key = None
        
        # Find path key
        for key, data in paths_data.items():
            if data.get("name") == path_name:
                path_key = key
                break
        
        if not path_key or "backgrounds" not in paths_data[path_key]:
            QMessageBox.critical(parent, "Error", "Could not find path or backgrounds in data.")
            return
        
        # Find background key
        for key, data in paths_data[path_key]["backgrounds"].items():
            if data.get("name") == bg_name:
                bg_key = key
                break
        
        if not bg_key:
            QMessageBox.critical(parent, "Error", "Could not find background in data.")
            return
        
        # Get background data
        bg_data = paths_data[path_key]["backgrounds"][bg_key]
        
        # Open background editor dialog
        editor = EntryEditorDialog("Background", bg_data, parent=parent)
        if editor.exec() == QDialog.Accepted:
            updated_data = editor.get_entry_data()
            
            # Validate background data
            valid, msg = validate_entry(updated_data, BACKGROUND_SCHEMA)
            if not valid:
                QMessageBox.critical(parent, "Validation Error", msg)
                return
            
            # Preserve path reference
            updated_data["path"] = path_key
            
            # Update background in path
            paths_data[path_key]["backgrounds"][bg_key] = updated_data
            
            # Also update in backgrounds data
            backgrounds_data[bg_key] = updated_data
            
            # Save to file
            save_callback("Paths")
            
            # Update backgrounds list
            bg_list.clear()
            for bg_key, bg_data in paths_data[path_key]["backgrounds"].items():
                bg_list.addItem(bg_data.get("name", bg_key))
            
            QMessageBox.information(parent, "Success", f"Background '{updated_data['name']}' updated successfully.")
    
    # Connect signals and handlers
    paths_list.itemClicked.connect(on_path_selected)
    
    btn_add.clicked.connect(add_new_path)
    btn_update.clicked.connect(update_path)
    btn_delete.clicked.connect(delete_path)
    
    btn_add_bg.clicked.connect(add_background)
    btn_edit_bg.clicked.connect(edit_background)
    
    # Assemble the layout
    main_layout = QHBoxLayout()
    main_layout.addWidget(paths_list, 1)
    
    form_widget = QWidget()
    form_layout_main = QVBoxLayout(form_widget)
    form_layout_main.addLayout(form_layout)
    form_layout_main.addLayout(bg_layout)
    form_layout_main.addLayout(bg_button_layout)
    form_layout_main.addLayout(button_layout)
    
    main_layout.addWidget(form_widget, 2)
    
    layout.addLayout(main_layout)
    return paths_tab