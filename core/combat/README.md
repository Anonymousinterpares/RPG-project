# Combat System (`core.combat`)

This module implements the turn-based combat system for the RPG game. It handles combat encounters, including entity management, turn order, action resolution, damage calculation, status effects, and interaction with other core systems.

## Overview

The combat system provides the framework for resolving conflicts between the player and enemies. Key features include:

-   **Turn-Based Flow:** Combat proceeds in rounds, with entities taking turns based on initiative.
-   **Action System:** Entities can perform various actions like attacking, casting spells, defending, using items, or attempting to flee.
-   **Stat Integration:** Combat calculations (hit chance, damage, defense, initiative) rely heavily on entity stats defined in `core.stats`.
-   **Dice Mechanics:** Uses the `core.utils.dice` module for randomized outcomes like attack rolls, damage, and critical hits/fumbles.
-   **Status Effects:** Entities can be affected by various conditions (e.g., defending, poisoned) that modify their capabilities or inflict damage over time.
-   **Combat Logging:** Records significant events during the encounter.

## Core Components

### 1. Combat Manager (`combat_manager.py`)

The central orchestrator of combat encounters.

-   **`CombatManager` Class:**
    -   Manages the overall state of a combat encounter (`CombatState`: `NOT_STARTED`, `IN_PROGRESS`, `PLAYER_VICTORY`, `PLAYER_DEFEAT`, `FLED`).
    -   Holds references to all participating `CombatEntity` objects.
    -   Determines turn order by calculating initiative (`_determine_initiative`) based on entity stats and a random roll.
    -   Processes `CombatAction` objects submitted by entities, resolving their effects (damage, healing, status effects, etc.).
    -   Advances turns (`_advance_turn`) and rounds.
    -   Checks for combat end conditions (player defeat, enemy defeat).
    -   Maintains a `combat_log` of events.
    -   Provides methods to start combat (`start_combat`) and get the current state (`get_combat_summary`).

### 2. Combat Entity (`combat_entity.py`)

Represents any participant in combat.

-   **`EntityType` Enum:** Defines the type of entity (`PLAYER`, `NPC`, `ALLY`, `ENEMY`, `CREATURE`).
-   **`CombatEntity` Class:**
    -   Stores the entity's current state in combat: ID, name, type, stats (from `core.stats`), current/max HP, MP, Stamina.
    -   Manages active `status_effects` (as a set of strings).
    -   Tracks initiative value and position (currently basic).
    -   Provides methods for taking damage (`take_damage`), healing (`heal`), spending/restoring resources (`spend_mp`, `spend_stamina`, etc.), and managing status effects (`add_status_effect`, `remove_status_effect`).
    -   Includes serialization methods (`to_dict`, `from_dict`).

### 3. Combat Action (`combat_action.py`)

Defines actions that entities can perform.

-   **`ActionType` Enum:** Categorizes actions (`ATTACK`, `SPELL`, `SKILL`, `DEFEND`, `ITEM`, `FLEE`, `MOVE`, `OTHER`).
-   **`CombatAction` Dataclass:** Base representation for an action, including performer ID, targets, costs (MP, stamina), dice notation for effects, description, and special effects.
-   **Specialized Action Subclasses:** Provide constructors and specific details for common actions:
    -   `AttackAction`: Basic attacks.
    -   `SpellAction`: Casting spells.
    -   `DefendAction`: Taking a defensive stance (applies "defending" status).
    -   `ItemAction`: Using items (currently basic implementation).
    -   `FleeAction`: Attempting to escape combat.

### 4. Developer Commands (`dev_commands.py`)

Provides commands for testing and debugging the combat system via the command processor (`core.base.commands`).

-   Registers commands like `//start_combat`, `//combat_status`, `//set_hp`, `//combat_action`.
-   Includes helper functions (`create_player_combat_entity`, `create_npc_combat_entity`) to convert game state objects (Player, NPCs from `core.character.npc_system`) into `CombatEntity` instances suitable for the `CombatManager`.

## Combat Flow

1.  **Initialization (`CombatManager.start_combat`):**
    -   Player and enemy entities are added to the `CombatManager`.
    -   Initiative is rolled for all entities (`_determine_initiative`).
    -   Turn order is established based on initiative rolls (highest first).
    -   Combat state is set to `IN_PROGRESS`, round counter starts at 1.
    -   Combat start and turn order are logged.
2.  **Turn Progression (`CombatManager._advance_turn`):**
    -   The manager identifies the `CombatEntity` whose turn it is based on the `turn_order` and `current_turn_index`.
    -   The entity (or its controlling agent/player) decides on a `CombatAction`.
3.  **Action Execution (`CombatManager.perform_action`):**
    -   The chosen `CombatAction` is passed to the `CombatManager`.
    -   The manager validates the action (is it the performer's turn? enough resources?).
    -   The appropriate handler (`_handle_attack_action`, `_handle_spell_action`, etc.) is called.
    -   **Resolution:**
        -   **Attack:** Roll to hit (d20 + bonus) vs. target's defense. On hit, roll damage (`dice_notation`), apply damage to target's HP. Check for critical hits/fumbles.
        -   **Spell/Item:** Check resource costs, apply effects (damage, healing, status effects) based on `dice_notation` and `special_effects`.
        -   **Defend:** Apply "defending" status effect.
        -   **Flee:** Calculate flee chance based on agility comparison, roll percentage dice.
    -   Results are logged.
4.  **State Check (`CombatManager._check_combat_state`):**
    -   After each action, the manager checks if all players or all enemies are defeated.
    -   If an end condition is met, the `state` is updated (`PLAYER_VICTORY`, `PLAYER_DEFEAT`).
    -   If the flee action was successful, the state is set to `FLED`.
5.  **Next Turn:**
    -   If combat is still `IN_PROGRESS`, the turn index advances (`_advance_turn`).
    -   Defeated entities are skipped.
    -   If the turn order wraps around, the round number increments.
    -   The process repeats from step 2.

## Key Mechanics

### Damage Calculation

-   Handled primarily within `CombatManager._handle_attack_action` and effect application in other handlers.
-   **Hit Chance:** Typically involves a d20 roll + attacker's relevant bonus (e.g., from stats) compared against the target's defense value (derived stat).
-   **Damage:** Based on the action's `dice_notation` (e.g., "2d6+3"), rolled using `core.utils.dice.roll_dice_notation`.
-   **Critical Hits/Fumbles:** Detected using `core.utils.dice.check_success` based on the d20 roll. Criticals usually involve rolling extra damage dice (`core.utils.dice.roll_critical`).
-   **Application:** Damage is applied using `CombatEntity.take_damage`, which reduces `current_hp`.

### Status Effects

-   Managed by `CombatEntity` (stored in `status_effects` set).
-   Applied by actions (e.g., `DefendAction` adds "defending", spells/items can add others via `special_effects`).
-   The *effects* of status effects (e.g., damage reduction for "defending", damage over time for "burning") need to be implemented within the relevant calculation steps (e.g., modifying damage taken in `take_damage`, applying DoT at the start/end of a turn - *Note: Turn-based effect processing is not explicitly shown in the current `CombatManager` code*).

## Dependencies and Interactions

The `core.combat` module relies on several other parts of the codebase:

-   **`core.stats`:** Essential for `CombatEntity` attributes (HP, MP, Stamina) and combat calculations (initiative, attack bonuses, defense). `StatType` and `DerivedStatType` are used directly.
-   **`core.utils.dice`:** Used extensively by `CombatManager` for all random rolls (initiative, hit chance, damage, flee chance).
-   **`core.base.commands`:** Used by `__init__.py` and `dev_commands.py` to register console commands.
-   **`core.base.state`:** Used by `dev_commands.py` to access the global game state (player info, NPC system).
-   **`core.character.npc_system`:** Used by `dev_commands.py` to create `CombatEntity` instances for enemies when starting test combats.
-   **`core.items` (Planned):** The `ItemAction` exists, but full integration (checking inventory, consuming items) is not yet implemented in `CombatManager._handle_item_action`.
-   **`core.utils.logging_config`:** Used for logging combat events and debug information.

## Configuration

While specific combat rules (like status effect details, critical hit multipliers) might be intended for external configuration (e.g., JSON files), the analyzed code within `core/combat/` does not currently show direct reading from configuration files. Default values or logic are embedded within the code (e.g., flee chance calculation, defend action effect).

## Usage Examples

*(Existing examples retained for demonstrating basic API usage)*

### 1. Starting Combat

```python
from core.combat.combat_manager import CombatManager
from core.combat.combat_entity import CombatEntity, EntityType
# Assume player_stats and enemy_stats are dictionaries populated from core.stats
# Assume player and enemy are created similar to dev_commands helpers

# Create combat manager
combat_mgr = CombatManager()

# Start combat
combat_mgr.start_combat(player_entity, [enemy_entity])
```

### 2. Performing Combat Actions

```python
from core.combat.combat_action import AttackAction, DefendAction

# Assume combat_mgr is an active CombatManager instance
# Assume current entity ID is known

# Attack action
attack = AttackAction(
    performer_id="player", # Use actual entity ID
    target_id="enemy_goblin_1", # Use actual entity ID
    weapon_name="sword",
    dice_notation="1d8+3" # Example damage
)
result = combat_mgr.perform_action(attack)

# Defend action
defend = DefendAction(performer_id="player") # Use actual entity ID
result = combat_mgr.perform_action(defend)
```

### 3. Getting Combat Information

```python
from core.combat.combat_manager import CombatState

# Assume combat_mgr is an active CombatManager instance

# Get combat summary
summary = combat_mgr.get_combat_summary()
print(f"Round: {summary['round']}, Turn: {summary['current_turn']}")
for entity_id, entity_data in summary['entities'].items():
    print(f"  {entity_data['name']}: {entity_data['hp']}")

# Check if combat has ended
if combat_mgr.state != CombatState.IN_PROGRESS:
    print(f"Combat ended: {combat_mgr.state.name}")

# Get recent combat log entries
for entry in summary['log']:
    print(entry)
```

## LLM Integration

*(Existing section retained)*

The combat system supports integration with the LLM narrative system:

-   Combat results can be narrated by the LLM.
-   Special combat actions can be triggered through narrative.
-   The LLM can apply appropriate modifiers based on narrative context.
-   Combat log provides content for narrative descriptions.

## Future Enhancements

*(Existing section retained)*

-   Multiple target and area effect attacks/spells.
-   Positioning and movement mechanics.
-   More complex action economy (e.g., main action, bonus action).
-   Tactical options (flanking, cover, opportunity attacks).
-   Combat AI for enemy decision-making (potentially via `core.agents`).
-   Full integration with `core.items` for item consumption.
-   Processing of duration-based status effects each turn.

## Testing

*(Existing section retained)*

The combat system requires comprehensive testing, including:
-   Initiative and turn order logic.
-   Attack/spell/item/flee action resolution.
-   Status effect application and interaction.
-   Combat state transitions (victory, defeat, flee).
-   Edge cases and error handling.
