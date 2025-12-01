"""
Manager for handling stat modifiers.
"""

from typing import Dict, List, Set, Optional, Union, Any

from core.stats.stats_base import StatType, DerivedStatType
from core.stats.modifier import StatModifier, ModifierGroup, ModifierType, ModifierSource
from core.utils.logging_config import get_logger


logger = get_logger(__name__)


class ModifierManager:
    """
    Manages all stat modifiers for a character.
    """
    
    def __init__(self):
        """Initialize the modifier manager."""
        self.modifiers: List[StatModifier] = []
        self.modifier_groups: List[ModifierGroup] = []
    
    def add_modifier(self, modifier: StatModifier) -> None:
        """
        Add a single modifier.
        
        Args:
            modifier: The modifier to add.
        """
        # Check for non-stacking modifiers from the same source
        if not modifier.stacks:
            # Remove any existing non-stacking modifiers to the same stat from the same source
            self.modifiers = [
                m for m in self.modifiers 
                if not (m.stat == modifier.stat and 
                       m.source_name == modifier.source_name and 
                       not m.stacks)
            ]
        
        self.modifiers.append(modifier)
        logger.debug(f"Added modifier: {modifier}")
    
    def add_modifier_group(self, group: ModifierGroup) -> None:
        """
        Add a group of modifiers.
        
        Args:
            group: The modifier group to add.
        """
        # First add the group to our tracking
        self.modifier_groups.append(group)
        
        # Then add all modifiers from the group
        for modifier in group.modifiers:
            self.add_modifier(modifier)
        
        logger.debug(f"Added modifier group: {group.name} with {len(group.modifiers)} modifiers")
    
    def remove_modifier(self, modifier_id: str) -> bool:
        """
        Remove a specific modifier by its ID.
        
        Args:
            modifier_id: The unique ID of the modifier to remove.
            
        Returns:
            bool: True if the modifier was found and removed, False otherwise.
        """
        original_length = len(self.modifiers)
        self.modifiers = [m for m in self.modifiers if m.id != modifier_id]
        removed = len(self.modifiers) != original_length
        
        if removed:
            logger.debug(f"Removed modifier with ID: {modifier_id}")
        else:
            logger.debug(f"No modifier found with ID: {modifier_id}")
        
        return removed
    
    def remove_modifier_group(self, group_id: str) -> bool:
        """
        Remove a modifier group and all its modifiers.
        
        Args:
            group_id: The unique ID of the group to remove.
            
        Returns:
            bool: True if the group was found and removed, False otherwise.
        """
        # Find the group
        group = next((g for g in self.modifier_groups if g.id == group_id), None)
        if not group:
            logger.debug(f"No modifier group found with ID: {group_id}")
            return False
        
        # Remove all modifiers from the group
        for modifier in group.modifiers:
            self.remove_modifier(modifier.id)
        
        # Remove the group itself
        self.modifier_groups = [g for g in self.modifier_groups if g.id != group_id]
        logger.debug(f"Removed modifier group: {group.name}")
        
        return True
    
    def remove_modifiers_by_source(self, source_type: ModifierSource, source_name: Optional[str] = None) -> int:
        """
        Remove all modifiers from a specific source.
        
        Args:
            source_type: The type of source to remove modifiers from.
            source_name: Optional specific source name to match.
            
        Returns:
            int: The number of modifiers removed.
        """
        # Remove matching modifier groups
        groups_to_remove = []
        for group in self.modifier_groups:
            if group.source_type == source_type and (source_name is None or group.name == source_name):
                groups_to_remove.append(group.id)
        
        for group_id in groups_to_remove:
            self.remove_modifier_group(group_id)
        
        # Remove individual modifiers
        original_length = len(self.modifiers)
        self.modifiers = [
            m for m in self.modifiers 
            if not (m.source_type == source_type and 
                   (source_name is None or m.source_name == source_name))
        ]
        removed_count = original_length - len(self.modifiers)
        
        if removed_count > 0:
            source_desc = f"{source_type.name}"
            if source_name:
                source_desc += f" ({source_name})"
            logger.debug(f"Removed {removed_count} modifiers from source: {source_desc}")
        
        return removed_count
    
    def get_modifiers_for_stat(
        self, stat: Union[StatType, DerivedStatType, str]
    ) -> List[StatModifier]:
        """
        Get all modifiers affecting a specific stat.
        
        Args:
            stat: The stat to get modifiers for.
            
        Returns:
            List of modifiers affecting the stat.
        """
        return [m for m in self.modifiers if m.stat == stat]
    
    def get_stat_modifier_value(
        self, stat: Union[StatType, DerivedStatType, str]
    ) -> Dict[str, float]:
        """
        Calculate the total modifier value for a stat.
        
        Args:
            stat: The stat to calculate modifiers for.
            
        Returns:
            Dictionary with 'flat' and 'percentage' keys for the two types of modifiers.
        """
        flat_modifier = 0.0
        percentage_modifier = 0.0
        
        for modifier in self.get_modifiers_for_stat(stat):
            if modifier.is_percentage:
                percentage_modifier += modifier.value
            else:
                flat_modifier += modifier.value
        
        return {
            'flat': flat_modifier,
            'percentage': percentage_modifier
        }
    
    def update_durations(self) -> Set[str]:
        """
        Update durations for all temporary modifiers.
        Removes expired modifiers and groups.
        
        Returns:
            Set of IDs of expired modifiers that were removed.
        """
        expired_ids = set()
        
        # Update group durations first
        expired_groups = []
        for group in self.modifier_groups:
            if group.modifier_type != ModifierType.PERMANENT and not group.update_duration():
                expired_groups.append(group.id)
                # Add all modifiers from this group to expired list
                expired_ids.update(m.id for m in group.modifiers)
        
        # Remove expired groups
        for group_id in expired_groups:
            self.remove_modifier_group(group_id)
        
        # Update individual modifiers (not in groups)
        expired_individual = []
        for modifier in self.modifiers:
            if (modifier.modifier_type != ModifierType.PERMANENT and 
                modifier.duration is not None and 
                modifier.duration <= 0):
                expired_individual.append(modifier.id)
                expired_ids.add(modifier.id)
        
        # Remove expired individual modifiers
        for modifier_id in expired_individual:
            self.remove_modifier(modifier_id)
        
        if expired_ids:
            logger.debug(f"Removed {len(expired_ids)} expired modifiers")
        
        return expired_ids
    
    def clear_all_modifiers(self) -> None:
        """Remove all modifiers and groups."""
        self.modifiers.clear()
        self.modifier_groups.clear()
        logger.debug("Cleared all modifiers")
    
    def clear_temporary_modifiers(self) -> int:
        """
        Remove all temporary modifiers.
        
        Returns:
            int: Number of modifiers removed.
        """
        # Remove temporary groups
        temp_groups = [g.id for g in self.modifier_groups if g.modifier_type == ModifierType.TEMPORARY]
        for group_id in temp_groups:
            self.remove_modifier_group(group_id)
        
        # Remove individual temporary modifiers
        original_length = len(self.modifiers)
        self.modifiers = [m for m in self.modifiers if m.modifier_type != ModifierType.TEMPORARY]
        removed_count = original_length - len(self.modifiers)
        
        if removed_count > 0:
            logger.debug(f"Cleared {removed_count} temporary modifiers")
        
        return removed_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "modifiers": [m.to_dict() for m in self.modifiers],
            "modifier_groups": [g.to_dict() for g in self.modifier_groups]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModifierManager':
        """Create a ModifierManager from a dictionary."""
        manager = cls()
        
        # Load modifier groups first
        for group_data in data.get("modifier_groups", []):
            manager.modifier_groups.append(ModifierGroup.from_dict(group_data))
        
        # Load individual modifiers
        for modifier_data in data.get("modifiers", []):
            manager.modifiers.append(StatModifier.from_dict(modifier_data))
        
        return manager
