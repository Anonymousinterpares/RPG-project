# Mechanics Implementation Checklist (Resistances, AP/Speed, Crits, Accuracy/Dodge, Consumables, Skills, Requirements)

Guiding principles
- Core does not call UI. Use CombatOutputOrchestrator + DisplayEvent for feedback.
- Use singleton getters and GameConfig for data.
- Keep data-driven: new knobs go to config and JSON schemas; registry governs stat names.
- Prefer additive changes and feature flags; avoid breaking existing flows.

Status update (Phase 0 data normalization)
- Dry-run re-executed; unknown_effect_types now 0; remaining unknown stats are intentional (consumables, typed resistances, skill-like labels, requirements).
- Applied normalization with --apply; items updated to canonical stat names (total_renamed=19 across 5 files), ensuring equipment modifiers map cleanly to engine enums.
- Proceeding to next step: Typed Resistances foundation (dice + percent).

Scope of this document
- 2) Typed magical resistances (dice-based with tiers)
- 3) Attack speed via Action Points (AP) model
- 4) Critical chance (classic crit% with multiplier)
- 5) Accuracy & Dodge (reach/range/noise deferred)
- 6) Consumable effects and durations (turns/minutes)
- 7) Skills (plan only now)
- 8) Item stat requirements

---

## 2) Typed Magical Resistances — Dice + Percent Tiers

Data model (items/statuses/config)
- Items: move resistances under custom_properties.typed_resistances; support mixed entries per type:
  - Example (item):
    - custom_properties.typed_resistances: { "fire": { "dice": "1d6" }, "cold": { "percent": 20 }, "poison": { "percent": 10, "dice": "1d4" } }
- Status effects (from spells): use effect atoms of type "status_apply" with custom_data to feed StatsManager contributions for typed resistances.
- Canonical lists: extend config/gameplay/canonical_lists.json
  - Add resistance_tiers: { "minor": {"min":1, "max":24}, "medium": {"min":25, "max":49}, "major": {"min":50, "max":74}, "supreme": {"min":75, "max":90} }
  - Add combat.defense.magical.resistance_cap default 90 (already read by StatsManager.get_resistance_percent); align with tiers.
  - Optional: resistance_presets mapping tier→default dice (e.g., minor: 1d4, medium: 1d6, major: 1d8, supreme: 1d10), for editor quick-pick.

Engine integration (StatsManager)
- Status: IMPLEMENTED
  - Percent path: _typed_resist_contrib_by_source + get_resistance_percent (cap via combat.defense.magical.resistance_cap)
  - Dice path: _typed_resist_dice_by_source + set_resistance_dice_contribution + get_resistance_dice_pool
- Equipment sync: IMPLEMENTED (percent)
  - InventoryManager._sync_stats_modifiers reads item.custom_properties.typed_resistances and calls set_resistance_contribution per slot
  - Next: extend to support dice entries on items if/when authoring adopts dice for resistances
- Status effects: PLANNED
  - When status_apply atoms carry typed resistance contributions, call StatsManager.set_resistance_* with a stable status source_id on add/remove

Engine integration (EffectsEngine)
- Status: IMPLEMENTED
  - _apply_damage_to_target now rolls typed resistance dice (once per notation) before percent mitigation
  - Breakdown includes typed_resist_dice_sum, typed_resist_dice_rolls, after_dice
- Logging via orchestrator (for melee in action_handlers) remains; effects engine returns breakdown for upstream display if desired.

World Configurator & Validation
- Editor widgets for typed_resistances per type with two modes (dice/percent) and optional tier quick-pick.
- Validation against canonical damage types; show effective cap.
- For statuses: UI to add a resistance buff that compiles to a status_apply atom carrying custom_data for StatsManager contributions.

QA & Telemetry
- Unit coverage for: mixed dice+percent stacking; cap enforcement; empty dice list; multi-type damage split.
- Log samples in tests to ensure breakdown formatting is stable.

Cutover & Safety
- Backward-compatible: percent-only items already work; dice path is additive (pre-pct); disabled when no dice contributions present.

---

## 3) Attack Speed via Action Points (AP)

Data and config
- Add config keys (config/game/game_config.json or combat section used by engine):
  - combat.ap: { base_ap: 1.0, min_action_cost: 0.5, costs: { ATTACK: 1.0, SPELL: 1.0, DEFEND: 0.5, MOVE: 0.5, ITEM: 0.5 } }
  - combat.ap.rounding: "floor" (how to round residual AP when turn ends)
- Items may adjust AP costs via custom_properties.action_cost_modifiers: { "ATTACK": -0.25 } or via a generic "attack_speed" stat mapped to an AP cost multiplier.

Engine touchpoints (current code references)
- CombatManager (core/combat/combat_manager.py)
  - Introduce per-turn AP pool for the active entity (ephemeral): cm._ap_pool[entity_id] = float
  - On STARTING_ROUND / when setting first actor: initialize AP = base_ap (+ buffs) for that entity
  - In perform_action flow (after costs are validated/applied), deduct AP based on action type and modifiers
  - If AP ≥ min_action_cost after an action: set current_step back to AWAITING_PLAYER_INPUT (player) or AWAITING_NPC_INTENT (NPC) instead of ADVANCING_TURN; otherwise proceed to APPLYING_STATUS_EFFECTS/ADVANCING_TURN
  - Ensure AP resets at the start of the entity’s next turn; carryover can be disallowed (recommended) or limited by a small cap if enabled later
- Action handlers (core/combat/action_handlers.py)
  - No direct AP knowledge; only report action type used; CM calculates AP costs
- CombatEntity (core/combat/combat_entity.py)
  - Optional ephemeral fields: current_ap/max_ap for display only; do not persist
- Orchestrator events
  - Queue UI bar updates for AP similar to stamina/mana (AP bar optional)

AP cost modifiers (attack speed)
- Derive effective cost = base_cost × (1 + sum(flat_multipliers)) + sum(flat_offsets)
  - From items: custom_properties.action_cost_modifiers
  - From statuses: via modifiers or custom_data on status that CM reads when computing cost
- Support a “free follow-up” trigger as an optional alternative: if effective cost < 1 and AP rounding leaves ≥ min_action_cost, the player can chain another action.

AI/NPC
- NPC turn loop mirrors player: after action, if AP remains, ask agent for another intent (cap actions per turn to avoid stalls, e.g., max 2–3).

World Configurator
- Per item: optional action_cost_modifiers editor
- Global AP settings: read-only reference for designers

QA
- Tests for: multi-action turns; AP floor; interactions with stamina/mana (both must pass); end-of-turn transitions.

---

## 4) Critical Chance (Classic crit% + multiplier)

Data
- stat_registry: add/enable as supported: { key: "crit_chance", category: "derived", label: "Critical Chance", aliases: ["crit"], supported: true }, { key: "crit_multiplier", category: "derived", label: "Critical Multiplier", aliases: ["crit_mult"], supported: true }
- Items/statuses can modify these via modifiers (flat percent for chance; flat multiplier, e.g., 1.5)
- Config defaults: combat.crits: { base_chance_percent: 5, base_multiplier: 1.5, allow_natural_20_override: true }

Mechanics (attack handler & effects engine damage path)
- Determine crit:
  - If natural-20 logic marks critical (existing), it’s always a crit (unless config disables)
  - Else, after a successful hit, roll against effective crit_chance (base + modifiers, clamp to reasonable max, e.g., 60%)
- On crit:
  - Use multiplier on raw damage before mitigation OR roll extra damage dice (current code duplicates dice on crit; maintain that as a baseline and then treat multiplier as a final modifier)
  - Recommended: keep “roll dice twice” as natural-20 effect; for chance-based crits, use multiplier only to maintain clarity
- Logging
  - Explicit “Critical Hit!” line plus multiplier shown in raw→mitigation lines

World Configurator
- Add fields to items/status editors for crit_chance% and crit_multiplier

QA
- Validate interaction with typed resistances and shields; ensure order: raw → (crit) → shields → flat → typed dice → typed % → final

---

## 5) Accuracy & Dodge (reach/range/noise deferred)

Accuracy
- Continue to use MELEE_ATTACK/RANGED_ATTACK vs DEFENSE as primary hit math
- “Accuracy” improvements are modelled as modifiers to the relevant derived stats (no new stat):
  - Items/statuses add modifiers to MELEE_ATTACK / RANGED_ATTACK (flat or % via ModifierManager)

Dodge
- Model as modifiers to DEFENSE or as temporary statuses (e.g., “Dodge” +X DEFENSE for N turns)
- Avoid a permanent "dodge" core stat to prevent bloat; use statuses and modifiers

Editor
- Provide simple modifier rows targeting existing derived stats

---

## 6) Consumable Effects & Durations

Data schema
- Items gain use_effects: [] (effect atoms). Examples:
  - Heal potion: { type: "resource_change", resource: "HEALTH", magnitude: { dice: "2d4+2" } }
  - Mana potion: { type: "resource_change", resource: "MANA", magnitude: { flat: 20 } }
  - Antidote: { type: "status_remove", status: "Poisoned" }
  - Bandage: two atoms (resource_change+status_remove)
  - Buff potion: { type: "status_apply", status: "Strength Buff", duration: { unit: "minutes", value: 10 }, modifiers: [...] }
- Duration semantics
  - In combat: unit="turns"
  - Out of combat: unit="minutes"; persisted via StatusEffect.custom_data and purged via time advancement

Engine
- EffectsEngine already supports these atoms; extend item use path to dispatch atoms to effects engine
- Ensure world time controller decrements minute-based effects; already supported pattern via StatsManager status_effect_manager (advance minutes / purge)

World Configurator
- Add Use Effects editor with schema-validated fields; presets for common potions

Migration
- Replace legacy “healing/mana_restore/bleed_cure…” stats on consumables with use_effects; keep a migration script; validators warn on legacy fields

---

## 7) Skills (plan only for now)

Data
- config/character/skills.json: list of skills { id, label, primary_stat, trained_only, description, tags }
- stat_registry: do not add each skill; skills live in their own catalog

Engine
- SkillManager (read-only for now) to expose skill metadata
- StatsManager.perform_skill_check already supports skill_name path; wire to SkillManager for proficiency/bonuses when implemented

World Configurator
- Add Skills catalog editor and per-item/per-status skill modifiers (as modifiers to checks later)

---

## 8) Item Stat Requirements

Data
- Items: requirements: [ { "stat": "STRENGTH", "min": 15 }, { "stat": "DEXTERITY", "min": 12 } ]

Engine
- Inventory/equip gating: on equip, verify all requirements; if failed, block equip with a SYSTEM_MESSAGE and UI hint
- Combat gating (mechanical stage 2): if action uses an item not meeting requirements, block action with SYSTEM_MESSAGE and do not consume turn (keep at AWAITING_PLAYER_INPUT)
- Developer mode: allow bypass per settings

World Configurator
- Requirements editor (multi-row): stat picker from registry + min value; validation on save

---

## Cross-cutting Work Plan & Order of Operations

1) Finish Phase 0 data normalization
   - Re-run normalizer (dry) → confirm unknowns=0 except intentional unsupported
   - Run with --apply; commit item files
2) Typed resistances foundation
   - Add resistance_tiers + cap to canonical_lists.json
   - Update items to use custom_properties.typed_resistances consistently (percent/dice)
   - Extend StatsManager (dice contributions) + EffectsEngine pipeline step; logs
   - Editor widgets + validators
3) AP model + attack speed
   - Config: combat.ap
   - CombatManager AP pool + turn loop changes; AP bar events
   - Item/status cost modifiers path
   - NPC multi-action loop guard
4) Criticals
   - Registry enable crit_chance/crit_multiplier; defaults in config
   - Attack handler integration; logs; editor fields
5) Consumables
   - Add use_effects; migrate legacy consumable stats; validators
6) Requirements
   - Add requirements field; equip & action gating; UI messages; editor
7) Skills (catalog + manager) — placeholder

Feature flags (optional)
- combat.defense.typed_resist_dice_enabled (true when ready)
- combat.ap.enabled (default off until UI/AI done)
- combat.crits.enabled (default on; baseline already present via natural 20)

Acceptance criteria (per feature)
- Typed resistances: full breakdown logs; mixed percent+dice; cap enforced; editor validation
- AP: multiple actions per turn possible; stamina/mana gates still respected; UI updates; NPC loop capped
- Crits: post-hit crit% works; multiplier applied; clear logs; maintains natural-20 behavior
- Consumables: effect atoms applied; durations respected in/out of combat; legacy fields removed or warned
- Requirements: clean gating with clear messages; configurator edits persist
