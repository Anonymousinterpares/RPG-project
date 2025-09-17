# world_configurator/models/origin_data.py
"""
Origin data models for starting origins.
(Formerly Scenario Data)
"""

import logging
import os
import shutil
import datetime
from typing import Dict, List, Any, Optional, Union

# Assuming Origin model exists in base_models with the new fields
from models.base_models import Origin, Quest, QuestObjective, WorldModelState
from utils.file_manager import load_json, save_json, get_world_config_dir

logger = logging.getLogger("world_configurator.models.origin_data") # Updated logger name

class OriginManager: # Renamed class
    """
    Manager for starting origin data.
    """
    def __init__(self):
        self.origins: Dict[str, Origin] = {} # Renamed variable and type hint
        self.state = WorldModelState()

    def load_from_file(self, file_path: str) -> bool:
        """
        Load origins from a JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            data = load_json(file_path)
            # Check for 'origins' key instead of 'scenarios'
            if not data or "origins" not in data:
                logger.error(f"Invalid origins file format: {file_path}")
                return False

            # Clear existing origins
            self.origins.clear() # Renamed variable

            # Load each origin
            for origin_id, origin_data in data["origins"].items(): # Use 'origins' key
                # Ensure the origin has an ID
                if "id" not in origin_data:
                    origin_data["id"] = origin_id

                origin = Origin.from_dict(origin_data) # Use Origin model
                self.origins[origin_id] = origin # Renamed variable

            # Update state
            self.state.path = file_path
            self.state.modified = False

            logger.info(f"Loaded {len(self.origins)} origins from {file_path}") # Renamed log message
            return True
        except Exception as e:
            logger.error(f"Error loading origins from {file_path}: {e}", exc_info=True) # Added exc_info
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        Save origins to a JSON file.

        Args:
            file_path: Path to the JSON file. If None, uses the path from state.

        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            # Use provided path or the one from state
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving origins")
                return False

            # Prepare data
            data = {
                # Use 'origins' key
                "origins": {k: v.to_dict() for k, v in self.origins.items()}, # Renamed variable
                "metadata": {
                    "version": "1.0.1", # Updated version
                    "description": "Starting origin definitions for the RPG game world" # Updated description
                }
            }

            # Save to file
            result = save_json(data, path)
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved {len(self.origins)} origins to {path}") # Renamed log message

            return result
        except Exception as e:
            logger.error(f"Error saving origins: {e}", exc_info=True) # Added exc_info
            return False

    def add_origin(self, origin: Origin) -> None: # Renamed method and type hint
        """
        Add an origin to the manager.

        Args:
            origin: The origin to add.
        """
        self.origins[origin.id] = origin # Renamed variable
        self.state.modified = True
        logger.info(f"Added origin: {origin.name} ({origin.id})")

    def remove_origin(self, origin_id: str) -> bool: # Renamed method
        """
        Remove an origin from the manager.

        Args:
            origin_id: The ID of the origin to remove.

        Returns:
            True if the origin was removed, False if it wasn't found.
        """
        if origin_id in self.origins: # Renamed variable
            del self.origins[origin_id] # Renamed variable
            self.state.modified = True
            logger.info(f"Removed origin: {origin_id}")
            return True
        else:
            logger.warning(f"Cannot remove non-existent origin: {origin_id}")
            return False

    def get_origin(self, origin_id: str) -> Optional[Origin]: # Renamed method and return type
        """
        Get an origin by ID.

        Args:
            origin_id: The ID of the origin to get.

        Returns:
            The origin if found, None otherwise.
        """
        return self.origins.get(origin_id) # Renamed variable

    def export_to_game(self) -> bool:
        """
        Export origins to the game's configuration directory.

        Returns:
            True if export was successful, False otherwise.
        """
        try:
            # Define target path - Changed filename
            target_dir = os.path.join(get_world_config_dir(), "scenarios") # Keep subfolder for now
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "origins.json") # Changed filename

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
            logger.error(f"Error exporting origins to game: {e}", exc_info=True) # Added exc_info
            return False

# --- QuestManager remains the same ---
# (Assuming Quest data structure hasn't changed)
# ... (Keep existing QuestManager class here) ...
class QuestManager:
    """
    Manager for quest data.
    """
    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self.state = WorldModelState()

    def load_from_file(self, file_path: str) -> bool:
        """
        Load quests from a JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            data = load_json(file_path)
            if not data or "quests" not in data:
                logger.error(f"Invalid quests file format: {file_path}")
                return False

            # Clear existing quests
            self.quests.clear()

            # Load each quest
            for quest_id, quest_data in data["quests"].items():
                # Ensure the quest has an ID
                if "id" not in quest_data:
                    quest_data["id"] = quest_id

                quest = Quest.from_dict(quest_data)
                self.quests[quest_id] = quest

            # Update state
            self.state.path = file_path
            self.state.modified = False

            logger.info(f"Loaded {len(self.quests)} quests from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading quests from {file_path}: {e}")
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        Save quests to a JSON file.

        Args:
            file_path: Path to the JSON file. If None, uses the path from state.

        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            # Use provided path or the one from state
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving quests")
                return False

            # Prepare data
            data = {
                "quests": {k: v.to_dict() for k, v in self.quests.items()},
                "metadata": {
                    "version": "1.0.0",
                    "description": "Quest definitions for the RPG game world"
                }
            }

            # Save to file
            result = save_json(data, path)
            if result:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved {len(self.quests)} quests to {path}")

            return result
        except Exception as e:
            logger.error(f"Error saving quests: {e}")
            return False

    def add_quest(self, quest: Quest) -> None:
        """
        Add a quest to the manager.

        Args:
            quest: The quest to add.
        """
        self.quests[quest.id] = quest
        self.state.modified = True
        logger.info(f"Added quest: {quest.title} ({quest.id})")

    def remove_quest(self, quest_id: str) -> bool:
        """
        Remove a quest from the manager.

        Args:
            quest_id: The ID of the quest to remove.

        Returns:
            True if the quest was removed, False if it wasn't found.
        """
        if quest_id in self.quests:
            del self.quests[quest_id]
            self.state.modified = True
            logger.info(f"Removed quest: {quest_id}")
            return True
        else:
            logger.warning(f"Cannot remove non-existent quest: {quest_id}")
            return False

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """
        Get a quest by ID.

        Args:
            quest_id: The ID of the quest to get.

        Returns:
            The quest if found, None otherwise.
        """
        quest = self.quests.get(quest_id)

        # Ensure we're returning a Quest object, not a dict
        if quest and isinstance(quest, dict):
            try:
                quest = Quest.from_dict(quest)
                self.quests[quest_id] = quest  # Update the dictionary with the object
                logger.info(f"Converted dict to Quest object for {quest_id}")
            except Exception as e:
                logger.error(f"Error converting quest dict to object for {quest_id}: {str(e)}")

        return quest

    def add_objective_to_quest(self, quest_id: str, objective: QuestObjective) -> bool:
        """
        Add an objective to a quest.

        Args:
            quest_id: The ID of the quest to modify.
            objective: The objective to add.

        Returns:
            True if the objective was added, False if the quest wasn't found.
        """
        quest = self.get_quest(quest_id)
        if not quest:
            logger.warning(f"Cannot add objective to non-existent quest: {quest_id}")
            return False

        quest.objectives.append(objective)
        self.state.modified = True
        logger.info(f"Added objective to quest {quest_id}: {objective.description}")
        return True

    def remove_objective_from_quest(self, quest_id: str, objective_id: str) -> bool:
        """
        Remove an objective from a quest.

        Args:
            quest_id: The ID of the quest to modify.
            objective_id: The ID of the objective to remove.

        Returns:
            True if the objective was removed, False if the quest or objective wasn't found.
        """
        quest = self.get_quest(quest_id)
        if not quest:
            logger.warning(f"Cannot remove objective from non-existent quest: {quest_id}")
            return False

        initial_len = len(quest.objectives)
        quest.objectives = [obj for obj in quest.objectives if obj.id != objective_id]

        if len(quest.objectives) < initial_len:
             self.state.modified = True
             logger.info(f"Removed objective {objective_id} from quest {quest_id}")
             return True
        else:
             logger.warning(f"Cannot remove non-existent objective {objective_id} from quest {quest_id}")
             return False


    def export_to_game(self) -> bool:
        """
        Export quests to the game's configuration directory.

        Returns:
            True if export was successful, False otherwise.
        """
        try:
            # Define target path
            target_dir = os.path.join(get_world_config_dir(), "scenarios") # Keep quests in scenarios subfolder for now
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "quests.json")

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
            logger.error(f"Error exporting quests to game: {e}")
            return False