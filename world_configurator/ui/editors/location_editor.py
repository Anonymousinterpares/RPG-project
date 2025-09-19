"""
Location editor component for the World Configurator Tool.
"""

import logging
from typing import Dict, List, Optional, Callable

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QSpinBox,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame, QComboBox, QDoubleSpinBox
)

from models.base_models import Location, LocationConnection, LocationFeature
from models.location_data import LocationManager
from models.world_data import CultureManager

logger = logging.getLogger("world_configurator.ui.location_editor")

class FeatureDialog(QDialog):
    """Dialog for editing a location feature."""
    
    def __init__(self, parent=None, feature: Optional[LocationFeature] = None):
        """
        Initialize the feature edit dialog.
        
        Args:
            parent: The parent widget.
            feature: Optional existing feature to edit.
        """
        super().__init__(parent)
        self.setWindowTitle("Location Feature")
        self.setMinimumWidth(400)
        
        # Feature to edit
        self.feature = feature or LocationFeature("", "")
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Name field
        self.name_edit = QLineEdit(self.feature.name)
        form.addRow("Name:", self.name_edit)
        
        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.feature.description)
        self.desc_edit.setMinimumHeight(100)
        form.addRow("Description:", self.desc_edit)
        
        # Interaction type field
        self.interaction_combo = QComboBox()
        self.interaction_combo.addItems(["none", "examine", "use", "interact", "collect"])
        current_index = self.interaction_combo.findText(self.feature.interaction_type)
        if current_index >= 0:
            self.interaction_combo.setCurrentIndex(current_index)
        form.addRow("Interaction Type:", self.interaction_combo)
        
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
    
    def get_feature(self) -> LocationFeature:
        """Get the edited feature."""
        self.feature.name = self.name_edit.text()
        self.feature.description = self.desc_edit.toPlainText()
        self.feature.interaction_type = self.interaction_combo.currentText()
        return self.feature

class ConnectionDialog(QDialog):
    """Dialog for editing a location connection."""
    
    def __init__(self, parent=None, connection: Optional[LocationConnection] = None, 
                 available_locations: Optional[Dict[str, str]] = None):
        """
        Initialize the connection edit dialog.
        
        Args:
            parent: The parent widget.
            connection: Optional existing connection to edit.
            available_locations: Dictionary of location IDs to names.
        """
        super().__init__(parent)
        self.setWindowTitle("Location Connection")
        self.setMinimumWidth(400)
        
        # Connection to edit
        self.connection = connection or LocationConnection("", "", 0)
        
        # Available locations
        self.available_locations = available_locations or {}
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Target location field
        self.target_combo = QComboBox()
        for loc_id, loc_name in self.available_locations.items():
            self.target_combo.addItem(loc_name, loc_id)
        
        # Set current target if it exists
        if self.connection.target in self.available_locations:
            index = self.target_combo.findData(self.connection.target)
            if index >= 0:
                self.target_combo.setCurrentIndex(index)
        
        form.addRow("Target Location:", self.target_combo)
        
        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.connection.description)
        self.desc_edit.setMinimumHeight(80)
        form.addRow("Description:", self.desc_edit)
        
        # Travel time field
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 10000)  # 1 minute to ~7 days
        self.time_spin.setValue(self.connection.travel_time)
        self.time_spin.setSuffix(" minutes")
        form.addRow("Travel Time:", self.time_spin)
        
        layout.addLayout(form)
        
        # Requirements section
        req_label = QLabel("Requirements")
        req_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(req_label)
        
        self.req_list = QListWidget()
        self.req_list.setMaximumHeight(80)
        layout.addWidget(self.req_list)
        
        # Add existing requirements
        for req in self.connection.requirements:
            self.req_list.addItem(req)
        
        # Requirement controls
        req_controls = QHBoxLayout()
        
        self.req_edit = QLineEdit()
        self.req_edit.setPlaceholderText("Enter requirement (e.g., 'key', 'quest_completed')")
        req_controls.addWidget(self.req_edit)
        
        self.add_req_btn = QPushButton("Add")
        self.add_req_btn.clicked.connect(self._add_requirement)
        req_controls.addWidget(self.add_req_btn)
        
        self.remove_req_btn = QPushButton("Remove")
        self.remove_req_btn.clicked.connect(self._remove_requirement)
        req_controls.addWidget(self.remove_req_btn)
        
        layout.addLayout(req_controls)
        
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
    
    def _add_requirement(self):
        """Add a requirement to the list."""
        req_text = self.req_edit.text().strip()
        if req_text:
            self.req_list.addItem(req_text)
            self.req_edit.clear()
    
    def _remove_requirement(self):
        """Remove the selected requirement from the list."""
        current_item = self.req_list.currentItem()
        if current_item:
            self.req_list.takeItem(self.req_list.row(current_item))
    
    def get_connection(self) -> LocationConnection:
        """Get the edited connection."""
        # Get selected target
        target_id = self.target_combo.currentData()
        
        # Get requirements
        requirements = []
        for i in range(self.req_list.count()):
            requirements.append(self.req_list.item(i).text())
        
        # Update connection
        self.connection.target = target_id
        self.connection.description = self.desc_edit.toPlainText()
        self.connection.travel_time = self.time_spin.value()
        self.connection.requirements = requirements
        
        return self.connection

class LocationEditor(QWidget):
    """Location editor component."""
    
    # Signals
    location_modified = Signal()
    
    def __init__(self, parent=None):
        """
        Initialize the location editor.
        
        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        
        # Internal state
        self.location_manager = LocationManager()
        self.culture_manager = CultureManager()
        self.current_location: Optional[Location] = None
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the editor UI."""
        main_layout = QHBoxLayout(self)
        
        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (location list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = QLabel("Locations")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(list_label)
        
        self.location_list = QListWidget()
        self.location_list.setMinimumWidth(200)
        self.location_list.currentItemChanged.connect(self._on_location_selected)
        left_layout.addWidget(self.location_list)
        
        list_buttons = QHBoxLayout()
        
        self.add_location_btn = QPushButton("Add")
        self.add_location_btn.clicked.connect(self._add_location)
        list_buttons.addWidget(self.add_location_btn)
        
        self.remove_location_btn = QPushButton("Remove")
        self.remove_location_btn.clicked.connect(self._remove_location)
        self.remove_location_btn.setEnabled(False)
        list_buttons.addWidget(self.remove_location_btn)
        
        left_layout.addLayout(list_buttons)
        
        # Add left panel to splitter
        splitter.addWidget(left_panel)
        
        # Right panel (location details)
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setFrameShape(QFrame.NoFrame)
        
        self.details_widget = QWidget()
        right_panel.setWidget(self.details_widget)
        
        self.details_layout = QVBoxLayout(self.details_widget)
        
        # Location details form
        self.form_layout = QFormLayout()
        
        # Location name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter location name")
        self.name_edit.textChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Name:", self.name_edit)
        
        # Location description
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Enter location description")
        self.desc_edit.textChanged.connect(self._on_field_changed)
        self.desc_edit.setMinimumHeight(100)
        self.form_layout.addRow("Description:", self.desc_edit)
        
        # Location type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["village", "city", "dungeon", "forest", "mountain", "cave", "ruins", "castle", "other"])
        self.type_combo.currentTextChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Type:", self.type_combo)
        
        # Region
        self.region_edit = QLineEdit()
        self.region_edit.setPlaceholderText("Enter region name")
        self.region_edit.textChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Region:", self.region_edit)
        
        # Culture
        self.culture_combo = QComboBox()
        self.culture_combo.currentIndexChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Culture:", self.culture_combo)
        
        # Population
        self.population_spin = QSpinBox()
        self.population_spin.setRange(0, 1000000)
        self.population_spin.setSingleStep(10)
        self.population_spin.valueChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Population:", self.population_spin)
        
        self.details_layout.addLayout(self.form_layout)
        
        # Features section
        features_label = QLabel("Location Features")
        features_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(features_label)
        
        self.features_list = QListWidget()
        self.features_list.setMinimumHeight(120)
        self.features_list.itemDoubleClicked.connect(self._edit_feature)
        self.details_layout.addWidget(self.features_list)
        
        features_buttons = QHBoxLayout()
        
        self.add_feature_btn = QPushButton("Add Feature")
        self.add_feature_btn.clicked.connect(self._add_feature)
        features_buttons.addWidget(self.add_feature_btn)
        
        self.edit_feature_btn = QPushButton("Edit Feature")
        self.edit_feature_btn.clicked.connect(lambda: self._edit_feature(self.features_list.currentItem()))
        features_buttons.addWidget(self.edit_feature_btn)
        
        self.remove_feature_btn = QPushButton("Remove Feature")
        self.remove_feature_btn.clicked.connect(self._remove_feature)
        features_buttons.addWidget(self.remove_feature_btn)
        
        self.details_layout.addLayout(features_buttons)
        
        # Connections section
        connections_label = QLabel("Location Connections")
        connections_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(connections_label)
        
        self.connections_list = QListWidget()
        self.connections_list.setMinimumHeight(120)
        self.connections_list.itemDoubleClicked.connect(self._edit_connection)
        self.details_layout.addWidget(self.connections_list)
        
        connections_buttons = QHBoxLayout()
        
        self.add_connection_btn = QPushButton("Add Connection")
        self.add_connection_btn.clicked.connect(self._add_connection)
        connections_buttons.addWidget(self.add_connection_btn)
        
        self.edit_connection_btn = QPushButton("Edit Connection")
        self.edit_connection_btn.clicked.connect(lambda: self._edit_connection(self.connections_list.currentItem()))
        connections_buttons.addWidget(self.edit_connection_btn)
        
        self.remove_connection_btn = QPushButton("Remove Connection")
        self.remove_connection_btn.clicked.connect(self._remove_connection)
        connections_buttons.addWidget(self.remove_connection_btn)
        
        self.details_layout.addLayout(connections_buttons)
        
        # Culture Mix Override Section
        cm_label = QLabel("Culture Mix (Override for this Location)")
        cm_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(cm_label)
        
        cm_controls = QHBoxLayout()
        self.cm_culture_combo = QComboBox()
        self.cm_weight_spin = QDoubleSpinBox()
        self.cm_weight_spin.setRange(0.0, 1.0)
        self.cm_weight_spin.setSingleStep(0.05)
        self.cm_add_btn = QPushButton("Add/Update")
        self.cm_add_btn.clicked.connect(self._cm_add_update)
        cm_controls.addWidget(QLabel("Culture:"))
        cm_controls.addWidget(self.cm_culture_combo)
        cm_controls.addWidget(QLabel("Weight:"))
        cm_controls.addWidget(self.cm_weight_spin)
        cm_controls.addWidget(self.cm_add_btn)
        self.details_layout.addLayout(cm_controls)
        
        self.cm_list = QListWidget()
        self.cm_list.setMinimumHeight(100)
        self.details_layout.addWidget(self.cm_list)
        cm_buttons = QHBoxLayout()
        self.cm_remove_btn = QPushButton("Remove")
        self.cm_remove_btn.clicked.connect(self._cm_remove)
        self.cm_clear_btn = QPushButton("Clear Override")
        self.cm_clear_btn.clicked.connect(self._cm_clear)
        cm_buttons.addWidget(self.cm_remove_btn)
        cm_buttons.addWidget(self.cm_clear_btn)
        self.details_layout.addLayout(cm_buttons)
        
        # Global Culture Mix Defaults Section
        gcm_label = QLabel("Global Culture Mix Defaults")
        gcm_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(gcm_label)
        
        gcm_controls = QHBoxLayout()
        self.gcm_culture_edit = QLineEdit()
        self.gcm_culture_edit.setPlaceholderText("culture id (e.g., concordant)")
        self.gcm_weight_spin = QDoubleSpinBox()
        self.gcm_weight_spin.setRange(0.0, 1.0)
        self.gcm_weight_spin.setSingleStep(0.05)
        self.gcm_add_btn = QPushButton("Add/Update Default")
        self.gcm_add_btn.clicked.connect(self._gcm_add_update)
        gcm_controls.addWidget(self.gcm_culture_edit)
        gcm_controls.addWidget(QLabel("Weight:"))
        gcm_controls.addWidget(self.gcm_weight_spin)
        gcm_controls.addWidget(self.gcm_add_btn)
        self.details_layout.addLayout(gcm_controls)
        
        self.gcm_list = QListWidget()
        self.gcm_list.setMinimumHeight(100)
        self.details_layout.addWidget(self.gcm_list)
        gcm_buttons = QHBoxLayout()
        self.gcm_remove_btn = QPushButton("Remove Default")
        self.gcm_remove_btn.clicked.connect(self._gcm_remove)
        self.gcm_load_btn = QPushButton("Load Defaults File")
        self.gcm_load_btn.clicked.connect(self._gcm_load)
        self.gcm_save_btn = QPushButton("Save Defaults File")
        self.gcm_save_btn.clicked.connect(self._gcm_save)
        gcm_buttons.addWidget(self.gcm_remove_btn)
        gcm_buttons.addWidget(self.gcm_load_btn)
        gcm_buttons.addWidget(self.gcm_save_btn)
        self.details_layout.addLayout(gcm_buttons)
        
        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current_location)
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
    
    def set_managers(self, location_manager: LocationManager, culture_manager: CultureManager) -> None:
        """
        Set the managers to use.
        
        Args:
            location_manager: The location manager.
            culture_manager: The culture manager for culture selection.
        """
        self.location_manager = location_manager
        self.culture_manager = culture_manager
        self._refresh_location_list()
        self._populate_culture_combo()
        # Populate culture combo for culture mix editor
        self.cm_culture_combo.clear()
        for culture_id, culture in self.culture_manager.cultures.items():
            self.cm_culture_combo.addItem(culture.name, culture_id)
        # Load global defaults
        self._gcm_load()
    
    def _populate_culture_combo(self) -> None:
        """Populate the culture combo box from the culture manager."""
        self.culture_combo.clear()
        
        # Add empty option
        self.culture_combo.addItem("<None>", "")
        
        # Add all cultures
        for culture_id, culture in self.culture_manager.cultures.items():
            self.culture_combo.addItem(culture.name, culture_id)
    
    def _refresh_location_list(self) -> None:
        """Refresh the location list from the manager."""
        # Clear list
        self.location_list.clear()
        
        # Add all locations
        for location_id, location in self.location_manager.locations.items():
            item = QListWidgetItem(location.name)
            item.setData(Qt.UserRole, location_id)
            self.location_list.addItem(item)
        
        # Sort alphabetically
        self.location_list.sortItems()
        
        # Select the first item if available
        if self.location_list.count() > 0:
            self.location_list.setCurrentRow(0)
    
    def _on_location_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        """
        Handle location selection change.
        
        Args:
            current: The current selected item, or None.
            previous: The previously selected item, or None.
        """
        if current:
            location_id = current.data(Qt.UserRole)
            location = self.location_manager.get_location(location_id)
            
            if location:
                self._load_location(location)
                self.remove_location_btn.setEnabled(True)
                return
        
        # No valid selection
        self._disable_details()
        self.remove_location_btn.setEnabled(False)
    
    def _load_location(self, location: Location) -> None:
        """
        Load a location into the editor.
        
        Args:
            location: The location to load.
        """
        try:
            self.current_location = location
            
            # Set form values
            self.name_edit.setText(location.name)
            self.desc_edit.setPlainText(location.description)
            
            # Set type
            index = self.type_combo.findText(location.type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            
            self.region_edit.setText(location.region)
            
            # Set culture
            index = self.culture_combo.findData(location.culture_id)
            if index >= 0:
                self.culture_combo.setCurrentIndex(index)
            else:
                self.culture_combo.setCurrentIndex(0)  # None
            
            self.population_spin.setValue(location.population)
            
            # Load features
            self.features_list.clear()
            for feature in location.features:
                # Ensure feature is a LocationFeature object
                if hasattr(feature, 'name'):
                    feature_name = feature.name
                elif isinstance(feature, dict) and 'name' in feature:
                    # Convert dict to LocationFeature if needed
                    from world_configurator.models.base_models import LocationFeature
                    feature = LocationFeature(
                        name=feature.get('name', ''),
                        description=feature.get('description', ''),
                        interaction_type=feature.get('interaction_type', 'none')
                    )
                    feature_name = feature.get('name', 'Unknown Feature')
                else:
                    logger.warning(f"Skipping invalid feature in location {location.name}: {feature}")
                    continue
                    
                item = QListWidgetItem(feature_name)
                item.setData(Qt.UserRole, feature)
                self.features_list.addItem(item)
            
            # Load connections
            self.connections_list.clear()
            for connection in location.connections:
                # Ensure connection is a LocationConnection object
                if hasattr(connection, 'target') and hasattr(connection, 'travel_time'):
                    target_id = connection.target
                    travel_time = connection.travel_time
                elif isinstance(connection, dict) and 'target' in connection:
                    # Convert dict to LocationConnection if needed
                    from world_configurator.models.base_models import LocationConnection
                    connection = LocationConnection(
                        target=connection.get('target', ''),
                        description=connection.get('description', ''),
                        travel_time=connection.get('travel_time', 0),
                        requirements=connection.get('requirements', [])
                    )
                    target_id = connection.target
                    travel_time = connection.travel_time
                else:
                    logger.warning(f"Skipping invalid connection in location {location.name}: {connection}")
                    continue
                
                target_name = "Unknown"
                target_loc = self.location_manager.get_location(target_id)
                if target_loc:
                    target_name = target_loc.name
                
                item = QListWidgetItem(f"{target_name} ({travel_time} mins)")
                item.setData(Qt.UserRole, connection)
                self.connections_list.addItem(item)
            
            # Load culture mix override
            self._cm_refresh_list()
            # Enable controls
            self._enable_details()
            self.save_btn.setEnabled(False)  # Initially not modified
            
        except Exception as e:
            logger.error(f"Error loading location {location.name}: {str(e)}")
            QMessageBox.warning(
                self,
                "Error Loading Location",
                f"There was an error loading the location '{location.name}':\n\n{str(e)}\n\nSome data may not be displayed correctly."
            )
            # Still enable the editor to allow fixing the issue
            self._enable_details()
            self.save_btn.setEnabled(True)  # Enable saving to fix issues
    
    def _disable_details(self) -> None:
        """Disable all detail controls."""
        self.current_location = None
        
        self.name_edit.clear()
        self.desc_edit.clear()
        self.region_edit.clear()
        self.population_spin.setValue(0)
        
        self.features_list.clear()
        self.connections_list.clear()
        
        self.name_edit.setEnabled(False)
        self.desc_edit.setEnabled(False)
        self.type_combo.setEnabled(False)
        self.region_edit.setEnabled(False)
        self.culture_combo.setEnabled(False)
        self.population_spin.setEnabled(False)
        
        self.features_list.setEnabled(False)
        self.connections_list.setEnabled(False)
        
        self.add_feature_btn.setEnabled(False)
        self.edit_feature_btn.setEnabled(False)
        self.remove_feature_btn.setEnabled(False)
        
        self.add_connection_btn.setEnabled(False)
        self.edit_connection_btn.setEnabled(False)
        self.remove_connection_btn.setEnabled(False)
        
        self.save_btn.setEnabled(False)
    
    def _enable_details(self) -> None:
        """Enable all detail controls."""
        self.name_edit.setEnabled(True)
        self.desc_edit.setEnabled(True)
        self.type_combo.setEnabled(True)
        self.region_edit.setEnabled(True)
        self.culture_combo.setEnabled(True)
        self.population_spin.setEnabled(True)
        
        self.features_list.setEnabled(True)
        self.connections_list.setEnabled(True)
        
        self.add_feature_btn.setEnabled(True)
        self.edit_feature_btn.setEnabled(True)
        self.remove_feature_btn.setEnabled(True)
        
        self.add_connection_btn.setEnabled(True)
        self.edit_connection_btn.setEnabled(True)
        self.remove_connection_btn.setEnabled(True)
    
    def _on_field_changed(self) -> None:
        """Handle field value changes."""
        if self.current_location:
            self.save_btn.setEnabled(True)
    
    def _save_current_location(self) -> None:
        """Save the current location to the manager."""
        if not self.current_location:
            return
        
        # Update location from form
        self.current_location.name = self.name_edit.text()
        self.current_location.description = self.desc_edit.toPlainText()
        self.current_location.type = self.type_combo.currentText()
        self.current_location.region = self.region_edit.text()
        self.current_location.culture_id = self.culture_combo.currentData()
        self.current_location.population = self.population_spin.value()
        
        # Update features
        self.current_location.features = []
        for i in range(self.features_list.count()):
            item = self.features_list.item(i)
            feature = item.data(Qt.UserRole)
            self.current_location.features.append(feature)
        
        # Update connections
        self.current_location.connections = []
        for i in range(self.connections_list.count()):
            item = self.connections_list.item(i)
            connection = item.data(Qt.UserRole)
            self.current_location.connections.append(connection)
        
        # Save culture mix from UI to model
        self._cm_save_from_list()
        # Update location in manager
        self.location_manager.add_location(self.current_location)
        
        # Mark as saved
        self.save_btn.setEnabled(False)
        
        # Update location list
        self._refresh_location_list()
        
        # Find and select the current location in the list
        for i in range(self.location_list.count()):
            item = self.location_list.item(i)
            if item.data(Qt.UserRole) == self.current_location.id:
                self.location_list.setCurrentItem(item)
                break
        
        # Emit modified signal
        self.location_modified.emit()
        
        # Log
        logger.info(f"Saved location: {self.current_location.name} ({self.current_location.id})")
    
    def _add_location(self) -> None:
        """Add a new location."""
        # Create new location
        location = Location.create_new("New Location", "Description of the location", "other")
        
        # Add to manager
        self.location_manager.add_location(location)
        
        # Refresh list
        self._refresh_location_list()
        
        # Find and select the new location
        for i in range(self.location_list.count()):
            item = self.location_list.item(i)
            if item.data(Qt.UserRole) == location.id:
                self.location_list.setCurrentItem(item)
                break
        
        # Set focus to name for immediate editing
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        
        # Emit modified signal
        self.location_modified.emit()
        
        # Log
        logger.info(f"Added new location: {location.id}")
    
    def _remove_location(self) -> None:
        """Remove the selected location."""
        current_item = self.location_list.currentItem()
        if not current_item:
            return
        
        location_id = current_item.data(Qt.UserRole)
        location = self.location_manager.get_location(location_id)
        
        if not location:
            return
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the location '{location.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Check for connections to this location
        connected_locations = []
        for other_id, other_loc in self.location_manager.locations.items():
            if other_id == location_id:
                continue
            
            for conn in other_loc.connections:
                if conn.target == location_id:
                    connected_locations.append(other_loc.name)
                    break
        
        if connected_locations:
            # Warn about connected locations
            conn_warn = QMessageBox.warning(
                self,
                "Connected Locations",
                f"The following locations have connections to '{location.name}':\n\n" +
                "\n".join(connected_locations) +
                "\n\nDeleting this location will leave invalid connections. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if conn_warn != QMessageBox.Yes:
                return
        
        # Remove from manager
        self.location_manager.remove_location(location_id)
        
        # Refresh list
        self._refresh_location_list()
        
        # Emit modified signal
        self.location_modified.emit()
        
        # Log
        logger.info(f"Removed location: {location_id}")
    
    def _add_feature(self) -> None:
        """Add a new location feature."""
        if not self.current_location:
            return
        
        # Create dialog
        dialog = FeatureDialog(self)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get feature from dialog
            feature = dialog.get_feature()
            
            # Add to list
            item = QListWidgetItem(feature.name)
            item.setData(Qt.UserRole, feature)
            self.features_list.addItem(item)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Added feature: {feature.name}")
    
    def _edit_feature(self, item: Optional[QListWidgetItem]) -> None:
        """
        Edit a location feature.
        
        Args:
            item: The list item to edit, or None.
        """
        if not item:
            return
        
        # Get feature from item
        feature = item.data(Qt.UserRole)
        
        # Create dialog
        dialog = FeatureDialog(self, feature)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get updated feature from dialog
            updated_feature = dialog.get_feature()
            
            # Update item
            item.setText(updated_feature.name)
            item.setData(Qt.UserRole, updated_feature)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Edited feature: {updated_feature.name}")
    
    def _remove_feature(self) -> None:
        """Remove the selected location feature."""
        item = self.features_list.currentItem()
        if not item:
            return
        
        # Get feature from item
        feature = item.data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the feature '{feature.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove item
        self.features_list.takeItem(self.features_list.row(item))
        
        # Mark as modified
        self.save_btn.setEnabled(True)
        
        # Log
        logger.debug(f"Removed feature: {feature.name}")
    
    def _cm_refresh_list(self) -> None:
        self.cm_list.clear()
        if not self.current_location:
            return
        mix = getattr(self.current_location, 'culture_mix', {}) or {}
        for cid, weight in mix.items():
            item = QListWidgetItem(f"{cid}: {weight:.2f}")
            item.setData(Qt.UserRole, (cid, weight))
            self.cm_list.addItem(item)
    
    def _cm_add_update(self) -> None:
        if not self.current_location:
            return
        cid = self.cm_culture_combo.currentData()
        weight = float(self.cm_weight_spin.value())
        # Update or add in the list
        # Find existing
        found_row = -1
        for i in range(self.cm_list.count()):
            c, _ = self.cm_list.item(i).data(Qt.UserRole)
            if c == cid:
                found_row = i
                break
        item_text = f"{cid}: {weight:.2f}"
        if found_row >= 0:
            self.cm_list.item(found_row).setText(item_text)
            self.cm_list.item(found_row).setData(Qt.UserRole, (cid, weight))
        else:
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, (cid, weight))
            self.cm_list.addItem(item)
        self.save_btn.setEnabled(True)
    
    def _cm_remove(self) -> None:
        row = self.cm_list.currentRow()
        if row >= 0:
            self.cm_list.takeItem(row)
            self.save_btn.setEnabled(True)
    
    def _cm_clear(self) -> None:
        self.cm_list.clear()
        self.save_btn.setEnabled(True)
    
    def _cm_save_from_list(self) -> None:
        if not self.current_location:
            return
        mix: Dict[str, float] = {}
        for i in range(self.cm_list.count()):
            cid, weight = self.cm_list.item(i).data(Qt.UserRole)
            mix[cid] = float(weight)
        self.current_location.culture_mix = mix
    
    def _get_available_locations(self) -> Dict[str, str]:
        """Get a dictionary of available target locations."""
        locations = {}
        
        # Include all locations except the current one
        for loc_id, location in self.location_manager.locations.items():
            if self.current_location and loc_id == self.current_location.id:
                continue
            
            locations[loc_id] = location.name
        
        return locations
    
    def _add_connection(self) -> None:
        """Add a new location connection."""
        if not self.current_location:
            return
        
        # Get available target locations
        available_locations = self._get_available_locations()
        
        if not available_locations:
            QMessageBox.information(
                self,
                "No Available Locations",
                "There are no other locations available to connect to.\n\nPlease create more locations first."
            )
            return
        
        # Create dialog
        dialog = ConnectionDialog(self, None, available_locations)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get connection from dialog
            connection = dialog.get_connection()
            
            # Get target location name
            target_name = available_locations.get(connection.target, "Unknown")
            
            # Add to list
            item = QListWidgetItem(f"{target_name} ({connection.travel_time} mins)")
            item.setData(Qt.UserRole, connection)
            self.connections_list.addItem(item)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Added connection to: {target_name}")
    
    def _edit_connection(self, item: Optional[QListWidgetItem]) -> None:
        """
        Edit a location connection.
        
        Args:
            item: The list item to edit, or None.
        """
        if not item:
            return
        
        # Get connection from item
        connection = item.data(Qt.UserRole)
        
        # Get available target locations
        available_locations = self._get_available_locations()
        
        # Add the current target if it's not in the list (might have been removed)
        if connection.target not in available_locations:
            target_loc = self.location_manager.get_location(connection.target)
            if target_loc:
                available_locations[connection.target] = target_loc.name
            else:
                available_locations[connection.target] = "Unknown Location"
        
        # Create dialog
        dialog = ConnectionDialog(self, connection, available_locations)
        
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            # Get updated connection from dialog
            updated_connection = dialog.get_connection()
            
            # Get target location name
            target_name = available_locations.get(updated_connection.target, "Unknown")
            
            # Update item
            item.setText(f"{target_name} ({updated_connection.travel_time} mins)")
            item.setData(Qt.UserRole, updated_connection)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Edited connection to: {target_name}")
    
    def _gcm_load(self) -> None:
        # Load defaults from config/world/locations/defaults.json
        from utils.file_manager import get_world_config_dir, load_json, save_json
        try:
            path = os.path.join(get_world_config_dir(), "locations", "defaults.json")
            data = load_json(path) or {}
            mix = (data.get("culture_mix") or {})
            self.gcm_list.clear()
            for cid, weight in mix.items():
                item = QListWidgetItem(f"{cid}: {float(weight):.2f}")
                item.setData(Qt.UserRole, (cid, float(weight)))
                self.gcm_list.addItem(item)
        except Exception:
            self.gcm_list.clear()
    
    def _gcm_save(self) -> None:
        from utils.file_manager import get_world_config_dir, save_json
        path = os.path.join(get_world_config_dir(), "locations", "defaults.json")
        mix: Dict[str, float] = {}
        for i in range(self.gcm_list.count()):
            cid, weight = self.gcm_list.item(i).data(Qt.UserRole)
            mix[cid] = float(weight)
        data = {"culture_mix": mix, "metadata": {"version": "1.0.0", "description": "Default cultural mixture"}}
        if save_json(data, path):
            QMessageBox.information(self, "Saved", "Global culture mix defaults saved.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save culture mix defaults.")
    
    def _gcm_add_update(self) -> None:
        cid = self.gcm_culture_edit.text().strip()
        weight = float(self.gcm_weight_spin.value())
        if not cid:
            return
        # Update or add
        found = -1
        for i in range(self.gcm_list.count()):
            c, _ = self.gcm_list.item(i).data(Qt.UserRole)
            if c == cid:
                found = i
                break
        item_text = f"{cid}: {weight:.2f}"
        if found >= 0:
            self.gcm_list.item(found).setText(item_text)
            self.gcm_list.item(found).setData(Qt.UserRole, (cid, weight))
        else:
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, (cid, weight))
            self.gcm_list.addItem(item)
    
    def _gcm_remove(self) -> None:
        row = self.gcm_list.currentRow()
        if row >= 0:
            self.gcm_list.takeItem(row)
    
    def _remove_connection(self) -> None:
        """Remove the selected location connection."""
        item = self.connections_list.currentItem()
        if not item:
            return
        
        # Get connection from item
        connection = item.data(Qt.UserRole)
        
        # Get target location name
        target_name = "Unknown"
        target_loc = self.location_manager.get_location(connection.target)
        if target_loc:
            target_name = target_loc.name
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the connection to '{target_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove item
        self.connections_list.takeItem(self.connections_list.row(item))
        
        # Mark as modified
        self.save_btn.setEnabled(True)
        
        # Log
        logger.debug(f"Removed connection to: {target_name}")
