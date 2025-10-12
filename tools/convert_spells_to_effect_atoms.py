#!/usr/bin/env python3
"""
Convert legacy spell 'effects' to effect_atoms across magic_systems.json (and optionally other catalogs).

Usage (PowerShell):
  # Dry-run (no writes), produces a report JSON next to the file
  python tools\convert_spells_to_effect_atoms.py --dry-run

  # Apply changes in-place after reviewing the report
  python tools\convert_spells_to_effect_atoms.py --apply

Behavior:
- For each spell with legacy 'effects', produces 'effect_atoms' using mapping rules.
- Leaves legacy 'effects' intact unless --apply and --remove-legacy-effects is set.
- Validates produced atoms against config/gameplay/effect_atoms.schema.json.
- Writes a conversion_report.json adjacent to magic_systems.json in dry-run and apply modes.

Mapping rules (initial):
- damage -> {type: damage, selector: by role (offensive->enemy else ally/self), magnitude: dice or flat, damage_type: arcane if unknown}
- healing -> {type: heal, selector: ally/self (range 'self' => self), magnitude: dice or flat}
- stat_modification -> {type: buff, selector by role, modifiers: [{stat, value}] with duration if >0}
- status_effect -> {type: status_apply, status: <name>, duration if >0}
- All atoms get source_id=<spell.id> and tags from spell.tags when present.

Notes:
- Selector logic prefers spell.combat_role; range 'self' forces selector='self'.
- Unknown effect types are logged and skipped.
- Stat names are passed through; engine will resolve via registry at runtime.
"""
from __future__ import annotations

import json
import os
import argparse
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)  # up from tools/

MAGIC_PATH = os.path.join(PROJECT_ROOT, 'config', 'world', 'base', 'magic_systems.json')
SCHEMA_PATH = os.path.join(PROJECT_ROOT, 'config', 'gameplay', 'effect_atoms.schema.json')
REPORT_PATH = os.path.join(PROJECT_ROOT, 'config', 'world', 'base', 'conversion_report.json')


def load_json_abspath(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_abspath(path: str, data: Any) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _infer_selector(spell: Dict[str, Any], effect_entry: Dict[str, Any]) -> str:
    # If explicit target on spell says 'self', honor that
    target_decl = (spell.get('range') or '').strip().lower()
    if target_decl == 'self':
        return 'self'

    # effect entry target_type 'caster' means self
    ttype = (effect_entry.get('target_type') or '').strip().lower()
    if ttype in ('caster', 'self'):
        return 'self'

    # role-based defaulting
    role = (spell.get('combat_role') or 'offensive').strip().lower()
    if role == 'offensive':
        return 'enemy'
    # defensive & utility -> ally by default (self allowed by engine targeting policies)
    return 'ally'


def _magnitude_from(effect_entry: Dict[str, Any]) -> Dict[str, Any]:
    dice = (effect_entry.get('dice_notation') or '').strip()
    if dice:
        return {'dice': dice}
    try:
        val = float(effect_entry.get('value', 0))
        return {'flat': val}
    except Exception:
        return {'flat': 0}


def _to_atom(spell: Dict[str, Any], eff: Dict[str, Any]) -> Dict[str, Any] | None:
    etype = (eff.get('effect_type') or '').strip().lower()
    selector = _infer_selector(spell, eff)
    base = {
        'selector': selector,
        'magnitude': _magnitude_from(eff),
        'source_id': spell.get('id'),
    }
    # carry tags if any
    tags = spell.get('tags')
    if isinstance(tags, list):
        base['tags'] = [str(t) for t in tags]

    # duration
    try:
        dur = int(eff.get('duration', 0))
    except Exception:
        dur = 0
    if dur and dur > 0:
        base['duration'] = {'unit': 'turns', 'value': int(dur)}

    if etype == 'damage':
        atom = {'type': 'damage', **base}
        # attempt to infer damage type from tags or default
        atom['damage_type'] = 'arcane'
        return atom
    elif etype in ('healing', 'heal'):
        return {'type': 'heal', **base}
    elif etype in ('stat_modification', 'buff', 'debuff'):
        # map to buff with one modifier; normalize stat id to SCHEMA pattern [A-Z_]+
        raw_stat = (eff.get('stat_affected') or '').strip()
        stat = raw_stat.upper().replace(' ', '_').replace('-', '_') if raw_stat else 'UNKNOWN'
        try:
            val = float(eff.get('value', 0))
        except Exception:
            val = 0.0
        atom = {'type': 'buff', **base, 'modifiers': [{'stat': stat, 'value': val}]}
        return atom
    elif etype in ('status_effect', 'status_apply'):
        status_name = (eff.get('status_effect') or eff.get('status') or '').strip() or 'Status'
        # status_apply requires duration in schema; default to 1 turn if missing/zero
        if 'duration' not in base:
            base['duration'] = {'unit': 'turns', 'value': 1}
        atom = {'type': 'status_apply', **base, 'status': status_name}
        return atom
    elif etype in ('cleanse', 'status_remove'):
        atom = {'type': 'cleanse', **base}
        return atom
    else:
        return None


def convert_spells(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (new_data, report). Leaves legacy effects in place.
    report contains per-spell atom counts and any skipped effects.
    """
    systems = data.get('magic_systems') or data
    report: Dict[str, Any] = {'converted': [], 'skipped': []}

    def _iter_spells(systems_obj: Any):
        if isinstance(systems_obj, dict):
            for sys_entry in systems_obj.values():
                if not isinstance(sys_entry, dict):
                    continue
                spells = sys_entry.get('spells')
                if isinstance(spells, dict):
                    for sp in spells.values():
                        yield sp
                elif isinstance(spells, list):
                    for sp in spells:
                        yield sp
        elif isinstance(systems_obj, list):
            for sys_entry in systems_obj:
                if not isinstance(sys_entry, dict):
                    continue
                spells = sys_entry.get('spells')
                if isinstance(spells, dict):
                    for sp in spells.values():
                        yield sp
                elif isinstance(spells, list):
                    for sp in spells:
                        yield sp

    for sp in _iter_spells(systems):
        if not isinstance(sp, dict):
            continue
        sid = sp.get('id') or sp.get('name')
        legacy = sp.get('effects')
        if not isinstance(legacy, list) or not legacy:
            continue
        atoms: List[Dict[str, Any]] = []
        skipped: List[str] = []
        for eff in legacy:
            atom = _to_atom(sp, eff)
            if atom:
                atoms.append(atom)
            else:
                skipped.append((eff.get('effect_type') or 'unknown'))
        if atoms:
            sp['effect_atoms'] = atoms
            report['converted'].append({'spell_id': sid, 'atoms': len(atoms), 'skipped': skipped})
        else:
            report['skipped'].append({'spell_id': sid, 'reason': 'no mappable effects', 'effect_types': skipped})

    return data, report


def validate_atoms(new_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    # Basic schema validation using jsonschema if available
    errors: List[str] = []
    try:
        import jsonschema  # type: ignore
    except Exception:
        # If jsonschema not installed, perform minimal structural checks
        for sys in (new_data.get('magic_systems') or {}).values():
            spells = sys.get('spells', {})
            if isinstance(spells, dict):
                for sp in spells.values():
                    atoms = sp.get('effect_atoms')
                    if atoms is None:
                        continue
                    if not isinstance(atoms, list):
                        errors.append(f"spell {sp.get('id')}: effect_atoms not a list")
                        continue
                    for i, a in enumerate(atoms):
                        if not isinstance(a, dict):
                            errors.append(f"spell {sp.get('id')}: atom {i} not object")
                            continue
                        if 'type' not in a or 'selector' not in a or 'magnitude' not in a:
                            errors.append(f"spell {sp.get('id')}: atom {i} missing required fields")
        return (len(errors) == 0, errors)

    try:
        schema = load_json_abspath(SCHEMA_PATH)
    except Exception as e:
        return False, [f"Failed to load schema: {e}"]

    # Build a bag of all atoms and validate each against schema "oneOf" via per-atom validation
    try:
        validator = jsonschema.Draft7Validator(schema)
    except Exception:
        # Fallback minimal check
        return validate_atoms.__wrapped__(new_data)  # type: ignore

    for sys in (new_data.get('magic_systems') or {}).values():
        spells = sys.get('spells', {})
        if not isinstance(spells, dict):
            continue
        for sp in spells.values():
            atoms = sp.get('effect_atoms')
            if atoms is None:
                continue
            if not isinstance(atoms, list):
                errors.append(f"spell {sp.get('id')}: effect_atoms not a list")
                continue
            for i, a in enumerate(atoms):
                errs = sorted(validator.iter_errors(a), key=lambda e: e.path)
                if errs:
                    for e in errs:
                        errors.append(f"spell {sp.get('id')} atom {i}: {e.message}")
    return (len(errors) == 0, errors)


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description='Convert legacy spell effects to effect_atoms')
    ap.add_argument('--apply', action='store_true', help='Apply changes to magic_systems.json')
    ap.add_argument('--remove-legacy-effects', action='store_true', help='Remove legacy effects after applying')
    ap.add_argument('--dry-run', action='store_true', help='Dry-run only (default)')
    ns = ap.parse_args(argv)

    if not os.path.exists(MAGIC_PATH):
        print(f"ERROR: magic_systems.json not found at {MAGIC_PATH}")
        return 1

    data = load_json_abspath(MAGIC_PATH)
    new_data, report = convert_spells(data)

    ok, errors = validate_atoms(new_data)
    report['validation_ok'] = ok
    report['validation_errors'] = errors

    save_json_abspath(REPORT_PATH, report)
    print(f"Report written to {REPORT_PATH}")

    if not ok:
        print("Validation failed. Aborting apply.")
        return 2

    if ns.apply:
        if ns.remove_legacy_effects:
            # Remove legacy effects where effect_atoms present
            systems = new_data.get('magic_systems') or new_data
            for sys_entry in systems.values():
                spells = sys_entry.get('spells', {})
                for sp in spells.values():
                    if 'effect_atoms' in sp and 'effects' in sp:
                        sp.pop('effects', None)
        save_json_abspath(MAGIC_PATH, new_data)
        print(f"Applied changes to {MAGIC_PATH}")
    else:
        print("Dry run only. Use --apply to write changes.")

    return 0


if __name__ == '__main__':
    import sys
    raise SystemExit(main(sys.argv[1:]))
