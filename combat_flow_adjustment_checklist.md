Okay, Manager, here is the detailed implementation checklist for the Enhanced Combat Flow Algorithm (TTS Ready).

```markdown
# ECFA_implementation.md

## Reason and Goal for Implementation

**Reason:** The current combat system exhibits several misalignments with the desired narrative-rich, sequential, and immersive turn-based RPG experience. Key issues include incorrect ordering of narrative and system messages, lack of clear pacing control, potential race conditions between game logic and UI updates (especially with gradual text display), incomplete NPC action processing, and missing narrative elements like combat initiation and conclusion summaries. These problems detract from player immersion and can make combat feel disjointed or confusing.

**Goal:** To implement a robust, strictly sequential, and narrative-rich combat system ("Enhanced Combat Flow Algorithm") that:
1.  Ensures the correct chronological display of all combat events: player/NPC action attempt narratives, system messages (rolls, damage, status changes), and action impact narratives.
2.  Integrates a flag-based signaling system (`visualDisplayComplete`, `ttsPlaybackComplete`) to meticulously control the flow, ensuring that game logic pauses and waits for visual text rendering and (future) TTS playback to complete before proceeding to the next logical step or event.
3.  Introduces configurable inter-step delays to provide a more deliberate, readable, and traditional text-RPG pacing.
4.  Corrects existing issues such as the NPC action conversion failure.
5.  Clearly distinguishes between narrative content (eligible for TTS) and system messages.
6.  Implements a two-phase visual effect for HP, Stamina, and Mana bar reductions to enhance feedback.
7.  Establishes a resilient architecture prepared for future enhancements like full Text-to-Speech (TTS) integration for narratives and more complex visual/audio effects for combat actions.

---

## Implementation Checklist

**Phase I: Core Architectural Changes (Orchestrator, Signals, Event Queue)**

*   **[ ] 1. Design `DisplayEvent` Data Structure:**
    *   Location: Define in a new module, e.g., `core/orchestration/events.py` or within the orchestrator module.
    *   Content:
        *   `event_id: str` (UUID for tracking)
        *   `type: DisplayEventType` (Enum: `NARRATIVE_ATTEMPT`, `NARRATIVE_IMPACT`, `NARRATIVE_GENERAL`, `SYSTEM_MESSAGE`, `UI_BAR_UPDATE_PHASE1`, `UI_BAR_UPDATE_PHASE2`, `VISUAL_EFFECT_TRIGGER`, `BUFFER_FLUSH`)
        *   `content: Union[str, Dict[str, Any]]` (Text for narratives/messages, Dict for UI updates)
        *   `role: Optional[str]` (e.g., "gm", "system", "player" - for `MainWindow._handle_game_output`)
        *   `target_display: DisplayTarget` (Enum: `COMBAT_LOG`, `MAIN_GAME_OUTPUT`)
        *   `gradual_visual_display: bool` (Hint for `CombatDisplay`/`GameOutputWidget`)
        *   `tts_eligible: bool`
        *   `source_step: Optional[str]` (e.g., `CombatStep.name` for debugging)
        *   `metadata: Optional[Dict[str, Any]]` (e.g., for UI bar updates: `entity_id`, `bar_type`, `old_value`, `new_value`)

*   **[ ] 2. Implement `CombatOutputOrchestrator` Class:**
    *   Location: `core/orchestration/combat_orchestrator.py` (new module).
    *   Inheritance: `QObject` to use signals/slots and timers.
    *   Attributes:
        *   `event_queue: collections.deque[DisplayEvent]`
        *   `is_processing_event: bool`
        *   `is_waiting_for_visual: bool`
        *   `is_waiting_for_tts: bool`
        *   `inter_step_delay_timer: QTimer`
        *   `current_combat_manager_ref: Optional[weakref.ref[CombatManager]]`
        *   `engine_ref: Optional[weakref.ref[GameEngine]]`
        *   `tts_manager_ref: Optional[weakref.ref[TTSManager]]` (Placeholder)
        *   `config_delay_ms: int` (Load from game settings)
    *   Methods:
        *   `add_event_to_queue(DisplayEvent)`
        *   `_process_next_event_from_queue()`
            *   Pops event, sets `is_processing_event = True`.
            *   Sets `is_waiting_for_visual = True`. If `tts_eligible` and TTS active, `is_waiting_for_tts = True`.
            *   Routes content to `MainWindow._handle_game_output()` (via `engine_ref`).
            *   If `tts_eligible` and TTS active, calls `tts_manager_ref.speak()`.
            *   If neither visual nor TTS is awaited (e.g., a silent UI update event), directly call `_check_event_processing_complete()`.
        *   `_handle_visual_display_complete()`: Slot. Sets `is_waiting_for_visual = False`. Calls `_check_event_processing_complete()`.
        *   `_handle_tts_playback_complete()`: Slot. Sets `is_waiting_for_tts = False`. Calls `_check_event_processing_complete()`.
        *   `_check_event_processing_complete()`: If `not is_waiting_for_visual and not is_waiting_for_tts`:
            *   Sets `is_processing_event = False`.
            *   Starts `inter_step_delay_timer` with `config_delay_ms`.
        *   `_on_inter_step_delay_timeout()`: Slot.
            *   If `current_combat_manager_ref` exists and its `waiting_for_display_completion` flag (new flag in `CombatManager`) is true:
                *   Set `CombatManager.waiting_for_display_completion = False`.
                *   Call `CombatManager.process_combat_step(engine_ref)`.
            *   Calls `_process_next_event_from_queue()` if queue not empty.
        *   `set_references(engine, combat_manager, tts_manager)`
        *   `clear_queue_and_reset_flags()`

*   **[ ] 3. Add `visualDisplayComplete = Signal()` to `CombatDisplay` and `GameOutputWidget`:**
    *   File: `gui/components/combat_display.py` -> `CombatDisplay._append_formatted_text()` and `_display_next_log_char()`.
    *   File: `gui/components/game_output.py` -> `GameOutputWidget.append_text()` and `_display_next_char()`.
    *   Emit this signal when the *entire text segment* passed to `_append_formatted_text` (or `append_text`) has finished its visual rendering (either immediately or at the end of gradual display).

*   **[ ] 4. Create Placeholder `TTSManager` Class:**
    *   File: `core/audio/tts_manager.py` (new module).
    *   Class: `TTSManager(QObject)`.
    *   Signals: `ttsPlaybackComplete = Signal()`.
    *   Attributes: `is_enabled: bool` (from settings).
    *   Methods: `speak(text: str)`, `stop_playback()`. `speak` should immediately emit `ttsPlaybackComplete` if `is_enabled` is false or if text is empty. Otherwise, simulate playback with a `QTimer` based on text length and emit signal on timeout.

*   **[ ] 5. Integrate `CombatOutputOrchestrator` and `TTSManager` into `GameEngine`:**
    *   File: `core/base/engine.py`.
    *   In `GameEngine.__init__()`: Instantiate `CombatOutputOrchestrator` and `TTSManager`. Store them as attributes (e.g., `self._combat_orchestrator`).
    *   Pass necessary references (`engine`, `combat_manager` when it's created, `tts_manager`) to the orchestrator.

*   **[ ] 6. Modify `CombatManager` to Use Event Queue & Pause Logic:**
    *   File: `core/combat/combat_manager.py`.
    *   Add attribute: `waiting_for_display_completion: bool = False`.
    *   Modify all step methods (e.g., `_step_starting_combat`, `_step_performing_surprise_attack`, etc.):
        *   Replace `self._add_to_log()` calls (that are for player-visible messages) with logic to create `DisplayEvent` objects.
        *   Queue these events using `engine._combat_orchestrator.add_event_to_queue(display_event)`.
        *   After queueing one or more events that represent a logical pause point:
            *   Set `self.waiting_for_display_completion = True`.
            *   `return` or `break` from the `process_combat_step`'s internal `while` loop.

*   **[ ] 7. Modify `MainWindow._handle_game_output()`:**
    *   File: `gui/main_window.py`.
    *   This method is now primarily a router for `DisplayEvent.content` to the correct UI widget (`CombatDisplay` or `GameOutputWidget`) based on `DisplayEvent.target_display` or `game_state.current_mode`.
    *   Connect `CombatDisplay.visualDisplayComplete` and `GameOutputWidget.visualDisplayComplete` to `engine._combat_orchestrator._handle_visual_display_complete()`.
    *   The logic for buffering initial combat narrative needs to change: `MainWindow._update_ui` will now create and queue the `BUFFER_FLUSH` `DisplayEvent` when it detects the switch to combat view and a populated buffer.

*   **[ ] 8. Connect `TTSManager.ttsPlaybackComplete`:**
    *   In `GameEngine` or `MainWindow` (where orchestrator signals are accessible), connect `tts_manager.ttsPlaybackComplete` to `engine._combat_orchestrator._handle_tts_playback_complete()`.

---

**Phase II: Combat Initiation (Algorithm Point 1-6)**

*   **[ ] 1. `GameState` Flag Timing (`is_transitioning_to_combat`):**
    *   File: `core/game_flow/mode_transitions.py` -> `_handle_transition_request()`.
    *   Before calling `_initiate_combat_transition()`, if `target_mode == InteractionMode.COMBAT`, set `game_state.is_transitioning_to_combat = True`.
*   **[ ] 2. `_initiate_combat_transition()` (in `mode_transitions.py`):**
    *   Confirm it no longer calls `engine._output()` for the narrative that *triggered* combat. This narrative (from `NarratorAgent`) should have been output by `interaction_core.process_with_llm()`, received by `MainWindow`, and then buffered because `is_transitioning_to_combat` was (or should be, with fix II.1) true.
*   **[ ] 3. `MainWindow._update_ui()` for Combat Transition:**
    *   File: `gui/main_window.py`.
    *   When `current_mode_name == "COMBAT"` and `game_state.is_transitioning_to_combat` is true (or buffer is non-empty):
        *   Create `DisplayEvent` for `BUFFER_FLUSH` using `game_state.combat_narrative_buffer`.
        *   Queue with `engine._combat_orchestrator`.
        *   Crucially, `CombatManager.process_combat_step()` should only be invoked by the orchestrator *after* this `BUFFER_FLUSH` event (and its potential TTS) is complete and its inter-step delay has passed.
        *   Set `game_state.is_transitioning_to_combat = False` after the buffer is handed to the orchestrator.

---

**Phase III: Combat Start & Surprise Round (Algorithm Points 7-11 - `CombatManager` Steps)**

*   **[ ] 1. `_step_starting_combat()`:**
    *   Queue `DisplayEvent(type="system_message", content="Combat started! ...")`.
    *   Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 2. `_step_handling_surprise_check()`:**
    *   Apply "Surprised" status.
    *   Queue `DisplayEvent(type="system_message", content="Round 1 (Surprise Attack!)")`.
    *   If surprised targets, queue `DisplayEvent(type="system_message", content="Targets Surprised: ...")`.
    *   Generate surprise `AttackAction`.
    *   **NEW:** Call `CombatNarratorAgent` to get the *attempt* narrative for the surprise attack.
    *   Queue `DisplayEvent(type="narrative_attempt", content="[LLM: Player prepares surprise...]", tts_eligible=True)`.
    *   Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 3. `_step_performing_surprise_attack()`:**
    *   A. Deduct resources. Queue `DisplayEvent(type="ui_bar_update_phase1", metadata={...})`.
    *   B. Perform attack roll. Queue `DisplayEvent(type="system_message", content="Attacker rolls X...")`.
    *   Set `self.waiting_for_display_completion = True`; `return`.
    *   *(Orchestrator processes A then B with delay)*
    *   C. If hit: Calculate damage, apply to target. Queue `DisplayEvent(type="ui_bar_update_phase1", metadata={...target_hp...})`.
    *   D. Queue `DisplayEvent(type="system_message", content="Target takes B damage...")`.
    *   Set `self.waiting_for_display_completion = True`; `return`.
    *   *(Orchestrator processes C then D with delay)*
    *   E. Queue `DisplayEvent(type="ui_bar_update_phase2", metadata={...target_hp...})`.
    *   Store result. `current_step = NARRATING_SURPRISE_OUTCOME`. Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 4. `_step_narrating_surprise_outcome(engine)`:**
    *   Get LLM impact narrative.
    *   Queue `DisplayEvent(type="narrative_impact", content="[LLM: Surprise blow lands...]", tts_eligible=True)`.
    *   Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 5. `_step_ending_surprise_round()`:**
    *   Queue `DisplayEvent(type="system_message", content="Surprise round ends.")`.
    *   Remove "Surprised" status.
    *   Set `self.waiting_for_display_completion = True`; `return`.

---

**Phase IV: Regular Combat Rounds (Algorithm Points 12-19 - `CombatManager` Steps)**

*   **[ ] 1. `_step_rolling_initiative()`:**
    *   For each entity, queue `DisplayEvent` for their initiative roll system message.
    *   After queueing all roll messages: Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 2. `_step_starting_round()`:**
    *   Queue `DisplayEvent` for "Round X begins!".
    *   Queue `DisplayEvent` for "Turn order: ...".
    *   Determine first actor. Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 3. `_step_awaiting_npc_intent(engine)`:**
    *   (No direct display changes, primarily logic to get intent string).
*   **[ ] 4. `_step_processing_player/npc_action(engine)`:**
    *   Call `CombatNarratorAgent.process()`.
    *   Queue `DisplayEvent(type="narrative_attempt", tts_eligible=True)` for attempt narrative.
    *   Set `self.waiting_for_display_completion = True`; `return`.
    *   *(After resume)* Convert to `CombatAction`. If fails:
        *   Queue `DisplayEvent(type="system_message", content="Entity falters...")`.
        *   Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 5. `_step_resolving_action_mechanics()`:**
    *   (Follow similar pattern as surprise attack: queue resource bar phase 1, then roll message, pause; then damage bar phase 1, then damage message, pause; then damage bar phase 2. Each pause waits for orchestrator signal).
*   **[ ] 6. `_step_narrating_action_outcome(engine)`:**
    *   Get LLM impact narrative.
    *   Queue `DisplayEvent(type="narrative_impact", tts_eligible=True)`.
    *   Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 7. `_step_applying_status_effects()`:**
    *   For DOTs/HOTs:
        *   Queue `DisplayEvent` for `UI_BAR_UPDATE_PHASE1`.
        *   Queue `DisplayEvent` for system message (e.g., "Takes poison damage").
        *   Queue `DisplayEvent` for `UI_BAR_UPDATE_PHASE2`.
    *   For expired effects: Queue `DisplayEvent` for system message (e.g., "Effect worn off").
    *   After all status effect related events are queued: Set `self.waiting_for_display_completion = True`; `return`.
*   **[ ] 8. `_step_advancing_turn()`:**
    *   Call `_advance_turn()`.
    *   If turn advanced, queue `DisplayEvent` for "It is now EntityZ's turn."
    *   Set `self.waiting_for_display_completion = True`; `return`.

---

**Phase V: Combat End (Algorithm Points 20-21)**

*   **[ ] 1. `_step_ending_combat(engine)` (in `CombatManager`):**
    *   Cleanup effects.
    *   Queue `DisplayEvent(type="system_message", content="Combat has ended. Outcome: ...")`.
    *   Set `self.waiting_for_display_completion = True`; `return`.
    *   *(After resume)* `current_step = COMBAT_ENDED`.
*   **[ ] 2. Engine Post-Combat Processing (in `GameEngine` or `InputRouter`):**
    *   Detect `CombatStep.COMBAT_ENDED`.
    *   Set `game_state.current_mode = InteractionMode.NARRATIVE`.
    *   Set `game_state.combat_manager = None`.
    *   **NEW:** Prompt `NarratorAgent` for a *closing combat narrative*.
    *   Call `engine._output("gm", closing_narrative)` (this will now be routed to `GameOutputWidget` as mode is `NARRATIVE`).
    *   **Crucially, the GameEngine must now PAUSE its own main input loop or further processing until `GameOutputWidget` emits `visualDisplayComplete` (and `TTSManager` emits `ttsPlaybackComplete` if active) for this closing narrative.** This might involve the engine having its own "waiting for display" flag or using a modal approach for this specific output.

---

**Phase VI: UI Bar Visuals (HP/Stamina/Mana Two-Phase Decrease)**

*   **[ ] 1. Modify Bar Update Logic:**
    *   Files: `gui/components/combat_display.py -> CombatEntityWidget.update_stats()` and `gui/components/character_sheet.py -> CharacterSheetWidget._update_resources()`.
    *   These methods need to handle two types of `DisplayEvent` metadata:
        *   For `UI_BAR_UPDATE_PHASE1`:
            *   Receive `entity_id`, `bar_type`, `current_value_before_loss`, `amount_to_be_lost`.
            *   **Visual Change:** Style the segment of the bar representing `amount_to_be_lost` with a "bleak/transparent" color. The bar's actual `value` property is NOT changed yet.
            *   (This is the hard part with `QProgressBar`. May need a custom painted widget or an overlay.)
            *   Emit `visualDisplayComplete` *for this phase*.
        *   For `UI_BAR_UPDATE_PHASE2`:
            *   Receive `entity_id`, `bar_type`, `final_new_value`.
            *   Set the `QProgressBar.setValue(final_new_value)`.
            *   Re-apply the standard chunk stylesheet based on the new percentage.
            *   Emit `visualDisplayComplete` *for this phase*.
    *   The Orchestrator will insert a 1-second delay *between* processing a PHASE1 event and its corresponding PHASE2 event for the same bar update.

---

**Phase VII: TTS Integration Placeholders**

*   **[ ] 1. `CombatOutputOrchestrator` TTS Handling:**
    *   When processing a `DisplayEvent` with `tts_eligible=True`:
        *   If `TTSManager.is_enabled`, call `tts_manager_ref.speak(event.content)`.
        *   Set `self.is_waiting_for_tts = True`.
    *   In `_check_event_processing_complete()`: Only proceed if `not self.is_waiting_for_visual and not self.is_waiting_for_tts`.
*   **[ ] 2. `DisplayEvent` `tts_eligible` Flag:**
    *   Ensure `DisplayEvent`s created for NARRATIVE_ATTEMPT, NARRATIVE_IMPACT, NARRATIVE_GENERAL, and the BUFFER_FLUSH are marked `tts_eligible=True`.
    *   System messages should generally have `tts_eligible=False`.

---

**Phase VIII: General Refinements & Testing**

*   **[ ] 1. Configuration for Delays:**
    *   Add to `config/game_config.json`: `combat_inter_step_delay_ms: 1000`.
    *   `CombatOutputOrchestrator` loads and uses this.
*   **[ ] 2. NPC Action Conversion (`CombatManager`):**
    *   File: `core/combat/combat_manager.py` -> `_step_processing_npc_action()` and `_step_processing_player_action()`.
    *   Add `elif combat_action_type == ActionType.SPELL:` block.
    *   Inside, create `SpellAction` instance, extracting `spell_name`, `target_actor_id` (resolve to internal ID), `cost_mp`, `dice_notation` from the agent's structured request. Handle missing fields gracefully.
    *   Extend for other `ActionType`s as they are added (ITEM, FLEE, etc.).
*   **[ ] 3. MainWindow `_handle_game_output` Echo Prevention:**
    *   Review and ensure the `_last_submitted_command` logic in `MainWindow._handle_game_output` correctly prevents echoes, especially with the new orchestrator flow. The orchestrator might need to pass the original `DisplayEvent` type or source to help `MainWindow` differentiate.
*   **[ ] 4. Game State Access in `CombatManager`:**
    *   Many `CombatManager` methods currently rely on `engine` being passed to access `game_state`. It would be cleaner if `CombatManager` received a `GameState` reference during its instantiation or via a dedicated method, reducing direct dependency on the `engine` object for state data. For now, the engine reference is passed where needed.
*   **[ ] 5. Thorough Testing:**
    *   Test all combat initiation paths (surprise, no surprise).
    *   Test player and NPC turns.
    *   Test various action outcomes (hit, miss, crit, fumble).
    *   Test combat end scenarios (victory, defeat, flee, surrender).
    *   Test with TTS disabled and (once placeholder is active) enabled.
    *   Test different gradual text display speeds to ensure delays are independent.
*   **[ ] 6. Review Logging:** Add detailed logging to the `CombatOutputOrchestrator` and confirm logs from other modules are still relevant and clear.

```