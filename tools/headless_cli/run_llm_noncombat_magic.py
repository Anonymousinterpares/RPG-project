#!/usr/bin/env python3
"""
Headless non-combat magic test with LLM enabled.
- Starts new game (LLM on)
- Learns a utility/defensive spell
- Sends a natural language input to cast the spell outside combat
- Captures transcript to verify agentic workflow triggers

Usage:
  python tools\headless_cli\run_llm_noncombat_magic.py --spell planar_transit --timeout 15000 --llm
"""
import argparse
from typing import List

from PySide6.QtCore import QCoreApplication, QTimer

from core.testing.headless_env import bootstrap_headless
from core.testing.headless_ui_listener import HeadlessUIListener

from core.base.engine import get_game_engine


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Headless LLM non-combat magic test")
    p.add_argument("--spell", default="planar_transit", help="Spell id to test (utility or defensive)")
    p.add_argument("--timeout", type=int, default=15000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--llm", action="store_true", help="Enable LLM")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    ns = parse_args(argv)

    ctx = bootstrap_headless(seed=ns.seed, llm_enabled=bool(ns.llm), tts_enabled=False, combat_delay_ms=0)
    app: QCoreApplication = ctx["app"]
    engine = ctx["engine"]
    listener = HeadlessUIListener(engine)

    # Start a new game
    engine.start_new_game(player_name="HeadlessNarrative")

    # Learn the spell for deterministic gating
    engine.process_command(f"//learn_spell {ns.spell}")

    # Natural language non-combat casting attempt
    user_text = f"I cast {ns.spell.replace('_',' ')} on myself."
    engine.process_input(user_text)

    QTimer.singleShot(int(ns.timeout), app.quit)
    app.exec()

    print("\n===== Transcript Dump (LLM) =====")
    import sys as _sys
    _sys.stdout.write(listener.dump_transcript() + "\n")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
