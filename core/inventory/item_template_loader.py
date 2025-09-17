#!/usr/bin/env python3
"""
Item template loader module.

This module provides functionality for loading item templates
from configuration files.
"""

from typing import Dict, List, Optional, Any, Union, Set
import os
import json
import logging
from pathlib import Path

from core.utils.logging_config import get_logger
from core.inventory.item import Item
from core.inventory.item_enums import ItemType, ItemRarity, EquipmentSlot
from core.inventory.item_stat import ItemStat
from core.inventory.item_serialization import dict_to_item
from core.base.config import get_config

# Get module logger
logger = get_logger("Inventory")


class ItemTemplateLoader:
    """
    Loader for item templates.
    
    This class handles loading item templates from configuration files.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ItemTemplateLoader, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance._initializing = False
        return cls._instance
    
    def __init__(self):
        """Initialize the template loader."""
        # Prevent re-entrant initialization during first construction
        if getattr(self, "_initializing", False) or getattr(self, "_initialized", False):
            return
        
        self._initializing = True
        try:
            logger.info("Initializing ItemTemplateLoader")
            
            # Get configuration
            self._config = get_config()
            
            # Item templates
            self._templates: Dict[str, Item] = {}
            
            # Cache of available item icons by category
            self._icon_paths: Dict[str, List[str]] = {}
            
            # Set up directory paths
            self._templates_dir = self._config.get("paths", {}).get(
                "item_templates", os.path.join("config", "items")
            )
            self._icons_dir = self._config.get("paths", {}).get(
                "item_icons", os.path.join("images", "items")
            )
            
            # Load templates and scan for icons
            self._load_templates()
            self._scan_icon_paths()
            
            self._initialized = True
            logger.info(f"ItemTemplateLoader initialized with {len(self._templates)} templates")
        finally:
            self._initializing = False
    
    def _load_templates(self) -> None:
        """Load item templates from configuration files."""
        if not os.path.exists(self._templates_dir):
            logger.warning(f"Item templates directory not found: {self._templates_dir}")
            return
        
        # Find all JSON files in the templates directory
        template_files = []
        for root, _, files in os.walk(self._templates_dir):
            for file in files:
                if file.endswith(".json"):
                    template_files.append(os.path.join(root, file))
        
        # Load each template file
        for filepath in template_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle single template or array of templates
                templates_data = data if isinstance(data, list) else [data]
                
                for template_data in templates_data:
                    try:
                        # Generate a template ID if not provided
                        if "id" not in template_data:
                            # Use filename as part of the ID
                            filename = os.path.basename(filepath)
                            name = template_data.get("name", "unknown")
                            template_data["id"] = f"template_{filename}_{name}".lower().replace(" ", "_")
                        
                        # Mark as template
                        template_data["is_template"] = True
                        
                        # Convert to Item
                        template = dict_to_item(template_data)
                        
                        # Store in templates dictionary
                        self._templates[template.id] = template
                        
                    except Exception as e:
                        logger.error(f"Error processing template in {filepath}: {e}")
                
            except Exception as e:
                logger.error(f"Error loading template file {filepath}: {e}")
        
        logger.info(f"Loaded {len(self._templates)} item templates from {len(template_files)} files")
    
    def _scan_icon_paths(self) -> None:
        """Scan for available item icons and categorize them."""
        if not os.path.exists(self._icons_dir):
            logger.warning(f"Item icons directory not found: {self._icons_dir}")
            return
        
        # Reset icon paths
        self._icon_paths = {}
        
        # Walk through the icons directory
        for root, _, files in os.walk(self._icons_dir):
            relative_path = os.path.relpath(root, self._icons_dir)
            category = relative_path if relative_path != "." else "general"
            
            # Get image files
            image_files = [os.path.join(root, file) for file in files 
                           if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            
            if image_files:
                self._icon_paths[category] = image_files
        
        # Log results
        total_icons = sum(len(icons) for icons in self._icon_paths.values())
        logger.info(f"Found {total_icons} item icons in {len(self._icon_paths)} categories")
    
    def reload_templates(self) -> None:
        """Reload item templates from configuration files."""
        self._templates = {}
        self._load_templates()
        logger.info(f"Reloaded {len(self._templates)} item templates")
    
    def get_template(self, template_id: str) -> Optional[Item]:
        """
        Get a template by ID.
        
        Args:
            template_id: The ID of the template.
            
        Returns:
            The Item template, or None if not found.
        """
        return self._templates.get(template_id)
    
    def get_all_templates(self) -> Dict[str, Item]:
        """
        Get all available templates.
        
        Returns:
            Dictionary mapping template IDs to Item templates.
        """
        return dict(self._templates)
    
    def get_templates_by_type(self, item_type: Union[ItemType, str]) -> Dict[str, Item]:
        """
        Get templates of a specific type.
        
        Args:
            item_type: The type of items to get.
            
        Returns:
            Dictionary mapping template IDs to Item templates of the specified type.
        """
        # Convert string to enum if needed
        if isinstance(item_type, str):
            try:
                item_type = ItemType(item_type)
            except ValueError:
                logger.warning(f"Invalid item type: {item_type}")
                return {}
        
        # Filter templates by type
        return {template_id: template for template_id, template in self._templates.items()
                if template.item_type == item_type}
    
    def get_templates_by_criteria(self, **criteria) -> Dict[str, Item]:
        """
        Get templates matching specific criteria.
        
        Args:
            **criteria: Criteria to match, e.g., rarity=ItemRarity.RARE, is_equippable=True
            
        Returns:
            Dictionary mapping template IDs to matching Item templates.
        """
        # Special handling for item_type and rarity which might be strings
        if "item_type" in criteria and isinstance(criteria["item_type"], str):
            try:
                criteria["item_type"] = ItemType(criteria["item_type"])
            except ValueError:
                logger.warning(f"Invalid item type: {criteria['item_type']}")
                return {}
        
        if "rarity" in criteria and isinstance(criteria["rarity"], str):
            try:
                criteria["rarity"] = ItemRarity(criteria["rarity"])
            except ValueError:
                logger.warning(f"Invalid item rarity: {criteria['rarity']}")
                return {}
        
        # Filter templates by criteria
        result = {}
        for template_id, template in self._templates.items():
            matches = True
            for key, value in criteria.items():
                template_value = getattr(template, key, None)
                if template_value != value:
                    matches = False
                    break
            
            if matches:
                result[template_id] = template
        
        return result
    
    def get_random_icon_path(self, category: str = "general") -> Optional[str]:
        """
        Get a random icon path for a category.
        
        Args:
            category: The icon category.
            
        Returns:
            A random icon path, or None if no icons are available.
        """
        icon_paths = self._icon_paths.get(category, [])
        if not icon_paths:
            # Try general category as fallback
            icon_paths = self._icon_paths.get("general", [])
            if not icon_paths:
                return None
        
        return random.choice(icon_paths)
    
    def get_icon_categories(self) -> List[str]:
        """
        Get available icon categories.
        
        Returns:
            List of available icon categories.
        """
        return list(self._icon_paths.keys())


# Convenience function
def get_item_template_loader() -> ItemTemplateLoader:
    """Get the item template loader instance."""
    return ItemTemplateLoader()
