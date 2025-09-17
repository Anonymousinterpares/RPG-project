--- START OF FILE checklist.md ---

Okay, here's a comprehensive checklist for recreating and expanding the RPG project, based on the detailed functional breakdown and design principles we've established. This checklist is designed to guide the development process, ensuring all core features and requirements are addressed.

**Project Creation Checklist**

This checklist is organized by major project areas and includes sub-steps for each. It assumes a phased approach, starting with the core engine and gradually adding more complex features.

**Priority Fixes**

*   [x] **0. Immediate Fixes:**
    *   [x] 0.1 Implement on-demand game data retrieval for LLM agents:
        *   [x] 0.1.1 Create command framework for LLM to request specific game data (inventory, stats, quests, etc.)
        *   [x] 0.1.2 Implement two-phase response generation (analysis phase to identify needed data, final response with retrieved data)
        *   [x] 0.1.3 Add `{GET_INVENTORY}`, `{GET_STATS}`, `{GET_QUESTS}`, and `{GET_LOCATION_INFO}` commands
        *   [x] 0.1.4 Modify `NarratorAgent` prompt to include instructions on when/how to use data retrieval commands
        *   [x] 0.1.5 Update `AgentManager` to support the two-phase processing flow
        *   [x] 0.1.6 Fix inventory checking issue where narrator makes up items instead of checking actual inventory

**Phase 1: Core Engine and Infrastructure**

*   [x] **1. Project Setup:**
    *   [x] 1.1 Create project directory structure (including `core`, `gui`, `config`, `sound`, `tests`, `images`, `logs`, `saves`).
    *   [x] 1.2 Initialize version control (e.g., Git).
    *   [x] 1.3 Set up a virtual environment.
    *   [x] 1.4 Install required libraries (PySide6, `vlc`, `openai`, `anthropic`, `google-generativeai`, `requests`, `markdown`, etc.).
    *   [x] 1.5 Create basic `main.py` and `run_gui.py` entry points.
    *   [x] 1.6 Set up initial logging configuration (`core/utils/logging_config.py`).
    *   [x] 1.7 Create `core/utils/json_utils.py` with `EnhancedJSONEncoder`.

*   [x] **2. Core Classes (No LLM, No GUI):**
    *   [x] 2.1 Implement `core/base/config.py` (`GameConfig` class) to load JSON configurations.
    *   [x] 2.2 Implement `core/base/state.py` (`StateManager`, `GameState`, `PlayerState`, `WorldState` dataclasses).
    *   [x] 2.3 Implement `core/base/commands.py` (`CommandProcessor`, `CommandResult` dataclass) – *without* any command handlers yet.  Just the framework.
    *   [x] 2.4 Implement `core/base/game_loop.py` (`GameLoop`, `GameSpeed`, `GameTime`) – focus on basic tick processing and time advancement.
    *   [x] 2.5 Implement basic `core/base/engine.py` (`GameEngine`) – for now, just initialization and a placeholder `process_command`.
    *   [x] 2.6 Implement `core/utils/dotdict.py` (`DotDict` class).
    *   [x] 2.7 Implement `core/utils/time_utils.py` (time conversion functions).
    *   [x] 2.8 Implement basic save/load in `core/utils/save_manager.py` (`SaveManager` class).

*   [x] **3. Basic Command Handlers:**
    *   [x] 3.1 Implement basic command handlers in `core/base/commands.py`:
        *   `help`
        *   `quit`
        *   `save` (without memory context)
        *   `load` (without memory context)
        *   `list_saves`

*   [x] **4. Initial Testing (CLI):**
    *   [x] 4.1 Create a simple command-line interface in `main.py` (or a separate test script) to:
        *   Start a new game (basic character creation: name only).
        *   Process basic commands (save, load, quit, help).
        *   Test save/load functionality.
        *   Verify that the game loop runs and time advances.

**Phase 2: Inventory and Items**

*   [x] **5. Item System:**
    *   [x] 5.1 Implement `core/inventory/item.py` (`Item`, `ItemType`, `ItemRarity`, `EquipmentSlot`, `ItemStat` dataclasses/enums).
    *   [x] 5.2 Implement `core/inventory/item_manager.py` (`InventoryManager` class) with:
        *   `add_item`, `remove_item`
        *   `equip_item`, `unequip_item`
        *   `get_current_weight`, `get_weight_limit`
        *   `add_currency`, `remove_currency`
        *   `to_dict`, `from_dict` (for serialization)
        *    `get_item()`
        *   Initial item database loading.
    *   [x] 5.3 Create basic item JSON files in `config/items/`.
    *   [x] 5.4 Implement `core/inventory/item_factory.py` (`ItemFactory` class) with:
        *   `_load_templates()`:  Loads item templates from JSON.
        *   `create_item_from_spec()`:  Creates item instances.
        *    `_scan_icon_paths()`: Scans for available item icons.
    *   [x] 5.5 Implement basic commands in `core/base/commands.py`:
        *   `inventory` (to list items)
    *   [x] 5.6 Test item creation, addition, removal, and inventory display (CLI).

**Phase 3: Web UI**

*   [x] **6. Backend API:**
    *   [x] 6.1 Set up web server framework (FastAPI).
        *   Create `web/server.py` for API endpoints.
        *   Implement authentication/session management.
        *   Configure CORS and security settings.
    *   [x] 6.2 Implement API endpoints for game actions:
        *   `/api/command` - Process game commands.
        *   `/api/new_game` - Start new game with character creation.
        *   `/api/save_game` - Save the current game.
        *   `/api/load_game` - Load a saved game.
        *   `/api/list_saves` - List available save files.
    *   [x] 6.3 Implement WebSocket for real-time updates:
        *   Game state changes.
        *   Time advancement notifications.
        *   Game events and messages.
    *   [x] 6.4 Create serialization layer for API responses.
    *   [x] 6.5 Implement logging middleware for API requests.
    *   [x] 6.6 Create JSON schema definitions for API contracts.

*   [x] **7. Frontend Web UI:**
    *   [x] 7.1 Set up web frontend structure:
        *   Create base HTML/CSS templates.
        *   Set up JavaScript client-side modules.
        *   Define component structure.
    *   [x] 7.2 Create core UI components:
        *   Game output/message display area.
        *   Command input field with history.
        *   Navigation and action buttons.
        *   Dialog modal system.
    *   [x] 7.3 Implement API client service for backend communication.
    *   [x] 7.4 Create WebSocket client for real-time updates.
    *   [x] 7.5 Design responsive layout for different screen sizes.
    *   [x] 7.6 Implement game dialogs as modal components:
        *   New Game dialog (character creation).
        *   Save Game dialog.
        *   Load Game dialog with save browser.
        *   Settings dialog.
    *   [x] 7.7 Fix server.py path handling for client directory.
    *   [x] 7.8 Add compatibility for JSON utilities between server and client.

**Phase 4: LLM Integration and Agents**

*   [x] **8. LLM Setup:**
    *   [x] 8.1 Create `core/llm/provider_manager.py` (`ProviderManager` class) to manage LLM providers.
    *   [x] 8.2 Implement `core/llm/llm_manager.py` (`LLMManager` class) to handle LLM interactions.
    *   [x] 8.3 Create LLM configuration files (`config/llm/base_config.json`, `config/llm/providers.json`, `config/llm/agents/`).
    *   [x] 8.4 Implement `get_completion()` in `LLMManager` to send prompts and receive responses.
    *   [x] 8.5 Implement `verify_client()` in `LLMManager` to test provider connections.
    *   [x] 8.6 Implement `run_llm_diagnostics()` in `LLMManager`.
    *   [x] 8.7 Fix Google Gemini 2.0 API integration.

*   [x] **9. Agent Implementation:**
    *   [x] 9.1 Implement `core/agents/base_agent.py` (`BaseAgent`, `AgentContext`, `AgentResponse`).
    *   [x] 9.2 Implement `core/agents/narrator.py` (`NarratorAgent`).
        *   [x] Focus on basic narrative generation (no item/quest commands yet).
        *   [x] Implement `_generate_system_prompt()`.
        *   [x] Implement `process()`.
    *   [x] 9.3 Implement `core/agents/rule_checker.py` (`RuleCheckerAgent`).
        *   [x] Focus on basic rule validation (e.g., preventing invalid commands).
        *   [x] Implement `_validate_action()`.
    *   [x] 9.4 Implement `core/agents/context_evaluator.py` (`ContextEvaluatorAgent`).
        *   [x] Focus on basic context analysis and importance scoring.
        *   [x] Implement `_evaluate_context()`.
    *   [x] 9.5 Implement `core/agents/agent_manager.py` to coordinate between agents.

*   [x] **10. Connect LLM to GUI:**
    *   [x] 10.1 Modify `GameEngine` to use the `AgentManager` to process player input and generate output.
    *   [x] 10.2 Display LLM-generated text in the GUI's output area.
    *   [x] 10.3 Add compatibility layers for web server integration.
    *   [x] 10.4 Add settings management for LLM and agent configuration.
    *   [x] 10.5 Implement CLI utility for agent settings management.
    *   [x] 10.6 Add `/llm` command for toggling and checking LLM status.
    *   [x] 10.7 Improve error handling and debugging in LLM integration.
    *   [x] 10.8 Fix command routing for natural language vs. system commands.

**Phase 5: Stats and Rules System**

*   [x] **11. Core Stats System:** (Implemented)
    *   [x] 11.1 Create `core/stats/stats_base.py`:
        *   [x] Define `StatType` enum for primary stats (STR, DEX, CON, INT, WIS, CHA)
        *   [x] Define `DerivedStatType` enum for secondary stats (HP, MP, Stamina, Initiative, etc.)
        *   [x] Implement `Stat` dataclass with name, value, base_value, and modifiers
    *   [x] 11.2 Create `core/stats/derived_stats.py`:
        *   [x] Implement calculation functions for each derived stat
        *   [x] Create formulas that use primary stats as input
    *   [x] 11.3 Implement `core/stats/stats_manager.py`:
        *   [x] Methods to get/set stat values
        *   [x] Calculate modifiers from stat values
        *   [x] Track and apply temporary and permanent changes
        *   [x] Implement stat validation rules
        *   [x] Implement random stat generation methods
        *   [x] Implement skill check functionality
    *   [x] 11.4 Implement stats serialization/deserialization for save/load
    *   [x] 11.5 Create `config/character/stats_config.json`:
        *   [x] Define base stat values and ranges
        *   [x] Configure formulas for derived stats
        *   [x] Define progression curves for stat advancement
    *   [x] 11.6 Update `PlayerState` in state.py to include character stats
    *   [x] 11.7 Add new `/stats` command to display character stats
    *   [x] 11.8 Update GUI to display character stats in `character_sheet.py`
    *   [x] 11.9 Add tooltips and detailed info dialog for right-clicking stats

*   [x] **12. Modifier System:** (Implemented)
    *   [x] 12.1 Create `core/stats/modifier.py`:
        *   [x] Define `ModifierType` enum (permanent, semi-permanent, temporary)
        *   [x] Define `ModifierSource` enum (racial, class, equipment, spell, etc.)
        *   [x] Implement `StatModifier` class with source, value, duration, etc.
        *   [x] Implement stacking rules for modifiers
    *   [x] 12.2 Implement `core/stats/modifier_manager.py`:
        *   [x] Methods to add/remove modifiers
        *   [x] Track active modifiers and their durations
        *   [x] Apply modifiers to base stats
        *   [x] Handle modifier expiration and updates
    *   [x] 12.3 Implement `core/stats/combat_effects.py`:
        *   [x] Define `StatusEffectType` enum for effect types
        *   [x] Implement `StatusEffect` class for combat effects
        *   [x] Implement `StatusEffectManager` for tracking effects
        *   [x] Create factory methods for common effects
    *   [x] 12.4 Update `GameLoop` to process time-based modifiers
    *   [x] 12.5 Add event system for modifier application/expiration
    *   [x] 12.6 Create `config/character/modifiers_config.json`:
        *   [x] Define standard modifier templates
        *   [x] Configure stacking rules and priorities
    *   [x] 12.7 Update GUI to show active modifiers
    *   [x] 12.8 Create special command formats for LLM to apply modifiers:
        *   [x] `{STAT_MODIFY:character:stat:value:duration:reason}`

*   [x] **13. Skill Check System:** (Implemented)
    *   [x] 13.1 Create `core/stats/skill_check.py`:
        *   [x] Implement `perform_check()` function for stat-based checks
        *   [x] Implement `calculate_success_chance()` for probability calculations
        *   [x] Implement `SkillCheckResult` class with detailed outcome information
        *   [x] Add support for advantage/disadvantage mechanics
    *   [x] 13.2 Add skill check methods to `StatsManager`:
        *   [x] `perform_skill_check()` for executing checks
        *   [x] `calculate_check_probability()` for getting success odds
    *   [x] 13.3 Implement critical success/failure mechanics
    *   [x] 13.4 Add logging for skill check results
    *   [x] 13.5 Create GUI components for displaying check results
    *   [x] 13.6 Update LLM prompts to make effective use of the skill check system

*   [~] **14. Stat Allocation System:** (Partially Implemented)
    *   [x] 14.1 Create `core/stats/stat_allocation.py`:
        *   [x] Implement `StatPointAllocator` class for managing stat points
        *   [x] Implement point cost system (higher stats cost more points)
        *   [x] Add methods for increasing/decreasing stats
        *   [x] Add automatic allocation based on priorities
    *   [x] 14.2 Create configuration files for race and class modifiers:
        *   [x] 14.2.1 Create `config/character/races.json` with racial stat bonuses and traits
        *   [x] 14.2.2 Create `config/character/classes.json` with class stat bonuses and recommended stat distributions
        *   [x] 14.2.3 Define standard modifiers for each race (e.g., Elves: +2 DEX, +1 INT, -1 CON)
        *   [x] 14.2.4 Define standard modifiers for each class (e.g., Warrior: +1 STR, +1 CON)
        *   [x] 14.2.5 Include minimum stat requirements for each class
    *   [x] 14.3 Create Stat Allocation Widget component:
        *   [x] 14.3.1 Create `gui/components/stat_allocation_widget.py` with UI for allocating points
        *   [x] 14.3.2 Implement stat increase/decrease buttons with visual feedback
        *   [x] 14.3.3 Display point costs and remaining points
        *   [x] 14.3.4 Show current modifiers from each stat (e.g., STR 14 → +2)
        *   [x] 14.3.5 Implement visual indicators for race/class bonuses on each stat
        *   [x] 14.3.6 Add hover tooltips showing detailed stat information
        *   [x] 14.3.7 Display the source of each modifier (Race, Class, Base) with different colors
        *   [x] 14.3.8 Include warning indicators when stats are below class minimums
    *   [x] 14.4 Integrate Stat Allocation into Character Creation:
        *   [x] 14.4.1 Modify `new_game_dialog.py` to include the stat allocation widget
        *   [x] 14.4.2 Update race/class selections to dynamically apply bonuses to stats
        *   [x] 14.4.3 Add preset buttons for quick stat allocation based on class archetypes
        *   [x] 14.4.4 Implement validation to ensure minimum requirements are met before character creation
        *   [x] 14.4.5 Add info panel showing race/class modifier details and recommendations
        *   [x] 14.4.6 Create visual comparison between current allocation and class recommendations
    *   [ ] 14.5 Create Level-Up Stat Allocation Dialog:
        *   [ ] 14.5.1 Create `gui/dialogs/level_up_dialog.py` for handling stat points during level up
        *   [ ] 14.5.2 Display current stats and available improvement points
        *   [ ] 14.5.3 Show increased costs for higher stat values
        *   [ ] 14.5.4 Implement confirmation before applying changes
        *   [ ] 14.5.5 Display projected derived stat changes based on allocation
    *   [x] 14.6 Implement Character Archetype Presets:
        *   [x] 14.6.1 Define balanced presets for each class (e.g., Balanced Warrior, Offensive Warrior, Defensive Warrior)
        *   [x] 14.6.2 Create quick-allocation buttons for each preset
        *   [x] 14.6.3 Add description tooltips explaining the focus of each preset

*   [~] **15. Combat System Framework & Testing:** (Partially Implemented, Testing added)
    *   [x] 15.1 Create `core/combat/combat_manager.py`:
        *   [x] Track combat state and participants
        *   [x] Manage turn order and initiative
        *   [x] Coordinate attack and defense calculations
    *   [x] 15.2 Implement `core/combat/combat_entity.py`:
        *   [x] Define entity types and properties
        *   [x] Track health, mana, and status effects
        *   [x] Handle damage and healing
    *   [x] 15.3 Implement `core/combat/combat_action.py`:
        *   [x] Define different combat action types
        *   [x] Create specialized actions (attack, defend, spell, etc.)
    *   [x] 15.4 Add combat damage calculation:
        *   [x] Implement damage types and resistances
        *   [x] Calculate damage with modifiers
        *   [x] Handle special damage effects
    *   [x] 15.5 Implement combat effects:
        *   [x] Status effects during combat (stunned, poisoned, etc.)
        *   [x] Special combat actions and maneuvers
    *   [x] 15.6 Create simple combat commands:
        *   [x] `attack [target] [with weapon]`
        *   [x] `defend`
        *   [x] `flee`
    *   [x] 15.7 Configure combat settings:
        *   [x] Define combat rules and constants in `config/combat/combat_config.json`
        *   [x] Configure turn mechanics and timing
    *   [ ] **15.8 Implement Developer Command Framework:** (New)
        *   [ ] Modify `core/base/commands.py` (`CommandProcessor.process_command`) to handle a distinct dev command prefix (e.g., `//`).
        *   [ ] Add `self._dev_handlers` dictionary and `register_dev_command()` method to `CommandProcessor`.
    *   [ ] **15.9 Implement Core Combat Dev Commands:** (New)
        *   [ ] Implement `//start_combat <enemy_template> [level] [count]` handler (needs `NPCSystem`, `CombatManager`).
        *   [ ] Implement `//combat_status` handler (needs `CombatManager`).
        *   [ ] Implement `//set_hp <entity_id> <value>` handler (needs `CombatManager`).
        *   [ ] Implement basic `//combat_action <performer_id> attack <target_id>` handler (needs `CombatManager`, `CombatAction`).
        *   [ ] *Consider adding handlers for applying status effects, checking specific stats during combat later.*
    *   [ ] **15.10 Update GUI for Basic Combat Display:** (Moved Up)
        *   [ ] Create a simple combat status area/log in the GUI (`gui/components/combat_display.py`?).
        *   [ ] Display participant list with HP.
        *   [ ] Show current turn indicator.
        *   [ ] Display combat log messages from `CombatManager`.
    *   [ ] **15.11 Implement Scenario-Based Testing:** (New)
        *   [ ] Create "Combat Arena" origin in `config/world/scenarios/origins.json` with `on_start_actions`.
        *   [ ] Implement execution of `on_start_actions` in `core/base/engine.py` (`start_new_game`).
        *   [ ] Ensure `CombatManager` state is correctly saved/loaded via `StateManager` and `SaveManager`.
    *   [ ] **15.12 Perform Comprehensive Combat Testing:** (New)
        *   [ ] Use `//start_combat` to test various enemies and group sizes.
        *   [ ] Use `//combat_action`, `//set_hp` to test specific mechanics (damage, status effects, low HP AI).
        *   [ ] Use `//combat_status` to verify internal state during tests.
        *   [ ] Use the "Combat Arena" origin for standard encounter flow testing.
        *   [ ] Use save/load workflow to test specific complex combat scenarios.
        *   [ ] Test combat initiation and description via narrative triggering (LLM).
    *   [ ] **15.13 Integrate with Skill Check System:** (Previously 15.9)
        *   [ ] Use `StatsManager.perform_skill_check()` for attack rolls, saving throws, flee attempts, etc., within `CombatManager`.

*   [ ] **16. Character Progression and Traits:**
    *   [ ] 16.1 Create `core/character/progression.py`:
        *   [ ] 16.1.1 Implement experience points tracking and calculation
        *   [ ] 16.1.2 Define level-up thresholds with increasing requirements
        *   [ ] 16.1.3 Create methods for awarding XP from various actions
        *   [ ] 16.1.4 Implement level-up event triggers and notifications
        *   [ ] 16.1.5 Add derived stat recalculation on level-up
    *   [ ] 16.2 Implement `core/character/race.py`:
        *   [ ] 16.2.1 Create `Race` class for managing racial properties
        *   [ ] 16.2.2 Implement methods to apply racial stat modifiers
        *   [ ] 16.2.3 Define racial abilities and traits system
        *   [ ] 16.2.4 Add racial background and description generation
        *   [ ] 16.2.5 Implement racial appearance traits for character description
    *   [ ] 16.3 Implement `core/character/class.py`:
        *   [ ] 16.3.1 Create `CharacterClass` for class properties
        *   [ ] 16.3.2 Implement methods to apply class stat modifiers
        *   [ ] 16.3.3 Define class abilities and progression system
        *   [ ] 16.3.4 Create class-based equipment proficiency system
        *   [ ] 16.3.5 Implement class specialization options at higher levels
    *   [ ] 16.4 Character Traits System:
        *   [ ] 16.4.1 Create `core/character/traits.py` for character traits
        *   [ ] 16.4.2 Implement trait effects on stats and gameplay
        *   [ ] 16.4.3 Add trait selection options during character creation
        *   [ ] 16.4.4 Create system for acquiring traits through gameplay
        *   [ ] 16.4.5 Implement trait compatibility rules (some traits conflict)
    *   [ ] 16.5 Level Up System Integration:
        *   [ ] 16.5.1 Add new `/level` command to display level information
        *   [ ] 16.5.2 Create level-up notification and process
        *   [ ] 16.5.3 Integrate with the stat allocation system for level-up points
        *   [ ] 16.5.4 Add class-based ability selection on level-up
        *   [ ] 16.5.5 Implement derived stat increases based on level
    *   [ ] 16.6 Experience System:
        *   [ ] 16.6.1 Create XP reward system for combat, quests, exploration
        *   [ ] 16.6.2 Implement XP scaling based on challenge difficulty
        *   [ ] 16.6.3 Add LLM integration for narrative-based XP rewards
        *   [ ] 16.6.4 Create XP visualization and progress tracking
        *   [ ] 16.6.5 Implement milestone-based XP alternatives

**Phase 6: LLM Integration for Character System**

*   [x] **17. NPC Generation System:**
    *   [x] 17.1 Implement `core/character/npc_base.py`:
        *   [x] Define core data structures (`NPC`, `NPCType`, `NPCRelationship`, etc.)
        *   [x] Implement `NPCMemory` for tracking interactions
        *   [x] Add serialization/deserialization methods
    *   [x] 17.2 Implement `core/character/npc_manager.py`:
        *   [x] Create NPC tracking and persistence system
        *   [x] Implement methods for retrieving NPCs by ID, name, location
        *   [x] Add methods for updating NPC information
    *   [x] 17.3 Implement `core/character/npc_generator.py`:
        *   [x] Create methods for generating NPCs based on role and context
        *   [x] Implement template-based NPC creation
        *   [x] Add methods for minimal vs detailed NPC generation
        *   [x] Add support for blank template for unexpected NPC types
        *   [x] Add support for boss-type NPCs with enhanced stats
    *   [x] 17.4 Implement `core/character/npc_creator.py`:
        *   [x] Create specialized NPC creation methods (merchants, enemies, etc.)
        *   [x] Implement NPC enhancement for new interaction types
        *   [x] Add support for NPC subtypes for more specific templates
    *   [x] 17.5 Implement `core/character/npc_persistence.py`:
        *   [x] Create methods for saving/loading NPCs
        *   [x] Implement persistence for important NPCs
        *   [x] Add cleanup for unused NPCs
    *   [x] 17.6 Implement `core/character/npc_memory.py`:
        *   [x] Create system for tracking NPC interactions
        *   [x] Add importance scoring for memories
        *   [x] Implement context generation for LLM
    *   [x] 17.7 Implement `core/character/npc_system.py`:
        *   [x] Create unified interface for all NPC subsystems
        *   [x] Implement just-in-time access pattern
        *   [x] Add support for NPC subtypes in all relevant methods
    *   [x] 17.8 Create `config/character/npc_templates.json`:
        *   [x] Define templates for common NPC types
        *   [x] Add name pools for different NPC categories
        *   [x] Include blank template for unexpected NPC types
        *   [x] Add boss-type templates with enhanced stats

*   [~] **18. Character Creation Enhancement:**
    *   [x] 18.1 Update character creation UI:
        *   [x] Add race and class selection with descriptions
        *   [x] Implement stat point allocation interface
        *   [x] Add starting scenario selection with auto-population based on race/class
        *   [~] Create character appearance customization
    *   [x] 18.2 Implement LLM-enhanced character description:
        *   [x] Add text area for basic character background
        *   [x] Create button to generate enhanced description
        *   [x] Implement description editing and finalizing
    *   [x] 18.3 Create race/class selection guidance:
        *   [x] Add tooltips and info panels for races/classes
        *   [x] Show stat bonuses and special abilities
        *   [x] Provide recommended builds for beginners
    *   [x] **18.4 Starting Scenario Integration:**
        *   [x] 18.4.1 Create a dropdown for selecting starting scenarios in character creation
        *   [x] 18.4.2 Implement filtering based on race and class compatibility
        *   [x] 18.4.3 Add automatic population of the first valid scenario for chosen race/class
        *   [x] 18.4.4 Add detailed scenario information display in character creation UI
        *   [x] 18.4.5 Include scenario context in character background generation
        *   [x] 18.4.6 Store scenario information with character data

*   [~] **19. LLM Integration for Stats and Rules:** (Partially Implemented)
    *   [x] 19.1 Update `NarratorAgent` prompt to:
        *   [x] Generate combat and action results based on stats
        *   [x] Apply appropriate modifiers through commands
        *   [x] Describe actions accounting for character abilities
    *   [x] 19.2 Update `RuleCheckerAgent` prompt to:
        *   [x] Validate actions based on character stats and abilities
        *   [x] Check for stat requirements for actions
        *   [x] Calculate success probabilities
    *   [ ] 19.3 Update `ContextEvaluatorAgent` prompt to:
        *   [ ] Track relevant stat changes and abilities
        *   [ ] Prioritize context based on character capabilities
    *   [x] 19.4 Create specialized command formats for stats:
        *   [x] `{RULE_CHECK:action:stat:difficulty:context}`
        *   [x] `{STAT_CHECK:stat:difficulty:context}`
        *   [ ] `{CONTEXT_EVAL:situation:relevant_stats:importance}`
    *   [x] 19.5 Add templates and examples for LLM to follow for stats descriptions
    *   [x] 19.6 Update command parser to handle new stat-related commands

**Phase 7: Memory and Context Systems**

*   [~] **20. Memory and Journal System:**
    *   [x] 20.1 Implement stub methods for memory/context in the state manager
    *   [ ] 20.2 Implement `core/memory/data_classes.py` (`MemoryEntry`, `MemoryState`)
    *   [ ] 20.3 Implement `core/memory/enums.py` (`MemoryType`, `ContextType`)
    *   [ ] 20.4 Implement `core/memory/memory_operations.py` (`MemoryOperations` class)
    *   [ ] 20.5 Implement `core/memory/memory_indexing.py` (`MemoryIndexing` class)
    *   [ ] 20.6 Implement `core/memory/memory_io.py` (`MemoryIO` class)
    *   [ ] 20.7 Implement `core/memory/memory_utils.py` (`MemoryUtils` class)
    *   [ ] 20.8 Implement `core/memory/context_manager.py` (`ContextManager` class)
    *   [ ] 20.9 Integrate `ContextManager` into `StateManager`
    *   [x] 20.10 Update save/load to include memory data (placeholder implementation)
    *   [ ] 20.11 Implement journal system for player-accessible information:
        *   [ ] Create `core/journal/journal_entry.py` (`JournalEntry` class)
        *   [ ] Create `core/journal/journal_manager.py` (`JournalManager` class)
        *   [ ] Implement sections for character information, quests, and personal notes
        *   [ ] Create save/load functionality for journal content
        *   [ ] Implement LLM access to journal content via special commands
    *   [ ] 20.12 Implement time-based memory importance decay
    *   [ ] 20.13 Add command for LLM to request specific journal information

*   [ ] **21. Context Utilization:**
    *   [ ] 21.1 Modify `NarratorAgent` to use the `ContextManager` to retrieve relevant memories for prompt generation.
    *   [ ] 21.2 Modify `RuleCheckerAgent` to use context for rule validation.
    *   [ ] 21.3 Modify `ContextEvaluatorAgent` to use context for its evaluations.
    *   [ ] 21.4 Integrate stats and character progression into memory system
    *   [ ] 21.5 Track important combat encounters and outcomes
    *   [ ] 21.6 Store narrative-significant stat changes and their causes
    *   [ ] 21.7 Implement NPC memory integration:
        *   [ ] Track NPC interactions and relationship changes
        *   [ ] Store key information about NPCs for future reference
        *   [ ] Add importance scoring for different NPC memories

**Phase 8: Quests and World Building**

*   [ ] **22. Quest System:**
    *   [ ] 22.1 Implement `core/quest/quest_manager.py` (`QuestManager` class).
    *   [ ] 22.2 Implement quest-related commands in `CommandProcessor`.
    *   [ ] 22.3 Create `gui/quest_widgets.py` for GUI quest display.
    *   [ ] 22.4 Integrate quest management into `NarratorAgent` (command extraction).
    *   [ ] 22.5 Create `config/world/scenarios/starting_scenarios.json`.  ?? to be checked if makes sense
    *   [ ] 22.6 Implement quest requirements based on character stats
    *   [ ] 22.7 Add stat-based outcomes and rewards for quests

*   [ ] **23. World Data:**
    *   [ ] 23.1 Create `config/world/base/cultures.json`.
    *   [ ] 23.2 Create `config/world/base/fundamental_rules.json`.
    *   [ ] 23.3 Create `config/world/base/world_history.json`.
    *   [ ] 23.4 Implement `core/utils/world_config_loader.py` (`WorldConfigLoader` class).
    *   [ ] 23.5 Update `StateManager` to load world data.
    *   [ ] 23.6 Update `NarratorAgent` to use world data in prompts.

*   [~] **24. World Configurator Tool:**
    *   [x] 24.1 **Project Setup:**
        *   [x] 24.1.1 Create `world_configurator/` directory in the project root
        *   [x] 24.1.2 Create subdirectories for the tool: `data/`, `models/`, `ui/`, `utils/`
        *   [x] 24.1.3 Set up a separate virtual environment for the configurator
        *   [x] 24.1.4 Create `main.py` entry point for the configurator application
        *   [x] 24.1.5 Set up basic logging configuration
    *   [x] 24.2 **Data Models:**
        *   [x] 24.2.1 Define base data models in `models/base_models.py`
        *   [x] 24.2.2 Implement `models/world_data.py` (cultures, history, locations, etc.)
        *   [x] 24.2.3 Implement `models/scenario_data.py` (starting scenarios, quests, etc.)
        *   [x] 24.2.4 Implement `models/character_data.py` (for NPC templates, factions, etc.)
        *   [x] 24.2.5 Create JSON schema definitions for data validation
        *   [x] 24.2.6 Implement serialization/deserialization methods for all models
    *   [x] 24.3 **Core Functions:**
        *   [x] 24.3.1 Implement `utils/file_manager.py` for reading/writing JSON files
        *   [x] 24.3.2 Create `utils/data_validator.py` for schema validation
        *   [x] 24.3.3 Implement `utils/path_manager.py` to handle file paths
        *   [x] 24.3.4 Create `utils/import_export.py` for game integration
        *   [x] 24.3.5 Implement data relationship tracking between entities
    *   [x] **24.4 GUI Implementation:** # Mark parent as complete if all sub-items are done, otherwise leave as [~]
        *   [x] 24.4.1 Create main application window with tabs for different data categories
        *   [x] 24.4.2 Implement `ui/editors/culture_editor.py` for culture creation and editing
        *   [x] 24.4.3 Implement `ui/editors/history_editor.py` for historical events management
        *   [x] 24.4.4 Implement `ui/editors/location_editor.py` for world locations
        *   [x] 24.4.5 Implement `ui/editors/scenario_editor.py` for starting scenarios and quests
        *   [x] 24.4.6 Implement `ui/editors/quest_editor.py` for quest management
        *   [x] 24.4.7 Create magic systems editor (`ui/editors/magic_systems_editor.py`) # Already checked, confirm details if needed
            *   [x] Create data models for magic systems and spells
            *   [x] Implement MagicSystemManager for managing magic systems
            *   [x] Build Magic Systems UI editor with support for adding/editing/removing magical systems
            *   [x] Add spell management with effects and properties
            *   [x] Integrate with main window and export functionality
        *   [x] 24.4.8 Implement `ui/editors/race_editor.py` for race creation and editing # NEW & CHECKED
        *   [x] 24.4.9 Implement `ui/editors/class_editor.py` for class creation and editing # NEW & CHECKED
        *   [x] 24.4.10 Implement `ui/editors/background_editor.py` for background creation and editing # NEW & CHECKED
        *   [ ] 24.4.11 Implement drag-and-drop functionality for reorganizing items # Renumbered
        *   [ ] 24.4.12 Create tree view for hierarchical data exploration # Renumbered
    *   [~] 24.5 **File Operations:**
        *   [x] 24.5.1 Implement New/Open/Save/Save As functionality
        *   [x] 24.5.2 Create file browser for project selection
        *   [x] 24.5.3 Implement automatic backup system
        *   [x] 24.5.4 Add export functionality to game config directory
        *   [x] 24.5.5 Add import functionality from game config
    *   [ ] 24.6 **Templates System:**
        *   [ ] 24.6.1 Create template library for common game elements
        *   [ ] 24.6.2 Implement template import/export functionality
        *   [ ] 24.6.3 Create template editor for customization
        *   [ ] 24.6.4 Add template preview system
    *   [~] 24.7 **Validation and Testing:**
        *   [x] 24.7.1 Implement data validation for all editors
        *   [ ] 24.7.2 Create validation report generation
        *   [x] 24.7.3 Implement relationship consistency checking
        *   [ ] 24.7.4 Add test data generation capabilities
    *   [~] 24.8 **Integration with Game Engine:**
        *   [x] 24.8.1 Modify the game's `WorldConfigLoader` to use configurator format
        *   [ ] 24.8.2 Add data directory scanning for configurator exports
        *   [ ] 24.8.3 Implement version compatibility checking
        *   [x] 24.8.4 Create game data update mechanism
        *   [x] 24.8.5 Fix World Configurator export functionality:
            *   [x] 24.8.5.1 Fix issue with export dialog not respecting selected components
            *   [x] 24.8.5.2 Fix backup creation for exported JSON files
            *   [x] 24.8.5.3 Update UI feedback to show which components were exported
    *   [ ] 24.9 **Documentation:**
        *   [ ] 24.9.1 Create user manual for the configurator
        *   [ ] 24.9.2 Document data formats and schemas
        *   [ ] 24.9.3 Add in-app help system
        *   [ ] 24.9.4 Create tutorials for common workflows

**Phase 9: Advanced Features and Refinement**

*   [x] **25. Narrative Item Management:**
    *   [x] 25.1 Implement `core/inventory/narrative_item_manager.py` (`NarrativeItemManager` class).
        *   Implement `create_combat_loot()`.
        *   Implement `parse_items_from_narrative()`.
        *   Implement `generate_item_from_llm()`.
        *   Implement helper methods for item name generation, type determination, etc.
    *   [x] 25.2 Integrate `NarrativeItemManager` with `NarratorAgent` (command handling).
    *   [x] 25.3 Update `ItemFactory` to handle LLM-generated specifications.

**Phase 10: Magic Systems**

*   [x] **33. Magic Systems Framework**
    *   [x] 33.1 **Data Models:**
        *   [x] 33.1.1 Create `MagicalSystem` dataclass with properties for name, description, origin, etc.
        *   [x] 33.1.2 Create `Spell` dataclass with properties for name, description, mana cost, effects, etc.
        *   [x] 33.1.3 Create `SpellEffect` dataclass with properties for target type, effect type, etc.
        *   [x] 33.1.4 Implement serialization/deserialization methods for magic systems and spells
    *   [x] 33.2 **Management:**
        *   [x] 33.2.1 Implement `MagicSystemManager` class for managing magic systems
        *   [x] 33.2.2 Add methods for adding/removing/editing magic systems and spells
        *   [x] 33.2.3 Implement import/export functionality for magic systems
        *   [x] 33.2.4 Add integration with the world configuration system
    *   [x] 33.3 **UI Editor:**
        *   [x] 33.3.1 Create `MagicSystemsEditor` component for editing magic systems
        *   [x] 33.3.2 Implement `MagicSystemDialog` for creating/editing magic systems
        *   [x] 33.3.3 Implement `SpellDialog` for creating/editing spells
        *   [x] 33.3.4 Create `SpellEffectDialog` for configuring spell effects
        *   [x] 33.3.5 Integrate with main window and export dialog
    *   [ ] 33.4 **Game Integration:**
        *   [ ] 33.4.1 Implement magic system loading in the game engine
        *   [ ] 33.4.2 Create magic system integration with combat system
        *   [ ] 33.4.3 Develop UI for player interaction with magic systems
        *   [ ] 33.4.4 Add narrative integration for magic spell descriptions
        *   [ ] 33.4.5 Implement spell learning and progression system

**(New Phase Added Here)**

**Phase 11: Hex Grid World Visualization** (Requires Core Engine, State Management, LLM Agents, GUI Framework)

*   [ ] **34. Hex Grid Engine (Core Logic):**
    *   [ ] 34.1 Choose or implement Hex Grid library/logic (e.g., `hexpy`, custom cube/axial coordinates).
    *   [ ] 34.2 Define `HexData` dataclass/structure in `core/world/hex_map.py`:
        *   [ ] `coordinates` (q, r) or similar
        *   [ ] `visibility` (`hidden`, `fogged`, `visible`)
        *   [ ] `terrain_type` (enum/str: `forest`, `plains`, `city_street`, `building_interior`, etc.)
        *   [ ] `location_name` (Optional string, e.g., "Whispering Woods")
        *   [ ] `poi_type` (Optional enum/str: `tavern`, `cave_entrance`, `landmark`, etc.)
        *   [ ] `poi_name` (Optional string, e.g., "The Drunken Dragon")
        *   [ ] `description_summary` (Optional brief text summary)
        *   [ ] `connections` (Optional: Explicit traversability rules if not all neighbors are accessible)
        *   [ ] `llm_full_description` (Optional reference to full description)
        *   [ ] `discovered_by_player` (boolean)
    *   [ ] 34.3 Implement `core/world/hex_map_manager.py` (`HexMapManager` class):
        *   [ ] Store map data (dictionary of `coordinates: HexData`).
        *   [ ] Methods: `get_hex(coords)`, `update_hex(coords, updates)`, `get_neighbors(coords)`.
        *   [ ] Implement visibility logic (e.g., revealing adjacent hexes on movement).
        *   [ ] Load/save hex map data (integrate with `SaveManager`).
    *   [ ] 34.4 Integrate `HexMapManager` instance into `WorldState` or `GameState`.

*   [ ] **35. LLM Integration for Hex Map:**
    *   [ ] 35.1 Define new LLM command formats (e.g., in `core/base/llm_commands.py` or similar):
        *   [ ] `{UPDATE_HEX:coords=[q,r]:updates={'terrain_type':'forest', 'poi_type':'cave', ...}}`
        *   [ ] `{REVEAL_HEX:coords=[q,r]:visibility='fogged'}`
    *   [ ] 35.2 Update `NarratorAgent` prompt (`core/agents/narrator.py`):
        *   [ ] Add instructions to output `UPDATE_HEX` commands when describing a newly entered/revealed hex.
        *   [ ] Provide context in the prompt about the current hex coordinates and known/visible neighbors (terrain, POIs).
        *   [ ] Establish conventions for LLM to use for `terrain_type`, `poi_type` values.
        *   [ ] Instruct LLM to potentially reveal adjacent hexes (`REVEAL_HEX`) based on line of sight implied in the narrative.
    *   [ ] 35.3 Update `AgentManager` or `CommandProcessor` (`core/agents/agent_manager.py`, `core/base/commands.py`):
        *   [ ] Implement parsing logic for the new hex commands from LLM output.
        *   [ ] Call the appropriate `HexMapManager` methods based on parsed commands.
    *   [ ] 35.4 Implement robust error handling for malformed or invalid hex commands from the LLM.

*   [ ] **36. Hex Grid Visualization (GUI):**
    *   [ ] 36.1 Choose rendering approach (e.g., `PySide6 QGraphicsScene`, dedicated `QWidget`, embedded `pygame`).
    *   [ ] 36.2 Create `gui/components/hex_grid_widget.py` (`HexGridWidget` class).
    *   [ ] 36.3 Implement hex drawing logic within the widget:
        *   [ ] Draw basic hex shapes based on coordinates.
        *   [ ] Color hexes according to `HexData.terrain_type`.
        *   [ ] Apply visual effects for `HexData.visibility` (e.g., full color, grayscale/fog texture, black/hidden).
        *   [ ] Render icons or text labels based on `HexData.poi_type` and `HexData.poi_name`.
        *   [ ] Clearly indicate the player's current hex location.
    *   [ ] 36.4 Implement basic interaction (optional but recommended):
        *   [ ] Panning the map view.
        *   [ ] Zooming in/out.
        *   [ ] Hovering over a hex to show basic info tooltip.
    *   [ ] 36.5 Integrate `HexGridWidget` into the main GUI layout:
        *   [ ] Add it as a new tab in the right panel (alongside Character, Inventory, Journal).
        *   [ ] Or create a dedicated map view button/window.

*   [ ] **37. Integration with Game Loop and Movement:**
    *   [ ] 37.1 Modify player movement command handling (e.g., `go north`, `move ne`) in `CommandProcessor` or `GameEngine`:
        *   [ ] Calculate target hex coordinates based on current player hex and direction.
        *   [ ] Check the status of the target hex using `HexMapManager.get_hex()`.
        *   [ ] **If hex is known & visible:** Update `PlayerState.current_coordinates`, potentially show cached info/summary, update visual player marker on `HexGridWidget`.
        *   [ ] **If hex is unknown (`hidden`) or `fogged`:**
            *   Trigger LLM `NarratorAgent` process with context about entering the new hex coordinates.
            *   (LLM generates narrative + hex commands).
            *   (System parses commands, updates `HexMapManager`).
            *   Update `PlayerState.current_coordinates`.
            *   Signal `HexGridWidget` to redraw/update based on changes in `HexMapManager`.
    *   [ ] 37.2 Ensure `HexMapManager` updates trigger redraws in `HexGridWidget` (e.g., using signals/slots if using Qt).
    *   [ ] 37.3 Update game state saving/loading to correctly handle player coordinates on the hex map.

**Phase 12: Ongoing Development & Refinement**

*   [~] **26. Enhanced Desktop GUI:** (Partially Implemented)
    *   [ ] 26.1 Create themed GUI assets in `images/gui/`:
        *   [ ] Create `main_background.png` for the application background
        *   [x] Create `scroll_background.png` for the text output area
        *   [x] Create `button_normal.png`, `button_hover.png`, and `button_pressed.png` for menu buttons
        *   [ ] Create `panel_background.png` for right panel background
        *   [ ] Create `tab_active.png` and `tab_inactive.png` for panel tabs
        *   [ ] Create `title_banner.png` for game title
        *   [x] Create `input_background.png` for command input area
        *   [ ] Create music control icons: `music_play.png`, `music_pause.png`, `music_next.png`, `music_volume.png`
    *   [~] 26.2 Implement collapsible left menu panel:
        *   [x] Create `gui/components/menu_panel.py` with collapsible animation
        *   [x] Add toggle button for expanding/collapsing
        *   [x] Style menu buttons with themed assets
    *   [~] 26.3 Redesign game output area:
        *   [x] Update `game_output.py` to use scroll background
        *   [x] Increase vertical space for text output
        *   [x] Add themed styling for text (fonts, colors)
        *   [ ] Position scroll background properly (needs fixing)
    *   [x] 26.4 Implement command input at bottom:
        *   [x] Update `command_input.py` to attach to bottom of window
        *   [x] Apply themed styling with background image
    *   [~] 26.5 Enhance right panel system:
        *   [x] Implement collapsible animation for right panel
        *   [x] Add tab-based navigation between Character, Inventory, and Journal
        *   [x] Create toggle behavior when clicking active tab header
    *   [ ] 26.6 Implement Journal tab in right panel:
        *   [x] Create `gui/components/journal_panel.py` component
        *   [ ] Add sections for character information, quests, and personal notes
        *   [ ] Implement save/load for journal content
        *   [ ] Add LLM integration for journal access
    *   [ ] 26.7 Implement time progression system:
        *   [ ] Add time display in status bar
        *   [ ] Implement different time advancement rates for different modes:
            *   [ ] Normal mode: 1 minute per command
            *   [ ] Combat mode: Seconds per action
            *   [ ] Barter mode: One-time advancement (1-5 minutes)
    *   [ ] 26.8 Add music controls:
        *   [ ] Add music control buttons to top-right corner
        *   [ ] Implement volume slider control
    *   [ ] 26.9 Implement fixed window size with resolution options in settings
    *   [ ] 26.10 Apply consistent visual styling throughout all components

*   [ ] **27. Web UI Enhancement:**
    *   [ ] 27.1 Design and implement inventory UI components:
        *   Item grid/list view with filtering.
        *   Equipment slot visualization.
        *   Item detail panel with stats and actions.
        *   Drag-and-drop item management.
    *   [ ] 27.2 Create character sheet component with stats display.
    *   [ ] 27.3 Implement quest log interface with filtering and tracking.
    *   [ ] 27.4 Create map/location visualization component.
    *   [ ] 27.5 Design and implement tabbed interface for different game panels.
    *   [ ] 27.6 Add animations and transitions for UI interactions.
    *   [ ] 27.7 Create notification system for game events.
    *   [ ] 27.8 Implement settings panel with theme options.
    *   [ ] 27.9 Create configuration editor interface for admins/developers.
    *   [ ] 27.10 Add responsive design for mobile/tablet devices.
    
*   [ ] **28. Music:**
    *   [ ] 28.1 Implement `sound/music_manager.py` (`MusicManager` class).
    *   [ ] 28.2 Create API endpoints to control music playback from the web UI.
    *   [ ] 28.3 Implement browser-based audio playback using Web Audio API.
    *   [ ] 28.4 Add music files to `sound/music/`.
    
*   [ ] **29. Advanced LLM Integration:**
    *   [ ] 29.1 Refine LLM prompts for better narrative generation.
    *   [ ] 29.2 Implement more sophisticated context management.
    *   [ ] 29.3 Improve rule checking and anti-cheat measures.
    *   [ ] 29.4 Enhance LLM prompts for stat-based gameplay
    *   [ ] 29.5 Add special command formats for advanced game mechanics
    *   [x] 29.6 Improve error handling and fallback for LLM failures
    
*   [ ] **30. Testing and Refinement:**
    *   [ ] 30.1 Write unit tests for core components.
    *   [ ] 30.2 Thoroughly test all game features.
    *   [ ] 30.3 Refactor code for clarity and efficiency.
    *   [ ] 30.4 Optimize performance (especially LLM interactions).
    *   [ ] 30.5 Test combat balance and stat interactions
    *   [ ] 30.6 User testing for gameplay flow and enjoyment

*   [x] **31. Item System Enhancements**
    *   [ ] 31.1 Implement items management from within `advanced_config_editor`.
    *   [ ] 31.2 Implement item modifiers in prompts regarding narrative, given defeated NPC.
    *   [ ] 31.3 Implement creation of items like notes and books by the LLM.
    *   [ ] 31.4 Implement proper tracking of items (context & memory management).
    *   [x] 31.5 Implement item damage and destruction.
    *   [ ] 31.6 Implement item removal by tossing them out or being stolen.
    *   [x] 31.7 Implement item discovery (expanding user's knowledge on item's statistics).
    *   [x] 31.8 Implement two-handed weapon logic.
    *   [ ] 31.9 Integrate item stats with character stats system
    *   [ ] 31.10 Implement stat requirements for item usage
    
*   [x] **32. Additional functionalities:**
    *   [ ] 32.1 Implement character creation with selection of a visual representation.
    *   [ ] 32.2 Implement a notepad for user notes.
    *   [ ] 32.3 Implement advanced combat system.
    *   [ ] 32.4 Implement anti-cheat system.
    *   [ ] 32.5 Implement a way for the user to access game settings.
    *   [ ] 32.6 Implement a way for developers to access and modify JSON files.
    *   [ ] 32.7 Consider implementing multi-language support.
    *   [x] 32.8 Implement web-based framework for the UI.
    *   [x] 32.9 Improve new game initialization with proper state cleanup.
    *   [x] 32.10 Add command to toggle and check LLM status during gameplay.
    *   [x] 32.11 Add fallback for non-LLM gameplay mode.
    *   [ ] 32.12 Implement relay system for module communication.
    *   [x] 32.13 Fix OpenRouter integration for Narrator agent.
    *   [x] 32.14 Implement threading for LLM calls to prevent UI freezing.
    *   [x] 32.15 Add welcome narration when starting a new game.
    *   [x] 32.16 Fix rule checker for welcome narration to handle None reasons.
    *   [ ] 32.17 Further investigate rule check failures for welcome narration.
    *   [ ] 32.18 Investigate OpenRouter model validation issues.
    *   [x] 32.19 Implement GUI for adding, modifying, and removing LLM models.
    *   [ ] 32.20 Add game introduction narration:
        *   [ ] Implement option in New Game dialog for tutorial level (full/basic/none)
        *   [ ] Create special introduction narration trigger after character creation
        *   [ ] Add specialized prompt templates for different introduction levels

**Detailed Implementation Notes for Stats and Rules System:**

*   **Character Statistics Structure:**
    *   Primary Stats: STR, DEX, CON, INT, WIS, CHA
    *   Secondary Stats: HP, MP, Stamina, Initiative, Carrying Capacity
    *   Combat Stats: Attack (Melee/Ranged/Magic), Defense, Magic Resistance
    *   All stats should have base values, current values, and modifier collections
    *   Stats should provide methods to calculate modifiers (e.g., +1 for each 2 points above 10)

*   **Modifier System Implementation:**
    *   Modifiers should be objects with source, affected stat(s), value, duration, stacking rules, and priority
    *   Permanent Modifiers: Racial, Class, Background, Sexual dimorphism, Level-up bonuses
    *   Semi-Permanent Modifiers: Training effects, Long-term injuries, Diseases/curses, Blessings
    *   Temporary Modifiers: Equipment, Potions/consumables, Spell effects, Environmental effects, Context-based

*   **Dice-Based Calculation System:**
    *   Implement dice rolling using XdY notation (X dice of Y sides)
    *   Base Damage Calculation: WeaponDice + Stat modifier
    *   Critical Hits: Additional dice or multipliers
    *   Defense Calculation: AC/Defense Value determines hit chance
    *   Saving Throws: Stat checks to resist effects

*   **LLM Integration for Rules and Stats:**
    *   Narrator Agent: Generate narratives based on stats, implement context-based modifiers
    *   Rule Checker Agent: Validate actions based on stats, enforce rules, calculate success/failure
    *   Context Evaluator: Track effects and modifiers, determine relevant stats for scenarios
    *   Special Command Formats:
        *   `{STAT_MODIFY:character:stat:value:duration:reason}`
        *   `{RULE_CHECK:action:stat:difficulty:context}`
        *   `{CONTEXT_EVAL:situation:relevant_stats:importance}`

*   **Combat System Framework:**
    *   Turn-Based Structure: Initiative, action selection, resolution, condition updates
    *   Attack Resolution: Attack roll vs. defense, damage calculation, effects
    *   Special Actions: Special attacks, defensive maneuvers, positioning, item usage

*   **GUI Enhancements for Stats:**
    *   Character Sheet: Visual representation of stats, tooltip info, right-click for details
    *   Combat Interface: Turn sequence, action selection, combat log, status indicators
    *   Effects Panel: Active modifiers list, duration indicators, source information

This checklist provides a detailed roadmap for implementing a comprehensive stats and rules system in the RPG project. Remember to test frequently and iterate on the design as needed. Good luck!