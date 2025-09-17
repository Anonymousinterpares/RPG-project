"""
System for managing stat point allocation during character creation and leveling.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import logging

from core.stats.stats_base import StatType
from core.stats.stats_manager import StatsManager


logger = logging.getLogger(__name__)


class StatPointAllocator:
    """
    Manages allocation of stat points during character creation and leveling.
    """
    
    def __init__(
        self,
        stats_manager: StatsManager,
        total_points: int = 22,
        min_value: int = 8,
        max_value: int = 15
    ):
        """
        Initialize the stat point allocator.
        
        Args:
            stats_manager: The StatsManager to modify
            total_points: Total points available for allocation
            min_value: Minimum allowed stat value
            max_value: Maximum allowed stat value
        """
        self.stats_manager = stats_manager
        self.total_points = total_points
        self.min_value = min_value
        self.max_value = max_value
        
        # Cost of each point above the minimum value (D&D style)
        self.point_costs = {
            8: 0,    # Base value costs nothing
            9: 1,    # 9 costs 1 point
            10: 2,   # 10 costs 2 points
            11: 3,   # 11 costs 3 points
            12: 4,   # 12 costs 4 points
            13: 5,   # 13 costs 5 points
            14: 7,   # 14 costs 7 points
            15: 9,   # 15 costs 9 points
            16: 11,  # 16 costs 11 points (usually from racial bonuses)
            17: 14,  # 17 costs 14 points
            18: 17   # 18 costs 17 points
        }
        
        # Initialize to minimum values
        self.reset_to_minimum()
    
    def reset_to_minimum(self) -> None:
        """Reset all stats to their minimum values."""
        logger.info("Resetting all stats to minimum values")
        for stat_type in StatType:
            current_value = int(self.stats_manager.get_stat_value(stat_type))
            if current_value != self.min_value:
                logger.debug(f"Resetting {stat_type} from {current_value} to {self.min_value}")
                self.stats_manager.set_base_stat(stat_type, self.min_value)
    
    def get_point_cost(self, value: int) -> int:
        """
        Get the point cost for a specific stat value.
        
        Args:
            value: The stat value to check
            
        Returns:
            The point cost for that value
        """
        if value < self.min_value:
            return 0
        elif value in self.point_costs:
            return self.point_costs[value]
        else:
            # For values beyond our chart, use a quadratic cost
            # This is an approximation of the D&D point buy system
            return value * 2 - 14
    
    def calculate_total_cost(self) -> int:
        """
        Calculate the total point cost of the current stat allocation.
        
        Returns:
            The total points spent
        """
        total_cost = 0
        for stat_type in StatType:
            stat_value = int(self.stats_manager.get_stat_value(stat_type))
            total_cost += self.get_point_cost(stat_value)
        return total_cost
    
    def get_remaining_points(self) -> int:
        """
        Calculate how many points remain to be allocated.
        
        Returns:
            The number of remaining points
        """
        return self.total_points - self.calculate_total_cost()
    
    def can_increase_stat(self, stat_type: StatType) -> bool:
        """
        Check if a stat can be increased.
        
        Args:
            stat_type: The stat to check
            
        Returns:
            True if the stat can be increased, False otherwise
        """
        current_value = int(self.stats_manager.get_stat_value(stat_type))
        
        # Check if we're already at max
        if current_value >= self.max_value:
            return False
        
        # Calculate cost to increase
        current_cost = self.get_point_cost(current_value)
        next_cost = self.get_point_cost(current_value + 1)
        additional_cost = next_cost - current_cost
        
        # Check if we have enough points
        return additional_cost <= self.get_remaining_points()
    
    def can_decrease_stat(self, stat_type: StatType) -> bool:
        """
        Check if a stat can be decreased.
        
        Args:
            stat_type: The stat to check
            
        Returns:
            True if the stat can be decreased, False otherwise
        """
        current_value = int(self.stats_manager.get_stat_value(stat_type))
        return current_value > self.min_value
    
    def increase_stat(self, stat_type: StatType) -> bool:
        """
        Increase a stat by one point.
        
        Args:
            stat_type: The stat to increase
            
        Returns:
            True if the stat was increased, False otherwise
        """
        if not self.can_increase_stat(stat_type):
            logger.debug(f"Cannot increase {stat_type} - max value or not enough points")
            return False
        
        try:
            current_value = int(self.stats_manager.get_stat_value(stat_type))
            new_value = current_value + 1
            logger.info(f"Increasing {stat_type} from {current_value} to {new_value}")
            
            # Get current base value directly from the stat object for accuracy
            actual_base = self.stats_manager.get_stat(stat_type).base_value
            new_base = actual_base + 1
            logger.debug(f"Base value before: {actual_base}, after: {new_base}")
            
            # Update the base stat value
            self.stats_manager.set_base_stat(stat_type, new_base)
            
            # Verify the change was applied
            actual_after = self.stats_manager.get_stat(stat_type).base_value
            if actual_after != new_base:
                logger.error(f"Failed to update {stat_type} base value. Expected {new_base}, got {actual_after}")
                return False
                
            logger.debug(f"Successfully increased {stat_type} to base={actual_after}, total={self.stats_manager.get_stat_value(stat_type)}")
            return True
        except Exception as e:
            logger.error(f"Error increasing {stat_type}: {e}")
            return False
    
    def decrease_stat(self, stat_type: StatType) -> bool:
        """
        Decrease a stat by one point.
        
        Args:
            stat_type: The stat to decrease
            
        Returns:
            True if the stat was decreased, False otherwise
        """
        if not self.can_decrease_stat(stat_type):
            logger.debug(f"Cannot decrease {stat_type} - already at minimum value")
            return False
        
        try:
            current_value = int(self.stats_manager.get_stat_value(stat_type))
            new_value = current_value - 1
            logger.info(f"Decreasing {stat_type} from {current_value} to {new_value}")
            
            # Get current base value directly from the stat object for accuracy
            actual_base = self.stats_manager.get_stat(stat_type).base_value
            new_base = actual_base - 1
            logger.debug(f"Base value before: {actual_base}, after: {new_base}")
            
            # Update the base stat value
            self.stats_manager.set_base_stat(stat_type, new_base)
            
            # Verify the change was applied
            actual_after = self.stats_manager.get_stat(stat_type).base_value
            if actual_after != new_base:
                logger.error(f"Failed to update {stat_type} base value. Expected {new_base}, got {actual_after}")
                return False
                
            logger.debug(f"Successfully decreased {stat_type} to base={actual_after}, total={self.stats_manager.get_stat_value(stat_type)}")
            return True
        except Exception as e:
            logger.error(f"Error decreasing {stat_type}: {e}")
            return False
    
    def allocate_points_automatically(
        self,
        priority_stats: List[StatType] = None,
        balanced: bool = False
    ) -> None:
        """
        Automatically allocate available points.
        
        Args:
            priority_stats: List of stats to prioritize in order
            balanced: If True, maintain a balanced distribution
        """
        # Reset to minimum first
        self.reset_to_minimum()
        
        # If no priority stats provided, use all stats
        if not priority_stats:
            priority_stats = list(StatType)
        
        if balanced:
            # Balanced allocation: round-robin approach
            while self.get_remaining_points() > 0:
                allocated = False
                for stat_type in priority_stats:
                    if self.can_increase_stat(stat_type):
                        self.increase_stat(stat_type)
                        allocated = True
                        break
                
                if not allocated:
                    break  # No more stats can be increased
        else:
            # Priority allocation: max out high priority stats first
            for stat_type in priority_stats:
                # Keep increasing this stat until we can't anymore
                while self.can_increase_stat(stat_type):
                    self.increase_stat(stat_type)
        
        logger.debug(
            f"Automatic allocation complete. "
            f"Spent {self.calculate_total_cost()} points, "
            f"{self.get_remaining_points()} points remaining."
        )
    
    def get_stat_allocation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current stat allocation.
        
        Returns:
            Dictionary with allocation details
        """
        stats = {}
        for stat_type in StatType:
            value = int(self.stats_manager.get_stat_value(stat_type))
            cost = self.get_point_cost(value)
            stats[str(stat_type)] = {
                "value": value,
                "cost": cost,
                "can_increase": self.can_increase_stat(stat_type),
                "can_decrease": self.can_decrease_stat(stat_type)
            }
        
        return {
            "stats": stats,
            "total_points": self.total_points,
            "spent_points": self.calculate_total_cost(),
            "remaining_points": self.get_remaining_points(),
            "min_value": self.min_value,
            "max_value": self.max_value
        }
