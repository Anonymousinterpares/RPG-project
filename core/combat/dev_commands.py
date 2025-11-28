#!/usr/bin/env python3
"""
Developer commands for the combat system.

This module provides developer commands for testing and debugging the combat system.
"""

import logging
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING
import uuid

from core.base.commands import CommandProcessor, CommandResult
from core.base.state import GameState, get_state_manager
from core.interaction.enums import InteractionMode
from core.utils.logging_config import get_logger
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import CombatAction, ActionType, AttackAction
from core.combat.enums import CombatStep
from core.character.npc_system import NPCSystem
from core.stats.stats_base import StatType, DerivedStatType
from core.stats.stats_manager import get_stats_manager
from core.game_flow.npc_interaction import trigger_combat_narration

if TYPE_CHECKING:
    from core.combat.combat_manager import CombatManager

# Get the module logger
logger = get_logger("GAME")

def register_combat_dev_commands(command_processor: CommandProcessor):
    """Register all combat-related developer commands."""
    
    command_processor.register_dev_command(
        name="start_combat",
        handler=dev_start_combat,
        syntax="//start_combat <enemy_template> [level] [count]",
        description="Start a combat encounter with specified enemies.",
        examples=[
            "start_combat bandit",
            "start_combat wolf 3",
            "start_combat goblin 2 3"
        ]
    )

    # List authored spells
    command_processor.register_dev_command(
        name="list_spells",
        handler=dev_list_spells,
        syntax="//list_spells",
        description="List known spell IDs from the SpellCatalog.",
        examples=["list_spells"]
    )

    # Player spellbook management (Developer Mode)
    command_processor.register_dev_command(
        name="learn_spell",
        handler=dev_learn_spell,
        syntax="//learn_spell <spell_id>",
        description="Learn a spell by id and add it to the player's known spells.",
        examples=["learn_spell prismatic_bolt"]
    )
    command_processor.register_dev_command(
        name="forget_spell",
        handler=dev_forget_spell,
        syntax="//forget_spell <spell_id>",
        description="Forget a spell by id, removing it from the player's known spells.",
        examples=["forget_spell prismatic_bolt"]
    )
    command_processor.register_dev_command(
        name="known_spells",
        handler=dev_known_spells,
        syntax="//known_spells",
        description="List the player's currently known spells.",
        examples=["known_spells"]
    )

    # Execute a spell by id, optional target id
    command_processor.register_dev_command(
        name="cast",
        handler=dev_cast_spell,
        syntax="//cast <spell_id> [target_id]",
        description="Execute a spell by id using the effects interpreter (optional target id).",
        examples=[
            "cast prismatic_bolt",
            "cast prismatic_bolt ghoul_1"
        ]
    )
    
    logger.info("Registered combat developer commands")
    

def create_player_combat_entity(game_state: GameState, combat_name: str) -> CombatEntity: 
    """Creates a CombatEntity for the player."""
    player_state = game_state.player
    stats_manager = get_stats_manager()

    max_hp = stats_manager.get_stat_value(DerivedStatType.MAX_HEALTH)
    max_mp = stats_manager.get_stat_value(DerivedStatType.MAX_MANA)
    max_stamina = stats_manager.get_stat_value(DerivedStatType.MAX_STAMINA)

    current_hp = stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
    current_mp = stats_manager.get_current_stat_value(DerivedStatType.MANA)
    current_stamina = stats_manager.get_current_stat_value(DerivedStatType.STAMINA)

    current_hp = min(current_hp, max_hp)
    current_mp = min(current_mp, max_mp)
    current_stamina = min(current_stamina, max_stamina)

    all_stats_dict = {stat_enum: stats_manager.get_stat_value(stat_enum) for stat_enum in stats_manager.stats}
    all_stats_dict.update({stat_enum: stats_manager.get_stat_value(stat_enum) for stat_enum in stats_manager.derived_stats})

    return CombatEntity(
        id=player_state.stats_manager_id or "player_default_id",
        name=player_state.name,
        combat_name=combat_name, #
        entity_type=EntityType.PLAYER,
        stats=all_stats_dict,
        current_hp=current_hp,
        max_hp=max_hp,
        current_mp=current_mp,
        max_mp=max_mp,
        current_stamina=current_stamina,
        max_stamina=max_stamina,
        description=f"{player_state.race} {player_state.path}"
    )

def create_enemy_combat_entity(npc, combat_name: str) -> CombatEntity:
    """Creates a CombatEntity for an enemy NPC."""
    if not hasattr(npc, 'stats_manager'):
        raise ValueError(f"NPC {getattr(npc, 'name', 'Unknown')} is missing a stats_manager.")

    stats_manager = npc.stats_manager

    max_hp = stats_manager.get_stat_value(DerivedStatType.MAX_HEALTH)
    max_mp = stats_manager.get_stat_value(DerivedStatType.MAX_MANA)
    max_stamina = stats_manager.get_stat_value(DerivedStatType.MAX_STAMINA)

    current_hp = stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
    current_mp = stats_manager.get_current_stat_value(DerivedStatType.MANA)
    current_stamina = stats_manager.get_current_stat_value(DerivedStatType.STAMINA)

    current_hp = min(current_hp, max_hp)
    current_mp = min(current_mp, max_mp)
    current_stamina = min(current_stamina, max_stamina)

    all_stats_dict = {stat_enum: stats_manager.get_stat_value(stat_enum) for stat_enum in stats_manager.stats}
    all_stats_dict.update({stat_enum: stats_manager.get_stat_value(stat_enum) for stat_enum in stats_manager.derived_stats})


    return CombatEntity(
        id=npc.id,
        name=npc.name,
        combat_name=combat_name, 
        entity_type=EntityType.ENEMY,
        stats=all_stats_dict,
        current_hp=current_hp,
        max_hp=max_hp,
        current_mp=current_mp,
        max_mp=max_mp,
        current_stamina=current_stamina,
        max_stamina=max_stamina,
        description=getattr(npc, 'description', '')
    )

def dev_list_spells(game_state: GameState, args: List[str]) -> CommandResult:
    """List known spells from the SpellCatalog."""
    try:
        from core.magic.spell_catalog import get_spell_catalog
        cat = get_spell_catalog(force_reload=True)
        ids = cat.list_known_spells()
        if not ids:
            msg = "No spells found in catalog."
            _emit_dev_feedback(msg, is_combat=(game_state.current_mode == InteractionMode.COMBAT))
            return CommandResult.success(msg)
        out = ["Known spells:"] + [f"- {sid}" for sid in ids]
        msg = "\n".join(out)
        _emit_dev_feedback(msg, is_combat=(game_state.current_mode == InteractionMode.COMBAT))
        return CommandResult.success(msg)
    except Exception as e:
        logger.error(f"list_spells failed: {e}", exc_info=True)
        msg = f"Failed to list spells: {e}"
        _emit_dev_feedback(msg, is_combat=(game_state.current_mode == InteractionMode.COMBAT))
        return CommandResult.error(msg)


def _emit_dev_feedback(message: str, is_combat: bool) -> None:
    """Helper to route dev command feedback to the right channel."""
    try:
        from core.base.engine import get_game_engine
        engine = get_game_engine()
        if is_combat and hasattr(engine, '_combat_orchestrator'):
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
            engine._combat_orchestrator.add_event_to_queue(
                DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=message, target_display=DisplayTarget.COMBAT_LOG)
            )
        else:
            engine._output("system", message)
    except Exception:
        # As a fallback, just log it
        logger.info(message)


def dev_learn_spell(game_state: GameState, args: List[str]) -> CommandResult:
    """Learn a spell by id and add it to the player's known spells (Developer Mode)."""
    if not args:
        return CommandResult.invalid("Usage: //learn_spell <spell_id>")
    spell_id = str(args[0]).strip()
    try:
        from core.magic.spell_catalog import get_spell_catalog
        catalog = get_spell_catalog(force_reload=True)
        sp = catalog.get_spell_by_id(spell_id)
        if not sp:
            msg = f"Unknown spell id: {spell_id}"
            _emit_dev_feedback(msg, is_combat=(game_state.current_mode == InteractionMode.COMBAT))
            return CommandResult.failure(msg)
        added = game_state.player.add_known_spell(spell_id)
        if added:
            msg = f"Learned spell '{sp.name}' ({sp.id})."
        else:
            msg = f"Spell '{sp.id}' is already known."
        _emit_dev_feedback(msg, is_combat=(game_state.current_mode == InteractionMode.COMBAT))
        return CommandResult.success(msg)
    except Exception as e:
        logger.error(f"learn_spell failed: {e}", exc_info=True)
        return CommandResult.error(f"Failed to learn spell: {e}")


def dev_forget_spell(game_state: GameState, args: List[str]) -> CommandResult:
    """Forget a spell by id, removing it from the player's known spells (Developer Mode)."""
    if not args:
        return CommandResult.invalid("Usage: //forget_spell <spell_id>")
    spell_id = str(args[0]).strip()
    try:
        removed = game_state.player.remove_known_spell(spell_id)
        if removed:
            msg = f"Forgot spell '{spell_id}'."
            status = CommandResult.success
        else:
            msg = f"Spell '{spell_id}' not found in known spells."
            status = CommandResult.failure
        _emit_dev_feedback(msg, is_combat=(game_state.current_mode == InteractionMode.COMBAT))
        return status(msg)
    except Exception as e:
        logger.error(f"forget_spell failed: {e}", exc_info=True)
        return CommandResult.error(f"Failed to forget spell: {e}")


def dev_known_spells(game_state: GameState, args: List[str]) -> CommandResult:
    """List the player's currently known spells (Developer Mode)."""
    try:
        known = game_state.player.list_known_spells()
        if not known:
            msg = "You do not know any spells yet."
            _emit_dev_feedback(msg, is_combat=(game_state.current_mode == InteractionMode.COMBAT))
            return CommandResult.success(msg)
        # Optionally resolve names from catalog
        try:
            from core.magic.spell_catalog import get_spell_catalog
            cat = get_spell_catalog()
            lines = ["Known spells:"]
            for sid in sorted(known):
                sp = cat.get_spell_by_id(sid)
                if sp:
                    lines.append(f"- {sp.id} ({sp.name})")
                else:
                    lines.append(f"- {sid}")
            msg = "\n".join(lines)
        except Exception:
            msg = "Known spells:\n" + "\n".join(f"- {sid}" for sid in sorted(known))
        _emit_dev_feedback(msg, is_combat=(game_state.current_mode == InteractionMode.COMBAT))
        return CommandResult.success(msg)
    except Exception as e:
        logger.error(f"known_spells failed: {e}", exc_info=True)
        return CommandResult.error(f"Failed to list known spells: {e}")


def dev_cast_spell(game_state: GameState, args: List[str]) -> CommandResult:
    """Execute a spell by id or name (optional target id). In combat, route via CombatManager with proper orchestration."""
    if not args:
        return CommandResult.invalid("Usage: //cast <spell_id_or_name> [target_id]")

    raw_query = str(args[0]).strip()
    explicit_target_id = str(args[1]).strip() if len(args) > 1 and args[1] else None

    try:
        from core.base.engine import get_game_engine
        engine = get_game_engine()

        # If not in combat, use pure engine path for quick testing (no orchestrated events)
        if game_state.current_mode != InteractionMode.COMBAT or not getattr(game_state, 'combat_manager', None):
            try:
                # Resolve fuzzy id first to avoid confusion out of combat
                from core.magic.spell_catalog import get_spell_catalog
                cat = get_spell_catalog()
                player_known = getattr(game_state.player, 'known_spells', []) or []
                # Allow broad scope for dev casts out of combat
                resolved_id = cat.resolve_spell_id(raw_query, scope_ids=player_known, allow_broad_scope=True) or raw_query
                result = engine.execute_cast_spell(resolved_id, explicit_target_id)
                # Emit feedback in narrative log if available
                _emit_dev_feedback(result.message if hasattr(result, 'message') else str(result), is_combat=False)
                return result
            except Exception as inner_e:
                logger.error(f"Out-of-combat dev cast failed: {inner_e}", exc_info=True)
                return CommandResult.error(f"Failed to cast: {inner_e}")

        # In COMBAT: build a proper CombatAction (SpellAction) and let orchestrator handle
        cm = game_state.combat_manager
        if not cm:
            return CommandResult.error("Combat manager not available.")

        # Resolve canonical spell id from query against player's known spells, fallback to full catalog in Dev Mode
        try:
            from PySide6.QtCore import QSettings
            dev_enabled = bool(QSettings("RPGGame", "Settings").value("dev/enabled", False, type=bool))
        except Exception:
            dev_enabled = False

        from core.magic.spell_catalog import get_spell_catalog
        cat = get_spell_catalog()
        player_known = getattr(game_state.player, 'known_spells', []) or []
        resolved_sid = cat.resolve_spell_id(raw_query, scope_ids=player_known, allow_broad_scope=dev_enabled)
        if not resolved_sid:
            # Last resort: scan free-text query
            resolved_sid = cat.resolve_spell_from_text(raw_query, scope_ids=player_known, allow_broad_scope=dev_enabled)
        if not resolved_sid:
            msg = f"Cannot resolve spell from '{raw_query}'."
            _emit_dev_feedback(msg, is_combat=True)
            return CommandResult.failure(msg)

        sp = cat.get_spell_by_id(resolved_sid)
        if not sp:
            msg = f"Unknown spell id: {resolved_sid}"
            _emit_dev_feedback(msg, is_combat=True)
            return CommandResult.failure(msg)

        # Determine mana cost from catalog
        try:
            catalog_cost = float((sp.data or {}).get('mana_cost', 5.0))
        except Exception:
            catalog_cost = 5.0

        # Determine performer and target(s)
        performer_id = getattr(cm, '_player_entity_id', None)
        if not performer_id:
            # Fallback: find player entity
            try:
                from core.combat.combat_entity import EntityType
                player_entity = next((e for e in cm.entities.values() if getattr(e, 'entity_type', None) == EntityType.PLAYER), None)
                performer_id = player_entity.id if player_entity else None
            except Exception:
                performer_id = None
        if not performer_id:
            msg = "Developer cast aborted: player entity not found in combat."
            _emit_dev_feedback(msg, is_combat=True)
            return CommandResult.failure(msg)

        final_target_ids: List[str] = []
        if explicit_target_id:
            final_target_ids = [explicit_target_id]
        else:
            role = getattr(sp, 'combat_role', 'offensive') or 'offensive'
            if role == 'defensive':
                final_target_ids = [performer_id]
            elif role == 'offensive':
                try:
                    from core.combat.combat_entity import EntityType
                    alive_enemies = [e.id for e in cm.entities.values() if getattr(e, 'entity_type', None) == EntityType.ENEMY and getattr(e, 'is_active_in_combat', True) and e.is_alive()]
                    if len(alive_enemies) == 1:
                        final_target_ids = alive_enemies
                    elif len(alive_enemies) > 1:
                        import random
                        final_target_ids = [random.choice(alive_enemies)]
                except Exception:
                    final_target_ids = []
            else: # utility in combat -> blocked
                msg = "This spell can only be used outside of combat."
                _emit_dev_feedback(msg, is_combat=True)
                return CommandResult.failure(msg)

        # Create and enqueue the SpellAction
        try:
            from core.combat.combat_action import SpellAction
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
            # Attempt narrative is typically generated by agent; for dev cast, issue a system line
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=f"[DEV] Casting {sp.name} ({sp.id})", target_display=DisplayTarget.COMBAT_LOG))
            cm._pending_action = SpellAction(performer_id=performer_id, spell_name=sp.id, target_ids=final_target_ids, cost_mp=catalog_cost, dice_notation="")
            cm.current_step = CombatStep.RESOLVING_ACTION_MECHANICS
            cm.waiting_for_display_completion = True
            _emit_dev_feedback(f"Queued spell {sp.id} for casting.", is_combat=True)
            # Nudge the combat loop to proceed
            try:
                cm.process_combat_step(engine)
            except Exception as nudge_err:
                logger.debug(f"Non-fatal: direct process_combat_step nudge failed: {nudge_err}")
            return CommandResult.success(f"Casting {sp.id} queued.")
        except Exception as queue_err:
            logger.error(f"Failed to queue dev spell action: {queue_err}", exc_info=True)
            return CommandResult.error(f"Failed to queue cast: {queue_err}")

    except Exception as e:
        logger.error(f"cast failed: {e}", exc_info=True)
        return CommandResult.error(f"Failed to cast: {e}")


def dev_start_combat(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Initiates combat mode with specified enemies.
    """
    # IMPORT HERE TO AVOID CIRCULAR DEPENDENCY
    from core.combat.combat_manager import CombatManager

    if game_state.current_mode == InteractionMode.COMBAT:
        return CommandResult.failure("Already in combat.")

    if not args:
        return CommandResult.invalid("Specify enemy template: //start_combat <template> [level] [count]")

    enemy_template = args[0]
    level = int(args[1]) if len(args) > 1 else 1
    count = int(args[2]) if len(args) > 2 else 1

    try:
        state_manager = get_state_manager()
        npc_system = state_manager.get_npc_system()
        if not npc_system:
            logger.warning("NPCSystem not found in StateManager, attempting to create fallback.")
            from core.character.npc_system import NPCSystem
            npc_system = NPCSystem()
            state_manager.set_npc_system(npc_system)

        enemy_npcs = []
        # --- Temporary list to hold created NPCs before assigning combat names ---
        temp_enemy_npcs = []
        for i in range(count):
            enemy_name = f"{enemy_template.capitalize()} {i+1}" if count > 1 else enemy_template.capitalize()
            try:
                enemy_npc = npc_system.create_enemy_for_combat(
                    name=enemy_name, # Use potentially non-unique name for creation
                    enemy_type=enemy_template,
                    level=level,
                    location=game_state.player.current_location
                )
                if enemy_npc and hasattr(enemy_npc, 'id'):
                    temp_enemy_npcs.append(enemy_npc) # Add to temp list
                else:
                    logger.error(f"Failed to create or get ID for enemy NPC: {enemy_name}")
            except Exception as creation_error:
                logger.error(f"Error creating enemy NPC '{enemy_name}': {creation_error}", exc_info=True)
                return CommandResult.error(f"Error creating enemy NPC '{enemy_name}': {creation_error}")

        if not temp_enemy_npcs:
            return CommandResult.error(f"Could not create any enemy NPCs with template '{enemy_template}'.")

        # --- Create Player Combat Entity (determine combat_name first) ---
        player_id = getattr(game_state.player, 'id', getattr(game_state.player, 'stats_manager_id', 'player_default_id'))
        player_combat_name = game_state.player.name # Start with player name
        # Check against potential enemy names *before* numbering enemies
        initial_enemy_names = {npc.name for npc in temp_enemy_npcs}
        if player_combat_name in initial_enemy_names:
             player_combat_name += " (Player)" # Append clarification if name clashes
        try:
            player_entity = create_player_combat_entity(game_state, player_combat_name) # Pass name
        except ValueError as e:
            logger.error(f"Error retrieving player stats: {e}")
            return CommandResult.error(f"Failed to get player stats for combat: {e}")

        # --- Generate Unique Combat Names and Create Enemy Entities ---
        enemy_entities = []
        name_counts: Dict[str, int] = {}
        # Initialize counts based on existing names (including player)
        all_combat_names_so_far = {player_entity.combat_name}

        for npc in temp_enemy_npcs:
            base_name = npc.name
            combat_name = base_name
            if base_name in name_counts:
                name_counts[base_name] += 1
                combat_name = f"{base_name} {name_counts[base_name]}"
            else:
                name_counts[base_name] = 1
                # Initial assignment is base_name

            # Final uniqueness check against *all* names assigned so far
            final_name = combat_name
            final_count = 1
            while final_name in all_combat_names_so_far:
                 final_count = name_counts[base_name] + 1 # Increment based on original count
                 final_name = f"{base_name} {final_count}"
                 name_counts[base_name] = final_count # Update count for next potential collision

            # Assign the unique name and create entity
            try:
                enemy_entity = create_enemy_combat_entity(npc, final_name) # Pass unique name
                enemy_entities.append(enemy_entity)
                all_combat_names_so_far.add(final_name) # Add to set for uniqueness check
            except Exception as e:
                logger.error(f"Error creating combat entity for {npc.name} ({final_name}): {e}", exc_info=True)
                # Optionally decide whether to skip this enemy or halt combat start

        if not enemy_entities:
             return CommandResult.error(f"Failed to create combat entities for enemies.")


        # --- Initialize Combat Manager ---
        combat_manager = CombatManager()
        
        # --- FIX: Explicitly Register StatsManagers for Dynamic NPCs ---
        for i, enemy_entity in enumerate(enemy_entities):
            npc_obj = temp_enemy_npcs[i] # Correspondence maintained by list order
            if hasattr(npc_obj, 'stats_manager'):
                combat_manager.register_stats_manager(enemy_entity.id, npc_obj.stats_manager)
                logger.info(f"Registered StatsManager for dynamic enemy: {enemy_entity.combat_name} ({enemy_entity.id})")
            else:
                logger.warning(f"Dynamic NPC {enemy_entity.combat_name} has no stats_manager!")
        # -----------------------------------------------------------------

        # Pass entities that *now have combat_name assigned*
        combat_manager.start_combat(player_entity, enemy_entities)

        # --- Update Game State ---
        game_state.combat_manager = combat_manager
        game_state.current_combatants = [e.id for e in [player_entity] + enemy_entities]
        game_state.set_interaction_mode(InteractionMode.COMBAT)

        enemy_names_display = ', '.join(e.combat_name for e in enemy_entities) # Use combat names
        logger.info(f"Initiating COMBAT mode. Player ({player_entity.combat_name}) vs Enemies: {enemy_names_display} ([{', '.join(e.id for e in enemy_entities)}])")
        logger.info(f"CombatManager created and assigned to GameState. Round: {combat_manager.round_number}")

        from core.base.engine import get_game_engine
        engine = get_game_engine()
        trigger_combat_narration(engine, game_state)

        return CommandResult.success(
            f"Combat initiated! {player_entity.combat_name} vs {enemy_names_display}. Entering combat mode."
        )

    except Exception as e:
        logger.error(f"Error starting combat via dev command: {e}", exc_info=True)
        return CommandResult.error(f"Failed to start combat: {str(e)}")