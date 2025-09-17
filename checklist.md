--- START OF FILE filtered_checklist.md ---

**Project Creation Checklist**

**Priority Fixes**

*   [x] **0. Immediate Fixes:**

**Phase 1: Core Engine and Infrastructure**

*   [x] **1. Project Setup:**
*   [x] **2. Core Classes (No LLM, No GUI):**
*   [x] **3. Basic Command Handlers:**
*   [x] **4. Initial Testing (CLI):**

**Phase 2: Inventory and Items**

*   [x] **5. Item System:**

**Phase 3: Web UI**

*   [x] **6. Backend API:**
*   [x] **7. Frontend Web UI:**

**Phase 4: LLM Integration and Agents**

*   [x] **8. LLM Setup:**
*   [x] **9. Agent Implementation:**
*   [x] **10. Connect LLM to GUI:**

**Phase 5: Stats and Rules System**

*   [x] **11. Core Stats System:** (Implemented)
*   [x] **12. Modifier System:** (Implemented)
*   [x] **13. Skill Check System:** (Implemented)
*   [ ] **13.5 Enhanced Skill System:**
    *   [ ] 13.5.1 Create JSON-based skill definition system (config/skills.json) for externalized skills
    *   [ ] 13.5.2 Implement SkillManager to load skills from JSON and manage skill operations
    *   [ ] 13.5.3 Update skill check system to use SkillManager instead of hardcoded enum
    *   [ ] 13.5.4 Implement skill categorization (general, race-specific, class-specific)
    *   [ ] 13.5.5 Add level requirements and prerequisites for skills
    *   [ ] 13.5.6 Integrate skill acquisition with character progression (skills unlocked at level up)
    *   [ ] 13.5.7 Update agent prompts to use available skills from SkillManager
    *   [ ] 13.5.8 Implement dynamic skill generation for custom character-specific skills
    *   [ ] 13.5.9 Create persistence system for custom skills in save files
    *   [ ] 13.5.10 Improve LLM mapping of player intents to appropriate skills
*   [~] **14. Stat Allocation System:** (Partially Implemented)
    *   [ ] 14.5 Create Level-Up Stat Allocation Dialog:
        *   [ ] 14.5.1 Create `gui/dialogs/level_up_dialog.py` for handling stat points during level up
        *   [ ] 14.5.2 Display current stats and available improvement points
        *   [ ] 14.5.3 Show increased costs for higher stat values
        *   [ ] 14.5.4 Implement confirmation before applying changes
        *   [ ] 14.5.5 Display projected derived stat changes based on allocation
*   [~] **15. Combat System Framework & Testing:** (Partially Implemented, Testing added)
    *   [x] **15.8 Implement Developer Command Framework:** 
        *   [x] Modify `core/base/commands.py` (`CommandProcessor.process_command`) to handle a distinct dev command prefix (e.g., `//`).
        *   [x] Add `self._dev_handlers` dictionary and `register_dev_command()` method to `CommandProcessor`.
    *   [x] **15.9 Implement Core Combat Dev Commands:** 
        *   [x] Implement `//start_combat <enemy_template> [level] [count]` handler (needs `NPCSystem`, `CombatManager`).
        *   [x] Implement `//combat_status` handler (needs `CombatManager`).
        *   [x] Implement `//set_hp <entity_id> <value>` handler (needs `CombatManager`).
        *   [x] Implement basic `//combat_action <performer_id> attack <target_id>` handler (needs `CombatManager`, `CombatAction`).
        *   [x] *Consider adding handlers for applying status effects, checking specific stats during combat later.*
    *   [x] **15.10 Update GUI for Basic Combat Display:** 
        *   [x] Create a simple combat status area/log in the GUI (`gui/components/combat_display.py`).
        *   [x] Display participant list with HP.
        *   [x] Show current turn indicator.
        *   [x] Display combat log messages from `CombatManager`.
    *   [ ] **15.11 (Phase A) Foundational Mechanics & Context:**
        *   [ ] **A1. Solidify Stat/Modifier/Skill Check Systems:**
            *   [ ] Review/enhance `core/stats/` for comprehensive stat handling (physical, social, derived).
            *   [ ] Define core social attributes (e.g., Charisma, Willpower, Insight) and derived social stats (e.g., Resolve/Composure).
            *   [ ] Ensure robust modifier system (stacking, temporary effects, duration).
            *   [ ] Ensure flexible `StatsManager.perform_skill_check` logic (any skill/stat, target numbers, crits, advantage/disadvantage).
            *   [ ] Add/improve comments and unit tests for `core/stats/`.
        *   [x] **A2. Context Builder:** (Implemented)
            *   [x] Create `core/combat/context_builder.py` (or similar, e.g., `core/interaction/context_builder.py`).
            *   [x] Implement logic to gather comprehensive context for LLM based on game mode (participants, stats, statuses, inventory snippets, environmental interactables list, recent events).
        *   [ ] **A3. Game State Management:**
            *   [ ] Implement distinct state flags in `GameState`: `mode: 'narrative' | 'combat' | 'social_conflict' | 'trade'`.
            *   [ ] Implement basic state tracking relevant to each mode (participants, turn order, conflict status, trade partner).
        *   [ ] **A4. Conflict/Trade Initiation Logic:**
            *   [ ] Implement mechanisms for state transitions based on narrative triggers, player choices, commands.
            *   [ ] Adapt dev commands (`//start_combat`, etc.) for testing initiation only.
        *   [ ] **A5. Enhanced Initiative System:**
            *   [ ] Implement derived initiative based on stats (primarily Dexterity with other factors)
            *   [ ] Create situational initiative modifiers framework
            *   [ ] Support surprise detection and bonuses/penalties
            *   [ ] Allow initiative recalculation during combat when events impact entities' speed/reaction
            *   [ ] Update combat_manager._determine_initiative to use enhanced system
            *   [ ] Ensure initiative values are properly stored in entity stats for UI display
    *   [ ] **15.12 (Phase B) LLM Integration & Core Loop:**
        *   [x] **B1. LLM Agents:**
        *   [x] Enhance primary `NarratorAgent` (`'narrative'` mode) to interpret natural language, identify required skill checks, and output structured requests (`{'action': 'request_skill_check', ...}`).            
        *   [x] Design/Implement specialized agents (`CombatNarratorAgent`, `SocialConflictAgent`, `TradeAgent`) tailored to their modes, also outputting structured requests.
        *   [x] Integrate agents with `RuleCheckerAgent` workflow for validation.
        *   [ ] **B2. Natural Language Input Handling:**
            *   [x] **B2.1 Investigate & Plan Current Input Routing:**
                *   [x] B2.1.1 Review `core/game_flow/command_router.py` and related files for existing routing logic
                *   [x] B2.1.2 Identify gaps in mode-based input routing
                *   [x] B2.1.3 Document existing flow and proposed changes
                *   [x] B2.1.4 Design a unified input processing pipeline diagram
            *   [x] **B2.2 Implement Centralized Mode-Aware Router:**
                *   [x] B2.2.1 Create a new `InputRouter` class or enhance existing router
                *   [x] B2.2.2 Implement mode detection from `GameState`
                *   [x] B2.2.3 Implement routing logic based on current mode
                *   [x] B2.2.4 Add logging for input routing decisions
                *   [x] B2.2.5 Integrate with existing command processor for command fallback
            *   [ ] **B2.3 Enhance Natural Language Processing:**
                *   [ ] B2.3.1 Ensure all mode-specific agents receive appropriate context
                *   [ ] B2.3.2 Update agent prompt templates to focus on natural language interpretation
                *   [ ] B2.3.3 Remove any requirements for command-like syntax in agent instructions
                *   [ ] B2.3.4 Implement feedback mechanism for unrecognized commands to LLM
            *   [ ] **B2.4 Implement Mode Transition Intent Detection:**
                *   [ ] B2.4.1 Update prompts for all agents to identify mode transition intents
                *   [ ] B2.4.2 Define JSON structure for mode transition requests
                *   [ ] B2.4.3 Implement probability-based mode transition logic:
                    *   [ ] B2.4.3.1 Implement COMBAT → NARRATIVE (flee) transitions with initiative-based dice checks
                    *   [ ] B2.4.3.2 Implement NARRATIVE → TRADE transitions (context-dependent)
                    *   [ ] B2.4.3.3 Implement NARRATIVE → SOCIAL_CONFLICT transitions (context-dependent)
                    *   [ ] B2.4.3.4 Implement NARRATIVE → COMBAT transitions (context-dependent)
                    *   [ ] B2.4.3.5 Implement TRADE → NARRATIVE transitions (always allowed)
                    *   [ ] B2.4.3.6 Implement TRADE → SOCIAL_CONFLICT transitions (charisma-based)
                    *   [ ] B2.4.3.7 Implement TRADE → COMBAT transitions (extreme case, charisma-based)
                    *   [ ] B2.4.3.8 Implement SOCIAL_CONFLICT → NARRATIVE transitions (context-dependent)
                    *   [ ] B2.4.3.9 Implement SOCIAL_CONFLICT → TRADE transitions (difficult, charisma-based)
                    *   [ ] B2.4.3.10 Implement SOCIAL_CONFLICT → COMBAT transitions (extreme provocation)
                *   [ ] B2.4.4 Add state transition validation in `RuleCheckerAgent`
            *   [ ] **B2.5 Create Mode Transition Request Processor:**
                *   [ ] B2.5.1 Implement handlers for each transition type
                *   [ ] B2.5.2 Create dice throw mechanics for transition attempts
                *   [ ] B2.5.3 Add modifiers based on character stats (initiative, charisma, etc.)
                *   [ ] B2.5.4 Implement contextual difficulty adjustments
                *   [ ] B2.5.5 Create descriptive narration for transition attempts and results
            *   [ ] **B2.6 Add Mode Transition Feedback:**
                *   [ ] B2.6.1 Create feedback messages for successful transitions
                *   [ ] B2.6.2 Create feedback messages for failed transitions
                *   [ ] B2.6.3 Implement UI updates for mode changes.
                    *   **Approach:** Use a `QStackedWidget` in the central area of the `MainWindow` to swap between different views for each mode (e.g., Narrative View, Combat View).
                    *   **Narrative View:** Contains the main game output log and command input. Preserves narrative history when switching modes.
                    *   **Combat View:** Contains the `CombatDisplay` widget (for combatants' HP/MP, turn order, status effects, combat log) and command input.
                    *   **Trade View:** (Future) Displays player and NPC inventories side-by-side with trade options.
                    *   **Social Conflict View:** (Future) Displays social stats (Resolve), social status effects, and relevant interaction options.
                    *   [ ] Implement signals/callbacks from `GameEngine`/`StateManager` to notify the GUI (`MainWindow`) of mode changes.
                    *   [ ] Implement slots/methods in `MainWindow` to react to mode change signals by switching the visible widget in the `QStackedWidget`.
                    *   [ ] Ensure mode-specific display widgets (`CombatDisplay`, etc.) are updated with relevant state information when their view is active.
                *   [ ] B2.6.4 Update game log with appropriate transition narration
            *   [ ] **B2.7 Handle Special Cases and Edge Conditions:**
                *   [ ] B2.7.1 Add handling for ambiguous inputs
                *   [ ] B2.7.2 Implement fallback behavior when intent is unclear
                *   [ ] B2.7.3 Add special handling for repeated transition attempts
                *   [ ] B2.7.4 Create rules for cooldowns between transition attempts
            *   [ ] **B2.8 Implement Response Integration:**
                *   [ ] B2.8.1 Standardize agent response formats across all modes
                *   [ ] B2.8.2 Create unified processing for agent outputs
                *   [ ] B2.8.3 Ensure UI components properly display mode-specific content
                *   [ ] B2.8.4 Add graceful fallbacks for unexpected response formats
            *   [ ] **B2.9 Testing and Refinement:**
                *   [ ] B2.9.1 Create test scenarios for all mode transitions
                *   [ ] B2.9.2 Test natural language interpretation across different phrasings
                *   [ ] B2.9.3 Verify dice throw mechanics and statistics
                *   [ ] B2.9.4 Test edge cases and unusual inputs
                *   [ ] B2.9.5 Refine agent prompts based on testing results
            *   [ ] **B2.10 Documentation and Integration:**
                *   [ ] B2.10.1 Document the natural language input processing flow
                *   [ ] B2.10.2 Update player tutorial/help to explain natural interactions
                *   [ ] B2.10.3 Create examples of effective natural language commands
                *   [ ] B2.10.4 Document the mode transition mechanics for future reference
                *   [ ] B2.10.5 Integrate with SaveManager to persist mode state properly
        *   [ ] **B3. Unified Core Loop:**
            *   [ ] Implement central logic: NL Input -> Context -> LLM Agent (Narrative + Structured Request) -> RuleChecker Validation -> Skill Check Execution -> Programmatic State Update -> Outcome Narration.
        *   [~] **B4. Basic UI Integration:**
            *   [x] Ensure narrative/dice rolls display correctly in `gui/components/game_output.py`.
            *   [x] Implement/update status display panel (`gui/components/combat_display.py`?) for essential info (HP, Resolve, statuses).
            *   [ ] Add basic UI elements/feedback for 'trade' mode.
        *   [x] **B5. Combat Narrator Improvements:**
            *   [x] Fix input echo issue where player commands appear as GM narration
            *   [x] Improve prompt to ensure clear separation between action attempts and results
            *   [x] Ensure narrative references previous actions when describing results
            *   [x] Implement clear turn transition indicators in output flow
        *   [ ] **B6. Combat State Display:**
            *   [ ] Update right panel character tab to show accurate combat stats
            *   [ ] Display current HP, initiative, and active status effects
            *   [ ] Show turn order indicator in the UI
            *   [ ] Ensure stats display updates when values change during combat
    *   [~] **15.13 (Phase C) Expanding Capabilities:**    *   [ ] **15.12 (Phase B) LLM Integration & Core Loop:**
            *   [x] **B1. LLM Agents:**
            *   [x] Enhance primary `NarratorAgent` (`'narrative'` mode) to interpret natural language, identify required skill checks, and output structured requests (`{'action': 'request_skill_check', ...}`).            
            *   [x] Design/Implement specialized agents (`CombatNarratorAgent`, `SocialConflictAgent`, `TradeAgent`) tailored to their modes, also outputting structured requests.
            *   [x] Integrate agents with `RuleCheckerAgent` workflow for validation.
            *   [ ] **B2. Natural Language Input Handling:**
                *   [ ] Modify input processing to route natural language to the appropriate agent based on game `mode`.
            *   [ ] **B3. Unified Core Loop:**
                *   [ ] Implement central logic: NL Input -> Context -> LLM Agent (Narrative + Structured Request) -> RuleChecker Validation -> Skill Check Execution -> Programmatic State Update -> Outcome Narration.
            *   [~] **B4. Basic UI Integration:**
                *   [x] Ensure narrative/dice rolls display correctly in `gui/components/game_output.py`.
                *   [x] Implement/update status display panel (`gui/components/combat_display.py`?) for essential info (HP, Resolve, statuses).
                *   [ ] Add basic UI elements/feedback for 'trade' mode.
            *   [x] **B5. Combat Narrator Improvements:**
                *   [x] Fix input echo issue where player commands appear as GM narration  <-- Marked as completed
                *   [x] Improve prompt to ensure clear separation between action attempts and results
                *   [x] Ensure narrative references previous actions when describing results
                *   [x] Implement clear turn transition indicators in output flow
            *   [ ] **B6. Combat State Display:**
                *   [ ] Update right panel character tab to show accurate combat stats
                *   [ ] Display current HP, initiative, and active status effects
                *   [ ] Show turn order indicator in the UI
                *   [ ] Ensure stats display updates when values change during combat
        *   [ ] **15.12 (Phase B) LLM Integration & Core Loop:**
            *   [x] **B1. LLM Agents:**
            *   [x] Enhance primary `NarratorAgent` (`'narrative'` mode) to interpret natural language, identify required skill checks, and output structured requests (`{'action': 'request_skill_check', ...}`).            
            *   [x] Design/Implement specialized agents (`CombatNarratorAgent`, `SocialConflictAgent`, `TradeAgent`) tailored to their modes, also outputting structured requests.
            *   [x] Integrate agents with `RuleCheckerAgent` workflow for validation.
            *   [ ] **B2. Natural Language Input Handling:**
                *   [ ] Modify input processing to route natural language to the appropriate agent based on game `mode`.
            *   [ ] **B3. Unified Core Loop:**
                *   [ ] Implement central logic: NL Input -> Context -> LLM Agent (Narrative + Structured Request) -> RuleChecker Validation -> Skill Check Execution -> Programmatic State Update -> Outcome Narration.
            *   [ ] **B4. Basic UI Integration:**
                *   [ ] Ensure narrative/dice rolls display correctly in `gui/components/game_output.py`.
                *   [ ] Implement/update status display panel (`gui/components/combat_display.py`?) for essential info (HP, Resolve, statuses).
                *   [ ] Add basic UI elements/feedback for 'trade' mode.
            *   [ ] **B5. Combat Narrator Improvements:**
                *   [x] Fix input echo issue where player commands appear as GM narration  <-- Marked as completed
                *   [ ] Improve prompt to ensure clear separation between action attempts and results
                *   [ ] Ensure narrative references previous actions when describing results
                *   [ ] Implement clear turn transition indicators in output flow
            *   [ ] **B6. Combat State Display:**
                *   [ ] Update right panel character tab to show accurate combat stats
                *   [ ] Display current HP, initiative, and active status effects
                *   [ ] Show turn order indicator in the UI
                *   [ ] Ensure stats display updates when values change during combat
        *   [ ] **15.12 (Phase B) LLM Integration & Core Loop:**
            *   [x] **B1. LLM Agents:**
            *   [x] Enhance primary `NarratorAgent` (`'narrative'` mode) to interpret natural language, identify required skill checks, and output structured requests (`{'action': 'request_skill_check', ...}`).            
            *   [x] Design/Implement specialized agents (`CombatNarratorAgent`, `SocialConflictAgent`, `TradeAgent`) tailored to their modes, also outputting structured requests.
            *   [x] Integrate agents with `RuleCheckerAgent` workflow for validation.
            *   [ ] **B2. Natural Language Input Handling:**
                *   [ ] Modify input processing to route natural language to the appropriate agent based on game `mode`.
            *   [ ] **B3. Unified Core Loop:**
                *   [ ] Implement central logic: NL Input -> Context -> LLM Agent (Narrative + Structured Request) -> RuleChecker Validation -> Skill Check Execution -> Programmatic State Update -> Outcome Narration.
            *   [ ] **B4. Basic UI Integration:**
                *   [ ] Ensure narrative/dice rolls display correctly in `gui/components/game_output.py`.
                *   [ ] Implement/update status display panel (`gui/components/combat_display.py`?) for essential info (HP, Resolve, statuses).
                *   [ ] Add basic UI elements/feedback for 'trade' mode.
            *   [ ] **B5. Combat Narrator Improvements:**
                *   [x] Fix input echo issue where player commands appear as GM narration  <-- Marked as completed
                *   [ ] Improve prompt to ensure clear separation between action attempts and results
                *   [ ] Ensure narrative references previous actions when describing results
                *   [ ] Implement clear turn transition indicators in output flow
            *   [ ] **B6. Combat State Display:**
                *   [ ] Update right panel character tab to show accurate combat stats
                *   [ ] Display current HP, initiative, and active status effects
                *   [ ] Show turn order indicator in the UI
                *   [ ] Ensure stats display updates when values change during combat
    *   [ ] **15.13 (Phase C) Expanding Capabilities:**
        
        *   [ ] **C1. Environmental Interaction:**
            *   [ ] Implement initial environmental assessment at combat start (based on location data/LLM).
            *   [ ] Define environmental tags/properties and interaction rules.
            *   [ ] Ensure `RuleCheckerAgent` validates environmental interaction attempts based on context, rules, positioning.
        *   [ ] **C2. Modular/Creative Actions (LLM Driven):**
            *   [ ] Refine LLM prompts to interpret creative intents, grounding them in validated skill checks.
        *   [x] **C3. NPC AI (LLM-driven):**
            *   [x] Implement separate LLM call/prompt for NPC action determination -> outputs structured requests.
            *   [x] Ensure NPC requests are validated by `RuleCheckerAgent`.
            *   [x] Ensure validated actions/outcomes are processed programmatically and narrated impartially.
        *   [ ] **C4. Multi-Entity Combat Coordination:**
            *   [ ] Implement proper combat flow following this exact sequence:
                *   [ ] Initial combat narration prompting user for action
                *   [ ] User input
                *   [ ] Narration describing what user intends to do
                *   [ ] System message showing calculations and results
                *   [ ] Narration describing effects of user's action
                *   [ ] NPC action determination (behind the scenes)
                *   [ ] Narration describing what NPC does
                *   [ ] System message showing calculations and results of NPC action
                *   [ ] Narration describing effects of NPC action and prompt for next user action
            *   [ ] Implement initiative recalculation when relevant events occur (wounds, spells, etc.)
            *   [ ] Ensure proper ordering of turns based on initiative values, even with multiple NPCs
            *   [ ] Support situations where NPC1 acts first, then player, then NPC2, etc.
    *   [ ] **15.14 (Phase D) Social Conflict & Trade Systems:**
        *   [ ] **D1. Social Mechanics Definition:**
            *   [ ] Define social stats, skills, "social HP" (Resolve), social status effects. Integrate into character system.
        *   [ ] **D2. Social Context & State:**
            *   [ ] Adapt Context Builder and State Management for social conflict.
        *   [ ] **D3. Social Conflict Loop & LLM:**
            *   [ ] Adapt core loop and LLM prompting for social scenarios (validation, programmatic updates).
        *   [ ] **D4. Trade System Implementation:**
            *   [ ] Define trade mechanics (inventory display, value calculation, haggling checks).
            *   [ ] Adapt Context Builder, State Management, Core Loop, and LLM prompting for 'trade' mode.
    *   [ ] **15.15 (Phase E) Refinement & Advanced Integration:**
        *   [ ] **E1. Hex Grid Integration:**
            *   [ ] Enhance Context Builder and Rule Checker validation with detailed positioning/terrain data from Hex Grid system (when available).
        *   [ ] **E2. Balancing & Testing:**
            *   [ ] Continuous testing of skill checks, LLM consistency, narrative quality, rule validation, and overall challenge across all modes.
        *   [ ] **E3. Visual/Audio Polish:**
            *   [ ] Add optional visual/audio effects triggered by events.
        *   [ ] **E4. Combat Presentation Enhancement:**
            *   [ ] Update character tab in right panel to accurately display current stats with all modifiers
            *   [ ] Display initiative values and turn order in character tab during combat
            *   [ ] Improve formatting of system messages during combat
            *   [ ] Ensure turn transition indicators are properly displayed
            *   [ ] Keep NPC decision-making behind the scenes, only show results and effects
    *   [ ] **15.16 Combat Output Routing & Display Improvements:**
        *   [x] **15.16.1 Fix Combat Display Transition Timing:**
            *   [x] Add transition state tracking in GameState for detecting narrative->combat transitions
            *   [x] Add narrative buffers in GameState for collecting combat intro text 
            *   [x] Modify engine output handler to detect transition state and buffer narrative content
            *   [x] Update MainWindow._handle_game_output to properly route combat messages based on current view
            *   [x] Enhance _update_ui to process buffered combat narratives after combat view is shown
        *   [ ] **15.16.2 Combat Ending Mechanics:**
            *   [x] Implement victory detection when all enemies are defeated
            *   [x] Implement defeat detection when player HP reaches 0
            *   [x] Implement flee mechanics that use dexterity checks and set appropriate state
            *   [ ] Implement player surrender command and handling
            *   [ ] Add enemy surrender mechanic based on remaining health and other factors
            *   [ ] Create combat end narration system that summarizes outcome
            *   [ ] Implement game over state that blocks input when player is defeated
            *   [ ] Add post-combat cleanup that properly forgets combat context
            *   [ ] Create smooth transition back to narrative mode after combat ends
        *   [ ] **15.16.3 Combat Ending Prompt Creation:**
            *   [ ] Create LLM prompt templates for different combat endings (victory, defeat, fled, surrender)
            *   [ ] Implement special handling to provide combat statistics to LLM for ending narration
            *   [ ] Add post-combat inventory updates (loot acquisition) after victory
            *   [ ] Add post-combat status effect handling (injuries, etc.)
            *   [ ] Create a dedicated post-combat agent for generating narrative outcomes
            
    *   [ ] **15.19 Combat Testing Framework:**
        *   [ ] 15.19.1 Create "Combat Arena" origin in `config/world/scenarios/origins.json` with `on_start_actions`
        *   [ ] 15.19.2 Implement execution of `on_start_actions` in `core/base/engine.py` (`start_new_game`)
        *   [ ] 15.19.3 Ensure `CombatManager` state is correctly saved/loaded via `StateManager` and `SaveManager`
        *   [ ] 15.19.4 Create automated tests for combat mechanics
        *   [ ] 15.19.5 Implement stress tests for multiple combatants and complex scenarios
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
*   [~] **18. Character Creation Enhancement:**
    *   [x] 18.1 Update character creation UI:
        *   [~] Create character appearance customization
*   [~] **19. LLM Integration for Stats and Rules:** (Partially Implemented)
    *   [ ] 19.3 Update `ContextEvaluatorAgent` prompt to:
        *   [ ] Track relevant stat changes and abilities
        *   [ ] Prioritize context based on character capabilities
    *   [x] 19.4 Create specialized command formats for stats:
        *   [ ] `{CONTEXT_EVAL:situation:relevant_stats:importance}`

**Phase 7: Memory and Context Systems**

*   [~] **20. Memory and Journal System:**
    *   [ ] 20.2 Implement `core/memory/data_classes.py` (`MemoryEntry`, `MemoryState`)
    *   [ ] 20.3 Implement `core/memory/enums.py` (`MemoryType`, `ContextType`)
    *   [ ] 20.4 Implement `core/memory/memory_operations.py` (`MemoryOperations` class)
    *   [ ] 20.5 Implement `core/memory/memory_indexing.py` (`MemoryIndexing` class)
    *   [ ] 20.6 Implement `core/memory/memory_io.py` (`MemoryIO` class)
    *   [ ] 20.7 Implement `core/memory/memory_utils.py` (`MemoryUtils` class)
    *   [ ] 20.8 Implement `core/memory/context_manager.py` (`ContextManager` class)
    *   [ ] 20.9 Integrate `ContextManager` into `StateManager`
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

*   [x] **22. Quest System:**
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
    *   [x] 24.4 GUI Implementation: # Mark parent as complete if all sub-items are done, otherwise leave as [~]
        *   [ ] 24.4.11 Implement drag-and-drop functionality for reorganizing items # Renumbered
        *   [ ] 24.4.12 Create tree view for hierarchical data exploration # Renumbered
    *   [~] 24.5 **File Operations:**
    *   [ ] 24.6 **Templates System:**
        *   [ ] 24.6.1 Create template library for common game elements
        *   [ ] 24.6.2 Implement template import/export functionality
        *   [ ] 24.6.3 Create template editor for customization
        *   [ ] 24.6.4 Add template preview system
    *   [~] 24.7 **Validation and Testing:**
        *   [ ] 24.7.2 Create validation report generation
        *   [ ] 24.7.4 Add test data generation capabilities
    *   [~] 24.8 **Integration with Game Engine:**
        *   [ ] 24.8.2 Add data directory scanning for configurator exports
        *   [ ] 24.8.3 Implement version compatibility checking
    *   [ ] 24.9 **Documentation:**
        *   [ ] 24.9.1 Create user manual for the configurator
        *   [ ] 24.9.2 Document data formats and schemas
        *   [ ] 24.9.3 Add in-app help system
        *   [ ] 24.9.4 Create tutorials for common workflows

**Phase 9: Advanced Features and Refinement**

*   [x] **25. Narrative Item Management:**

**Phase 10: Magic Systems**

*   [x] **33. Magic Systems Framework**
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
            *   [ ] Trigger LLM `NarratorAgent` process with context about entering the new hex coordinates.
            *   [ ] (LLM generates narrative + hex commands).
            *   [ ] (System parses commands, updates `HexMapManager`).
            *   [ ] Update `PlayerState.current_coordinates`.
            *   [ ] Signal `HexGridWidget` to redraw/update based on changes in `HexMapManager`.
    *   [ ] 37.2 Ensure `HexMapManager` updates trigger redraws in `HexGridWidget` (e.g., using signals/slots if using Qt).
    *   [ ] 37.3 Update game state saving/loading to correctly handle player coordinates on the hex map.

**Phase 12: Ongoing Development & Refinement**

*   [~] **26. Enhanced Desktop GUI:** (Partially Implemented)
    *   [ ] 26.1 Create themed GUI assets in `images/gui/`:
        *   [ ] Create `main_background.png` for the application background
        *   [ ] Create `panel_background.png` for right panel background
        *   [ ] Create `tab_active.png` and `tab_inactive.png` for panel tabs
        *   [ ] Create `title_banner.png` for game title
        *   [ ] Create music control icons: `music_play.png`, `music_pause.png`, `music_next.png`, `music_volume.png`
    *   [~] 26.2 Implement collapsible left menu panel:
    *   [~] 26.3 Redesign game output area:
        *   [ ] Position scroll background properly (needs fixing)
    *   [~] 26.5 Enhance right panel system:
    *   [ ] 26.6 Implement Journal tab in right panel:
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
        *   [ ] Item grid/list view with filtering.
        *   [ ] Equipment slot visualization.
        *   [ ] Item detail panel with stats and actions.
        *   [ ] Drag-and-drop item management.
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
    *   [ ] 31.6 Implement item removal by tossing them out or being stolen.
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
    *   [ ] 32.12 Implement relay system for module communication.
    *   [ ] 32.17 Further investigate rule check failures for welcome narration.
    *   [ ] 32.18 Investigate OpenRouter model validation issues.
    *   [ ] 32.20 Add game introduction narration:
        *   [ ] Implement option in New Game dialog for tutorial level (full/basic/none)
        *   [ ] Create special introduction narration trigger after character creation
        *   [ ] Add specialized prompt templates for different introduction levels

--- END OF FILE filtered_checklist.md ---