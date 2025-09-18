#!/usr/bin/env python3
"""
Top-level launcher to headlessly load a save and try continuing combat.

Example:
  python run_headless_load.py --file wolf_alpha.json --actions attack attack --timeout 12000
"""
import sys
from tools.headless_cli.run_loaded import main as run_loaded_main

if __name__ == "__main__":
    raise SystemExit(run_loaded_main(sys.argv[1:]))

