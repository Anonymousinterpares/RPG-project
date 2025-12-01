"""
System for managing skill point allocation during character creation and leveling.
"""

from typing import List

from core.stats.stats_manager import StatsManager
from core.utils.logging_config import get_logger

logger = get_logger(__name__)

class SkillAllocator:
    """
    Manages allocation of skill points.
    """
    
    def __init__(
        self,
        stats_manager: StatsManager,
        class_skills: List[str],
        origin_skills: List[str],
        skill_points: int = 4,
        max_rank: int = 4 
    ):
        """
        Initialize the skill allocator.
        
        Args:
            stats_manager: The StatsManager to modify.
            class_skills: List of skill names that are class skills (cheaper).
            origin_skills: List of skill names granted by origin (start at 1).
            skill_points: Total points available for allocation.
            max_rank: Maximum rank allowed during this allocation phase.
        """
        self.stats_manager = stats_manager
        self.class_skills = [s.lower().replace(" ", "_") for s in class_skills]
        self.origin_skills = [s.lower().replace(" ", "_") for s in origin_skills]
        self.total_points = skill_points
        self.max_rank = max_rank
        
        # Reset skills to default state before allocation
        self.reset_skills()

    def reset_skills(self) -> None:
        """Reset all skills to 0, then apply origin bonuses."""
        for skill_key, stat in self.stats_manager.skills.items():
            # Reset to 0
            self.stats_manager.set_skill_value(skill_key, 0)
            
        # Apply Origin Skills (Rank 1 free)
        for skill_name in self.origin_skills:
            if self.stats_manager.get_skill(skill_name):
                self.stats_manager.set_skill_value(skill_name, 1)
                logger.debug(f"Set origin skill {skill_name} to rank 1")

    def get_skill_cost(self, skill_name: str) -> int:
        """
        Get the point cost to increase a skill by 1 rank.
        
        Args:
            skill_name: The skill to check.
            
        Returns:
            1 for class skills, 2 for cross-class skills.
        """
        normalized_name = skill_name.lower().replace(" ", "_")
        if normalized_name in self.class_skills:
            return 1
        return 2

    def calculate_points_spent(self) -> int:
        """
        Calculate total points spent by the player (excluding free origin ranks).
        
        Returns:
            Total points spent.
        """
        spent = 0
        for skill_key, stat in self.stats_manager.skills.items():
            rank = int(stat.base_value)
            normalized_key = skill_key.lower().replace(" ", "_")
            
            # Determine starting rank (free)
            start_rank = 1 if normalized_key in self.origin_skills else 0
            
            if rank > start_rank:
                cost_per_rank = self.get_skill_cost(skill_key)
                spent += (rank - start_rank) * cost_per_rank
                
        return spent

    def get_remaining_points(self) -> int:
        """
        Calculate remaining skill points.
        
        Returns:
            Remaining points.
        """
        return self.total_points - self.calculate_points_spent()

    def can_increase_skill(self, skill_name: str) -> bool:
        """
        Check if a skill can be increased.
        
        Args:
            skill_name: The skill to check.
            
        Returns:
            True if possible.
        """
        current_rank = int(self.stats_manager.get_skill_value(skill_name))
        
        if current_rank >= self.max_rank:
            return False
            
        cost = self.get_skill_cost(skill_name)
        return cost <= self.get_remaining_points()

    def can_decrease_skill(self, skill_name: str) -> bool:
        """
        Check if a skill can be decreased.
        
        Args:
            skill_name: The skill to check.
            
        Returns:
            True if possible.
        """
        current_rank = int(self.stats_manager.get_skill_value(skill_name))
        normalized_name = skill_name.lower().replace(" ", "_")
        
        # Minimum rank is 1 for origin skills, 0 for others
        min_rank = 1 if normalized_name in self.origin_skills else 0
        
        return current_rank > min_rank

    def increase_skill(self, skill_name: str) -> bool:
        """
        Increase a skill by one rank.
        
        Args:
            skill_name: The skill to increase.
            
        Returns:
            True if successful.
        """
        if not self.can_increase_skill(skill_name):
            return False
            
        current = self.stats_manager.get_skill_value(skill_name)
        self.stats_manager.set_skill_value(skill_name, current + 1)
        return True

    def decrease_skill(self, skill_name: str) -> bool:
        """
        Decrease a skill by one rank.
        
        Args:
            skill_name: The skill to decrease.
            
        Returns:
            True if successful.
        """
        if not self.can_decrease_skill(skill_name):
            return False
            
        current = self.stats_manager.get_skill_value(skill_name)
        self.stats_manager.set_skill_value(skill_name, current - 1)
        return True
