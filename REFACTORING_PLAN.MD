# RPG Development Task Checklist

## I. Core Item System & Initialization

### 1.1. Starting Item Initialization & Templates
-   **Files:**
    -   `core/game_flow/lifecycle.py` (modify `start_new_game_with_state`)
    -   **New File:** `config/items/origin_items.json` (to define templates for all items listed in `origins.json` `starting_items`)
    -   `config/items/base_weapons.json`, `config/items/base_armor.json`, `config/items/consumables.json`, `config/items/miscellaneous.json` (ensure these are loaded and potentially add base templates if `origin_items.json` refers to generic types not covered by specific origin item templates).
-   **Task:** Ensure all `starting_items` from `origins.json` can be successfully created and added to player inventory.
-   **Details:**
    -   [~] `lifecycle.py`: Modify `start_new_game_with_state` to iterate through `starting_items` from `origins.json`.
    -   [~] Each string in `starting_items` (e.g., "ritual_dagger", "ash-treated_clothing") will be treated as a `template_id`.
    -   [~] `ItemFactory.create_item_from_template(template_id, variation=False)` will be used.
    -   [~] `ItemTemplateLoader` must successfully load templates from `origin_items.json` and other item config files.
    -   [~] All items listed in any `origins.json` `starting_items` array **must** have a corresponding template definition in one of the item JSON files (preferably `origin_items.json` for specificity, or other files like `base_weapons.json` if it's a generic base item).
    -   [~] Add created items to the player's `InventoryManager`.
    -   [~] Ensure starting items are **not** automatically equipped.
    -   [~] Confirm this occurs *after* base character stats, racial, and class modifiers are applied.

### 1.2. Dice Roll Effects for Items
-   **File (New):** `core/inventory/item_effect.py`
    -   [~] Create `DiceRollEffect` dataclass (`effect_type: str`, `dice_notation: str`, `description: Optional[str]`, `to_dict()`, `from_dict()`).
-   **File:** `core/inventory/item.py`
    -   [~] Add `dice_roll_effects: List[DiceRollEffect] = field(default_factory=list)` to `Item` dataclass.
-   **Files:** `core/inventory/item_serialization.py`
    -   [~] Update `item_to_dict` and `dict_to_item` to handle `dice_roll_effects`.
-   **Files:** `config/items/*.json` (e.g., `base_weapons.json`, new `origin_items.json`)
    -   [ ] Update/add item templates to include a `dice_roll_effects` array where appropriate (e.g., weapons define their base physical damage, magical items define elemental damage). Example: `{"effect_type": "physical_damage", "dice_notation": "1d8"}`.
-   **File:** `core/inventory/item_variation_generator.py`
    -   [ ] Review `ItemVariationGenerator.create_variation`: For now, quality factor will primarily affect `Item.stats`, not `dice_roll_effects`.

### 1.3. Structured Item Naming & Generation Pipeline (New - Foundation for Dynamic Items)
-   **File (New):** `config/items/base_type_nouns.json`
    -   [ ] Create this file.
    -   [ ] Populate with mappings from base type nouns to primary `template_id`s (e.g., `"Longsword": "template_longsword_base"`, `"HealingPotion": "template_potion_healing_minor"`).
-   **File (New):** `config/items/adjectives.json`
    -   [ ] Create this file.
    -   [ ] Define adjectives, their applicable `ItemType`s, `stat_modifiers` (with min/max ranges for randomization), `value_multiplier`, `weight_multiplier`.
-   **File (New):** `config/items/rarity_modifiers.json`
    -   [ ] Create this file.
    -   [ ] Define effects of `ItemRarity` (e.g., percentage bonus to existing stats, value multipliers, chance for extra minor effects).
-   **File (New):** `config/items/special_name_effects.json`
    -   [ ] Create this file.
    -   [ ] Define predefined `DiceRollEffect`s or `ItemStat` modifications for common `specialName` parts (e.g., "flames" -> fire damage effect).
-   **File (New - Agent):** `core/agents/item_effect_suggester_agent.py` (or similar name)
    -   [ ] Create a new `ItemEffectSuggesterAgent` (inheriting `BaseAgent`).
    -   [ ] Implement a method like `suggest_effects_for_special_name(item_base_name: str, item_rarity: str, special_name_part: str, context: str) -> Dict[str, Any]`
        -   This method will use an LLM to generate structured JSON for `DiceRollEffect`s and/or `ItemStat` modifications based on an item's `specialName` part, its base type, rarity, and game context.
-   **File:** `core/inventory/item_factory.py`
    -   [ ] Add a new method: `create_item_from_structured_name(adjective: Optional[str], noun: str, special_name: Optional[str], rarity: ItemRarity, context_description: str) -> Optional[Item]`.
        -   This method will:
            1.  Use `noun` to get base `template_id` from `base_type_nouns.json`, then fetch the template.
            2.  Instantiate the base item from the template.
            3.  If `adjective` is provided, apply modifiers from `adjectives.json` (randomizing within min/max).
            4.  Apply modifiers based on `rarity` from `rarity_modifiers.json`.
            5.  If `special_name` is provided:
                *   Check `special_name_effects.json` for predefined effects and apply them.
                *   If not predefined (or for additional nuance), call the new `ItemEffectSuggesterAgent` to get LLM-suggested effects for the `special_name` and apply them.
            6.  Construct the final display name (e.g., "Fine Longsword of Flames").
            7.  Return the fully constructed `Item`.

## II. LLM Context & Item Handling

### 2.1. Item Name Uniqueness
-   **File:** `core/inventory/inventory_item_operations.py`
    -   [~] Modify `InventoryItemOperations.add_item` method to handle name collisions by appending sequential numbers (e.g., "Iron Dagger (2)") if an item with the exact same final display name is added to an inventory.

### 2.2. LLM Context Population
-   **File:** `core/agents/data_retrieval_commands.py` (`get_inventory_data`)
    -   [ ] **(Narrative Mode):** Structure return for `NarratorAgent` `additional_context["inventory"]` as:
        -   `equipped`: `Dict[str_slot_name, {"name": str, "id": str, "type": str}]`.
        -   `backpack`: `List[{"name": str, "id": str, "type": str, "quantity": int}]`.
-   **File:** `core/agents/agent_manager.py` (`_create_agent_context` or `process_input`)
    -   [ ] **(Combat Mode):** For `CombatNarratorAgent`, `additional_context` (or `combat_context.player_equipment`) should only contain player's *equipped* items (name, id, type, slot).
-   **File:** `core/agents/agent_manager.py` (`process_input`)
    -   [ ] Adjust default message for `GET_INVENTORY` (if LLM returns empty) to use the new simplified inventory structure.

### 2.3. NPC Inventory System & LLM Item Generation
-   **File:** `core/character/npc_base.py`
    -   [ ] Change `NPC.inventory` to `List[Item]`. Update `to_dict/from_dict`.
-   **File:** `core/character/npc_generator.py` (or new `_populate_inventory` method)
    -   [ ] When NPC generated/enhanced:
        *   Check NPC template for `default_items: List[str_template_id]`. If present, create and add to `NPC.inventory`.
        *   Else, if NPC type warrants inventory:
            *   Prepare `npc_profile` (name, type, etc.).
            *   Call `NarratorAgent.generate_npc_inventory_list(npc_profile)` (new method).
-   **File:** `core/agents/narrator.py`
    -   [ ] **New Method:** `generate_npc_inventory_list(npc_profile: Dict) -> List[Dict[str, Any]]`.
        -   Prompts LLM for a JSON list of item *name strings* (in `adjective_noun_specialName` format) and *rarities* suitable for the NPC.
        -   Example LLM Output: `[{"name_string": "crude_shortsword_none", "rarity": "common"}, {"name_string": "minor_healing_potion_none", "rarity": "common"}]`
        -   Returns this list of dictionaries.
-   **File:** `core/character/npc_generator.py` (Resuming `_populate_inventory`)
    -   For each dict from `NarratorAgent.generate_npc_inventory_list`:
        1.  Parse `name_string` into `adj, noun, specName`.
        2.  **Validation & Correction Loop (Handled by `NPCGenerator`):**
            *   Validate `noun` against `base_type_nouns.json`. If fail -> call `NarratorAgent.correct_item_name(original_name, problem, context, required_format="noun")`.
            *   Validate `adj` against `adjectives.json`. If fail -> call `NarratorAgent.correct_item_name(original_name, problem, context, required_format="adjective")`.

## III. GUI Enhancements

### 3.1. Character Sheet Widget (`gui/components/character_sheet.py`)
-   **Stat Display & Tooltips:**
    -   [ ] In `_update_stat_display` (or equivalent methods for primary and derived stats):
        -   [ ] Compare the current stat value with its base value (requires `StatsManager` to expose base values or for `PlayerState` to store them if not already).
        -   [ ] If `current_value > base_value`, set the stat label's text color to GREEN (configurable).
        -   [ ] If `current_value < base_value`, set the stat label's text color to RED (configurable).
        -   [ ] If `current_value == base_value`, use the default text color.
        -   [ ] For modified stats, set a tooltip on the label.
        -   [ ] The tooltip text should list each active modifier: "Source Name 1: +/-Value\nSource Name 2: +/-Value".
        -   [ ] This may require a new method in `StatsManager` like `get_stat_modifier_details_for_tooltip(stat_type: StatType) -> List[Tuple[str, float]]`.
-   **Combat Status Section Removal:**
    -   [ ] Remove the `QGroupBox` and its layout related to "Combat Status" from the `CharacterSheetWidget` UI setup.
-   **Stats & Skills Section Toggling:**
    -   [ ] Add a `QPushButton` named "Stats" below the "Resources" section.
    -   [ ] Connect its `clicked` signal to a slot that toggles the visibility of `self.primary_stats_group` and `self.derived_stats_group`.
    -   [ ] Add a `QPushButton` named "Skills" below the new "Stats" button.
    -   [ ] Set the "Skills" button to be initially disabled (`setEnabled(False)`).
    -   [ ] (Future: Connect "Skills" button to toggle visibility of a skills group box).
-   **New "Equipment" Section:**
    -   [ ] Add a new `QGroupBox` titled "Equipment" to `CharacterSheetWidget`.
    -   [ ] Inside this group box, add a `QListWidget` (e.g., `self.equipment_list_widget`).
    -   [ ] Populate this list with "Slot Name: Item Name" for each equipped item from `InventoryManager.equipment`. This list needs to be updated whenever equipment changes.
    -   [ ] Implement `customContextMenuRequested` for `self.equipment_list_widget`.
    -   [ ] **Context Menu Actions:**
        -   [ ] "Unequip":
            -   Identify the `EquipmentSlot` of the selected item.
            -   Emit a new signal: `item_unequip_from_slot_requested = Signal(EquipmentSlot)`.
        -   [ ] "Item Information":
            -   Identify the `Item` object.
            -   Create and show a new modal `QDialog` (e.g., `ItemInfoDialog`).
            -   The `ItemInfoDialog` should display: Name, Type, Rarity, Description, Weight, Value (formatted currency), Durability (current/max, if applicable), Equip Slots, Known Stats (name: value, formatted), Known Custom Properties (name: value), Tags. This dialog will need to be created.
        -   [ ] "Drop":
            -   Show a `QMessageBox.question` for confirmation ("Are you sure you want to drop [Item Name]? This action cannot be undone.").
            -   If confirmed, identify the `EquipmentSlot` and `item_id`.
            -   Emit a new signal: `item_drop_from_slot_requested = Signal(EquipmentSlot, str)`.
-   **Signal Handling in `MainWindow` or `GameEngine` for new CharacterSheet signals:**
    -   [ ] Connect `item_unequip_from_slot_requested` to a handler that calls `InventoryManager.unequip_item(slot)`.
    -   [ ] Connect `item_drop_from_slot_requested` to a handler that calls `InventoryManager.unequip_item(slot)` and then `InventoryManager.remove_item(item_id)`.
    -   [ ] After these actions, ensure `CharacterSheetWidget` and `InventoryPanelWidget` are updated.

### 3.2. Combat Display Widget (`gui/components/combat_display.py`)
-   **Visual Turn Indicator:**
    -   [ ] In `CombatEntityWidget.highlight_active(active: bool)`:
        -   [ ] If `active` is true, set the widget's background color to a configurable "active turn highlight" color (e.g., from `self.settings.get("color_entity_active_bg_highlight", "yellow")`).
        -   [ ] If `active` is false, revert to the normal player/enemy background color based on `self.is_player` and current settings.

### 3.3. Inventory Panel Widget (`gui/components/inventory_panel.py`)
-   **Equip Action - Slot Presentation:**
    -   [ ] Modify `_show_context_menu` (or the handler for the "Equip" action).
    -   [ ] When "Equip" is selected for an unequipped item:
        -   Get the item's `equip_slots` from its `Item` object.
        -   Get currently equipped items from `InventoryManager.equipment`.
        -   Determine valid and *empty* slots for the item.
        -   Determine valid but *occupied* slots.
        -   **If one or more valid empty slots exist:** Create a sub-menu listing these empty slots. User selection triggers `item_equip_requested.emit(item_id, selected_empty_slot)`.
        -   **If no valid empty slots, but valid occupied slots exist:** Create a sub-menu listing these occupied slots, perhaps suffixed with "(replace [current_item_name])". User selection triggers an attempt to unequip the current item and then equip the new one. This might need a confirmation dialog. *For simplicity in this phase, if all valid slots are occupied, the "Equip" action could initially just show a message "No free slot of the correct type." or only list slots that can be directly equipped to (if they are empty). The sub-menu for replacing items can be a further refinement.*
            *   **Agreed Simplification:** For now, if only occupied slots are valid, the "Equip" action via context menu will attempt to unequip the existing item in the *first valid slot for the new item* and then equip the new item. A more nuanced selection for replacement can be future work.
            *   The `item_equip_requested` signal should probably take `(item_id_to_equip, preferred_slot_to_equip_in)`. `InventoryManager.equip_item` already has logic for handling occupied preferred slots.

## IV. Combat Flow & Agent Logic

### 4.1. Rule Checker Integration for Player Combat Commands
-   **File:** `core/game_flow/input_router.py` (or `core/game_engine.py` if input routing is simpler)
    -   **Task:** Modify the part that handles player textual input when `game_state.current_mode == InteractionMode.COMBAT`.
    -   **Details:**
        -   [ ] Before the textual command is passed to `CombatManager._step_processing_player_action` (which then calls `CombatNarratorAgent`):
            *   Construct an `AgentContext` for the `RuleCheckerAgent`. This context should reflect `InteractionMode.COMBAT`.
            *   Call `RuleCheckerAgent.validate_action(context_for_rule_checker, player_text_command)`.
            *   If `is_valid` is `False`:
                *   Send the `reason` from `RuleCheckerAgent` to the player via `CombatOutputOrchestrator` (as a system message to `COMBAT_LOG`).
                *   The `CombatManager` should remain in `CombatStep.AWAITING_PLAYER_INPUT`.
                *   The `GameInputWidget` should be re-enabled for player input.
            *   If `is_valid` is `True`, proceed with the current flow (passing the command to `CombatManager` for processing by `CombatNarratorAgent`).

## V. Data Retrieval & Context (AgentManager)

### 5.1. Simplified Inventory Data for `GET_INVENTORY` (Narrative Mode)
-   **File:** `core/agents/data_retrieval_commands.py`
    -   **Task:** Modify `get_inventory_data`.
    -   **Details:**
        -   [ ] The dictionary returned should be structured to produce the desired simplified format for `NarratorAgent`'s `additional_context["inventory"]`:
            -   A top-level key `equipped`: `Dict[str, Dict[str, str]]` (slot_name -> `{"name": ..., "id": ..., "type": ...}`)
            -   A top-level key `backpack`: `List[Dict[str, Union[str, int]]]` (list of `{"name": ..., "id": ..., "type": ..., "quantity": ...}`)
-   **File:** `core/agents/agent_manager.py`
    -   **Task:** Adjust the default message generation in `process_input` if the LLM returns empty after `GET_INVENTORY`.
    -   **Details:**
        -   [ ] Ensure the fallback message correctly iterates over the new `equipped` and `backpack` structure to list items.


VI. Additonal improvements:
 6.1 discover more infromation about given item:
    - implement statistical probability calculation (involve dice roll?) for marking given item as 'mysterious' -> once an item (even ordinary one) would be marked as such, user could be focusing on diccovering more information on it
    - information expansion on given item could happen in specified circumstances such as:
        - buing more information from appropriate vendor (e.g. sage -> to be defined the exact mechanics and logic)
        - using appropriate spell (to be implemented in magic system)
        - in course of narrative developpement e.g. LLM narrator would decide that some new infromation about a given item is discovered
    
---

This checklist provides a detailed breakdown. I will proceed with these changes.