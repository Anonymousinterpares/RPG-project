#!/usr/bin/env python3
"""
Validate effect atom samples against the effect_atoms JSON Schema.
"""
import json
import os
import sys

try:
    import jsonschema
except ImportError as e:
    print("ERROR: jsonschema not installed. Install with: python -m pip install jsonschema", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, 'config', 'gameplay', 'effect_atoms.schema.json')
SAMPLES_PATH = os.path.join(ROOT, 'config', 'gameplay', 'examples', 'effect_atoms_samples.json')


def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    schema = load_json(SCHEMA_PATH)
    samples = load_json(SAMPLES_PATH)

    # Validate the entire array (EffectSequence)
    jsonschema.validate(instance=samples, schema=schema)

    # Validate each atom individually as well (EffectAtom)
    for idx, atom in enumerate(samples):
        try:
            jsonschema.validate(instance=atom, schema=schema)
        except jsonschema.ValidationError as ve:
            print(f"Per-atom validation failed at index {idx}: {ve}")
            raise

    print("OK: effect_atoms_samples.json validated against effect_atoms.schema.json")


if __name__ == '__main__':
    main()
