# NPC System (Rule-Driven, Procedural, Deterministic Mechanics)

Status: Design document for the next-gen NPC model. The current `config/character/npc_templates.json` is considered LEGACY and will be replaced by the system described here.

Goals
- Keep core mechanics deterministic and evaluable (combat, quests, rewards, progression).
- Let the world expand procedurally and contextually via rules, tags, and bounded LLM creativity.
- Avoid an ever-growing static bestiary; use a small set of reusable, composable templates (“families”) + overlays + tags.
- Make quests robust by matching against canonical lineage/tags/instances rather than fragile names.

Key Concepts
1) NPC Family (Template)
- Defines a reusable archetype used to mint concrete NPC variants at runtime.
- Families are defined along broad axes instead of specific species lists:
  - actor_type: beast, humanoid, undead, construct, etc.
  - threat_tier: harmless, easy, normal, dangerous, ferocious, mythic
  - role_archetype: striker, tank, controller/caster, support, skirmisher, sniper (extensible)
  - biome/theme tags: forest, tundra, cave, urban, ruins, sewers, etc.
  - faction/culture tags: bandit, tribal, imperial, corrupted, arcane, etc.
- Families carry rule sets (stat budgets, ability pools, allowed tag sets, scaling curves).

2) Boss Overlay (is_boss)
- Independent boolean overlay that modifies any family+tier:
  - is_boss: true/false (can have an easy boss or a very hard non-boss)
  - Adds boss-specific scaling (HP/DR multipliers), ability complexity, behavior phases, reward/loot policy.
- Overlay ensures cinematic encounters without hardcoding species.

3) Variant (Runtime-Minted NPC)
- A concrete NPC created from a family + overlay + context.
- Carries:
  - instance_id: globally unique ID
  - template_lineage: e.g., `beast_normal_base → wolfish_variant` (lineage chain)
  - is_boss: true/false
  - tags: actor_type, threat_tier, role, biome, faction, species?, color?, temperament?, etc.
  - numeric stats: HP, damage, defense, initiative, etc. (deterministic budgets)
  - ability set: chosen from family pools within allowed budgets
  - provenance: seed, context, (optional) LLM rationale for flavor
- Stored in a runtime registry (persisted in the save) for reproducibility and resolution later.

4) Tags (Taxonomy)
- Tags are first-class attributes used for matching, scaling, and quest evaluation.
- Recommended base set:
  - actor_type: beast | humanoid | undead | construct | …
  - threat_tier: harmless | easy | normal | dangerous | ferocious | mythic
  - is_boss: true | false
  - role: striker | tank | controller | support | skirmisher | sniper | …
  - biome: forest | tundra | desert | swamp | cave | urban | ruins | sewers | …
  - faction/culture: bandit | tribal | imperial | corrupted | arcane | …
  - species (optional): wolf | boar | goblin | ogre | human | …
  - color/appearance (optional): white | black | mottled | spectral | …
  - temperament (optional): docile | skittish | aggressive | territorial | …
  - elemental (optional): fire | ice | poison | necrotic | radiant | …
  - alignment (optional): lawful | neutral | chaotic; good | neutral | evil (flexible)
  - communicative: true | false (see Interaction Flags)
  - languages (optional): common | goblinoid | druidic | …
  - social_structure (optional): solitary | pair | pack | tribe | legion | …
  - diurnal/nocturnal/crepuscular (optional)

5) Interaction Flags (LLM-decided, engine-enforced)
- communicative: boolean indicating if this entity can be engaged in dialogue (LLM suggests from context).
- trade_enabled: boolean (for sentient/humanoid or unique beasts) — optional.
- quest_giver: boolean (rare; used by story logic) — optional.
- intimidation/persuasion applicable: boolean or threshold-driven — optional.
- Note: These flags may be proposed by the LLM based on narrative context, but the engine validates against family rules and tags. Final flags are stored on the variant and used to gate interactions.

6) Context Adaptors and Scaling
- Variant generation considers:
  - player_level (later), difficulty_setting (planned), party size, region_danger, quest_stage
  - encounter type: solo, pack, mixed
- These adaptors scale numeric budgets and ability complexity within tier envelopes, ensuring fairness and variety without breaking tier identity.

Minting Pipeline (Engine + LLM)
1) Engine chooses a family by actor_type + threat_tier (and optional role, biome, faction) based on context.
2) Compute numeric budgets using family curves + scaling adaptors.
3) Select roles and abilities from family pools (deterministic, bounded).
4) LLM adds bounded flavor: name, short description, optional “signature” trait/ability in structured form.
   - The engine validates signature against budgets and allowed lists; otherwise, it downgrades or replaces.
5) Produce final variant spec: stats, abilities, tags, is_boss, lineage, provenance.
6) Persist variant to runtime registry (for determinism and save/load continuity).

Events (Deterministic Evidence)
- EV_ENEMY_DEFEATED should include:
  - instance_id (unique)
  - template_lineage (family_id, optional variant_id)
  - tags (actor_type, threat_tier, is_boss, role, biome, faction, species?, …)
  - location_id, time (if applicable)
- Similar enrichment recommended for EV_ITEM_DELTA, EV_LOCATION_VISITED, EV_DIALOGUE, EV_INTERACTION, EV_FLAG_SET when applicable (carry canonical ids and tags).

Quests and Objectives (Robust Matching)
- Objectives can target:
  - Instance: kill instance_id=X (that unique NPC)
  - Lineage: kill entity where lineage includes `humanoid_dangerous_base`
  - Tags: kill entity where tags satisfy DSL (e.g., {all: [actor_type:beast, threat_tier>=dangerous, biome:forest]}) with count ≥ N
  - Boss toggle: is_boss:true or false (independent of tier)
- Mandatory/Optional semantics:
  - Quest completes automatically when all mandatory objectives complete.
  - Quest fails immediately if any mandatory objective fails.
  - Optional objectives don’t block completion but affect rewards/outcomes.
- The DSL evaluator uses lineage/tags/instances deterministically; LLM is used only to propose/clarify objective intent during creation.

Aliases and Resolution
- Global `config/world/aliases.json` and per-quest alias maps allow narrative labels (e.g., “white_wolf”) to resolve to tags or lineage.
- With the tag-first model, aliases are a convenience fallback, not a primary dependency.

World Configurator (Authoring)
- Authors define a small number of powerful NPC families by actor_type + threat_tier, with:
  - stat budget envelopes and scaling curves
  - role distributions and ability pools
  - allowed tag combinations (biome/faction/etc.)
  - boss overlay rules (multipliers, phases, loot policies)
- Quests are authored against lineage or tag constraints (preferred), or specific instances (for story roles).
- Tools:
  - Variant Preview: mint a sample variant for a seed/context to inspect stats/tags/abilities.
  - Objective Evaluator: feed mock events to see objective/quest transitions in real-time.
  - Tag Taxonomy Editor: maintain the controlled vocabulary.

File Layout (Proposed)
- `config/npc/families.json` — family definitions (actor_type + threat_tier + rules)
- `config/npc/boss_overlays.json` — boss scaling/ability overlays
- `config/npc/roles.json` — role archetypes and ability pools
- `config/npc/abilities.json` — ability definitions and tags
- `config/npc/tags.json` — controlled vocabulary and validation rules
- `config/npc/generation_rules.json` — global scaling rules (difficulty, player level, encounter size)
- `config/world/aliases.json` — global alias mappings for narrative labels → tags/lineage/ids

Data Ownership and Persistence
- Static definitions live under `config/npc` (families, overlays, roles, abilities, tags, rules).
- Runtime-minted variants are stored in the save (registry of instances), including provenance (seed/context) for reproducibility.

LLM Interfaces (Structured, Bounded)
- Variant Creation Request (engine → LLM): includes context (biome, faction, role, tier, is_boss), asks for:
  - name (string), short description (string)
  - proposed trait tags (list of strings)
  - optional signature_ability (structured: name, effect_type, brief mechanics)
  - communicative suggestion (boolean) and optional languages
- LLM returns structured JSON; engine validates, clips, or ignores excess.
- Quest Creation (LLM → engine): produces objectives in terms of tags/lineage or a specific instance. If narrative labels are used, resolver creates canonical mappings.

Validation and Safety Rails
- Budget validation: numeric stats and ability complexity must remain within family+tier envelopes.
- Tag validation: only allowed combinations; disallowed combos are auto-corrected or rejected.
- If LLM proposals conflict, engine degrades gracefully and logs a rationale (for telemetry and debugging).

Performance Considerations
- Maintain indexes by tags and lineage in runtime so tag-based quest checks and counts are O(1)/O(log n).
- Keep event logs compact but include canonical references.

Examples (Illustrative)
- Ferocious non-boss beast minted as “White Wolf Alpha”:
  - lineage: `beast_ferocious_base → wolfish_variant`
  - tags: actor_type:beast, threat_tier:ferocious, species:wolf, color:white, role:skirmisher, biome:forest, is_boss:false
  - events: EV_ENEMY_DEFEATED carries instance_id, lineage, tags → objective `{all: [actor_type:beast, threat_tier>=dangerous]}` matches.

- Easy boss humanoid “Cocky Bandit Leader”:
  - lineage: `humanoid_easy_base → bandit_leader_variant`
  - tags: actor_type:humanoid, threat_tier:easy, faction:bandit, role:controller, is_boss:true
  - tuned for early story; cinematic but not punishing.

Backward Compatibility and Migration
- Treat `config/character/npc_templates.json` as LEGACY.
- A migration tool can:
  - Convert select legacy entries to families and roles or create “starter” variants.
  - Populate initial alias entries for common narrative labels.

Why This Works
- Deterministic mechanics: evaluation uses lineage/tags/instances from canonical events and a data-driven DSL.
- Emergent world: families + overlays + tags + bounded LLM flavor produce endless, context-bound variety.
- Authorable at scale: small, powerful rule sets replace unwieldy static lists.

Appendix — Suggested Minimal Tag Vocabulary
- actor_type, threat_tier, is_boss, role, biome, faction, species, color, temperament, elemental, communicative, languages, social_structure, alignment.

Appendix — Interaction Policy Examples
- communicative:true & actor_type:humanoid → dialogue, trade, persuasion enabled by default (subject to story flags)
- communicative:true & actor_type:beast, species:wolf, temperament:aggressive → limited dialogue (growls), intimidation, animal empathy; trade disabled
- communicative:false → only combat or non-verbal interactions (observe, track, evade)

