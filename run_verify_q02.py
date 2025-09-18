#!/usr/bin/env python3
"""
Top-level launcher to verify TEST_Q02 auto-completion after wolf defeat.

Example:
  python run_verify_q02.py --file wolf_alpha.json --llm --timeout 45000
"""
import sys
from tools.headless_cli.verify_q02_autocomplete import main as verify_main

if __name__ == "__main__":
    raise SystemExit(verify_main(sys.argv[1:]))

