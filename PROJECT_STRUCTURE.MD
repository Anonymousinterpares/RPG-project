new project
├── config/
│   ├── character/
│   │   ├── backup/
│   │   │   ├── classes_20250418_133031.json
│   │   │   ├── classes_20250418_135120.json
│   │   │   ├── races_20250418_131835.json
│   │   │   ├── races_20250418_132122.json
│   │   │   ├── races_20250418_132911.json
│   │   │   └── races_20250418_135120.json
│   │   ├── backgrounds.json
│   │   ├── classes.json
│   │   ├── npc_templates.json
│   │   ├── races.json
│   │   └── stats_config.json
│   ├── combat/
│   │   └── combat_config.json
│   ├── game/
│   │   └── base_config.json
│   ├── items/
│   │   ├── base_armor.json
│   │   ├── base_weapons.json
│   │   ├── consumables.json
│   │   └── miscellaneous.json
│   ├── llm/
│   │   ├── agents/
│   │   │   ├── combatnarrator.json
│   │   │   ├── context_evaluator.json
│   │   │   ├── narrator.json
│   │   │   └── rule_checker.json
│   │   ├── base_config.json
│   │   ├── models.json
│   │   └── providers.json
│   ├── world/
│   │   ├── base/
│   │   │   ├── cultures.json
│   │   │   ├── fundamental_rules.json
│   │   │   ├── magic_systems.json
│   │   │   └── world_history.json
│   │   ├── locations/
│   │   │   └── locations.json
│   │   └── scenarios/
│   │       ├── origins.json
│   │       └── quests.json
│   ├── game_config.json
│   ├── gui_config.json
│   ├── llm_config.json
│   ├── skills.json
│   └── system_config.json
├── core/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent_manager.py
│   │   ├── base_agent.py
│   │   ├── combat_narrator.py
│   │   ├── context_evaluator.py
│   │   ├── data_retrieval_commands.py
│   │   ├── narrator.py
│   │   ├── rule_checker.py
│   │   ├── social_conflict_agent.py
│   │   └── trade_agent.py
│   ├── base/
│   │   ├── state/
│   │   │   ├── __init__.py
│   │   │   ├── game_state.py
│   │   │   ├── player_state.py
│   │   │   ├── state_manager.py
│   │   │   ├── stats_integration.py
│   │   │   └── world_state.py
│   │   ├── __init__.py
│   │   ├── commands.py
│   │   ├── config.py
│   │   ├── engine.py
│   │   ├── game_loop.py
│   │   ├── init_modules.py
│   │   └── state.py
│   ├── character/
│   │   ├── __init__.py
│   │   ├── background_generator.py
│   │   ├── npc_base.py
│   │   ├── npc_creator.py
│   │   ├── npc_generator.py
│   │   ├── npc_manager.py
│   │   ├── npc_memory.py
│   │   ├── npc_persistence.py
│   │   └── npc_system.py
│   ├── combat/
│   │   ├── __init__.py
│   │   ├── combat_action.py
│   │   ├── combat_entity.py
│   │   ├── combat_manager.py
│   │   └── dev_commands.py
│   ├── game_flow/
│   │   ├── __init__.py
│   │   ├── command_handlers.py
│   │   ├── command_router.py
│   │   ├── game_flow_utils.py
│   │   ├── input_router.py
│   │   ├── interaction_core.py
│   │   ├── interaction_processor.py
│   │   ├── lifecycle.py
│   │   ├── mode_transitions.py
│   │   ├── npc_interaction.py
│   │   └── request_handlers.py
│   ├── interaction/
│   │   ├── context_builder.py
│   │   ├── enums.py
│   │   ├── social_effects.py
│   │   └── structured_requests.py
│   ├── inventory/
│   │   ├── __init__.py
│   │   ├── currency_manager.py
│   │   ├── equipment_manager.py
│   │   ├── inventory_base.py
│   │   ├── inventory_commands.py
│   │   ├── inventory_commands_2.py
│   │   ├── inventory_commands_3.py
│   │   ├── inventory_item_operations.py
│   │   ├── inventory_limits.py
│   │   ├── inventory_manager.py
│   │   ├── item.py
│   │   ├── item_enums.py
│   │   ├── item_factory.py
│   │   ├── item_manager.py
│   │   ├── item_modifier.py
│   │   ├── item_serialization.py
│   │   ├── item_stat.py
│   │   ├── item_stat_modifier.py
│   │   ├── item_template_loader.py
│   │   ├── item_variation_generator.py
│   │   ├── narrative_item_creation.py
│   │   ├── narrative_item_discovery.py
│   │   ├── narrative_item_manager.py
│   │   └── narrative_item_mappings.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── llm_manager.py
│   │   ├── provider_manager.py
│   │   ├── settings_cli.py
│   │   ├── settings_manager.py
│   │   └── settings_manager_new.py
│   ├── stats/
│   │   ├── enums/
│   │   │   └── __init__.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   └── test_stats_manager.py
│   │   ├── __init__.py
│   │   ├── combat_effects.py
│   │   ├── derived_stats.py
│   │   ├── enums.py
│   │   ├── modifier.py
│   │   ├── modifier_manager.py
│   │   ├── skill_check.py
│   │   ├── skill_manager.py
│   │   ├── stat_allocation.py
│   │   ├── stat_modifier_info.py
│   │   ├── stats_base.py
│   │   └── stats_manager.py
│   ├── utils/
│   │   ├── dice.py
│   │   ├── dotdict.py
│   │   ├── json_utils.py
│   │   ├── logging_config.py
│   │   ├── save_manager.py
│   │   └── time_utils.py
│   └── __init__.py
├── gui/
│   ├── components/
│   │   ├── character_sheet.py
│   │   ├── combat_display.py
│   │   ├── command_input.py
│   │   ├── game_menu.py
│   │   ├── game_output.py
│   │   ├── inventory_panel.py
│   │   ├── journal_panel.py
│   │   ├── menu_panel.py
│   │   ├── right_panel.py
│   │   ├── skill_check_display.py
│   │   ├── stat_allocation_widget.py
│   │   └── status_bar.py
│   ├── dialogs/
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── agent_setup_tab.py
│   │   │   ├── anthropic_tab.py
│   │   │   ├── background_tab.py
│   │   │   ├── base_settings_dialog.py
│   │   │   ├── llm_general_tab.py
│   │   │   ├── llm_provider_tab.py
│   │   │   ├── llm_settings_dialog.py
│   │   │   ├── model_management_widget.py
│   │   │   ├── provider_tabs.py
│   │   │   ├── settings_dialog.py
│   │   │   └── style_tab.py
│   │   ├── __init__.py
│   │   ├── character_creation_dialog.py
│   │   ├── load_game_dialog.py
│   │   ├── new_game_dialog.py
│   │   └── save_game_dialog.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── init_settings.py
│   │   └── resource_manager.py
│   └── main_window.py
├── images/
│   ├── character_icons/
│   ├── gui/
│   │   ├── background/
│   │   ├── colors/
│   │   │   └── placeholder_creator.py
│   │   ├── textures/
│   │   └── placeholder_creator.py
│   └── icons/
├── logs/
├── saves/
│   ├── backups/
│   ├── npcs/
│   ├── test1.json
│   └── test2.json
├── selected_files_documentation_25.04.2025_22_17_26_output/
├── sound/
├── tests/
│   ├── __init__.py
│   └── test_stats_system.py
├── web/
│   ├── client/
│   │   ├── css/
│   │   └── js/
│   └── server/
│       └── server.py
├── world_configurator/
│   ├── data/
│   ├── logs/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base_models.py
│   │   ├── location_data.py
│   │   ├── origin_data.py
│   │   ├── world_config.py
│   │   └── world_data.py
│   ├── ui/
│   │   ├── dialogs/
│   │   │   ├── __init__.py
│   │   │   ├── export_dialog.py
│   │   │   ├── new_project_dialog.py
│   │   │   └── settings_dialog.py
│   │   ├── editors/
│   │   │   ├── __init__.py
│   │   │   ├── class_editor.py
│   │   │   ├── culture_editor.py
│   │   │   ├── history_editor.py
│   │   │   ├── location_editor.py
│   │   │   ├── magic_systems_editor.py
│   │   │   ├── origin_editor.py
│   │   │   ├── quest_editor.py
│   │   │   └── race_editor.py
│   │   ├── __init__.py
│   │   └── main_window.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── data_validator.py
│   │   ├── file_manager.py
│   │   └── logging_setup.py
│   ├── __init__.py
│   └── main.py
├── world_configurator.egg-info/
├── create_color_swatches.py
├── create_texture.py
├── create_textures.py
├── main.py
├── manage_llm_settings.py
├── run_gui.py
├── setup.py
├── simulation_stats.json
├── start_server.py
└── test_inventory.py