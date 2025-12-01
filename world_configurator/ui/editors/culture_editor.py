"""
Culture editor component for the World Configurator Tool.
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QSpinBox,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame
)

from models.base_models import Culture, CultureValue, Tradition
from models.world_data import CultureManager
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.ui.culture_editor")

class ValueDialog(QDialog):
    """Dialog for editing a cultural value."""
    
    def __init__(self, parent=None, value: Optional[CultureValue] = None):
        """
        Initialize the value edit dialog.
        
        Args:
            parent: The parent widget.
            value: Optional existing value to edit.
        """
        super().__init__(parent)
        self.setWindowTitle("Cultural Value")
        self.setMinimumWidth(400)
        
        # Value to edit
        self.value = value or CultureValue("", "")
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Name field
        self.name_edit = QLineEdit(self.value.name)
        form.addRow("Name:", self.name_edit)
        
        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.value.description)
        self.desc_edit.setMinimumHeight(100)
        form.addRow("Description:", self.desc_edit)
        
        # Importance field
        self.importance_spin = QSpinBox()
        self.importance_spin.setRange(1, 10)
        self.importance_spin.setValue(self.value.importance)
        self.importance_spin.setToolTip("1 = Least important, 10 = Most important")
        form.addRow("Importance:", self.importance_spin)
        
        layout.addLayout(form)
        
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
    
    def get_value(self) -> CultureValue:
        """Get the edited value."""
        self.value.name = self.name_edit.text()
        self.value.description = self.desc_edit.toPlainText()
        self.value.importance = self.importance_spin.value()
        return self.value

class TraditionDialog(QDialog):
    """Dialog for editing a cultural tradition."""
    
    def __init__(self, parent=None, tradition: Optional[Tradition] = None):
        """
        Initialize the tradition edit dialog.
        
        Args:
            parent: The parent widget.
            tradition: Optional existing tradition to edit.
        """
        super().__init__(parent)
        self.setWindowTitle("Cultural Tradition")
        self.setMinimumWidth(400)
        
        # Tradition to edit
        self.tradition = tradition or Tradition("", "", "", "")
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Name field
        self.name_edit = QLineEdit(self.tradition.name)
        form.addRow("Name:", self.name_edit)
        
        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.tradition.description)
        self.desc_edit.setMinimumHeight(80)
        form.addRow("Description:", self.desc_edit)
        
        # Occasion field
        self.occasion_edit = QLineEdit(self.tradition.occasion)
        form.addRow("Occasion:", self.occasion_edit)
        
        # Significance field
        self.significance_edit = QTextEdit()
        self.significance_edit.setPlainText(self.tradition.significance)
        self.significance_edit.setMinimumHeight(80)
        form.addRow("Significance:", self.significance_edit)
        
        layout.addLayout(form)
        
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
    
    def get_tradition(self) -> Tradition:
        """Get the edited tradition."""
        self.tradition.name = self.name_edit.text()
        self.tradition.description = self.desc_edit.toPlainText()
        self.tradition.occasion = self.occasion_edit.text()
        self.tradition.significance = self.significance_edit.toPlainText()
        return self.tradition

class CultureEditor(QWidget):
    """Culture editor component."""
    
    # Signals
    culture_modified = Signal()
    
    def __init__(self, parent=None):
        """
        Initialize the culture editor.
        
        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        
        # Internal state
        self.culture_manager = CultureManager()
        self.current_culture: Optional[Culture] = None
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the editor UI."""
        main_layout = QHBoxLayout(self)
        
        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (culture list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = QLabel("Cultures")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(list_label)
        
        self.culture_list = QListWidget()
        self.culture_list.setMinimumWidth(200)
        self.culture_list.currentItemChanged.connect(self._on_culture_selected)
        left_layout.addWidget(self.culture_list)
        
        list_buttons = QHBoxLayout()
        
        self.add_culture_btn = QPushButton("Add")
        self.add_culture_btn.clicked.connect(self._add_culture)
        list_buttons.addWidget(self.add_culture_btn)
        
        self.remove_culture_btn = QPushButton("Remove")
        self.remove_culture_btn.clicked.connect(self._remove_culture)
        self.remove_culture_btn.setEnabled(False)
        list_buttons.addWidget(self.remove_culture_btn)
        
        left_layout.addLayout(list_buttons)
        
        # Add left panel to splitter
        splitter.addWidget(left_panel)
        
        # Right panel (culture details)
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setFrameShape(QFrame.NoFrame)
        
        self.details_widget = QWidget()
        right_panel.setWidget(self.details_widget)
        
        self.details_layout = QVBoxLayout(self.details_widget)
        
        # Culture details form
        self.form_layout = QFormLayout()
        
        # Culture name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter culture name")
        self.name_edit.textChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Name:", self.name_edit)
        
        # Culture description
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Enter culture description")
        self.desc_edit.textChanged.connect(self._on_field_changed)
        self.desc_edit.setMinimumHeight(100)
        self.form_layout.addRow("Description:", self.desc_edit)
        
        # Language style
        self.language_edit = QLineEdit()
        self.language_edit.setPlaceholderText("Describe the language style")
        self.language_edit.textChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Language Style:", self.language_edit)
        
        self.details_layout.addLayout(self.form_layout)
        
        # Values section
        values_label = QLabel("Cultural Values")
        values_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(values_label)
        
        self.values_list = QListWidget()
        self.values_list.setMinimumHeight(150)
        self.values_list.itemDoubleClicked.connect(self._edit_value)
        self.details_layout.addWidget(self.values_list)
        
        values_buttons = QHBoxLayout()
        
        self.add_value_btn = QPushButton("Add Value")
        self.add_value_btn.clicked.connect(self._add_value)
        values_buttons.addWidget(self.add_value_btn)
        
        self.edit_value_btn = QPushButton("Edit Value")
        self.edit_value_btn.clicked.connect(lambda: self._edit_value(self.values_list.currentItem()))
        values_buttons.addWidget(self.edit_value_btn)
        
        self.remove_value_btn = QPushButton("Remove Value")
        self.remove_value_btn.clicked.connect(self._remove_value)
        values_buttons.addWidget(self.remove_value_btn)
        
        self.details_layout.addLayout(values_buttons)
        
        # Traditions section
        traditions_label = QLabel("Cultural Traditions")
        traditions_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(traditions_label)
        
        self.traditions_list = QListWidget()
        self.traditions_list.setMinimumHeight(150)
        self.traditions_list.itemDoubleClicked.connect(self._edit_tradition)
        self.details_layout.addWidget(self.traditions_list)
        
        traditions_buttons = QHBoxLayout()
        
        self.add_tradition_btn = QPushButton("Add Tradition")
        self.add_tradition_btn.clicked.connect(self._add_tradition)
        traditions_buttons.addWidget(self.add_tradition_btn)
        
        self.edit_tradition_btn = QPushButton("Edit Tradition")
        self.edit_tradition_btn.clicked.connect(lambda: self._edit_tradition(self.traditions_list.currentItem()))
        traditions_buttons.addWidget(self.edit_tradition_btn)
        
        self.remove_tradition_btn = QPushButton("Remove Tradition")
        self.remove_tradition_btn.clicked.connect(self._remove_tradition)
        traditions_buttons.addWidget(self.remove_tradition_btn)
        
        self.details_layout.addLayout(traditions_buttons)
        
        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current_culture)
        self.save_btn.setEnabled(False)
        save_layout.addWidget(self.save_btn)
        
        self.details_layout.addLayout(save_layout)
        
        # Add right panel to splitter
        splitter.addWidget(right_panel)
        
        # Set up initial state
        self._disable_details()
        
        # Prioritize the details panel for resizing
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
    
    def set_culture_manager(self, manager: CultureManager) -> None:
        """
        Set the culture manager to use.
        
        Args:
            manager: The culture manager.
        """
        self.culture_manager = manager
        self._refresh_culture_list()
    
    def _refresh_culture_list(self) -> None:
        """Refresh the culture list from the manager."""
        # Clear list
        self.culture_list.clear()
        
        # Add all cultures
        for culture_id, culture in self.culture_manager.cultures.items():
            item = QListWidgetItem(culture.name)
            item.setData(Qt.UserRole, culture_id)
            self.culture_list.addItem(item)
        
        # Sort alphabetically
        self.culture_list.sortItems()
        
        # Select the first item if available
        if self.culture_list.count() > 0:
            self.culture_list.setCurrentRow(0)
    
    def _on_culture_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        """
        Handle culture selection change.
        
        Args:
            current: The current selected item, or None.
            previous: The previously selected item, or None.
        """
        if current:
            culture_id = current.data(Qt.UserRole)
            culture = self.culture_manager.get_culture(culture_id)
            
            if culture:
                self._load_culture(culture)
                self.remove_culture_btn.setEnabled(True)
                return
        
        # No valid selection
        self._disable_details()
        self.remove_culture_btn.setEnabled(False)
    
    def _load_culture(self, culture: Culture) -> None:
        """
        Load a culture into the editor.
        
        Args:
            culture: The culture to load.
        """
        try:
            self.current_culture = culture
            
            # Set form values
            self.name_edit.setText(culture.name)
            self.desc_edit.setPlainText(culture.description)
            self.language_edit.setText(culture.language_style)
            
            # Load values
            self.values_list.clear()
            for value in culture.values:
                # Ensure value is a CultureValue object
                if hasattr(value, 'name') and hasattr(value, 'importance'):
                    value_name = value.name
                    importance = value.importance
                elif isinstance(value, dict) and 'name' in value:
                    # Convert dict to CultureValue if needed
                    from world_configurator.models.base_models import CultureValue
                    value = CultureValue(
                        name=value.get('name', ''),
                        description=value.get('description', ''),
                        importance=value.get('importance', 5)
                    )
                    value_name = value.get('name', 'Unknown Value')
                    importance = value.get('importance', 5)
                else:
                    logger.warning(f"Skipping invalid value in culture {culture.name}: {value}")
                    continue
                    
                item = QListWidgetItem(f"{value_name} (Importance: {importance})")
                item.setData(Qt.UserRole, value)
                self.values_list.addItem(item)
            
            # Load traditions
            self.traditions_list.clear()
            for tradition in culture.traditions:
                # Ensure tradition is a Tradition object
                if hasattr(tradition, 'name'):
                    tradition_name = tradition.name
                elif isinstance(tradition, dict) and 'name' in tradition:
                    # Convert dict to Tradition if needed
                    from world_configurator.models.base_models import Tradition
                    tradition = Tradition(
                        name=tradition.get('name', ''),
                        description=tradition.get('description', ''),
                        occasion=tradition.get('occasion', ''),
                        significance=tradition.get('significance', '')
                    )
                    tradition_name = tradition.get('name', 'Unknown Tradition')
                else:
                    logger.warning(f"Skipping invalid tradition in culture {culture.name}: {tradition}")
                    continue
                    
                item = QListWidgetItem(tradition_name)
                item.setData(Qt.UserRole, tradition)
                self.traditions_list.addItem(item)
            
            # Enable controls
            self._enable_details()
            self.save_btn.setEnabled(False)  # Initially not modified
            
        except Exception as e:
            logger.error(f"Error loading culture {culture.name}: {str(e)}")
            QMessageBox.warning(
                self,
                "Error Loading Culture",
                f"There was an error loading the culture '{culture.name}':\n\n{str(e)}\n\nSome data may not be displayed correctly."
            )
            # Still enable the editor to allow fixing the issue
            self._enable_details()
            self.save_btn.setEnabled(True)  # Enable saving to fix issues
    
    def _disable_details(self) -> None:
        """Disable all detail controls."""
        self.current_culture = None
        
        self.name_edit.clear()
        self.desc_edit.clear()
        self.language_edit.clear()
        
        self.values_list.clear()
        self.traditions_list.clear()
        
        self.name_edit.setEnabled(False)
        self.desc_edit.setEnabled(False)
        self.language_edit.setEnabled(False)
        
        self.values_list.setEnabled(False)
        self.traditions_list.setEnabled(False)
        
        self.add_value_btn.setEnabled(False)
        self.edit_value_btn.setEnabled(False)
        self.remove_value_btn.setEnabled(False)
        
        self.add_tradition_btn.setEnabled(False)
        self.edit_tradition_btn.setEnabled(False)
        self.remove_tradition_btn.setEnabled(False)
        
        self.save_btn.setEnabled(False)
    
    def _enable_details(self) -> None:
        """Enable all detail controls."""
        self.name_edit.setEnabled(True)
        self.desc_edit.setEnabled(True)
        self.language_edit.setEnabled(True)
        
        self.values_list.setEnabled(True)
        self.traditions_list.setEnabled(True)
        
        self.add_value_btn.setEnabled(True)
        self.edit_value_btn.setEnabled(True)
        self.remove_value_btn.setEnabled(True)
        
        self.add_tradition_btn.setEnabled(True)
        self.edit_tradition_btn.setEnabled(True)
        self.remove_tradition_btn.setEnabled(True)
    
    def _on_field_changed(self) -> None:
        """Handle field value changes."""
        if self.current_culture:
            self.save_btn.setEnabled(True)
    
    def _save_current_culture(self) -> None:
        """Save the current culture to the manager."""
        if not self.current_culture:
            return
        
        # Update culture from form
        self.current_culture.name = self.name_edit.text()
        self.current_culture.description = self.desc_edit.toPlainText()
        self.current_culture.language_style = self.language_edit.text()
        
        # Update values
        self.current_culture.values = []
        for i in range(self.values_list.count()):
            item = self.values_list.item(i)
            value = item.data(Qt.UserRole)
            self.current_culture.values.append(value)
        
        # Update traditions
        self.current_culture.traditions = []
        for i in range(self.traditions_list.count()):
            item = self.traditions_list.item(i)
            tradition = item.data(Qt.UserRole)
            self.current_culture.traditions.append(tradition)
        
        # Update culture in manager
        self.culture_manager.add_culture(self.current_culture)
        
        # Mark as saved
        self.save_btn.setEnabled(False)
        
        # Update culture list
        self._refresh_culture_list()
        
        # Find and select the current culture in the list
        for i in range(self.culture_list.count()):
            item = self.culture_list.item(i)
            if item.data(Qt.UserRole) == self.current_culture.id:
                self.culture_list.setCurrentItem(item)
                break
        
        # Emit modified signal
        self.culture_modified.emit()
        
        # Log
        logger.info(f"Saved culture: {self.current_culture.name} ({self.current_culture.id})")
    
    def _add_culture(self) -> None:
        """Add a new culture."""
        # Create new culture
        culture = Culture.create_new("New Culture", "Description of the culture")
        
        # Add to manager
        self.culture_manager.add_culture(culture)
        
        # Refresh list
        self._refresh_culture_list()
        
        # Find and select the new culture
        for i in range(self.culture_list.count()):
            item = self.culture_list.item(i)
            if item.data(Qt.UserRole) == culture.id:
                self.culture_list.setCurrentItem(item)
                break
        
        # Set focus to name for immediate editing
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        
        # Emit modified signal
        self.culture_modified.emit()
        
        # Log
        logger.info(f"Added new culture: {culture.id}")
    
    def _remove_culture(self) -> None:
        """Remove the selected culture."""
        current_item = self.culture_list.currentItem()
        if not current_item:
            return
        
        culture_id = current_item.data(Qt.UserRole)
        culture = self.culture_manager.get_culture(culture_id)
        
        if not culture:
            return
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the culture '{culture.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove from manager
        self.culture_manager.remove_culture(culture_id)
        
        # Refresh list
        self._refresh_culture_list()
        
        # Emit modified signal
        self.culture_modified.emit()
        
        # Log
        logger.info(f"Removed culture: {culture_id}")
    
    def _add_value(self) -> None:
        """Add a new cultural value."""
        if not self.current_culture:
            return
        
        # Create dialog
        dialog = ValueDialog(self)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get value from dialog
            value = dialog.get_value()
            
            # Add to list
            item = QListWidgetItem(f"{value.name} (Importance: {value.importance})")
            item.setData(Qt.UserRole, value)
            self.values_list.addItem(item)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Added value: {value.name}")
    
    def _edit_value(self, item: Optional[QListWidgetItem]) -> None:
        """
        Edit a cultural value.
        
        Args:
            item: The list item to edit, or None.
        """
        if not item:
            return
        
        # Get value from item
        value = item.data(Qt.UserRole)
        
        # Create dialog
        dialog = ValueDialog(self, value)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get updated value from dialog
            updated_value = dialog.get_value()
            
            # Update item
            item.setText(f"{updated_value.name} (Importance: {updated_value.importance})")
            item.setData(Qt.UserRole, updated_value)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Edited value: {updated_value.name}")
    
    def _remove_value(self) -> None:
        """Remove the selected cultural value."""
        item = self.values_list.currentItem()
        if not item:
            return
        
        # Get value from item
        value = item.data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the value '{value.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove item
        self.values_list.takeItem(self.values_list.row(item))
        
        # Mark as modified
        self.save_btn.setEnabled(True)
        
        # Log
        logger.debug(f"Removed value: {value.name}")
    
    def _add_tradition(self) -> None:
        """Add a new cultural tradition."""
        if not self.current_culture:
            return
        
        # Create dialog
        dialog = TraditionDialog(self)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get tradition from dialog
            tradition = dialog.get_tradition()
            
            # Add to list
            item = QListWidgetItem(tradition.name)
            item.setData(Qt.UserRole, tradition)
            self.traditions_list.addItem(item)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Added tradition: {tradition.name}")
    
    def _edit_tradition(self, item: Optional[QListWidgetItem]) -> None:
        """
        Edit a cultural tradition.
        
        Args:
            item: The list item to edit, or None.
        """
        if not item:
            return
        
        # Get tradition from item
        tradition = item.data(Qt.UserRole)
        
        # Create dialog
        dialog = TraditionDialog(self, tradition)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get updated tradition from dialog
            updated_tradition = dialog.get_tradition()
            
            # Update item
            item.setText(updated_tradition.name)
            item.setData(Qt.UserRole, updated_tradition)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Edited tradition: {updated_tradition.name}")
    
    def _remove_tradition(self) -> None:
        """Remove the selected cultural tradition."""
        item = self.traditions_list.currentItem()
        if not item:
            return
        
        # Get tradition from item
        tradition = item.data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the tradition '{tradition.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove item
        self.traditions_list.takeItem(self.traditions_list.row(item))
        
        # Mark as modified
        self.save_btn.setEnabled(True)
        
        # Log
        logger.debug(f"Removed tradition: {tradition.name}")
