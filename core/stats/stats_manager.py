"""
Manager for character statistics.
"""

import math
from typing import Dict, List, Any, Optional, Tuple, Union, Set
import logging
import json
import os
import random
from PySide6.QtCore import QObject, Signal

from core.stats.stats_base import Stat, StatType, DerivedStatType, StatCategory, Skill # Import Skill enum
from core.stats.derived_stats import DERIVED_STAT_CALCULATORS, calculate_derived_stat, get_modifier_from_stat
from core.stats.modifier import StatModifier, ModifierSource, ModifierGroup, ModifierType
from core.stats.modifier_manager import ModifierManager
from core.stats.skill_check import perform_check, calculate_success_chance, SkillCheckResult
from core.stats.combat_effects import StatusEffect, StatusEffectManager, StatusEffectType


logger = logging.getLogger(__name__)


class StatsManager(QObject):
    """
    Manages character statistics, including primary stats, derived stats, and modifiers.
    """

    # Signal emitted when stats change
    stats_changed = Signal(dict)
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the stats manager.

        Args:
            config_file: Optional path to a stats configuration file.
        """
        super().__init__()  # Initialize QObject
        
        self.stats: Dict[Union[StatType, str], Stat] = {}
        self.derived_stats: Dict[Union[DerivedStatType, str], Stat] = {}
        self.modifier_manager = ModifierManager()
        self.status_effect_manager = StatusEffectManager(self)
        self.level = 1
        self.config: Dict[str, Any] = {}
        
        # Reference to inventory manager for equipment modifiers
        # This will be set by the state manager or game engine
        self._inventory_manager = None

        # Load default configuration
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)

        # Initialize primary stats with default values
        self._initialize_primary_stats()

        # Initialize derived stats
        self._initialize_derived_stats()

    def _initialize_primary_stats(self) -> None:
        """Initialize the primary stats with default values."""
        # Default base value for stats
        default_base = self.config.get("default_stat_value", 10)

        # Initialize each primary stat
        for stat_type in StatType:
            base_value = self.config.get(f"base_{stat_type.name.lower()}", default_base)

            self.stats[stat_type] = Stat(
                name=stat_type,
                base_value=base_value,
                category=StatCategory.PRIMARY,
                description=self._get_stat_description(stat_type)
            )

    def _initialize_derived_stats(self) -> None:
            """Initialize the derived stats. Calculates max values and sets current values."""
            for stat_type in DerivedStatType:
                if stat_type in [DerivedStatType.HEALTH, DerivedStatType.RESOLVE, DerivedStatType.MANA, DerivedStatType.STAMINA]:
                    continue

                try:
                    if stat_type in DERIVED_STAT_CALCULATORS:
                        base_value = calculate_derived_stat(
                            stat_type=stat_type,
                            stats=self.stats,
                            level=self.level,
                            config=self.config
                        )
                    else:
                        logger.debug(f"No calculator found for {stat_type}, initializing base value to 0.0.")
                        base_value = 0.0

                    self.derived_stats[stat_type] = Stat(
                        name=stat_type,
                        base_value=float(base_value), 
                        category=StatCategory.DERIVED,
                        description=self._get_stat_description(stat_type)
                    )
                except ValueError as e: 
                    logger.warning(f"{e}, skipping initialization for {stat_type}.")
                    # Ensure stat exists even if calculation fails, with a default.
                    if stat_type not in self.derived_stats:
                        self.derived_stats[stat_type] = Stat(
                            name=stat_type, base_value=0.0, category=StatCategory.DERIVED,
                            description=self._get_stat_description(stat_type)
                        )
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error initializing derived stat {stat_type}: {e}", exc_info=True)
                    if stat_type not in self.derived_stats: # Ensure it exists with default if error
                        self.derived_stats[stat_type] = Stat(name=stat_type, base_value=0.0, category=StatCategory.DERIVED, description=self._get_stat_description(stat_type))
                    continue


            resource_pairs = [
                (DerivedStatType.HEALTH, DerivedStatType.MAX_HEALTH),
                (DerivedStatType.RESOLVE, DerivedStatType.MAX_RESOLVE),
                (DerivedStatType.MANA, DerivedStatType.MAX_MANA),      
                (DerivedStatType.STAMINA, DerivedStatType.MAX_STAMINA) 
            ]

            for current_stat_type, max_stat_type in resource_pairs:
                if max_stat_type in self.derived_stats:
                    # Use get_stat_value for MAX to include any modifiers already applied (e.g. racial to base primary impacting max)
                    max_value = self.get_stat_value(max_stat_type) 
                    
                    if current_stat_type not in self.derived_stats:
                        self.derived_stats[current_stat_type] = Stat(
                            name=current_stat_type,
                            base_value=max_value, 
                            category=StatCategory.DERIVED,
                            description=self._get_stat_description(current_stat_type)
                        )
                    else:
                        # If it exists (e.g. from loaded save), ensure it doesn't exceed the new max
                        self.derived_stats[current_stat_type].base_value = min(
                            self.derived_stats[current_stat_type].base_value,
                            max_value
                        )
                else:
                    default_current = 1.0 # Small default if MAX is somehow not calculable
                    if current_stat_type not in self.derived_stats:
                        self.derived_stats[current_stat_type] = Stat(
                            name=current_stat_type, base_value=default_current, category=StatCategory.DERIVED,
                            description=self._get_stat_description(current_stat_type)
                        )
                    logger.warning(f"{max_stat_type} not calculated, cannot initialize {current_stat_type} based on it. Initialized to {self.derived_stats[current_stat_type].base_value}.")


    def _get_stat_description(self, stat_type: Union[StatType, DerivedStatType]) -> str:
            """Get a description for a stat type."""
            descriptions = {
                # Primary stats
                StatType.STRENGTH: "Physical power, affects melee damage and carrying capacity.",
                StatType.DEXTERITY: "Agility and reflexes, affects ranged attacks, initiative, and dodge.",
                StatType.CONSTITUTION: "Physical resilience, affects health, stamina, and resistance to poison/disease.",
                StatType.INTELLIGENCE: "Mental acuity, affects spell power and learning ability.",
                StatType.WISDOM: "Intuition and perception, affects magical resistance and willpower.",
                StatType.CHARISMA: "Social influence, affects dialogue, prices, and persuasion.",
                StatType.WILLPOWER: "Mental fortitude, resistance to influence and fear.",
                StatType.INSIGHT: "Understanding situations, detecting lies, and sensing motives.",

                # Derived stats
                DerivedStatType.HEALTH: "Your current hit points. When this reaches zero, you are incapacitated.",
                DerivedStatType.MAX_HEALTH: "Your maximum hit points.",
                DerivedStatType.MANA: "Your current magical energy. Required for casting spells.",
                DerivedStatType.MAX_MANA: "Your maximum magical energy.",          
                DerivedStatType.STAMINA: "Your current physical energy. Required for special physical actions.",
                DerivedStatType.MAX_STAMINA: "Your maximum physical energy.",      
                DerivedStatType.RESOLVE: "Your current social/mental composure. Reduced by stress or social defeats.",
                DerivedStatType.MAX_RESOLVE: "Your maximum social/mental composure.",
                DerivedStatType.MELEE_ATTACK: "Your ability to hit opponents in melee combat.",
                DerivedStatType.RANGED_ATTACK: "Your ability to hit opponents with ranged weapons.",
                DerivedStatType.MAGIC_ATTACK: "Your ability to hit opponents with magical attacks.",
                DerivedStatType.DEFENSE: "Your ability to avoid physical damage.",
                DerivedStatType.MAGIC_DEFENSE: "Your ability to resist magical effects.",
                DerivedStatType.DAMAGE_REDUCTION: "Reduces incoming physical damage by a flat amount.",
                DerivedStatType.INITIATIVE: "Determines your turn order in combat.",
                DerivedStatType.CARRY_CAPACITY: "The maximum weight you can carry.",
                DerivedStatType.MOVEMENT: "How far you can move in combat.",
            }

            return descriptions.get(stat_type, "")

    def get_stat(self, stat_type: Union[StatType, DerivedStatType, str]) -> Optional[Stat]:
        """
        Get a stat by its type.

        Args:
            stat_type: The stat type to get.

        Returns:
            The stat if found, None otherwise.
        """
        if isinstance(stat_type, StatType):
            return self.stats.get(stat_type)
        elif isinstance(stat_type, DerivedStatType):
            return self.derived_stats.get(stat_type)
        else:
            # Try to find by string name (case insensitive)
            try:
                return self.stats[StatType.from_string(stat_type)]
            except ValueError:
                try:
                    return self.derived_stats[DerivedStatType.from_string(stat_type)]
                except ValueError:
                    return None

    def get_stat_value(self, stat_type: Union[StatType, DerivedStatType, str]) -> float:
        """
        Get the current value of a stat.

        Args:
            stat_type: The stat type to get.

        Returns:
            The current value of the stat.

        Raises:
            ValueError: If the stat is not found.
        """
        stat = self.get_stat(stat_type)
        if stat is None:
            raise ValueError(f"Stat not found: {stat_type}")

        # Get the base value with any direct modifiers on the stat object
        base_value = stat.value

        # Apply modifiers from the modifier manager
        mods = self.modifier_manager.get_stat_modifier_value(stat_type)

        # Apply flat modifiers first
        modified_value = base_value + mods['flat']

        # Then apply percentage modifiers
        if mods['percentage'] != 0:
            modified_value = modified_value * (1 + mods['percentage'] / 100)

        return modified_value

    def set_base_stat(self, stat_type: Union[StatType, str], value: float) -> None:
        """
        Set the base value of a primary stat.

        Args:
            stat_type: The stat type to set.
            value: The new base value.

        Raises:
            ValueError: If the stat is not found or is not a primary stat.
        """
        if isinstance(stat_type, str):
            try:
                stat_type = StatType.from_string(stat_type)
            except ValueError:
                raise ValueError(f"Unknown primary stat: {stat_type}")

        if stat_type not in self.stats:
            raise ValueError(f"Stat not found: {stat_type}")

        self.stats[stat_type].base_value = value
        logger.debug(f"Set base value of {stat_type} to {value}")

        # Recalculate derived stats that depend on this stat
        self._recalculate_derived_stats()
        
        # Emit signal with current stats
        self.stats_changed.emit(self.get_all_stats())

    def add_modifier(self, modifier: StatModifier) -> None:
        """
        Add a modifier to a stat.

        Args:
            modifier: The modifier to add.
        """
        self.modifier_manager.add_modifier(modifier)

        # If this is a primary stat, recalculate derived stats
        if any(modifier.stat == stat_type for stat_type in StatType):
            self._recalculate_derived_stats()

    def add_modifier_group(self, group: ModifierGroup) -> None:
        """
        Add a group of modifiers.

        Args:
            group: The modifier group to add.
        """
        self.modifier_manager.add_modifier_group(group)

        # Check if any primary stats are affected
        if any(any(modifier.stat == stat_type for stat_type in StatType) for modifier in group.modifiers):
            self._recalculate_derived_stats()

    def remove_modifier(self, modifier_id: str) -> bool:
        """
        Remove a specific modifier by its ID.

        Args:
            modifier_id: The unique ID of the modifier to remove.

        Returns:
            bool: True if the modifier was found and removed, False otherwise.
        """
        result = self.modifier_manager.remove_modifier(modifier_id)

        # Recalculate derived stats
        self._recalculate_derived_stats()
        
        # Emit signal with updated stats
        self.stats_changed.emit(self.get_all_stats())

        return result

    def remove_modifiers_by_source(self, source_type: ModifierSource, source_name: Optional[str] = None) -> int:
        """
        Remove all modifiers from a specific source.

        Args:
            source_type: The type of source to remove modifiers from.
            source_name: Optional specific source name to match.

        Returns:
            int: The number of modifiers removed.
        """
        removed = self.modifier_manager.remove_modifiers_by_source(source_type, source_name)

        if removed > 0:
            # Recalculate derived stats
            self._recalculate_derived_stats()
            
            # Emit signal with updated stats
            self.stats_changed.emit(self.get_all_stats())

        return removed

    def update_durations(self) -> Set[str]:
        """
        Update durations for all temporary modifiers and status effects.
        Removes expired modifiers, groups, and effects.

        Returns:
            Set of IDs of expired modifiers that were removed.
        """
        # Update modifiers
        expired_modifiers = self.modifier_manager.update_durations()

        # Update status effects
        expired_effects = self.status_effect_manager.update_durations()

        if expired_modifiers or expired_effects:
            # Recalculate derived stats
            self._recalculate_derived_stats()
            
            # Emit signal with updated stats
            self.stats_changed.emit(self.get_all_stats())

        # Combine the expired IDs
        expired = expired_modifiers.union(expired_effects)
        return expired

    def add_status_effect(self, effect: StatusEffect) -> None:
        """
        Add a status effect to the character.

        Args:
            effect: The effect to add
        """
        self.status_effect_manager.add_effect(effect)

        # Emit signal with updated stats if the effect has associated stat modifiers
        if effect.modifier_group: # Check for modifier_group instead of stat_modifiers
            # Recalculate derived stats as the group might affect primary stats
            self._recalculate_derived_stats() # Recalculate to be safe
            # Emit signal AFTER recalculating
            self.stats_changed.emit(self.get_all_stats())

    def remove_status_effect(self, effect_id: str) -> bool:
        """
        Remove a status effect by ID.

        Args:
            effect_id: The ID of the effect to remove

        Returns:
            True if the effect was found and removed, False otherwise
        """
        result = self.status_effect_manager.remove_effect(effect_id)
        
        # Emit signal with updated stats if the effect was removed
        if result:
            self.stats_changed.emit(self.get_all_stats())
            
        return result

    def has_status_effect(self, name: str) -> bool:
        """
        Check if the character has a specific status effect.

        Args:
            name: The name of the effect to check for

        Returns:
            True if the effect is active, False otherwise
        """
        return self.status_effect_manager.has_effect(name)

    def get_status_effects(self, effect_type: Optional[StatusEffectType] = None) -> List[StatusEffect]:
        """
        Get all active status effects, optionally filtered by type.

        Args:
            effect_type: Optional type to filter by

        Returns:
            List of active status effects
        """
        if effect_type:
            return self.status_effect_manager.get_effects_by_type(effect_type)
        return list(self.status_effect_manager.active_effects.values())

    def set_level(self, level: int) -> None:
        """
        Set the character level and recalculate derived stats.

        Args:
            level: The new level value.
        """
        if level < 1:
            level = 1

        self.level = level
        logger.debug(f"Set character level to {level}")

        # Recalculate derived stats
        self._recalculate_derived_stats()

    def set_current_stat(self, stat_type: Union[DerivedStatType, str], value: float) -> bool:
            """
            Set the *current* value of a derived stat (like HEALTH, MANA, STAMINA, RESOLVE).
            Handles clamping between 0 and the MAX value.

            Args:
                stat_type: The derived stat type to set (e.g., DerivedStatType.HEALTH).
                value: The new current value.

            Returns:
                True if the value was set successfully, False otherwise.
            """
            if isinstance(stat_type, str):
                try:
                    stat_type = DerivedStatType.from_string(stat_type)
                except ValueError:
                    logger.error(f"Cannot set current value for unknown derived stat: {stat_type}")
                    return False

            if stat_type not in self.derived_stats:
                logger.error(f"Cannot set current value: Derived stat {stat_type} not found.")
                # Attempt to initialize if max exists
                max_stat_type_name = f"MAX_{stat_type.name}"
                max_stat_type = getattr(DerivedStatType, max_stat_type_name, None)

                if max_stat_type and max_stat_type in self.derived_stats:
                    logger.warning(f"Initializing current stat {stat_type.name} based on max value.")
                    # Get the *current* max value, which includes modifiers
                    max_value = self.get_stat_value(max_stat_type)
                    self.derived_stats[stat_type] = Stat(
                        name=stat_type,
                        base_value=max_value, # Start at max
                        category=StatCategory.DERIVED,
                        description=self._get_stat_description(stat_type)
                    )
                else:
                    logger.warning(f"Cannot initialize stat {stat_type.name} as its MAX counterpart ({max_stat_type_name}) is not found.")
                    return False # Cannot set if stat doesn't exist and max doesn't exist

            # Determine the corresponding MAX stat using the name convention
            max_stat_type = getattr(DerivedStatType, f"MAX_{stat_type.name}", None)

            # Get the maximum value (including modifiers)
            max_value = float('inf') # Default to infinity if no max exists
            if max_stat_type:
                try:
                    max_value = self.get_stat_value(max_stat_type)
                except ValueError:
                    logger.warning(f"Could not find MAX stat ({max_stat_type}) for clamping {stat_type}. Using infinity.")


            # Clamp the new value
            clamped_value = max(0.0, min(float(value), max_value)) # Ensure float comparison

            # Check if the value actually changed
            if self.derived_stats[stat_type].base_value != clamped_value:
                self.derived_stats[stat_type].base_value = clamped_value
                logger.debug(f"Set current value of {stat_type} to {clamped_value}")
                # Emit signal *after* changing the value
                self.stats_changed.emit(self.get_all_stats()) # Ensure this line exists and is called
                return True
            else:
                # Value didn't change, no need to emit signal
                logger.debug(f"Value for {stat_type} already {clamped_value}. No change.")
                return False

    def get_current_stat_value(self, stat_type: Union[DerivedStatType, str]) -> float:
        """
        Get the *current* value of a derived stat (like HEALTH, MANA, STAMINA).
        This refers to the base_value of the *current* stat (e.g., HEALTH),
        not the MAX stat (e.g., MAX_HEALTH).

        Args:
            stat_type: The derived stat type (e.g., DerivedStatType.HEALTH).

        Returns:
            The current value, or 0.0 if not found.
        """
        if isinstance(stat_type, str):
            try:
                # Ensure we are looking for the *current* stat, not the MAX stat string
                if stat_type.upper().startswith("MAX_"):
                    logger.warning(f"get_current_stat_value called with MAX stat '{stat_type}'. Use get_stat_value instead.")
                    # Attempt to find corresponding current stat
                    current_stat_name = stat_type[4:] # Remove "MAX_"
                    try:
                        stat_type = DerivedStatType.from_string(current_stat_name)
                    except ValueError:
                        logger.error(f"Could not find current stat corresponding to '{stat_type}'")
                        return 0.0
                else:
                    stat_type = DerivedStatType.from_string(stat_type)
            except ValueError:
                logger.warning(f"Unknown derived stat type string: {stat_type}")
                return 0.0

        # Check if it's a resource stat that should have a current value stored
        resource_stats = [
            DerivedStatType.HEALTH, DerivedStatType.MANA,
            DerivedStatType.STAMINA, DerivedStatType.RESOLVE
        ]
        if stat_type not in resource_stats:
            logger.warning(f"get_current_stat_value called for non-resource stat '{stat_type}'. Returning calculated value.")
            # For non-resource stats, "current" is just the calculated value
            return self.get_stat_value(stat_type)


        stat = self.derived_stats.get(stat_type)
        # Return the base_value which holds the current tracked value for resources
        return stat.base_value if stat else 0.0

    def _recalculate_derived_stats(self) -> None:
        """Recalculate all derived stats based on the current primary stats."""
        logger.debug("Recalculating derived stats...")
        current_percentages = {}
        resource_pairs = [
            (DerivedStatType.HEALTH, DerivedStatType.MAX_HEALTH),
            (DerivedStatType.RESOLVE, DerivedStatType.MAX_RESOLVE),
            (DerivedStatType.MANA, DerivedStatType.MAX_MANA),
            (DerivedStatType.STAMINA, DerivedStatType.MAX_STAMINA)
        ]

        # Store current percentages BEFORE recalculating max values
        for current_stat_type, max_stat_type in resource_pairs:
            # Check if both current and max derived stats exist
            current_stat = self.derived_stats.get(current_stat_type)
            max_stat = self.derived_stats.get(max_stat_type)

            if current_stat and max_stat:
                current_val = current_stat.base_value
                # Use get_stat_value for MAX to include modifiers
                max_val = self.get_stat_value(max_stat_type)
                if max_val > 0:
                    current_percentages[current_stat_type] = current_val / max_val
                else:
                    current_percentages[current_stat_type] = 1.0
            elif current_stat: # Max stat doesn't exist yet
                current_percentages[current_stat_type] = 1.0 # Assume full if max is missing
            # else: # Current stat doesn't exist, nothing to store

        # Recalculate base values for all derived stats (including MAX values)
        for stat_type in DerivedStatType:
            # Skip recalculating the *current* value of resources here
            if stat_type in [DerivedStatType.HEALTH, DerivedStatType.RESOLVE, DerivedStatType.MANA, DerivedStatType.STAMINA]:
                continue

            try:
                # Calculate the base value (typically the MAX value or calculated derived value)
                new_base_value = calculate_derived_stat(
                    stat_type=stat_type,
                    stats=self.stats,
                    level=self.level,
                    config=self.config
                )
                # Ensure the stat exists before setting its base value
                if stat_type not in self.derived_stats:
                    self.derived_stats[stat_type] = Stat(
                        name=stat_type, base_value=0.0, category=StatCategory.DERIVED,
                        description=self._get_stat_description(stat_type)
                    )
                # Update the base_value of the stat (e.g., MAX_HEALTH's base value)
                self.derived_stats[stat_type].base_value = float(new_base_value)
                logger.debug(f"Recalculated base value for {stat_type}: {new_base_value}")

            except ValueError:
                # This occurs if no calculator exists for the stat type
                logger.debug(f"No calculator found for {stat_type}, skipping base value recalculation.")
                # Ensure the stat still exists if it was supposed to
                if stat_type not in self.derived_stats:
                    self.derived_stats[stat_type] = Stat(
                        name=stat_type, base_value=0.0, category=StatCategory.DERIVED,
                        description=self._get_stat_description(stat_type)
                    )
            except Exception as e:
                logger.error(f"Error recalculating derived stat {stat_type}: {e}", exc_info=True)

        # Restore current values based on percentages of the *new* calculated MAX values
        stats_changed_during_recalc = False
        for current_stat_type, max_stat_type in resource_pairs:
            # Ensure both current and max stats exist after recalculation
            if current_stat_type in self.derived_stats and max_stat_type in self.derived_stats:
                # Get the NEW max value (including modifiers)
                new_max_value = self.get_stat_value(max_stat_type)
                percentage = current_percentages.get(current_stat_type, 1.0)
                new_current_value = round(new_max_value * percentage)

                # Clamp the new current value
                clamped_current_value = max(0.0, min(new_current_value, new_max_value))

                # Update the base_value of the *current* stat if it changed
                if self.derived_stats[current_stat_type].base_value != clamped_current_value:
                    self.derived_stats[current_stat_type].base_value = clamped_current_value
                    stats_changed_during_recalc = True
                    logger.debug(f"Restored current value for {current_stat_type}: {clamped_current_value} (Max: {new_max_value})")

            elif max_stat_type in self.derived_stats:
                # Initialize current stat if it was missing but max exists now
                max_value = self.get_stat_value(max_stat_type)
                self.derived_stats[current_stat_type] = Stat(
                    name=current_stat_type, base_value=max_value, category=StatCategory.DERIVED,
                    description=self._get_stat_description(current_stat_type)
                )
                stats_changed_during_recalc = True
                logger.debug(f"Initialized current stat {current_stat_type} to max value: {max_value}")


        # Emit signal only if any value actually changed during the whole process
        if stats_changed_during_recalc:
            logger.debug("Emitting stats_changed signal after recalculation.")
            self.stats_changed.emit(self.get_all_stats())
        else:
            logger.debug("No stat values changed during recalculation, skipping signal emission.")

    def generate_random_stats(self, method: str = "standard", min_value: int = 8, max_value: int = 18) -> None:
        """Generate random stats using various methods.

        Args:
            method: The method to use for stat generation:
                - "standard": 3d6 for each stat
                - "heroic": 4d6 drop lowest for each stat
                - "balanced": Random values with a point total constraint
                - "uniform": Random values between min_value and max_value
            min_value: Minimum stat value (for uniform method)
            max_value: Maximum stat value (for uniform method)
        """
        for stat_type in StatType:
            value = 10  # Default fallback

            if method == "standard":
                # 3d6 (standard D&D style)
                value = sum(random.randint(1, 6) for _ in range(3))

            elif method == "heroic":
                # 4d6 drop lowest (heroic D&D style)
                rolls = [random.randint(1, 6) for _ in range(4)]
                rolls.remove(min(rolls))  # Drop the lowest roll
                value = sum(rolls)

            elif method == "balanced":
                # Random values with a point total constraint
                # Implementation ensures a reasonable total
                remaining_points = 70 - sum(s.base_value for s in self.stats.values())
                min_allowed = max(8, min_value)
                max_allowed = min(15, max_value)
                value = random.randint(min_allowed, max_allowed)
                if remaining_points < 0:
                    value = max(8, value + remaining_points)

            elif method == "uniform":
                # Simple random value in range
                value = random.randint(min_value, max_value)

            # Set the stat value
            self.set_base_stat(stat_type, value)

        # Recalculate derived stats
        self._recalculate_derived_stats()

        logger.debug(f"Generated random stats using {method} method")
        
        # Emit signal with the new stats
        self.stats_changed.emit(self.get_all_stats())

    def roll_stat(self, method: str = "standard") -> int:
        """Roll a single stat value using the specified method.

        Args:
            method: The method to use for rolling ("standard", "heroic")

        Returns:
            The rolled stat value
        """
        if method == "standard":
            # 3d6
            return sum(random.randint(1, 6) for _ in range(3))

        elif method == "heroic":
            # 4d6 drop lowest
            rolls = [random.randint(1, 6) for _ in range(4)]
            rolls.remove(min(rolls))  # Drop the lowest roll
            return sum(rolls)

        else:
            # Fallback
            return 10

    def perform_skill_check(
        self,
        stat_type: Union[StatType, DerivedStatType, str],
        difficulty: int,
        advantage: bool = False,
        disadvantage: bool = False,
        situational_modifier: int = 0,
        skill_name: Optional[str] = None
    ) -> SkillCheckResult:
        """Perform a skill check against a specific stat or using a named skill.

        Args:
            stat_type: The stat to check against
            difficulty: The difficulty class (DC) of the check
            advantage: Whether the check has advantage
            disadvantage: Whether the check has disadvantage
            situational_modifier: Any additional flat modifier applying to this specific check
            skill_name: Optional name of the skill being used (for display purposes)

        Returns:
            A SkillCheckResult object with detailed information

        Raises:
            ValueError: If the stat is not found
        """
        # If a skill name is provided, try to use the SkillManager
        if skill_name:
            try:
                from core.stats.skill_check import perform_skill_check_by_name
                return perform_skill_check_by_name(
                    skill_name=skill_name,
                    difficulty=difficulty,
                    stats_manager=self,
                    advantage=advantage,
                    disadvantage=disadvantage,
                    situational_modifier=situational_modifier
                )
            except (ImportError, AttributeError) as e:
                logger.warning(f"Error using skill-based check: {e}. Falling back to stat-based check.")
                # Fall back to stat-based check if skill check fails
        
        # Get the stat value
        try:
            stat_value = self.get_stat_value(stat_type)
        except ValueError as e:
            logger.error(f"Error getting stat value: {e}")
            # Use a default value if stat is not found
            stat_value = None

        # Calculate the modifier
        try:
            mod = get_modifier_from_stat(stat_value) if stat_value is not None else 0
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
            skill_name=skill_name
        )

        logger.debug(f"Skill check result: {result}")
        return result

    def calculate_check_probability(
        self,
        stat_type: Union[StatType, DerivedStatType, str],
        difficulty: int,
        advantage: bool = False,
        disadvantage: bool = False
    ) -> float:
        """Calculate the probability of success for a skill check.

        Args:
            stat_type: The stat to check against
            difficulty: The difficulty class (DC) of the check
            advantage: Whether the check has advantage
            disadvantage: Whether the check has disadvantage

        Returns:
            A float between 0 and 1 representing the success probability

        Raises:
            ValueError: If the stat is not found
        """
        # Get the stat value
        stat_value = self.get_stat_value(stat_type)

        # Calculate and return the success probability
        probability = calculate_success_chance(stat_value, difficulty, advantage, disadvantage)
        return probability

    def reset_for_new_game(self) -> None:
        """
        Fully reset this StatsManager for a fresh game session.

        - Clears all modifiers and status effects
        - Resets level to 1
        - Reinitializes primary and derived stats to defaults
        - Ensures current resource values (HP/Resolve/Mana/Stamina) are set to their maxima
        Emits a single stats_changed signal at the end.
        """
        try:
            # Clear modifiers and status effects first, to avoid influencing reinit calculations
            if hasattr(self, 'modifier_manager') and self.modifier_manager:
                self.modifier_manager.clear_all_modifiers()
            if hasattr(self, 'status_effect_manager') and self.status_effect_manager:
                self.status_effect_manager.clear_all_effects()
        except Exception:
            # Best effort; continue reset regardless
            pass

        # Reset level
        self.level = 1

        # Reinitialize stats dictionaries
        self.stats = {}
        self.derived_stats = {}
        # Primary then derived (derived depends on primary)
        self._initialize_primary_stats()
        self._initialize_derived_stats()

        # Ensure resource currents are exactly max after any internal clamping
        try:
            resource_pairs = [
                (DerivedStatType.HEALTH, DerivedStatType.MAX_HEALTH),
                (DerivedStatType.RESOLVE, DerivedStatType.MAX_RESOLVE),
                (DerivedStatType.MANA, DerivedStatType.MAX_MANA),
                (DerivedStatType.STAMINA, DerivedStatType.MAX_STAMINA),
            ]
            for cur_stat, max_stat in resource_pairs:
                max_val = self.get_stat_value(max_stat)
                # Use internal setter for proper clamping and signaling consistency (we'll emit once below)
                if cur_stat in self.derived_stats:
                    self.derived_stats[cur_stat].base_value = max_val
                else:
                    # Initialize if missing
                    self.derived_stats[cur_stat] = Stat(
                        name=cur_stat, base_value=max_val, category=StatCategory.DERIVED,
                        description=self._get_stat_description(cur_stat)
                    )
        except Exception:
            # Non-fatal: if anything goes wrong, the current values will still be sensible
            pass

        # Emit consolidated stats_changed after reset
        try:
            self.stats_changed.emit(self.get_all_stats())
        except Exception:
            pass

    def set_inventory_manager(self, inventory_manager) -> None:
        """
        Set the inventory manager reference for equipment modifier synchronization.
        
        Args:
            inventory_manager: The inventory manager instance
        """
        self._inventory_manager = inventory_manager
        logger.debug("Inventory manager reference set in StatsManager")
        
        # Sync equipment modifiers if available
        if inventory_manager:
            self.sync_equipment_modifiers()
    
    def sync_equipment_modifiers(self) -> None:
        """
        Synchronize equipment modifiers from inventory manager into the modifier system.
        This should be called whenever equipment changes.
        """
        if not self._inventory_manager:
            logger.debug("No inventory manager available for equipment modifier sync")
            return
            
        try:
            # Remove all existing equipment modifiers
            removed_count = self.modifier_manager.remove_modifiers_by_source(ModifierSource.EQUIPMENT)
            if removed_count > 0:
                logger.debug(f"Removed {removed_count} existing equipment modifiers")
            
            # Get current equipment modifiers from inventory manager
            if hasattr(self._inventory_manager, '_equipment_modifiers'):
                equipment_modifiers = self._inventory_manager._equipment_modifiers
                
                # Convert equipment modifiers to StatModifier objects
                for modifier_id, modifier_data in equipment_modifiers.items():
                    try:
                        # Get item name for source identification
                        source_name = f"Item ({modifier_data.get('source_slot', 'Unknown Slot')})"
                        if modifier_data.get('source_item'):
                            item = self._inventory_manager.get_item(modifier_data['source_item'])
                            if item:
                                source_name = item.name
                        
                        # Convert stat name string to appropriate enum
                        stat_name = modifier_data.get('stat', '')
                        stat_enum = None
                        
                        # Try StatType first
                        try:
                            stat_enum = StatType.from_string(stat_name)
                        except ValueError:
                            try:
                                stat_enum = DerivedStatType.from_string(stat_name)
                            except ValueError:
                                logger.warning(f"Unknown stat type in equipment modifier: {stat_name}")
                                continue
                        
                        # Create StatModifier object
                        stat_modifier = StatModifier(
                            stat=stat_enum,
                            value=float(modifier_data.get('value', 0)),
                            source_type=ModifierSource.EQUIPMENT,
                            source_name=source_name,
                            modifier_type=ModifierType.PERMANENT,  # Equipment modifiers are permanent while equipped
                            is_percentage=modifier_data.get('is_percentage', False),
                            description=f"Equipment bonus from {source_name}"
                        )
                        
                        # Add the modifier
                        self.modifier_manager.add_modifier(stat_modifier)
                        logger.debug(f"Added equipment modifier: {stat_modifier}")
                        
                    except Exception as e:
                        logger.error(f"Error creating equipment modifier {modifier_id}: {e}")
                        continue
                
                logger.info(f"Synchronized {len(equipment_modifiers)} equipment modifiers")
            else:
                logger.debug("Inventory manager has no equipment modifiers")
            
            # Recalculate derived stats to account for new modifiers
            self._recalculate_derived_stats()
            
            # Emit stats changed signal
            self.stats_changed.emit(self.get_all_stats())
            
        except Exception as e:
            logger.error(f"Error synchronizing equipment modifiers: {e}", exc_info=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "level": self.level,
            "stats": {str(stat_type): stat.to_dict() for stat_type, stat in self.stats.items()},
            "derived_stats": {str(stat_type): stat.to_dict() for stat_type, stat in self.derived_stats.items()},
            "modifiers": self.modifier_manager.to_dict(),
            "status_effects": self.status_effect_manager.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatsManager':
        """Create a StatsManager from a dictionary."""
        manager = cls()

        # Set level
        manager.level = data.get("level", 1)

        # Load stats
        manager.stats = {}
        for stat_name, stat_data in data.get("stats", {}).items():
            manager.stats[StatType.from_string(stat_name)] = Stat.from_dict(stat_data)

        # Load derived stats
        manager.derived_stats = {}
        for stat_name, stat_data in data.get("derived_stats", {}).items():
            manager.derived_stats[DerivedStatType.from_string(stat_name)] = Stat.from_dict(stat_data)

        # Load modifiers
        if "modifiers" in data:
            manager.modifier_manager = ModifierManager.from_dict(data["modifiers"])

        # Load status effects
        if "status_effects" in data:
            manager.status_effect_manager = StatusEffectManager.from_dict(data["status_effects"], manager)

        return manager

    def is_valid_stat_or_skill(self, name: str) -> bool:
        """
        Check if a given name is a valid stat or skill.
        
        Args:
            name: The name to check
            
        Returns:
            True if the name is a valid stat or skill, False otherwise
        """
        # Check if it's a primary stat
        try:
            StatType.from_string(name)
            return True
        except ValueError:
            pass
            
        # Check if it's a derived stat
        try:
            DerivedStatType.from_string(name)
            return True
        except ValueError:
            pass
            
        # Check if it's a skill
        try:
            skill_name = name.upper()
            if skill_name in [skill.name for skill in Skill]:
                return True
        except (ValueError, AttributeError):
            pass
            
        return False
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
            """
            Get all stats with their current values, organized by category.

            Returns:
                Dictionary with stat categories as keys and stat info as values.
            """
            result = {
                "primary": {},
                "combat": {},
                "resources": {},
                "social": {},
                "skills": {},
                "other": {}
            }

            # Add primary stats
            for stat_type, stat in self.stats.items():
                stat_name_key = stat_type.name # Use enum name "STR" as key
                result["primary"][stat_name_key] = {
                    "name": str(stat_type), # Keep display name "STR"
                    "value": self.get_stat_value(stat_type),
                    "base_value": stat.base_value,
                    "description": stat.description,
                    # --- REVERTED: Return the calculated value dict ---
                    "modifier_value": self.modifier_manager.get_stat_modifier_value(stat_type)
                }

            # Categorize derived stats
            resource_stats = [DerivedStatType.HEALTH, DerivedStatType.MAX_HEALTH, DerivedStatType.MANA, DerivedStatType.STAMINA]
            combat_stats = [
                DerivedStatType.MELEE_ATTACK, DerivedStatType.RANGED_ATTACK,
                DerivedStatType.MAGIC_ATTACK, DerivedStatType.DEFENSE,
                DerivedStatType.MAGIC_DEFENSE, DerivedStatType.INITIATIVE
            ]
            social_stats = [DerivedStatType.RESOLVE, DerivedStatType.MAX_RESOLVE]

            for stat_type, stat in self.derived_stats.items():
                stat_name_key = stat_type.name # Use enum name like "MELEE_ATTACK" as key
                stat_info = {
                    "name": str(stat_type), # Keep display name like "Melee Attack"
                    "value": self.get_stat_value(stat_type),
                    "base_value": stat.base_value,
                    "description": stat.description,
                    # --- REVERTED: Return the calculated value dict ---
                    "modifier_value": self.modifier_manager.get_stat_modifier_value(stat_type)
                }

                if stat_type in resource_stats:
                    result["resources"][stat_name_key] = stat_info # Use enum name key
                elif stat_type in combat_stats:
                    result["combat"][stat_name_key] = stat_info # Use enum name key
                elif stat_type in social_stats:
                    result["social"][stat_name_key] = stat_info # Use enum name key
                else: # CARRY_CAPACITY, MOVEMENT etc.
                    result["other"][stat_name_key] = stat_info # Use enum name key

            # Add skills (if skill management is implemented and needed here)
            # Example:
            # for skill in Skill:
            #     result["skills"][skill.name] = { ... skill details ... }

            return result
    
    def regenerate_combat_stamina(self) -> Tuple[float, Optional[str]]:
        """
        Regenerates a portion of stamina for the entity at the end of their turn in combat.
        The amount regenerated depends on CON modifier and other potential factors.
        Does not exceed MAX_STAMINA.

        Returns:
            Tuple: (amount_regenerated, narrative_message_for_log)
                Returns (0, None) if no regeneration occurred or stat not found.
        """
        try:
            current_stamina = self.get_current_stat_value(DerivedStatType.STAMINA)
            max_stamina = self.get_stat_value(DerivedStatType.MAX_STAMINA)

            if current_stamina >= max_stamina:
                return 0, None # Already at max

            # Base regeneration (e.g., 1 point + portion of CON modifier)
            con_value = self.get_stat_value(StatType.CONSTITUTION)
            con_mod = get_modifier_from_stat(con_value)
            
            base_regen = self.config.get("combat_stamina_regen_base", 1.0)
            con_regen_factor = self.config.get("combat_stamina_regen_con_factor", 0.5)
            
            regen_amount = base_regen + max(0, math.floor(con_mod * con_regen_factor))

            # Placeholder for STAMINA_REGENERATION stat/modifier
            # Example: regen_modifier_value = self.get_stat_value(DerivedStatType.STAMINA_REGENERATION)
            # regen_amount += regen_modifier_value

            # Placeholder for status effect modifiers
            if self.has_status_effect("Fatigued"): # Assuming StatusEffectManager is on StatsManager
                regen_amount *= 0.5 # Halve regeneration if fatigued
            if self.has_status_effect("Energized"):
                regen_amount *= 1.5 # Increase regeneration if energized
            
            regen_amount = max(0, round(regen_amount)) # Ensure non-negative and integer

            if regen_amount == 0:
                return 0, None

            new_stamina = min(current_stamina + regen_amount, max_stamina)
            actual_regenerated = new_stamina - current_stamina

            if actual_regenerated > 0:
                self.set_current_stat(DerivedStatType.STAMINA, new_stamina) # This emits stats_changed
                
                entity_name = "Entity" # Placeholder, ideally get actual name
                # This manager might not know the entity's name directly.
                # The CombatManager, when calling this, could pass the name for the message.
                # For now, a generic message part.
                
                narrative = f"  {entity_name} recovers {actual_regenerated:.0f} stamina."
                logger.debug(f"Stamina regenerated by {actual_regenerated:.0f} to {new_stamina:.0f}/{max_stamina:.0f}")
                return actual_regenerated, narrative
            
            return 0, None

        except ValueError as e: # e.g. stat not found
            logger.warning(f"Could not regenerate stamina: {e}")
            return 0, None
        except Exception as e:
            logger.error(f"Unexpected error during stamina regeneration: {e}", exc_info=True)
            return 0, None


# Singleton instance for the stats manager
_stats_manager_instance = None

# Convenience function to get the stats manager
def get_stats_manager() -> StatsManager:
    """Get the stats manager instance."""
    global _stats_manager_instance
    if _stats_manager_instance is None:
        _stats_manager_instance = StatsManager()
    
    return _stats_manager_instance
