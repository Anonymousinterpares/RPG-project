"""
State manager for the RPG game.

This module provides the StateManager class for managing game state.
"""

import os
import uuid
import datetime
import json
from typing import Dict, List, Optional, Any
from core.stats.stats_base import StatType
from PySide6.QtCore import QTimer
from core.base.state.game_state import GameState
from core.base.state.player_state import PlayerState
from core.base.state.world_state import WorldState
from core.character.npc_system import NPCSystem
from core.character.npc_base import NPCInteractionType
from core.stats.modifier import ModifierSource, StatModifier, ModifierType
from core.stats.stats_base import StatType
from core.utils.logging_config import get_logger
from core.utils.json_utils import save_json, load_json
from core.base.config import get_config

# Get the module logger
logger = get_logger("STATE")

class StateManager:
    """
    Manager for game state.
    
    This class handles creating, loading, and saving game states.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, saves_dir: Optional[str] = None):
        """Initialize the state manager."""
        if self._initialized:
            return
        
        # Get configuration
        config = get_config()
        self._saves_dir = saves_dir or config.get("system.save_dir", "saves")
        
        # Create saves directory if it doesn't exist
        os.makedirs(self._saves_dir, exist_ok=True)
        
        # Current game state
        self._current_state: Optional[GameState] = None
        
        # Last deleted save (for undo)
        self._last_deleted_save: Optional[Dict[str, Any]] = None
        
        # Stats manager instance (set when creating or loading a game)
        self._stats_manager = None
        
        self._initialized = True
    
    @property
    def current_state(self) -> Optional[GameState]:
        """Get the current game state."""
        return self._current_state
    
    # Compatibility property for web server
    @property
    def state(self) -> Optional[GameState]:
        """Compatibility property for web server to access the current state."""
        return self._current_state
    
    @property
    def stats_manager(self):
        """Get the stats manager for the current player."""
        if self._stats_manager is None and self._current_state is not None:
            # Get stats manager singleton
            try:
                from core.stats.stats_manager import get_stats_manager
                self._stats_manager = get_stats_manager()
                
                # Link stats manager ID with player
                if self._current_state.player.stats_manager_id is None:
                    self._current_state.player.stats_manager_id = str(uuid.uuid4())
                
                # Do not emit signals automatically here - UI components will request stats when needed
                # This prevents duplicate updates and reduces unnecessary processing
                # UI components like CharacterSheetWidget will directly request stats when needed
            except Exception as e:
                logger.error(f"Failed to initialize stats manager: {e}")
        
        return self._stats_manager
                
    def ensure_stats_manager_initialized(self):
        """Ensure the stats manager is initialized."""
        # Simply access the property to ensure initialization
        return self.stats_manager
        
    def get_npc_system(self) -> Optional['NPCSystem']:
        """Get the NPC system instance."""
        if self._npc_system is None:
            # Try to initialize NPC system if needed
            try:
                from core.character.npc_system import NPCSystem
                self._npc_system = NPCSystem()
                logger.info("NPC system initialized")
            except Exception as e:
                logger.error(f"Failed to initialize NPC system: {e}")
        
        return self._npc_system
        
    def set_npc_system(self, npc_system: 'NPCSystem') -> None:
        """Set the NPC system instance."""
        self._npc_system = npc_system
    
    def create_new_game(self, player_name: str, race: str = "Human", 
                       path: str = "Wanderer", background: str = "Commoner",
                       sex: str = "Male", character_image: Optional[str] = None,
                       stats: Optional[Dict[str, int]] = None,
                       origin_id: Optional[str] = None) -> GameState: # Added origin_id parameter
        """
        Create a new game state.
        
        Args:
            player_name: The name of the player character.
            race: The race of the player character.
            path: The class/path of the player character.
            background: The background of the player character.
            sex: The sex/gender of the player character.
            character_image: Path to the character's portrait image.
            stats: Optional dictionary of starting stats.
            origin_id: The ID of the player's chosen origin.
        
        Returns:
            The new game state.
        """
        logger.info(f"Creating new game for player {player_name}, origin: {origin_id}")
        
        # Create player state
        player = PlayerState(
            name=player_name,
            race=race,
            path=path,
            background=background,
            sex=sex,
            character_image=character_image,
            stats_manager_id=str(uuid.uuid4()),
            origin_id=origin_id # Set origin_id
        )
        
        # Create world state (default values)
        world = WorldState()
        
        # Create game state
        self._current_state = GameState(
            player=player,
            world=world,
        )
        
        # Initialize stats manager - use singleton instance
        try:
            from core.stats.stats_manager import get_stats_manager
            self._stats_manager = get_stats_manager()
            
            # Add comprehensive logging
            logger.info(f"Stats manager initialized for player {player_name}")
            
            # Log whether custom stats were provided
            if stats:
                logger.info(f"Custom stats provided for player {player_name}: {stats}")
            else:
                logger.info(f"No custom stats provided for player {player_name}, using defaults")
            
            # First clear any existing race/class modifiers if stats are being set manually
            # This helps ensure clean application of custom stats
            if stats:

                self._stats_manager.remove_modifiers_by_source(ModifierSource.RACIAL)
                self._stats_manager.remove_modifiers_by_source(ModifierSource.CLASS)
                logger.debug("Cleared existing race and class modifiers before applying custom stats")
            
            # Apply custom stats if provided
            if stats:
                for stat_name, value in stats.items():
                    try:
                        stat_type = StatType.from_string(stat_name.upper())
                        self._stats_manager.set_base_stat(stat_type, value)
                        logger.info(f"Set {stat_name} to {value} from custom stats")
                    except Exception as e:
                        logger.warning(f"Failed to set custom stat {stat_name}: {e}")
                
                # Make sure all stats are recalculated properly
                self._stats_manager._recalculate_derived_stats()
                logger.info("Recalculated derived stats after setting custom stats")
            
            # Apply race modifiers from config file
            try:
                # Load race configuration 
                import os, json
                project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                race_config_path = os.path.join(project_root, "config", "character", "races.json")
                
                if os.path.exists(race_config_path):
                    with open(race_config_path, 'r') as f:
                        race_data = json.load(f)
                        
                    if race in race_data.get("races", {}):
                        race_modifiers = race_data["races"][race].get("stat_modifiers", {})
                        for stat_name, modifier in race_modifiers.items():
                            try:
                                stat_type = StatType.from_string(stat_name.upper())
                                # Create and add the modifier instead of changing base stat
                                race_modifier = StatModifier(
                                    stat=stat_type,
                                    value=modifier,
                                    source_type=ModifierSource.RACIAL,
                                    source_name=f"{race} Racial Bonus",
                                    modifier_type=ModifierType.PERMANENT,
                                    is_percentage=False,
                                    duration=None
                                )
                                self._stats_manager.add_modifier(race_modifier)
                                logger.info(f"Applied race modifier {stat_name}: {modifier}")
                            except Exception as e:
                                logger.warning(f"Failed to apply race modifier for {stat_name}: {e}")
            except Exception as e:
                logger.warning(f"Failed to apply race modifiers: {e}")
            
            # Apply class modifiers from config file
            try:
                class_config_path = os.path.join(project_root, "config", "character", "classes.json")
                
                if os.path.exists(class_config_path):
                    with open(class_config_path, 'r') as f:
                        class_data = json.load(f)
                        
                    if path in class_data.get("classes", {}):
                        class_modifiers = class_data["classes"][path].get("stat_modifiers", {})
                        for stat_name, modifier in class_modifiers.items():
                            try:
                                stat_type = StatType.from_string(stat_name.upper())
                                # Create and add the modifier instead of changing base stat
                                class_modifier = StatModifier(
                                    stat=stat_type,
                                    value=modifier,
                                    source_type=ModifierSource.CLASS,
                                    source_name=f"{path} Class Bonus",
                                    modifier_type=ModifierType.PERMANENT,
                                    is_percentage=False,
                                    duration=None
                                )
                                self._stats_manager.add_modifier(class_modifier)
                                logger.info(f"Applied class modifier {stat_name}: {modifier}")
                            except Exception as e:
                                logger.warning(f"Failed to apply class modifier for {stat_name}: {e}")
            except Exception as e:
                logger.warning(f"Failed to apply class modifiers: {e}")
            
            # Log final stats after all modifications
            try:
                all_stats = self._stats_manager.get_all_stats()
                logger.info(f"Final character stats after creation:")
                
                # Log primary stats
                if "primary" in all_stats:
                    primary_stats_list = []
                    for stat_key, stat_data_val in all_stats['primary'].items():
                        if isinstance(stat_data_val, dict): # New structure
                            primary_stats_list.append(f"{stat_key}={stat_data_val.get('value')}")
                        else: # Old structure (direct value)
                            primary_stats_list.append(f"{stat_key}={stat_data_val}")
                    logger.info(f"Primary stats: {', '.join(primary_stats_list)}")

                # Log derived stats
                for category in ["combat", "resources", "social", "other"]:
                    if category in all_stats and all_stats[category]:
                        cat_stats_list = []
                        for stat_key, stat_data_val in all_stats[category].items():
                            if isinstance(stat_data_val, dict): # New structure
                                cat_stats_list.append(f"{stat_key}={stat_data_val.get('value')}")
                            else: # Old structure
                                 cat_stats_list.append(f"{stat_key}={stat_data_val}")
                        logger.info(f"{category.capitalize()} stats: {', '.join(cat_stats_list)}")
            except Exception as e:
                logger.error(f"Error logging final character stats: {e}")
            
        except Exception as e:
            logger.error(f"Failed to initialize stats manager: {e}")
        
        # Initialize memory/context system
        self.initialize_memory_context(self._current_state)
        
        # Explicitly ensure stats manager is initialized and signal is emitted
        self.ensure_stats_manager_initialized()
        
        logger.info(f"New game created with session ID {self._current_state.session_id}")
        return self._current_state
    
    def save_game(self, filename: Optional[str] = None, 
                 auto_save: bool = False) -> Optional[str]:
        """
        Save the current game state.
        
        This method saves the full game state including stats, memory/context information,
        equipment, and quest data if those systems are implemented.
        
        Args:
            filename: The name of the save file. If None, uses a default name.
            auto_save: Whether this is an auto-save.
        
        Returns:
            The path to the save file, or None if the save failed.
        """
        if self._current_state is None:
            logger.error("Cannot save: No current game state")
            return None
        
        # Update last saved time
        self._current_state.last_saved_at = datetime.datetime.now().timestamp()
        
        # Generate filename if not provided
        if filename is None:
            player_name = self._current_state.player.name
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "auto_" if auto_save else ""
            filename = f"{prefix}{player_name}_{timestamp}.json"
        
        # Ensure filename has .json extension
        if not filename.endswith(".json"):
            filename += ".json"
        
        # Prepare full state dict with enhanced data
        state_dict = self._current_state.to_dict()
        
        # Add stats data if available
        try:
            if self.stats_manager is not None:
                stats_data = self.stats_manager.to_dict()
                state_dict['character_stats'] = stats_data
                logger.info("Including character stats data in save")
        except Exception as e:
            logger.warning(f"Error including stats data in save: {e}")
        
        # Add memory/context data if available
        try:
            # This will be expanded when memory/context modules are implemented
            if hasattr(self, 'get_memory_context_data'):
                memory_data = self.get_memory_context_data()
                if memory_data:
                    state_dict['memory_context'] = memory_data
                    logger.info("Including memory/context data in save")
        except Exception as e:
            logger.warning(f"Error including memory/context data in save: {e}")
        
        # Add enhanced inventory/equipment data if available
        try:
            if self._current_state.player.inventory_id:
                from core.inventory.item_manager import get_inventory_manager
                inv_manager = get_inventory_manager()
                if inv_manager:
                    inventory_data = inv_manager.to_dict()
                    state_dict['detailed_inventory'] = inventory_data
                    logger.info("Including detailed inventory data in save")
        except Exception as e:
            logger.warning(f"Error including detailed inventory data in save: {e}")
        
        # Add quest data if available (future implementation)
        try:
            if hasattr(self._current_state, 'quests') and self._current_state.quests:
                state_dict['detailed_quests'] = self._current_state.quests
                logger.info("Including detailed quest data in save")
        except Exception as e:
            logger.warning(f"Error including quest data in save: {e}")
        
        # Save state
        try:
            save_path = os.path.join(self._saves_dir, filename)
            save_json(state_dict, save_path)
            
            logger.info(f"Game saved to {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Error saving game: {e}")
            return None
    
    def load_game(self, filename: str) -> Optional[GameState]:
        """
        Load a game state from a file.
        
        This method loads the full game state including stats, memory/context information,
        equipment, and quest data if those were included in the save.
        
        Args:
            filename: The name of the save file.
        
        Returns:
            The loaded game state, or None if the load failed.
        """
        # Ensure filename has .json extension
        if not filename.endswith(".json"):
            filename += ".json"
        
        # Load state
        try:
            load_path = os.path.join(self._saves_dir, filename)
            if not os.path.exists(load_path):
                logger.error(f"Save file not found: {load_path}")
                return None
            
            data = load_json(load_path)
            self._current_state = GameState.from_dict(data)
            
            # Restore stats data if available
            if 'character_stats' in data:
                try:
                    from core.stats.stats_manager import get_stats_manager
                    self._stats_manager = get_stats_manager()
                    # Load saved stats into the singleton instance
                    if isinstance(data['character_stats'], dict):
                        for stat_type, stat_dict in data['character_stats'].get('stats', {}).items():
                            if 'base_value' in stat_dict:
                                try:
                                    self._stats_manager.set_base_stat(stat_type, stat_dict['base_value'])
                                except Exception as e:
                                    logger.warning(f"Failed to restore stat {stat_type}: {e}")
                    # Make sure to recalculate derived stats and emit signal
                    self._stats_manager._recalculate_derived_stats()
                    logger.info("Recalculated derived stats and emitted stats_changed signal")
                    logger.info("Restored character stats data from save")
                except Exception as e:
                    logger.warning(f"Error restoring character stats data: {e}")
                    
            # Restore memory/context data if available
            if 'memory_context' in data:
                try:
                    # This will be expanded when memory/context modules are implemented
                    if hasattr(self, 'restore_memory_context_data'):
                        self.restore_memory_context_data(data['memory_context'])
                        logger.info("Restored memory/context data from save")
                except Exception as e:
                    logger.warning(f"Error restoring memory/context data: {e}")
            
            # Restore detailed inventory/equipment data if available
            if 'detailed_inventory' in data:
                try:
                    from core.inventory.item_manager import get_inventory_manager
                    inv_manager = get_inventory_manager()
                    if inv_manager:
                        inv_manager.load_from_dict(data['detailed_inventory'])
                        logger.info("Restored detailed inventory data from save")
                        
                        # Update inventory ID in player state if needed
                        if not self._current_state.player.inventory_id and inv_manager.inventory_id:
                            self._current_state.player.inventory_id = inv_manager.inventory_id
                except Exception as e:
                    logger.warning(f"Error restoring detailed inventory data: {e}")
            
            # Restore quest data if available (future implementation)
            if 'detailed_quests' in data:
                try:
                    # This would set up the quest manager when implemented
                    if hasattr(self._current_state, 'quests'):
                        self._current_state.quests = data['detailed_quests']
                        logger.info("Restored detailed quest data from save")
                except Exception as e:
                    logger.warning(f"Error restoring quest data: {e}")
            
            # Explicitly ensure stats manager is initialized and signal is emitted
            self.ensure_stats_manager_initialized()

            # If we loaded during combat, rehydrate the combat UI and sync stats
            try:
                if self._current_state and getattr(self._current_state, 'current_mode', None) and \
                   self._current_state.current_mode.name == 'COMBAT' and \
                   getattr(self._current_state, 'combat_manager', None):
                    cm = self._current_state.combat_manager
                    # Ensure NPC StatsManagers are available/linked by loading NPC system state and prepping NPCs
                    try:
                        npc_system = self.get_npc_system()
                        if npc_system:
                            # Load NPCs from persistence if available (best effort)
                            try:
                                npc_system.load_state()
                            except Exception as e_load_npcs:
                                logger.warning(f"NPCSystem.load_state failed during load_game: {e_load_npcs}")
                            # Prepare each non-player entity for combat to guarantee StatsManagers exist (fallback by name)
                            try:
                                player_id = getattr(self._current_state.player, 'id', None) or getattr(self._current_state.player, 'stats_manager_id', None)
                                for entity_id, entity in getattr(cm, 'entities', {}).items():
                                    if entity_id != player_id:
                                        try:
                                            npc_system.prepare_npc_for_interaction(
                                                getattr(entity, 'name', None) or getattr(entity, 'combat_name', ''),
                                                NPCInteractionType.COMBAT
                                            )
                                        except Exception:
                                            # Best-effort per-entity; continue on errors
                                            continue
                            except Exception as e_prep:
                                logger.warning(f"Error preparing NPCs for combat after load: {e_prep}")
                    except Exception as e_link:
                        logger.warning(f"NPC StatsManager linkage step failed: {e_link}")
                    # Sync StatsManagers to saved CombatEntity values
                    try:
                        cm.sync_stats_with_managers_from_entities()
                    except Exception as e:
                        logger.warning(f"Failed to sync stats from combat entities after load: {e}")

                    # Queue a BUFFER_FLUSH to repopulate the Combat Log from display_log
                    try:
                        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
                        from core.base.engine import get_game_engine
                        engine = get_game_engine()
                        # Bind orchestrator to the loaded CombatManager so resume signals work
                        try:
                            if hasattr(engine, '_combat_orchestrator') and cm is not None:
                                engine._combat_orchestrator.set_combat_manager(cm)
                                logger.info("Bound loaded CombatManager to CombatOutputOrchestrator.")
                        except Exception as bind_err:
                            logger.warning(f"Failed to bind CombatManager to orchestrator after load: {bind_err}")
                        html_snapshot = getattr(cm, 'display_log_html', "")
                        if html_snapshot:
                            set_event = DisplayEvent(
                                type=DisplayEventType.COMBAT_LOG_SET_HTML,
                                content=html_snapshot,
                                role='system',
                                target_display=DisplayTarget.COMBAT_LOG,
                                gradual_visual_display=False,
                                tts_eligible=False,
                                source_step='REHYDRATE_FROM_SAVE'
                            )
                            # Schedule enqueue asynchronously to avoid processing during load call stack
                            try:
                                QTimer.singleShot(0, lambda se=set_event: engine._combat_orchestrator.add_event_to_queue(se))
                            except Exception:
                                engine._combat_orchestrator.add_event_to_queue(set_event)
                        # Additionally, sync the player's resource bars (HP/MP/Stamina) via Phase 2 UI events
                        try:
                            from core.stats.stats_base import DerivedStatType
                            from core.combat.combat_entity import EntityType
                            player_entity_id = None
                            for eid, e in getattr(cm, 'entities', {}).items():
                                if getattr(e, 'entity_type', None) == EntityType.PLAYER:
                                    player_entity_id = eid
                                    break
                            sm_local = self.stats_manager
                            if player_entity_id and sm_local and hasattr(engine, '_combat_orchestrator'):
                                # Build and enqueue Phase 2 events for HP, Stamina, and Mana
                                try:
                                    hp_cur = sm_local.get_current_stat_value(DerivedStatType.HEALTH)
                                    hp_max = sm_local.get_stat_value(DerivedStatType.MAX_HEALTH)
                                    ev_hp = DisplayEvent(
                                        type=DisplayEventType.UI_BAR_UPDATE_PHASE2,
                                        content={},
                                        metadata={"entity_id": player_entity_id, "bar_type": "hp", "final_new_value": hp_cur, "max_value": hp_max},
                                        target_display=DisplayTarget.COMBAT_LOG
                                    )
                                    try:
                                        QTimer.singleShot(0, lambda e=ev_hp: engine._combat_orchestrator.add_event_to_queue(e))
                                    except Exception:
                                        engine._combat_orchestrator.add_event_to_queue(ev_hp)
                                except Exception:
                                    pass
                                try:
                                    stam_cur = sm_local.get_current_stat_value(DerivedStatType.STAMINA)
                                    stam_max = sm_local.get_stat_value(DerivedStatType.MAX_STAMINA)
                                    ev_st = DisplayEvent(
                                        type=DisplayEventType.UI_BAR_UPDATE_PHASE2,
                                        content={},
                                        metadata={"entity_id": player_entity_id, "bar_type": "stamina", "final_new_value": stam_cur, "max_value": stam_max},
                                        target_display=DisplayTarget.COMBAT_LOG
                                    )
                                    try:
                                        QTimer.singleShot(0, lambda e=ev_st: engine._combat_orchestrator.add_event_to_queue(e))
                                    except Exception:
                                        engine._combat_orchestrator.add_event_to_queue(ev_st)
                                except Exception:
                                    pass
                                try:
                                    mana_cur = sm_local.get_current_stat_value(DerivedStatType.MANA)
                                    mana_max = sm_local.get_stat_value(DerivedStatType.MAX_MANA)
                                    ev_mp = DisplayEvent(
                                        type=DisplayEventType.UI_BAR_UPDATE_PHASE2,
                                        content={},
                                        metadata={"entity_id": player_entity_id, "bar_type": "mana", "final_new_value": mana_cur, "max_value": mana_max},
                                        target_display=DisplayTarget.COMBAT_LOG
                                    )
                                    try:
                                        QTimer.singleShot(0, lambda e=ev_mp: engine._combat_orchestrator.add_event_to_queue(e))
                                    except Exception:
                                        engine._combat_orchestrator.add_event_to_queue(ev_mp)
                                except Exception:
                                    pass
                        except Exception as e_syncbars:
                            logger.warning(f"Failed to enqueue player resource bar sync events after load: {e_syncbars}")
                    except Exception as e:
                        logger.warning(f"Failed to queue combat log rehydrate event: {e}")
            except Exception as e:
                logger.warning(f"Combat rehydrate block failed: {e}")
            
            logger.info(f"Game loaded from {load_path}")
            return self._current_state
        except Exception as e:
            logger.error(f"Error loading game: {e}")
            return None
    
    def get_available_saves(self) -> List[Dict[str, Any]]:
        """
        Get a list of available save files.
        
        Returns:
            A list of dictionaries with information about each save file.
        """
        saves = []
        
        try:
            for filename in os.listdir(self._saves_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self._saves_dir, filename)
                    try:
                        # Get file info
                        stat = os.stat(file_path)
                        
                        # Try to read basic save info without loading the whole state
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                            # Extract basic info
                            save_info = {
                                "filename": filename,
                                "player_name": data.get("player", {}).get("name", "Unknown"),
                                "level": data.get("player", {}).get("level", 1),
                                "created_at": data.get("created_at", 0),
                                "last_saved_at": data.get("last_saved_at", 0),
                                "location": data.get("player", {}).get("current_location", "Unknown"),
                                "file_size": stat.st_size,
                                "mod_time": stat.st_mtime,
                                "is_auto_save": filename.startswith("auto_"),
                            }
                            
                            saves.append(save_info)
                    except Exception as e:
                        logger.warning(f"Error reading save file {filename}: {e}")
                        # Include basic file info even if we couldn't read the full save
                        saves.append({
                            "filename": filename,
                            "mod_time": os.path.getmtime(file_path),
                            "file_size": os.path.getsize(file_path),
                            "error": str(e),
                        })
        except Exception as e:
            logger.error(f"Error listing save files: {e}")
        
        # Sort by last modified time, newest first
        saves.sort(key=lambda x: x.get("mod_time", 0), reverse=True)
        
        return saves
    
    def delete_save(self, filename: str) -> bool:
        """
        Delete a save file.
        
        Args:
            filename: The name of the save file.
        
        Returns:
            True if the file was deleted, False otherwise.
        """
        # Ensure filename has .json extension
        if not filename.endswith(".json"):
            filename += ".json"
        
        # Delete the file
        try:
            file_path = os.path.join(self._saves_dir, filename)
            
            # Store file info for undo
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self._last_deleted_save = {
                        "filename": filename,
                        "content": f.read(),
                    }
            
            # Delete the file
            os.remove(file_path)
            
            logger.info(f"Save file deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting save file: {e}")
            return False
    
    def undo_delete(self) -> bool:
        """
        Undo the last save file deletion.
        
        Returns:
            True if the deletion was undone, False otherwise.
        """
        if self._last_deleted_save is None:
            logger.warning("No save file deletion to undo")
            return False
        
        try:
            filename = self._last_deleted_save["filename"]
            content = self._last_deleted_save["content"]
            
            file_path = os.path.join(self._saves_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Restored deleted save file: {file_path}")
            
            # Clear the stored deleted save
            self._last_deleted_save = None
            
            return True
        except Exception as e:
            logger.error(f"Error restoring deleted save file: {e}")
            return False

    def initialize_memory_context(self, game_state: GameState) -> None:
        """
        Initialize memory and context system for a new game state.
        
        This is a stub method that will be implemented when the memory/context
        system is fully developed. For now, it does nothing but log the call.
        
        Args:
            game_state: The game state to initialize memory/context for.
        """
        logger.info("Memory/context initialization stub called (not fully implemented)")
        # Will be implemented when memory/context modules are added
    
    def get_memory_context_data(self) -> Optional[Dict[str, Any]]:
        """
        Get memory and context data for saving.
        
        This is a stub method that will be implemented when the memory/context
        system is fully developed. For now, it returns minimal placeholder data.
        
        Returns:
            A dictionary of memory/context data, or None if not available.
        """
        logger.info("Memory/context data retrieval stub called (not fully implemented)")
        # Placeholder for future implementation
        return {
            "version": "0.1.0",
            "memory_entries": [],
            "context_state": {}
        }
    
    def restore_memory_context_data(self, data: Dict[str, Any]) -> None:
        """
        Restore memory and context data from a save.
        
        This is a stub method that will be implemented when the memory/context
        system is fully developed. For now, it does nothing but log the call.
        
        Args:
            data: The memory/context data to restore.
        """
        logger.info("Memory/context restoration stub called (not fully implemented)")
        # Will be implemented when memory/context modules are added


# Convenience function
def get_state_manager() -> StateManager:
    """Get the state manager instance."""
    return StateManager()
