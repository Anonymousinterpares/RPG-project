"""
Location data models for the world configurator.
"""

import logging
import os
import shutil
import datetime
from typing import Dict, List, Any, Optional, Union

from models.base_models import Location, LocationConnection, LocationFeature, WorldModelState
from utils.file_manager import load_json, save_json, get_world_config_dir

logger = logging.getLogger("world_configurator.models.location_data")

class LocationManager:
    """
    Manager for location data.
    """
    def __init__(self):
        self.locations: Dict[str, Location] = {}
        self.state = WorldModelState()
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load locations from a JSON file.
        
        Args:
            file_path: Path to the JSON file.
        
        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            data = load_json(file_path)
            if not data or "locations" not in data:
                logger.error(f"Invalid locations file format: {file_path}")
                return False
            
            # Clear existing locations
            self.locations.clear()
            
            # Load each location
            for location_id, location_data in data["locations"].items():
                # Ensure the location has an ID
                if "id" not in location_data:
                    location_data["id"] = location_id
                
                location = Location.from_dict(location_data)
                self.locations[location_id] = location
            
            # Update state
            self.state.path = file_path
            self.state.modified = False
            
            logger.info(f"Loaded {len(self.locations)} locations from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading locations from {file_path}: {e}")
            return False
    
    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        Save locations to a JSON file.
        
        Args:
            file_path: Path to the JSON file. If None, uses the path from state.
        
        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            # Use provided path or the one from state
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving locations")
                return False
            
            # Prepare data
            data = {
                "locations": {k: v.to_dict() for k, v in self.locations.items()},
                "metadata": {
                    "version": "1.0.0",
                    "description": "Location definitions for the RPG game world"
                }
            }
            
            # Save to file
            result = save_json(data, path)
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved {len(self.locations)} locations to {path}")
            
            return result
        except Exception as e:
            logger.error(f"Error saving locations: {e}")
            return False
    
    def add_location(self, location: Location) -> None:
        """
        Add a location to the manager.
        
        Args:
            location: The location to add.
        """
        self.locations[location.id] = location
        self.state.modified = True
        logger.info(f"Added location: {location.name} ({location.id})")
    
    def remove_location(self, location_id: str) -> bool:
        """
        Remove a location from the manager.
        
        Args:
            location_id: The ID of the location to remove.
        
        Returns:
            True if the location was removed, False if it wasn't found.
        """
        if location_id in self.locations:
            del self.locations[location_id]
            self.state.modified = True
            logger.info(f"Removed location: {location_id}")
            return True
        else:
            logger.warning(f"Cannot remove non-existent location: {location_id}")
            return False
    
    def get_location(self, location_id: str) -> Optional[Location]:
        """
        Get a location by ID.
        
        Args:
            location_id: The ID of the location to get.
        
        Returns:
            The location if found, None otherwise.
        """
        return self.locations.get(location_id)
    
    def add_connection(self, source_id: str, target_id: str, description: str, travel_time: int) -> bool:
        """
        Add a connection between two locations.
        
        Args:
            source_id: The ID of the source location.
            target_id: The ID of the target location.
            description: Description of the connection.
            travel_time: Travel time in minutes.
        
        Returns:
            True if the connection was added, False if a location wasn't found.
        """
        source = self.get_location(source_id)
        target = self.get_location(target_id)
        
        if not source:
            logger.warning(f"Cannot add connection from non-existent location: {source_id}")
            return False
        
        if not target:
            logger.warning(f"Cannot add connection to non-existent location: {target_id}")
            return False
        
        # Create connection
        connection = LocationConnection(
            target=target_id,
            description=description,
            travel_time=travel_time
        )
        
        # Add to source location
        source.connections.append(connection)
        self.state.modified = True
        
        logger.info(f"Added connection from {source_id} to {target_id}")
        return True
    
    def remove_connection(self, source_id: str, target_id: str) -> bool:
        """
        Remove a connection between two locations.
        
        Args:
            source_id: The ID of the source location.
            target_id: The ID of the target location.
        
        Returns:
            True if the connection was removed, False if a location or connection wasn't found.
        """
        source = self.get_location(source_id)
        
        if not source:
            logger.warning(f"Cannot remove connection from non-existent location: {source_id}")
            return False
        
        for i, connection in enumerate(source.connections):
            if connection.target == target_id:
                source.connections.pop(i)
                self.state.modified = True
                logger.info(f"Removed connection from {source_id} to {target_id}")
                return True
        
        logger.warning(f"No connection found from {source_id} to {target_id}")
        return False
    
    def add_feature_to_location(self, location_id: str, feature: LocationFeature) -> bool:
        """
        Add a feature to a location.
        
        Args:
            location_id: The ID of the location to modify.
            feature: The feature to add.
        
        Returns:
            True if the feature was added, False if the location wasn't found.
        """
        location = self.get_location(location_id)
        if not location:
            logger.warning(f"Cannot add feature to non-existent location: {location_id}")
            return False
        
        location.features.append(feature)
        self.state.modified = True
        logger.info(f"Added feature to location {location_id}: {feature.name}")
        return True
    
    def remove_feature_from_location(self, location_id: str, feature_name: str) -> bool:
        """
        Remove a feature from a location.
        
        Args:
            location_id: The ID of the location to modify.
            feature_name: The name of the feature to remove.
        
        Returns:
            True if the feature was removed, False if the location or feature wasn't found.
        """
        location = self.get_location(location_id)
        if not location:
            logger.warning(f"Cannot remove feature from non-existent location: {location_id}")
            return False
        
        for i, feature in enumerate(location.features):
            if feature.name == feature_name:
                location.features.pop(i)
                self.state.modified = True
                logger.info(f"Removed feature {feature_name} from location {location_id}")
                return True
        
        logger.warning(f"No feature named {feature_name} found in location {location_id}")
        return False
    
    def verify_connections(self) -> List[str]:
        """
        Verify that all connections reference valid location IDs.
        
        Returns:
            A list of error messages, or an empty list if all connections are valid.
        """
        errors = []
        
        for location_id, location in self.locations.items():
            for i, connection in enumerate(location.connections):
                if connection.target not in self.locations:
                    error = f"Location {location_id} has invalid connection to non-existent location: {connection.target}"
                    errors.append(error)
                    logger.warning(error)
        
        return errors
    
    def export_to_game(self) -> bool:
        """
        Export locations to the game's configuration directory.
        
        Returns:
            True if export was successful, False otherwise.
        """
        try:
            # Define target path
            target_dir = os.path.join(get_world_config_dir(), "locations")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "locations.json")
            
            # Create backup folder if it doesn't exist
            backup_dir = os.path.join(target_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create timestamped backup if target file exists
            if os.path.exists(target_path):
                filename = os.path.basename(target_path)
                name, ext = os.path.splitext(filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{name}_{timestamp}{ext}"
                backup_path = os.path.join(backup_dir, backup_filename)
                
                try:
                    shutil.copy2(target_path, backup_path)
                    logger.info(f"Created backup of {target_path} at {backup_path}")
                except Exception as backup_err:
                    logger.error(f"Failed to create backup: {backup_err}")
                    # Continue with export even if backup fails
            
            # Save to target path
            return self.save_to_file(target_path)
        except Exception as e:
            logger.error(f"Error exporting locations to game: {e}")
            return False
