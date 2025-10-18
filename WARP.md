# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

***CURRENT TASK -> WORKING ON magic SYSTEMS -> ALWAYS REFER TO THE DRAFTER DIAGNOSIS & PLAN FROM magic_system_overhaul.md PLACED IN PROJECT ROOT FOLDER.
If any step is finished, amend this file to reflect the latest stage***

TREAT USER AS A PRODUCT/GAME MANAGER, NOT A DEVELOPER -> ALWAYS TRANSLATE TECHNICAL SOLUTION TO A NON-CODE LOGIC WHILE EXPLAIN SOMETHING

I. The Golden Rules (Most Important Principles)
Separation of Concerns is Paramount: The core logic (game state, combat mechanics, stats) MUST NOT directly interact with the gui. The gui observes and reacts to changes in the core.
Use Singleton Getters: The project extensively uses singleton managers. NEVER instantiate classes like GameEngine, StateManager, InventoryManager, AgentManager, etc., directly. Always use their respective get_*() functions (e.g., get_game_engine()).
UI Updates are Event-Driven: For complex, sequential UI updates (especially in combat), the core logic MUST NOT call UI methods. It must create and queue DisplayEvent objects with the CombatOutputOrchestrator. The UI listens for signals from the orchestrator. This is the most critical pattern for combat flow.
Configuration is Data-Driven: All game world data (races, classes, items, locations, etc.) is defined in .json files within the config/ directory. Core game logic should be flexible enough to handle changes in these files without code modification. Use the GameConfig singleton (get_config()) to access this data.
II. Project Structure & Imports
Directory Structure:
config/: All static game data (JSON files).
core/: Backend game logic, state management, and systems. No UI code here.
gui/: All PySide6 UI code, including windows, dialogs, and components.
world_configurator/: A separate, standalone PySide6 tool for editing config/ files. Treat it as a distinct application.
Import Strategy:
Use absolute imports from the project root (e.g., from core.base.engine import GameEngine).
To prevent circular dependencies, use forward references with strings or the if TYPE_CHECKING: block.
code
Python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.base.engine import GameEngine
III. Core Architecture & Design Patterns
State Management:
All game state is centralized in the GameState object.
Always access the current state via get_state_manager().current_state.
GameState contains PlayerState and WorldState. Do not create separate instances of these.
Modifications to player stats, inventory, or state should be done through the appropriate managers (get_stats_manager(), get_inventory_manager()), which then update the state objects.
Orchestration for UI (Critical for Combat):
The Problem: Combat involves a sequence of events (narrative, rolls, damage, UI updates) that need to be displayed sequentially, with delays.
The Solution: The CombatOutputOrchestrator (core/orchestration/combat_orchestrator.py).
Your Task:
When implementing core logic (e.g., in CombatManager or action_handlers), do not call UI methods.
Instead, create DisplayEvent objects (from core/orchestration/events.py) for each piece of information that needs to be displayed.
Add these events to the CombatOutputOrchestrator's queue. Example: engine._combat_orchestrator.add_event_to_queue(my_display_event).
The orchestrator will process these events one by one, signaling the UI to display them and waiting for completion signals (visualDisplayComplete) before proceeding. This allows for animated text, delays, and sound effects to play out in order.
Data Models:
Use Python's @dataclass for simple data structures (e.g., PlayerState, NPCMemory, CommandResult). This is the established pattern for holding structured data.
For more complex world data used in the world_configurator, refer to the models in world_configurator/models/base_models.py (e.g., Culture, Location, Origin).
IV. GUI Development (PySide6)
Communication via Signals & Slots:
Communication between different UI components (e.g., InventoryPanel and MainWindow) MUST be done using Qt's signal and slot mechanism.
Avoid direct method calls between components (e.g., self.inventory_panel.update()). Instead, the InventoryPanel should connect to a signal (like stats_changed or a new inventory_updated signal) and update itself in its own slot.
UI Updates:
The UI should update itself by reacting to signals from the core.
Connect UI components to signals from StatsManager (stats_changed), GameEngine (output_generated, orchestrated_event_to_ui), and the CombatOutputOrchestrator.
The MainWindow class is the central hub for connecting core signals to UI component slots.
User Settings:
User-configurable settings (like window size, colors, fonts) are managed using PySide6.QtCore.QSettings. Refer to gui/dialogs/settings/settings_dialog.py for the implementation pattern.
V. Configuration & Data Handling
Accessing Config:
Inside the core or gui modules, NEVER open .json files from the config/ directory directly.
Always use from core.base.config import get_config and then config.get("path.to.value").
The GameConfig class handles loading, caching, and providing access to all configuration data.
JSON Structure:
Be aware of the structure of the JSON files. For example, classes.json has a top-level "classes": {} object that contains the actual class definitions. The GameConfig loader handles this. When adding new config files, follow this pattern if appropriate.
VI. LLM & Agent Interaction
Agent Manager: The AgentManager (core/agents/agent_manager.py) is the primary interface for high-level interaction with the LLM.
Structured Output: LLM agents (especially CombatNarratorAgent) are designed to return structured JSON (AgentOutput TypedDict). When modifying these agents, ensure they strictly adhere to their specified JSON output format. This is critical for the game engine to parse their responses into actions.
Agent Configuration: Each agent's settings (provider, model, temperature) are defined in a corresponding JSON file in config/llm/agents/. Do not hardcode these values.
VII. Logging & Error Handling
Getting a Logger:
Obtain a logger instance at the top of each file using the project's utility:
code
Python
from core.utils.logging_config import get_logger
logger = get_logger("MODULE_NAME") # e.g., "COMBAT" or "INVENTORY"
Log Levels:
logger.debug(): For detailed diagnostic information.
logger.info(): For general operational messages (e.g., "Combat started," "Settings saved").
logger.warning(): For non-critical issues that should be noted (e.g., "Config file not found, using defaults").
logger.error(): For errors that prevent a specific function from completing but don't crash the app.
logger.exception(): Use inside an except block to log an error with a full stack trace.
Robustness:
Wrap all file I/O and external API calls (LLM requests) in try...except blocks to handle potential failures gracefully.
VIII. Code Style & Quality
PEP 8: Adhere to the PEP 8 style guide for Python code.
Type Hinting: All new functions and methods MUST include type hints for arguments and return values. Use the typing module.
Docstrings: All new classes and public methods MUST have clear, concise docstrings explaining their purpose, arguments, and return values.
***IMPORTANT: the project is on WINDOWS 11 environment***
folders to be ignored:
backup, .pytest_cache, .vscode, __pycache__, tests, web, images, log_viewer_tool, world_configurator.egg-info

never commit/push without USER's EXPLICIT COMFIRMATION
NEVER ASSUME RESOLUTION - always double check with the user while providing a clear instruction how to test proposed solution

important directories:
project root: D:\coding\RPG project\latest version
directory with all JSON config files: \config (many subfolders)
dir with core logic: \core
dir with GUI files: gui
dir  with web_configurator tool: \world_configurator
saves: \saves
logs: \logs
tests designed for LLM in headless mode in CLI -> \tools\headless_cli
