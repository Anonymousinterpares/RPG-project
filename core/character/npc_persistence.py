#!/usr/bin/env python3
"""
NPC Persistence module handling saving, loading, and serialization of NPCs.
"""

import os
import json
from typing import Optional, Tuple
from datetime import datetime

from core.character.npc_base import NPC
from core.character.npc_manager import NPCManager
from core.utils.logging_config import get_logger

logger = get_logger(__name__)


class NPCPersistence:
    """
    Class for handling NPC persistence operations.
    Manages saving, loading, and serialization of NPCs.
    """
    
    def __init__(self, npc_manager: NPCManager):
        """
        Initialize the NPC persistence handler.
        
        Args:
            npc_manager: The NPCManager instance to use
        """
        self.npc_manager = npc_manager
        self.save_directory = npc_manager.save_directory
    
    def save_npc(self, npc: NPC) -> bool:
        """
        Save an individual NPC to file.
        
        Args:
            npc: The NPC to save
            
        Returns:
            True if successful, False otherwise
        """
        if not npc.is_persistent:
            logger.debug(f"Not saving non-persistent NPC: {npc.name}")
            return False
        
        try:
            os.makedirs(self.save_directory, exist_ok=True)
            
            # Create a filename based on the NPC's ID
            filename = os.path.join(self.save_directory, f"{npc.id}.json")
            
            # Convert NPC to dictionary
            npc_data = npc.to_dict()
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(npc_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved NPC {npc.name} to {filename}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving NPC {npc.name}: {e}")
            return False
    
    def load_npc(self, npc_id: str) -> Optional[NPC]:
        """
        Load an individual NPC from file.
        
        Args:
            npc_id: ID of the NPC to load
            
        Returns:
            The loaded NPC if successful, None otherwise
        """
        try:
            # Create filename based on NPC ID
            filename = os.path.join(self.save_directory, f"{npc_id}.json")
            
            if not os.path.exists(filename):
                logger.warning(f"NPC file not found: {filename}")
                return None
            
            # Load from file
            with open(filename, 'r', encoding='utf-8') as f:
                npc_data = json.load(f)
            
            # Create NPC from data
            npc = NPC.from_dict(npc_data)
            
            logger.info(f"Loaded NPC {npc.name} from {filename}")
            return npc
        
        except Exception as e:
            logger.error(f"Error loading NPC {npc_id}: {e}")
            return None
    
    def save_all_persistent_npcs(self, target_directory: Optional[str] = None) -> Tuple[int, int]:
        """
        Save all persistent NPCs to file.
        
        Args:
            target_directory: Optional override directory. If provided, NPCs are saved 
                              to this path instead of self.save_directory.
        
        Returns:
            Tuple of (success_count, total_count)
        """
        # Use provided target or default to manager's directory
        save_dir = target_directory if target_directory else self.save_directory
        
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create NPC save directory {save_dir}: {e}")
            return 0, 0

        persistent_npcs = [npc for npc in self.npc_manager.npcs.values() if npc.is_persistent]
        success_count = 0
        
        for npc in persistent_npcs:
            if self._save_npc_to_dir(npc, save_dir):
                success_count += 1
        
        logger.info(f"Saved {success_count}/{len(persistent_npcs)} persistent NPCs to {save_dir}")
        return success_count, len(persistent_npcs)

    def _save_npc_to_dir(self, npc: NPC, directory: str) -> bool:
        """Internal helper to save a specific NPC to a specific directory."""
        try:
            filename = os.path.join(directory, f"{npc.id}.json")
            npc_data = npc.to_dict()
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(npc_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving NPC {npc.name} to {directory}: {e}")
            return False
    
    def load_all_npcs(self) -> int:
        """
        Load all NPCs from files in the save directory.
        
        Returns:
            Number of NPCs loaded
        """
        try:
            if not os.path.exists(self.save_directory):
                logger.warning(f"NPC save directory not found: {self.save_directory}")
                return 0
            
            # Find all JSON files in the directory
            npc_files = [f for f in os.listdir(self.save_directory) if f.endswith('.json')]
            loaded_count = 0
            
            for file in npc_files:
                try:
                    # Extract NPC ID from filename
                    npc_id = os.path.splitext(file)[0]
                    
                    # Load the NPC
                    npc = self.load_npc(npc_id)
                    if npc:
                        # Add to manager
                        self.npc_manager.add_npc(npc)
                        loaded_count += 1
                
                except Exception as e:
                    logger.error(f"Error loading NPC from {file}: {e}")
            
            logger.info(f"Loaded {loaded_count}/{len(npc_files)} NPCs from {self.save_directory}")
            return loaded_count
        
        except Exception as e:
            logger.error(f"Error loading NPCs: {e}")
            return 0
    
    def delete_npc_file(self, npc_id: str) -> bool:
        """
        Delete an NPC's save file.
        
        Args:
            npc_id: ID of the NPC whose file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filename = os.path.join(self.save_directory, f"{npc_id}.json")
            
            if not os.path.exists(filename):
                logger.warning(f"NPC file not found: {filename}")
                return False
            
            os.remove(filename)
            logger.info(f"Deleted NPC file: {filename}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting NPC file for {npc_id}: {e}")
            return False
    
    def cleanup_unused_npcs(self, days_threshold: int = 30) -> int:
        """
        Remove NPCs that haven't been interacted with for a long time.
        
        Args:
            days_threshold: Number of days of inactivity before removal
            
        Returns:
            Number of NPCs removed
        """
        cutoff_date = datetime.now() - datetime.timedelta(days=days_threshold)
        npcs_to_remove = []
        
        for npc_id, npc in self.npc_manager.npcs.items():
            # Skip NPCs without a last interaction date
            if not npc.last_interaction:
                continue
            
            # Check if the NPC is older than the threshold
            if npc.last_interaction < cutoff_date:
                npcs_to_remove.append(npc_id)
        
        # Remove the NPCs
        for npc_id in npcs_to_remove:
            self.delete_npc_file(npc_id)
            self.npc_manager.remove_npc(npc_id)
        
        logger.info(f"Cleaned up {len(npcs_to_remove)} unused NPCs")
        return len(npcs_to_remove)
    
    def export_npcs_to_json(self, filepath: str, include_non_persistent: bool = False) -> bool:
        """
        Export all NPCs to a single JSON file for debugging or external processing.
        
        Args:
            filepath: Path to save the JSON file
            include_non_persistent: Whether to include non-persistent NPCs
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if include_non_persistent:
                npcs_to_export = list(self.npc_manager.npcs.values())
            else:
                npcs_to_export = [npc for npc in self.npc_manager.npcs.values() if npc.is_persistent]
            
            npc_data = {npc.id: npc.to_dict() for npc in npcs_to_export}
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(npc_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(npcs_to_export)} NPCs to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting NPCs to {filepath}: {e}")
            return False
    
    def import_npcs_from_json(self, filepath: str) -> int:
        """
        Import NPCs from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Number of NPCs imported
        """
        try:
            if not os.path.exists(filepath):
                logger.warning(f"NPC import file not found: {filepath}")
                return 0
            
            with open(filepath, 'r', encoding='utf-8') as f:
                npc_data = json.load(f)
            
            imported_count = 0
            
            for npc_id, data in npc_data.items():
                try:
                    npc = NPC.from_dict(data)
                    self.npc_manager.add_npc(npc)
                    imported_count += 1
                
                except Exception as e:
                    logger.error(f"Error importing NPC {npc_id}: {e}")
            
            logger.info(f"Imported {imported_count}/{len(npc_data)} NPCs from {filepath}")
            return imported_count
        
        except Exception as e:
            logger.error(f"Error importing NPCs from {filepath}: {e}")
            return 0
