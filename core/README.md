# Core Module

The `core` module serves as the heart of the game engine, containing the primary logic, data structures, and systems that drive the gameplay experience. It is designed with a modular approach, organizing distinct functionalities into specific sub-modules.

## Overview

This module encapsulates the fundamental mechanics of the game, including state management, character representation, combat resolution, inventory handling, interaction with Large Language Models (LLMs), and various utility functions. The sub-modules are designed to interact with each other to create a cohesive game world.

## Architecture

The core module emphasizes modularity and separation of concerns. Key architectural patterns include:
*   **State Management:** Centralized handling of game, world, and player states within the `base/state` submodule.
*   **Command Pattern:** Processing player and system actions via a command system in `base/commands.py`.
*   **Agent-Based Systems:** Utilizing LLM-powered agents (`agents/`) for dynamic content generation and rule enforcement.
*   **Component-Based Structure:** Various managers (Inventory, Stats, Character, Combat, LLM) handle specific domains.

## Sub-Modules

Below is a breakdown of the primary sub-modules within `core`:

### `agents/`

Contains LLM-powered game agents responsible for:
*   Generating narrative content and descriptions (`narrator.py`).
*   Enforcing game rules and validating actions (`rule_checker.py`).
*   Evaluating game context (`context_evaluator.py`).
*   Coordinating agent interactions (`agent_manager.py`).

### `base/`

Provides the foundational engine components:
*   Main game engine logic (`engine.py`).
*   Game loop and time management (`game_loop.py`).
*   Command processing infrastructure (`commands.py`).
*   Configuration loading (`config.py`).
*   **`base/state/`**: Manages the different states of the game, including `game_state.py`, `player_state.py`, and `world_state.py`, coordinated by `state_manager.py`.

### `character/`

Manages all aspects of characters, both player and non-player characters (NPCs):
*   NPC creation, logic, memory, and persistence (`npc_*.py` files).
*   Character background generation (`background_generator.py`).
*   Overall coordination of character-related systems (`npc_system.py`, `npc_manager.py`).

### `combat/`

Handles the systems and logic required for combat encounters:
*   Defining combat actions (`combat_action.py`).
*   Representing entities involved in combat (`combat_entity.py`).
*   Managing the flow and rules of combat (`combat_manager.py`).

### `inventory/`

Manages all item-related functionality:
*   Core inventory and equipment management (`inventory_manager.py`, `equipment_manager.py`).
*   Item representation and creation (`item.py`, `item_factory.py`).
*   Currency management (`currency_manager.py`).
*   Dynamic item creation based on narrative context (`narrative_item_manager.py`).

### `llm/`

Integrates with Large Language Models (LLMs):
*   Manages interactions with different LLM providers (`llm_manager.py`, `provider_manager.py`).
*   Handles LLM settings and configuration (`settings_manager*.py`).

### `stats/`

Defines and manages statistics for characters and potentially items:
*   Base stat definitions and management (`stats_base.py`, `stats_manager.py`).
*   Handling of temporary or permanent modifiers (`modifier.py`, `modifier_manager.py`).
*   Calculation of derived statistics (`derived_stats.py`).
*   Skill check resolution (`skill_check.py`).
*   Combat-related effects tied to stats (`combat_effects.py`).

### `utils/`

Contains common utility functions and classes used across the core module:
*   Dice rolling (`dice.py`).
*   Data structures (`dotdict.py`).
*   Serialization/JSON handling (`json_utils.py`).
*   Logging setup (`logging_config.py`).
*   Saving and loading game state (`save_manager.py`).
*   Time-related functions (`time_utils.py`).
