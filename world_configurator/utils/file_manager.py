"""
File management utilities for the World Configurator Tool.
"""

import os
import json
import logging
import shutil
import datetime
from typing import Dict, Any, Optional, Union

logger = logging.getLogger("world_configurator.file_manager")

def get_project_root() -> str:
    """
    Get the root directory of the project.
    
    Returns:
        The absolute path to the project root directory.
    """
    # Go up from the utils directory to find project root
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.normpath(os.path.join(current_dir, ".."))

def get_config_dir() -> str:
    """
    Get the configuration directory of the project.
    
    Returns:
        The absolute path to the config directory.
    """
    return os.path.join(get_project_root(), "config")

def get_world_config_dir() -> str:
    """
    Get the world configuration directory.
    
    Returns:
        The absolute path to the world config directory.
    """
    return os.path.join(get_config_dir(), "world")

def ensure_dir_exists(directory: str) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory: The directory path to check/create.
    """
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: The path to the JSON file.
    
    Returns:
        The loaded JSON data as a dictionary, or None if loading failed.
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.debug(f"Loaded JSON from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return None

def save_json(data: Dict[str, Any], file_path: str, pretty: bool = True) -> bool:
    """
    Save JSON data to a file.
    
    Args:
        data: The data to save.
        file_path: The path to the JSON file.
        pretty: Whether to format the JSON for readability.
    
    Returns:
        True if the save was successful, False otherwise.
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save with appropriate formatting
        indent = 2 if pretty else None
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        logger.debug(f"Saved JSON to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False

def create_backup(file_path: str) -> Optional[str]:
    """
    Create a backup of a file.
    
    Args:
        file_path: The path to the file to back up.
    
    Returns:
        The path to the backup file, or None if backup failed.
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Cannot back up non-existent file: {file_path}")
            return None
        
        # Create backup filename
        backup_path = f"{file_path}.bak"
        
        # Copy file
        shutil.copy2(file_path, backup_path)
        
        logger.debug(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Error creating backup of {file_path}: {e}")
        return None

def export_to_game(source_path: str, target_subpath: str) -> bool:
    """
    Export a configuration file to the game's config directory.
    
    Args:
        source_path: The path to the source file.
        target_subpath: The subpath within the game's config directory.
    
    Returns:
        True if the export was successful, False otherwise.
    """
    try:
        if not os.path.exists(source_path):
            logger.warning(f"Source file does not exist: {source_path}")
            return False
        
        # Construct target path
        config_dir = get_config_dir()
        target_path = os.path.join(config_dir, target_subpath)
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Create backup folder if it doesn't exist
        backup_dir = os.path.join(os.path.dirname(target_path), "backup")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamped backup if target exists
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
        
        # Copy file
        shutil.copy2(source_path, target_path)
        
        logger.info(f"Exported {source_path} to {target_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting {source_path} to {target_subpath}: {e}")
        return False

def list_files_in_dir(directory: str, extension: Optional[str] = None) -> list:
    """
    List all files in a directory, optionally filtered by extension.
    
    Args:
        directory: The directory to list files from.
        extension: The file extension to filter by, or None for all files.
    
    Returns:
        A list of filenames in the directory.
    """
    try:
        if not os.path.exists(directory) or not os.path.isdir(directory):
            logger.warning(f"Directory does not exist: {directory}")
            return []
        
        if extension:
            # Filter by extension
            return [f for f in os.listdir(directory) 
                  if os.path.isfile(os.path.join(directory, f)) and f.endswith(extension)]
        else:
            # All files
            return [f for f in os.listdir(directory) 
                  if os.path.isfile(os.path.join(directory, f))]
    except Exception as e:
        logger.error(f"Error listing files in {directory}: {e}")
        return []
