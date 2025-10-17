### **Phase 1: Establish Canonical Data and Schemas (The "Source of Truth")**

This phase focuses on creating the foundational data files that will define the rules for stats, magic, and items. No major code changes happen here; this is about defining the data contracts.

*   **Checkpoint 1.1: Create the Canonical Stat Registry.**
    *   **Action:** Create a new file: `config/character/stat_registry.json`.
    *   **Content:** Define all stats the engine recognizes. Use the format specified in the analysis, including `key`, `category`, `label`, and `aliases`.
    *   **Details:**
        *   **Primary Stats:** Add `STRENGTH`, `DEXTERITY`, `CONSTITUTION`, `INTELLIGENCE`, `WISDOM`, `CHARISMA`, `WILLPOWER`, `INSIGHT`.
        *   **Derived Stats:** Add all `DerivedStatType` enums from `core/stats/stats_base.py` as canonical keys (e.g., `MAX_HEALTH`, `MELEE_ATTACK`, `DAMAGE_REDUCTION`).
        *   **Aliases:** Populate the `aliases` array by reviewing existing `config/items/*.json` files. Map common non-standard names to their canonical keys (e.g., `"strenght"` -> `"strength"`, `"armor"` -> `"DEFENSE"`, `"attack_bonus"` -> `"MELEE_ATTACK"`).
        *   **Unsupported Stats:** For stats like `attack_speed` and `critical_chance`, add them to the registry but mark them with a `"supported": false` flag for now. This allows them to be recognized by the configurator but flagged as not yet implemented in the engine.

*   **Checkpoint 1.2: Finalize Canonical Lists for Magic.**
    *   **Action:** Create a new file `config/gameplay/canonical_lists.json` or add a section to an existing core config file.
    *   **Content:**
        *   **Damage Types:** Formalize the list from `config/combat/combat_config.json` (`slashing`, `piercing`, `fire`, `cold`, etc.).
        *   **Status Conditions:** Formalize a list of supported status effects. Start with those implemented in `core/stats/combat_effects.py` (`Poisoned`, `Stunned`, `Berserk`, `Regeneration`, `Defending`, `Burning`, etc.).

*   **Checkpoint 1.3: Define Schemas in Documentation.**
    *   **Action:** Create or update a `DESIGN_DOCS.md` file in the project root.
    *   **Content:**
        *   **Magic System Schema:** Formally document the proposed JSON structure for a magic system, including the `creativity_policy`, `casting_model`, `chaos`, and the `spells` array with `effect_atoms`.
        *   **Effect Atom Schema:** Document the structure for `effect_atoms` (`type`, `damage_type`, `stat`, `status_effect`, `base`, `duration_rounds`, etc.).
        *   **Item Type Schemas:** Document the required and optional fields for each major `item_type` (Weapon, Armor, Consumable) as outlined in the analysis.

---

### **Phase 2: Enhance `world_configurator` to Enforce Schemas**

- Casting Model (per-school defaults; read-only to assistant)
  - Add a new Casting Model tab in MagicSystemDialog capturing:
    - allowed_damage_types (multi-select)
    - allowed_selectors/targets (self/ally/enemy/area with area_kind limited to all_enemies/all_allies)
    - default_target_by_role mapping
    - allow_chain_magic (bool) and chain_decay (float)
    - cost_multiplier and cast_time_multiplier
    - creativity_policy (short text surfaced to LLM as advisory)
  - Persist under magic_systems[].casting_model; include in assistant references; exclude from allowed_paths

- Components & Casting Time (editor + normalization)
  - Replace free-form casting_time string with integer spinbox (0 = instant). Label clarifies: turns in combat, minutes outside combat.
  - Add a normalizer/migration pass to convert legacy strings to integers; warn when ambiguous.

This phase updates the editing tools to use and enforce the new data contracts created in Phase 1.

*   **Checkpoint 2.1: Integrate Stat Registry into Editors.**
    *   **File:** `world_configurator/ui/editors/SpecificItemEditor.py` (for items) and `world_configurator/ui/editors/magic_systems_editor.py` (for spells).
    *   **Action:**
        *   Modify the `ItemStatDialog` and Spell editing UI.
        *   Replace the free-text input for stat names (`stat_affected`, `stats.name`) with a `QComboBox`.
        *   This `QComboBox` should be populated from the `stat_registry.json` file, showing the user-friendly `label` but storing the canonical `key`.
    *   **Status:** DONE — Items editor uses a stat picker; Magic Systems Effect Atom dialog uses a stat picker for magnitude/stat mode and buff/debuff modifiers.

*   **Checkpoint 2.2: Update Item Editor for Type-Specific Schemas.**
    *   **File:** `world_configurator/ui/editors/SpecificItemEditor.py`.
    *   **Action:**
        *   Modify the `_populate_details_from_item_data` and `_apply_details_to_current_item_data` methods.
        *   Dynamically show/hide UI fields based on the selected `item_type` to match the schemas from Phase 1. For example, `dice_roll_effects` and `attack_speed` fields should only be visible for `item_type: "weapon"`.

*   **Checkpoint 2.3: Overhaul Magic Systems Editor.**
    *   **File:** `world_configurator/ui/editors/magic_systems_editor.py`.
    *   **Action:**
        *   Effect Atom dialog enhancements: dice presets dropdown (NdS ± modifier), unified duration spin (0 = instant), comprehensive tooltips, stacking rules, periodic tags.
        *   Use canonical damage types from `canonical_lists.json` and stat IDs from `stat_registry.json` where applicable.
        *   Assistant integration: headless Modify/Create with pre-apply schema validation; race/class affinities read-only.
    *   **Status:** PARTIAL — UI/assistant improvements complete; Casting Model/Creativity/Backlash sections are pending.

---

### **Phase 3: Migrate Existing Configuration Data**

This phase involves cleaning up all existing `.json` files to conform to the new canonical standards. This can be done with a one-off script or manually.

*   **Checkpoint 3.1: Normalize Item Stats.**
    *   **Files:** All files in `config/items/`.
    *   **Action:**
        *   Iterate through every item in every file.
        *   For each entry in an item's `stats` list, use the `stat_registry.json` alias map to convert its `name` to the canonical key.
        *   For stats marked as `"supported": false` (e.g., `attack_speed`), move them to a `custom_properties.legacy_stats` dictionary within the item to preserve the data without affecting the engine.
        *   Ensure all resistance-related stats are moved to `custom_properties.typed_resistances`.

*   **Checkpoint 3.2: Normalize Magic System and Spell Effects.**
    *   **File:** `config/world/base/magic_systems.json`.
    *   **Action:**
        *   For each spell in each magic system, review its `effects`.
        *   Validate that `damage_type`, `stat_affected`, and `status_effect` values match the canonical lists from Phase 1.
        *   Update any non-compliant values (e.g., change `"Defense"` to `"DEFENSE"`).
        *   Add `(narrative-only)` to the description of any status effects not on the canonical list.

---

### **Phase 4: Implement Runtime Integration in Core Engine**

- Casting Time semantics
  - If cast_time > 0 in combat: casting spans cast_time turns and is interrupted on damage; outside combat: delays by cast_time minutes.

- Components consumption
  - On cast, verify required components in inventory; consume them on successful cast; fail with clear message if missing.

- Typed resistances and shields/DoT behavior
  - Apply typed resistance by damage_type after DR/magic defense with clear logs.
  - Re-applying shields/DoT/HoT refreshes duration by default (no additive stacking unless stacking_rule overrides).

- AoE and Chain
  - AoE: support only all_enemies/all_allies (no shapes); resolve deterministically with per-target logs.
  - Chain magic: diminishing effectiveness per hop; avoid hitting the same entity twice in one chain.

This phase connects the newly structured data to the game's mechanics, making the magic system functional.

*   **Checkpoint 4.1: Enhance StatsManager with Alias Resolution.**
    *   **File:** `core/stats/stats_manager.py`.
    *   **Action:**
        *   Modify the `sync_equipment_modifiers` method.
        *   The manager should load `config/character/stat_registry.json` on initialization.
        *   When processing an item's stats, use the registry's alias map to resolve the stat name to its canonical key before applying the modifier. Log a warning for any stat that cannot be mapped.

*   **Checkpoint 4.2: Implement the Spell Resolver.**
    *   **Action:** Create a new module: `core/combat/spell_resolver.py`.
    *   **Functionality:**
        *   Implement a `resolve_spell(spell_id, caster_stats)` function.
        *   This function will load `config/world/base/magic_systems.json`, find the specified spell, and read its `effect_atoms`.
        *   It will translate these atoms into a `CombatAction` object, populating `dice_notation`, `cost_mp`, `cost_stamina`, and `special_effects` (e.g., `{"apply_status": {"name": "Burning", "duration": 3}}`) as expected by the action handlers.
        *   It should also apply scaling based on `caster_stats` and the spell's `scaling` rules.

*   **Checkpoint 4.3: Integrate Spell Resolver into Combat Flow.**
    *   **File:** `core/combat/action_handlers.py`.
    *   **Action:**
        *   Modify `_handle_spell_action`. Instead of directly using the `CombatAction`'s data, it should now treat the action as an *intent to cast*.
        *   Call the new `spell_resolver.resolve_spell()` function using the `spell_id` from the `CombatAction`.
        *   Use the fully-formed `CombatAction` returned by the resolver to execute the rest of the spell mechanics (damage, effects, etc.).

---

### **Phase 5: Integrate LLM Guardrails and Policy**

This phase teaches the AI agents about the new, structured magic system.

*   **Checkpoint 5.1: Update Agent System Prompts.**
    *   **Files:** `core/agents/narrator.py`, `core/agents/combat_narrator.py`.
    *   **Action:** Modify the `_generate_system_prompt` methods.
    *   **Content:**
        *   Instruct the LLM that when proposing a spell, it should return a `request` to cast a spell by its canonical `spell_id`.
        *   Provide the LLM with the canonical lists of damage types and status conditions and instruct it to use them when describing effects.

*   **Checkpoint 5.2: Implement Creativity Policy.**
    *   **File:** `core/agents/combat_narrator.py`.
    *   **Action:**
        *   When generating a prompt for the LLM, the `process` method should load the `creativity_policy` from the relevant magic system in `magic_systems.json`.
        *   Include this policy in the system prompt, giving the LLM clear boundaries for its narrative descriptions (e.g., "Flavor changes are allowed, but do not change the damage type from 'fire'").

---

### **Phase 6: Verification and Documentation**

This final phase ensures the overhaul is working correctly and is well-documented.

*   **Checkpoint 6.1: End-to-End Testing.**
    *   **Action:** Perform manual tests covering the entire workflow:
        1.  In `world_configurator`, create a new spell with a `stat_modification` using a canonical stat from the dropdown.
        2.  Assign this spell to a magic system.
        3.  Export all data to the game.
        4.  In-game (or via dev command), have a character learn and cast the spell in combat.
        5.  Verify that the combat log shows the correct mechanical effect and that the LLM narrates it according to the defined flavor.

*   **Checkpoint 6.2: Write Unit Tests.**
    *   **Action:** Add new tests for:
        *   The `SpellResolver` to ensure it correctly translates effect atoms into `CombatAction` properties.
        *   The `StatsManager` to verify that it correctly resolves stat aliases from items.

*   **Checkpoint 6.3: Update Documentation.**
    *   **Action:** Update developer documentation (`README.md` or a dedicated `docs/` folder).
    *   **Content:** Explain the new data-driven magic system, the role of the canonical stat registry, and the process for adding new stats, spells, or magic effects.