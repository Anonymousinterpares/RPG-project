#!/usr/bin/env python3
"""
Journal panel widget for the RPG game GUI.
This module provides a widget for displaying and editing the player's journal.
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, 
    QScrollArea, QFrame, QGroupBox, QListWidget, QListWidgetItem,
    QPushButton, QTabWidget, QTextEdit, QSplitter, QTabBar
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont, QTextCharFormat, QColor

from core.base.state import get_state_manager
from gui.utils.resource_manager import get_resource_manager

# Fantasy RPG Color Palette
COLOR_BG_DARK = "#1a1410"           # Dark background
COLOR_BG_MEDIUM = "#2a2420"         # Medium background
COLOR_BG_LIGHT = "#3a302a"          # Light background
COLOR_BORDER = "#4a3a30"            # Border color
COLOR_TEXT_PRIMARY = "#c9a875"      # Golden/amber text
COLOR_TEXT_SECONDARY = "#e0d4c0"    # Light parchment text
COLOR_ACCENT_GREEN = "#5a9068"      # Green accent
COLOR_ACCENT_GREEN_LIGHT = "#6ac46a" # Light green
COLOR_ACCENT_RED = "#8a5050"        # Red accent
COLOR_ACCENT_RED_LIGHT = "#ff6b6b"  # Light red
COLOR_HOVER = "#3a3028"             # Hover state
COLOR_SELECTED = "#4a5040"          # Selected state

class JournalSectionType(Enum):
    """Types of journal sections."""
    CHARACTER = 0
    QUESTS = 1
    NOTES = 2


class JournalPanelWidget(QScrollArea):
    """Widget for displaying and editing the journal."""
    
    # Signals for journal actions
    journal_updated = Signal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the journal panel widget."""
        super().__init__(parent)
        
        # Set up the scroll area
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #2D2D30;
                border: none;
            }
        """)
        
        # Create the main widget
        self.journal_widget = QWidget()
        self.setWidget(self.journal_widget)
        
        # Journal data structure
        self.journal_data = {
            "character": "",
            "quests": {},
            "notes": []
        }
        
        # Get state manager
        self.state_manager = get_state_manager()
        
        # Get resource manager
        self.resource_manager = get_resource_manager()
        
        # Set up the UI
        self._setup_ui()

        # --- FIX: APPLY CURSORS AFTER UI IS BUILT ---
        main_win = self.window()
        if hasattr(main_win, 'link_cursor'):
            # Apply to tab bars
            self.tab_widget.tabBar().setCursor(main_win.link_cursor)
            self.quest_status_tabs.tabBar().setCursor(main_win.link_cursor)
        
        if hasattr(main_win, 'text_cursor'):
            # Apply to editable text widgets
            self.character_info_editor.viewport().setCursor(main_win.text_cursor)
            self.note_editor.viewport().setCursor(main_win.text_cursor)
        # --- END FIX ---
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        self.main_layout = QVBoxLayout(self.journal_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)
        
        # Create tab widget for sections
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget {{
                background-color: {COLOR_BG_MEDIUM};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
            }}
            QTabWidget::pane {{
                background-color: {COLOR_BG_MEDIUM};
                border: 1px solid {COLOR_BORDER};
                border-top: none;
                border-radius: 0 0 5px 5px;
            }}
            QTabBar::tab {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_BG_LIGHT}, stop:1 {COLOR_BG_MEDIUM});
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 8px 12px;
                margin-right: 2px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_BG_MEDIUM}, stop:1 {COLOR_BG_DARK});
                color: {COLOR_TEXT_SECONDARY};
                border-bottom: none;
            }}
            QTabBar::tab:hover:!selected {{
                background: {COLOR_HOVER};
                color: {COLOR_ACCENT_GREEN};
            }}
        """)
        
        # Add tabs for each section
        self._setup_character_tab()
        self._setup_quests_tab()
        self._setup_notes_tab()
        
        # Add tab widget to main layout
        self.main_layout.addWidget(self.tab_widget)
    
    def _setup_character_tab(self):
        """Set up the character information tab."""
        # Create character tab
        character_tab = QWidget()
        character_layout = QVBoxLayout(character_tab)
        
        # Create character info editor
        self.character_info_editor = QTextEdit()
        self.character_info_editor.setPlaceholderText("Character bio and information will appear here...")
        self.character_info_editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_BG_DARK};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                padding: 8px;
                selection-background-color: {COLOR_SELECTED};
            }}
        """)
        self.character_info_editor.textChanged.connect(self._on_character_info_changed)
        
        # Add editor to layout
        character_layout.addWidget(self.character_info_editor)
        
        # Add tab to tab widget
        self.tab_widget.addTab(character_tab, "Character")
    
    def _setup_quests_tab(self):
        """Set up the quests tab."""
        # Create quests tab
        quests_tab = QWidget()
        quests_layout = QVBoxLayout(quests_tab)
        
        # Create quest status tabs
        self.quest_status_tabs = QTabWidget()
        self.quest_status_tabs.setStyleSheet(f"""
            QTabBar::tab {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_BG_LIGHT}, stop:1 {COLOR_BG_MEDIUM});
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                padding: 5px 10px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {COLOR_BG_DARK};
                color: {COLOR_TEXT_SECONDARY};
                border-bottom: none;
            }}
            QTabBar::tab:hover:!selected {{
                background: {COLOR_HOVER};
                color: {COLOR_ACCENT_GREEN};
            }}
        """)
        
        # Create lists for active, completed, and failed quests
        list_style = f"""
            QListWidget {{
                background-color: {COLOR_BG_DARK};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                alternate-background-color: {COLOR_BG_MEDIUM};
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLOR_BORDER};
            }}
            QListWidget::item:selected {{
                background-color: {COLOR_SELECTED};
                color: {COLOR_TEXT_SECONDARY};
            }}
            QListWidget::item:hover {{
                background-color: {COLOR_HOVER};
                color: {COLOR_ACCENT_GREEN};
            }}
        """
        
        self.active_quests_list = QListWidget()
        self.active_quests_list.setStyleSheet(list_style)
        self.active_quests_list.setAlternatingRowColors(True)
        self.active_quests_list.itemClicked.connect(self._on_quest_selected)
        self.active_quests_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.active_quests_list.customContextMenuRequested.connect(self._show_active_context_menu)
        
        self.completed_quests_list = QListWidget()
        self.completed_quests_list.setStyleSheet(list_style)
        self.completed_quests_list.setAlternatingRowColors(True)
        self.completed_quests_list.itemClicked.connect(self._on_quest_selected)
        self.completed_quests_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.completed_quests_list.customContextMenuRequested.connect(lambda pos: self._show_notes_only_context_menu(self.completed_quests_list, pos))
        
        self.failed_quests_list = QListWidget()
        self.failed_quests_list.setStyleSheet(list_style)
        self.failed_quests_list.setAlternatingRowColors(True)
        self.failed_quests_list.itemClicked.connect(self._on_quest_selected)
        self.failed_quests_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.failed_quests_list.customContextMenuRequested.connect(lambda pos: self._show_notes_only_context_menu(self.failed_quests_list, pos))
        
        # Add lists to quest status tabs
        self.quest_status_tabs.addTab(self.active_quests_list, "Active")
        self.quest_status_tabs.addTab(self.completed_quests_list, "Completed")
        self.quest_status_tabs.addTab(self.failed_quests_list, "Failed")
        
        # Create quest details view
        self.quest_details = QTextEdit()
        self.quest_details.setReadOnly(True)
        self.quest_details.setPlaceholderText("Select a quest to view details...")
        self.quest_details.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_BG_DARK};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                padding: 8px;
            }}
        """)
        
        # Create splitter for quest list and details
        quests_splitter = QSplitter(Qt.Vertical)
        quests_splitter.addWidget(self.quest_status_tabs)
        quests_splitter.addWidget(self.quest_details)
        quests_splitter.setSizes([int(quests_tab.height() * 0.4), int(quests_tab.height() * 0.6)])
        
        # Add splitter to layout
        quests_layout.addWidget(quests_splitter)
        
        # Add tab to tab widget
        self.tab_widget.addTab(quests_tab, "Quests")
    
    def _setup_notes_tab(self):
        """Set up the personal notes tab."""
        # Create notes tab
        notes_tab = QWidget()
        notes_layout = QVBoxLayout(notes_tab)
        
        # Create notes list
        self.notes_list = QListWidget()
        self.notes_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLOR_BG_DARK};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                alternate-background-color: {COLOR_BG_MEDIUM};
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLOR_BORDER};
            }}
            QListWidget::item:selected {{
                background-color: {COLOR_SELECTED};
                color: {COLOR_TEXT_SECONDARY};
            }}
            QListWidget::item:hover {{
                background-color: {COLOR_HOVER};
                color: {COLOR_ACCENT_GREEN};
            }}
        """)
        self.notes_list.setAlternatingRowColors(True)
        self.notes_list.itemClicked.connect(self._on_note_selected)
        
        # Create note editor
        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Select a note to edit or create a new one...")
        self.note_editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLOR_BG_DARK};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                padding: 8px;
                selection-background-color: {COLOR_SELECTED};
            }}
        """)
        self.note_editor.textChanged.connect(self._on_note_text_changed)
        
        # Create buttons for note management
        button_layout = QHBoxLayout()
        
        # Style for buttons - enhanced with gradients
        button_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_BG_LIGHT}, stop:1 {COLOR_BG_MEDIUM});
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_HOVER}, stop:1 {COLOR_BG_LIGHT});
                border-color: {COLOR_ACCENT_GREEN};
                color: {COLOR_ACCENT_GREEN};
            }}
            QPushButton:pressed {{
                background: {COLOR_BG_DARK};
                border-color: {COLOR_ACCENT_GREEN};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BG_DARK};
                color: {COLOR_BORDER};
                border-color: {COLOR_BG_MEDIUM};
            }}
        """
        
        # Create buttons
        self.new_note_button = QPushButton("New Note")
        self.new_note_button.setStyleSheet(button_style)
        self.new_note_button.clicked.connect(self._on_new_note_clicked)
        
        self.delete_note_button = QPushButton("Delete Note")
        self.delete_note_button.setStyleSheet(button_style)
        self.delete_note_button.clicked.connect(self._on_delete_note_clicked)
        self.delete_note_button.setEnabled(False)
        
        self.save_note_button = QPushButton("Save Note")
        self.save_note_button.setStyleSheet(button_style)
        self.save_note_button.clicked.connect(self._on_save_note_clicked)
        self.save_note_button.setEnabled(False)
        
        # Add buttons to layout
        button_layout.addWidget(self.new_note_button)
        button_layout.addWidget(self.delete_note_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_note_button)
        
        # Create splitter for notes list and editor
        notes_splitter = QSplitter(Qt.Vertical)
        notes_splitter.addWidget(self.notes_list)
        
        # Create editor container with buttons
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self.note_editor)
        editor_layout.addLayout(button_layout)
        
        notes_splitter.addWidget(editor_container)
        notes_splitter.setSizes([int(notes_tab.height() * 0.3), int(notes_tab.height() * 0.7)])
        
        # Add splitter to layout
        notes_layout.addWidget(notes_splitter)
        
        # Add tab to tab widget
        self.tab_widget.addTab(notes_tab, "Notes")

    def _on_character_info_changed(self):
        """Handle character info text changes."""
        # Update journal data
        self.journal_data["character"] = self.character_info_editor.toPlainText()
        
        # Emit journal updated signal
        self._emit_journal_updated()
    
    def _on_quest_selected(self, item: QListWidgetItem):
        """Handle quest selection."""
        # Get the quest ID from the item
        quest_id = item.data(Qt.UserRole)
        
        # Get the quest data
        quest_status = self._get_current_quest_status()
        if quest_status and quest_id in self.journal_data["quests"]:
            quest_data = self.journal_data["quests"][quest_id]
            
            # Update quest details
            self.quest_details.clear()
            
            # Enhanced inline CSS with fantasy colors
            style = f"""
                <style>
                    body {{ color: {COLOR_TEXT_SECONDARY}; }}
                    h2 {{ color: {COLOR_TEXT_PRIMARY}; border-bottom: 2px solid {COLOR_BORDER}; padding-bottom: 5px; }}
                    h3 {{ color: {COLOR_TEXT_PRIMARY}; margin-top: 15px; }}
                    .obj-done {{ color: {COLOR_ACCENT_GREEN_LIGHT}; }}
                    .obj-failed {{ color: {COLOR_ACCENT_RED_LIGHT}; }}
                    .obj-pending {{ color: {COLOR_TEXT_SECONDARY}; }}
                    .obj-mandatory {{ color: {COLOR_TEXT_PRIMARY}; font-style: italic; margin-left: 6px; font-size: 0.9em; }}
                </style>
            """
            # Format the quest details
            html = style + f"<h2>{quest_data['title']}</h2>"
            html += f"<p><b style='color: {COLOR_TEXT_PRIMARY};'>Status:</b> {quest_status.title()}</p>"
            
            if "description" in quest_data:
                html += f"<p>{quest_data['description']}</p>"
            
            if "objectives" in quest_data and quest_data["objectives"]:
                html += "<h3>Objectives:</h3>"
                html += "<ul>"
                for objective in quest_data["objectives"]:
                    desc = objective.get('description', '')
                    completed = objective.get('completed', False)
                    failed = objective.get('failed', False)
                    mandatory = objective.get('mandatory', True)
                    tag = "(M)" if mandatory else "(O)"
                    cls = 'obj-pending'
                    if completed:
                        cls = 'obj-done'
                    elif failed:
                        cls = 'obj-failed'
                    tooltip = "Mandatory requirement" if mandatory else "Optional objective"
                    html += f"<li><span class='{cls}'>"
                    if completed:
                        html += f"<s>{desc}</s> <span class='obj-mandatory' title='{tooltip}'>{tag}</span>"
                    else:
                        html += f"{desc} <span class='obj-mandatory' title='{tooltip}'>{tag}</span>"
                    html += "</span></li>"
                html += "</ul>"
            
            if "rewards" in quest_data and quest_data["rewards"]:
                html += "<h3>Rewards:</h3>"
                html += "<ul>"
                for reward in quest_data["rewards"]:
                    html += f"<li style='color: {COLOR_ACCENT_GREEN};'>{reward}</li>"
                html += "</ul>"
            
            if "notes" in quest_data and quest_data["notes"]:
                html += "<h3>Notes:</h3>"
                html += f"<p>{quest_data['notes']}</p>"
            
            self.quest_details.setHtml(html)

    def _get_current_quest_status(self) -> Optional[str]:
        """Get the currently selected quest status tab."""
        current_tab_index = self.quest_status_tabs.currentIndex()
        if current_tab_index == 0:
            return "active"
        elif current_tab_index == 1:
            return "completed"
        elif current_tab_index == 2:
            return "failed"
        return None
    
    def _on_note_selected(self, item: QListWidgetItem):
        """Handle note selection."""
        # Get the note index from the item
        note_index = item.data(Qt.UserRole)
        
        # Enable delete and save buttons
        self.delete_note_button.setEnabled(True)
        self.save_note_button.setEnabled(True)
        
        # Get the note data
        if 0 <= note_index < len(self.journal_data["notes"]):
            note_data = self.journal_data["notes"][note_index]
            
            # Update note editor
            self.note_editor.setPlainText(note_data["content"])
            
            # Store the current note index
            self.note_editor.setProperty("note_index", note_index)
    
    def _on_note_text_changed(self):
        """Handle note text changes."""
        # Enable the save button if there is text
        self.save_note_button.setEnabled(bool(self.note_editor.toPlainText()))
    
    def _on_new_note_clicked(self):
        """Handle new note button click."""
        # Create a new note with a timestamp
        from datetime import datetime
        
        # Create new note with current time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_note = {
            "title": f"Note {len(self.journal_data['notes']) + 1}",
            "timestamp": timestamp,
            "content": ""
        }
        
        # Add to journal data
        self.journal_data["notes"].append(new_note)
        
        # Add to list
        self._update_notes_list()
        
        # Select the new note
        self.notes_list.setCurrentRow(len(self.journal_data["notes"]) - 1)
        
        # Set focus to the editor
        self.note_editor.clear()
        self.note_editor.setFocus()
        
        # Store the current note index
        self.note_editor.setProperty("note_index", len(self.journal_data["notes"]) - 1)
        
        # Enable delete and save buttons
        self.delete_note_button.setEnabled(True)
        self.save_note_button.setEnabled(False)
    
    def _on_delete_note_clicked(self):
        """Handle delete note button click."""
        # Get the current note index
        note_index = self.note_editor.property("note_index")
        
        if note_index is not None and 0 <= note_index < len(self.journal_data["notes"]):
            # Remove from journal data
            self.journal_data["notes"].pop(note_index)
            
            # Update list
            self._update_notes_list()
            
            # Clear editor
            self.note_editor.clear()
            self.note_editor.setProperty("note_index", None)
            
            # Disable delete and save buttons
            self.delete_note_button.setEnabled(False)
            self.save_note_button.setEnabled(False)
            
            # Emit journal updated signal
            self._emit_journal_updated()
    
    def _on_save_note_clicked(self):
        """Handle save note button click."""
        # Get the current note index
        note_index = self.note_editor.property("note_index")
        
        if note_index is not None and 0 <= note_index < len(self.journal_data["notes"]):
            # Update note content
            self.journal_data["notes"][note_index]["content"] = self.note_editor.toPlainText()
            
            # Update the list item title (first line of content)
            content = self.note_editor.toPlainText()
            first_line = content.split("\n")[0][:30]
            if len(first_line) < len(content.split("\n")[0]):
                first_line += "..."
            
            self.journal_data["notes"][note_index]["title"] = first_line
            
            # Update list
            self._update_notes_list()
            
            # Reselect the note
            self.notes_list.setCurrentRow(note_index)
            
            # Emit journal updated signal
            self._emit_journal_updated()
    
    def _update_notes_list(self):
        """Update the notes list with current journal data.
        
        This list is intended to show only the user's free-form journal notes.
        Structured entries (e.g., objective notes saved with _type="objective_note")
        may be present in journal_data["notes"], but they don't have 'title'/'timestamp'.
        We skip any entries missing those keys to avoid KeyError and to keep the
        list focused.
        """
        # Save the currently selected row
        current_row = self.notes_list.currentRow()
        
        # Clear the list
        self.notes_list.clear()
        
        # Add notes to the list (only those with required fields)
        for i, note in enumerate(self.journal_data.get("notes", [])):
            title = note.get("title")
            timestamp = note.get("timestamp")
            if title is None or timestamp is None:
                # Skip structured notes (like objective notes) or malformed entries
                continue
            # Create list item
            item = QListWidgetItem(f"{title} - {timestamp}")
            item.setData(Qt.UserRole, i)
            
            # Add to list
            self.notes_list.addItem(item)
        
        # Restore selection if possible
        if 0 <= current_row < self.notes_list.count():
            self.notes_list.setCurrentRow(current_row)
    
    def _update_quests_lists(self):
        """Update the quest lists with current journal data."""
        # Save the currently selected items
        active_item = self.active_quests_list.currentItem()
        active_quest_id = active_item.data(Qt.UserRole) if active_item else None
        
        completed_item = self.completed_quests_list.currentItem()
        completed_quest_id = completed_item.data(Qt.UserRole) if completed_item else None
        
        failed_item = self.failed_quests_list.currentItem()
        failed_quest_id = failed_item.data(Qt.UserRole) if failed_item else None
        
        # Clear the lists
        self.active_quests_list.clear()
        self.completed_quests_list.clear()
        self.failed_quests_list.clear()
        
        # Add quests to the appropriate lists
        for quest_id, quest_data in self.journal_data["quests"].items():
            # Determine status: completed tab only if ALL mandatory objectives completed and none failed
            status = quest_data.get("status", "active")
            objectives = quest_data.get("objectives", [])
            mandatory_total = sum(1 for o in objectives if o.get('mandatory', True)) or 0
            mandatory_completed = sum(1 for o in objectives if o.get('mandatory', True) and o.get('completed', False))
            any_failed = any(o.get('failed', False) for o in objectives)
            fully_completed = (mandatory_total == mandatory_completed) and not any_failed
            if quest_data.get("abandoned"):
                status = "failed"
            elif fully_completed:
                status = "completed"
            elif any_failed:
                # Keep as active unless all failed or explicit fail policy
                status = "active"

            # Create list item (append ABANDONED suffix if applicable)
            base_title = quest_data.get("title", quest_id)
            if quest_data.get("abandoned") and status == "failed":
                base_title += " (ABANDONED)"
            item = QListWidgetItem(base_title)
            item.setData(Qt.UserRole, quest_id)
            
            # Add to the appropriate list based on status
            if status == "active":
                self.active_quests_list.addItem(item)
            elif status == "completed":
                self.completed_quests_list.addItem(item)
            elif status == "failed":
                self.failed_quests_list.addItem(item)
        
        # Restore selections if possible
        if active_quest_id:
            for i in range(self.active_quests_list.count()):
                if self.active_quests_list.item(i).data(Qt.UserRole) == active_quest_id:
                    self.active_quests_list.setCurrentRow(i)
                    break
        
        if completed_quest_id:
            for i in range(self.completed_quests_list.count()):
                if self.completed_quests_list.item(i).data(Qt.UserRole) == completed_quest_id:
                    self.completed_quests_list.setCurrentRow(i)
                    break
        
        if failed_quest_id:
            for i in range(self.failed_quests_list.count()):
                if self.failed_quests_list.item(i).data(Qt.UserRole) == failed_quest_id:
                    self.failed_quests_list.setCurrentRow(i)
                    break
    
    def _emit_journal_updated(self):
        """Emit the journal updated signal."""
        self.journal_updated.emit(self.journal_data)

    def clear_all(self):
        """Clear all journal UI content to a blank state (used before loading a save)."""
        self.journal_data = {"character": "", "quests": {}, "notes": []}
        self.character_info_editor.clear()
        self.active_quests_list.clear()
        self.completed_quests_list.clear()
        self.failed_quests_list.clear()
        self.quest_details.clear()
        self.notes_list.clear()

    def _show_active_context_menu(self, pos):
        """Show context menu for active quest list to manage objectives and notes."""
        item = self.active_quests_list.itemAt(pos)
        if not item:
            return
        quest_id = item.data(Qt.UserRole)
        quest = self.journal_data.get("quests", {}).get(quest_id)
        if not quest:
            return
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        main_win = self.window()
        if hasattr(main_win, 'link_cursor'):
            menu.setCursor(main_win.link_cursor)

        menu.setStyleSheet(f"""
            QMenu {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_BG_MEDIUM}, stop:1 {COLOR_BG_DARK});
                color: {COLOR_TEXT_SECONDARY};
                border: 2px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 4px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: 6px 20px 6px 12px;
                border-radius: 2px;
            }}
            QMenu::item:selected {{
                background-color: {COLOR_SELECTED};
                color: {COLOR_TEXT_SECONDARY};
            }}
            QMenu::separator {{
                height: 2px;
                background: {COLOR_BORDER};
                margin: 4px 6px;
            }}
        """)
        complete_sub = menu.addMenu("Mark Objective as Completed")
        fail_sub = menu.addMenu("Mark Objective as Failed")
        notes_sub = menu.addMenu("See Notes for Objective")
        submenu_style = menu.styleSheet()
        complete_sub.setStyleSheet(submenu_style)
        fail_sub.setStyleSheet(submenu_style)
        notes_sub.setStyleSheet(submenu_style)
        menu.addSeparator()
        abandon_action = menu.addAction("Abandon Quest")
        abandon_action.triggered.connect(lambda: self._abandon_quest(quest_id))
        menu.addSeparator()
        dev_complete = menu.addAction("(dev) Mark Quest Completed")
        dev_failed = menu.addAction("(dev) Mark Quest Failed")
        dev_complete.triggered.connect(lambda: self._mark_quest_status(quest_id, "completed"))
        dev_failed.triggered.connect(lambda: self._mark_quest_status(quest_id, "failed"))
        
        def add_actions_for_objectives(submenu, handler):
            for obj in quest.get("objectives", []):
                obj_id = obj.get("id")
                desc = obj.get("description", obj_id)
                act = submenu.addAction(desc)
                act.triggered.connect(lambda checked=False, qid=quest_id, oid=obj_id: handler(qid, oid))
        add_actions_for_objectives(complete_sub, self._mark_objective_completed)
        add_actions_for_objectives(fail_sub, self._mark_objective_failed)
        add_actions_for_objectives(notes_sub, self._open_objective_notes)
        menu.exec(self.active_quests_list.mapToGlobal(pos))

    def _mark_objective_completed(self, quest_id: str, objective_id: str):
        q = self.journal_data.get("quests", {}).get(quest_id)
        if not q:
            return
        for o in q.get("objectives", []):
            if o.get("id") == objective_id:
                o["completed"] = True
                o["failed"] = False
                break
        # Refresh details view to update colors/strikethrough
        self._update_quests_lists()
        self._refresh_current_quest_details(quest_id)
        self._emit_journal_updated()

    def _mark_objective_failed(self, quest_id: str, objective_id: str):
        q = self.journal_data.get("quests", {}).get(quest_id)
        if not q:
            return
        for o in q.get("objectives", []):
            if o.get("id") == objective_id:
                o["failed"] = True
                o["completed"] = False
                break
        # Refresh details view to update colors/strikethrough
        self._update_quests_lists()
        self._refresh_current_quest_details(quest_id)
        self._emit_journal_updated()

    def _open_objective_notes(self, quest_id: str, objective_id: str):
        # Minimal inline notes implementation: store under journal["notes"] as structured entries
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Objective Notes")
        layout = QVBoxLayout(dlg)
        editor = QTextEdit()
        # Load existing note if present
        notes_key = (quest_id, objective_id)
        existing = None
        if isinstance(self.journal_data.get("notes"), list):
            for n in self.journal_data["notes"]:
                if n.get("_type") == "objective_note" and n.get("quest_id") == quest_id and n.get("objective_id") == objective_id:
                    existing = n
                    break
        if existing:
            editor.setPlainText(existing.get("content", ""))
        layout.addWidget(editor)
        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        close_btn = QPushButton("Close")
        btns.addWidget(save_btn)
        btns.addStretch()
        btns.addWidget(close_btn)
        layout.addLayout(btns)
        
        def _save():
            content = editor.toPlainText()
            # Update or append note
            if existing:
                existing["content"] = content
            else:
                self.journal_data.setdefault("notes", []).append({
                    "_type": "objective_note",
                    "quest_id": quest_id,
                    "objective_id": objective_id,
                    "content": content,
                })
            self._emit_journal_updated()
            dlg.accept()
        save_btn.clicked.connect(_save)
        close_btn.clicked.connect(dlg.reject)
        dlg.exec()
    
    def _show_notes_only_context_menu(self, list_widget: QListWidget, pos):
        """Show a notes-only context menu for Completed/Failed lists."""
        item = list_widget.itemAt(pos)
        if not item:
            return
        quest_id = item.data(Qt.UserRole)
        quest = self.journal_data.get("quests", {}).get(quest_id)
        if not quest:
            return
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_BG_MEDIUM}, stop:1 {COLOR_BG_DARK});
                color: {COLOR_TEXT_SECONDARY};
                border: 2px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 12px;
                border-radius: 2px;
            }}
            QMenu::item:selected {{
                background-color: {COLOR_SELECTED};
            }}
            QMenu::separator {{
                height: 2px;
                background: {COLOR_BORDER};
                margin: 4px 6px;
            }}
        """)
        notes_sub = menu.addMenu("See Notes for Objective")
        existing_obj_notes = set()
        try:
            for n in self.journal_data.get("notes", []):
                if n.get("_type") == "objective_note" and n.get("quest_id") == quest_id:
                    content = n.get("content", "")
                    if isinstance(content, str) and content.strip():
                        existing_obj_notes.add(n.get("objective_id"))
        except Exception:
            pass
        
        from PySide6.QtGui import QAction
        any_clickable = False
        for obj in quest.get("objectives", []):
            obj_id = obj.get("id")
            desc = obj.get("description", obj_id)
            if obj_id in existing_obj_notes:
                act = notes_sub.addAction(desc)
                act.triggered.connect(lambda checked=False, qid=quest_id, oid=obj_id: self._open_objective_notes(qid, oid))
                any_clickable = True
            else:
                text_act = QAction(desc, notes_sub)
                text_act.setEnabled(False)
                notes_sub.addAction(text_act)
        if not any_clickable:
            placeholder = QAction("No notes available", notes_sub)
            placeholder.setEnabled(False)
            notes_sub.addAction(placeholder)
        menu.exec(list_widget.mapToGlobal(pos))
         
    def _mark_quest_status(self, quest_id: str, status: str):
        """Developer helper to set a quest's status directly (completed/failed)."""
        q = self.journal_data.get("quests", {}).get(quest_id)
        if not q:
            return
        if status == "completed":
            for o in q.get("objectives", []):
                if o.get("mandatory", True):
                    o["completed"] = True
                    o["failed"] = False
            q["status"] = "completed"
            q.pop("abandoned", None)
        elif status == "failed":
            # Mark as failed without changing individual objectives
            q["status"] = "failed"
            q.pop("abandoned", None)
        self._update_quests_lists()
        self._refresh_current_quest_details(quest_id)
        self._emit_journal_updated()

    def _abandon_quest(self, quest_id: str):
        """Abandon a quest after user confirmation: moves it to Failed and flags as abandoned."""
        from PySide6.QtWidgets import QMessageBox
        q = self.journal_data.get("quests", {}).get(quest_id)
        if not q:
            return
        title = q.get("title", quest_id)
        reply = QMessageBox.question(
            self,
            "Abandon Quest",
            f"Are you sure you want to abandon '{title}'? This will move it to Failed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            q["status"] = "failed"
            q["abandoned"] = True
            self._update_quests_lists()
            self._refresh_current_quest_details(quest_id)
            self._emit_journal_updated()
    
    def _refresh_current_quest_details(self, quest_id: str):
        """If the provided quest_id is currently selected in any tab, rebuild its details HTML.
        This ensures the colors for completed/failed objectives refresh immediately.
        """
        # Determine which list contains the quest
        for lst in (self.active_quests_list, self.completed_quests_list, self.failed_quests_list):
            for i in range(lst.count()):
                it = lst.item(i)
                if it.data(Qt.UserRole) == quest_id and it.isSelected():
                    # Rebuild by calling the selection handler
                    self._on_quest_selected(it)
                    return

    def update_journal(self, journal_data: Dict[str, Any] = None):
        """
        Update the journal panel with journal data.
        
        Args:
            journal_data: The journal data to display.
        """
        # If no journal data is provided, use the current state
        if journal_data is None:
            if self.state_manager and self.state_manager.current_state:
                if hasattr(self.state_manager.current_state, "journal"):
                    journal_data = self.state_manager.current_state.journal
                else:
                    logging.warning("No journal data available to update journal panel")
                    return
            else:
                logging.warning("No state available to update journal panel")
                return
        
        # Update journal data
        self.journal_data = journal_data
        
        # Update character info
        self.character_info_editor.setPlainText(journal_data.get("character", ""))
        
        # Update quests lists
        self._update_quests_lists()
        # If a quest is selected, refresh its details to ensure colors/styles render
        cur = self.active_quests_list.currentItem() or self.completed_quests_list.currentItem() or self.failed_quests_list.currentItem()
        if cur:
            self._on_quest_selected(cur)
        else:
            self.quest_details.clear()
        
        # Update notes list
        self._update_notes_list()
