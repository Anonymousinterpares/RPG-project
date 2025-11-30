#!/usr/bin/env python3
"""
NPC System - Main integration module for the NPC subsystem.
Provides a unified interface for NPC management, creation, persistence, and memory.
"""

from typing import Dict, List, Any, Optional, Union, Tuple

from core.character.npc_base import NPC, NPCRelationship, NPCInteractionType, NPCMemory
from core.character.npc_manager import get_npc_manager # Import singleton getter
from core.character.npc_creator import NPCCreator
from core.character.npc_persistence import NPCPersistence
from core.character.npc_memory import NPCMemoryManager
from core.utils.logging_config import get_logger

logger = get_logger(__name__)

class NPCSystem:
    """
    Main class for the NPC subsystem.
    Integrates NPC management, creation, persistence, and memory into a single interface.
    """
    
    def __init__(self, save_directory: str = "saves/npcs"):
        """
        Initialize the NPC system.
        
        Args:
            save_directory: Directory for saving NPC data
        """
        # Initialize storage for direct access fallbacks
        self.npcs: Dict[str, NPC] = {}
        self.npc_list: List[NPC] = []
        
        # Initialize all the component managers
        # Use the singleton getter to ensure shared state across system instances
        self.manager = get_npc_manager()
        # If save_directory differs from default and manager wasn't init with it, update it
        if save_directory != "saves/npcs" and self.manager.save_directory == "saves/npcs":
             self.manager.save_directory = save_directory

        self.creator = NPCCreator(self.manager)
        self.persistence = NPCPersistence(self.manager)
        self.memory = NPCMemoryManager(self.manager)
        
        logger.info("NPC system initialized")
    
    def load_all_npcs(self) -> int:
        """Load all persisted NPCs."""
        return self.persistence.load_all_npcs()
    
    def save_all_npcs(self) -> Tuple[int, int]:
        """Save all persistent NPCs."""
        return self.persistence.save_all_persistent_npcs()
    
    def clear_all_npcs(self) -> None:
        """Clear all NPCs from the system."""
        self.manager.clear_all()
        self.npcs.clear()
        self.npc_list.clear()
    
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """Get an NPC by ID."""
        return self.manager.get_npc_by_id(npc_id)
    
    def get_npc_by_id(self, npc_id: str) -> Optional[NPC]:
        """Retrieves an NPC instance by its unique ID."""
        # First try the main manager (which is the singleton now)
        npc = self.manager.get_npc_by_id(npc_id)
        if npc:
            return npc
        
        # Fallback to direct storage
        if npc_id in self.npcs:
            return self.npcs[npc_id]
        
        # Fallback to list search
        for npc in self.npc_list:
            if getattr(npc, 'id', None) == npc_id:
                return npc
        
        return None
    
    def get_npc_by_name(self, name: str) -> Optional[NPC]:
        """Get an NPC by name."""
        return self.manager.get_npc_by_name(name)
    
    def get_npcs_by_location(self, location: str) -> List[NPC]:
        """
        Get all NPCs at a specific location.
        
        Args:
            location: The location to check
            
        Returns:
            List of NPCs at the location
        """
        return self.manager.get_npcs_by_location(location)
    
    def get_or_create_npc(self, 
                         name: str, 
                         interaction_type: NPCInteractionType,
                         location: Optional[str] = None,
                         npc_subtype: Optional[str] = None) -> Tuple[NPC, bool]:
        """Get an existing NPC by name or create a new one."""
        npc, is_new = self.creator.get_or_create_npc(
            name=name,
            interaction_type=interaction_type,
            location=location,
            npc_subtype=npc_subtype
        )
        # Register in direct storage if newly created
        if npc and is_new:
            self.register_npc(npc)
        return npc, is_new
    
    def prepare_npc_for_interaction(self, 
                                   npc_or_name: Union[NPC, str],
                                   interaction_type: NPCInteractionType,
                                   npc_subtype: Optional[str] = None) -> Optional[NPC]:
        """Prepare an NPC for a specific interaction, enhancing it if necessary."""
        # Get or create the NPC
        if isinstance(npc_or_name, str):
            npc, _ = self.get_or_create_npc(npc_or_name, interaction_type, npc_subtype=npc_subtype)
            if not npc:
                return None
        else:
            npc = npc_or_name
            
        # Enhance the NPC for this interaction if needed
        self.creator.enhance_npc_for_interaction(npc, interaction_type)
        
        return npc
    
    def record_interaction(self,
                          npc_or_name: Union[NPC, str],
                          interaction_type: NPCInteractionType,
                          description: str,
                          location: Optional[str] = None,
                          importance: int = 3,
                          npc_subtype: Optional[str] = None) -> Optional[NPCMemory]:
        """Record an interaction with an NPC."""
        # Get or create the NPC
        if isinstance(npc_or_name, str):
            npc, _ = self.get_or_create_npc(npc_or_name, interaction_type, location, npc_subtype=npc_subtype)
            if not npc:
                return None
        else:
            npc = npc_or_name
        
        # Record the interaction
        return self.memory.record_interaction(
            npc_id=npc.id,
            interaction_type=interaction_type,
            description=description,
            location=location,
            importance=importance
        )
    
    def get_context_for_interaction(self,
                                   npc_or_name: Union[NPC, str],
                                   interaction_type: NPCInteractionType,
                                   npc_subtype: Optional[str] = None) -> Dict[str, Any]:
        """Get context for an interaction with an NPC."""
        # Prepare the NPC
        npc = self.prepare_npc_for_interaction(npc_or_name, interaction_type, npc_subtype)
        if not npc:
            return {"error": "NPC not found or could not be created"}
        
        # Get relevant memories
        memories = self.memory.get_relevant_context_for_interaction(npc.id, interaction_type)
        
        # Build the context
        context = {
            "npc": {
                "id": npc.id,
                "name": npc.name,
                "type": npc.npc_type.name,
                "relationship": npc.relationship.name,
                "description": npc.description,
                "occupation": npc.occupation,
                "location": npc.location,
                "personality": npc.personality
            },
            "stats": {},
            "memories": memories,
            "interaction_count": npc.interaction_count
        }
        
        # Add stats if available
        if npc.has_stats():
            if interaction_type == NPCInteractionType.COMBAT:
                combat_stats = ["STR", "DEX", "CON", "MELEE_ATTACK", "RANGED_ATTACK", "DEFENSE"]
                for stat in combat_stats:
                    value = npc.get_stat(stat)
                    if value is not None:
                        context["stats"][stat] = value
            elif interaction_type == NPCInteractionType.SOCIAL:
                social_stats = ["CHA", "WIS"]
                for stat in social_stats:
                    value = npc.get_stat(stat)
                    if value is not None:
                        context["stats"][stat] = value
            elif interaction_type == NPCInteractionType.COMMERCE:
                commerce_stats = ["CHA", "INT"]
                for stat in commerce_stats:
                    value = npc.get_stat(stat)
                    if value is not None:
                        context["stats"][stat] = value
        
        return context
    
    def create_enemy_for_combat(self, name: Optional[str] = None, enemy_type: str = "bandit",
                               level: int = 1, location: Optional[str] = None) -> NPC:
        """Create an enemy NPC ready for combat."""
        # (Same logic as provided previously, kept here for completeness of the file)
        try:
            from core.base.config import get_config
            cfg = get_config()
            mode = (cfg.get("system.npc_generation_mode", "legacy") or "legacy").lower()
        except Exception:
            mode = "legacy"

        if mode == "families":
            try:
                from core.character.npc_family_generator import NPCFamilyGenerator
                fam_gen = NPCFamilyGenerator()
                raw = enemy_type
                overlay_id = None
                target_id = raw
                if isinstance(raw, str) and "::" in raw:
                    parts = raw.split("::", 1)
                    target_id, overlay_id = parts[0], parts[1] or None
                elif isinstance(raw, str) and raw.endswith("+boss"):
                    target_id = raw[:-5]
                    overlay_id = overlay_id or "default_boss"

                # Heuristic resolution
                def _heuristic_map_unknown(label: str, lvl: int) -> Optional[str]:
                    if not label: return None
                    key = label.lower().strip()
                    if any(w in key for w in ["wolf", "hound", "dog", "boar", "bear", "lion", "beast"]):
                        return "beast_normal_base" if lvl >= 2 else "beast_easy_base"
                    if any(w in key for w in ["bandit", "guard", "soldier", "thug", "brigand", "human"]):
                        return "humanoid_easy_base" if lvl <= 2 else "humanoid_normal_base"
                    return None

                var = getattr(fam_gen, "get_variant", None)
                fam = getattr(fam_gen, "get_family", None)
                used_variant = False
                
                try:
                    difficulty = (cfg.get("game.difficulty", "normal") or "normal")
                    encounter_size = (cfg.get("game.encounter_size", "solo") or "solo")
                except Exception:
                    difficulty = "normal"
                    encounter_size = "solo"

                try:
                    fam_exists = callable(fam) and bool(fam(target_id))
                except Exception: fam_exists = False
                try:
                    var_exists = callable(var) and bool(var(target_id))
                except Exception: var_exists = False
                
                if not fam_exists and not var_exists:
                    mapped = _heuristic_map_unknown(target_id, level)
                    if mapped: target_id = mapped

                if callable(var) and var(target_id):
                    npc = fam_gen.generate_npc_from_variant(
                        variant_id=target_id, name=name, location=location, level=level,
                        overlay_id=overlay_id, difficulty=difficulty, encounter_size=encounter_size
                    )
                    used_variant = True
                else:
                    npc = fam_gen.generate_npc_from_family(
                        family_id=target_id, name=name, location=location, level=level,
                        overlay_id=overlay_id, difficulty=difficulty, encounter_size=encounter_size
                    )
                
                if npc:
                    npc.is_persistent = True
                    self.manager.add_npc(npc)
                    
            except Exception as e:
                logger.error(f"Families-based NPC generation failed: {e}", exc_info=True)
                npc = self.creator.create_enemy(name=name, enemy_type=enemy_type, level=level, location=location)
        else:
            npc = self.creator.create_enemy(name=name, enemy_type=enemy_type, level=level, location=location)

        if npc:
            self.register_npc(npc)
        return npc
    
    def create_merchant(self, name: str, shop_type: str = "general", location: Optional[str] = None) -> NPC:
        """Create a merchant NPC."""
        return self.creator.create_merchant(name=name, shop_type=shop_type, location=location)
    
    def update_npc_location(self, npc_id: str, new_location: str) -> bool:
        """Update an NPC's location."""
        return self.manager.update_npc_location(npc_id, new_location)
    
    def update_npc_relationship(self, npc_id: str, new_relationship: NPCRelationship) -> bool:
        """Update an NPC's relationship with the player."""
        return self.manager.update_npc_relationship(npc_id, new_relationship)
    
    def save_state(self) -> bool:
        """Save the entire NPC system state."""
        try:
            self.save_all_npcs()
            return True
        except Exception as e:
            logger.error(f"Error saving NPC system state: {e}")
            return False
    
    def load_state(self) -> bool:
        """Load the entire NPC system state."""
        try:
            self.clear_all_npcs()
            self.load_all_npcs()
            return True
        except Exception as e:
            logger.error(f"Error loading NPC system state: {e}")
            return False

    def register_npc(self, npc: NPC) -> None:
        """Register an NPC in the direct storage for fallback access."""
        if npc and hasattr(npc, 'id') and npc.id:
            self.npcs[npc.id] = npc
            if npc not in self.npc_list:
                self.npc_list.append(npc)
            if self.manager.get_npc_by_id(npc.id) is None:
                self.manager.add_npc(npc)
            logger.debug(f"Registered NPC {npc.name} (ID: {npc.id}) in direct storage.")


# Singleton instance for global access
_npc_system_singleton = None

def get_npc_system() -> 'NPCSystem':
    """
    Get the global NPC system instance.
    
    Returns:
        The global NPCSystem instance
    """
    global _npc_system_singleton
    if _npc_system_singleton is None:
        _npc_system_singleton = NPCSystem()
    return _npc_system_singleton