#!/usr/bin/env python3
"""
Headless reproduction script:
- Load the last save 'test_fight_new'
- Start a new game
- Ask the LLM narrator (natural language) to start a fight with a wolf
- Observe stats and combat participants to detect any stale carry-over

Usage (PowerShell):
  python tools\headless_cli\repro_new_game_wolf.py --timeout 12000 --llm
"""
import argparse
import sys
from typing import List

from PySide6.QtCore import QCoreApplication, QTimer

# Ensure project root is on sys.path (mirror run_families_quick.py behavior)
import sys as _sys
from pathlib import Path as _Path
_proj_root = _Path(__file__).resolve().parents[2]
if str(_proj_root) not in _sys.path:
    _sys.path.insert(0, str(_proj_root))

from core.testing.headless_env import bootstrap_headless, run_in_qt_thread
from core.testing.headless_ui_listener import HeadlessUIListener
from core.base.engine import get_game_engine


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Repro: stale combat stats after new game")
    p.add_argument("--timeout", type=int, default=12000, help="qt run timeout ms")
    p.add_argument("--seed", type=int, default=42, help="random seed")
    p.add_argument("--llm", action="store_true", help="enable LLM (recommended)")
    p.add_argument("--save", default="test_fight_new", help="save filename (without .json)")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    ns = parse_args(argv)

    ctx = bootstrap_headless(seed=ns.seed, llm_enabled=bool(ns.llm), tts_enabled=False, combat_delay_ms=0)
    app: QCoreApplication = ctx["app"]
    engine = ctx["engine"]

    listener = HeadlessUIListener(engine)

    def load_save_then_new_game():
        try:
            print(f"INFO: Loading save '{ns.save}'...")
            engine.load_game(ns.save)
        except Exception as e:
            print(f"WARN: load_game failed: {e}")
        finally:
            # Proceed regardless; we want to simulate the sequence user reported
            QTimer.singleShot(200, start_new_game)

    def start_new_game():
        try:
            print("INFO: Starting NEW GAME now...")
            engine.start_new_game(player_name="HeadlessTester")
        except Exception as e:
            print(f"ERROR: start_new_game failed: {e}")
        finally:
            QTimer.singleShot(200, inspect_fresh_stats)

    def inspect_fresh_stats():
        try:
            sm = engine._state_manager.stats_manager
            from core.stats.stats_base import DerivedStatType as D
            hp = sm.get_current_stat_value(D.HEALTH); hp_max = sm.get_stat_value(D.MAX_HEALTH)
            sta = sm.get_current_stat_value(D.STAMINA); sta_max = sm.get_stat_value(D.MAX_STAMINA)
            mp = sm.get_current_stat_value(D.MANA); mp_max = sm.get_stat_value(D.MAX_MANA)
            print(f"CHECK: After NEW GAME -> HP {hp:.0f}/{hp_max:.0f}, STA {sta:.0f}/{sta_max:.0f}, MP {mp:.0f}/{mp_max:.0f}")
            # Also list active status effects
            try:
                effects = [e.name for e in sm.get_status_effects()]  # type: ignore
            except Exception:
                effects = []
            print(f"CHECK: Active status effects after NEW GAME: {effects}")
        except Exception as e:
            print(f"WARN: Could not inspect fresh stats: {e}")
        finally:
            QTimer.singleShot(400, request_llm_wolf)

    def request_llm_wolf():
        try:
            # Natural language request that should route via NarratorAgent
            prompt = "I look for a wolf nearby and attack it."
            print(f"INFO: Sending NL input to LLM: '{prompt}'")
            engine.process_input(prompt)
        except Exception as e:
            print(f"ERROR: process_input failed: {e}")
        finally:
            # Give some time for mode transition and combat init
            QTimer.singleShot(1500, inspect_combat_state)

    def inspect_combat_state():
        try:
            gs = engine._state_manager.current_state
            if not gs:
                print("WARN: No current GameState.")
                return
            from core.interaction.enums import InteractionMode
            mode = getattr(gs, 'current_mode', None)
            print(f"CHECK: Current mode = {getattr(mode, 'name', mode)}")
            if mode and mode.name == 'COMBAT':
                cm = getattr(gs, 'combat_manager', None)
                if cm:
                    from core.combat.combat_entity import EntityType
                    print("INFO: Combat participants and HP:")
                    for eid, ent in cm.entities.items():
                        who = 'PLAYER' if getattr(ent, 'entity_type', None) == EntityType.PLAYER else 'ENEMY'
                        print(f"  - {who}: {ent.combat_name} HP {int(ent.current_hp)}/{int(ent.max_hp)} STA {int(ent.current_stamina)}/{int(ent.max_stamina)} MP {int(getattr(ent, 'current_mp', 0))}/{int(getattr(ent, 'max_mp', 0))}")
                else:
                    print("WARN: current_mode=COMBAT but combat_manager is None")
            else:
                print("INFO: No combat started by LLM within the time window.")
                print("HINT: You can re-run with --llm to ensure NarratorAgent is enabled.")
        except Exception as e:
            print(f"WARN: inspect_combat_state failed: {e}")
        finally:
            # Quit shortly after
            QTimer.singleShot(2000, app.quit)

    run_in_qt_thread(load_save_then_new_game, 50)
    QTimer.singleShot(int(ns.timeout), app.quit)
    app.exec()

    # Dump captured transcript/events for further inspection
    print("\n===== Transcript Dump =====")
    sys.stdout.write(listener.dump_transcript() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

