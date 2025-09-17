# Stats and Rules System

This module provides a comprehensive stats and rules framework for the RPG game, including character statistics, modifiers, derived attributes, dice-based calculations, and combat mechanics.

## Overview

The stats system implements traditional RPG character attributes with support for:

- Primary stats (STR, DEX, CON, INT, WIS, CHA)
- Derived statistics (Health, Mana, Stamina, etc.)
- Temporary and permanent modifiers
- Race and class-based stat bonuses
- Combat calculations
- Dice-based resolution mechanics

## System Components

### 1. Stats Base (`stats_base.py`)

Defines the fundamental data structures for character statistics:

- `StatType` - Enum for primary stats (STR, DEX, CON, INT, WIS, CHA)
- `DerivedStatType` - Enum for calculated stats (Health, Mana, Initiative, etc.)
- `StatCategory` - Grouping for different types of stats
- `Stat` - Base class representing a single character statistic with modifiers

### 2. Derived Stats (`derived_stats.py`)

Contains formulas for calculating secondary attributes based on primary stats:

- Health calculation based on Constitution
- Mana calculation based on Intelligence and Wisdom
- Initiative calculation based on Dexterity
- Carry capacity calculation based on Strength
- Combat stats (attack, defense) derivation
- Movement speed calculation

### 3. Modifier System (`modifier.py` & `modifier_manager.py`)

Manages temporary and permanent bonuses to character stats:

- `ModifierType` - Categories of modifiers (permanent, semi-permanent, temporary)
- `ModifierSource` - Sources of modifiers (racial, class, equipment, spell, etc.)
- `StatModifier` - Individual modifier with source, value, duration, etc.
- `ModifierGroup` - Collection of related modifiers (e.g., from a single buff spell)
- `ModifierManager` - Tracks and applies all active modifiers

### 4. Stats Manager (`stats_manager.py`)

Coordinates all character statistics and provides the main interface for accessing stat values:

- Initializes primary and derived stats
- Applies racial and class bonuses
- Calculates current values with modifiers
- Manages level-based progression
- Serializes stats for save/load

### 5. Dice System (`core/utils/dice.py`)

Provides functions for dice-based calculations:

- Basic dice rolling with XdY notation
- Advantage/disadvantage mechanics (roll twice, take higher/lower)
- Critical hit calculations
- Probability calculations
- Parsing dice notation strings

### 6. Combat System (`core/combat/`)

Implements turn-based combat mechanics:

- `CombatEntity` - Represents combatants with stats and status effects
- `CombatAction` - Different actions in combat (attack, defend, spell, etc.)
- `CombatManager` - Coordinates combat flow, turn order, and resolution

## Configuration

Stats and rules are configured through JSON files:

- `config/character/stats_config.json` - Base stats, derived stat formulas, progression curves
- `config/combat/combat_config.json` - Combat rules, dice patterns, critical thresholds

## Usage Examples

### 1. Accessing Character Stats

```python
# Get the stats manager from the state manager
stats_manager = get_state_manager().stats_manager

# Get a primary stat value
strength = stats_manager.get_stat_value(StatType.STRENGTH)

# Get a derived stat
health = stats_manager.get_stat_value(DerivedStatType.HEALTH)

# Get all stats organized by category
all_stats = stats_manager.get_all_stats()
```

### 2. Adding Stat Modifiers

```python
# Create a temporary strength bonus
modifier = StatModifier(
    stat=StatType.STRENGTH,
    value=2,
    source_type=ModifierSource.SPELL,
    source_name="Bull's Strength",
    modifier_type=ModifierType.TEMPORARY,
    duration=10  # 10 turns
)

# Add the modifier
stats_manager.add_modifier(modifier)
```

### 3. Using the Dice System

```python
from core.utils.dice import roll_dice_notation, roll_with_advantage

# Roll 2d6+3
result = roll_dice_notation("2d6+3")
# Returns: {'rolls': [4, 6], 'total': 13, 'num_dice': 2, 'sides': 6, 'modifier_type': '+', 'modifier_value': 3}

# Roll with advantage
result, roll1, roll2 = roll_with_advantage(20)
```

### 4. Combat Example

```python
from core.combat.combat_manager import CombatManager
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import AttackAction

# Create combat manager
combat_mgr = CombatManager()

# Start combat between player and enemies
combat_mgr.start_combat(player_entity, enemy_entities)

# Perform an attack action
action = AttackAction(
    performer_id=player_entity.id,
    target_id=enemy_entity.id,
    weapon_name="sword",
    dice_notation="1d8+3"
)
result = combat_mgr.perform_action(action)
```

## GUI Integration

The stats system integrates with the GUI through the following components:

- `CharacterSheetWidget` - Displays all character stats with tooltips
- Automatic updates when stats change
- Resource bars for health, mana, and stamina
- Right-click context menus for detailed stat information

## Save/Load Integration

Stats are automatically saved and loaded as part of the game state:

- Stats are serialized to dictionaries for JSON storage
- ModifierManager state is preserved in save files
- Temporary modifiers with durations are properly restored

## LLM Integration

The system supports integration with the LLM narrative system through special commands:

- `{STAT_MODIFY:character:stat:value:duration:reason}` - Apply stat modifiers based on narrative
- `{RULE_CHECK:action:stat:difficulty:context}` - Check if an action succeeds based on stats
- `{CONTEXT_EVAL:situation:relevant_stats:importance}` - Evaluate context based on character stats

## Future Enhancements

- Character progression system with level-ups and stat allocation
- Racial and class-specific abilities
- More sophisticated combat mechanics with action economy
- Skill system built on core stats
- Equipment enhancement effects on stats
- Character conditions (tired, sick, etc.) affecting stats

## Testing

The stats system includes test cases to verify correct operation:
- Stat calculation tests
- Modifier application and duration tests
- Combat resolution tests
- Dice probability tests

Note: The system is currently implemented but needs comprehensive testing.
