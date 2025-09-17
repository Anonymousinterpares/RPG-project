#!/usr/bin/env python3
"""
Save file management utilities for the RPG game.

This module provides classes and functions for managing saved game files,
including listing, backup creation, validation, and metadata operations.
It works alongside StateManager but focuses on file operations rather than
actual game state serialization.
"""

import os
import json
import shutil
import glob
import uuid
import time
import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Union
from pathlib import Path

from core.utils.logging_config import get_logger
from core.utils.json_utils import enhanced_json_loads, enhanced_json_dumps, EnhancedJSONEncoder

logger = get_logger(__name__)

@dataclass
class SaveMetadata:
    """Metadata for a saved game file."""
    save_id: str  # UUID string
    save_name: str  # User-friendly name
    save_time: float  # Unix timestamp
    version: str  # Game version
    player_name: str  # Name of player character
    player_level: int  # Level of player character
    world_time: str  # In-game time when saved
    location: str  # Current location
    playtime: float  # Time played in seconds
    screenshot: Optional[str] = None  # Path to screenshot image (relative to save)
    custom_notes: str = ""  # User notes about this save
    tags: List[str] = field(default_factory=list)  # User-defined tags
    auto_save: bool = False  # Whether this was an auto-save
    backup_of: Optional[str] = None  # ID of save this is a backup of (if any)
    
    @property
    def formatted_save_time(self) -> str:
        """Return the save time as a formatted string."""
        dt = datetime.datetime.fromtimestamp(self.save_time)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def formatted_playtime(self) -> str:
        """Return the playtime as a formatted string (HH:MM:SS)."""
        hours, remainder = divmod(int(self.playtime), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "save_id": self.save_id,
            "save_name": self.save_name,
            "save_time": self.save_time,
            "version": self.version,
            "player_name": self.player_name,
            "player_level": self.player_level,
            "world_time": self.world_time,
            "location": self.location,
            "playtime": self.playtime,
            "screenshot": self.screenshot,
            "custom_notes": self.custom_notes,
            "tags": self.tags,
            "auto_save": self.auto_save,
            "backup_of": self.backup_of
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SaveMetadata':
        """Create a SaveMetadata instance from a dictionary."""
        # Handle potential missing fields with defaults
        return cls(
            save_id=data.get("save_id", str(uuid.uuid4())),
            save_name=data.get("save_name", "Unknown Save"),
            save_time=data.get("save_time", time.time()),
            version=data.get("version", "0.0.0"),
            player_name=data.get("player_name", "Unknown"),
            player_level=data.get("player_level", 1),
            world_time=data.get("world_time", "00:00"),
            location=data.get("location", "Unknown"),
            playtime=data.get("playtime", 0.0),
            screenshot=data.get("screenshot"),
            custom_notes=data.get("custom_notes", ""),
            tags=data.get("tags", []),
            auto_save=data.get("auto_save", False),
            backup_of=data.get("backup_of")
        )


class SaveFileError(Exception):
    """Base exception for save file operations."""
    pass


class SaveFileNotFoundError(SaveFileError):
    """Exception raised when a save file doesn't exist."""
    pass


class SaveFileCorruptedError(SaveFileError):
    """Exception raised when a save file is corrupted or invalid."""
    pass


class SaveManager:
    """
    Manages saved game files, providing operations for listing, backup creation,
    validation, metadata management, and file operations.
    
    This class works alongside StateManager but focuses on file operations
    rather than actual game state serialization.
    """
    
    DEFAULT_SAVE_DIR = "saves"
    BACKUP_DIR = "backups"
    METADATA_FILENAME = "metadata.json"
    STATE_FILENAME = "state.json"
    MAX_AUTO_BACKUPS = 5
    
    def __init__(self, save_dir: Optional[str] = None):
        """
        Initialize the SaveManager.
        
        Args:
            save_dir: Directory where save files are stored. If None, uses the default.
        """
        if save_dir is None:
            save_dir = self.DEFAULT_SAVE_DIR
        
        self.save_dir = save_dir
        self.backup_dir = os.path.join(save_dir, self.BACKUP_DIR)
        
        # Ensure save directories exist
        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logger.info(f"SaveManager initialized with save directory: {self.save_dir}")
    
    def get_save_list(self, include_backups: bool = False) -> List[SaveMetadata]:
        """
        Get a list of available save files with their metadata.
        
        Args:
            include_backups: Whether to include backup saves in the list.
            
        Returns:
            List of SaveMetadata objects.
        """
        saves = []
        
        # Get all save directories
        search_path = os.path.join(self.save_dir, "*", self.METADATA_FILENAME)
        metadata_files = glob.glob(search_path)
        
        # Get all backup directories if requested
        if include_backups:
            backup_search_path = os.path.join(self.backup_dir, "*", self.METADATA_FILENAME)
            metadata_files.extend(glob.glob(backup_search_path))
        
        # Load metadata from each file
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_dict = json.loads(f.read())
                    metadata = SaveMetadata.from_dict(metadata_dict)
                    saves.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to load metadata from {metadata_file}: {e}")
        
        # Sort by save time, most recent first
        saves.sort(key=lambda x: x.save_time, reverse=True)
        
        return saves
    
    def get_save_path(self, save_id: str, is_backup: bool = False) -> str:
        """
        Get the directory path for a specific save.
        
        Args:
            save_id: The UUID of the save.
            is_backup: Whether this is a backup save.
            
        Returns:
            Path to the save directory.
        """
        base_dir = self.backup_dir if is_backup else self.save_dir
        return os.path.join(base_dir, save_id)
    
    def get_metadata(self, save_id: str, is_backup: bool = False) -> SaveMetadata:
        """
        Get metadata for a specific save.
        
        Args:
            save_id: The UUID of the save.
            is_backup: Whether this is a backup save.
            
        Returns:
            SaveMetadata object.
            
        Raises:
            SaveFileNotFoundError: If the save file doesn't exist.
            SaveFileCorruptedError: If the metadata is corrupted.
        """
        save_dir = self.get_save_path(save_id, is_backup)
        metadata_path = os.path.join(save_dir, self.METADATA_FILENAME)
        
        if not os.path.exists(metadata_path):
            raise SaveFileNotFoundError(f"Save metadata not found for {save_id}")
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_dict = json.loads(f.read())
                return SaveMetadata.from_dict(metadata_dict)
        except Exception as e:
            raise SaveFileCorruptedError(f"Failed to load metadata: {e}")
    
    def update_metadata(self, save_id: str, updates: Dict[str, Any], 
                        is_backup: bool = False) -> SaveMetadata:
        """
        Update metadata for a specific save.
        
        Args:
            save_id: The UUID of the save.
            updates: Dictionary of updates to apply.
            is_backup: Whether this is a backup save.
            
        Returns:
            Updated SaveMetadata object.
            
        Raises:
            SaveFileNotFoundError: If the save file doesn't exist.
        """
        try:
            metadata = self.get_metadata(save_id, is_backup)
        except SaveFileNotFoundError:
            raise
        except SaveFileCorruptedError:
            # Create new metadata if corrupted
            metadata = SaveMetadata(
                save_id=save_id,
                save_name="Recovered Save",
                save_time=time.time(),
                version="0.0.0",
                player_name="Unknown",
                player_level=1,
                world_time="00:00",
                location="Unknown",
                playtime=0.0
            )
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
            else:
                logger.warning(f"Unknown metadata field: {key}")
        
        # Save updated metadata
        save_dir = self.get_save_path(save_id, is_backup)
        metadata_path = os.path.join(save_dir, self.METADATA_FILENAME)
        
        os.makedirs(save_dir, exist_ok=True)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2, cls=EnhancedJSONEncoder)
        
        return metadata
    
    def create_backup(self, save_id: str) -> str:
        """
        Create a backup of a save file.
        
        Args:
            save_id: The UUID of the save to back up.
            
        Returns:
            The UUID of the backup save.
            
        Raises:
            SaveFileNotFoundError: If the save file doesn't exist.
        """
        source_dir = self.get_save_path(save_id)
        
        if not os.path.exists(source_dir):
            raise SaveFileNotFoundError(f"Save not found: {save_id}")
        
        # Create a new ID for the backup
        backup_id = str(uuid.uuid4())
        backup_dir = self.get_save_path(backup_id, is_backup=True)
        
        # Copy all files
        shutil.copytree(source_dir, backup_dir)
        
        # Update metadata to mark as backup
        try:
            metadata = self.get_metadata(backup_id, is_backup=True)
            metadata.backup_of = save_id
            metadata.save_time = time.time()  # Update backup time
            
            metadata_path = os.path.join(backup_dir, self.METADATA_FILENAME)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2, cls=EnhancedJSONEncoder)
                
            logger.info(f"Created backup {backup_id} of save {save_id}")
            return backup_id
            
        except Exception as e:
            # If metadata update fails, remove the backup
            shutil.rmtree(backup_dir, ignore_errors=True)
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def auto_backup(self, save_id: str) -> Optional[str]:
        """
        Create an automatic backup of a save file, managing rotation.
        
        Args:
            save_id: The UUID of the save to back up.
            
        Returns:
            The UUID of the backup save, or None if backup wasn't needed.
        """
        try:
            # Get existing backups for this save
            existing_backups = [
                meta for meta in self.get_save_list(include_backups=True)
                if meta.backup_of == save_id and meta.auto_save
            ]
            
            # If we already have max backups, remove the oldest
            if len(existing_backups) >= self.MAX_AUTO_BACKUPS:
                existing_backups.sort(key=lambda x: x.save_time)
                oldest_backup = existing_backups[0]
                self.delete_save(oldest_backup.save_id, is_backup=True)
            
            # Create new backup
            backup_id = self.create_backup(save_id)
            
            # Mark as auto backup
            self.update_metadata(backup_id, {"auto_save": True}, is_backup=True)
            
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create auto backup: {e}")
            return None
    
    def delete_save(self, save_id: str, is_backup: bool = False) -> bool:
        """
        Delete a save file.
        
        Args:
            save_id: The UUID of the save to delete.
            is_backup: Whether this is a backup save.
            
        Returns:
            True if successful, False otherwise.
        """
        save_dir = self.get_save_path(save_id, is_backup)
        
        if not os.path.exists(save_dir):
            logger.warning(f"Cannot delete non-existent save: {save_id}")
            return False
        
        try:
            shutil.rmtree(save_dir)
            logger.info(f"Deleted save: {save_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete save {save_id}: {e}")
            return False
    
    def rename_save(self, save_id: str, new_name: str, is_backup: bool = False) -> bool:
        """
        Rename a save file.
        
        Args:
            save_id: The UUID of the save to rename.
            new_name: The new name for the save.
            is_backup: Whether this is a backup save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            metadata = self.get_metadata(save_id, is_backup)
            metadata.save_name = new_name
            
            save_dir = self.get_save_path(save_id, is_backup)
            metadata_path = os.path.join(save_dir, self.METADATA_FILENAME)
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2, cls=EnhancedJSONEncoder)
            
            logger.info(f"Renamed save {save_id} to '{new_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rename save {save_id}: {e}")
            return False
    
    def validate_save(self, save_id: str, is_backup: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate a save file for integrity.
        
        Args:
            save_id: The UUID of the save to validate.
            is_backup: Whether this is a backup save.
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        save_dir = self.get_save_path(save_id, is_backup)
        
        # Check if directory exists
        if not os.path.exists(save_dir):
            return False, "Save directory does not exist"
        
        # Check metadata file
        metadata_path = os.path.join(save_dir, self.METADATA_FILENAME)
        if not os.path.exists(metadata_path):
            return False, "Metadata file missing"
        
        # Try to load metadata
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_dict = json.loads(f.read())
                # Basic validation that required fields exist
                for field in ["save_id", "save_name", "save_time", "version"]:
                    if field not in metadata_dict:
                        return False, f"Metadata missing required field: {field}"
        except json.JSONDecodeError:
            return False, "Metadata file is not valid JSON"
        except Exception as e:
            return False, f"Failed to read metadata: {e}"
        
        # Check state file
        state_path = os.path.join(save_dir, self.STATE_FILENAME)
        if not os.path.exists(state_path):
            return False, "State file missing"
        
        # Try to load state (just check if it's valid JSON)
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                json.loads(f.read())
        except json.JSONDecodeError:
            return False, "State file is not valid JSON"
        except Exception as e:
            return False, f"Failed to read state file: {e}"
        
        return True, None
    
    def restore_backup(self, backup_id: str, replace_original: bool = True) -> Optional[str]:
        """
        Restore a backup to its original save location.
        
        Args:
            backup_id: The UUID of the backup to restore.
            replace_original: Whether to replace the original save.
            
        Returns:
            The UUID of the restored save, or None if restoration failed.
        """
        try:
            backup_metadata = self.get_metadata(backup_id, is_backup=True)
            
            if not backup_metadata.backup_of:
                logger.warning(f"Backup {backup_id} does not reference an original save")
                return None
            
            original_id = backup_metadata.backup_of
            backup_dir = self.get_save_path(backup_id, is_backup=True)
            original_dir = self.get_save_path(original_id)
            
            # Check if original exists and backup if needed
            if os.path.exists(original_dir):
                if replace_original:
                    # Create a temporary backup of the current state before overwriting
                    temp_backup_id = self.create_backup(original_id)
                    self.update_metadata(temp_backup_id, {
                        "save_name": f"Pre-restore backup of {backup_metadata.save_name}",
                        "custom_notes": "Automatic backup created before restoring from another backup"
                    }, is_backup=True)
                    
                    # Delete original to prepare for copy
                    shutil.rmtree(original_dir)
                else:
                    # Create a new ID for the restored save
                    new_id = str(uuid.uuid4())
                    original_dir = self.get_save_path(new_id)
                    original_id = new_id
            
            # Copy backup to original/new location
            shutil.copytree(backup_dir, original_dir)
            
            # Update metadata if this is a new save ID
            if original_id != backup_metadata.backup_of:
                try:
                    metadata = self.get_metadata(original_id)
                    metadata.save_id = original_id
                    metadata.backup_of = None
                    metadata.save_name += " (Restored)"
                    metadata.save_time = time.time()
                    
                    metadata_path = os.path.join(original_dir, self.METADATA_FILENAME)
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata.to_dict(), f, indent=2, cls=EnhancedJSONEncoder)
                        
                except Exception as e:
                    logger.error(f"Failed to update restored save metadata: {e}")
            
            logger.info(f"Restored backup {backup_id} to save {original_id}")
            return original_id
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return None
    
    def get_save_content(self, save_id: str, is_backup: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get the content of a save file (the actual game state).
        
        Args:
            save_id: The UUID of the save.
            is_backup: Whether this is a backup save.
            
        Returns:
            Dictionary containing the game state, or None if loading failed.
        """
        save_dir = self.get_save_path(save_id, is_backup)
        state_path = os.path.join(save_dir, self.STATE_FILENAME)
        
        if not os.path.exists(state_path):
            logger.warning(f"State file not found for save {save_id}")
            return None
        
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                return enhanced_json_loads(f.read())
        except Exception as e:
            logger.error(f"Failed to load state for save {save_id}: {e}")
            return None
    
    def create_save_directory(self, save_id: str, is_backup: bool = False) -> str:
        """
        Create a new save directory structure.
        
        Args:
            save_id: The UUID of the save.
            is_backup: Whether this is a backup save.
            
        Returns:
            Path to the save directory.
        """
        save_dir = self.get_save_path(save_id, is_backup)
        os.makedirs(save_dir, exist_ok=True)
        return save_dir
    
    def save_screenshot(self, save_id: str, screenshot_data: bytes, 
                        is_backup: bool = False) -> Optional[str]:
        """
        Save a screenshot for a save file.
        
        Args:
            save_id: The UUID of the save.
            screenshot_data: The raw image data.
            is_backup: Whether this is a backup save.
            
        Returns:
            Relative path to the screenshot, or None if saving failed.
        """
        save_dir = self.get_save_path(save_id, is_backup)
        screenshots_dir = os.path.join(save_dir, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Create a filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(screenshots_dir, filename)
        
        try:
            with open(filepath, 'wb') as f:
                f.write(screenshot_data)
            
            # Return path relative to save directory
            rel_path = os.path.join("screenshots", filename)
            
            # Update metadata with screenshot path
            try:
                self.update_metadata(save_id, {"screenshot": rel_path}, is_backup)
            except Exception as e:
                logger.warning(f"Failed to update metadata with screenshot: {e}")
            
            return rel_path
            
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return None
    
    def get_screenshot_path(self, save_id: str, is_backup: bool = False) -> Optional[str]:
        """
        Get the path to the latest screenshot for a save file.
        
        Args:
            save_id: The UUID of the save.
            is_backup: Whether this is a backup save.
            
        Returns:
            Full path to the screenshot, or None if not found.
        """
        try:
            metadata = self.get_metadata(save_id, is_backup)
            if not metadata.screenshot:
                return None
            
            save_dir = self.get_save_path(save_id, is_backup)
            return os.path.join(save_dir, metadata.screenshot)
            
        except Exception as e:
            logger.warning(f"Failed to get screenshot path: {e}")
            return None
    
    def add_save_tag(self, save_id: str, tag: str, is_backup: bool = False) -> bool:
        """
        Add a tag to a save file.
        
        Args:
            save_id: The UUID of the save.
            tag: The tag to add.
            is_backup: Whether this is a backup save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            metadata = self.get_metadata(save_id, is_backup)
            if tag not in metadata.tags:
                metadata.tags.append(tag)
                
                save_dir = self.get_save_path(save_id, is_backup)
                metadata_path = os.path.join(save_dir, self.METADATA_FILENAME)
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata.to_dict(), f, indent=2, cls=EnhancedJSONEncoder)
                
                return True
            return True  # Tag already exists, consider this success
            
        except Exception as e:
            logger.error(f"Failed to add tag to save {save_id}: {e}")
            return False
    
    def remove_save_tag(self, save_id: str, tag: str, is_backup: bool = False) -> bool:
        """
        Remove a tag from a save file.
        
        Args:
            save_id: The UUID of the save.
            tag: The tag to remove.
            is_backup: Whether this is a backup save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            metadata = self.get_metadata(save_id, is_backup)
            if tag in metadata.tags:
                metadata.tags.remove(tag)
                
                save_dir = self.get_save_path(save_id, is_backup)
                metadata_path = os.path.join(save_dir, self.METADATA_FILENAME)
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata.to_dict(), f, indent=2, cls=EnhancedJSONEncoder)
                
                return True
            return True  # Tag doesn't exist, consider this success
            
        except Exception as e:
            logger.error(f"Failed to remove tag from save {save_id}: {e}")
            return False
    
    def update_save_notes(self, save_id: str, notes: str, is_backup: bool = False) -> bool:
        """
        Update user notes for a save file.
        
        Args:
            save_id: The UUID of the save.
            notes: The notes to set.
            is_backup: Whether this is a backup save.
            
        Returns:
            True if successful, False otherwise.
        """
        return bool(self.update_metadata(save_id, {"custom_notes": notes}, is_backup))
    
    def find_saves_by_tag(self, tag: str, include_backups: bool = False) -> List[SaveMetadata]:
        """
        Find saves with a specific tag.
        
        Args:
            tag: The tag to search for.
            include_backups: Whether to include backup saves.
            
        Returns:
            List of SaveMetadata objects with the specified tag.
        """
        all_saves = self.get_save_list(include_backups=include_backups)
        return [save for save in all_saves if tag in save.tags]
    
    def find_saves_by_player(self, player_name: str, include_backups: bool = False) -> List[SaveMetadata]:
        """
        Find saves for a specific player.
        
        Args:
            player_name: The player name to search for.
            include_backups: Whether to include backup saves.
            
        Returns:
            List of SaveMetadata objects for the specified player.
        """
        all_saves = self.get_save_list(include_backups=include_backups)
        return [save for save in all_saves if save.player_name.lower() == player_name.lower()]
    
    def get_recent_saves(self, count: int = 5, include_backups: bool = False) -> List[SaveMetadata]:
        """
        Get the most recent saves.
        
        Args:
            count: Maximum number of saves to return.
            include_backups: Whether to include backup saves.
            
        Returns:
            List of the most recent SaveMetadata objects.
        """
        all_saves = self.get_save_list(include_backups=include_backups)
        return all_saves[:min(count, len(all_saves))]
    
    def count_saves(self, include_backups: bool = False) -> int:
        """
        Count the number of saves.
        
        Args:
            include_backups: Whether to include backup saves.
            
        Returns:
            Number of saves.
        """
        return len(self.get_save_list(include_backups=include_backups))


# Example usage
if __name__ == "__main__":
    save_manager = SaveManager()
    
    # List available saves
    saves = save_manager.get_save_list()
    print(f"Found {len(saves)} saves:")
    for save in saves:
        print(f"  {save.save_name} ({save.formatted_save_time})")
    
    # Create a test save if none exist
    if not saves:
        print("\nCreating a test save...")
        save_id = str(uuid.uuid4())
        save_dir = save_manager.create_save_directory(save_id)
        
        # Create sample metadata
        metadata = SaveMetadata(
            save_id=save_id,
            save_name="Test Save",
            save_time=time.time(),
            version="0.1.0",
            player_name="TestPlayer",
            player_level=5,
            world_time="13:45",
            location="Test Village",
            playtime=3600.0,
            tags=["test"]
        )
        
        # Save metadata
        metadata_path = os.path.join(save_dir, SaveManager.METADATA_FILENAME)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2, cls=EnhancedJSONEncoder)
        
        # Create sample state
        state = {
            "player": {
                "name": "TestPlayer",
                "level": 5,
                "stats": {"health": 100, "mana": 50}
            },
            "world": {
                "current_location": "Test Village",
                "time": "13:45",
                "weather": "clear"
            }
        }
        
        # Save state
        state_path = os.path.join(save_dir, SaveManager.STATE_FILENAME)
        with open(state_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_json_dumps(state, indent=2))
        
        print(f"Created test save with ID: {save_id}")
        
        # Create a backup
        backup_id = save_manager.create_backup(save_id)
        print(f"Created backup with ID: {backup_id}")
        
        # List saves again
        saves = save_manager.get_save_list(include_backups=True)
        print(f"\nNow found {len(saves)} saves (including backups):")
        for save in saves:
            save_type = "Backup" if save.backup_of else "Regular"
            print(f"  {save.save_name} - {save_type} ({save.formatted_save_time})")