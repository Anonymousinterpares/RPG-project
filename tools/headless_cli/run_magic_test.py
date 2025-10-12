#!/usr/bin/env python3
"""
Headless magic test: start combat, list entities (with IDs), learn a spell, and cast it at a chosen target.

Usage (PowerShell):
  python tools\headless_cli\run_magic_test.py --spell prismatic_bolt --enemies wolf --count 2 --timeout 8000
"""
import argparse
from typing import List

from PySide6.QtCore import QCoreApplication, QTimer

from core.testing.headless_env import bootstrap_headless
from core.base.engine import get_game_engine
from core.base.state import get_state_manager
from core.stats.stats_base import DerivedStatType
from core.stats.stats_manager import get_stats_manager
from core.testing.headless_ui_listener import HeadlessUIListener


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a headless magic casting test")
    p.add_argument("--spell", default="prismatic_bolt", help="Spell id to cast")
    p.add_argument("--enemies", default="wolf", help="Enemy template id")
    p.add_argument("--count", type=int, default=2, help="Number of enemies to spawn")
    p.add_argument("--timeout", type=int, default=8000, help="QT event loop timeout (ms)")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    ns = parse_args(argv)

    ctx = bootstrap_headless(seed=ns.seed, llm_enabled=False, tts_enabled=False, combat_delay_ms=0)
    app: QCoreApplication = ctx["app"]
    engine = ctx["engine"]
    listener = HeadlessUIListener(engine)

    # Start a new game to ensure GameState is initialized
    try:
        engine.start_new_game(player_name="HeadlessMage")
    except Exception as e:
        print(f"WARN: start_new_game failed or already started: {e}")

    # Ensure we have plenty of mana for the test
    try:
        sm = get_stats_manager()
        sm.set_current_stat(DerivedStatType.MANA, 999.0)
    except Exception:
        pass

    # Start combat with specified enemies
    cmd = f"//start_combat {ns.enemies} 1 {ns.count}"
    print(f"INFO: {cmd}")
    engine.process_command(cmd)

    # Inspect combat entities and pick an enemy target
    gs = get_state_manager().current_state
    cm = getattr(gs, 'combat_manager', None)
    if not cm or not cm.entities:
        print("ERROR: Combat manager/entities not available")
        return 1

    print("INFO: Combat entities (id -> name [type])")
    enemy_ids: List[str] = []
    player_id: str = ""
    for eid, ent in cm.entities.items():
        etype = getattr(ent, 'entity_type', None)
        etype_s = getattr(etype, 'name', str(etype))
        print(f"  {eid} -> {ent.combat_name} [{etype_s}]")
        if etype_s == 'ENEMY' and ent.is_alive():
            enemy_ids.append(eid)
        if etype_s == 'PLAYER':
            player_id = eid

    if not enemy_ids:
        print("ERROR: No enemy ids found")
        return 1

    target_id = enemy_ids[0]

    # Ensure high mana on the player's combat StatsManager (prevents pre-block)
    if player_id:
        try:
            player_sm = cm._get_entity_stats_manager(player_id)
            # Raise max mana first to avoid clamping
            if hasattr(player_sm, 'derived_stats'):
                try:
                    player_sm.derived_stats[DerivedStatType.MAX_MANA].base_value = 999.0
                except Exception:
                    pass
            player_sm.set_current_stat(DerivedStatType.MANA, 999.0)
        except Exception as _e:
            pass

    # Learn the spell (dev)
    learn_cmd = f"//learn_spell {ns.spell}"
    print(f"INFO: {learn_cmd}")
    engine.process_command(learn_cmd)

    # Cast at explicit target id
    cast_cmd = f"//cast {ns.spell} {target_id}"
    print(f"INFO: {cast_cmd}")
    engine.process_command(cast_cmd)

    # Also test fallback targeting (no explicit target) when multiple enemies
    cast_cmd2 = f"//cast {ns.spell}"
    print(f"INFO: {cast_cmd2}")
    engine.process_command(cast_cmd2)

    # Let the orchestrator run
    QTimer.singleShot(int(ns.timeout), app.quit)
    app.exec()

    # Dump captured transcript/events for further inspection
    print("\n===== Transcript Dump =====")
    import sys as _sys
    _sys.stdout.write(listener.dump_transcript() + "\n")

    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
