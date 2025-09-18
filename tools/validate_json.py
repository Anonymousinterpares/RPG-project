#!/usr/bin/env python3
import sys
import json
from pathlib import Path

USAGE = "Usage: validate_json.py <schema_path> <json_path>"


def main() -> int:
    if len(sys.argv) != 3:
        print(USAGE)
        return 2
    schema_path = Path(sys.argv[1])
    json_path = Path(sys.argv[2])
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: Failed to read files: {e}")
        return 2

    try:
        from jsonschema import Draft202012Validator
    except Exception as e:
        print(f"MISSING_JSONSCHEMA: {e}")
        print("Tip: Install with 'py -m pip install jsonschema' or 'python -m pip install jsonschema'.")
        return 3

    try:
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if errors:
            print("INVALID: \n" + "\n".join(f"- {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors))
            return 1
        print("VALID")
        return 0
    except Exception as e:
        print(f"ERROR: Validation exception: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

