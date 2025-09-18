#!/usr/bin/env python3
"""
Top-level launcher for headless runs.

Examples (PowerShell):
  python run_headless.py --commands "look" "inventory" --timeout 4000
  python run_headless.py --seed 123 --player-name Alice --race Elf --path Ranger --commands "look" "help"
"""
import sys
from tools.headless_cli.main import main as headless_main

if __name__ == "__main__":
    raise SystemExit(headless_main(sys.argv[1:]))

