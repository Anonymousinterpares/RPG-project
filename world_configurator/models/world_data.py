"""
World data models for cultures, history, and rules.
"""

import os
import shutil
import datetime
from typing import Dict, Optional

from models.base_models import CharacterClass, Culture, Race, WorldHistory, WorldRules, MagicalSystem, Spell, WorldModelState
from utils.file_manager import load_json, save_json, get_world_config_dir
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.models.world_data")

class CultureManager:
    """
    Manager for culture data.
    """
    def __init__(self):
        self.cultures: Dict[str, Culture] = {}
        self.state = WorldModelState()
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load cultures from a JSON file.
        
        Args:
            file_path: Path to the JSON file.
        
        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            data = load_json(file_path)
            if not data or "cultures" not in data:
                logger.error(f"Invalid cultures file format: {file_path}")
                return False
            
            # Clear existing cultures
            self.cultures.clear()
            
            # Load each culture
            for culture_id, culture_data in data["cultures"].items():
                # Ensure the culture has an ID
                if "id" not in culture_data:
                    culture_data["id"] = culture_id
                
                culture = Culture.from_dict(culture_data)
                self.cultures[culture_id] = culture
            
            # Update state
            self.state.path = file_path
            self.state.modified = False
            
            logger.info(f"Loaded {len(self.cultures)} cultures from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading cultures from {file_path}: {e}")
            return False
    
    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        Save cultures to a JSON file.
        
        Args:
            file_path: Path to the JSON file. If None, uses the path from state.
        
        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            # Use provided path or the one from state
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving cultures")
                return False
            
            # Prepare data
            data = {
                "cultures": {k: v.to_dict() for k, v in self.cultures.items()},
                "metadata": {
                    "version": "1.0.0",
                    "description": "Culture definitions for the RPG game world"
                }
            }
            
            # Save to file
            result = save_json(data, path)
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved {len(self.cultures)} cultures to {path}")
            
            return result
        except Exception as e:
            logger.error(f"Error saving cultures: {e}")
            return False
    
    def add_culture(self, culture: Culture) -> None:
        """
        Add a culture to the manager.
        
        Args:
            culture: The culture to add.
        """
        self.cultures[culture.id] = culture
        self.state.modified = True
        logger.info(f"Added culture: {culture.name} ({culture.id})")
    
    def remove_culture(self, culture_id: str) -> bool:
        """
        Remove a culture from the manager.
        
        Args:
            culture_id: The ID of the culture to remove.
        
        Returns:
            True if the culture was removed, False if it wasn't found.
        """
        if culture_id in self.cultures:
            del self.cultures[culture_id]
            self.state.modified = True
            logger.info(f"Removed culture: {culture_id}")
            return True
        else:
            logger.warning(f"Cannot remove non-existent culture: {culture_id}")
            return False
    
    def get_culture(self, culture_id: str) -> Optional[Culture]:
        """
        Get a culture by ID.
        
        Args:
            culture_id: The ID of the culture to get.
        
        Returns:
            The culture if found, None otherwise.
        """
        return self.cultures.get(culture_id)
    
    def export_to_game(self) -> bool:
        """
        Export cultures to the game's configuration directory.
        
        Returns:
            True if export was successful, False otherwise.
        """
        try:
            # Define target path
            target_dir = os.path.join(get_world_config_dir(), "base")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "cultures.json")
            
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
            logger.error(f"Error exporting cultures to game: {e}")
            return False

class WorldHistoryManager:
    """
    Manager for world history data.
    """
    def __init__(self):
        self.history: Optional[WorldHistory] = None
        self.state = WorldModelState()
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load world history from a JSON file.
        
        Args:
            file_path: Path to the JSON file.
        
        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            data = load_json(file_path)
            if not data:
                logger.error(f"Invalid world history file format: {file_path}")
                return False
            
            # Create history from data
            self.history = WorldHistory.from_dict(data)
            
            # Update state
            self.state.path = file_path
            self.state.modified = False
            
            logger.info(f"Loaded world history from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading world history from {file_path}: {e}")
            return False
    
    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        Save world history to a JSON file.
        
        Args:
            file_path: Path to the JSON file. If None, uses the path from state.
        
        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            # Check if we have history data
            if not self.history:
                logger.error("No world history data to save")
                return False
            
            # Use provided path or the one from state
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving world history")
                return False
            
            # Save to file
            result = save_json(self.history.to_dict(), path)
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved world history to {path}")
            
            return result
        except Exception as e:
            logger.error(f"Error saving world history: {e}")
            return False
    
    def create_new_history(self, name: str, description: str, current_year: int) -> None:
        """
        Create a new world history.
        
        Args:
            name: The name of the world.
            description: A description of the world.
            current_year: The current year in the world timeline.
        """
        self.history = WorldHistory.create_new(name, description, current_year)
        self.state.modified = True
        logger.info(f"Created new world history: {name}")
    
    def export_to_game(self) -> bool:
        """
        Export world history to the game's configuration directory.
        
        Returns:
            True if export was successful, False otherwise.
        """
        try:
            # Define target path
            target_dir = os.path.join(get_world_config_dir(), "base")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "world_history.json")
            
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
            logger.error(f"Error exporting world history to game: {e}")
            return False

class WorldRulesManager:
    """
    Manager for world rules data.
    """
    def __init__(self):
        self.rules: Optional[WorldRules] = None
        self.state = WorldModelState()
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load world rules from a JSON file.
        
        Args:
            file_path: Path to the JSON file.
        
        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            data = load_json(file_path)
            if not data:
                logger.error(f"Invalid world rules file format: {file_path}")
                return False
            
            # Create rules from data
            self.rules = WorldRules.from_dict(data)
            
            # Update state
            self.state.path = file_path
            self.state.modified = False
            
            logger.info(f"Loaded world rules from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading world rules from {file_path}: {e}")
            return False
    
    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        Save world rules to a JSON file.
        
        Args:
            file_path: Path to the JSON file. If None, uses the path from state.
        
        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            # Check if we have rules data
            if not self.rules:
                logger.error("No world rules data to save")
                return False
            
            # Use provided path or the one from state
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving world rules")
                return False
            
            # Save to file
            result = save_json(self.rules.to_dict(), path)
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved world rules to {path}")
            
            return result
        except Exception as e:
            logger.error(f"Error saving world rules: {e}")
            return False
    
    def create_new_rules(self, name: str, description: str) -> None:
        """
        Create new world rules.
        
        Args:
            name: The name of the rules set.
            description: A description of the rules.
        """
        self.rules = WorldRules.create_new(name, description)
        self.state.modified = True
        logger.info(f"Created new world rules: {name}")
    
    def export_to_game(self) -> bool:
        """
        Export world rules to the game's configuration directory.
        
        Returns:
            True if export was successful, False otherwise.
        """
        try:
            # Define target path
            target_dir = os.path.join(get_world_config_dir(), "base")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "fundamental_rules.json")
            
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
            logger.error(f"Error exporting world rules to game: {e}")
            return False

class MagicSystemManager:
    """
    Manager for magic system data.
    """
    def __init__(self):
        self.magic_systems: Dict[str, MagicalSystem] = {}
        self.state = WorldModelState()
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load magic systems from a JSON file.
        
        Args:
            file_path: Path to the JSON file.
        
        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            data = load_json(file_path)
            if not data or "magic_systems" not in data:
                logger.error(f"Invalid magic systems file format: {file_path}")
                return False
            
            # Clear existing magic systems
            self.magic_systems.clear()
            
            # Load each magic system
            for system_id, system_data in data["magic_systems"].items():
                # Ensure the magic system has an ID
                if "id" not in system_data:
                    system_data["id"] = system_id
                
                magic_system = MagicalSystem.from_dict(system_data)
                self.magic_systems[system_id] = magic_system
            
            # Update state
            self.state.path = file_path
            self.state.modified = False
            
            logger.info(f"Loaded {len(self.magic_systems)} magic systems from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading magic systems from {file_path}: {e}")
            return False
    
    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        Save magic systems to a JSON file.
        
        Args:
            file_path: Path to the JSON file. If None, uses the path from state.
        
        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            # Use provided path or the one from state
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving magic systems")
                return False
            
            # Prepare data
            data = {
                "magic_systems": {k: v.to_dict() for k, v in self.magic_systems.items()},
                "metadata": {
                    "version": "1.0.0",
                    "description": "Magic system definitions for the RPG game world"
                }
            }
            
            # Save to file
            result = save_json(data, path)
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved {len(self.magic_systems)} magic systems to {path}")
            
            return result
        except Exception as e:
            logger.error(f"Error saving magic systems: {e}")
            return False
    
    def add_magic_system(self, magic_system: MagicalSystem) -> None:
        """
        Add a magic system to the manager.
        
        Args:
            magic_system: The magic system to add.
        """
        self.magic_systems[magic_system.id] = magic_system
        self.state.modified = True
        logger.info(f"Added magic system: {magic_system.name} ({magic_system.id})")
    
    def remove_magic_system(self, system_id: str) -> bool:
        """
        Remove a magic system from the manager.
        
        Args:
            system_id: The ID of the magic system to remove.
        
        Returns:
            True if the magic system was removed, False if it wasn't found.
        """
        if system_id in self.magic_systems:
            del self.magic_systems[system_id]
            self.state.modified = True
            logger.info(f"Removed magic system: {system_id}")
            return True
        else:
            logger.warning(f"Cannot remove non-existent magic system: {system_id}")
            return False
    
    def get_magic_system(self, system_id: str) -> Optional[MagicalSystem]:
        """
        Get a magic system by ID.
        
        Args:
            system_id: The ID of the magic system to get.
        
        Returns:
            The magic system if found, None otherwise.
        """
        return self.magic_systems.get(system_id)
    
    def add_spell_to_system(self, system_id: str, spell: Spell) -> bool:
        """
        Add a spell to a magic system.
        
        Args:
            system_id: The ID of the magic system to add the spell to.
            spell: The spell to add.
        
        Returns:
            True if the spell was added, False if the magic system wasn't found.
        """
        magic_system = self.get_magic_system(system_id)
        if not magic_system:
            logger.warning(f"Cannot add spell to non-existent magic system: {system_id}")
            return False
        
        magic_system.spells[spell.id] = spell
        self.state.modified = True
        logger.info(f"Added spell '{spell.name}' to magic system '{magic_system.name}'")
        return True
    
    def remove_spell_from_system(self, system_id: str, spell_id: str) -> bool:
        """
        Remove a spell from a magic system.
        
        Args:
            system_id: The ID of the magic system to remove the spell from.
            spell_id: The ID of the spell to remove.
        
        Returns:
            True if the spell was removed, False if the magic system or spell wasn't found.
        """
        magic_system = self.get_magic_system(system_id)
        if not magic_system:
            logger.warning(f"Cannot remove spell from non-existent magic system: {system_id}")
            return False
        
        if spell_id in magic_system.spells:
            del magic_system.spells[spell_id]
            self.state.modified = True
            logger.info(f"Removed spell '{spell_id}' from magic system '{magic_system.name}'")
            return True
        else:
            logger.warning(f"Cannot remove non-existent spell '{spell_id}' from magic system '{magic_system.name}'")
            return False
    
    def get_spell(self, system_id: str, spell_id: str) -> Optional[Spell]:
        """
        Get a spell from a magic system.
        
        Args:
            system_id: The ID of the magic system to get the spell from.
            spell_id: The ID of the spell to get.
        
        Returns:
            The spell if found, None otherwise.
        """
        magic_system = self.get_magic_system(system_id)
        if not magic_system:
            return None
        
        return magic_system.spells.get(spell_id)
    
    def export_to_game(self) -> bool:
        """
        Export magic systems to the game's configuration directory.
        
        Returns:
            True if export was successful, False otherwise.
        """
        try:
            # Define target path
            target_dir = os.path.join(get_world_config_dir(), "base")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "magic_systems.json")
            
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
            logger.error(f"Error exporting magic systems to game: {e}")
            return False

class RaceManager:
    """Manager for race data."""
    def __init__(self):
        self.races: Dict[str, Race] = {}
        self.state = WorldModelState()

    def load_from_file(self, file_path: str) -> bool:
        """Load races from a JSON file."""
        try:
            data = load_json(file_path)
            if not data or "races" not in data:
                logger.error(f"Invalid races file format: {file_path}")
                self.races.clear() # Clear even if load fails partially
                return False

            self.races.clear()
            for race_key, race_data in data["races"].items():
                if "id" not in race_data: race_data["id"] = race_key
                if "name" not in race_data:
                    race_data["name"] = race_key
                race = Race.from_dict(race_data)
                self.races[race_key] = race

            self.state.path = file_path
            self.state.modified = False
            logger.info(f"Loaded {len(self.races)} races from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading races from {file_path}: {e}")
            self.races.clear()
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """Save races to a JSON file using name as the key."""
        try:
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving races")
                return False

            # This dictionary comprehension now correctly uses the name as the key
            data_to_save = {k: v.to_dict() for k, v in self.races.items()}

            final_data = {"races": data_to_save}


            result = save_json(final_data, path) # Save the structure {"races": {...}}
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved {len(self.races)} races to {path}")
            return result
        except Exception as e:
            logger.error(f"Error saving races: {e}")
            return False
        
    def add_race(self, race: Race) -> None:
        """Add a race to the manager."""
        self.races[race.name] = race
        self.state.modified = True
        logger.info(f"Added race: {race.name} ({race.id})")

    def remove_race(self, race_name: str) -> bool:
        """Remove a race from the manager."""
        if race_name in self.races:
            del self.races[race_name]
            self.state.modified = True
            logger.info(f"Removed race: {race_name}")
            return True
        else:
            logger.warning(f"Cannot remove non-existent race: {race_name}")
            return False

    def get_race(self, race_name: str) -> Optional[Race]:
        """Get a race by ID."""
        return self.races.get(race_name)

    def export_to_game(self) -> bool:
        """Export races to the game's configuration directory."""
        try:
            target_dir = os.path.join(get_world_config_dir(), "..", "character")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "races.json")

            backup_dir = os.path.join(target_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)

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

            return self.save_to_file(target_path)
        except Exception as e:
            logger.error(f"Error exporting races to game: {e}")
            return False

class ClassManager:
    """Manager for character class data."""
    def __init__(self):
        self.classes: Dict[str, CharacterClass] = {}
        self.state = WorldModelState()

    def load_from_file(self, file_path: str) -> bool:
        """Load classes from a JSON file."""
        try:
            data = load_json(file_path)
            if not data or "classes" not in data:
                logger.error(f"Invalid classes file format: {file_path}")
                self.classes.clear()
                return False

            self.classes.clear()
            for class_id, class_data in data["classes"].items():
                if "id" not in class_data: class_data["id"] = class_id
                if "name" not in class_data:
                    class_data["name"] = class_id
                char_class = CharacterClass.from_dict(class_data)
                self.classes[char_class.id] = char_class # Use class.id as key

            self.state.path = file_path
            self.state.modified = False
            logger.info(f"Loaded {len(self.classes)} classes from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading classes from {file_path}: {e}")
            self.classes.clear()
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """Save classes to a JSON file."""
        try:
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving classes")
                return False

            data = {
                "classes": {k: v.to_dict() for k, v in self.classes.items()},
                 # Optionally add metadata from JSON if needed
                # "display_colors": {...},
                # "details": {...}
            }

            result = save_json(data, path)
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved {len(self.classes)} classes to {path}")
            return result
        except Exception as e:
            logger.error(f"Error saving classes: {e}")
            return False

    def add_class(self, char_class: CharacterClass) -> None:
        """Add a class to the manager."""
        self.classes[char_class.id] = char_class
        self.state.modified = True
        logger.info(f"Added class: {char_class.name} ({char_class.id})")

    def remove_class(self, class_id: str) -> bool:
        """Remove a class from the manager."""
        if class_id in self.classes:
            del self.classes[class_id]
            self.state.modified = True
            logger.info(f"Removed class: {class_id}")
            return True
        else:
            logger.warning(f"Cannot remove non-existent class: {class_id}")
            return False

    def get_class(self, class_id: str) -> Optional[CharacterClass]:
        """Get a class by ID."""
        return self.classes.get(class_id)

    def export_to_game(self) -> bool:
        """Export classes to the game's configuration directory."""
        try:
            target_dir = os.path.join(get_world_config_dir(), "..", "character")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "classes.json")

            backup_dir = os.path.join(target_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)

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

            return self.save_to_file(target_path)
        except Exception as e:
            logger.error(f"Error exporting classes to game: {e}")
            return False
