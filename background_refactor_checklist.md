# Checklist: Character Background Refactor to "Origin" System

This checklist outlines the steps required to replace the separate "Background" and "Starting Scenario" systems with a unified "Origin" system, integrating character starting points deeply with the game world's lore, locations, and cultures as defined in `gameworld_framework.md` and related JSON files.

**Phase 1: Data Structure Definition and Consolidation**

*   [ ] **1.1. Decide Final Filename:**
    *   [ ] Confirm the new file name (e.g., `origins.json`). For this checklist, we'll assume `origins.json`.
*   [ ] **1.2. Retire Old Files:**
    *   [ ] Remove `config/character/backgrounds.json` from the project structure (or archive it).
    *   [ ] Mentally (or physically) rename `config/world/scenarios/starting_scenarios.json` to `config/world/scenarios/origins.json` (or move/rename the file if preferred).
*   [ ] **1.3. Define New Origin JSON Structure:**
    *   [ ] Finalize the JSON structure for each entry in `origins.json`. Ensure it includes:
        *   `id` (string, unique identifier)
        *   `name` (string, display name)
        *   `description` (string, short summary for selection UI)
        *   `starting_location_id` (string, links to `locations.json`)
        *   `starting_culture_id` (string, optional, links to `cultures.json`, overrides location default if present)
        *   `starting_items` (list of strings, item IDs)
        *   `initial_quests` (list of strings, quest IDs, optional)
        *   `suitable_races` (list of strings, race IDs)
        *   `suitable_classes` (list of strings, class IDs)
        *   `introduction_text` (string, detailed narrative seed for LLM)
        *   `skill_proficiencies` (list of strings, names of skills granted) **(NEW)**
        *   `origin_traits` (list of objects, each with `name` (string) and `description` (string)) **(NEW)**
*   [ ] **1.4. Populate New Fields in `origins.json`:**
    *   [ ] Review each existing entry (formerly "scenario") in the `origins.json` file.
    *   [ ] For each entry, add appropriate `skill_proficiencies` based on the origin's theme.
    *   [ ] For each entry, add relevant `origin_traits` (1-3 minor traits) that provide narrative flavor and potentially minor mechanical effects.
*   [ ] **1.5. Verify Data Links:**
    *   [ ] Double-check that all `starting_location_id` values correctly match an `id` in `locations.json`.
    *   [ ] Double-check that all `starting_culture_id` values (if used) correctly match an `id` in `cultures.json`.
    *   [ ] Ensure `starting_items`, `initial_quests`, `suitable_races`, and `suitable_classes` reference valid IDs from their respective config files.

**Phase 2: World Configurator Tool Updates (`world_configurator/`)**

*   [ ] **2.1. Update UI - Main Window:**
    *   [ ] Remove the "Backgrounds" editor tab/section.
    *   [ ] Rename the "Starting Scenarios" editor tab/section to "Origins".
*   [ ] **2.2. Update UI - Origin Editor:**
    *   [ ] Add a widget (e.g., `QListWidget` with add/remove buttons or a simple text edit for comma-separated values) to manage the `skill_proficiencies` list.
    *   [ ] Add a widget (e.g., `QTableWidget` or a custom list widget) to manage the `origin_traits` list, allowing editing of both `name` and `description` for each trait.
    *   [ ] Ensure fields for `starting_location_id` and `starting_culture_id` use dropdowns populated from loaded locations/cultures for better linking.
    *   [ ] Update any references from "Scenario" to "Origin" in labels and tooltips.
*   [ ] **2.3. Update Data Models (`models/`)**
    *   [ ] Modify the Python data class(es) representing scenarios/origins (e.g., in `models/scenario_data.py`) to include `skill_proficiencies` (list of strings) and `origin_traits` (list of trait objects/dicts).
    *   [ ] Remove data models related to the old `backgrounds.json`.
*   [ ] **2.4. Update File Loading/Saving (`utils/file_manager.py` or similar):**
    *   [ ] Modify the loading logic to read the enhanced `origins.json` structure.
    *   [ ] Modify the saving logic to write the enhanced `origins.json` structure, including the new fields.
    *   [ ] Remove logic related to loading/saving `backgrounds.json`.
*   [ ] **2.5. Update Export Logic (`utils/import_export.py` or similar):**
    *   [ ] Ensure the "Export to Game" function correctly targets the game's `origins.json` file (or the chosen path).
    *   [ ] Verify that the exported JSON includes the new `skill_proficiencies` and `origin_traits` fields.
    *   [ ] Remove export options related to `backgrounds.json`.
*   [ ] **2.6. Update Validation (`utils/data_validator.py`):**
    *   [ ] Add validation rules to check the format and content of `skill_proficiencies` and `origin_traits`.
    *   [ ] (Optional) If you have a master skill list, validate proficiency names against it.
    *   [ ] Remove validation rules related to `backgrounds.json`.

**Phase 3: Core Game Engine Updates (`core/`)**

*   [ ] **3.1. Update Configuration Loading:**
    *   [ ] Modify the `StateManager`, `GameConfig`, or relevant loader to read `origins.json`.
    *   [ ] Remove code that loads `backgrounds.json`.
*   [ ] **3.2. Update Player State (`core/base/state.py` -> `PlayerState`):**
    *   [ ] Add fields to store the character's origin information:
        *   `origin_id` (string)
        *   `skill_proficiencies` (list of strings, or integrate with a broader skill system)
        *   `origin_traits` (list of objects/dicts with name/description)
*   [ ] **3.3. Update Character Creation Logic:**
    *   [ ] When a player selects an Origin during character creation:
        *   Store the selected `origin_id` in `PlayerState`.
        *   Apply the `skill_proficiencies` from the chosen Origin to the player's state.
        *   Apply the `origin_traits` from the chosen Origin to the player's state.
        *   Set the player's starting location using `starting_location_id`.
        *   Store the `starting_items` in the player's initial inventory.
        *   Add `initial_quests` to the player's quest log (when implemented).
*   [ ] **3.4. Remove Old Background Logic:**
    *   [ ] Remove any code that applied effects or skills based on the old `backgrounds.json` data.

**Phase 4: GUI Updates (`gui/`)**

*   [ ] **4.1. Update New Game Dialog (`gui/dialogs/new_game_dialog.py`):**
    *   [ ] Remove the UI element (e.g., dropdown, list) for selecting a "Background".
    *   [ ] Rename any UI elements referencing "Starting Scenario" to "Origin".
    *   [ ] Enhance the "Origin" selection widget/area:
        *   Display the list of available Origins (potentially filtered by Race/Class based on `suitable_races`/`classes`).
        *   When an Origin is selected/highlighted, display its `name`, `description`, `skill_proficiencies`, and `origin_traits` in informational text boxes or labels.
    *   [ ] Consider pre-populating the LLM background text area with the selected Origin's `introduction_text` as a starting point for the player.
*   [ ] **4.2. Update Character Sheet (Optional):**
    *   [ ] If the character sheet (`gui/components/character_sheet.py`) displays background info, update it to show the selected Origin `name` and potentially its `description` or `traits`.

**Phase 5: LLM Integration Updates (`core/agents/`, `core/llm/`)**

*   [ ] **5.1. Update Background Generation Prompt:**
    *   [ ] Modify the prompt template used for generating the detailed background story.
    *   [ ] Ensure the prompt receives the selected Origin's full details (`name`, `introduction_text`, `skill_proficiencies`, `origin_traits`, `starting_location_id`, `starting_culture_id`) along with Race and Class info.
    *   [ ] Add instructions for the LLM to weave these elements together, explaining *how* the character fits their Origin, starting location, and culture, expanding on the `introduction_text`.
*   [ ] **5.2. Update Initial Game Narration Prompt:**
    *   [ ] Modify the prompt template for the *first* narrative message after character creation.
    *   [ ] Provide the LLM with the final generated background story, the chosen Origin's `introduction_text`, and the `starting_location_id`.
    *   [ ] Instruct the LLM to use the `introduction_text` as the core for scene-setting at the starting location, possibly referencing the generated background for flavor.
*   [ ] **5.3. Consider New LLM Command (Optional):**
    *   [ ] Implement a command like `{GET_ORIGIN_INFO}` that allows agents to retrieve the player's `origin_id`, `skill_proficiencies`, and `origin_traits` from the `PlayerState` if needed for contextual responses later.

**Phase 6: Journal System Integration (Future Planning)**

*   [ ] **6.1. Design Journal Structure:**
    *   [ ] Plan a dedicated section in the Journal (e.g., "Character Origin" or "Background").
*   [ ] **6.2. Implement Journal Population:**
    *   [ ] When the Journal system is built, add logic to populate the Origin section after character creation with:
        *   Origin Name (`name` from `origins.json`)
        *   Origin Description (`description` from `origins.json`)
        *   Starting Location (`name` from `locations.json` via `starting_location_id`)
        *   Starting Culture (if applicable, `name` from `cultures.json` via `starting_culture_id`)
        *   Starting Plane (derived from `starting_location_id` in `locations.json`)
        *   List of `skill_proficiencies`
        *   List of `origin_traits` (name and description)
        *   The final LLM-generated background story.

**Phase 7: Testing and Refinement**

*   [ ] **7.1. Test Character Creation:** Create characters with various Race/Class/Origin combinations. Verify:
    *   Filtering works correctly.
    *   Correct information is displayed in the UI.
    *   Correct skills, traits, items, and location are applied to the `PlayerState`.
*   [ ] **7.2. Test LLM Generation:**
    *   Verify the LLM background generation uses the Origin details effectively.
    *   Verify the initial game narration sets the scene correctly based on the Origin's `introduction_text` and location.
*   [ ] **7.3. Test World Configurator:**
    *   Verify creating, editing, saving, loading, and exporting Origins works correctly with the new structure.

This checklist provides a comprehensive guide to implementing the suggested refactor. Remember to commit changes frequently and test each phase thoroughly. Good luck!