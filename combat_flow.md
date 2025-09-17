Okay, Manager. Based on our previous analysis and your additional thoughts on TTS integration, here's a refined, step-by-step natural language algorithm for the desired combat flow. This incorporates the flag-based sequential execution, display completion signals, inter-step delays, placeholders for status effects and visual effects, and the two-phase bar decrease, while also preparing for future TTS integration by clearly distinguishing narrative content.

## Enhanced Combat Flow Algorithm (TTS Ready)

**Core Principles for this Algorithm:**

1.  **Output Orchestrator:** A central component (let's call it `CombatOutputOrchestrator`) manages a queue of "Display Events." Each event specifies its type (narrative, system_message, ui_update), content, target display (CombatLog, GameOutput, UIBarAnimation), and flags for `gradual_visual_display` and `tts_eligible`.
2.  **CombatManager's Role:** The `CombatManager` focuses on game logic. When it needs to communicate something to the player, it creates a Display Event object and adds it to the `CombatOutputOrchestrator`'s queue. It then *pauses* its own processing until the Orchestrator signals that the relevant Display Events have been fully processed (visually displayed and, if applicable, spoken by TTS).
3.  **Display Completion Signals:**
    *   `CombatDisplay` and `GameOutputWidget` emit `visualDisplayComplete` after their text (gradual or immediate) is fully rendered.
    *   A new `TTSManager` will emit `ttsPlaybackComplete` after it finishes speaking a segment.
4.  **Sequential Execution:** The `CombatOutputOrchestrator` processes one Display Event at a time (or a logical group). It waits for `visualDisplayComplete` and (if `tts_eligible` and TTS is active) `ttsPlaybackComplete` before starting any configured inter-step delay (`QTimer.singleShot`). After the delay, it either processes the next queued event or signals the `CombatManager` to resume its logic.
5.  **Inter-Step Delays:** These are 1-second delays (configurable) managed by the `CombatOutputOrchestrator` *after* a Display Event (or a logical block of them) is fully processed (displayed + TTSed) and *before* signaling the `CombatManager` to proceed to its next internal logic step.

---

**Phase 0: Combat Initiation (Triggered by Player Action in Narrative Mode)**

1.  **Player Input:** Player enters action (e.g., "I attack the guard!").
2.  **Engine: Input Routing:** `InputRouter` identifies combat-triggering intent.
3.  **Engine: LLM Narrative (Attempt Generation):**
    *   `NarratorAgent` generates:
        *   Narrative of the player's attempt (e.g., "You lunge at the guard...").
        *   Structured `request_mode_transition` to `COMBAT`.
    *   `GameState` flag `is_transitioning_to_combat` set to `TRUE`.
    *   `engine._output("gm", initial_narrative)` is called.
4.  **UI: Initial Narrative Handling (`MainWindow._handle_game_output`):**
    *   Detects `is_transitioning_to_combat`.
    *   Buffers `initial_narrative` into `game_state.combat_narrative_buffer`. (Does not display yet).
5.  **Engine: Mode Transition Processing (`_initiate_combat_transition`):**
    *   Enemies and player combat entities created/identified (with unique `combat_name` for each).
    *   `CombatManager` instance created and assigned to `game_state.combat_manager`.
    *   `CombatManager.prepare_for_combat()` called (stores entities, surprise flag, original intent, sets `current_step = STARTING_COMBAT`, `state = IN_PROGRESS`).
    *   `game_state.set_interaction_mode(InteractionMode.COMBAT)`.
6.  **UI: Switch to Combat View (`MainWindow._update_ui`):**
    *   Switches to `combat_view`.
    *   **Output Orchestrator - Event 0.1 (Queued by UI/Engine):**
        *   `{event_id: "init_narrative_flush", type: "narrative_block", content_list: game_state.combat_narrative_buffer, target_display: "CombatLog", gradual_visual_display: true, tts_eligible: true}`
    *   **Orchestrator -> `CombatDisplay`:** Displays buffered narrative lines. Emits `visualDisplayComplete` after all lines are shown.
    *   **Orchestrator -> `TTSManager` (if TTS active):** Speaks buffered narrative. Emits `ttsPlaybackComplete`.
    *   `game_state.combat_narrative_buffer` cleared. `game_state.is_transitioning_to_combat` set to `FALSE`.
    *   **Orchestrator (after both `visualDisplayComplete` and `ttsPlaybackComplete`, if applicable):**
        *   **1-SECOND DELAY.**
        *   Signals `CombatManager` to `process_combat_step(engine)`.

---

**Phase 1: Combat Start & Surprise Round (Driven by `CombatManager.process_combat_step`)**

*(`CombatManager.current_step` is `STARTING_COMBAT`)*

7.  **Combat Manager: `_step_starting_combat()`**
    *   **Orchestrator - Event 1.1 (Queued):** `{event_id: "combat_start_msg", type: "system_message", content: "Combat started! Player vs Enemy1, Enemy2", target_display: "CombatLog", gradual_visual_display: false, tts_eligible: false}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes Event 1.1 (display, no TTS). After `visualDisplayComplete` and 1-SECOND DELAY, signals `CombatManager` to resume.
    *   **`CombatManager`:** If surprise, `current_step = HANDLING_SURPRISE_CHECK`. Else, `current_step = ROLLING_INITIATIVE`. Pauses.
    *   **Orchestrator:** Signals `CombatManager` to resume (no new display, just proceeds).

*(If `current_step` is `HANDLING_SURPRISE_CHECK`)*

8.  **Combat Manager: `_step_handling_surprise_check()`**
    *   Applies "Surprised" status effect (via `StatsManager` and `CombatEntity` update).
        *   **Placeholder for Status Effect Visual:** Orchestrator could queue an event like `{type: "visual_effect", target_entity_id: "enemy1", effect_name: "surprised_status_icon"}`. UI handles this non-blockingly.
    *   **Orchestrator - Event 1.2 (Queued):** `{type: "system_message", content: "Round 1 (Surprise Attack!)" ...}`.
    *   If surprised targets: **Event 1.3 (Queued):** `{type: "system_message", content: "Targets Surprised: Enemy1" ...}`.
    *   Sets active entity, generates surprise `AttackAction` -> `self._pending_action`.
    *   **Orchestrator - Event 1.4 (Queued):** `{type: "narrative_attempt", content: "[LLM: Player prepares surprise attack...]" ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes 1.2, then 1.3 (if exists), then 1.4 sequentially, each with display, optional TTS, and 1-SECOND DELAY. After last one, signals `CombatManager` to resume.
    *   **`CombatManager`:** `current_step = PERFORMING_SURPRISE_ATTACK`. Pauses.
    *   **Orchestrator:** Signals `CombatManager` to resume.

*(If `current_step` is `PERFORMING_SURPRISE_ATTACK`)*

9.  **Combat Manager: `_step_performing_surprise_attack()`** (calls `perform_action` -> `_handle_attack_action`)
    *   Retrieves `_pending_action`.
    *   **Resource Cost:** Deducts Stamina/Mana (via `StatsManager`).
        *   `StatsManager` emits `stats_changed`.
        *   **Orchestrator - Event 1.5.A (Queued):** `{type: "ui_bar_update_phase1", entity_id: "attacker", bar_type: "stamina", old_value: X, new_value: Y}`.
    *   Performs attack roll.
    *   **Orchestrator - Event 1.5.B (Queued):** `{type: "system_message", content: "Attacker rolls X..." ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes 1.5.A (UI updates bar phase 1 visually). Then processes 1.5.B (display, 1-SECOND DELAY). Signals `CombatManager` to resume.
    *   **`CombatManager`:** If hits:
        *   Calculates damage. Applies to target (via `StatsManager`).
            *   `StatsManager` emits `stats_changed`.
            *   **Orchestrator - Event 1.6.A (Queued):** `{type: "ui_bar_update_phase1", entity_id: "target", bar_type: "hp", old_value: P, new_value: Q}`.
        *   **Orchestrator - Event 1.6.B (Queued):** `{type: "system_message", content: "Target takes B damage..." ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes 1.6.A. Then processes 1.6.B (display, 1-SECOND DELAY). Signals `CombatManager` to resume.
    *   **`CombatManager`:**
        *   **Orchestrator - Event 1.6.C (Queued):** `{type: "ui_bar_update_phase2", entity_id: "target", bar_type: "hp", new_value: Q}` (Finalizes HP bar visual).
    *   Stores result in `_last_action_result_detail`.
    *   `current_step = NARRATING_SURPRISE_OUTCOME`. Pauses.
    *   **Orchestrator:** Processes 1.6.C. After `visualDisplayComplete` and 1-SECOND DELAY, signals `CombatManager` to resume.

*(If `current_step` is `NARRATING_SURPRISE_OUTCOME`)*

10. **Combat Manager: `_step_narrating_surprise_outcome(engine)`**
    *   Gets LLM narrative for impact from `CombatNarratorAgent`.
    *   **Orchestrator - Event 1.7 (Queued):** `{type: "narrative_impact", content: "[LLM: Surprise blow lands...]" ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes 1.7. After `visualDisplayComplete`, (optional `ttsPlaybackComplete`), and 1-SECOND DELAY, signals `CombatManager` to resume.
    *   **`CombatManager`:** `current_step = ENDING_SURPRISE_ROUND`. Pauses.
    *   **Orchestrator:** Signals `CombatManager` to resume.

*(If `current_step` is `ENDING_SURPRISE_ROUND`)*

11. **Combat Manager: `_step_ending_surprise_round()`**
    *   **Orchestrator - Event 1.8 (Queued):** `{type: "system_message", content: "Surprise round ends." ...}`.
    *   Removes "Surprised" status.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes 1.8. After `visualDisplayComplete` and 1-SECOND DELAY, signals `CombatManager` to resume.
    *   **`CombatManager`:** `current_step = ROLLING_INITIATIVE`. Pauses.
    *   **Orchestrator:** Signals `CombatManager` to resume.

---

**Phase 2: Regular Combat Rounds**

*(If `current_step` is `ROLLING_INITIATIVE`)*

12. **Combat Manager: `_step_rolling_initiative()`**
    *   Calls `_determine_initiative()`.
        *   For each entity:
            *   **Orchestrator - Event 2.1.N (Queued):** `{type: "system_message", content: "EntityX rolls initiative..." ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes all 2.1.N events sequentially (display, no TTS, 1-SECOND DELAY after *each*). After the last one, signals `CombatManager` to resume.
    *   **`CombatManager`:** Sets turn order, `round_number = 0`, `current_turn_index = -1`. `current_step = STARTING_ROUND`. Pauses.
    *   **Orchestrator:** Signals `CombatManager` to resume.

*(If `current_step` is `STARTING_ROUND`)*

13. **Combat Manager: `_step_starting_round()`**
    *   Increments `round_number`.
    *   **Orchestrator - Event 2.2 (Queued):** `{type: "system_message", content: f"Round {self.round_number} begins!" ...}`.
    *   **Orchestrator - Event 2.3 (Queued):** `{type: "system_message", content: "Turn order: A, B, C" ...}`.
    *   Determines first active entity.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes 2.2, then 2.3 sequentially (display, no TTS, 1-SECOND DELAY after each). After last one, signals `CombatManager` to resume.
    *   **`CombatManager`:** Calls `_set_next_actor_step()`.
        *   If player: `current_step = AWAITING_PLAYER_INPUT`. CombatManager loop breaks.
        *   If NPC: `current_step = AWAITING_NPC_INTENT`. Pauses. Orchestrator signals resume.

---

**(Loop for each entity's turn)**

*(If `current_step` is `AWAITING_NPC_INTENT`)*

14. **Combat Manager: `_step_awaiting_npc_intent(engine)`**
    *   Gets NPC intent string from LLM. Stores in `_current_intent`.
    *   `current_step = PROCESSING_NPC_ACTION`. Pauses. Orchestrator signals resume.

*(If `current_step` is `PROCESSING_PLAYER_ACTION` or `PROCESSING_NPC_ACTION`)*

15. **Combat Manager: `_step_processing_player/npc_action(engine)`**
    *   Uses `_current_intent`. Calls `CombatNarratorAgent.process()`.
    *   **Orchestrator - Event T.1 (Turn.Event Attempt) (Queued):** `{type: "narrative_attempt", content: "[LLM: Entity attempts X...]" ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes T.1 (display, TTS, 1-SECOND DELAY). Signals `CombatManager` to resume.
    *   **`CombatManager`:** Converts agent request to `CombatAction` -> `_pending_action`.
        *   If conversion fails:
            *   **Orchestrator - Event T.1.Error (Queued):** `{type: "system_message", content: "Entity falters..." ...}`.
            *   `CombatManager` pauses.
            *   **Orchestrator:** Processes T.1.Error. Signals resume.
            *   **`CombatManager`:** `current_step = APPLYING_STATUS_EFFECTS`. Go to Step 18.
        *   Else (success): `current_step = RESOLVING_ACTION_MECHANICS`. Pauses. Orchestrator signals resume.
    *   **Placeholder for Action Visual:** After T.1 and its `displayComplete`, Orchestrator could trigger a non-blocking visual for the action *attempt* (e.g., character sprite animation for "swinging sword").

*(If `current_step` is `RESOLVING_ACTION_MECHANICS`)*

16. **Combat Manager: `_step_resolving_action_mechanics()`** (calls `perform_action`)
    *   Retrieves `_pending_action`.
    *   **Resource Cost:** Deducts Stamina/Mana (via `StatsManager`).
        *   `StatsManager` emits `stats_changed`.
        *   **Orchestrator - Event T.2.A (Queued):** `{type: "ui_bar_update_phase1", entity_id: "current_actor", bar_type: "stamina/mana", ...}`.
    *   **Action Resolution:**
        *   Rolls dice.
        *   **Orchestrator - Event T.2.B (Queued):** `{type: "system_message", content: "Entity rolls..." ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes T.2.A. Then T.2.B (display, 1-SECOND DELAY). Signals resume.
    *   **`CombatManager`:**
        *   **Orchestrator - Event T.2.C (Queued):** `{type: "ui_bar_update_phase2", entity_id: "current_actor", bar_type: "stamina/mana", ...}`.
    *   If hits:
        *   Calculates damage. Applies to target (via `StatsManager`).
            *   `StatsManager` emits `stats_changed`.
            *   **Orchestrator - Event T.3.A (Queued):** `{type: "ui_bar_update_phase1", entity_id: "target", bar_type: "hp", ...}`.
        *   **Orchestrator - Event T.3.B (Queued):** `{type: "system_message", content: "Target takes damage..." ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes T.2.C. Then T.3.A. Then T.3.B (display, 1-SECOND DELAY). Signals resume.
    *   **`CombatManager`:**
        *   **Orchestrator - Event T.3.C (Queued):** `{type: "ui_bar_update_phase2", entity_id: "target", bar_type: "hp", ...}`.
    *   Stores result in `_last_action_result_detail`.
    *   `current_step = NARRATING_ACTION_OUTCOME`. Pauses.
    *   **Orchestrator:** Processes T.3.C. After `visualDisplayComplete` and 1-SECOND DELAY, signals resume.
    *   **Placeholder for Impact Visual:** After T.3.B (damage system message) and its `displayComplete`, Orchestrator could trigger a non-blocking visual for the *impact* (e.g., target sprite flashing, damage numbers appearing).

*(If `current_step` is `NARRATING_ACTION_OUTCOME`)*

17. **Combat Manager: `_step_narrating_action_outcome(engine)`**
    *   Gets LLM narrative for impact.
    *   **Orchestrator - Event T.4 (Queued):** `{type: "narrative_impact", content: "[LLM: Attack connects...]" ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes T.4. After `visualDisplayComplete`, (optional `ttsPlaybackComplete`), and 1-SECOND DELAY, signals `CombatManager` to resume.
    *   **`CombatManager`:** `current_step = APPLYING_STATUS_EFFECTS`. Pauses. Orchestrator signals resume.

*(If `current_step` is `APPLYING_STATUS_EFFECTS`)*

18. **Combat Manager: `_step_applying_status_effects()`**
    *   **Status Effect Application/Update (Active Entity):**
        *   Apply DOTs/HOTs via `StatsManager`.
            *   If stat changes: `StatsManager` emits `stats_changed`.
            *   **Orchestrator - Events T.5.N (Queued):** For UI bar updates (Phase1/Phase2) and system messages like `"Entity takes D damage from Poison."`.
        *   Decrement temporary effect durations via `StatsManager`.
        *   **Orchestrator - Events T.6.N (Queued):** For system messages like `"Effect 'XYZ' has worn off."`.
    *   **Placeholder for Status Effect Visual Update:** After a status is applied/removed, an Orchestrator event could update status icons on the `CombatEntityWidget`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes all T.5.N, T.6.N events sequentially (relevant display, TTS for some, 1-SECOND DELAY after each block of similar effects). After last one, signals `CombatManager` to resume.
    *   **`CombatManager`:** `current_step = ADVANCING_TURN`. Pauses. Orchestrator signals resume.

*(If `current_step` is `ADVANCING_TURN`)*

19. **Combat Manager: `_step_advancing_turn()`**
    *   Calls `_advance_turn()`:
        *   Checks combat end conditions. If ended, sets `self.state`, returns `None`.
        *   Else, finds next active entity, updates `current_turn_index`, `_active_entity_id`.
        *   **Orchestrator - Event T.7 (Queued if turn advanced):** `{type: "system_message", content: "It is now EntityZ's turn." ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes T.7 (if queued). After `visualDisplayComplete` and 1-SECOND DELAY, signals `CombatManager` to resume.
    *   **`CombatManager`:**
        *   If combat ended: `current_step = ENDING_COMBAT`.
        *   Else: Calls `_set_next_actor_step()`. (To `AWAITING_PLAYER_INPUT` or `AWAITING_NPC_INTENT`).
    *   If `AWAITING_PLAYER_INPUT`, `CombatManager` loop breaks. Else, pauses and Orchestrator signals resume.

---

**Phase 3: Combat End**

*(If `current_step` is `ENDING_COMBAT`)*

20. **Combat Manager: `_step_ending_combat(engine)`**
    *   Final cleanup (remove temp combat effects like "Defending").
    *   **Orchestrator - Event 3.1 (Queued):** `{type: "system_message", content: f"Combat has ended. Outcome: {self.state.name}" ...}`.
    *   `CombatManager` pauses.
    *   **Orchestrator:** Processes 3.1. After `visualDisplayComplete` and 1-SECOND DELAY, signals `CombatManager` to resume.
    *   **`CombatManager`:** `current_step = COMBAT_ENDED`. `CombatManager` loop effectively ends.

21. **Engine: Post-Combat Processing (`GameEngine` detects `CombatStep.COMBAT_ENDED`)**
    *   Sets `game_state.current_mode = InteractionMode.NARRATIVE`.
    *   Sets `game_state.combat_manager = None`.
    *   **LLM Closing Narrative Generation:**
        *   Prompts `NarratorAgent` for closing narrative.
        *   **Output (Engine -> UI):** Sends this narrative to `MainWindow` (role "gm").
        *   **UI Handling (`MainWindow`):**
            *   Displays in `GameOutputWidget`.
            *   `GameOutputWidget` emits `visualDisplayComplete`.
            *   (If TTS active) `TTSManager` speaks. Emits `ttsPlaybackComplete`.
    *   **Engine (after `visualDisplayComplete` and `ttsPlaybackComplete`):** Game fully returns to NARRATIVE, ready for next player input.

This detailed flow emphasizes distinct logical steps within the `CombatManager`, each queuing its displayable information for the `CombatOutputOrchestrator`. The Orchestrator then ensures sequential display, TTS (if applicable), and timed delays before allowing the `CombatManager` to proceed to its next logical step. This should address the ordering issues and prepare the system for TTS and more complex visual effects.