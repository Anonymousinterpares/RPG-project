"""
History editor component for the World Configurator Tool.
"""

from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QSpinBox,
    QDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)

from ui.dialogs.base_dialog import BaseDialog
from models.base_models import WorldHistory, Era, HistoricalEvent
from models.world_data import WorldHistoryManager
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.ui.history_editor")

class EventDialog(BaseDialog):
    """Dialog for editing a historical event."""
    
    def __init__(self, parent=None, event: Optional[HistoricalEvent] = None,
                 affected_cultures: Optional[Dict[str, str]] = None,
                 affected_locations: Optional[Dict[str, str]] = None):
        """
        Initialize the event edit dialog.
        
        Args:
            parent: The parent widget.
            event: Optional existing event to edit.
            affected_cultures: Dictionary of culture IDs to names.
            affected_locations: Dictionary of location IDs to names.
        """
        super().__init__(parent)
        self.setWindowTitle("Historical Event")
        self.setMinimumWidth(500)
        
        # Event to edit
        self.event = event or HistoricalEvent(0, "", "")
        
        # Available selections
        self.affected_cultures = affected_cultures or {}
        self.affected_locations = affected_locations or {}
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Year field
        self.year_spin = QSpinBox()
        self.year_spin.setRange(-10000, 10000)
        self.year_spin.setValue(self.event.year)
        form.addRow("Year:", self.year_spin)
        
        # Title field
        self.title_edit = QLineEdit(self.event.title)
        form.addRow("Title:", self.title_edit)
        
        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.event.description)
        self.desc_edit.setMinimumHeight(100)
        form.addRow("Description:", self.desc_edit)
        
        # Significance field
        self.significance_edit = QTextEdit()
        self.significance_edit.setPlainText(self.event.significance)
        self.significance_edit.setMaximumHeight(60)
        form.addRow("Significance:", self.significance_edit)
        
        layout.addLayout(form)
        
        # Affected cultures
        cultures_group = QGroupBox("Affected Cultures")
        cultures_layout = QVBoxLayout(cultures_group)
        
        self.cultures_list = QListWidget()
        self.cultures_list.setSelectionMode(QListWidget.MultiSelection)
        cultures_layout.addWidget(self.cultures_list)
        
        # Add cultures to the list
        for culture_id, culture_name in self.affected_cultures.items():
            item = QListWidgetItem(culture_name)
            item.setData(Qt.UserRole, culture_id)
            self.cultures_list.addItem(item)
            
            # Select the item if it's in the event's affected cultures
            if culture_id in self.event.affected_cultures:
                item.setSelected(True)
        
        layout.addWidget(cultures_group)
        
        # Affected locations
        locations_group = QGroupBox("Affected Locations")
        locations_layout = QVBoxLayout(locations_group)
        
        self.locations_list = QListWidget()
        self.locations_list.setSelectionMode(QListWidget.MultiSelection)
        locations_layout.addWidget(self.locations_list)
        
        # Add locations to the list
        for location_id, location_name in self.affected_locations.items():
            item = QListWidgetItem(location_name)
            item.setData(Qt.UserRole, location_id)
            self.locations_list.addItem(item)
            
            # Select the item if it's in the event's affected locations
            if location_id in self.event.affected_locations:
                item.setSelected(True)
        
        layout.addWidget(locations_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
    
    def get_event(self) -> HistoricalEvent:
        """Get the edited event."""
        self.event.year = self.year_spin.value()
        self.event.title = self.title_edit.text()
        self.event.description = self.desc_edit.toPlainText()
        self.event.significance = self.significance_edit.toPlainText()
        
        # Update affected cultures
        self.event.affected_cultures = []
        for i in range(self.cultures_list.count()):
            item = self.cultures_list.item(i)
            if item.isSelected():
                self.event.affected_cultures.append(item.data(Qt.UserRole))
        
        # Update affected locations
        self.event.affected_locations = []
        for i in range(self.locations_list.count()):
            item = self.locations_list.item(i)
            if item.isSelected():
                self.event.affected_locations.append(item.data(Qt.UserRole))
        
        return self.event

class EraDialog(QDialog):
    """Dialog for editing a historical era."""
    
    def __init__(self, parent=None, era: Optional[Era] = None, event_dialog_factory=None):
        """
        Initialize the era edit dialog.
        
        Args:
            parent: The parent widget.
            era: Optional existing era to edit.
            event_dialog_factory: Function to create an event dialog.
        """
        super().__init__(parent)
        self.setWindowTitle("Historical Era")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # Era to edit
        self.era = era or Era("", 0, 0, "")
        
        # Event dialog factory
        self.event_dialog_factory = event_dialog_factory or (lambda event: EventDialog(self, event))
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for basic fields
        form = QFormLayout()
        
        # Name field
        self.name_edit = QLineEdit(self.era.name)
        form.addRow("Name:", self.name_edit)
        
        # Year fields
        years_layout = QHBoxLayout()
        
        self.start_year_spin = QSpinBox()
        self.start_year_spin.setRange(-10000, 10000)
        self.start_year_spin.setValue(self.era.start_year)
        years_layout.addWidget(QLabel("Start Year:"))
        years_layout.addWidget(self.start_year_spin)
        
        self.end_year_spin = QSpinBox()
        self.end_year_spin.setRange(-10000, 10000)
        self.end_year_spin.setValue(self.era.end_year)
        years_layout.addWidget(QLabel("End Year:"))
        years_layout.addWidget(self.end_year_spin)
        
        form.addRow("Years:", years_layout)
        
        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.era.description)
        self.desc_edit.setMinimumHeight(80)
        form.addRow("Description:", self.desc_edit)
        
        layout.addLayout(form)
        
        # Events section
        events_group = QGroupBox("Historical Events")
        events_layout = QVBoxLayout(events_group)
        
        # Events table
        self.events_table = QTableWidget(0, 2)  # 2 columns: Year and Title
        self.events_table.setHorizontalHeaderLabels(["Year", "Title"])
        self.events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.events_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.events_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.events_table.setSelectionMode(QTableWidget.SingleSelection)
        self.events_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.events_table.doubleClicked.connect(self._edit_event)
        
        # Add events to the table
        self._refresh_events_table()
        
        events_layout.addWidget(self.events_table)
        
        # Event buttons
        event_buttons = QHBoxLayout()
        
        self.add_event_btn = QPushButton("Add Event")
        self.add_event_btn.clicked.connect(self._add_event)
        event_buttons.addWidget(self.add_event_btn)
        
        self.edit_event_btn = QPushButton("Edit Event")
        self.edit_event_btn.clicked.connect(lambda: self._edit_event(None))
        event_buttons.addWidget(self.edit_event_btn)
        
        self.remove_event_btn = QPushButton("Remove Event")
        self.remove_event_btn.clicked.connect(self._remove_event)
        event_buttons.addWidget(self.remove_event_btn)
        
        events_layout.addLayout(event_buttons)
        
        layout.addWidget(events_group)
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
    
    def _refresh_events_table(self):
        """Refresh the events table."""
        self.events_table.setRowCount(0)
        
        for i, event in enumerate(sorted(self.era.events, key=lambda e: e.year)):
            self.events_table.insertRow(i)
            
            year_item = QTableWidgetItem(str(event.year))
            year_item.setData(Qt.UserRole, event)
            self.events_table.setItem(i, 0, year_item)
            
            title_item = QTableWidgetItem(event.title)
            self.events_table.setItem(i, 1, title_item)
    
    def _add_event(self):
        """Add a new event to the era."""
        # Create a new event with the era's start year as default
        event = HistoricalEvent(self.start_year_spin.value(), "New Event", "")
        
        # Show the event dialog
        dialog = self.event_dialog_factory(event)
        
        if dialog.exec() == QDialog.Accepted:
            # Get the event from the dialog
            event = dialog.get_event()
            
            # Add to era's events
            self.era.events.append(event)
            
            # Refresh the table
            self._refresh_events_table()
    
    def _edit_event(self, index=None):
        """Edit an event in the era."""
        # Get the selected event
        if index and index.isValid():
            row = index.row()
        else:
            rows = self.events_table.selectionModel().selectedRows()
            if not rows:
                return
            row = rows[0].row()
        
        # Get the event from the first column
        event = self.events_table.item(row, 0).data(Qt.UserRole)
        
        # Show the event dialog
        dialog = self.event_dialog_factory(event)
        
        if dialog.exec() == QDialog.Accepted:
            # Get the updated event
            updated_event = dialog.get_event()
            
            # Find and update the event in the era
            for i, e in enumerate(self.era.events):
                if e is event:  # Check identity, not just equality
                    self.era.events[i] = updated_event
                    break
            
            # Refresh the table
            self._refresh_events_table()
    
    def _remove_event(self):
        """Remove an event from the era."""
        # Get the selected event
        rows = self.events_table.selectionModel().selectedRows()
        if not rows:
            return
        
        row = rows[0].row()
        event = self.events_table.item(row, 0).data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the event '{event.title}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove from era's events
        self.era.events.remove(event)
        
        # Refresh the table
        self._refresh_events_table()
    
    def get_era(self) -> Era:
        """Get the edited era."""
        self.era.name = self.name_edit.text()
        self.era.start_year = self.start_year_spin.value()
        self.era.end_year = self.end_year_spin.value()
        self.era.description = self.desc_edit.toPlainText()
        
        return self.era

class HistoryEditor(QWidget):
    """History editor component."""
    
    # Signals
    history_modified = Signal()
    
    def __init__(self, parent=None):
        """
        Initialize the history editor.
        
        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        
        # Internal state
        self.history_manager = WorldHistoryManager()
        self.culture_manager = None
        self.location_manager = None
        self.current_history: Optional[WorldHistory] = None
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the editor UI."""
        main_layout = QVBoxLayout(self)
        
        # World history details section
        details_group = QGroupBox("World History Details")
        details_layout = QFormLayout(details_group)
        
        # World name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter world name")
        self.name_edit.textChanged.connect(self._on_field_changed)
        details_layout.addRow("World Name:", self.name_edit)
        
        # Description
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Enter world description")
        self.desc_edit.textChanged.connect(self._on_field_changed)
        self.desc_edit.setMaximumHeight(80)
        details_layout.addRow("Description:", self.desc_edit)
        
        # Current year
        self.year_spin = QSpinBox()
        self.year_spin.setRange(-10000, 10000)
        self.year_spin.valueChanged.connect(self._on_field_changed)
        details_layout.addRow("Current Year:", self.year_spin)
        
        main_layout.addWidget(details_group)
        
        # Eras section
        eras_group = QGroupBox("Historical Eras")
        eras_layout = QVBoxLayout(eras_group)
        
        # Eras table
        self.eras_table = QTableWidget(0, 3)  # 3 columns: Name, Period, Description
        self.eras_table.setHorizontalHeaderLabels(["Name", "Period", "Description"])
        self.eras_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.eras_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.eras_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.eras_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.eras_table.setSelectionMode(QTableWidget.SingleSelection)
        self.eras_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.eras_table.doubleClicked.connect(self._edit_era)
        eras_layout.addWidget(self.eras_table)
        
        # Eras buttons
        era_buttons = QHBoxLayout()
        
        self.add_era_btn = QPushButton("Add Era")
        self.add_era_btn.clicked.connect(self._add_era)
        era_buttons.addWidget(self.add_era_btn)
        
        self.edit_era_btn = QPushButton("Edit Era")
        self.edit_era_btn.clicked.connect(lambda: self._edit_era(None))
        era_buttons.addWidget(self.edit_era_btn)
        
        self.remove_era_btn = QPushButton("Remove Era")
        self.remove_era_btn.clicked.connect(self._remove_era)
        era_buttons.addWidget(self.remove_era_btn)
        
        eras_layout.addLayout(era_buttons)
        
        main_layout.addWidget(eras_group)
        
        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current_history)
        self.save_btn.setEnabled(False)
        save_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(save_layout)
        
        # Set up initial state
        self._disable_details()
    
    def set_managers(self, history_manager: WorldHistoryManager, 
                    culture_manager=None, location_manager=None) -> None:
        """
        Set the managers to use.
        
        Args:
            history_manager: The history manager.
            culture_manager: Optional culture manager for references.
            location_manager: Optional location manager for references.
        """
        self.history_manager = history_manager
        self.culture_manager = culture_manager
        self.location_manager = location_manager
        self.refresh()
    
    def refresh(self) -> None:
        """Refresh the editor from the manager."""
        # Check if there's a history to load
        if self.history_manager.history:
            self._load_history(self.history_manager.history)
        else:
            # Create a default history if none exists
            if QMessageBox.question(
                self,
                "No World History",
                "No world history found. Would you like to create a new one?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            ) == QMessageBox.Yes:
                self.history_manager.create_new_history("New World", "Description of your world", 1000)
                self._load_history(self.history_manager.history)
            else:
                self._disable_details()
    
    def _load_history(self, history: WorldHistory) -> None:
        """
        Load a world history into the editor.
        
        Args:
            history: The world history to load.
        """
        try:
            self.current_history = history
            
            # Set form values
            self.name_edit.setText(history.name)
            self.desc_edit.setPlainText(history.description)
            self.year_spin.setValue(history.current_year)
            
            # Load eras
            self._refresh_eras_table()
            
            # Enable controls
            self._enable_details()
            self.save_btn.setEnabled(False)  # Initially not modified
            
        except Exception as e:
            logger.error(f"Error loading history: {str(e)}")
            QMessageBox.warning(
                self,
                "Error Loading History",
                f"There was an error loading the world history:\n\n{str(e)}\n\nSome data may not be displayed correctly."
            )
            # Still enable the editor to allow fixing the issue
            self._enable_details()
            self.save_btn.setEnabled(True)  # Enable saving to fix issues
    
    def _refresh_eras_table(self):
        """Refresh the eras table."""
        self.eras_table.setRowCount(0)
        
        if not self.current_history:
            return
        
        for i, era in enumerate(sorted(self.current_history.eras, key=lambda e: e.start_year)):
            self.eras_table.insertRow(i)
            
            name_item = QTableWidgetItem(era.name)
            name_item.setData(Qt.UserRole, era)
            self.eras_table.setItem(i, 0, name_item)
            
            period_item = QTableWidgetItem(f"{era.start_year} to {era.end_year}")
            self.eras_table.setItem(i, 1, period_item)
            
            desc_item = QTableWidgetItem(era.description[:100] + ("..." if len(era.description) > 100 else ""))
            self.eras_table.setItem(i, 2, desc_item)
    
    def _disable_details(self) -> None:
        """Disable all detail controls."""
        self.current_history = None
        
        self.name_edit.clear()
        self.desc_edit.clear()
        self.year_spin.setValue(0)
        
        self.eras_table.setRowCount(0)
        
        self.name_edit.setEnabled(False)
        self.desc_edit.setEnabled(False)
        self.year_spin.setEnabled(False)
        
        self.eras_table.setEnabled(False)
        
        self.add_era_btn.setEnabled(False)
        self.edit_era_btn.setEnabled(False)
        self.remove_era_btn.setEnabled(False)
        
        self.save_btn.setEnabled(False)
    
    def _enable_details(self) -> None:
        """Enable all detail controls."""
        self.name_edit.setEnabled(True)
        self.desc_edit.setEnabled(True)
        self.year_spin.setEnabled(True)
        
        self.eras_table.setEnabled(True)
        
        self.add_era_btn.setEnabled(True)
        self.edit_era_btn.setEnabled(True)
        self.remove_era_btn.setEnabled(True)
    
    def _on_field_changed(self) -> None:
        """Handle field value changes."""
        if self.current_history:
            self.save_btn.setEnabled(True)
    
    def _save_current_history(self) -> None:
        """Save the current history to the manager."""
        if not self.current_history:
            return
        
        # Update history from form
        self.current_history.name = self.name_edit.text()
        self.current_history.description = self.desc_edit.toPlainText()
        self.current_history.current_year = self.year_spin.value()
        
        # Update history in manager
        self.history_manager.history = self.current_history
        self.history_manager.state.modified = True
        
        # Mark as saved
        self.save_btn.setEnabled(False)
        
        # Emit modified signal
        self.history_modified.emit()
        
        # Log
        logger.info(f"Saved world history: {self.current_history.name}")
    
    def _create_event_dialog(self, event: Optional[HistoricalEvent] = None) -> EventDialog:
        """
        Create an event dialog with the current cultures and locations.
        
        Args:
            event: Optional event to edit.
        
        Returns:
            The event dialog.
        """
        cultures = {}
        locations = {}
        
        # Add cultures if available
        if self.culture_manager:
            for culture_id, culture in self.culture_manager.cultures.items():
                cultures[culture_id] = culture.name
        
        # Add locations if available
        if self.location_manager:
            for location_id, location in self.location_manager.locations.items():
                locations[location_id] = location.name
        
        # Create and return the dialog
        return EventDialog(self, event, cultures, locations)
    
    def _add_era(self) -> None:
        """Add a new era to the history."""
        if not self.current_history:
            return
        
        # Create a new era
        era = Era("New Era", 0, 100, "Description of the era")
        
        # Show the era dialog
        dialog = EraDialog(self, era, self._create_event_dialog)
        
        if dialog.exec() == QDialog.Accepted:
            # Get the era from the dialog
            era = dialog.get_era()
            
            # Add to history's eras
            self.current_history.eras.append(era)
            
            # Refresh the table
            self._refresh_eras_table()
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Added era: {era.name}")
    
    def _edit_era(self, index=None) -> None:
        """
        Edit an era in the history.
        
        Args:
            index: The model index of the item to edit, or None.
        """
        if not self.current_history:
            return
        
        # Get the selected era
        if index and index.isValid():
            row = index.row()
        else:
            rows = self.eras_table.selectionModel().selectedRows()
            if not rows:
                return
            row = rows[0].row()
        
        # Get the era from the first column
        era = self.eras_table.item(row, 0).data(Qt.UserRole)
        
        # Show the era dialog
        dialog = EraDialog(self, era, self._create_event_dialog)
        
        if dialog.exec() == QDialog.Accepted:
            # Get the updated era
            updated_era = dialog.get_era()
            
            # Find and update the era in the history
            for i, e in enumerate(self.current_history.eras):
                if e is era:  # Check identity, not just equality
                    self.current_history.eras[i] = updated_era
                    break
            
            # Refresh the table
            self._refresh_eras_table()
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Edited era: {updated_era.name}")
    
    def _remove_era(self) -> None:
        """Remove an era from the history."""
        if not self.current_history:
            return
        
        # Get the selected era
        rows = self.eras_table.selectionModel().selectedRows()
        if not rows:
            return
        
        row = rows[0].row()
        era = self.eras_table.item(row, 0).data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the era '{era.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove from history's eras
        self.current_history.eras.remove(era)
        
        # Refresh the table
        self._refresh_eras_table()
        
        # Mark as modified
        self.save_btn.setEnabled(True)
        
        # Log
        logger.debug(f"Removed era: {era.name}")
