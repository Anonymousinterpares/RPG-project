# Plan: Natural Language Mode Transition Handling (Checklist 15.12.B2.4-B2.10)

**Goal:** Enable players *and the narrative* to initiate transitions between game modes (Combat, Narrative, Trade, Social Conflict) using natural language commands or narrative events, and ensure the system processes these requests correctly, including surprise mechanics, checks, and feedback.

---

## Phase 6: Combat System Refinements (Based on Testing Feedback)

1. [x] **Fix Surprise Status Effect Handling:**
   * [x] Fix `CombatManager.apply_surprise()` by modifying the call to `entity.add_status_effect("Surprised", duration=1)` to not use the `duration` parameter, since `CombatEntity.add_status_effect()` doesn't accept it.
   * [x] Update `CombatEntity.add_status_effect()` to properly accept and handle a duration parameter for timed status effects.
   * [x] Add appropriate logging for status effect application and removal.

2. [x] **Improve NPC Action Processing:**
   * [x] Fix rule checker validation parsing for NPC actions to properly interpret validation results.
   * [x] Modify output handling to avoid showing "Action cannot be performed" messages for NPC actions.
   * [x] Implement retry logic for invalid NPC actions by continuing processing despite validation failures.
   * [x] Add fallback mechanisms to ensure combat flow isn't interrupted by NPC action failures.

3. [ ] **Refactor Agent Manager for Player/NPC Separation:**
   * [ ] Create proper architectural design for separating player and NPC agent handling:
     * [ ] Create an abstract base class `BaseAgentManager` with common functionality.
     * [ ] Implement `PlayerAgentManager` extending the base class, focusing on player-specific handling.
     * [ ] Implement `NPCAgentManager` extending the base class, with specialized NPC handling.
     * [ ] Move existing `process_input` logic to `PlayerAgentManager`.
     * [ ] Implement proper `process_npc_intent` in `NPCAgentManager` with specialized handling.
   * [ ] Update all references to the current `AgentManager` across the codebase.
   * [ ] Ensure combat flow uses the appropriate manager for the entity type.
   * [ ] Add specialized validation handling for NPC actions (silent failures, retry logic).

4. [ ] **Combat Flow Improvements:**
   * [ ] Enhance combat turn handling to always advance after an action, regardless of success/failure.
   * [ ] Improve exception handling and fallback mechanisms throughout combat loop.
   * [ ] Add better combat state display for the player (clear turn indicators, detailed status).
   * [ ] Ensure surprise mechanics are properly executed and visualized.
   * [ ] **TODO:** Implement visual/animated initiative roll display in the GUI (potentially in a separate combat output area) as a future enhancement.

5. [ ] **Testing and Validation:**
   * [ ] Create specific test scenarios for each combat sequence and edge case.
   * [ ] Test surprise attack handling in both directions (player surprising NPC and vice versa).
   * [ ] Verify stability of combat with multiple NPCs and complex actions.
   * [ ] Ensure consistent behavior across all combat transitions.

## Phase 1: Intent Detection & Request Generation (Checklist B2.4)

1.  [x] **Define Structured Request:** Finalize the JSON structure for the new `request_mode_transition` action within the `AgentOutput`.
    *   **Proposal:**
        ```json
        {
          "action": "request_mode_transition",
          "target_mode": "NARRATIVE | COMBAT | TRADE | SOCIAL_CONFLICT", // Enum or string
          "origin_mode": "NARRATIVE | COMBAT | TRADE | SOCIAL_CONFLICT", // Current mode for context
          "reason": "Optional: Brief explanation from LLM (e.g., 'Player wants to flee', 'Ambush by goblins', 'Guard initiates attack').",
          "target_entity_id": "Optional: ID of the NPC involved (for Trade/Social).",
          "surprise": "Optional: Boolean indicating if the transition involves surprise." // Added field
        }
        ```
2.  [x] **Update Agent Prompts:** Modify the system prompts for relevant agents (`NarratorAgent`, `CombatNarratorAgent`, potentially `SocialConflictAgent`, `TradeAgent` later) to include instructions for generating `request_mode_transition` requests, including narrative-driven combat starts and the `surprise` flag.
    *   **`NarratorAgent`:**
        *   [x] Recognize player intents to initiate combat, trade, or social conflict from narrative mode.
        *   [x] Recognize narrative events (ambushes, NPC hostility) that *should* trigger combat *without* explicit player action.
        *   [x] Generate the `request_mode_transition` with `target_mode: "COMBAT"` and appropriate `reason` and `surprise: true/false` when such events occur.
    *   **`CombatNarratorAgent`:**
        *   [x] Recognize player intents to flee combat (`target_mode: "NARRATIVE"`).
    *   [ ] Provide examples of player input/narrative context and the corresponding expected JSON output. (Needs refinement/documentation)
3.  [ ] **Initial Testing:** Test agents with sample inputs and narrative scenarios (e.g., player input "I attack the guard", narrative context describing an ambush) to verify correct `request_mode_transition` generation, including the `surprise` flag.

---

## Phase 2: Transition Processing Logic (Checklist B2.5)

1.  [x] **Extend `InteractionProcessor`:** In `core/game_flow/interaction_processor.py`, modify `_execute_validated_requests` to recognize the `"action": "request_mode_transition"` and dispatch to a handler.
    *   [x] Create new private helper methods for handling specific transitions (`_handle_transition_request`, `_initiate_combat_transition`, `_attempt_flee_transition`, `_initiate_trade_transition`, `_end_trade_transition`, `_initiate_social_conflict_transition`, `_end_social_conflict_transition`).
    *   [x] Added placeholder helper methods for Trade <-> Social Conflict, Trade -> Combat, Social Conflict -> Combat.
    *   [x] Updated `_handle_transition_request` dispatcher to call new placeholder methods.
2.  [x] **Implement Transition Rules:** Code the logic within the helper methods according to the checklist rules (B2.4.3).
    *   [x] Implement probabilistic checks (dice rolls) for transitions like fleeing (using a Dexterity check).
    *   [~] Fetch relevant player/NPC stats for modifiers. (Partially done in flee check - added status effect checks).
    *   [~] Add logic for contextual difficulty adjustments. (Partially done in flee check - added enemy count/initiative adjustments).
    *   [x] **Update `_initiate_combat`:** Enhanced to handle narrative triggers, read the `surprise` flag, call `apply_surprise`, and improve error handling.
    *   [x] Implement state updates (`game_state.set_interaction_mode`, update `current_combatants`, etc.) for implemented transitions (Narrative <-> Combat, Narrative <-> Trade, Narrative <-> Social Conflict).
    *   [x] Implement logic for other transitions (TRADE <-> SOCIAL_CONFLICT, etc.). (Trade -> Combat and Social Conflict -> Combat implemented)
3.  [x] **Generate System Narratives:** Create clear system messages describing the transition attempt and outcome for implemented transitions.

---

## Phase 3: Feedback and Validation (Checklist B2.6 & RuleChecker Integration)

1.  [x] **Output Feedback:** Ensure system narratives generated in Phase 2 are correctly passed to `engine._output("system", ...)`.
2.  [ ] **GUI Updates:** Implement visual changes in the GUI based on the current interaction mode.
    *   **Approach:** Use a `QStackedWidget` in the central area of the `MainWindow` to swap between different views for each mode (e.g., Narrative View, Combat View).
    *   **Narrative View:** Contains the main game output log and command input. Preserves narrative history when switching modes.
    *   **Combat View:** Contains the `CombatDisplay` widget (for combatants' HP/MP, turn order, status effects, combat log) and command input.
    *   **Trade View:** (Future) Displays player and NPC inventories side-by-side with trade options.
    *   **Social Conflict View:** (Future) Displays social stats (Resolve), social status effects, and relevant interaction options.
    *   [ ] Identify/implement signals/callbacks from `GameEngine`/`StateManager` to notify the GUI (`MainWindow`) of mode changes.
    *   [ ] Implement slots/methods in `MainWindow` to react to mode change signals by switching the visible widget in the `QStackedWidget`.
    *   [ ] Ensure mode-specific display widgets (`CombatDisplay`, etc.) are updated with relevant state information when their view is active.
3.  [~] **RuleChecker Validation:**
    *   [~] Update `RuleCheckerAgent`'s `validate_action` to understand `request_mode_transition`. (Prompt updated to guide LLM, core code unchanged).
    *   [~] Add rules to check if a transition is contextually valid *before* attempting it. (Prompt updated to guide LLM).

---

## Phase 4: Edge Cases & Refinements (Checklist B2.7, B2.8, B2.9)

1.  [ ] **Ambiguity Handling:** Refine agent prompts and `interaction_processor` logic to handle unclear inputs gracefully.
2.  [x] **Repeated Attempts:** Implement cooldowns or increasing difficulty for failed attempts where appropriate. (Implemented cooldowns in `InteractionProcessor`)
3.  [ ] **Response Integration:** Ensure `AgentOutput` structure is consistently used and parsed across all modes and transition types. Verify UI components react correctly.
4.  [ ] **Testing:** Perform comprehensive testing using diverse NL inputs, scenarios, and edge cases. Refine prompts and logic.

---

## Phase 5: Documentation & Persistence (Checklist B2.10)

1.  [~] **Code Comments:** Add clear comments explaining the transition logic. (Added comments in implemented/modified functions).
2.  [~] **Documentation:** Update project documentation/diagrams reflecting the new flow. (This plan is part of it, but other docs may need updates).
3.  [~] **Save/Load:** Verify that `GameState.current_mode` and any related state (cooldowns, surprise status) are correctly saved and restored. (Added cooldowns and surprise state to `GameState` and `CombatManager` serialization)

---

## Mermaid Diagram (Conceptual Flow)

```mermaid
graph TD
   A[Player NL Input / Narrative Event] --> B(InputRouter / AgentManager);
   B -- Mode / Context --> C{InteractionProcessor};

   subgraph InteractionProcessor Loop
       direction LR
       C1[Build Context] --> C2(Get Agent Response);
       C2 -- AgentOutput --> C3(RuleChecker Validation);
       C3 -- Valid --> C4(Execute Requests);
       C3 -- Invalid --> C5(Output Validation Feedback);
       C4 --> C6(Output Request Results / Narrative);
   end

   subgraph Execute Requests
       direction TB
       ER1{Request Type?}
       ER1 -- Skill Check --> ER2(Process Skill Check);
       ER1 -- State Change --> ER3(Process State Change);
       ER1 -- Mode Transition --> ER4(Process Mode Transition);
   end

   subgraph Process Mode Transition
       direction TB
       MT0[Check Cooldowns] --> MT1[Get Transition Rules];
       MT1 --> MT2{Perform Check? (Dice, Stats, Surprise?)};
       MT2 -- Success --> MT3(Update GameState.current_mode);
       MT2 -- Failure --> MT4(Generate Failure Narrative);
       MT3 --> MT5(Generate Success Narrative);
       MT3 --> MT6(Signal GUI Update);
       MT4 --> MT7(Apply Cooldown);
   end

   C4 -- Contains Mode Transition --> ER1;
   ER4 -- Narrative --> C6;

   C --> E[Output to GUI / Game Log];
   C5 --> E;
   C6 --> E;

```
---

**Summary of Implemented Steps:**

*   Phase 1: Defined the structured request and updated NarratorAgent and CombatNarratorAgent prompts to generate mode transition requests.
*   Phase 2: Extended InteractionProcessor to handle mode transition requests. Implemented logic for Narrative <-> Combat, Narrative <-> Trade, Narrative <-> Social Conflict, Trade -> Combat, and Social Conflict -> Combat transitions. Refined flee check and combat initiation (including surprise call). Added placeholders for Trade <-> Social Conflict transitions. **Initial structure for a surprise round added to CombatManager.**
*   Phase 3: Ensured system narratives for implemented transitions are output. Updated RuleChecker prompt to guide validation of mode transitions.
*   Phase 4: **Implemented cooldowns for failed mode transition attempts.**
*   Phase 5: Added code comments to new/modified functions. **Added mode transition cooldowns and surprise state to GameState and CombatManager serialization.**

**Remaining Steps:**

*   Complete Phase 2: Implement detailed logic for Trade <-> Social Conflict transitions. Fully implement surprise mechanics in CombatManager (action execution during surprise round).
*   Complete Phase 3: Implement GUI updates for mode changes. Potentially add specific code logic to RuleChecker for transition validation if prompt guidance proves insufficient.
*   Complete Phase 4: Address edge cases, response integration, and comprehensive testing.
*   Complete Phase 5: Review/add more code comments, update external documentation, and verify save/load for all transition-related state.

---