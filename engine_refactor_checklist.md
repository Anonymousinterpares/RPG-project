# Engine Refactoring Checklist

This checklist outlines the steps to refactor `core/base/engine.py` into smaller, more manageable modules.

**Phase 1: Create New Modules and Move Logic**

*   [ ] **1.1 Create Directory:** Create `core/game_flow/` directory.
*   [ ] **1.2 Create `__init__.py`:** Create `core/game_flow/__init__.py`.
*   [ ] **1.3 Create `lifecycle.py`:**
    *   [ ] Create `core/game_flow/lifecycle.py`.
    *   [ ] Move `start_new_game`, `load_game`, `save_game`, `_on_tick` logic from `engine.py` to functions in `lifecycle.py`.
    *   [ ] Update function signatures to accept necessary arguments (e.g., `engine` instance, `state_manager`, `game_loop`).
    *   [ ] Add necessary imports to `lifecycle.py`.
*   [ ] **1.4 Create `command_router.py`:**
    *   [ ] Create `core/game_flow/command_router.py`.
    *   [ ] Move the main `process_command` logic from `engine.py` to a function (e.g., `route_command`) in `command_router.py`.
    *   [ ] Update function signature (e.g., `route_command(engine, command_text)`).
    *   [ ] Add necessary imports to `command_router.py`. This will likely import from `command_handlers` and `interaction_processor`.
*   [ ] **1.5 Create `command_handlers.py`:**
    *   [ ] Create `core/game_flow/command_handlers.py`.
    *   [ ] Move the logic for handling direct commands (`_process_direct_command` content: quit, save, load, help, status, llm, speed, pause, mode changes like start/end combat/trade/social) into separate functions (e.g., `handle_save_command`, `handle_start_trade_command`) within `command_handlers.py`.
    *   [ ] Update function signatures (e.g., `handle_save_command(engine, args)`).
    *   [ ] Add necessary imports to `command_handlers.py`.
*   [ ] **1.6 Create `interaction_processor.py`:**
    *   [ ] Create `core/game_flow/interaction_processor.py`.
    *   [ ] Move `_process_interactive_text`, `_process_with_llm`, `_process_unified_loop`, `_should_narrative_use_unified_loop`, `_get_npc_intent`, `_trigger_combat_narration`, `_get_participant_by_id` logic to functions in `interaction_processor.py`.
    *   [ ] Update function signatures (e.g., `process_llm_input(engine, text)`, `run_unified_loop(engine, intent, actor_id)`).
    *   [ ] Add necessary imports to `interaction_processor.py` (e.g., `ContextBuilder`, `RuleCheckerAgent`, agents, managers).

**Phase 2: Update `engine.py` Facade**

*   [ ] **2.1 Add Imports:** Add imports for the new modules (`core.game_flow.lifecycle`, `core.game_flow.command_router`, etc.) to `core/base/engine.py`.
*   [ ] **2.2 Delegate `process_command`:** Modify `GameEngine.process_command` to call the main routing function in `command_router.py`.
*   [ ] **2.3 Delegate Lifecycle Methods:** Modify `GameEngine.start_new_game`, `load_game`, `save_game`, `_on_tick` to call the corresponding functions in `lifecycle.py`.
*   [ ] **2.4 Remove Moved Code:** Delete the original implementations of the moved functions/logic from `engine.py`.
*   [ ] **2.5 Clean Up Imports:** Remove unused imports from `engine.py`.
*   [ ] **2.6 Ensure `get_game_engine()` Remains:** Verify `get_game_engine()` is still present and functional in `engine.py`.

**Phase 3: Testing and Verification**

*   [ ] **3.1 Run Basic Commands:** Test core commands (`/help`, `/save`, `/load`, `/quit`, `/status`, `/llm on/off`, `/speed`).
*   [ ] **3.2 Test Game Lifecycle:** Test starting a new game, saving, loading, auto-saving.
*   [ ] **3.3 Test Narrative Interaction:** Test basic LLM narrative generation and interaction in `NARRATIVE` mode.
*   [ ] **3.4 Test Mode Transitions:** Test commands like `/start_combat`, `/end_combat`, `/start_trade`, `/leave_trade`, `/start_social`, `/end_social`.
*   [ ] **3.5 Test Combat Mode:** Initiate combat and test basic player actions and NPC turns (if implemented sufficiently).
*   [ ] **3.6 Test Trade Mode:** Initiate trade and test basic trade interactions.
*   [ ] **3.7 Test Social Conflict Mode:** Initiate social conflict and test basic interactions.
*   [ ] **3.8 Check Dependent Files:** Briefly review the files identified in the initial search (`web/server/server.py`, `main.py`, `run_gui.py`, etc.) to ensure they still function as expected without needing explicit import changes. Pay close attention to `gui/main_window.py` as it uses several engine methods.
*   [ ] **3.9 Run Automated Tests:** If any relevant automated tests exist, run them.

**Phase 4: Refinement (Optional)**

*   [ ] **4.1 Review Circular Dependencies:** Check for potential circular dependencies introduced between the new modules and `engine.py`. Refactor if necessary (e.g., by passing specific managers instead of the full `engine` instance where possible).
*   [ ] **4.2 Improve Function Signatures:** Refine function arguments for clarity and necessity.
*   [ ] **4.3 Add Docstrings:** Ensure all new functions and modules have appropriate docstrings.
