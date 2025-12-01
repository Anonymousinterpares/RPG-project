#!/usr/bin/env python3
"""
Resource manager for the RPG game GUI.
This module provides a centralized system for loading and managing GUI resources.
"""

import os
from typing import Dict, Optional, List, Tuple

from PySide6.QtGui import QPixmap, QIcon, QMovie # Added QMovie
from PySide6.QtCore import QSize

from core.utils.logging_config import get_logger # Added QByteArray for QMovie\

logger = get_logger("GUI")
class ResourceManager:
    """Manages the loading and caching of GUI resources."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the resource manager."""
        # Cache for loaded resources
        self._pixmap_cache: Dict[str, QPixmap] = {}
        self._icon_cache: Dict[str, QIcon] = {}
        self._movie_cache: Dict[str, QMovie] = {} # Added movie cache

        # Base paths
        self.gui_path = os.path.join("images", "gui")
        self.background_path = os.path.join(self.gui_path, "background") # --- ADDED ---
        
    def get_pixmap(self, name: str, default_size: Optional[QSize] = None) -> QPixmap:
        """
        Get a pixmap resource.
        
        Args:
            name: The resource name (without path or extension)
            default_size: Optional default size for the pixmap
            
        Returns:
            The loaded pixmap
        """
        # Check cache first
        if name in self._pixmap_cache:
            pixmap = self._pixmap_cache[name]
            if default_size and not pixmap.isNull():
                pixmap = pixmap.scaled(default_size)
            return pixmap
        
        # Try to load the resource
        full_path = os.path.join(self.gui_path, f"{name}.png")
        
        try:
            pixmap = QPixmap(full_path)
            
            if pixmap.isNull():
                logger.warning(f"Failed to load pixmap: {full_path}")
                # Return an empty pixmap
                pixmap = QPixmap()
            else:
                # Cache the resource
                self._pixmap_cache[name] = pixmap
                
            # Scale if needed
            if default_size and not pixmap.isNull():
                pixmap = pixmap.scaled(default_size)
                
            return pixmap
            
        except Exception as e:
            logger.error(f"Error loading pixmap {full_path}: {e}")
            return QPixmap()
    
    def get_icon(self, name: str) -> QIcon:
        """
        Get an icon resource.
        
        Args:
            name: The resource name (without path or extension)
            
        Returns:
            The loaded icon
        """
        # Check cache first
        if name in self._icon_cache:
            return self._icon_cache[name]
        
        # Try to load the resource
        try:
            # For button states, check for specific state images
            states = {
                "normal": f"{name}.png",
                "hover": f"{name}_hover.png",
                "pressed": f"{name}_pressed.png",
                "disabled": f"{name}_disabled.png"
            }
            
            # Create icon
            icon = QIcon()
            
            # Add states if they exist
            for state_name, filename in states.items():
                full_path = os.path.join(self.gui_path, filename)
                if os.path.exists(full_path):
                    pixmap = QPixmap(full_path)
                    if not pixmap.isNull():
                        if state_name == "normal":
                            icon.addPixmap(pixmap, QIcon.Normal, QIcon.Off)
                        elif state_name == "hover":
                            icon.addPixmap(pixmap, QIcon.Active, QIcon.Off)
                        elif state_name == "pressed":
                            icon.addPixmap(pixmap, QIcon.Selected, QIcon.Off)
                        elif state_name == "disabled":
                            icon.addPixmap(pixmap, QIcon.Disabled, QIcon.Off)
            
            # If no states were added, try to add the base name
            if icon.isNull():
                pixmap = self.get_pixmap(name)
                if not pixmap.isNull():
                    icon.addPixmap(pixmap)
            
            # Cache the icon
            self._icon_cache[name] = icon
            
            return icon
            
        except Exception as e:
            logger.error(f"Error loading icon {name}: {e}")
            return QIcon()
    

    def list_background_names(self) -> List[Tuple[str, str]]:
        """List available background image/animation names and their extensions."""
        backgrounds = []
        if not os.path.isdir(self.background_path):
            logger.warning(f"Background directory not found: {self.background_path}")
            return backgrounds
        try:
            for filename in os.listdir(self.background_path):
                name, ext = os.path.splitext(filename)
                ext_lower = ext.lower()
                if ext_lower in [".png", ".gif"]:
                    backgrounds.append((name, ext)) # Store name and extension
        except Exception as e:
            logger.error(f"Error listing backgrounds in {self.background_path}: {e}")
        return sorted(backgrounds, key=lambda x: x[0]) # Sort by name

    def get_background_pixmap(self, name: str) -> QPixmap:
        """
        Get a pixmap resource specifically from the background directory.

        Args:
            name: The resource name (without path or extension)

        Returns:
            The loaded pixmap
        """
        cache_key = f"background_{name}"
        # Check cache first
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]

        # Try to load the resource
        full_path = os.path.join(self.background_path, f"{name}.png")

        try:
            pixmap = QPixmap(full_path)

            if pixmap.isNull():
                logger.warning(f"Failed to load background pixmap: {full_path}")
                pixmap = QPixmap() # Return an empty pixmap
            else:
                # Cache the resource
                self._pixmap_cache[cache_key] = pixmap

            return pixmap

        except Exception as e:
            logger.error(f"Error loading background pixmap {full_path}: {e}")
            return QPixmap()

    def get_background_movie(self, name: str) -> QMovie:
        """
        Get a QMovie resource specifically from the background directory.

        Args:
            name: The resource name (without path or extension)

        Returns:
            The loaded QMovie
        """
        cache_key = f"background_movie_{name}"
        # Check cache first
        if cache_key in self._movie_cache:
            # Return a new QMovie instance pointing to the same data if needed,
            # but for simplicity, let's assume sharing the instance is okay for now.
            # If issues arise, create new QMovie(self._movie_cache[cache_key].fileName())
            return self._movie_cache[cache_key]

        # Try to load the resource
        full_path = os.path.join(self.background_path, f"{name}.gif")

        try:
            # QMovie needs the path, not raw data like QPixmap sometimes uses
            movie = QMovie(full_path)

            if not movie.isValid():
                logger.warning(f"Failed to load or invalid background movie: {full_path}")
                # Return an empty/invalid movie
                return QMovie()
            else:
                # Cache the resource
                self._movie_cache[cache_key] = movie
                return movie

        except Exception as e:
            logger.error(f"Error loading background movie {full_path}: {e}")
            return QMovie()

    def get_gif_path(self, name: str) -> str:
        """
        Get the full path to a GIF resource.

        Args:
            name: The resource name (without path or extension)

        Returns:
            The full path to the GIF file, or an empty string if not found.
        """
        # Construct the full path
        full_path = os.path.join(self.gui_path, f"{name}.gif")
        
        # Check if the file exists
        if os.path.exists(full_path):
            return full_path
        else:
            logger.warning(f"GIF resource not found: {full_path}")
            return ""

    def clear_cache(self):
        """Clear the resource cache."""
        self._pixmap_cache.clear()
        self._icon_cache.clear()
        self._movie_cache.clear() # Clear movie cache

# Global instance for easy access
def get_resource_manager() -> ResourceManager:
    """Get the singleton resource manager instance."""
    return ResourceManager()
