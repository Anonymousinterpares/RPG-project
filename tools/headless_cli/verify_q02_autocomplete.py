#!/usr/bin/env python3
"""
Verify that TEST_Q02 (Q02 – Defeat the Test Wolf) is automatically marked completed
once the defeat criteria are met (enemy defeated event logged).

Usage example (from project root):
  python tools/headless_cli/verify_q02_autocomplete.py --file wolf_alpha.json --llm --timeout 45000
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, Optional

from PySide6.QtCore import QCoreApplication, QTimer

from core.testing.headless_env import bootstrap_headless, run_in_qt_thread
from core.base.engine import get_game_engine


def parse_args(argv):
    p = argparse.ArgumentParser(description="Verify TEST_Q02 auto-completion after wolf defeat")
    p.add_argument("--file", required=True, help="Save filename in saves/ (e.g., wolf_alpha.json)")
    p.add_argument("--timeout", type=int, default=30000, help="Timeout (ms)")
    p.add_argument("--llm", action="store_true", help="Enable LLM")
    p.add_argument("--max_attacks", type=int, default=12, help="Max 'attack' actions to attempt")
    return p.parse_args(argv)


def main(argv) -> int:
    ns = parse_args(argv)
    ctx = bootstrap_headless(seed=42, llm_enabled=bool(ns.llm), tts_enabled=False, combat_delay_ms=0)
    app: QCoreApplication = ctx["app"]
    engine = ctx["engine"]

    # Load flat JSON save using engine
    loaded_state = engine.load_game(ns.file)
    if loaded_state is None:
        print("[ERROR] Failed to load save.")
        return 2

    result: Dict[str, Any] = {
        "defeat_event_found": False,
        "quest_status": None,
        "quest_detail": None,
    }

    def check_defeat_event(gs) -> Optional[str]:
        try:
            from core.game_flow.quest_updates import EV_ENEMY_DEFEATED
            log = getattr(gs, 'event_log', []) or []
            for ev in log:
                if ev.get('type') == EV_ENEMY_DEFEATED:
                    tid = str(ev.get('template_id') or '').lower()
                    eid = str(ev.get('entity_id') or '').lower()
                    if tid in ("test_wolf_alpha", "wolf_alpha") or eid in ("test_wolf_alpha", "wolf_alpha"):
                        return ev.get('template_id') or ev.get('entity_id') or 'wolf_alpha'
        except Exception:
            pass
        return None

    def get_q02_status(gs) -> Dict[str, Any]:
        try:
            j = getattr(gs, 'journal', {}) or {}
            qs = j.get('quests', {}) if isinstance(j, dict) else {}
            q02 = qs.get('TEST_Q02')
            if isinstance(q02, dict):
                return {"status": q02.get('status'), "objectives": q02.get('objectives')}
        except Exception:
            pass
        return {"status": None}

    def drive():
        try:
            gs = engine._state_manager.current_state
            if gs is None:
                return

            # If enemy already defeated, just proceed to check quest status
            match = check_defeat_event(gs)
            if match:
                result["defeat_event_found"] = True
                # Allow a short delay for quest recompute
                QTimer.singleShot(200, finalize)
                return

            # Otherwise, if in combat and waiting for input, attack
            try:
                from core.combat.enums import CombatStep
                from core.interaction.enums import InteractionMode
                cm = getattr(gs, 'combat_manager', None)
                if gs.current_mode == InteractionMode.COMBAT and cm and cm.current_step == CombatStep.AWAITING_PLAYER_INPUT:
                    if drive.remaining_attacks > 0:
                        drive.remaining_attacks -= 1
                        engine.process_input('attack')
                # No else: just keep polling
            except Exception:
                pass
        finally:
            if result["quest_status"] is None:
                QTimer.singleShot(200, drive)

    def finalize():
        try:
            gs = engine._state_manager.current_state
            q02 = get_q02_status(gs)
            result["quest_status"] = q02.get("status")
            result["quest_detail"] = q02
        finally:
            # Report
            print(f"[RESULT] defeat_event_found={result['defeat_event_found']} quest_status={result['quest_status']}")
            if isinstance(result.get("quest_detail"), dict):
                import json
                print("[DETAIL] "+json.dumps(result["quest_detail"], ensure_ascii=False))
            app.quit()

    drive.remaining_attacks = int(ns.max_attacks)
    run_in_qt_thread(drive, 50)

    # End after timeout regardless
    QTimer.singleShot(int(ns.timeout), app.quit)

    app.exec()

    # Interpret
    if result["defeat_event_found"] and result["quest_status"] == "completed":
        print("[PASS] TEST_Q02 auto-completed after wolf defeat.")
        return 0
    else:
        print("[FAIL] TEST_Q02 did not auto-complete (see above).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

