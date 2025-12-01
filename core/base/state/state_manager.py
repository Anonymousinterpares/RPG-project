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
from core.base.state.game_state import GameState
from core.base.state.player_state import PlayerState
from core.base.state.world_state import WorldState
from typing import TYPE_CHECKING
if TYPE_CHECKING:
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
        
        # NPC System instance
        self._npc_system = None
        
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
        return self._npc_system
        
    def set_npc_system(self, npc_system: 'NPCSystem') -> None:
        """Set the NPC system instance."""
        self._npc_system = npc_system
    
    def create_new_game(self, player_name: str, race: str = "Human", 
                       path: str = "Wanderer", background: str = "Commoner",
                       sex: str = "Male", character_image: Optional[str] = None,
                       stats: Optional[Dict[str, int]] = None,
                       skills: Optional[Dict[str, int]] = None,
                       origin_id: Optional[str] = None) -> GameState:
        """
        Create a new game state and ensure a clean environment.
        """
        logger.info(f"Creating new game for player {player_name}, origin: {origin_id}")
        
        # 1. Clean NPC System (Session Isolation)
        # We must wipe any loaded NPCs from a previous session from memory.
        try:
            npc_system = self.get_npc_system()
            if npc_system:
                npc_system.clear_all_npcs()
                # We don't set a specific directory yet; that happens on the first Save.
                # However, ensuring memory is empty prevents "Ghost NPCs" from appearing.
                logger.info("NPC System memory cleared for new game.")
        except Exception as e:
            logger.warning(f"Failed to clear NPC system during new game creation: {e}")

        # 2. Create Player State
        player = PlayerState(
            name=player_name,
            race=race,
            path=path,
            background=background,
            sex=sex,
            character_image=character_image,
            stats_manager_id=str(uuid.uuid4()),
            origin_id=origin_id
        )
        
        # 3. Create World State
        world = WorldState()
        
        # 4. Create Game State
        self._current_state = GameState(
            player=player,
            world=world,
        )
        
        # 5. Initialize Stats Manager
        try:
            from core.stats.stats_manager import get_stats_manager
            self._stats_manager = get_stats_manager()
            
            # Full reset for new game
            try:
                if hasattr(self._stats_manager, 'reset_for_new_game'):
                    self._stats_manager.reset_for_new_game()
                    logger.info("StatsManager reset to a clean state for new game.")
            except Exception as e_reset:
                logger.warning(f"Failed to fully reset StatsManager for new game: {e_reset}")
            
            # --- Apply Custom Stats/Skills/Modifiers (Same logic as before) ---
            if stats:
                self._stats_manager.remove_modifiers_by_source(ModifierSource.RACIAL)
                self._stats_manager.remove_modifiers_by_source(ModifierSource.CLASS)
                for stat_name, value in stats.items():
                    try:
                        stat_type = StatType.from_string(stat_name.upper())
                        self._stats_manager.set_base_stat(stat_type, value)
                    except Exception: pass
                self._stats_manager._recalculate_derived_stats()

            if skills:
                for skill_name, rank in skills.items():
                    try:
                        skill_key = skill_name.lower().replace(" ", "_")
                        if skill_key in self._stats_manager.skills:
                            self._stats_manager.skills[skill_key].base_value = int(rank)
                    except Exception: pass

            # Apply Race Modifiers
            try:
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
                                race_modifier = StatModifier(stat=stat_type, value=modifier, source_type=ModifierSource.RACIAL, source_name=f"{race} Racial", modifier_type=ModifierType.PERMANENT)
                                self._stats_manager.add_modifier(race_modifier)
                            except Exception: pass
            except Exception: pass

            # Apply Class Modifiers
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
                                class_modifier = StatModifier(stat=stat_type, value=modifier, source_type=ModifierSource.CLASS, source_name=f"{path} Class", modifier_type=ModifierType.PERMANENT)
                                self._stats_manager.add_modifier(class_modifier)
                            except Exception: pass
            except Exception: pass
            
        except Exception as e:
            logger.error(f"Failed to initialize stats manager: {e}")
        
        # 6. Initialize Systems
        self._connect_inventory_and_stats_managers()
        self.initialize_memory_context(self._current_state)
        self.ensure_stats_manager_initialized()
        
        logger.info(f"New game created with session ID {self._current_state.session_id}")
        return self._current_state
    
    def save_game(self, filename: Optional[str] = None, 
                 auto_save: bool = False, background_summary: Optional[str] = None, 
                 last_events_summary: Optional[str] = None) -> Optional[str]:
        """
        Save the current game state into a dedicated directory.
        
        Structure:
        saves/
          {save_name}/
             state.json
             npcs/
               {npc_id}.json
        """
        if self._current_state is None:
            logger.error("Cannot save: No current game state")
            return None
        
        # Update last saved time
        self._current_state.last_saved_at = datetime.datetime.now().timestamp()
        
        # 1. Determine Save Folder Name
        if filename is None:
            player_name = self._current_state.player.name
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "auto_" if auto_save else ""
            # Sanitize filename
            safe_name = "".join(c for c in player_name if c.isalnum() or c in (' ', '_', '-')).strip()
            save_folder_name = f"{prefix}{safe_name.replace(' ', '_')}_{timestamp}"
        else:
            # Strip extension if user provided it, we are making a folder now
            save_folder_name = filename.replace(".json", "")

        # 2. Create Directory Structure
        save_dir_path = os.path.join(self._saves_dir, save_folder_name)
        npcs_dir_path = os.path.join(save_dir_path, "npcs")
        
        try:
            os.makedirs(save_dir_path, exist_ok=True)
            os.makedirs(npcs_dir_path, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create save directories at {save_dir_path}: {e}")
            return None

        # 3. Prepare State Data
        state_dict = self._current_state.to_dict()
        if background_summary:
            state_dict['player']['background_summary'] = background_summary
        if last_events_summary:
            state_dict['last_events_summary'] = last_events_summary

        # Add stats, inventory, context (same as before)
        try:
            if self.stats_manager is not None:
                state_dict['character_stats'] = self.stats_manager.to_dict()
        except Exception as e:
            logger.warning(f"Error including stats: {e}")
            
        try:
            if self._current_state.player.inventory_id:
                from core.inventory.item_manager import get_inventory_manager
                inv_manager = get_inventory_manager()
                if inv_manager:
                    state_dict['detailed_inventory'] = inv_manager.to_dict()
        except Exception as e:
            logger.warning(f"Error including inventory: {e}")

        # 4. Save Main State File
        state_file_path = os.path.join(save_dir_path, "state.json")
        try:
            save_json(state_dict, state_file_path)
            logger.info(f"Game state saved to {state_file_path}")
        except Exception as e:
            logger.error(f"Error writing state.json: {e}")
            return None

        # 5. Save NPCs to the specific folder (Snapshotting)
        # This writes current memory state to the new folder without changing active working dir
        try:
            if self.get_npc_system():
                self.get_npc_system().save_all_npcs(target_directory=npcs_dir_path)
                logger.info(f"Snapshotted NPCs to {npcs_dir_path}")
        except Exception as e:
            logger.warning(f"Error saving NPC snapshots: {e}")
            
        return save_dir_path
             
    def load_game(self, save_folder_name: str) -> Optional[GameState]:
        """
        Load a game state from a specific save folder.
        
        Args:
            save_folder_name: The name of the save directory (e.g., "Player_Level1").
        
        Returns:
            The loaded game state, or None if the load failed.
        """
        # 1. Path Resolution
        # Handle cases where full path or just name is passed
        if os.path.sep in save_folder_name:
            save_folder_name = os.path.basename(save_folder_name)
            
        # Strip extension if passed in legacy style (e.g. "save.json" -> "save")
        save_folder_name = save_folder_name.replace(".json", "")
        
        load_dir_path = os.path.join(self._saves_dir, save_folder_name)
        state_file_path = os.path.join(load_dir_path, "state.json")
        npcs_dir_path = os.path.join(load_dir_path, "npcs")

        if not os.path.exists(state_file_path):
            logger.error(f"Save state file not found: {state_file_path}")
            return None

        try:
            # 2. Load State JSON
            data = load_json(state_file_path)
            self._current_state = GameState.from_dict(data)
            
            # 3. Restore Stats (Singleton Injection)
            if 'character_stats' in data:
                try:
                    from core.stats.stats_manager import get_stats_manager
                    self._stats_manager = get_stats_manager()
                    
                    # Reset first to ensure clean slate
                    if hasattr(self._stats_manager, 'reset_for_new_game'):
                        self._stats_manager.reset_for_new_game()

                    if isinstance(data['character_stats'], dict):
                        # Restore primary stats BULK UPDATE
                        primary_stats_to_set = {}
                        for stat_type_str, stat_dict in data['character_stats'].get('stats', {}).items():
                            if 'base_value' in stat_dict:
                                try:
                                    # Resolve stat type
                                    from core.stats.registry import resolve_stat_enum
                                    from core.stats.stats_base import StatType
                                    enum_val = resolve_stat_enum(stat_type_str)
                                    if isinstance(enum_val, StatType):
                                        primary_stats_to_set[enum_val] = stat_dict['base_value']
                                    else:
                                        stat_type = StatType.from_string(stat_type_str)
                                        primary_stats_to_set[stat_type] = stat_dict['base_value']
                                except Exception as e:
                                    logger.warning(f"Failed to parse stat {stat_type_str}: {e}")
                        
                        if primary_stats_to_set:
                            self._stats_manager.set_base_stats_bulk(primary_stats_to_set)
                        
                        # Restore skills
                        skills_data = data['character_stats'].get('skills', {})
                        if skills_data:
                            for skill_key, skill_dict in skills_data.items():
                                try:
                                    normalized_key = skill_key.lower().replace(" ", "_")
                                    if normalized_key in self._stats_manager.skills:
                                        skill_stat = self._stats_manager.skills[normalized_key]
                                        skill_stat.base_value = float(skill_dict.get('base_value', 0.0))
                                        skill_stat.exp = float(skill_dict.get('exp', 0.0))
                                        skill_stat.exp_to_next = float(skill_dict.get('exp_to_next', 100.0))
                                    else:
                                        from core.stats.stats_base import Stat
                                        self._stats_manager.skills[normalized_key] = Stat.from_dict(skill_dict)
                                except Exception as e:
                                    logger.warning(f"Failed to restore skill {skill_key}: {e}")

                    # Recalculate derived stats once after all loading
                    self._stats_manager._recalculate_derived_stats()
                    logger.info("Restored character stats data from save")
                except Exception as e:
                    logger.warning(f"Error restoring character stats data: {e}")
                    
            # 4. Restore Context/Memory
            if 'memory_context' in data:
                try:
                    if hasattr(self, 'restore_memory_context_data'):
                        self.restore_memory_context_data(data['memory_context'])
                except Exception as e:
                    logger.warning(f"Error restoring memory/context data: {e}")
            
            # 5. Restore Inventory
            if 'detailed_inventory' in data:
                try:
                    from core.inventory.item_manager import get_inventory_manager
                    inv_manager = get_inventory_manager()
                    if inv_manager:
                        inv_manager.clear() # Clear before loading to prevent dupe accumulation
                        inv_manager.load_from_dict(data['detailed_inventory'])
                        
                        if not self._current_state.player.inventory_id and inv_manager.inventory_id:
                            self._current_state.player.inventory_id = inv_manager.inventory_id
                except Exception as e:
                    logger.warning(f"Error restoring detailed inventory data: {e}")
            
            # 6. Restore Quests
            if 'detailed_quests' in data:
                try:
                    if hasattr(self._current_state, 'quests'):
                        self._current_state.quests = data['detailed_quests']
                except Exception as e:
                    logger.warning(f"Error restoring quest data: {e}")
            
            # 7. Restore NPC System (Session Isolation Logic)
            try:
                npc_system = self.get_npc_system()
                if npc_system:
                    # A. Wipe current memory to prevent data bleed from previous session
                    npc_system.clear_all_npcs()
                    
                    # B. Point to the specific save folder for this session
                    if os.path.exists(npcs_dir_path):
                        npc_system.switch_save_directory(npcs_dir_path)
                        
                        # C. Load NPCs from that folder
                        npc_system.load_all_npcs()
                        logger.info(f"Loaded persistent NPCs from isolated session: {npcs_dir_path}")
                    else:
                        logger.warning(f"No NPC directory found at {npcs_dir_path}. Initializing empty persistence for this slot.")
                        # Switch directory anyway so new saves go there
                        npc_system.switch_save_directory(npcs_dir_path)
            except Exception as e:
                logger.warning(f"Error restoring NPC system state: {e}")
            
            # Connect inventory and stats managers
            self._connect_inventory_and_stats_managers()
            self.ensure_stats_manager_initialized()

            # 8. Combat Rehydration
            try:
                if self._current_state and getattr(self._current_state, 'current_mode', None) and \
                   self._current_state.current_mode.name == 'COMBAT' and \
                   getattr(self._current_state, 'combat_manager', None):
                    cm = self._current_state.combat_manager
                    cm.game_state = self._current_state
                    
                    # NPC Linkage
                    try:
                        npc_system = self.get_npc_system()
                        if npc_system:
                            # Reconstruct Missing NPCs (Dynamic enemies that weren't saved to disk yet)
                            from core.character.npc_base import NPC, NPCType
                            player_id = getattr(self._current_state.player, 'id', None) or getattr(self._current_state.player, 'stats_manager_id', None)
                            
                            for entity_id, entity in getattr(cm, 'entities', {}).items():
                                if entity_id != player_id:
                                    # Check if NPC exists in system (loaded from disk in step 7)
                                    existing_npc = npc_system.get_npc_by_id(entity_id)
                                    
                                    if not existing_npc:
                                        logger.info(f"Reconstructing transient NPC for combat entity: {entity.name} ({entity_id})")
                                        reconstructed_npc = NPC(
                                            id=entity_id,
                                            name=entity.name,
                                            npc_type=NPCType.ENEMY,
                                            is_persistent=False 
                                        )
                                        npc_system.register_npc(reconstructed_npc)
                                        
                                    # Prepare for interaction (ensure stats sync)
                                    try:
                                        npc_system.prepare_npc_for_interaction(
                                            getattr(entity, 'name', None) or getattr(entity, 'combat_name', ''),
                                        )
                                    except Exception:
                                        continue
                    except Exception as e_link:
                        logger.warning(f"NPC rehydration linkage failed: {e_link}")
                    
                    # Sync StatsManagers to saved CombatEntity values
                    try:
                        cm.sync_stats_with_managers_from_entities()
                    except Exception as e:
                        logger.warning(f"Failed to sync stats from combat entities after load: {e}")

                    # Rebuild Combat Log
                    try:
                        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
                        from core.base.engine import get_game_engine
                        engine = get_game_engine()

                        if hasattr(engine, '_combat_orchestrator') and cm is not None:
                            engine._combat_orchestrator.set_combat_manager(cm)

                        historical_log = getattr(cm, 'combat_log', [])
                        if historical_log:
                            rebuild_event = DisplayEvent(
                                type=DisplayEventType.COMBAT_LOG_REBUILD,
                                content=historical_log,
                                target_display=DisplayTarget.COMBAT_LOG,
                                source_step='REHYDRATE_FROM_SAVE',
                                metadata={"session_id": self._current_state.session_id}
                            )
                            engine._combat_orchestrator.add_event_to_queue(rebuild_event)

                        # Sync player bars (HP/Stamina/Mana)
                        self._rehydrate_player_bars(engine, cm)
                        
                    except Exception as e:
                        logger.warning(f"Failed to queue combat log rehydrate event: {e}")
            except Exception as e:
                logger.warning(f"Combat rehydrate block failed: {e}")
            
            logger.info(f"Game loaded from session: {save_folder_name}")
            return self._current_state
        except Exception as e:
            logger.error(f"Error loading game: {e}")
            return None

    def _rehydrate_player_bars(self, engine, cm):
        """Helper to queue bar updates on load."""
        try:
            from core.stats.stats_base import DerivedStatType
            from core.combat.combat_entity import EntityType
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
            
            player_entity_id = None
            for eid, e in getattr(cm, 'entities', {}).items():
                if getattr(e, 'entity_type', None) == EntityType.PLAYER:
                    player_entity_id = eid
                    break
            
            sm_local = self.stats_manager
            if player_entity_id and sm_local and hasattr(engine, '_combat_orchestrator'):
                for bar, stat_cur, stat_max in [
                    ("hp", DerivedStatType.HEALTH, DerivedStatType.MAX_HEALTH),
                    ("stamina", DerivedStatType.STAMINA, DerivedStatType.MAX_STAMINA),
                    ("mana", DerivedStatType.MANA, DerivedStatType.MAX_MANA)
                ]:
                    try:
                        cur = sm_local.get_current_stat_value(stat_cur)
                        mx = sm_local.get_stat_value(stat_max)
                        ev = DisplayEvent(
                            type=DisplayEventType.UI_BAR_UPDATE_PHASE2,
                            content={},
                            metadata={
                                "entity_id": player_entity_id, 
                                "bar_type": bar, 
                                "final_new_value": cur, 
                                "max_value": mx, 
                                "session_id": self._current_state.session_id
                            },
                            target_display=DisplayTarget.COMBAT_LOG,
                            source_step='REHYDRATE_FROM_SAVE'
                        )
                        engine._combat_orchestrator.add_event_to_queue(ev)
                    except Exception: pass
        except Exception: pass
    
    def get_available_saves(self) -> List[Dict[str, Any]]:
        """
        Get a list of available save slots (directories).
        
        This updated version scans for FOLDERS containing state.json, 
        ignoring the old flat .json files in the root saves directory.
        """
        saves = []
        try:
            if not os.path.exists(self._saves_dir):
                return []

            # Scan the directory
            for entry in os.listdir(self._saves_dir):
                full_path = os.path.join(self._saves_dir, entry)
                
                # CHECK 1: Must be a directory (New Structure)
                if os.path.isdir(full_path):
                    state_file = os.path.join(full_path, "state.json")
                    
                    # CHECK 2: Must contain state.json
                    if os.path.exists(state_file):
                        try:
                            # Read metadata from the state.json file
                            stat = os.stat(state_file)
                            with open(state_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                player_data = data.get("player", {})
                                
                                save_info = {
                                    "filename": entry, # The folder name is the ID
                                    "player_name": player_data.get("name", "Unknown"),
                                    "level": player_data.get("level", 1),
                                    "location": player_data.get("current_location", "Unknown"),
                                    "background_summary": player_data.get("background_summary"),
                                    "last_events_summary": data.get("last_events_summary"),
                                    "mod_time": stat.st_mtime,
                                    "file_size": stat.st_size,
                                    "is_auto_save": entry.startswith("auto_"),
                                    "origin_id": player_data.get("origin_id"),
                                    "display_name": f"{player_data.get('name')} - {player_data.get('current_location')}"
                                }
                                saves.append(save_info)
                        except Exception as e:
                            logger.warning(f"Skipping corrupt save folder {entry}: {e}")
        except Exception as e:
            logger.error(f"Error listing saves: {e}")
        
        # Sort by last modified time, newest first
        saves.sort(key=lambda x: x.get("mod_time", 0), reverse=True)
        return saves

    def delete_save(self, save_id: str) -> bool:
        """
        Delete a save directory.
        
        Args:
            save_id: The folder name of the save to delete.
        """
        # Strip extension if passed (legacy compatibility)
        save_id = save_id.replace(".json", "")
        target_path = os.path.join(self._saves_dir, save_id)
        
        try:
            import shutil
            if os.path.exists(target_path) and os.path.isdir(target_path):
                shutil.rmtree(target_path) # Recursively delete folder
                logger.info(f"Deleted save directory: {target_path}")
                
                # Clear undo history as we can't easily undo directory deletion
                self._last_deleted_save = None 
                return True
            else:
                logger.warning(f"Save directory not found: {target_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting save {save_id}: {e}")
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
    
    def _connect_inventory_and_stats_managers(self) -> None:
        """
        Connect the inventory manager and stats manager for equipment modifier synchronization.
        
        This establishes the bidirectional connection so that equipment changes
        automatically update stat modifiers.
        """
        try:
            # Get both managers
            stats_manager = self.stats_manager  # This property handles initialization
            
            if not stats_manager:
                logger.warning("Stats manager not available for inventory connection")
                return
            
            # Get inventory manager singleton
            from core.inventory.item_manager import get_inventory_manager
            inventory_manager = get_inventory_manager()
            
            if not inventory_manager:
                logger.warning("Inventory manager not available for stats connection")
                return
            
            # Establish bidirectional connection
            stats_manager.set_inventory_manager(inventory_manager)
            inventory_manager.set_stats_manager(stats_manager)
            
            # Trigger initial equipment modifier synchronization
            if hasattr(inventory_manager, '_equipment_modifiers') and inventory_manager._equipment_modifiers:
                stats_manager.sync_equipment_modifiers()
                logger.info("Initial equipment modifier synchronization completed")
            
            logger.info("Successfully connected inventory and stats managers")
            
        except Exception as e:
            logger.error(f"Error connecting inventory and stats managers: {e}", exc_info=True)


# Convenience function
def get_state_manager() -> StateManager:
    """Get the state manager instance."""
    return StateManager()
