# Magic System Delivery Checklist (Engine + GUI + WebUI)

This is the master, step-by-step checklist to implement the magic system safely and incrementally across core engine, GUI (PySide6), and WebUI. It is designed to be maintained as work proceeds.

Guiding principles (do not violate)
- Separation of Concerns: core logic must not call UI methods; only produce DisplayEvents for the Orchestrator.
- Use Singleton Getters: get_game_engine(), get_state_manager(), get_stats_manager(), etc.
- Config via get_config(): no direct file reads from core/gui; consume config data through GameConfig.
- Combat UI updates are event-driven via CombatOutputOrchestrator and DisplayEvent.
- Windows 11 environment; respect ignored folders (backup, .pytest_cache, .vscode, __pycache__, tests, web, images, log_viewer_tool, world_configurator.egg-info).

Status legend
- [ ] pending
- [x] done
- [~] in progress


Phase 0 — Foundations and Data Integrity
- [x] Add unified stat registry (config/character/stat_registry.json) with aliases and supported flags
- [x] Load unified registries in GameConfig (stat_registry, canonical_lists)
- [x] Introduce core/stats/registry.py for alias resolution (resolve_stat_enum, normalize_to_canonical_id, is_supported)
- [x] Wire alias resolution into StatsManager and equipment sync (non-breaking)
- [x] Item normalization script (dry-run) scripts/migrations/normalize_items_aliases.py
- [x] Update scanner to skip any directory named “backup”
- [ ] Review normalization report logs/item_normalization_report.json and decide:
  - [ ] Which unknown stat names should be added as aliases in stat_registry.json (supported: true when mapped to real enums)
  - [ ] Which items should be corrected (apply script once alias map is ready)
  - [ ] Which dice effect types are non-canonical vs should be added to canonical_lists.json
- [ ] Optionally: extend script to generate an aggregated “unknowns_index” with suggestions (Levenshtein)
- [ ] Re-run dry-run; then re-run with --apply once mapping is approved (version control before/after)


Phase 1 — Effect Atoms (shared schema for spells/items/abilities)
- [x] Draft effect atom JSON schema (config/gameplay/effect_atoms.schema.json)
  - [x] type: damage | heal | buff | debuff | resource_change | status_apply | status_remove | cleanse | shield
  - [x] selector: self | ally | enemy | area (as per design)
  - [x] magnitude: one of { flat:number | dice:string("NdS±M") | stat_based:{stat, coeff, base} }
  - [x] duration: { unit:"turns"|"minutes", value:int } (optional)
  - [x] stacking_rule: none | stack | refresh | replace (optional)
  - [x] damage_type/status_type: canonical strings from config/gameplay/canonical_lists.json
  - [x] source_id/tags/meta: optional
- [x] Validate sample atoms against schema locally (no runtime enforcement yet)
  - [x] Added examples at config/gameplay/examples/effect_atoms_samples.json and validator at scripts/validate_effect_atoms.py
- [x] Define mapping rules from magic_systems.json spell definitions to effect atoms (document in magic_system_overhaul.md)


Phase 2 — Minimal Effects Interpreter (core-only, no UI coupling)
- [x] Create core/effects/effects_engine.py with:
  - [x] apply_effects(atoms, caster, targets) -> EffectResult (pure core)
  - [x] Target resolution left to caller (selector mapping remains at the edge)
  - [x] Deterministic magnitude calculation (dice/flat/stat_based), dice recorded via core.utils.dice
  - [x] Calls to managers:
    - [x] resource_change/heal/damage via StatsManager (DerivedStatType: HEALTH/MANA/STAMINA/RESOLVE)
    - [x] buff/debuff via ModifierManager (ModifierGroup; duration -> turns)
    - [x] status_apply/remove/cleanse via StatusEffectManager (minutes duration captured in custom_data for future purge)
  - [x] No UI calls; returns EffectResult; caller may emit DisplayEvents
- [x] Duration semantics:
  - [x] In combat: durations in turns (existing decrement logic)
  - [x] Out of combat: minutes stored for later purge when world time advances (future integration)
- [x] Gracefully skip unknown/unsupported stats/damage/status types (log warnings; never crash)


Phase 3 — Engine Integration of Spells
- [x] Introduce spell.combat_role (offensive | defensive | utility)
  - [x] Add combat_role to spell JSON in config/world/base/magic_systems.json (backfill existing spells)
  - [x] SpellCatalog: surface combat_role from spell data; default to 'offensive' if missing (temporary until backfill)
  - [x] Core targeting uses combat_role for fallbacks (see rules below) and gating of utility in combat
- [x] Define a spell catalog loader in core (no direct file I/O):
  - [x] Read magic systems via get_config().get("magic_systems")
  - [x] Build an in-memory SpellCatalog (id -> spell definition + effect atoms + metadata)
  - [x] Cache and expose getters (e.g., get_spell_by_id, list_known_spells)
  - [x] Loader supports dict-of-systems and dict-of-spells structures (in addition to lists)
- [x] Known Spells store on player:
  - [x] Add known_spells to PlayerState (persisted)
  - [x] Add helpers: add_known_spell, remove_known_spell, list_known_spells
  - [x] Developer Mode commands (gated by settings):
    - [x] //learn_spell <spell_id>
    - [x] //forget_spell <spell_id>
    - [x] //known_spells
- [x] Implement execute_cast_spell(spell_id, actor_id, target_id=None):
  - [x] Dev phase: allow casting regardless of known_spells (current behavior)
  - [x] Enforce: gate on known_spells (release behavior)
  - [x] Validate resources (mana cost, components, etc.)
  - [x] Determine targets (based on selector) and call effects_engine.apply_effects
  - [x] Deduct costs (e.g., mana)
  - [x] Emit DisplayEvents via CombatOutputOrchestrator (narrative/system/VFX placeholders)
  - [x] Return a CommandResult/EffectResult for downstream narration
- [x] Integrate with combat action handlers so combat turns include casting (queue the action instead of immediate application; Orchestrator-driven display)
  - [x] Stage 0 (Pre-validation): In COMBAT, validate the player's raw intent with RuleCheckerAgent BEFORE any attempt narrative. If invalid (lore/physics/capability), enqueue a SYSTEM_MESSAGE explaining why and remain at AWAITING_PLAYER_INPUT (do not advance the turn; no attempt narrative queued).
  - [x] Stage 2 (Mechanical gating): when input intent maps to spell/skill/item, validate deterministically BEFORE creating the action object:
    - [x] Spells: verify player's known_spells. If unknown, queue a SYSTEM_MESSAGE (e.g., "You do not know this spell.") and remain at AWAITING_PLAYER_INPUT.
    - [ ] Items: verify possession/equipped (as applicable). If missing, queue a SYSTEM_MESSAGE and remain at AWAITING_PLAYER_INPUT.
    - [ ] Skills: verify known/valid via StatsManager and class/path constraints if defined. If not known, queue a SYSTEM_MESSAGE and remain at AWAITING_PLAYER_INPUT.
  - [x] Resource semantics in combat:
    - [x] Ignore player-specified resource amounts in the input (e.g., "cast X using 0 mana"). Resource costs are computed mechanically from spell data.
    - [x] Do NOT pre-block casting due to insufficient resources; allow the cast attempt to proceed. If costs cannot be met, the turn is effectively wasted with appropriate SYSTEM_MESSAGE(s), matching current gameplay behavior.
  - [x] Spell name resolution and typos:
    - [x] Fuzzy-match the input against the player's known spell IDs and names (case-insensitive). Resolve to the closest known spell when unambiguous; only reject if no reasonable match exists.
    - [x] In Developer Mode, allow relaxed gating (e.g., bypass or more permissive mapping) for rapid testing; otherwise enforce strictly.
  - [x] Target selection rules (combat):
    - [x] Role source: spell.combat_role enumerated as {'offensive','defensive','utility'}
    - [x] Validation: warn on unknown/missing role; default to 'offensive' temporarily until backfill complete
    - [x] Offensive spells (damage/debuff): target enemies. If exactly one enemy is alive, auto-target that enemy. If multiple enemies and target unspecified (text path), fallback to a RANDOM alive enemy. Grimoire UI will present an enemy dropdown filtered to alive enemies.
    - [x] Defensive / recovery (heal, buff, shield, cleanse, status_remove): target self or ally. In 1:1 battles, default to self. In battles with allies, require explicit selection (self or ally); fallback to self if unspecified.
    - [x] Non-combat-only spells (utility like lockpicking/teleportation): disabled in combat; routed to Narrative mode only.
  - [x] Design decision: execute_cast_spell remains pure (no DisplayEvents). Real gameplay in combat uses SpellAction + handler for orchestration; dev commands use execute_cast_spell for testing.
  - [ ] Future: introduce CostCalculator to compute final mana cost/casting time from base spell data plus active modifiers (items/statuses/passives).
  - [x] Only after Stage 0 and Stage 2 pass, enqueue the NARRATIVE_ATTEMPT and create the CombatAction; proceed to RESOLVING_ACTION_MECHANICS.
- [ ] Ensure LLM time_passage is excluded during combat (already the case); keep advancing time only outside combat


Recent Changes (engine/combat integration)
- [x] Effect‑atoms spells synchronize target HP via APPLY_ENTITY_RESOURCE_UPDATE and UI_BAR_UPDATE_PHASE1/2; defeat checks are triggered
- [x] Effect‑atoms path populates current_result_detail (damage, target_hp_before/after, target_defeated) for accurate fallback narrative
- [x] Combat text path auto‑targets offensive spells when target is omitted (random alive enemy if multiple)
- [x] Interpret‑failure message replaced with actionable guidance (cast <spell_id> [target], auto‑pick note)

Planned Next
- Deterministic cast parsing (on hold)
  - [ ] Strict grammar: "cast <spell_id_or_name> [target]" before any LLM
  - [ ] Catalog‑backed fuzzy normalization with disambiguation
  - [ ] Minimal low‑temp LLM normalizer as last‑mile typo fixer; output strictly validated
- Effect‑atoms mechanical & feedback parity
  - [ ] Apply flat DR/magic defense and typed resistance for damage atoms (mechanical parity)
  - [ ] Emit raw/mitigation/resistance/final lines plus HP preview (log parity)
  - [ ] Shields/absorbs semantics (temp HP/absorb pools + logs)
  - [ ] DoT/HoT native periodic handling; stacking/refresh/replace rules
  - [ ] Turn/minute bridging and purge on time advance
- AoE & chain mechanics
  - [ ] Area selector semantics (area_kind: all_enemies | all_allies | cone | radius)
  - [ ] Per‑target resolution; orchestrator order and non‑stalling UI updates
  - [ ] Chain reaction (e.g., chain lightning) with diminishing caps per hop and no immediate re‑hit
  - [ ] Sample spells to be added AFTER effect‑atoms parity is implemented to avoid rework


Phase 4 — World Configurator Validation & Data Entry (no runtime behavior change)
- [x] Update models and editor for spell.combat_role
  - [x] world_configurator/models/base_models.py: add Spell.combat_role: Literal['offensive','defensive','utility'] with default 'offensive'; update from_dict/to_dict
  - [x] world_configurator/ui/editors/magic_systems_editor.py (SpellDialog): add 'Combat Role' dropdown with the three values; persist selection
  - [x] Export/import: ensure magic_systems.json round-trips combat_role
  - [ ] Validation: highlight spells with missing/unknown combat_role; offer quick-fix default
- [ ] Hook stat_registry + canonical_lists into world_configurator validators
  - [ ] SpecificItemEditor: validate stats against registry; highlight unsupported; tooltips from registry labels
  - [x] MagicSystemsEditor: pre-validate effect_atoms (JSON Schema + canonical damage types) on assistant Modify/Create; block invalid patches
- [x] Effect Atoms UI improvements in MagicSystemsEditor
  - [x] Dice presets dropdown with sign/modifier; duration unified (0 = instant); tooltips for all fields
  - [x] Stat picker from stat_registry for magnitude/stat mode and buff/debuff modifiers; add/remove rows with proper widgets
- [x] Assistant integration for Magic Systems tab
  - [x] Implement provider methods (context, patch, create, references, examples); headless edits (no modal)
  - [x] Read-only guard: race/class affinities excluded from allowed_paths
  - [x] Search/focus helpers for spells in assistant (search_for_entries, focus_entry)
- [ ] Add gentle, non-blocking UI warnings with actionable messages
- [ ] Add “Validate All” command to produce a multi-file summary (no automatic writes)
- [ ] Origin editor: Starting spells configuration
  - [ ] Add starting_spells list per origin
  - [ ] 2-level selector: first choose Magic System, then filtered Spell list for that system (populated from SpellCatalog)
  - [ ] Validation: warn on unknown spell IDs or systems
  - [ ] Persist to config/world/scenarios/origins.json

- [ ] Magic Systems: Casting Model & Policy (editor, read-only to assistant)
  - [ ] Add a "Casting Model" tab in MagicSystemDialog
  - [ ] Fields (per-school defaults):
    - [ ] allowed_damage_types (multi-select)
    - [ ] allowed_selectors/targets (self/ally/enemy/area; for area allow only all_enemies/all_allies)
    - [ ] default_target_by_role mapping { offensive: enemy, defensive: self_or_ally, utility: disabled_in_combat }
    - [ ] allow_chain_magic (bool) and chain_decay (e.g., 0.7 -> next hops receive 70%)
    - [ ] cost_multiplier, cast_time_multiplier (floats)
    - [ ] creativity_policy (short advisory string shown to LLM; assistant uses for guidance only)
  - [ ] Persist under each system (e.g., magic_systems[].casting_model)
  - [ ] Expose to assistant in references; exclude from allowed_paths (no assistant edits)

- [ ] Components & Casting Time (data, UI, and semantics)
  - [ ] Replace free-form casting_time string with a unified integer spinbox in editor
    - [ ] Units: turns in combat, minutes outside combat; 0 = instant
    - [ ] Migrate existing string values to integers (normalizer; warn when ambiguous)
  - [ ] Engine semantics:
    - [ ] If cast_time > 0 in combat, casting spans multiple turns; taking damage interrupts (cast fails)
    - [ ] Out of combat, delay by cast_time minutes
  - [ ] Components: treat as required inventory items; on cast attempt, verify presence and consume on success; failure blocks cast with clear message

- [ ] Engine parity: resistances, shields/DoT, AoE, chain
  - [ ] Damage atoms: apply typed resistance by damage_type after DR/magic defense; log raw→mitigated→final
  - [ ] Shields/DoT/HoT: adopt refresh-on-reapply by default (no additive stacking); honor stacking_rule if present
  - [ ] AoE resolution (no shapes): implement all_enemies/all_allies selection deterministically with per-target logs
  - [ ] Chain magic: implement diminishing factor per hop; avoid re-hitting the same entity in a chain


Phase 5 — GUI (PySide6) Magic UI per MAGIC_SYSTEM_UI_design_doc.md
- [ ] Add Grimoire tab to right panel (accordion by Magic System)
  - [ ] Hover tooltip: mana cost, casting time, brief effect summary
  - [ ] Spell Details dialog (singleton, non-modal): full spell info from config
- [ ] Cast button
  - [ ] Enabled only in COMBAT mode (disabled in NARRATIVE)
  - [ ] On click: present target menu based on selector and current combatants
  - [ ] Targeting rules in UI: offensive → enemy list (auto-select if only one); defensive/recovery → self or ally list (default self in 1:1); non-combat-only spells are disabled in combat
  - [ ] Dispatch to engine via CombatManager by creating a SpellAction (do not call execute_cast_spell directly from UI)
  - [ ] Do not call UI from core. Observe orchestrated DisplayEvents
- [ ] Resource bars and status areas
  - [ ] Ensure modifier/status effects applied by spells render correctly via signals
  - [ ] Show temporary buffs/debuffs with duration when available (turns)
- [ ] Follow Qt signals/slots best practices; avoid direct calls across components; wire via MainWindow hub


Phase 6 — WebUI (client + server)
- [ ] Add Grimoire panel (accordion) mirroring the GUI design
  - [ ] Tooltip and Details drawer/dialog
- [ ] API endpoints (server)
  - [ ] GET /api/spells (for known spells)
  - [ ] POST /api/cast { spell_id, target_id }
  - [ ] Use engine.get_game_engine() and engine.execute_cast_spell under the hood
- [ ] Target selection UI when casting
- [ ] Ensure orchestrated events render in the existing WebUI output area (no schema changes to events)


Phase 7 — LLM Integration (Narrator + CombatNarrator)
- [ ] In Narrative mode: LLM may mention spells, but execution remains deterministic
  - [ ] For “cast” intents outside combat, Narrator proposes state changes and narrative only; engine may deny/confirm based on context
  - [ ] Enforce that time_passage remains a narrative-only construct; world.advance_time excluded in COMBAT
- [ ] Narrative-mode magic usage (non-combat):
  - [ ] LLM-driven creation of NPC entities on-the-fly (when user interacts with a newly described NPC): assign id, basic stats, and items; persist so they become part of the world state.
  - [ ] Gating: verify player knows the spell and has resources; resolve utility/healing-type spells via effects engine deterministically.
  - [ ] Offensive spells in Narrative mode trigger COMBAT immediately with a surprise opening (magic) attack; ensure the surprise logic is implemented (future subtask) and CombatManager is initialized correctly.
  - [ ] Apply effects to NPC stats even though NPC stats are hidden in UI outside combat; update player’s visible stats in non-combat when applicable (e.g., self-heals, mana costs).
  - [ ] Track out-of-combat durations via the time controller (minutes). On world time advance, purge/expire effects appropriately.
- [ ] In Combat mode: ensure CombatNarrator does not advance time
  - [ ] Optional: Support structured request to “cast_spell” resolving to engine.execute_cast_spell (safe routing)
- [ ] Tighten rule checker policies if needed (e.g., restrict spell names to known catalog; prohibit time manipulation in combat)


Phase 8 — Persistence, Save/Load, and Edge Cases
- [ ] Persist any active status effects and modifier groups (already supported)
- [ ] Persist out-of-combat effect expirations by absolute game_time (expires_at)
- [ ] On load: re-hydrate and purge any expired effects immediately
- [ ] Non-combat UI: update player stats immediately in the GUI when spells affect the player outside combat; NPC stats remain hidden.
- [ ] Guardrails: never crash on missing or renamed spells; provide fallback messages


Phase 9 — QA, Telemetry, and Documentation
- [ ] Add debug logs at key points (spell selection, target resolution, effects applied, dice rolls)
- [ ] Time audit logs remain disabled by default unless debug flags say otherwise
- [ ] Update docs (magic_system_overhaul.md) with effect atom mapping and example spells
- [ ] Produce a short “Designer’s checklist” for magic authors (within existing docs; not new files unless requested)


Operational Safety Checks (repeat each phase)
- [ ] No direct UI calls from core; only DisplayEvents
- [ ] All file access via get_config() in core/gui
- [ ] Respect singleton getters
- [ ] Validate stat names via registry; skip unsupported safely
- [ ] Keep changes additive; avoid breaking current flows
- [ ] Developer Mode gating: When settings.DisableDevMode is true, all dev commands must be ignored/return an informative error. When enabled, dev commands are allowed. UI must expose the toggle in game settings.


Cutover Plan (when feature-complete)
- [ ] Feature flag “magic_system.enabled” in config/game/game_config.json (optional)
- [ ] Staged rollout: engine core first, GUI second, WebUI last
- [ ] Backward compatibility: if spells disabled, ensure no new UI actions are enabled


Appendix — Practical Ordering Suggestions
- [ ] Complete Phase 0 review and applied normalization (aliases + --apply)
- [ ] Lock effect atom schema (Phase 1)
- [ ] Build interpreter + engine integration (Phases 2–3)
- [ ] Add validators in configurator (Phase 4)
- [ ] Implement GUI Grimoire + casting (Phase 5)
- [ ] Implement WebUI (Phase 6)
- [ ] LLM policy + routing finalization (Phase 7)


Open Questions
1) Scaling rules
- Exact formulas for stat_based magnitudes per school (e.g., coeffs per INT/WIS for spell power)?
- Should class/race affinities modify magnitude or cost or both?

2) Area / AoE and Chain semantics
- For selector = area, do we target all enemies, all allies, or require a sub-field (e.g., area_kind: "all_enemies" | "all_allies" | "cone" | "radius")?
- Should friendly fire be allowed/toggleable per spell?
- Chain logic: diminishing cap per hop (e.g., 100% → 70% → 50%); avoid immediately re‑hitting already hit entities unless explicitly allowed
- Resolution model: per‑target roll/magnitude + DR + typed resistance, with readable grouped logs

3) Status inventory
- Canonical set of status conditions to support initially (beyond the current list)?
- Standard durations for common statuses (e.g., Stunned 1–2 turns)?

4) Costs and components
- Are there non-mana costs (materials, rituals) that should be mechanically enforced now vs narrated only?
- How to consume materials in items vs spells (shared pipeline or separate hooks)?

5) Miscast/backlash/chaos
- Which magic systems include failure states or backlash rules?
- Where should this logic live (interpreter hook vs per-spell custom_data)?

6) Resistances and damage typing
- Final canonical list for damage types and how multi-type damage should be split (e.g., 50/50 fire/arcane)?
- Do typed resistances stack additively across armor, effects, and innate traits (current approach), or capped per layer?

7) Cooldowns and global locks
- Do spells have cooldowns beyond resource costs? If yes, how to track in engine state?

8) WebUI orchestration
- Are existing websockets/polling hooks sufficient to carry all DisplayEvents for smooth spell feedback?

9) Accessibility
- Text-to-speech coverage for spell narration in orchestrator (already present for general narration); do we need distinct voice cues?

10) Data editor UX
- In world_configurator, how strict should validation be (blocking vs warning)?
- Bulk operations for migrating legacy spell catalogs to effect atoms?


Notes
- Combat continues to exclude LLM-driven time passage; outside of combat, time advances via structured time_passage with a safe 1-minute fallback when absent.
- All changes are intended to be incremental and non-breaking. Use version control checkpoints after each phase.
