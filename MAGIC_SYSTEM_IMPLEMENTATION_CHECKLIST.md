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
- [~] Implement execute_cast_spell(spell_id, actor_id, target_id=None):
  - [x] Dev phase: allow casting regardless of known_spells (current behavior)
  - [ ] Enforce: gate on known_spells (release behavior)
  - [ ] Validate resources (mana cost, components, etc.)
  - [ ] Determine targets (based on selector) and call effects_engine.apply_effects
  - [ ] Deduct costs (e.g., mana)
  - [ ] Emit DisplayEvents via CombatOutputOrchestrator (narrative/system/VFX placeholders)
  - [ ] Return a CommandResult/EffectResult for downstream narration
- [ ] Integrate with combat action handlers so combat turns include casting (queue the action instead of immediate application; Orchestrator-driven display)
  - [ ] In COMBAT: when input intent maps to spell casting, validate player's known_spells BEFORE creating SpellAction. If unknown, queue a SYSTEM_MESSAGE to the Combat Log (via orchestrator) like "You do not know this spell." and remain at AWAITING_PLAYER_INPUT; do not proceed with action. (Location: core/combat/combat_manager.py::_step_processing_player_action)
- [ ] Ensure LLM time_passage is excluded during combat (already the case); keep advancing time only outside combat


Phase 4 — World Configurator Validation & Data Entry (no runtime behavior change)
- [ ] Hook stat_registry + canonical_lists into world_configurator validators
  - [ ] SpecificItemEditor: validate stats against registry; highlight unsupported; tooltips from registry labels
  - [ ] magic_systems_editor.py: validate spells’ effect atoms (types, damage/status, durations)
- [ ] Add gentle, non-blocking UI warnings with actionable messages
- [ ] Add “Validate All” command to produce a multi-file summary (no automatic writes)
- [ ] Origin editor: Starting spells configuration
  - [ ] Add starting_spells list per origin
  - [ ] 2-level selector: first choose Magic System, then filtered Spell list for that system (populated from SpellCatalog)
  - [ ] Validation: warn on unknown spell IDs or systems
  - [ ] Persist to config/world/scenarios/origins.json


Phase 5 — GUI (PySide6) Magic UI per MAGIC_SYSTEM_UI_design_doc.md
- [ ] Add Grimoire tab to right panel (accordion by Magic System)
  - [ ] Hover tooltip: mana cost, casting time, brief effect summary
  - [ ] Spell Details dialog (singleton, non-modal): full spell info from config
- [ ] Cast button
  - [ ] Enabled only in COMBAT mode (disabled in NARRATIVE)
  - [ ] On click: present target menu based on selector and current combatants
  - [ ] Dispatch to engine.execute_cast_spell(spell_id, target_id)
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
- [ ] In Combat mode: ensure CombatNarrator does not advance time
  - [ ] Optional: Support structured request to “cast_spell” resolving to engine.execute_cast_spell (safe routing)
- [ ] Tighten rule checker policies if needed (e.g., restrict spell names to known catalog; prohibit time manipulation in combat)


Phase 8 — Persistence, Save/Load, and Edge Cases
- [ ] Persist any active status effects and modifier groups (already supported)
- [ ] Persist out-of-combat effect expirations by absolute game_time (expires_at)
- [ ] On load: re-hydrate and purge any expired effects immediately
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

2) Area targeting semantics
- For selector = area, do we target all enemies, all allies, or do we need a sub-field (e.g., area_kind: "all_enemies" | "all_allies")?
- Should friendly fire be allowed/toggleable per spell?

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
