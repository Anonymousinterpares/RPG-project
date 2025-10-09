What exists today in your codebase
•  Item effects are defined in items as dice_roll_effects with an effect_type string
◦  Example values in config/items:
▪  physical_slashing_damage (e.g., swords)
▪  physical_piercing_damage (e.g., daggers, bows)
•  The backend doesn’t currently use effect_type in combat
◦  AttackAction and SpellAction compute damage with dice_notation and apply:
▪  Physical: flat DAMAGE_REDUCTION (DerivedStatType)
▪  Magic: flat MAGIC_DEFENSE
◦  They output text like “Physical” or “magic damage,” but do not differentiate slashing vs piercing vs bludgeoning.
•  There is a curated list of damage types already in config/combat/combat_config.json
◦  damage.types: ["slashing", "piercing", "bludgeoning", "fire", "cold", "lightning", "poison", "acid", "arcane"]
◦  This is the right authoritative list to standardize against.
•  Stats framework
◦  Derived stats include DAMAGE_REDUCTION, MAGIC_DEFENSE, but no typed resistances.
◦  Items freely add custom stats (e.g., fire_resistance, magic_resistance_minor), but these are not standardized or consumed in core combat calculations today.
•  World Configurator UI
◦  DiceRollEffectDialog takes effect_type as free text; not a dropdown or validated against a list.
◦  The assistant references do not yet include “effect_types” as a choice list, so LLM can invent arbitrary values.

Gaps and resulting issues
•  No standard effect_type vocabulary. Items use strings like physical_slashing_damage, but the canonical list in combat_config suggests single tokens like slashing.
•  Combat doesn’t consider effect_type for mitigation or narration; everything is Physical or magic.
•  Resistances are not standardized; some items define ad hoc resistance-ish stats that aren’t consumed systematically.
•  UI doesn’t guide authors (no dropdown), and the LLM isn’t grounded on allowed types.

Proposal: a lean, flavorful damage/effect type system
•  Controlled vocabulary
◦  Adopt the list already in config/combat/combat_config.json:
▪  Physical: slashing, piercing, bludgeoning
▪  Elemental: fire, cold, lightning, acid
▪  Other: poison, arcane
◦  Benefits: short, readable, already present, easy to understand, extensible later.
◦  Normalization: effect_type on items should be one of these exact strings. For existing items:
▪  physical_slashing_damage → slashing
▪  physical_piercing_damage → piercing
•  Backend mitigation model (simple, consistent)
◦  Keep what you have and add one layer for per-type resistance:
▪  Compute raw damage (dice + stat modifier) as today.
▪  Apply flat reduction if applicable:
▪  Physical: flat DAMAGE_REDUCTION first.
▪  Magic: flat MAGIC_DEFENSE first.
▪  Apply typed resistance as a percentage:
▪  final_damage = max(0, floor((raw - flat) × (1 - resistance[type]/100)))
▪  Cap resistances as per combat_config.defense.resistance_cap (e.g., 75%).
◦  Resistances storage options (pick one):
▪  A generic typed map on the entity: resistances = {"slashing": 10, "fire": 5, ...}. Items/armor can add to this via modifiers.
▪  Or standardized derived stats (if you prefer the enum route later): RESIST_SLASHING, RESIST_FIRE, etc. To stay lean, the generic map is simpler and more extensible.
•  Armor-type interactions that stay simple
◦  Let armor impart small ±% modifiers to relevant physical types:
▪  Plate: +10% vs slashing, -10% vs bludgeoning, +0% vs piercing.
▪  Chain: +10% vs slashing, -10% vs piercing, +0% vs bludgeoning.
▪  Leather: +10% vs piercing, -10% vs slashing, +0% vs bludgeoning.
◦  Encode these as part of the item’s resistances map when equipped (or via tags mapped to bonuses).
•  Light, evocative on-hit synergies per type
◦  Keep probabilities low (5–20%) and gated by crits or weapon tags to avoid spam:
▪  Slashing: small chance to apply Bleeding DoT (DAMAGE_OVER_TIME from your StatusEffect system).
▪  Piercing: chance to apply Punctured: -X Damage Reduction for 1–2 turns (temporary modifier).
▪  Bludgeoning: chance to apply Staggered: -Initiative for 1 turn (temporary modifier).
▪  Fire: chance to Burning DoT (already modeled in status effects config).
▪  Cold: chance to Chilled: slow/initiative penalty or temporary -DEX-based defense.
▪  Lightning: chance to Dazed: small action penalty (e.g., -Melee/Ranged Attack or -Initiative).
▪  Acid: small chance to Corroded: -Damage Reduction for a few turns.
▪  Poison: DoT that ignores some portion of MAGIC_DEFENSE or applies on subsequent turns only.
▪  Arcane: default magical (no extra rider) or flex to special spells only.
◦  Keep all riders optional and data-driven via combat_config and/or item tags, so it remains easy to tune.
•  World Configurator: make effect types selectable
◦  DiceRollEffectDialog should offer a dropdown populated from combat_config.damage.types.
◦  Optionally show a short description tooltip (e.g., “Slashing: better vs unarmored; may cause Bleeding”).
◦  Save exactly the selected string into effect_type (e.g., “slashing”).
◦  Continue to accept dice_notation as today.
•  World Configurator Assistant grounding
◦  Include effect_types in the assistant’s get_reference_catalogs for Items:
▪  "effect_types": ["slashing","piercing","bludgeoning","fire","cold","lightning","poison","acid","arcane"]
◦  Update prompts to ask it to only choose from that list; the create/modify outputs should set entry[i].dice_roll_effects[j].effect_type to one of these.
•  Migration plan (no code now, for later)
◦  Normalize existing items:
▪  physical_slashing_damage → slashing
▪  physical_piercing_damage → piercing
◦  For items missing effect_type in dice_roll_effects:
▪  Default by weapon tag: swords → slashing, daggers/bows → piercing, maces/hammers → bludgeoning.
•  Narrative and UI polish
◦  Damage lines: “X takes N slashing damage!” (typed and flavorful)
◦  Optional short rider lines on proc: “Target starts bleeding.”
◦  Item info dialog already renders effect_type in a readable way (it title-cases underscores). With single-token types, it becomes even clearer (e.g., “1d8 Slashing”).

Why this is immersive but not overcomplicated
•  3 physical types + 5 magical types is a sweet spot for distinction without a matrix explosion.
•  One flat mitigation (DR/Magic Defense) plus one typed resistance percentage is easy to reason about and tune.
•  Light, low-chance on-hit riders add flavor without turning every hit into a status soup.
•  Everything is data-driven (combat_config, items), so you can extend later.

Recommended next steps (when you want to implement)
•  Backend
◦  Introduce a DamageType enum or use the strings from combat_config.damage.types.
◦  Carry damage_type in CombatAction or compute it from equipped weapon dice_roll_effects; default when not available.
◦  Add typed resistance lookup on targets and apply it after the existing flat reductions.
◦  Optionally, wire simple rider-chance logic keyed by damage_type and crits.
•  World Configurator
◦  Change DiceRollEffectDialog effect_type input to a dropdown populated from config/combat/combat_config.json.
◦  Add effect_types to assistant references so LLM only uses valid types.
•  Migration
◦  Normalize existing effect_type strings to the controlled vocabulary.


Phase 1: Lock vocabulary and normalize data
•  Source of truth
◦  Use config/combat/combat_config.json → damage.types as the authoritative list:
▪  ["slashing","piercing","bludgeoning","fire","cold","lightning","poison","acid","arcane"]
•  Normalization policy
◦  Map legacy item effect_type values to this vocabulary:
▪  physical_slashing_damage → slashing
▪  physical_piercing_damage → piercing
▪  Others default to arcane if not mapped.
•  Implementation notes
◦  Core code should access damage types via the existing get_config() (GameConfig) so it remains data-driven.
◦  World Configurator can load from file via file_manager.load_json (it’s a separate tool).

Phase 2: Backend typed resistance model
•  Storage: generic resistance map (per-entity)
◦  Add a typed resistance aggregator owned by StatsManager (or adjacent):
▪  Internal structure (conceptual): _typed_resist_contrib: Dict[str damage_type, Dict[source_id, float]]
▪  Public API:
▪  set_resistance_contribution(source_id: str, resistances: Dict[str,float])
▪  remove_resistance_contribution(source_id: str)
▪  get_resistance_percent(damage_type: str) -> float
▪  Total per type = sum of contributions across sources, clamped to [min_vulnerability, resistance_cap]; allow negatives to represent vulnerability (e.g., -25).
▪  Pull resistance_cap from config/combat/combat_config.json.defense.resistance_cap (default 75).
•  Equip/unequip integration
◦  Inventory/equipment flow should call set/remove_resistance_contribution when items that carry resistances are equipped/unequipped.
◦  Short-term data source for item resistances:
▪  Option A (lean): use custom_properties.resistances on items (e.g., {"slashing": 5, "fire": 10}).
▪  Option B (future): formalize a top-level item field "typed_resistances".
◦  Keep it reversible with a stable source_id (e.g., item instance id or slot key).
•  Action damage typing
◦  AttackAction:
▪  Determine damage_type from equipped weapon’s primary dice_roll_effects[0].effect_type if recognized in allowed list; else default:
▪  Melee default: slashing
▪  Ranged default: piercing
◦  SpellAction:
▪  Prefer action.special_effects.damage_type if present and valid; else default arcane.
◦  Keep this logic minimal; avoid parsing complex stacks now.
•  Damage application order
◦  raw_damage = dice + relevant stat mod (current logic)
◦  Apply flat mitigation:
▪  Physical: -DAMAGE_REDUCTION
▪  Magic: -MAGIC_DEFENSE
◦  Apply typed resistance:
▪  resist% = stats_manager.get_resistance_percent(damage_type)
▪  damage_after_type = max(0, floor((raw_damage_after_flat) × (1 - resist%/100)))
◦  Update narration to include the type (e.g., “takes 7 slashing damage!”).

Phase 3: Optional riders (flavor, gated by config)
•  Config-driven typed riders
◦  In combat_config.json, add a typed_riders section (optional):
▪  Example: "slashing": {"bleeding": {"chance": 0.1, "duration": 2, "potency": 1}}
◦  On hit, roll rider chance and apply corresponding StatusEffect. Keep chances low (5–20%), optionally crit-gated.
•  Keep off by default; implement after the core typed resistance pipeline is stable.

Phase 4: World Configurator UX adjustments
•  DiceRollEffectDialog (effect_type control)
◦  Replace free-text with a dropdown populated from config/combat/combat_config.json.damage.types.
◦  Fallback to free text only if config missing (with a warning).
◦  Tooltip short descriptions (optional): e.g., Slashing—cuts flesh; may cause bleed (if riders enabled).
•  Items editor references for assistant
◦  In SpecificItemEditor.get_reference_catalogs(), include:
▪  "effect_types": ["slashing","piercing","bludgeoning","fire","cold","lightning","poison","acid","arcane"]
◦  This grounds the LLM to valid effect_type choices when creating/modifying weapons.
•  Validation (optional but recommended)
◦  Add a validator under world_configurator/validators to scan item files for dice_roll_effects.*.effect_type not in allowed list; report issues and suggest normalized mapping.

Phase 5: Migration plan for existing data
•  Passive normalization (no code yet)
◦  Identify all effect_type values in config/items/*.json and map obvious legacy patterns:
▪  physical_slashing_damage → slashing
▪  physical_piercing_damage → piercing
◦  Audit other non-conforming values; if ambiguous, default to arcane or flag for manual review.
•  Optional WC utility
◦  Add a “Normalize Effect Types” dialog later that runs the validator and offers automatic mapping with a preview.

Phase 6: Combat pipeline integration (minimal touch points)
•  Where to hook
◦  core/combat/action_handlers.py:
▪  _handle_attack_action: detect damage_type (from weapon or default), compute final damage with typed resistance step.
▪  _handle_spell_action: detect damage_type (special_effects.damage_type or default), compute final damage with typed resistance step.
◦  core/stats/stats_manager.py:
▪  Add typed resistance aggregator + methods.
•  Data access
◦  Allowed types: load once via get_config() into a cached list so validation is cheap.
•  Narration
◦  Ensure damage lines show the type token (slashing/piercing/etc.) instead of just “Physical” or “magic”.

Phase 7: Testing plan
•  Unit/integration tests (conceptual)
◦  Attack with a sword (slashing) against a target with {"slashing": 20} → verify -20% post-flat.
◦  Attack with a mace (bludgeoning) with vulnerability {"bludgeoning": -25} → verify increased damage (as long as overall doesn’t go below 0 after DR).
◦  SpellAction with damage_type fire vs target {"fire": 50} → verify % mitigation after MAGIC_DEFENSE.
◦  Equip/unequip armor that contributes {"slashing": 10} and ensure resistance map updates.
◦  Items without dice_roll_effects use sensible defaults (melee slashing, ranged piercing).
•  WC manual checks
◦  Dropdown shows allowed types; selection persists; assistant uses allowed types in generated items.

Phase 8: Performance and safety
•  Clamp resistance totals at resistance_cap (config-driven).
•  Allow negatives to represent vulnerability.
•  Keep computation O(1) per hit (simple lookups); contributions aggregated beforehand on equip changes.
•  Backwards compatibility: items without effect_type still work via defaults; resistances absent → 0%.

Data and API summary (for later implementation)
•  Allowed effect types: from config/combat/combat_config.json.damage.types
•  Item effect schema (unchanged):
◦  dice_roll_effects: [{effect_type: "slashing", dice_notation: "1d8", description: "..."}]
•  Entity typed resistance (runtime):
◦  Aggregated in StatsManager; set via set_resistance_contribution(source_id, {"slashing": 10, "fire": 5})
•  Damage calculation:
◦  raw -> flat DR/MagicDefense -> typed% -> clamp ≥ 0
•  Defaults:
◦  AttackAction melee = slashing; ranged = piercing; SpellAction = arcane (unless specified)

Dependencies and sequencing
•  Implement backend resistance aggregator and typed mitigation first.
•  Then add damage_type detection in actions.
•  Then WC dropdown + assistant references.
•  Finally migration/validator utilities and (optionally) typed riders.