"""
Functions for calculating derived stats based on primary stats.
"""

from typing import Dict, Any, Optional, Union, Callable
import math

from core.stats.stats_base import StatType, DerivedStatType, Stat
from core.utils.logging_config import get_logger

logger = get_logger("STATS")

def get_modifier_from_stat(stat_value: float) -> int:
    """
    Calculate the standard D&D-style modifier from a stat value.
    Formula: (stat - 10) / 2, rounded down.
    """
    return math.floor((stat_value - 10) / 2)


def calculate_max_health(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate maximum health points based on Constitution, level, and class."""
    base_hp = config.get("base_health", 10.0) # Ensure float
    con_mod = get_modifier_from_stat(stats[StatType.CONSTITUTION].value)
    per_level_hp = config.get("hp_per_level", 5.0) # Ensure float
    
    calculated_hp = 0.0
    if level == 1:
        calculated_hp = base_hp + con_mod
    else:
        calculated_hp = base_hp + con_mod + (per_level_hp + con_mod) * (level - 1)
    
    return max(1.0, float(calculated_hp))

def calculate_mana(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate maximum mana points based on Intelligence, Wisdom, and level."""
    base_mana = config.get("base_mana", 5.0) # Ensure float
    int_mod = get_modifier_from_stat(stats[StatType.INTELLIGENCE].value)
    wis_mod = get_modifier_from_stat(stats[StatType.WISDOM].value)
    per_level_mana = config.get("mana_per_level", 3.0) # Ensure float
    
    calculated_mana = base_mana + int_mod + wis_mod + (per_level_mana + int_mod) * (level - 1)
    return max(0.0, float(calculated_mana)) 

def calculate_stamina(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate maximum stamina based on Constitution, Strength, and level."""
    base_stamina = config.get("base_stamina", 10.0) # Ensure float
    con_mod = get_modifier_from_stat(stats[StatType.CONSTITUTION].value)
    str_mod = get_modifier_from_stat(stats[StatType.STRENGTH].value)
    per_level_stamina = config.get("stamina_per_level", 2.0) # Ensure float
    
    # Ensure result is at least 1, even with negative modifiers at level 1
    calculated_stamina = base_stamina + con_mod + (per_level_stamina + math.floor(str_mod / 2)) * level
    return max(1.0, float(calculated_stamina)) # Return float, min 1.0

def calculate_initiative(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate initiative based on Dexterity and Wisdom."""
    dex_mod = get_modifier_from_stat(stats[StatType.DEXTERITY].value)
    wis_mod = get_modifier_from_stat(stats[StatType.WISDOM].value)
    
    return dex_mod + math.floor(wis_mod / 2)


def calculate_carry_capacity(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate carrying capacity based on Strength."""
    base_capacity = config.get("base_carry_capacity", 50)
    str_value = stats[StatType.STRENGTH].value
    multiplier = config.get("carry_capacity_multiplier", 5)
    
    return base_capacity + (str_value * multiplier)


def calculate_melee_attack(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate melee attack bonus based on Strength and level."""
    str_mod = get_modifier_from_stat(stats[StatType.STRENGTH].value)
    proficiency = math.ceil(level / 4) + 1  # Simple proficiency bonus based on level
    
    return str_mod + proficiency


def calculate_ranged_attack(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate ranged attack bonus based on Dexterity and level."""
    dex_mod = get_modifier_from_stat(stats[StatType.DEXTERITY].value)
    proficiency = math.ceil(level / 4) + 1  # Simple proficiency bonus based on level
    
    return dex_mod + proficiency


def calculate_magic_attack(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate magic attack bonus based on Intelligence and level."""
    int_mod = get_modifier_from_stat(stats[StatType.INTELLIGENCE].value)
    proficiency = math.ceil(level / 4) + 1  # Simple proficiency bonus based on level
    
    return int_mod + proficiency


def calculate_defense(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate physical defense based on Constitution and Dexterity."""
    base_defense = config.get("base_defense", 10)
    con_mod = get_modifier_from_stat(stats[StatType.CONSTITUTION].value)
    dex_mod = get_modifier_from_stat(stats[StatType.DEXTERITY].value)
    
    # Cap the Dex modifier contribution to defense (if wearing heavy armor, etc.)
    max_dex_mod = config.get("max_dex_mod_to_defense", 5)
    dex_contribution = min(dex_mod, max_dex_mod)
    
    return base_defense + con_mod + dex_contribution


def calculate_magic_defense(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate magic defense based on Wisdom and Intelligence."""
    base_magic_defense = config.get("base_magic_defense", 10)
    wis_mod = get_modifier_from_stat(stats[StatType.WISDOM].value)
    int_mod = get_modifier_from_stat(stats[StatType.INTELLIGENCE].value)
    
    return base_magic_defense + wis_mod + math.floor(int_mod / 2)


def calculate_movement(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate movement speed based on Dexterity."""
    base_movement = config.get("base_movement", 30)
    dex_mod = get_modifier_from_stat(stats[StatType.DEXTERITY].value)
    
    # Movement speed increases with Dex, but with diminishing returns
    if dex_mod <= 0:
        return max(base_movement + dex_mod, 15)  # Minimum movement speed
    else:
        return base_movement + math.floor(math.sqrt(dex_mod) * 5)


def calculate_max_resolve(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate maximum social/mental resolve based on Willpower, Insight, and level."""
    base_resolve = config.get("base_resolve", 10)
    wil_mod = get_modifier_from_stat(stats[StatType.WILLPOWER].value)
    ins_mod = get_modifier_from_stat(stats[StatType.INSIGHT].value) # Changed from CHARISMA to INSIGHT
    per_level_resolve = config.get("resolve_per_level", 3)

    # Similar structure to HP/Mana calculation
    if level == 1:
        return base_resolve + wil_mod + ins_mod

    return base_resolve + wil_mod + ins_mod + (per_level_resolve + wil_mod) * (level - 1)


def calculate_damage_reduction(stats: Dict[Union[StatType, str], Stat], level: int, config: Dict[str, Any]) -> float:
    """Calculate base flat damage reduction based on Constitution."""
    # --- Future DR Integration Points ---
    # 1. Equipment Modifiers: Add logic here or preferably within StatsManager
    #    to sum DR bonuses from equipped items (armor, shields, amulets).
    #    Example: total_dr += stats_manager.get_equipment_modifier(DerivedStatType.DAMAGE_REDUCTION)
    # 2. Status Effect Modifiers: Apply DR from buffs/debuffs via ModifierManager.
    #    The get_stat_value in StatsManager should automatically include these if
    #    DAMAGE_REDUCTION is treated like other stats.
    # 3. Class/Race Features: Apply permanent DR bonuses via modifiers loaded
    #    from class/race configs.
    # ----------------------------------

    base_dr = float(config.get("base_damage_reduction", 0.0))
    # Add a small bonus from CON modifier (example)
    con_stat = stats.get(StatType.CONSTITUTION)
    if con_stat:
        con_mod = get_modifier_from_stat(con_stat.value)
        # Example: +1 DR for every 4 points of CON modifier, minimum 0
        base_dr += max(0, math.floor(con_mod / 4))
    else:
        logger.warning("Constitution stat not found for DR calculation.")

    return base_dr


# Mapping of derived stat types to their calculation functions
DERIVED_STAT_CALCULATORS: Dict[DerivedStatType, Callable] = {
    DerivedStatType.MAX_HEALTH: calculate_max_health,
    DerivedStatType.MAX_RESOLVE: calculate_max_resolve,
    DerivedStatType.MAX_MANA: calculate_mana,
    DerivedStatType.MAX_STAMINA: calculate_stamina,
    DerivedStatType.INITIATIVE: calculate_initiative,
    DerivedStatType.CARRY_CAPACITY: calculate_carry_capacity,
    DerivedStatType.MELEE_ATTACK: calculate_melee_attack,
    DerivedStatType.RANGED_ATTACK: calculate_ranged_attack,
    DerivedStatType.MAGIC_ATTACK: calculate_magic_attack,
    DerivedStatType.DEFENSE: calculate_defense,
    DerivedStatType.MAGIC_DEFENSE: calculate_magic_defense,
    DerivedStatType.MOVEMENT: calculate_movement,
    DerivedStatType.DAMAGE_REDUCTION: calculate_damage_reduction,
}


def calculate_derived_stat(
    stat_type: DerivedStatType,
    stats: Dict[Union[StatType, str], Stat],
    level: int,
    config: Optional[Dict[str, Any]] = None
) -> float:
    """Calculate a derived stat based on primary stats and level."""
    if config is None:
        config = {}
    
    calculator = DERIVED_STAT_CALCULATORS.get(stat_type)
    if not calculator:
        raise ValueError(f"No calculator defined for derived stat {stat_type}")
    
    return calculator(stats, level, config)
