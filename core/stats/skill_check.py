"""
System for handling skill checks based on character stats with SkillManager integration.

This module provides functions and classes for performing skill checks,
calculating success chances, and processing check results.
"""

import random
import math
import logging
from typing import Dict, Any, Optional, Union, Tuple

from core.stats.stats_base import StatType, DerivedStatType

# Import skill manager only when needed to avoid circular imports
# The skill_manager module imports StatType from stats_base

logger = logging.getLogger(__name__)


def calculate_success_chance(
    stat_value: float,
    difficulty: int,
    advantage: bool = False,
    disadvantage: bool = False
) -> float:
    """
    Calculate the probability of success for a skill check.
    
    Args:
        stat_value: The value of the stat being checked
        difficulty: The difficulty class (DC) of the check
        advantage: Whether the check has advantage
        disadvantage: Whether the check has disadvantage
        
    Returns:
        Float between 0 and 1 representing the success probability
    """
    # Handle None stat value
    if stat_value is None:
        logger.warning("Stat value is None in calculate_success_chance. Using default value of 10.")
        stat_value = 10

    # Handle None difficulty
    if difficulty is None:
        logger.warning("Difficulty is None in calculate_success_chance. Using default value of 15.")
        difficulty = 15
        
    # Base formula: success if d20 + stat_modifier >= difficulty
    # stat_modifier = (stat_value - 10) / 2
    mod = math.floor((stat_value - 10) / 2)
    
    # Calculate success probability for a single roll
    success_threshold = difficulty - mod
    single_roll_chance = min(max((21 - success_threshold) / 20, 0), 1)
    
    # Apply advantage/disadvantage
    if advantage and disadvantage:
        # They cancel out
        return single_roll_chance
    elif advantage:
        # Advantage: chance of at least one success in two rolls
        return 1 - (1 - single_roll_chance) ** 2
    elif disadvantage:
        # Disadvantage: chance of success in both rolls
        return single_roll_chance ** 2
    else:
        return single_roll_chance


def perform_check(
    stat_value: float,
    difficulty: int,
    advantage: bool = False,
    disadvantage: bool = False,
    situational_modifier: int = 0
) -> Tuple[bool, int]:
    """
    Perform a skill check and determine success or failure.

    Args:
        stat_value: The value of the stat being checked
        difficulty: The difficulty class (DC) of the check
        advantage: Whether the check has advantage
        disadvantage: Whether the check has disadvantage
        situational_modifier: Any additional flat modifier applying to this specific check

    Returns:
        Tuple of (success, roll_result)
    """
    # Handle None stat value
    if stat_value is None:
        logger.warning("Stat value is None in perform_check. Using default value of 10.")
        stat_value = 10
        
    # Handle None difficulty - default to moderate difficulty (15)
    if difficulty is None:
        logger.warning("Difficulty is None in perform_check. Using default value of 15.")
        difficulty = 15
        
    # Calculate modifier
    mod = math.floor((stat_value - 10) / 2)
    
    # Handle advantage/disadvantage
    if advantage and disadvantage:
        # They cancel out
        roll = random.randint(1, 20)
    elif advantage:
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        roll = max(roll1, roll2)
    elif disadvantage:
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        roll = min(roll1, roll2)
    else:
        roll = random.randint(1, 20)
    
    # Critical success always succeeds
    if roll == 20:
        return True, roll
    
    # Critical failure always fails
    if roll == 1:
        return False, roll
    
    # Normal check
    total = roll + mod
    total += situational_modifier
    success = total >= difficulty

    return success, roll


def get_difficulty_description(dc: int) -> str:
    """
    Get a descriptive label for a difficulty class.
    
    Args:
        dc: The difficulty class value
        
    Returns:
        A string describing the difficulty level
    """
    # Handle None dc
    if dc is None:
        logger.warning("DC is None in get_difficulty_description. Using default value of 15.")
        dc = 15
        
    if dc <= 5:
        return "Very Easy"
    elif dc <= 10:
        return "Easy"
    elif dc <= 15:
        return "Medium"
    elif dc <= 20:
        return "Hard"
    elif dc <= 25:
        return "Very Hard"
    elif dc <= 30:
        return "Nearly Impossible"
    else:
        return "Legendary"


def determine_outcome_description(
    success: bool,
    margin: int,
    critical: bool = False
) -> str:
    """
    Generate a description of the check outcome based on success and margin.
    
    Args:
        success: Whether the check succeeded
        margin: How much the check succeeded or failed by
        critical: Whether the roll was a critical success or failure
        
    Returns:
        A descriptive string of the outcome
    """
    if critical:
        if success:
            return "Spectacular Success"
        else:
            return "Spectacular Failure"
    
    if success:
        if margin >= 10:
            return "Exceptional Success"
        elif margin >= 5:
            return "Solid Success"
        else:
            return "Narrow Success"
    else:
        if margin >= 10:
            return "Catastrophic Failure"
        elif margin >= 5:
            return "Clear Failure"
        else:
            return "Near Miss"


class SkillCheckResult:
    """Class to hold the result of a skill check with detailed information."""
    
    def __init__(
        self,
        stat_type: Union[StatType, DerivedStatType, str],
        stat_value: float,
        difficulty: int,
        roll: int,
        modifier: int,
        success: bool,
        advantage: bool = False,
        disadvantage: bool = False,
        situational_modifier: int = 0,
        skill_name: Optional[str] = None,
        skill_exists: bool = True
    ):
        """Initialize the skill check result."""
        self.stat_type = stat_type
        self.skill_name = skill_name  # Optional name of the skill being used
        self.skill_exists = skill_exists  # Whether the skill exists in the system
        
        # Handle None stat_value
        if stat_value is None:
            logger.warning(f"Stat value is None for {skill_name or stat_type} check. Using default value of 10.")
            stat_value = 10
        self.stat_value = stat_value
        
        # Handle None difficulty
        if difficulty is None:
            logger.warning(f"Difficulty is None for {skill_name or stat_type} check. Using default value of 15.")
            difficulty = 15
        self.difficulty = difficulty
        
        self.roll = roll
        self.modifier = modifier
        self.situational_modifier = situational_modifier
        self.total = roll + modifier + situational_modifier # Apply situational modifier to final total
        self.success = success
        self.advantage = advantage
        self.disadvantage = disadvantage
        self.critical = (roll == 20 or roll == 1)

        # Recalculate margin based on final total and critical status
        # Handle criticals overriding success/failure for margin calculation
        effective_success = self.success if not self.critical else (self.roll == 20)
        self.margin = abs(self.total - self.difficulty) if effective_success == (self.total >= self.difficulty) else 0 # Margin is less meaningful on forced crit outcomes

        self.difficulty_desc = get_difficulty_description(difficulty)
        self.outcome_desc = determine_outcome_description(
            success, self.margin, self.critical
        )
    
    def __str__(self) -> str:
        """String representation of the result."""
        if not self.skill_exists and self.skill_name:
            return f"Invalid skill check: '{self.skill_name}' is not a valid skill."
            
        adv_str = ""
        if self.advantage and self.disadvantage:
            adv_str = " (with advantage and disadvantage, which cancel out)"
        elif self.advantage:
            adv_str = " (with advantage)"
        elif self.disadvantage:
            adv_str = " (with disadvantage)"

        # Use skill name if available, otherwise fall back to stat type
        check_name = self.skill_name if self.skill_name else str(self.stat_type)
            
        return (
            f"{check_name} Check ({self.difficulty_desc}, DC {self.difficulty}){adv_str}: " +
            f"Rolled {self.roll}" +
            f" + {self.modifier} (stat)" +
            (f" + {self.situational_modifier}" if self.situational_modifier > 0 else "") +
            (f" - {abs(self.situational_modifier)}" if self.situational_modifier < 0 else "") +
            (f" (situational)" if self.situational_modifier != 0 else "") +
            f" = {self.total} " +
            f"→ {self.outcome_desc}" +
            (f" (Crit!)" if self.critical else "")
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        result = {
            "stat_type": str(self.stat_type),
            "stat_value": self.stat_value,
            "difficulty": self.difficulty,
            "difficulty_desc": self.difficulty_desc,
            "roll": self.roll,
            "modifier": self.modifier,
            "total": self.total,
            "success": self.success,
            "situational_modifier": self.situational_modifier,
            "advantage": self.advantage,
            "disadvantage": self.disadvantage,
            "critical": self.critical,
            "margin": self.margin,
            "outcome_desc": self.outcome_desc
        }
        
        # Add skill-related fields if available
        if self.skill_name:
            result["skill_name"] = self.skill_name
            result["skill_exists"] = self.skill_exists
            
        return result


def get_skill_manager():
    """Import and return the skill manager instance (avoiding circular imports)."""
    from core.stats.skill_manager import get_skill_manager as get_manager
    return get_manager()


def map_intent_to_skill(intent: str) -> Optional[str]:
    """Map a player's intent description to the most appropriate skill."""
    skill_manager = get_skill_manager()
    return skill_manager.find_closest_skill(intent)


def perform_skill_check_by_name(
    skill_name: str,
    difficulty: int,
    stats_manager,  # Will be properly typed when integrated
    advantage: bool = False,
    disadvantage: bool = False,
    situational_modifier: int = 0,
    character_id: Optional[str] = None
) -> SkillCheckResult:
    """Perform a skill check using a skill name instead of a stat type."""
    # Get skill manager instance
    skill_manager = get_skill_manager()
    
    # Check if the skill exists
    skill = None
    if character_id is not None:
        # Try character-specific skills first
        skill = skill_manager.get_character_skill(character_id, skill_name)
    
    if skill is None:
        # Try standard skills
        skill = skill_manager.get_skill(skill_name)
    
    if not skill:
        logger.error(f"Unknown skill: {skill_name}")
        # Return a failure result with skill_exists=False
        return SkillCheckResult(
            stat_type="Unknown",
            stat_value=10,  # Default value
            difficulty=difficulty or 15,
            roll=0,
            modifier=0,
            success=False,
            advantage=advantage,
            disadvantage=disadvantage,
            situational_modifier=situational_modifier,
            skill_name=skill_name,
            skill_exists=False
        )
    
    # Get the primary stat for this skill
    stat_type_str = skill.get("primary_stat", "STRENGTH")  # Default to STRENGTH if not specified
    
    try:
        # Try to convert to StatType enum
        from core.stats.stats_base import StatType
        stat_type = StatType.from_string(stat_type_str)
    except (ValueError, AttributeError):
        # If conversion fails, use the string as is
        stat_type = stat_type_str
        logger.warning(f"Could not convert '{stat_type_str}' to StatType, using as string")
    
    # Get the stat value from the stats manager
    try:
        stat_value = stats_manager.get_stat_value(stat_type)
    except (ValueError, AttributeError) as e:
        logger.error(f"Error getting stat value for {stat_type}: {e}")
        stat_value = None  # Will be handled in perform_check
    
    # Calculate the modifier for display
    try:
        if stat_value is None:
            mod = 0
        else:
            mod = math.floor((stat_value - 10) / 2)
    except Exception as e:
        logger.error(f"Error calculating modifier: {e}")
        mod = 0
    
    # Perform the check
    success, roll = perform_check(
        stat_value=stat_value,
        difficulty=difficulty,
        advantage=advantage,
        disadvantage=disadvantage,
        situational_modifier=situational_modifier
    )
    
    # Create and return the result object
    result = SkillCheckResult(
        stat_type=stat_type,
        stat_value=stat_value,
        difficulty=difficulty,
        roll=roll,
        modifier=mod,
        success=success,
        advantage=advantage,
        disadvantage=disadvantage,
        situational_modifier=situational_modifier,
        skill_name=skill["name"],  # Use the proper display name from the skill definition
        skill_exists=True
    )
    
    logger.debug(f"Skill check result: {result}")
    return result
