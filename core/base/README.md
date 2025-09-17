# Core Base Module (`core/base`)

This module provides the foundational building blocks and core systems for the game engine. It contains the essential infrastructure for game operation, including state management, command handling, the main game loop, configuration loading, and the central engine coordination.

## Purpose

The `core/base` module establishes the fundamental architecture upon which the rest of the game is built. It defines how game state is managed, how player input is processed, how time progresses, and how these different systems interact under the control of the main `GameEngine`.

## Key Components

### `GameEngine` (`engine.py`)

*   **Role**: The central coordinator and main entry point for game operations.
*   **Responsibilities**:
    *   Initializes and manages other base components (`StateManager`, `CommandProcessor`, `GameLoop`) and integrates with other systems like `AgentManager`.
    *   Handles game initialization (starting new games, loading saved games).
    *   Processes player input, routing it to `CommandProcessor` for direct commands or `AgentManager` for interactive text/LLM processing.
    *   Manages the game loop lifecycle (running, stopping, pausing).
    *   Coordinates auto-saving based on configuration.
    *   Emits game output (system messages, narration, etc.) via the `output_generated` PySide6 signal for decoupling from UI components.
*   **Access**: Singleton, accessed via `get_game_engine()`.

### `StateManager` (`state/state_manager.py`)

*   **Role**: Manages the lifecycle and persistence of the game state.
*   **Responsibilities**:
    *   Creates new `GameState` instances for new games.
    *   Saves the current `GameState` to a file, including player data, world data, stats, inventory, conversation history, etc.
    *   Loads `GameState` from save files, restoring the game to a previous point.
    *   Handles serialization and deserialization of the entire game state.
    *   Provides access to the currently active `GameState`.
    *   Manages save files (listing available saves, deleting saves, undoing deletion).
*   **Access**: Singleton, accessed via `get_state_manager()`.

### `CommandProcessor` (`commands.py`)

*   **Role**: Parses and executes player commands.
*   **Responsibilities**:
    *   Maintains a registry of standard game commands (e.g., `help`, `save`, `load`, `look`, `inventory`) and their handlers.
    *   Supports registration and execution of developer-specific commands (prefixed with `//`).
    *   Parses command arguments, respecting quoted strings.
    *   Processes special commands embedded within LLM responses (e.g., `{ITEM_CREATE chest}`).
    *   Defines `CommandResult` and `CommandStatus` to provide standardized outcomes for command execution (success, failure, error, exit, help).
*   **Access**: Singleton, accessed via `get_command_processor()`.

### `GameLoop` & `GameTime` (`game_loop.py`)

*   **`GameLoop`**:
    *   **Role**: Manages the progression of game time and scheduled events.
    *   **Responsibilities**: Operates on a tick-based system. Advances in-game time based on real-time elapsed and the current `GameSpeed`. Controls the game's speed (paused, normal, fast). Executes callbacks on each tick. Manages and executes `ScheduledEvent` instances at specific game times.
    *   **Access**: Singleton, accessed via `get_game_loop()`.
*   **`GameTime`**:
    *   **Role**: Represents and manipulates the in-game time.
    *   **Responsibilities**: Tracks the current game time (seconds since a starting epoch). Provides methods to get formatted date/time strings and the general time of day (Morning, Afternoon, etc.).
*   **`ScheduledEvent`**: Represents a callback function scheduled to run at a specific future game time, potentially repeating at intervals.

### State Dataclasses (`state/`)

These dataclasses define the structure of the game's state, managed by the `StateManager`.

*   **`GameState` (`game_state.py`)**: The top-level container for all state related to a single game session. It aggregates `PlayerState`, `WorldState`, an optional `CombatManager` (when combat is active), the conversation history, and session metadata (ID, timestamps, version).
*   **`PlayerState` (`player_state.py`)**: Holds all persistent information about the player character, including name, race, class (path), background, sex, level, experience, current location (area and district), references to their inventory and stats manager instances, equipped items, and quest status.
*   **`WorldState` (`world_state.py`)**: Contains information about the game world environment, such as the current game time, date, weather conditions, day/night status, active magical effects, global variables (used for tracking world events or quest progression), and a list of active world events.

### `GameConfig` (`config.py`)

*   **Role**: Manages game configuration settings.
*   **Responsibilities**: Loads configuration data from JSON files (e.g., `config/game_config.json`). Provides a simple interface to access configuration values throughout the application. Handles default values if specific settings are missing.
*   **Access**: Singleton, accessed via `get_config()`.

## Interactions

*   The `GameEngine` acts as the central orchestrator. It receives player input and uses the `CommandProcessor` (for commands like `/save`) or the `AgentManager` (for natural language) to handle it. It uses the `StateManager` to load/save the game and access the current `GameState`. It controls the `GameLoop` to manage time progression and pausing.
*   The `StateManager` is responsible for the `GameState` object. When saving/loading, it serializes/deserializes the `GameState`, which includes the nested `PlayerState` and `WorldState`, along with data from associated systems like stats and inventory.
*   The `CommandProcessor` and `AgentManager` operate on the current `GameState` provided by the `GameEngine` or `StateManager` to understand the context (player location, inventory, world variables) needed to execute commands or generate relevant LLM responses.
*   The `GameLoop` advances the `game_time` within the `WorldState` (managed by `StateManager`) and triggers scheduled events or tick callbacks, which might affect other parts of the state (e.g., NPC behavior, world events).

## Dependencies

*   **Internal Core Modules**:
    *   `core.utils`: For logging, JSON handling, save file management (`SaveManager`).
    *   `core.agents`: The `GameEngine` interacts with the `AgentManager` for LLM processing.
    *   `core.inventory`: `StateManager` saves/loads inventory data; `GameEngine` registers inventory commands.
    *   `core.combat`: `GameState` can hold a `CombatManager`; `StateManager` saves/loads combat state.
    *   `core.character`: `StateManager` interacts with `NPCSystem`.
    *   `core.stats`: `StateManager` saves/loads stats data via `StatsManager`.
*   **External Libraries**:
    *   `PySide6`: Used by `GameEngine` for its `output_generated` signal, enabling decoupling from the UI.

## Usage Example

The game engine is typically accessed through the `get_game_engine()` function, which returns a singleton instance of the `GameEngine` class:

```python
from core.base.engine import get_game_engine

# Get the engine instance
engine = get_game_engine()

# Start a new game (or load one)
engine.start_new_game(player_name="Adventurer")
# or engine.load_game("my_save.json")

# Process player input (command or natural language)
result = engine.process_command("look around") # Handled by LLM if enabled
result_save = engine.process_command("/save my_adventure") # Direct command

# Output is handled via the engine's output_generated signal
# (Connect a slot/function to this signal in your UI or main application)
