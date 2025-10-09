#path/gui/dialogs.py

from pathlib import Path
import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,QSpinBox,QSlider,QDoubleSpinBox,
    QPushButton, QTextEdit, QMessageBox, QComboBox, QPlainTextEdit, QWidget, QTabWidget, QCheckBox, QGroupBox
)
from PySide6.QtGui import QFont, QPixmap, Qt
import json
import os
import glob
from core.inventory.item_manager import InventoryManager
from core.utils.logging_config import LoggingConfig, LogCategory
from enum import Enum, auto
from gui.llm_settings_dialog import LLMSettingsDialog
from gui.advanced_config_editor import AdvancedConfigEditor

# Global settings for developer mode
ENABLE_DEV_SETTINGS = True
REQUIRE_DEV_CREDENTIALS = False

class DialogResult(Enum):
    CANCELLED = auto()
    GAME_LOADED = auto()
    GAME_SAVED = auto()

def open_settings_popup(parent, gm):
    popup = QDialog(parent)
    popup.setWindowTitle("Settings")
    popup.resize(300, 200)
    layout = QVBoxLayout(popup)
    
    btn_resolution = QPushButton("GUI Resolution", popup)
    btn_layout = QPushButton("Layout", popup)
    btn_game_settings = QPushButton("Game Settings", popup)
    btn_llm_settings = QPushButton("LLM Settings", popup)  # Add this new button
    
    layout.addWidget(btn_resolution)
    layout.addWidget(btn_layout)
    layout.addWidget(btn_game_settings)
    layout.addWidget(btn_llm_settings)  # Add this line
    
    if ENABLE_DEV_SETTINGS:
        btn_dev_settings = QPushButton("Developer Settings", popup)
        layout.addWidget(btn_dev_settings)
        btn_dev_settings.clicked.connect(lambda: open_developer_settings_popup(parent, gm))
    
    btn_resolution.clicked.connect(lambda: [popup.close(), open_resolution_settings_popup(parent, gm)])
    btn_layout.clicked.connect(lambda: [popup.close(), open_layout_settings_popup(parent, gm)])
    btn_game_settings.clicked.connect(lambda: [popup.close(), open_game_settings_popup(parent, gm)])
    btn_llm_settings.clicked.connect(lambda: [popup.close(), open_llm_settings_popup(parent, gm)])  # Add this line
    
    popup.exec()

def open_llm_settings_popup(parent, gm):
    """Open LLM settings configuration dialog"""
    
    dialog = LLMSettingsDialog(parent)
    result = dialog.exec()
    
    if result == QDialog.Accepted and hasattr(gm, 'llm_manager'):
        # Reload LLM configuration if settings were changed
        gm.llm_manager.reload_config()

def open_game_settings_popup(parent, gm):
    """Open enhanced game settings popup with various options"""
    popup = QDialog(parent)
    popup.setWindowTitle("Game Settings")
    popup.resize(500, 400)
    layout = QVBoxLayout(popup)
    
    # Create tabbed interface for settings
    settings_tabs = QTabWidget(popup)
    
    # ----- General Settings Tab -----
    general_tab = QWidget()
    general_layout = QVBoxLayout(general_tab)
    
    # Autosave settings
    autosave_group = QGroupBox("Autosave Settings", general_tab)
    autosave_layout = QVBoxLayout(autosave_group)
    
    # Autosave interval setting
    interval_layout = QHBoxLayout()
    interval_layout.addWidget(QLabel("Autosave Interval (seconds):"))
    interval_spinner = QSpinBox(autosave_group)
    interval_spinner.setRange(30, 3600)
    interval_spinner.setValue(gm.config.settings.get("save_interval", 300))
    interval_spinner.setSingleStep(30)
    interval_layout.addWidget(interval_spinner)
    autosave_layout.addLayout(interval_layout)
    
    # Autosave on exit
    autosave_exit_check = QCheckBox("Autosave on Exit", autosave_group)
    autosave_exit_check.setChecked(gm.config.settings.get("autosave_on_exit", True))
    autosave_layout.addWidget(autosave_exit_check)
    
    # Maximum autosaves to keep
    max_autosaves_layout = QHBoxLayout()
    max_autosaves_layout.addWidget(QLabel("Maximum Autosaves:"))
    max_autosaves_spinner = QSpinBox(autosave_group)
    max_autosaves_spinner.setRange(1, 100)
    max_autosaves_spinner.setValue(gm.config.settings.get("max_autosaves", 5))
    max_autosaves_layout.addWidget(max_autosaves_spinner)
    autosave_layout.addLayout(max_autosaves_layout)
    
    general_layout.addWidget(autosave_group)
    
    # Display settings
    display_group = QGroupBox("Display Settings", general_tab)
    display_layout = QVBoxLayout(display_group)
    
    # Debug mode toggle
    debug_check = QCheckBox("Debug Mode", display_group)
    debug_check.setChecked(gm.config.settings.get("debug_mode", False))
    display_layout.addWidget(debug_check)
    
    general_layout.addWidget(display_group)
    general_layout.addStretch()
    
    # ----- Audio Settings Tab -----
    audio_tab = QWidget()
    audio_layout = QVBoxLayout(audio_tab)
    
    # Music volume slider
    volume_layout = QHBoxLayout()
    volume_layout.addWidget(QLabel("Music Volume:"))
    volume_slider = QSlider(Qt.Horizontal, audio_tab)
    volume_slider.setRange(0, 100)
    volume_slider.setValue(gm.config.settings.get("music", {}).get("volume", 50))
    volume_layout.addWidget(volume_slider)
    volume_label = QLabel(f"{volume_slider.value()}%")
    volume_layout.addWidget(volume_label)
    
    # Update volume label when slider changes
    def update_volume_label():
        volume_label.setText(f"{volume_slider.value()}%")
    volume_slider.valueChanged.connect(update_volume_label)
    
    audio_layout.addLayout(volume_layout)
    
    # Crossfade duration
    crossfade_layout = QHBoxLayout()
    crossfade_layout.addWidget(QLabel("Crossfade Duration:"))
    crossfade_spinner = QDoubleSpinBox(audio_tab)
    crossfade_spinner.setRange(0.0, 10.0)
    crossfade_spinner.setValue(gm.config.settings.get("music", {}).get("crossfade_duration", 3.0))
    crossfade_spinner.setSingleStep(0.5)
    crossfade_spinner.setSuffix(" seconds")
    crossfade_layout.addWidget(crossfade_spinner)
    audio_layout.addLayout(crossfade_layout)
    
    audio_layout.addStretch()
    
    # Add tabs to tabbed interface
    settings_tabs.addTab(general_tab, "General")
    settings_tabs.addTab(audio_tab, "Audio")
    
    layout.addWidget(settings_tabs)
    
    # Buttons
    button_layout = QHBoxLayout()
    save_btn = QPushButton("Save Settings", popup)
    cancel_btn = QPushButton("Cancel", popup)
    reset_btn = QPushButton("Reset to Defaults", popup)
    
    button_layout.addWidget(reset_btn)
    button_layout.addStretch()
    button_layout.addWidget(save_btn)
    button_layout.addWidget(cancel_btn)
    
    layout.addLayout(button_layout)
    
    # Save settings to config
    def save_settings():
        try:
            # Update save interval
            gm.config.settings["save_interval"] = interval_spinner.value()
            
            # Update autosave on exit
            gm.config.settings["autosave_on_exit"] = autosave_exit_check.isChecked()
            
            # Update max autosaves
            gm.config.settings["max_autosaves"] = max_autosaves_spinner.value()
            
            # Update debug mode
            debug_changed = gm.config.settings.get("debug_mode", False) != debug_check.isChecked()
            gm.config.settings["debug_mode"] = debug_check.isChecked()
            
            # Update music settings
            if "music" not in gm.config.settings:
                gm.config.settings["music"] = {}
            gm.config.settings["music"]["volume"] = volume_slider.value()
            gm.config.settings["music"]["crossfade_duration"] = crossfade_spinner.value()
            
            # Apply debug mode change immediately if needed
            if debug_changed:
                from core.utils.logging_config import LoggingConfig
                LoggingConfig.update_logging_level(debug_check.isChecked())
            
            # Apply music volume change immediately if possible
            if hasattr(gm, 'llm_manager') and hasattr(gm.llm_manager, 'update_music_mood'):
                if hasattr(parent, 'music_manager'):
                    parent.music_manager.set_volume(volume_slider.value())
            
            # Save settings to file
            gm.config.save_settings()
            
            QMessageBox.information(popup, "Settings", "Settings saved successfully.")
            popup.accept()
            
        except Exception as e:
            QMessageBox.critical(popup, "Settings", f"Error saving settings: {str(e)}")
    
    def reset_to_defaults():
        # Confirm reset
        reply = QMessageBox.question(popup, "Reset Settings", 
                                   "Are you sure you want to reset all settings to defaults?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        # Default settings
        interval_spinner.setValue(300)
        autosave_exit_check.setChecked(True)
        max_autosaves_spinner.setValue(5)
        debug_check.setChecked(False)
        volume_slider.setValue(50)
        crossfade_spinner.setValue(3.0)
    
    save_btn.clicked.connect(save_settings)
    cancel_btn.clicked.connect(popup.reject)
    reset_btn.clicked.connect(reset_to_defaults)
    
    popup.exec()

def open_save_load_dialog(parent, gm, mode: str):
    """
    Opens an enhanced dialog for saving or loading games with memory display and multi-select capabilities.
    mode: 'save' or 'load'
    """
    popup = QDialog(parent)
    popup.setWindowTitle("Save Game" if mode == "save" else "Load Game")
    popup.resize(800, 600)  # Larger default size
    layout = QVBoxLayout(popup)
    
    # Filtering and Sorting controls
    filter_sort_layout = QHBoxLayout()
    filter_label = QLabel("Filter:")
    filter_edit = QLineEdit(popup)
    sort_label = QLabel("Sort by:")
    sort_combo = QComboBox(popup)
    sort_combo.addItems(["Date Desc", "Date Asc", "Name Asc", "Name Desc"])
    filter_sort_layout.addWidget(filter_label)
    filter_sort_layout.addWidget(filter_edit)
    filter_sort_layout.addStretch()
    filter_sort_layout.addWidget(sort_label)
    filter_sort_layout.addWidget(sort_combo)
    layout.addLayout(filter_sort_layout)
    
    # Multi-select checkbox
    multi_select_check = QCheckBox("Enable Multi-select", popup)
    filter_sort_layout.addWidget(multi_select_check)
    
    # Main content area - split view
    content_layout = QHBoxLayout()
    
    # List widget for saves (left side)
    save_list_layout = QVBoxLayout()
    save_list_layout.addWidget(QLabel("Available Saves:"))
    list_widget = QListWidget(popup)
    save_list_layout.addWidget(list_widget)
    
    # Details panel (right side)
    details_panel = QWidget(popup)
    details_layout = QVBoxLayout(details_panel)
    
    # Character image
    char_image_label = QLabel("Character Image", details_panel)
    char_image_label.setAlignment(Qt.AlignCenter)
    char_image_label.setMinimumHeight(150)
    char_image_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
    details_layout.addWidget(char_image_label)
    
    # Memory display area
    details_layout.addWidget(QLabel("Save Details:"))
    memory_display = QTextEdit(details_panel)
    memory_display.setReadOnly(True)
    memory_display.setMinimumHeight(200)
    details_layout.addWidget(memory_display)
    
    # Add to main content layout
    content_layout.addLayout(save_list_layout, 3)  # 3:2 ratio
    content_layout.addWidget(details_panel, 2)
    
    layout.addLayout(content_layout, 1)  # Add with stretch
    
    # For save mode, allow entering a new save name.
    if mode == "save":
        layout.addWidget(QLabel("Enter save name (or select one to overwrite):"))
        save_name_entry = QLineEdit(popup)
        layout.addWidget(save_name_entry)
    
    # Undo delete button (initially hidden)
    undo_delete_btn = QPushButton("Undo Last Delete", popup)
    undo_delete_btn.setVisible(False)
    layout.addWidget(undo_delete_btn)
    
    # Create button layout
    button_layout = QHBoxLayout()
    
    current_saves = []
    
    def update_multi_select_mode():
        """Update list widget selection mode based on checkbox"""
        if multi_select_check.isChecked():
            list_widget.setSelectionMode(QListWidget.MultiSelection)
            # Update button visibility
            if mode == "save":
                btn_save_new.setVisible(False)
                btn_overwrite.setVisible(False)
            else:
                btn_load.setVisible(False)
        else:
            list_widget.setSelectionMode(QListWidget.SingleSelection)
            # Restore buttons
            if mode == "save":
                btn_save_new.setVisible(True)
                btn_overwrite.setVisible(True)
            else:
                btn_load.setVisible(True)
    
    multi_select_check.stateChanged.connect(update_multi_select_mode)
    
    def refresh_list():
        """Refresh the list of saves, excluding those marked for deletion"""
        list_widget.clear()
        all_saves = gm.save_manager.list_saves() if (gm and hasattr(gm, 'save_manager')) else []
        
        # Filter out saves that are marked for deletion
        if hasattr(gm, 'deleted_saves') and gm.deleted_saves:
            # Get the filenames of deleted saves
            deleted_filenames = [info['filename'] for info in gm.deleted_saves]
            # Filter out saves with filenames in the deleted set
            all_saves = [save for save in all_saves if save['filename'] not in deleted_filenames]
        
        # Apply user filters
        filter_text = filter_edit.text().strip().lower()
        filtered = [s for s in all_saves if filter_text in s['save_name'].lower() or 
                filter_text in s['metadata']['player_name'].lower()]
        
        # Apply sorting
        sort_option = sort_combo.currentText()
        if sort_option == "Name Asc":
            filtered.sort(key=lambda x: x['save_name'].lower())
        elif sort_option == "Name Desc":
            filtered.sort(key=lambda x: x['save_name'].lower(), reverse=True)
        elif sort_option == "Date Asc":
            filtered.sort(key=lambda x: x['timestamp'])
        else:  # Date Desc - default
            filtered.sort(key=lambda x: x['timestamp'], reverse=True)
        
        nonlocal current_saves
        current_saves = filtered
        
        for save in filtered:
            timestamp = save['timestamp'].replace("T", " ")
            display_text = f"{save['save_name']} - {save['metadata']['player_name']} (Level {save['metadata']['level']}) - {timestamp}"
            list_widget.addItem(display_text)
    
    def update_memory_display():
        """Update the memory display with data from selected save"""
        logger = LoggingConfig.get_logger(__name__, LogCategory.SAVE)
        memory_display.clear()
        char_image_label.clear()
        char_image_label.setText("Character Image")
        
        selected_rows = [list_widget.row(item) for item in list_widget.selectedItems()]
        if not selected_rows:
            return
        
        # Use the first selection for display
        selected = selected_rows[0]
        if selected >= 0 and selected < len(current_saves):
            selected_save = current_saves[selected]
            
            # Try to load and display image for the character
            try:
                # Load save to check if character image path exists
                save_path = gm.save_manager.saves_dir / selected_save['filename']
                with open(save_path, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)
                
                # Check if character image path exists in save data
                image_path = save_data.get('player', {}).get('image_path')
                if image_path:
                    char_img_path = Path(gm.config.project_root) / 'images' / 'characters' / image_path
                    if char_img_path.exists():
                        pixmap = QPixmap(str(char_img_path))
                        if not pixmap.isNull():
                            char_image_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        else:
                            char_image_label.setText("Image Load Failed")
                else:
                    char_image_label.setText("No Character Image")
            except Exception as e:
                char_image_label.setText("No Character Image")
                logger.error(f"Error loading character image: {e}")
            
            # Display save information
            memory_details = f"<h3>Save Information</h3>"
            memory_details += f"<p><b>Player:</b> {selected_save['metadata']['player_name']}</p>"
            memory_details += f"<p><b>Level:</b> {selected_save['metadata']['level']}</p>"
            memory_details += f"<p><b>Location:</b> {selected_save['metadata']['location']}</p>"
            memory_details += f"<p><b>Last Saved:</b> {selected_save['timestamp']}</p>"
            
            # Display summary if available
            if 'preview' in selected_save:
                memory_details += f"<h3>Summary</h3><p>{selected_save['preview']}</p>"
            
            # Try to load memory information
            try:
                # We need session ID from the save file
                session_id = save_data.get('session_id')
                if session_id and hasattr(gm.state_manager, 'context_manager'):
                    # Get memory counts
                    memory_path = gm.state_manager.context_manager.memory_io.get_memory_filepath(
                        session_id, selected_save['save_name'].split('.')[0])
                    
                    if memory_path.exists():
                        with open(memory_path, 'r', encoding='utf-8') as f:
                            memory_data = json.load(f)
                        
                        memory_details += "<h3>Memory Information</h3>"
                        if 'memory_counts' in memory_data:
                            memory_details += "<p><b>Memory Entries:</b></p><ul>"
                            for type_name, count in memory_data['memory_counts'].items():
                                memory_details += f"<li>{type_name}: {count}</li>"
                            memory_details += "</ul>"
                        
                        # Show sample memories (first few from hot memory)
                        if 'memories_by_type' in memory_data and 'hot' in memory_data['memories_by_type']:
                            hot_memories = memory_data['memories_by_type']['hot']
                            if hot_memories:
                                memory_details += "<p><b>Recent Hot Memories:</b></p><ul>"
                                for i, memory in enumerate(hot_memories[:3]):  # First 3 hot memories
                                    content = memory.get('content', '')
                                    if len(content) > 100:
                                        content = content[:100] + "..."
                                    memory_details += f"<li>{content}</li>"
                                memory_details += "</ul>"
            except Exception as e:
                memory_details += f"<p>Error loading memory data: {str(e)}</p>"
                logger.error(f"Error loading memory data: {e}")
            
            memory_display.setHtml(memory_details)
    
    def delete_selected():
        """Mark selected saves for deletion without renaming"""
        selected_items = list_widget.selectedItems()
        if not selected_items:
            QMessageBox.critical(popup, "Error", "Please select at least one save to delete.")
            return
        
        selected_indices = [list_widget.row(item) for item in selected_items]
        selected_saves = [current_saves[idx] for idx in selected_indices if idx < len(current_saves)]
        
        if not selected_saves:
            return
        
        # Confirm deletion
        plurality = "s" if len(selected_saves) > 1 else ""
        saves_str = ", ".join(s['save_name'] for s in selected_saves)
        reply = QMessageBox.question(popup, f"Delete Save{plurality}", 
                                    f"Are you sure you want to delete the following save{plurality}?\n{saves_str}",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        # Initialize deleted saves history if not exists
        if not hasattr(gm, 'deleted_saves'):
            gm.deleted_saves = []
        
        logger = LoggingConfig.get_logger(__name__, LogCategory.SAVE)
        
        marked_count = 0
        for save in selected_saves:
            try:
                # Create deletion info
                deleted_info = {
                    'filename': save['filename'],
                    'path': str(Path(gm.save_manager.saves_dir) / save['filename']),
                    'save_name': save['save_name'],
                    'session_id': None,
                    'memory_path': None
                }
                
                # Get session ID from save data if possible
                try:
                    with open(deleted_info['path'], 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                        deleted_info['session_id'] = save_data.get('session_id')
                except Exception as e:
                    logger.error(f"Could not extract session_id: {e}")
                
                # Get memory path if session ID is available
                if hasattr(gm, 'state_manager') and hasattr(gm.state_manager, 'context_manager'):
                    session_id = deleted_info['session_id']
                    if session_id:
                        memory_path = gm.state_manager.context_manager.memory_io.get_memory_filepath(
                            session_id, save['save_name'])
                        deleted_info['memory_path'] = str(memory_path)
                
                # Add to deletion history
                gm.deleted_saves.append(deleted_info)
                marked_count += 1
                
            except Exception as e:
                logger.error(f"Error during save deletion: {e}")
                QMessageBox.warning(popup, "Delete Save", 
                                    f"Error marking save '{save['save_name']}' for deletion: {str(e)}")
        
        if marked_count > 0:
            plurality = "s" if marked_count > 1 else ""
            QMessageBox.information(popup, "Delete Save", 
                                f"{marked_count} save{plurality} marked for deletion.")
            # Enable undo button
            undo_delete_btn.setVisible(True)
        
        refresh_list()

    def undo_last_delete():
        """Restore the last deleted save file by removing it from deletion list"""
        if not hasattr(gm, 'deleted_saves') or not gm.deleted_saves:
            QMessageBox.information(popup, "Undo Delete", "No saves to restore.")
            return
        
        # Pop the last deleted save
        deleted_save = gm.deleted_saves.pop()
        logger = LoggingConfig.get_logger(__name__, LogCategory.SAVE)
        
        try:
            QMessageBox.information(popup, "Undo Delete", f"Save '{deleted_save['save_name']}' restored successfully.")
            
            # Hide undo button if no more deleted saves
            if not gm.deleted_saves:
                undo_delete_btn.setVisible(False)
            
        except Exception as e:
            logger.error(f"Error restoring save: {e}")
            QMessageBox.critical(popup, "Undo Delete", f"Error restoring save: {str(e)}")
        
        refresh_list()
    
    undo_delete_btn.clicked.connect(undo_last_delete)
    
    list_widget.itemSelectionChanged.connect(update_memory_display)
    refresh_list()
    filter_edit.textChanged.connect(refresh_list)
    sort_combo.currentIndexChanged.connect(refresh_list)
    
    # Check for existing deleted saves and show undo button if present
    if hasattr(gm, 'deleted_saves') and gm.deleted_saves:
        undo_delete_btn.setVisible(True)
    
    # Setup buttons based on mode
    if mode == "save":
        def save_new():
            save_name = save_name_entry.text().strip()
            if not save_name:
                QMessageBox.critical(popup, "Error", "Save name cannot be empty.")
                return
            
            # Check if this save name exists in current visible saves
            exists_in_current = any(s['save_name'].lower() == save_name.lower() for s in current_saves)
            
            force = False
            
            if exists_in_current:
                reply = QMessageBox.question(popup, "Overwrite?", f"A save named '{save_name}' exists. Overwrite?",
                                        QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
                force = True
            
            # Generate a summary for the save using LLM if available
            preview = generate_save_summary(gm)
            
            success, message = gm.save_manager.create_save(
                gm.state_manager, save_name, auto=False, force=force, 
                json_encoder=None, llm_manager=gm.llm_manager,
                preview=preview
            )
            
            if success:
                QMessageBox.information(popup, "Save Game", f"Game saved successfully as '{save_name}'.")
            else:
                QMessageBox.critical(popup, "Save Game", f"Failed to save game: {message}")
            refresh_list()
            
        def overwrite_selected():
            selected_items = list_widget.selectedItems()
            if not selected_items or len(selected_items) != 1:
                QMessageBox.critical(popup, "Error", "Please select exactly one save to overwrite.")
                return
            
            selected = list_widget.row(selected_items[0])
            if selected < 0 or selected >= len(current_saves):
                return
                
            selected_save = current_saves[selected]
            save_name = selected_save['save_name']
            
            reply = QMessageBox.question(popup, "Overwrite?", f"Are you sure you want to overwrite '{save_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            
            # Generate a summary for the save using LLM if available
            preview = generate_save_summary(gm)
            
            success, message = gm.save_manager.create_save(
                gm.state_manager, save_name, auto=False, force=True, 
                json_encoder=None, llm_manager=gm.llm_manager,
                preview=preview
            )
            
            if success:
                QMessageBox.information(popup, "Save Game", f"Game saved successfully as '{save_name}'.")
            else:
                QMessageBox.critical(popup, "Save Game", f"Failed to save game: {message}")
            refresh_list()
            
        btn_save_new = QPushButton("Save New", popup)
        btn_overwrite = QPushButton("Overwrite Selected", popup)
        btn_delete = QPushButton("Delete Selected", popup)
        btn_cancel = QPushButton("Cancel", popup)
        
        btn_save_new.clicked.connect(save_new)
        btn_overwrite.clicked.connect(overwrite_selected)
        btn_delete.clicked.connect(delete_selected)
        btn_cancel.clicked.connect(popup.reject)
        
        button_layout.addWidget(btn_save_new)
        button_layout.addWidget(btn_overwrite)
        button_layout.addWidget(btn_delete)
        button_layout.addWidget(btn_cancel)
    else:  # Load mode
        def load_selected():
            selected_items = list_widget.selectedItems()
            if not selected_items or len(selected_items) != 1:
                QMessageBox.critical(popup, "Error", "Please select exactly one save file to load.")
                return
            
            selected = list_widget.row(selected_items[0])
            if selected < 0 or selected >= len(current_saves):
                return
                
            chosen_save = current_saves[selected]
            gm._load_game_with_filename(chosen_save['filename'])
            popup.accept()
            
        btn_load = QPushButton("Load", popup)
        btn_delete = QPushButton("Delete Selected", popup)
        btn_cancel = QPushButton("Cancel", popup)
        
        btn_load.clicked.connect(load_selected)
        btn_delete.clicked.connect(delete_selected)
        btn_cancel.clicked.connect(popup.reject)
        
        button_layout.addWidget(btn_load)
        button_layout.addWidget(btn_delete)
        button_layout.addWidget(btn_cancel)
    
    # Add button layout
    layout.addLayout(button_layout)
    
    # Initial update
    update_multi_select_mode()
    
    popup.exec()

def open_new_game_popup(parent, gm):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox, QTextEdit, QSplitter, QHBoxLayout
    popup = QDialog(parent)
    popup.setWindowTitle("New Game - Character Creation")
    popup.resize(700, 500)  # Increased size to accommodate descriptions
    main_layout = QVBoxLayout(popup)
    
    # Create split view for form and descriptions
    splitter = QSplitter(Qt.Horizontal)
    
    # Left side - Form inputs
    form_widget = QWidget()
    layout = QVBoxLayout(form_widget)
    
    # Character name
    layout.addWidget(QLabel("Character Name:"))
    name_entry = QLineEdit(popup)
    layout.addWidget(name_entry)
    
    # Race selection
    layout.addWidget(QLabel("Race:"))
    race_dropdown = QComboBox(popup)
    
    # Load races from configuration
    races = []
    race_data = {}
    try:
        # Try to load races from configuration
        if hasattr(gm, 'config'):
            # First check if races are in world_config
            if hasattr(gm, 'state_manager') and hasattr(gm.state_manager, 'world_config'):
                if hasattr(gm.state_manager.world_config, 'races'):
                    races = list(gm.state_manager.world_config.races.keys())
                    race_data = gm.state_manager.world_config.races
            
            # If not found, try to load directly from file
            if not races:
                race_file = os.path.join(gm.config.project_root, "config", "game_races.json")
                if os.path.exists(race_file):
                    with open(race_file, "r", encoding="utf-8") as f:
                        race_json = json.load(f)
                    if "races" in race_json:
                        race_data = race_json["races"]
                        races = list(race_data.keys())
                    else:
                        race_data = race_json
                        races = list(race_data.keys())
    except Exception as e:
        print(f"Error loading race data: {e}")
    
    # Fallback to default races if none found
    if not races:
        races = ["human", "ethereal", "stoneborn", "sylvani"]
        race_data = {
            "human": {"name": "Human", "description": "Versatile and adaptable."},
            "ethereal": {"name": "Ethereal", "description": "Connected to magical energies."},
            "stoneborn": {"name": "Stoneborn", "description": "Hardy and resilient race."},
            "sylvani": {"name": "Sylvani", "description": "Graceful forest dwellers."}
        }
    
    # Add races to dropdown
    for race_key in races:
        display_name = race_data.get(race_key, {}).get("name", race_key.title())
        race_dropdown.addItem(display_name, race_key)
    
    layout.addWidget(race_dropdown)
    
    # Path selection
    layout.addWidget(QLabel("Path:"))
    path_dropdown = QComboBox(popup)
    try:
        paths = gm.state_manager.world_config_loader.get_available_paths()
    except Exception:
        paths = ["academic", "military", "civilian", "criminal"]
    path_dropdown.addItems(paths)
    layout.addWidget(path_dropdown)
    
    # Background selection
    layout.addWidget(QLabel("Background:"))
    background_dropdown = QComboBox(popup)
    try:
        backgrounds = gm.state_manager.world_config_loader.get_backgrounds_for_path(paths[0])
    except Exception:
        backgrounds = []
    background_dropdown.addItems(backgrounds)
    layout.addWidget(background_dropdown)
    
    # NEW: Add starting scenario selection
    layout.addWidget(QLabel("Starting Scenario:"))
    scenario_dropdown = QComboBox(popup)
    scenario_dropdown.addItem("Default for Background", "default")
    layout.addWidget(scenario_dropdown)
    
    # Function to update the scenarios dropdown when background changes
    def update_scenario_dropdown():
        scenario_dropdown.clear()
        scenario_dropdown.addItem("Default for Background", "default")
        
        try:
            current_path = path_dropdown.currentText()
            current_bg = background_dropdown.currentText()
            
            # Get all scenarios for this path
            path_scenarios = gm.state_manager.world_config_loader.get_scenarios_for_path(current_path)
            
            # Filter to those applicable to this background
            for scenario_key, scenario in path_scenarios.items():
                if "applicable_backgrounds" in scenario:
                    bg_lower = current_bg.lower()
                    bg_underscored = bg_lower.replace(" ", "_")
                    applicable = [str(bg).lower() for bg in scenario["applicable_backgrounds"]]
                    
                    if bg_lower in applicable or bg_underscored in applicable:
                        scenario_dropdown.addItem(scenario.get("name", scenario_key), scenario_key)
        except Exception as e:
            print(f"Error updating scenario dropdown: {e}")
    
    # Start button
    btn_confirm = QPushButton("Start Game", popup)
    layout.addWidget(btn_confirm)
    
    # Add spacing at the bottom
    layout.addStretch()
    
    # Right side - Description panel
    description_panel = QWidget()
    desc_layout = QVBoxLayout(description_panel)
    
    desc_layout.addWidget(QLabel("<h2>Character Details</h2>"))
    
    # Race description
    desc_layout.addWidget(QLabel("<h3>Race</h3>"))
    race_desc = QTextEdit()
    race_desc.setReadOnly(True)
    race_desc.setMinimumHeight(150)
    desc_layout.addWidget(race_desc)
    
    # Path & Background description 
    desc_layout.addWidget(QLabel("<h3>Path & Background</h3>"))
    path_bg_desc = QTextEdit()
    path_bg_desc.setReadOnly(True)
    path_bg_desc.setMinimumHeight(150)
    desc_layout.addWidget(path_bg_desc)
    
    # NEW: Scenario description
    desc_layout.addWidget(QLabel("<h3>Starting Scenario</h3>"))
    scenario_desc = QTextEdit()
    scenario_desc.setReadOnly(True)
    scenario_desc.setMinimumHeight(150)
    desc_layout.addWidget(scenario_desc)
    
    # Add widgets to splitter
    splitter.addWidget(form_widget)
    splitter.addWidget(description_panel)
    splitter.setSizes([300, 400])  # Set initial sizes
    
    # Add splitter to main layout
    main_layout.addWidget(splitter)
    
    # Function to update descriptions based on selections
    def update_descriptions():
        # Update race description
        selected_race_key = race_dropdown.currentData()
        race_info = race_data.get(selected_race_key, {})
        race_name = race_info.get("name", selected_race_key.title())
        race_description = race_info.get("description", "No description available.")
        race_stats = race_info.get("stat_modifiers", {})
        
        # Format race description with HTML
        race_html = f"<h3>{race_name}</h3>"
        race_html += f"<p>{race_description}</p>"
        
        if race_stats:
            race_html += "<p><b>Stat Modifiers:</b></p><ul>"
            for stat, mod in race_stats.items():
                sign = "+" if mod > 0 else ""
                race_html += f"<li>{stat}: {sign}{mod}</li>"
            race_html += "</ul>"
        
        race_desc.setHtml(race_html)
        
        # Update path & background description
        selected_path = path_dropdown.currentText()
        selected_bg = background_dropdown.currentText()
        
        # Try to get detailed information about the path
        path_info = {}
        try:
            if hasattr(gm, 'state_manager') and hasattr(gm.state_manager, 'world_config_loader'):
                paths_data = None
                paths_file = os.path.join(gm.config.project_root, "config", "world", "characters", "paths.json")
                if os.path.exists(paths_file):
                    with open(paths_file, "r", encoding="utf-8") as f:
                        paths_data = json.load(f)
                    if paths_data and "paths" in paths_data:
                        path_info = paths_data["paths"].get(selected_path.lower(), {})
        except Exception as e:
            print(f"Error loading path data: {e}")
        
        # Get background information
        bg_info = {}
        try:
            if hasattr(gm, 'state_manager') and hasattr(gm.state_manager, 'world_config_loader'):
                bg_info = gm.state_manager.world_config_loader.load_background(selected_bg)
                if bg_info is None:
                    bg_info = {}  # Ensure bg_info is never None
        except Exception as e:
            print(f"Error loading background data: {e}")
            bg_info = {}  # Ensure bg_info is never None

        # Format path & background description with HTML
        path_html = f"<h3>{selected_path.title()}</h3>"
        path_html += f"<p>{path_info.get('description', 'No description available.')}</p>"

        if path_info.get('starting_advantages'):
            path_html += "<p><b>Starting Advantages:</b></p><ul>"
            for adv in path_info.get('starting_advantages', []):
                path_html += f"<li>{adv}</li>"
            path_html += "</ul>"

        path_html += f"<h3>{selected_bg}</h3>"
        path_html += f"<p>{bg_info.get('description', 'No description available.')}</p>"
        
        if bg_info.get('skills'):
            path_html += "<p><b>Starting Skills:</b></p><ul>"
            for skill, level in bg_info.get('skills', {}).items():
                path_html += f"<li>{skill.replace('_', ' ').title()}: {level}</li>"
            path_html += "</ul>"
        
        path_bg_desc.setHtml(path_html)
        
        # NEW: Update scenario description with proper default scenario loading
        scenario_key = scenario_dropdown.currentData()
        if scenario_key == "default":
            # Try to load the actual default scenario for this background
            try:
                # Load the default scenario that matches this background
                default_scenario = gm.state_manager.world_config_loader.load_starting_scenario(selected_bg)
                if default_scenario:
                    # Found a matching default scenario - display its details
                    scenario_html = f"<h3>{default_scenario.get('name', 'Default Scenario')}</h3>"
                    scenario_html += f"<p><b>Location:</b> {default_scenario.get('location', 'Unknown')}, {default_scenario.get('district', '')}</p>"
                    
                    # Add introduction
                    if "narrative_elements" in default_scenario and "introduction" in default_scenario["narrative_elements"]:
                        intro = default_scenario["narrative_elements"]["introduction"]
                        if isinstance(intro, list):
                            scenario_html += "<p><b>Introduction:</b></p>"
                            scenario_html += "<ul>"
                            for paragraph in intro:
                                scenario_html += f"<li>{paragraph}</li>"
                            scenario_html += "</ul>"
                        else:
                            scenario_html += f"<p><b>Introduction:</b> {intro}</p>"
                    
                    # Add objectives
                    if "narrative_elements" in default_scenario and "immediate_goals" in default_scenario["narrative_elements"]:
                        goals = default_scenario["narrative_elements"]["immediate_goals"]
                        if isinstance(goals, list):
                            scenario_html += "<p><b>Immediate Goals:</b></p>"
                            scenario_html += "<ul>"
                            for goal in goals:
                                scenario_html += f"<li>{goal}</li>"
                            scenario_html += "</ul>"
                    
                    scenario_desc.setHtml(scenario_html)
                else:
                    # No default scenario found
                    scenario_desc.setHtml("<p>No specific default scenario found for this background.</p><p>The game will use general background information to create your starting scenario.</p>")
            except Exception as e:
                print(f"Error loading default scenario: {e}")
                scenario_desc.setHtml("<p>Error loading default scenario.</p>")
        else:
            # Regular scenario selection
            try:
                current_path = path_dropdown.currentText()
                path_scenarios = gm.state_manager.world_config_loader.get_scenarios_for_path(current_path)
                
                if scenario_key in path_scenarios:
                    scenario_data = path_scenarios[scenario_key]
                    
                    scenario_html = f"<h3>{scenario_data.get('name', scenario_key)}</h3>"
                    scenario_html += f"<p><b>Location:</b> {scenario_data.get('location', 'Unknown')}, {scenario_data.get('district', '')}</p>"
                    
                    # Add introduction
                    if "narrative_elements" in scenario_data and "introduction" in scenario_data["narrative_elements"]:
                        intro = scenario_data["narrative_elements"]["introduction"]
                        if isinstance(intro, list):
                            scenario_html += "<p><b>Introduction:</b></p>"
                            scenario_html += "<ul>"
                            for paragraph in intro:
                                scenario_html += f"<li>{paragraph}</li>"
                            scenario_html += "</ul>"
                        else:
                            scenario_html += f"<p><b>Introduction:</b> {intro}</p>"
                    
                    # Add objectives
                    if "narrative_elements" in scenario_data and "immediate_goals" in scenario_data["narrative_elements"]:
                        goals = scenario_data["narrative_elements"]["immediate_goals"]
                        if isinstance(goals, list):
                            scenario_html += "<p><b>Immediate Goals:</b></p>"
                            scenario_html += "<ul>"
                            for goal in goals:
                                scenario_html += f"<li>{goal}</li>"
                            scenario_html += "</ul>"
                    
                    # Add equipment if present
                    if "starting_equipment" in scenario_data and scenario_data["starting_equipment"]:
                        scenario_html += "<p><b>Starting Equipment:</b></p><ul>"
                        try:
                            from core.base.config import GameConfig
                            inventory_manager = InventoryManager(GameConfig())
                            for item_id in scenario_data["starting_equipment"]:
                                item = inventory_manager.item_database.get(item_id)
                                if item:
                                    scenario_html += f"<li>{item.name}</li>"
                                else:
                                    scenario_html += f"<li>{item_id}</li>"
                        except Exception as e:
                            print(f"Error loading equipment: {e}")
                            for item_id in scenario_data["starting_equipment"]:
                                scenario_html += f"<li>{item_id}</li>"
                        scenario_html += "</ul>"
                    
                    scenario_desc.setHtml(scenario_html)
                else:
                    scenario_desc.setHtml("<p>No detailed description available.</p>")
            except Exception as e:
                scenario_desc.setHtml(f"<p>Error loading scenario description: {str(e)}</p>")
    
    def update_backgrounds():
        selected_path = path_dropdown.currentText()
        background_dropdown.clear()
        try:
            backgrounds = gm.state_manager.world_config_loader.get_backgrounds_for_path(selected_path)
        except Exception:
            backgrounds = []
        background_dropdown.addItems(backgrounds)
        update_descriptions()
        update_scenario_dropdown()
    
    path_dropdown.currentIndexChanged.connect(update_backgrounds)
    background_dropdown.currentIndexChanged.connect(update_scenario_dropdown)
    background_dropdown.currentIndexChanged.connect(update_descriptions)
    scenario_dropdown.currentIndexChanged.connect(update_descriptions)
    
    # Initialize descriptions
    update_descriptions()
    
    def on_confirm():
        name = name_entry.text().strip()
        race = race_dropdown.currentData()  # Use the race key, not display name
        if not race:
            race = race_dropdown.currentText()
        path = path_dropdown.currentText().strip()
        background = background_dropdown.currentText().strip()
        scenario = scenario_dropdown.currentData()
        
        if name and race and path and background:
            # Pass the selected scenario to the game manager
            gm._start_new_game_with_args(name, race, path, background, scenario)
            popup.accept()
        else:
            QMessageBox.critical(popup, "Error", "Please fill out all fields.")
    
    btn_confirm.clicked.connect(on_confirm)
    
    popup.exec()
    
def open_load_game_popup(parent, gm):
    open_save_load_dialog(parent, gm, "load")

def open_save_game_popup(parent, gm):
    open_save_load_dialog(parent, gm, "save")

def open_log_explorer(parent, gm):
    """Open the Log Explorer dialog"""
    from gui.log_explorer import LogExplorer
    explorer = LogExplorer(parent)
    explorer.exec()

# Then update open_developer_settings_popup function
def open_developer_settings_popup(parent, gm):
    if REQUIRE_DEV_CREDENTIALS:
        # Future implementation: prompt for credentials here.
        pass
    popup = QDialog(parent)
    popup.setWindowTitle("Developer Settings")
    popup.resize(300, 200)
    layout = QVBoxLayout(popup)
    
    btn_basic = QPushButton("Basic Settings (direct JSON)", popup)
    btn_advanced = QPushButton("Advanced Settings (explorer)", popup)
    btn_logs = QPushButton("Log Explorer", popup)  # New button
    layout.addWidget(btn_basic)
    layout.addWidget(btn_advanced)
    layout.addWidget(btn_logs)  # Add log explorer button
    
    btn_basic.clicked.connect(lambda: open_basic_developer_settings(parent, gm))
    btn_advanced.clicked.connect(lambda: open_advanced_config_editor(parent, gm))
    btn_logs.clicked.connect(lambda: open_log_explorer(parent, gm))  # Connect to new function
    
    popup.exec()

def open_basic_developer_settings(parent, gm):
    popup = QDialog(parent)
    popup.setWindowTitle("Basic Developer Settings (Direct JSON)")
    popup.resize(600, 500)
    layout = QVBoxLayout(popup)
    
    tab_widget = QTabWidget(popup)
    layout.addWidget(tab_widget)
    
    files_to_edit = [
        {"tab_name": "Paths", "filepath": "config/world/characters/paths.json"},
        {"tab_name": "World History", "filepath": "config/world/base/world_history.json"},
        {"tab_name": "Fundamental Rules", "filepath": "config/world/base/fundamental_rules.json"},
        {"tab_name": "Cultures", "filepath": "config/world/base/cultures.json"},
        {"tab_name": "Starting Scenarios", "filepath": "config/world/scenarios/starting_scenarios.json"}
    ]
    
    dev_editors = {}
    
    for file_info in files_to_edit:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        
        editor = QPlainTextEdit(tab)
        editor.setFont(QFont("Courier", 10))
        tab_layout.addWidget(editor)
        
        try:
            with open(file_info["filepath"], "r", encoding="utf-8") as f:
                content = f.read()
            editor.setPlainText(content)
        except Exception as e:
            editor.setPlainText(f"Error loading file: {e}")
        
        btn_save = QPushButton("Save", tab)
        tab_layout.addWidget(btn_save)
        
        def make_save_handler(filepath=file_info["filepath"], editor=editor):
            def save_handler():
                text = editor.toPlainText()
                try:
                    parsed = json.loads(text)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(parsed, f, indent=2)
                    QMessageBox.information(popup, "Success", f"File '{filepath}' saved successfully.")
                except Exception as e:
                    QMessageBox.critical(popup, "Error", f"Failed to save '{filepath}': {e}")
            return save_handler
        
        btn_save.clicked.connect(make_save_handler())
        
        tab_widget.addTab(tab, file_info["tab_name"])
        dev_editors[file_info["tab_name"]] = editor
    
    # New Tab for Backgrounds
    tab_bg = QWidget()
    tab_bg_layout = QVBoxLayout(tab_bg)
    
    combo_backgrounds = QComboBox(tab_bg)
    tab_bg_layout.addWidget(combo_backgrounds)
    
    editor_background = QPlainTextEdit(tab_bg)
    editor_background.setFont(QFont("Courier", 10))
    tab_bg_layout.addWidget(editor_background)
    
    btn_save_background = QPushButton("Save", tab_bg)
    tab_bg_layout.addWidget(btn_save_background)
    
    backgrounds_folder = "config/world/characters/backgrounds"
    background_files = sorted(glob.glob(os.path.join(backgrounds_folder, "*.json")))
    background_files_mapping = {}
    for file in background_files:
        base = os.path.basename(file)
        name, ext = os.path.splitext(base)
        display_name = name.capitalize()
        background_files_mapping[display_name] = file
        combo_backgrounds.addItem(display_name)
    
    def load_background_content():
        selected = combo_backgrounds.currentText()
        filepath = background_files_mapping.get(selected)
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                editor_background.setPlainText(content)
            except Exception as e:
                editor_background.setPlainText(f"Error loading file: {e}")
    combo_backgrounds.currentIndexChanged.connect(load_background_content)
    load_background_content()
    
    def save_background_content():
        selected = combo_backgrounds.currentText()
        filepath = background_files_mapping.get(selected)
        if filepath:
            text = editor_background.toPlainText()
            try:
                parsed = json.loads(text)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2)
                QMessageBox.information(popup, "Success", f"Background file '{filepath}' saved successfully.")
            except Exception as e:
                QMessageBox.critical(popup, "Error", f"Failed to save '{filepath}': {e}")
    btn_save_background.clicked.connect(save_background_content)
    
    tab_widget.addTab(tab_bg, "Backgrounds")
    dev_editors["Backgrounds"] = editor_background
    
    popup.exec()


def open_advanced_config_editor(parent, gm):
    # Close the current popup (if any) and open the advanced config editor.
    editor = AdvancedConfigEditor(parent)
    editor.exec()


def open_resolution_settings_popup(parent, gm):
    popup = QDialog(parent)
    popup.setWindowTitle("GUI Resolution Settings")
    popup.resize(300, 200)
    layout = QVBoxLayout(popup)
    
    layout.addWidget(QLabel("Select GUI Resolution:", popup))
    resolution_dropdown = QComboBox(popup)
    resolutions = [
        "800x600",
        "1024x768",
        "1280x720",
        "1366x768",
        "1600x900",
        "1920x1080",
        "2560x1440",
        "3840x2160"
    ]
    resolution_dropdown.addItems(resolutions)
    layout.addWidget(resolution_dropdown)
    
    full_screen_checkbox = QCheckBox("Full Screen", popup)
    layout.addWidget(full_screen_checkbox)
    
    def apply_resolution():
        if full_screen_checkbox.isChecked():
            parent.showFullScreen()
        else:
            res_text = resolution_dropdown.currentText()
            try:
                width, height = map(int, res_text.split("x"))
            except Exception as e:
                QMessageBox.critical(popup, "Error", "Invalid resolution selected.")
                return
            parent.setFixedSize(width, height)
            parent.showNormal()
        popup.accept()
    btn_apply = QPushButton("Apply", popup)
    btn_apply.clicked.connect(apply_resolution)
    layout.addWidget(btn_apply)
    
    popup.exec()


def open_layout_settings_popup(parent, gm):
    popup = QDialog(parent)
    popup.setWindowTitle("Settings - Layout")
    popup.resize(400, 300)
    layout = QVBoxLayout(popup)
    
    lbl = QLabel("Choose Theme:", popup)
    lbl.setFont(QFont("Arial", 12))
    layout.addWidget(lbl)
    
    theme_dropdown = QComboBox(popup)
    try:
        with open("config/gui_themes.json", "r") as f:
            themes_data = json.load(f)
        available_themes = list(themes_data["themes"].keys())
        theme_dropdown.addItems(available_themes)
    except Exception as e:
        available_themes = []
    layout.addWidget(theme_dropdown)
    
    preview_label = QLabel("Preview Text", popup)
    preview_label.setFont(QFont("Garamond", 12))
    layout.addWidget(preview_label)
    
    def update_preview(index):
        selected_theme = theme_dropdown.currentText()
        if selected_theme in themes_data["themes"]:
            theme = themes_data["themes"][selected_theme]
            font_main = theme.get("font_main", ["Garamond", 12])
            preview_label.setFont(QFont(font_main[0], font_main[1]))
    theme_dropdown.currentIndexChanged.connect(update_preview)
    
    def apply_settings():
        selected_theme = theme_dropdown.currentText()
        if selected_theme in themes_data["themes"]:
            theme = themes_data["themes"][selected_theme]
            font_main = theme.get("font_main", ["Garamond", 12])
            if hasattr(parent, "output_text"):
                parent.output_text.setFont(QFont(font_main[0], font_main[1]))
                parent.output_text.setStyleSheet("background: transparent; color: black;")
            if hasattr(parent, "tab_debug"):
                parent.tab_debug.setFont(QFont(*theme.get("font_debug", ["Courier", 10])))
                parent.tab_debug.setStyleSheet(f"background-color: {theme.get('bg_debug', '#EEE')};")
            if hasattr(parent, "left_buttons"):
                for btn in parent.left_buttons:
                    btn.update_theme(theme)
            if hasattr(parent, "control_buttons"):
                for btn in parent.control_buttons:
                    btn.update_theme(theme)
        popup.accept()
    btn_apply = QPushButton("Apply", popup)
    btn_apply.clicked.connect(apply_settings)
    layout.addWidget(btn_apply)
    
    popup.exec()

def generate_save_summary(gm) -> str:
    """Generate a summary for a save game using current game context"""
    logger = LoggingConfig.get_logger(__name__, LogCategory.SAVE)
    
    # First, create a basic static summary
    try:
        if not gm.state_manager.state:
            return "No active game state"
        
        player = gm.state_manager.state.player
        location = player.location
        level = player.level
        time_value = gm.state_manager.state.world.time
        
        # Convert time to readable format
        from core.utils.time_utils import format_world_time, get_time_of_day
        time_str = format_world_time(time_value)
        time_desc = get_time_of_day(time_value)
        
        # Get conversation history (last entry)
        last_conversation = None
        if gm.state_manager.state.conversation_history:
            last_entry = gm.state_manager.state.conversation_history[-1]
            if last_entry.get("speaker") == "GameMaster":
                last_conversation = last_entry.get("content", "")
                # Take only first 100 chars for brevity
                if last_conversation and len(last_conversation) > 100:
                    last_conversation = last_conversation[:100] + "..."
        
        # Get active quest count
        quest_count = len(gm.state_manager.state.active_quests)
        
        # Basic summary that works without LLM
        static_summary = (
            f"{player.name} the {player.race} ({player.background}) is currently at {location} "
            f"during {time_desc}. "
        )
        
        if quest_count > 0:
            static_summary += f"Active quests: {quest_count}. "
            
        if last_conversation:
            static_summary += f"Recent events: {last_conversation}"
        
        # Try to use LLM for enhanced summary if available
        try:
            if hasattr(gm, 'llm_manager'):
                import asyncio
                
                # Create specific prompt using game context
                prompt = (
                    f"Generate a short, engaging 2-3 sentence summary that captures the essence of the current game state. "
                    f"The character is {player.name}, a {player.race} {player.background}, currently at {location}. "
                    f"It is currently {time_desc}. "
                )
                
                # Add conversation context if available
                if last_conversation:
                    prompt += f"Recent events: {last_conversation} "
                
                if quest_count > 0:
                    prompt += f"They have {quest_count} active quests. "
                
                prompt += "The summary should read like an exciting book blurb that would make someone want to continue the adventure."
                
                # Get current event loop
                try:
                    loop = asyncio.get_event_loop()
                    if not loop.is_running():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except Exception:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Create messages for LLM
                messages = [
                    {"role": "system", "content": "You are creating brief, engaging summaries for saved games."},
                    {"role": "user", "content": prompt}
                ]
                
                # Try a safe synchronous approach
                try:
                    if hasattr(loop, 'run_until_complete'):
                        response_future = gm.llm_manager.get_completion(messages, "narrator")
                        llm_response = loop.run_until_complete(asyncio.wait_for(response_future, timeout=5.0))
                    else:
                        future = asyncio.run_coroutine_threadsafe(
                            gm.llm_manager.get_completion(messages, "narrator"),
                            loop
                        )
                        llm_response = future.result(timeout=5.0)
                    
                    if llm_response.success and llm_response.content:
                        # Clean up any LLM artifacts (like music tags)
                        content = re.sub(r'\{MUSIC:\s*[\w]+\s*\}', '', llm_response.content, flags=re.IGNORECASE)
                        return content.strip()
                    
                except Exception as e:
                    logger.error(f"LLM summary generation failed: {e}")
                    # Fall back to static summary
                    return static_summary
                    
        except Exception as e:
            logger.error(f"Error in LLM summary generation: {e}")
            # Fall back to static summary
        
        return static_summary
        
    except Exception as e:
        logger.error(f"Error generating save summary: {e}")
        return "Save game summary unavailable"
