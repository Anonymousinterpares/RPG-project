 Revised Implementation Plan

  Phase 1: Backend Logic (AP Mechanics & NPC Intelligence)

   1. Configuration (`config/combat/combat_config.json`):
       * I will add a new "ap_system" section containing the action costs, base AP values, and the formulas for
         deriving Max AP and AP Regeneration from Constitution and Dexterity, as planned.

   2. Stats Integration (`core/stats/stats_base.py` & `core/stats/stats_manager.py`):
       * I will add MAX_AP and AP_REGENERATION to the DerivedStatType enum and implement the calculation logic
         in the StatsManager. This remains unchanged from the original plan.

   3. Combat Logic (`core/combat/combat_manager.py`):
       * I will implement the AP tracking, initialization, regeneration, and cost deduction as previously
         described.
       * The multi-action turn logic will be added conditionally to the _step_advancing_turn method.
       * (New for Remark 2) In the _step_awaiting_npc_intent method, before calling the LLM agent for an NPC's
         action, I will dynamically construct a new prompt segment. This segment will:
           * State the NPC's current AP.
           * List only the actions the NPC can afford with its current AP pool.
           * Always include a zero-cost "pass" option to allow the NPC to end its turn and save AP if it cannot
             afford or does not wish to perform any other action. This ensures the NPC never gets stuck.
           * This context-rich prompt will be injected into the agent's request, ensuring NPCs act intelligently
              within the new AP rules.

   4. Event System (`core/orchestration/events.py`):
       * I will add a new AP_UPDATE event to DisplayEventType to communicate AP changes to the UI, as planned.

  Phase 2: Frontend Integration (UI Placement)

   5. Character Sheet UI (`gui/components/character_sheet.py`):
       * (New for Remark 1) I will instantiate the APDisplayWidget and add it to the layout of the "Combat Info"
          group box. It will be placed directly above the "Status Effects" label, ensuring it is visually
         grouped with other combat-relevant information.
       * The update_ap_display method will be added to the character sheet to facilitate updates.

   6. Main Window (`gui/main_window.py`):
       * I will add the necessary logic to process_orchestrated_display_event to listen for the AP_UPDATE event
         and call the corresponding update method on the CharacterSheetWidget, as planned.