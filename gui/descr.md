Files I opened and read in full for this analysis:
- Right panel container and tabs
  - gui/components/right_panel.py
  - gui/components/character_sheet.py
  - gui/components/inventory_panel.py
  - gui/components/journal_panel.py
- Character creation and stat allocation
  - gui/dialogs/new_game_dialog.py
  - gui/dialogs/character_creation_dialog.py
  - gui/components/stat_allocation_widget.py
- Save/load dialogs
  - gui/dialogs/load_game_dialog.py
  - gui/dialogs/save_game_dialog.py
  - gui/dialogs/item_info_dialog.py
  - gui/dialogs/base_dialog.py
- Main window (signal wiring and orchestrated UI)
  - gui/main_window.py

What these GUI components actually do (ground truth)

1) CollapsibleRightPanel (gui/components/right_panel.py)
- A QFrame housing a QTabWidget (Character, Inventory, Journal).
- Custom tab bar emits “tab_clicked_twice” to toggle panel collapsed/expanded (width animation only; tabs remain visible).
- Styling matches dark panel with slightly transparent background.
- Exposes update_character(), update_inventory(), update_journal() that delegate to each tab widget.

2) CharacterSheetWidget (gui/components/character_sheet.py)
- Shows:
  - Header: portrait, name, race/class, level/exp, exp bar.
  - Resources: Health, Mana, Stamina (and Resolve), with progress bars and labels.
  - Combat Info: textual Status Effects, Turn Order list, and Initiative label.
  - Primary stat grid (STR/DEX/… incl. WIL/INS).
  - Derived stats (Melee/Ranged/Magic/Defense/Magic Defense/Damage Reduction/Carry/Movement).
  - Equipment grid by slot; each slot shows item label with context menu (Unequip, Item Info, Drop).
- Signal wiring and updates:
  - Listens to StatsManager.stats_changed to update primary/derived stats and resource maxes.
  - Actively fetches InventoryManager equipment and shows per-slot equipped items; encodes 2H weapon logic (MAIN_HAND shows “(2H)” and OFF_HAND blocked).
  - Handles orchestrated resource animations via slots:
    - player_resource_bar_update_phase1(bar_type, data)
    - player_resource_bar_update_phase2(bar_type, data)
  - Handles TURN_ORDER_UPDATE to rebuild the turn-order text and Initiative value. Uses CombatManager.entities and player’s combat entity for initiative.
  - Stat labels have dynamic tooltips; on right-click show modifiers (expects modifier_manager.get_modifiers_for_stat()).
- Emits signals (to MainWindow):
  - item_unequip_from_slot_requested(EquipmentSlot)
  - item_examine_requested(item_id)
  - item_drop_from_slot_requested(EquipmentSlot, item_id)

3) InventoryPanelWidget (gui/components/inventory_panel.py)
- Header: currency (gold/silver/copper) and weight (current/max).
- Filters: ItemType dropdown + text search field.
- Item list: shows “(Equipped)” and green color when applicable; supports right-click context menu with Examine, Use (consumables), Equip/Unequip (weapons/armor/etc.), Drop.
- Item details panel: name, type, description, placeholder grid for stats (currently not populated with item stat modifiers).
- Actions emit signals (handled by MainWindow):
  - item_use_requested(item_id)
  - item_examine_requested(item_id)
  - item_equip_requested(item_id)
  - item_unequip_requested(item_id)
  - item_drop_requested(item_id)
- update_inventory(inv_manager) reads:
  - currency gold/silver/copper (copper calculated mod copper_per_silver), current weight/limit
  - items inv_manager.items; filters by type and name; marks equipped items using inv_manager.is_item_equipped
- “Collect Dropped Items” button is a placeholder (not implemented).

4) JournalPanelWidget (gui/components/journal_panel.py)
- Tabs: Character, Quests, Notes
  - Character: free-form QTextEdit (journal_data["character"]).
  - Quests:
    - Three lists (Active, Completed, Failed) with context menus:
      - Active: per-objective actions “mark completed/failed”, open objective notes. “Abandon Quest” (moves to Failed with ABANDONED tag). Developer actions to force Completed/Failed.
      - Completed/Failed: notes-only menu listing objectives which have saved notes (disabled items when none).
    - Quest details pane with inline-styled HTML (status, objectives with strikethrough/colored states, notes, rewards).
    - Status computed: “completed” only when all mandatory objectives done and none failed; “failed” on abandoned or explicit; else “active”.
  - Notes: personal notes list + editor; add/delete/save; list items show “title - timestamp”.
- Exposes:
  - update_journal(journal_data) to set entire journal, repopulate UI.
  - clear_all() to blank all UI (used before loading saves).
  - journal_updated(dict) signal emitted on edits.

5) StatAllocationWidget (gui/components/stat_allocation_widget.py)
- Drives character creation stat allocation:
  - Depends on StatsManager + StatPointAllocator, and StatModifierInfo (race/class modifiers, min requirements, recommended stats, presets).
  - Grid with stat rows: base value, +/- buttons, race/class modifiers, total, ability mod. Tooltip on each cell explains sources.
  - Presets (from archetypes), auto/balanced allocation, reset.
  - Signals: stats_changed, allocation_complete. Provides get_allocated_stats() of base values.

6) NewGameDialog + CharacterCreationDialog (gui/dialogs/new_game_dialog.py, gui/dialogs/character_creation_dialog.py)
- Both load configuration via GameConfig (get_config()) reading local JSON:
  - Races: config.get_all("races")
  - Classes: config.get_all("classes")
  - Origins: config.get_all("origins")
- NewGameDialog gives basic form (name, race, class, origin, sex), shows origin details (description, skills, origin traits), backstory seed, portrait chooser scanning images/character_icons/<Race_Class>.
- CharacterCreationDialog extends into a tabbed flow:
  - Tab 1: Basic Info & Origin (with AI “Generate/Improve Backstory” hooks via get_narrator_agent()).
  - Tab 2/3: Stats allocation with StatAllocationWidget and stat info text (race/class modifiers, requirements, recommended).
  - Returns full character data including:
    - name, race, path, origin_id, sex, description (seed), use_llm, character_image
    - stats: allocated base stats (dict of STR/DEX/…)
    - starting_location_id, starting_items, initial_quests from selected origin
- Filtering of origins uses suitable_races and suitable_classes when populating the origin combo.
- The actual game start is triggered in MainWindow after panel fade-in, passing these values to GameEngine.start_new_game(...).

7) LoadGameDialog / SaveGameDialog / ItemInfoDialog (gui/dialogs/*.py)
- SaveGameDialog:
  - Lists existing saves by scanning /saves directory for *.json, sorted by mtime.
  - Lets user type a name and accept; MainWindow then calls engine.save_game(name).
- LoadGameDialog:
  - Scans /saves for *.json, lists in a table (save name, date, character), shows details by reading the json (player/world summary).
  - On accept, returns selected save file name; MainWindow calls engine.load_game(...)
- ItemInfoDialog:
  - Shows detailed item info (rarity, type, description, weight including total for stacks, currency value with totals, quantity, stack limit, durability current/max, equip slots, stats/effects, custom properties, tags).
  - Respects “known_properties” to hide unknown bits (fog-of-war-like reveal).

8) MainWindow (gui/main_window.py)
- Composition: MenuPanel (left), Center (Narrative/Combat stacked views with GameOutputWidget and CombatDisplay), RightPanel (CollapsibleRightPanel with Character/Inventory/Journal tabs). Title banner, music controls, status bar, background loader.
- Signal wiring:
  - Engine->UI orchestrated_event_to_ui → process_orchestrated_display_event
    - Handles BUFFER_FLUSH, UI_BAR_UPDATE_PHASE1/2 (routes to character sheet and entity widgets), TURN_ORDER_UPDATE (routes to character sheet), COMBAT_LOG_SET_HTML, and string content to either combat log or game output with gradual display flags.
  - Engine.output_generated → _handle_game_output (legacy/system messages).
  - StatsManager.stats_changed → _handle_stats_update → right_panel.update_character(state.player), combat_display.update_display if in combat.
  - RightPanel inventory signals → equip/unequip/use/drop/examine handlers; some actions route to command processing (use/drop), others call InventoryManager mechanics (equip/unequip) and then refresh UI.
- New game flow:
  - Opens CharacterCreationDialog (uses config and icons), then animates panels in, then calls GameEngine.start_new_game with name/race/path/origin_id, description as background, sex, image, and final base stats. Sets LLM enabled flag.
  - Initializes/ensures journal and stats manager; then updates UI and binds orchestrator to CombatManager if needed.
- Load/save:
  - Load dialog returns a save name; MainWindow clears orchestrator queue and both output widgets, clears right panel UI content to avoid stale data, calls engine.load_game, rebinds orchestrator if in combat, emits a consolidated stats_changed to force UI refresh, updates right panel character, etc.
  - Also a “Load last save” convenience using SaveManager.
