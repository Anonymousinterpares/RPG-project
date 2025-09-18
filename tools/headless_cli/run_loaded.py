#!/usr/bin/env python3
"""
Headless loader/runner: load an existing flat-file save (StateManager JSON) and try to continue combat.

Example:
  python tools\headless_cli\run_loaded.py --file wolf_alpha.json --actions attack attack --timeout 12000
"""
import argparse
import sys
from typing import List, Dict, Any

from PySide6.QtCore import QCoreApplication, QTimer

from core.testing.headless_env import bootstrap_headless, run_in_qt_thread
from core.testing.headless_ui_listener import HeadlessUIListener
from core.base.engine import get_game_engine


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Headlessly load a save and continue combat if present.")
    p.add_argument("--file", required=True, help="Save filename in saves/ (e.g., wolf_alpha.json)")
    p.add_argument("--timeout", type=int, default=12000, help="Run timeout in ms")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument("--llm", action="store_true", help="Enable LLM (default disabled)")
    p.add_argument("--actions", nargs="*", default=["attack", "attack"], help="Actions to attempt when awaiting player input")
    return p.parse_args(argv)


essential_steps_to_wait = 6


def main(argv: List[str]) -> int:
    ns = parse_args(argv)
    ctx = bootstrap_headless(seed=ns.seed, llm_enabled=bool(ns.llm), tts_enabled=False, combat_delay_ms=0)
    app: QCoreApplication = ctx["app"]
    engine = ctx["engine"]

    listener = HeadlessUIListener(engine)

    # Load the save as a flat JSON via engine API
    loaded_state = engine.load_game(ns.file)

    # If load failed, quit quickly
    if loaded_state is None:
        QTimer.singleShot(0, app.quit)
        app.exec()
        sys.stdout.write(listener.dump_transcript() + "\n")
        return 2

    # Drive combat if in combat mode
    def drive_actions(actions: List[str]):
        try:
            gs = engine._state_manager.current_state
            if gs is None:
                return
            from core.combat.enums import CombatStep
            from core.interaction.enums import InteractionMode
            cm = getattr(gs, 'combat_manager', None)
            if gs.current_mode == InteractionMode.COMBAT and cm:
                # If waiting for player input, send next action
                if cm.current_step == CombatStep.AWAITING_PLAYER_INPUT and actions:
                    next_action = actions.pop(0)
                    engine.process_input(next_action)
            else:
                # Outside combat: process any remaining scripted actions directly
                if actions:
                    next_action = actions.pop(0)
                    engine.process_input(next_action)
        except Exception:
            pass
        finally:
            # Keep polling a few times to push the flow
            if actions:
                QTimer.singleShot(250, lambda: drive_actions(actions))

    # Start driving actions shortly after load
    run_in_qt_thread(drive_actions, 50, list(ns.actions))

    # End after timeout
    QTimer.singleShot(ns.timeout, app.quit)

    app.exec()

    # Print transcript
    sys.stdout.write(listener.dump_transcript() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

