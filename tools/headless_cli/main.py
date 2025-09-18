#!/usr/bin/env python3
"""
Headless CLI to run the RPG engine without GUI, suitable for local testing and CI.

Usage examples (PowerShell):
  # Quick run with defaults
  python tools\headless_cli\main.py --commands "/look" "/inventory" "/help" --timeout 4000

  # Specify a seed and character basics
  python tools\headless_cli\main.py --seed 123 --player-name Alice --race Elf --path Ranger --background Scout --commands "/look" "/help"

Outputs a transcript to stdout and saves a JSON log if --out is provided.
"""
import argparse
import json
import os
import sys
from typing import List, Dict, Any

from PySide6.QtCore import QCoreApplication

# Local imports
from core.testing.scenario_runner import run_scenario


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the RPG headlessly.")
    p.add_argument("--seed", type=int, default=42, help="Random seed for determinism")
    p.add_argument("--llm", action="store_true", help="Enable LLM (default disabled)")
    p.add_argument("--timeout", type=int, default=5000, help="Timeout to stop the run (ms)")

    p.add_argument("--player-name", default="Player")
    p.add_argument("--race", default="Human")
    p.add_argument("--path", default="Wanderer")
    p.add_argument("--background", default="Commoner")
    p.add_argument("--sex", default="Male")
    p.add_argument("--origin-id", default=None)

    p.add_argument("--commands", nargs="*", default=["/help"], help="Commands to send in order")
    p.add_argument("--out", default=None, help="Optional path to write a JSON log of events")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    ns = parse_args(argv)
    params: Dict[str, Any] = {
        "seed": ns.seed,
        "llm": bool(ns.llm),
        "timeout_ms": ns.timeout,
        "player_name": ns.__dict__.get("player_name"),
        "race": ns.race,
        "path": ns.path,
        "background": ns.background,
        "sex": ns.sex,
        "origin_id": ns.origin_id,
    }

    result = run_scenario(params, ns.commands)

    # Print transcript to stdout
    sys.stdout.write(result["transcript"] + "\n")

    if ns.out:
        try:
            with open(ns.out, "w", encoding="utf-8") as f:
                json.dump({"lines": result["lines"], "events": result["events"]}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            sys.stderr.write(f"Failed to write log to {ns.out}: {e}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

