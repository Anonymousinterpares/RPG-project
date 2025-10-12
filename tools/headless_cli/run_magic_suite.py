#!/usr/bin/env python3
"""
Headless combat magic suite:
- Starts a new game
- Spawns enemies
- Learns a set of spells representing core atom types
- Ensures high mana
- Casts spells to exercise: damage, heal, buff (positive), debuff (negative buff), status_apply
- Prints a transcript at the end

Usage:
  python -m tools.headless_cli.run_magic_suite --timeout 12000
"""
import argparse
from typing import List

from PySide6.QtCore import QCoreApplication, QTimer

from core.testing.headless_env import bootstrap_headless
from core.testing.headless_ui_listener import HeadlessUIListener
from core.base.state import get_state_manager
from core.stats.stats_base import DerivedStatType


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Headless magic combat suite")
    p.add_argument("--timeout", type=int, default=12000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--enemies", default="wolf")
    p.add_argument("--count", type=int, default=2)
    return p.parse_args(argv)


def _ensure_high_mana_for_player(cm) -> None:
    player_id = None
    for eid, ent in cm.entities.items():
        if getattr(ent, 'entity_type', None).name == 'PLAYER':
            player_id = eid
            break
    if not player_id:
        return
    try:
        sm = cm._get_entity_stats_manager(player_id)
        # bump max then current
        try:
            sm.derived_stats[DerivedStatType.MAX_MANA].base_value = 999.0
        except Exception:
            pass
        sm.set_current_stat(DerivedStatType.MANA, 999.0)
    except Exception:
        pass


def main(argv: List[str]) -> int:
    ns = parse_args(argv)

    ctx = bootstrap_headless(seed=ns.seed, llm_enabled=False, tts_enabled=False, combat_delay_ms=0)
    app: QCoreApplication = ctx["app"]
    engine = ctx["engine"]
    listener = HeadlessUIListener(engine)

    # Start new game
    engine.start_new_game(player_name="MagicSuiteTester")

    # Start combat
    engine.process_command(f"//start_combat {ns.enemies} 1 {ns.count}")
    gs = get_state_manager().current_state
    cm = getattr(gs, 'combat_manager', None)
    if not cm:
        print("ERROR: CombatManager not available")
        return 1

    _ensure_high_mana_for_player(cm)

    # Spells to exercise atoms
    spells = [
        # damage
        ("prismatic_bolt", None),            # explicit target chosen later
        # heal (self default)
        ("healing_touch", None),
        # buff (self)
        ("resonant_shield", None),
        # debuff + status_apply (two atoms)
        ("dirge_of_despair", None),
        # status_apply + debuff
        ("crystal_prison", None),
    ]

    # Learn all first
    for sid, _ in spells:
        engine.process_command(f"//learn_spell {sid}")

    # Pick first enemy for explicit casts
    enemy_ids: List[str] = []
    for eid, ent in cm.entities.items():
        if getattr(ent, 'entity_type', None).name == 'ENEMY' and ent.is_alive():
            enemy_ids.append(eid)
    target_id = enemy_ids[0] if enemy_ids else None

    # Cast sequences
    # damage with explicit target
    if target_id:
        engine.process_command(f"//cast prismatic_bolt {target_id}")
    # heal self (no target)
    engine.process_command(f"//cast healing_touch")
    # buff self
    engine.process_command(f"//cast resonant_shield")
    # debuff+status on enemy (fallback to random if none)
    if target_id:
        engine.process_command(f"//cast dirge_of_despair {target_id}")
    else:
        engine.process_command(f"//cast dirge_of_despair")
    # status_apply+debuff on enemy
    if target_id:
        engine.process_command(f"//cast crystal_prison {target_id}")
    else:
        engine.process_command(f"//cast crystal_prison")

    QTimer.singleShot(int(ns.timeout), app.quit)
    app.exec()

    print("\n===== Magic Suite Transcript =====")
    import sys as _sys
    _sys.stdout.write(listener.dump_transcript() + "\n")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
