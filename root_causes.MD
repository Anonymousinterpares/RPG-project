# Root Causes Log

This document records concise root causes and fixes for issues encountered in the project. Keep it short, specific, and updated.

---

## Combat stalls after player damage or magic attempt (GUI-only)

- Problem
  - After lines like:
    - "Pras/Lars takes N Physical damage! (HP: X/Y)"
    - "<Player> begins to channel/weave arcane energies..."
  - The GUI stopped advancing (no bar updates or further narration) until user input. Headless mode did not stall.

- Root cause
  - In the orchestrator, non-visual events APPLY_ENTITY_RESOURCE_UPDATE and APPLY_ENTITY_STATE_UPDATE set `is_processing_event = False` before calling `_check_event_processing_complete(...)`.
  - `_check_event_processing_complete` has a guard that requires `is_processing_event` to be True and the event ID to match; clearing it early caused completion to be ignored, so the queue never advanced.

- Why GUI-only
  - Headless acknowledges visual completion for every event automatically.
  - The GUI correctly completed gradual text events but then hit the APPLY_* bug, which blocked the queue.

- Final fix (working)
  - Orchestrator: For APPLY_* events, do not clear `is_processing_event` before calling `_check_event_processing_complete(...)`; let the normal event-based completion advance the queue. Added debug logs when APPLY_* completes.
  - CombatDisplay (COMBAT_LOG text): On immediate/gradual end, emit `visualDisplayComplete` and also directly notify the orchestrator if it’s still waiting. Added start/end logs.

- Attempts that did not work / were insufficient (and why)
  - CharacterSheet-only completion for bar updates: stall was earlier (on prior text or at APPLY_*), so it didn’t help.
  - Time-based safety net (QTimer): brittle and not event-driven; masked the real bug and still missed certain cases.
  - Fallback completion only on CombatEntityWidget: CharacterSheet path and APPLY_* events could still stall.

- Files changed
  - core/orchestration/combat_orchestrator.py — event-based completion for APPLY_* without clearing `is_processing_event` first; added logs.
  - gui/components/combat_display.py — event-based completion on immediate/gradual text (emit + direct notify); added detailed logs.
  - gui/main_window.py — routed event_id to CombatDisplay and added routing logs; removed time-based fallback for COMBAT_LOG strings.

- Status
  - Resolved. Verified: magic attempt and player damage progress through APPLY → PHASE1/PHASE2 and subsequent events without user input.

