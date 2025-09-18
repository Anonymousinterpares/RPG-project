#!/usr/bin/env python3
"""
Headless quick-run to test families mode by creating an enemy via command path.

Usage:
  py -3 -X utf8 tools\headless_cli\run_families_quick.py --family verdant_beast --count 1 --timeout 8000

This boots the engine headlessly, switches NPC generation mode to 'families' (in-memory),
starts a new game, and invokes the dev command to start combat against the chosen family id
(using the existing `start_combat` command pathway which now interprets enemy_type as family_id
when in families mode).
"""
import argparse
import sys
from PySide6.QtCore import QCoreApplication, QTimer

import os
import sys as _sys
from pathlib import Path as _Path
# Ensure project root is on sys.path
_proj_root = _Path(__file__).resolve().parents[2]
if str(_proj_root) not in _sys.path:
    _sys.path.insert(0, str(_proj_root))

from core.testing.headless_env import bootstrap_headless, run_in_qt_thread
from core.base.engine import get_game_engine
from core.combat import register_combat_commands


def parse_args(argv):
    p = argparse.ArgumentParser(description="Run a quick families-mode combat")
    p.add_argument("--family", required=True, help="family_id to fight (e.g., verdant_beast, concordant_citizen)")
    p.add_argument("--count", type=int, default=1, help="number of enemies")
    p.add_argument("--timeout", type=int, default=8000, help="qt run timeout ms")
    p.add_argument("--difficulty", type=str, default="normal", help="difficulty: story|normal|hard|expert")
    p.add_argument("--encounter", type=str, default="solo", help="encounter size: solo|pack|mixed")
    return p.parse_args(argv)


def main(argv) -> int:
    ns = parse_args(argv)
    ctx = bootstrap_headless(seed=42, llm_enabled=False, tts_enabled=False, combat_delay_ms=0)
    app: QCoreApplication = ctx["app"]
    engine = ctx["engine"]

    # Set config flag in-memory for this run
    cfg = engine._config
    try:
        cfg._config_data.setdefault("system", {})
        cfg._config_data["system"]["npc_generation_mode"] = "families"
        cfg._config_data.setdefault("game", {})
        cfg._config_data["game"]["difficulty"] = ns.difficulty
        cfg._config_data["game"]["encounter_size"] = ns.encounter
        print("INFO: In-memory system.npc_generation_mode=families")
        print(f"INFO: In-memory game.difficulty={ns.difficulty} game.encounter_size={ns.encounter}")
    except Exception:
        print("WARN: Could not set in-memory config flag; families path may not trigger.")

    def drive():
        try:
            # Ensure new game state exists
            engine.start_new_game(player_name="Tester")
            # Ensure dev commands are registered
            try:
                register_combat_commands()
            except Exception:
                pass
            # Use dev command to start combat; enemy type interpreted as family id in families mode
            cmd = f"//start_combat {ns.family} 1 {ns.count}"
            res = engine.process_input(cmd)
            print(f"INFO: issued '{cmd}' => {getattr(res, 'message', res)}")
        except Exception as e:
            print(f"ERROR during drive: {e}")
        finally:
            # Quit after a short delay to allow logs/events to emit
            QTimer.singleShot(2000, app.quit)

    run_in_qt_thread(drive, 50)
    QTimer.singleShot(int(ns.timeout), app.quit)
    app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

