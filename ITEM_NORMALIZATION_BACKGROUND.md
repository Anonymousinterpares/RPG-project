# Item Normalization Background and Handoff Guide

Purpose
- Equip another LLM/dev to continue the item normalization effort in a dedicated branch without re-deriving context.
- Summarize current state, files, commands, report format, and recommended enhancements.

Scope of normalization
- Normalize item stats and related fields in config/items/** to canonical engine stat IDs using the unified stat registry.
- Validate dice_roll_effects effect_type against canonical damage types.
- Produce actionable reports (dry-run by default) to drive alias additions or source data corrections.

Key files and modules (entry points and references)
- Script (normalization):
  - scripts/migrations/normalize_items_aliases.py
- Logs and reports:
  - logs/item_normalization_report.json (dry-run and apply modes)
- Canonical registries (read-only from core via get_config() in runtime, loaded directly by script):
  - config/character/stat_registry.json (unified registry with aliases and supported flags)
  - config/gameplay/canonical_lists.json (damage_types, status_conditions)
- Engine configuration loader (informs how runtime sees config):
  - core/base/config.py (maps domains: stat_registry, canonical_lists)
- Alias resolver and engine integration (runtime Resolution only; for context):
  - core/stats/registry.py (normalize_to_canonical_id, resolve_stat_enum, is_supported)
  - core/stats/stats_manager.py (integrated alias resolution in get_stat/setters/equipment sync)
- Items edited by configurator (targets of normalization):
  - config/items/**/*.json (script recursively scans, skipping any directory named exactly "backup")

What’s already done (baseline)
- The script scans config/items recursively, skipping any subdirectory named 'backup'.
- Dry-run writes a JSON report to logs/item_normalization_report.json (no file edits).
- Unknown stats/effect types are left untouched and listed in report counts; aliases must be added or source files corrected later.

How to run (Windows PowerShell)
- Dry-run (recommended first):
  - python "D:\coding\RPG project\latest version\scripts\migrations\normalize_items_aliases.py" --report "D:\coding\RPG project\latest version\logs\item_normalization_report.json"
- Apply (only after reviewing mappings and taking a VCS snapshot):
  - python "D:\coding\RPG project\latest version\scripts\migrations\normalize_items_aliases.py" --apply --report "D:\coding\RPG project\latest version\logs\item_normalization_report.json"

Report (JSON) structure (current)
- Top-level fields:
  - root: project root used for the scan
  - files_scanned: integer
  - files: array of per-file records with:
    - path (string)
    - entries (stat entries encountered in that file)
    - renamed (count of name normalizations performed in-memory)
    - unknown (count of names that could not be resolved)
    - unsupported (count of names resolved but marked unsupported in registry)
    - unknown_effect_types (count of dice effect types not in canonical list)
    - changed (boolean; only true if values were modified in-memory; persists only when --apply)
  - summary: aggregated counts across all files

Example (shortened):
- files: [{
  - path: ".../config/items/base_weapons.json",
  - entries: 8,
  - renamed: 5,
  - unknown: 1,
  - unsupported: 0,
  - unknown_effect_types: 0,
  - changed: true
}]

Important runtime context (for accurate decisions)
- Unified stat registry (config/character/stat_registry.json) contains a single list of stats with:
  - key (lowercase canonical id), category (primary/derived), label, aliases (lowercase synonyms), supported (bool)
- At runtime, engine converts aliases and strings to enums via core/stats/registry.py
  - resolve_stat_enum(name) returns StatType/DerivedStatType or None
  - is_supported(name) checks that canonical resolves and is marked supported
- Script directly imports registry helpers to inform normalization (outside engine runtime)

Known pain points this effort addresses
- Typos and inconsistent item stat names (e.g., strenght, nouse)
- Non-canonical effect types in dice_roll_effects
- Items in backup folders should be ignored

Your additional idea (requested enhancement)
Goal: Extend the report to list all unknown values with exact locations, making it easy to fix.

Implementation recommendation (two safe options)
- Option A (Structured JSON-only; machine-friendly):
  - Add to report:
    - unknown_stats_detail: [
      { "path": "<file>", "item_id": "<id-or-null>", "json_path": "/stats/3/name", "raw_value": "strenght", "note": "unresolved" }
    ]
    - unknown_effect_types_detail: [
      { "path": "<file>", "item_id": "<id-or-null>", "json_path": "/dice_roll_effects/0/effect_type", "raw_value": "sonic", "note": "non_canonical_effect_type" }
    ]
  - Pros: remains valid JSON; downstream tooling can parse it.
  - Cons: won’t be literally “below current content”; appended as new fields.

- Option B (Companion human-readable appendix; avoids breaking JSON):
  - Keep logs/item_normalization_report.json as-is.
  - Also write logs/item_normalization_report.appendix.txt with a human-friendly listing (sorted, grouped), for example:
    - Unknown Stats:
      - strenght -> config/items/base_weapons.json (id: longsword), at /stats/2/name
      - attack_sped -> config/items/origin_items.json (id: novice_axe), at /stats/0/name
    - Unknown Effect Types:
      - sonic -> config/items/base_weapons.json (id: thunder_blade), at /dice_roll_effects/1/effect_type
  - Pros: readable, won’t break JSON consumers.
  - Cons: two files instead of one.

Note on “append below JSON content”
- Appending non-JSON text to a .json file would invalidate parsers. Prefer Option A (pure JSON fields) or Option B (companion .txt appendix). If a single file is mandatory, consider switching the report to .md or .txt entirely.

Data captured per unknown
- path: absolute file path
- item_id: if present in the item payload (id field)
- json_path: JSON Pointer-style location (e.g., /stats/2/name) to support precise edits
- raw_value: the unrecognized string
- note: why it’s listed (unresolved stat, unsupported stat, non-canonical effect_type)

Suggested workflow for the separate branch
1) Create branch
   - git checkout -b chore/items-normalization-report-enhancements
2) Add enhancement (Option A or B above) to scripts/migrations/normalize_items_aliases.py
3) Re-run dry-run, inspect:
   - logs/item_normalization_report.json
   - logs/item_normalization_report.appendix.txt (if using Option B)
4) Aggregate unknowns to propose alias candidates in config/character/stat_registry.json
   - Add aliases under the correct canonical stat; set supported: true when they map to engine enums
5) Re-run dry-run; confirm unknown counts drop; iterate
6) When confident, run with --apply and commit changes to config/items/**
7) Open PR with the report(s) and mapping rationale

Quick reference: common locations
- Project root: D:\coding\RPG project\latest version
- Items directory: config/items\ (recurse)
- Script: scripts/migrations/normalize_items_aliases.py
- Unified registry: config/character/stat_registry.json
- Damage types/canon: config/gameplay/canonical_lists.json
- Report output: logs/item_normalization_report.json

Edge cases and tips
- Items may be lists or nested under keys (items, list) — script already handles common variants.
- Some items may lack id; include item name if present, else null in unknowns_detail.
- Consider adding a --include-backups flag if you need to audit backups intentionally (default remains excluded).
- Keep report stable between runs for easy diffing.

Acceptance criteria for this branch
- Running dry-run produces the standard report plus an explicit listing of unknowns with locations (Option A JSON fields or Option B appendix file).
- No changes to source item JSONs in dry-run.
- Script continues to skip any directory named exactly ‘backup’.
- Documentation in this file points future contributors to all relevant paths and conventions.

Appendix: JSON shape for Option A (proposed)
{
  "root": "...",
  "files_scanned": 5,
  "files": [ ... ],
  "summary": { ... },
  "unknown_stats_detail": [
    {
      "path": "D:/coding/RPG project/latest version/config/items/base_weapons.json",
      "item_id": "longsword",
      "json_path": "/stats/2/name",
      "raw_value": "strenght",
      "note": "unresolved"
    }
  ],
  "unknown_effect_types_detail": [
    {
      "path": "D:/coding/RPG project/latest version/config/items/base_weapons.json",
      "item_id": "thunder_blade",
      "json_path": "/dice_roll_effects/1/effect_type",
      "raw_value": "sonic",
      "note": "non_canonical_effect_type"
    }
  ]
}

Ownership and contact
- This background reflects the current implementation status and is intended for handoff.
- If additional context is needed, inspect the files listed above; they are the canonical sources of truth.
