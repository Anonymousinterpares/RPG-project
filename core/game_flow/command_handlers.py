"""
Handles the execution of specific direct commands (e.g., /save, /quit, mode changes).
"""

from collections import Counter
from typing import List, TYPE_CHECKING, Optional

from core.base.commands import CommandResult
from core.interaction.enums import InteractionMode
from core.inventory.item_serialization import dict_to_item
from core.utils.logging_config import get_logger
from core.inventory import get_inventory_manager, EquipmentSlot, get_item_factory # Added EquipmentSlot, get_item_factory

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.base.state import GameState

# Get the module logger
logger = get_logger("COMMAND_HANDLERS")

# --- Special LLM Command Handlers ---

def handle_loot_command(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles the /loot command to collect available loot from defeated enemies."""
    loot_list = getattr(game_state, 'available_loot', [])
    
    if not loot_list:
        return CommandResult.failure("There is no loot to collect.")

    inv_mgr = get_inventory_manager()
    collected_names = []
    items_added_count = 0
    
    for entry in loot_list:
        try:
            # Loot entries are dicts with 'item_data', 'source', etc.
            item_data = entry.get('item_data')
            if item_data:
                # Reconstruct Item object from dictionary
                item_obj = dict_to_item(item_data)
                # Add to player inventory
                added_ids = inv_mgr.add_item(item_obj)
                if added_ids:
                    collected_names.append(item_obj.name)
                    items_added_count += 1
        except Exception as e:
            logger.error(f"Failed to process loot item: {e}")

    # Clear the loot pile in game state
    game_state.available_loot = []
    
    # Notify UI that loot state changed (cleared)
    engine.request_ui_update()

    if items_added_count == 0:
        return CommandResult.failure("Failed to collect items (inventory full or error).")

    # Format output message
    counts = Counter(collected_names)
    msg_parts = [f"{count}x {name}" if count > 1 else name for name, count in counts.items()]
    msg = f"Looted {items_added_count} items: " + ", ".join(msg_parts)
    
    engine._output("system", msg)
    return CommandResult.success(msg)

def handle_mode_transition(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles the MODE_TRANSITION command from LLM output.

    Format is: target_mode:origin_mode:surprise:target_entity_id:reason
    """
    logger.info(f"Handling mode transition command with args: {args}")
    if not args:
        return CommandResult.invalid("MODE_TRANSITION command requires arguments.")

    # Parse the arguments string
    arg_str = args[0]
    parts = arg_str.split(":", 4)  # Allow up to 5 parts
    
    if len(parts) < 2:
        return CommandResult.invalid("MODE_TRANSITION requires at least target_mode and origin_mode.")
    
    # Extract the parts
    target_mode_str = parts[0].upper()
    origin_mode_str = parts[1].upper()
    surprise = parts[2].lower() == "true" if len(parts) > 2 else False
    target_entity_id = parts[3] if len(parts) > 3 and parts[3] else None
    reason = parts[4] if len(parts) > 4 else "Mode transition requested."
    
    logger.info(f"Mode transition requested: {origin_mode_str} -> {target_mode_str} (Surprise: {surprise}, Target: {target_entity_id}, Reason: {reason})")
    
    # Create a structured request for the mode transition handler
    request = {
        "target_mode": target_mode_str,
        "origin_mode": origin_mode_str,
        "surprise": surprise,
        "target_entity_id": target_entity_id,
        "reason": reason
    }
    
    # Import the handler directly
    from core.game_flow.mode_transitions import _handle_transition_request
    
    # Get the actor ID (typically the player)
    actor_id = getattr(game_state.player, 'id', getattr(game_state.player, 'stats_manager_id', 'player_default_id'))
    
    # Call the transition handler
    narrative_result = _handle_transition_request(engine, game_state, request, actor_id)
    
    # Return the result
    return CommandResult.success(narrative_result or "Mode transition processed.")


def handle_start_trade(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles the /start_trade command."""
    if len(args) < 1:
        return CommandResult.invalid("Usage: /start_trade <npc_id>")
    npc_id = args[0]
    # TODO: Add validation here to check if npc_id exists and is tradeable
    logger.info(f"Initiating trade with NPC: {npc_id}")
    game_state.current_trade_partner_id = npc_id
    game_state.set_interaction_mode(InteractionMode.TRADE)
    engine._output("system", f"Starting trade with {npc_id}.")
    # TODO: Trigger initial trade narration/UI update
    return CommandResult.success(f"Starting trade with {npc_id}.")

def handle_start_social(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles the /start_social command."""
    if len(args) < 1:
        return CommandResult.invalid("Usage: /start_social <npc_id>")
    npc_id = args[0]
    # TODO: Add validation here to check if npc_id exists and can enter social conflict
    logger.info(f"Initiating social conflict with NPC: {npc_id}")
    player_id = getattr(game_state.player, 'id', None)
    if player_id is None:
        logger.error("Player ID not found in game state for social conflict.")
        return CommandResult.error("Internal error: Player ID missing.")
    # TODO: Initialize social conflict state properly (e.g., setting resolve)
    game_state.current_combatants = [player_id, npc_id] # Using combatants for now
    game_state.set_interaction_mode(InteractionMode.SOCIAL_CONFLICT)
    engine._output("system", f"Starting social conflict with {npc_id}.")
    # TODO: Trigger initial social conflict narration/UI update
    return CommandResult.success(f"Starting social conflict with {npc_id}.")

def handle_end_combat(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles the /end_combat command."""
    if game_state.current_mode != InteractionMode.COMBAT:
        return CommandResult.invalid("Not currently in combat.")
    logger.info("Ending combat mode.")
    # TODO: Add combat cleanup logic (rewards, status effects removal?)
    game_state.set_interaction_mode(InteractionMode.NARRATIVE)
    engine._output("system", "Combat ended.")
    return CommandResult.success("Combat ended.")

def handle_leave_trade(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles the /leave_trade command."""
    if game_state.current_mode != InteractionMode.TRADE:
        return CommandResult.invalid("Not currently trading.")
    logger.info("Ending trade mode.")
    # TODO: Add trade finalization logic?
    game_state.current_trade_partner_id = None
    game_state.set_interaction_mode(InteractionMode.NARRATIVE)
    engine._output("system", "Trade concluded.")
    return CommandResult.success("Trade concluded.")

def handle_end_social(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles the /end_social command."""
    if game_state.current_mode != InteractionMode.SOCIAL_CONFLICT:
        return CommandResult.invalid("Not currently in social conflict.")
    logger.info("Ending social conflict mode.")
    # TODO: Add social conflict resolution logic
    game_state.current_combatants = [] # Clear participants
    game_state.set_interaction_mode(InteractionMode.NARRATIVE)
    engine._output("system", "Social conflict resolved.")
    return CommandResult.success("Social conflict resolved.")

def _handle_equip_command(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles direct 'equip' commands."""
    if not args:
        return CommandResult.invalid("Usage: equip <item_id_or_name> [slot_name]")
    
    inventory_manager = get_inventory_manager()
    item_identifier = args[0]
    preferred_slot_str: Optional[str] = args[1] if len(args) > 1 else None
    preferred_slot_enum: Optional[EquipmentSlot] = None

    if preferred_slot_str:
        try:
            preferred_slot_enum = EquipmentSlot(preferred_slot_str.lower().replace(" ", "_"))
        except ValueError:
            return CommandResult.invalid(f"Invalid slot name: {preferred_slot_str}. Valid slots are: {', '.join([s.value for s in EquipmentSlot])}")

    item = inventory_manager.get_item(item_identifier)
    if not item: # Try finding by name
        found_items = inventory_manager.find_items(name=item_identifier) # Basic name search
        if found_items:
            item = found_items[0] # Take the first match for simplicity
            logger.info(f"Found item '{item.name}' by name for equip command.")
        else:
            return CommandResult.failure(f"Item '{item_identifier}' not found in inventory.")

    if not item.is_equippable:
        return CommandResult.failure(f"Item '{item.name}' is not equippable.")

    if inventory_manager.equip_item(item.id, preferred_slot_enum):
        # Determine the actual slot it was equipped to for the message
        equipped_slot_str = "a suitable slot"
        for slot_enum_loop, item_id_loop in inventory_manager.equipment.items():
            if item_id_loop == item.id:
                equipped_slot_str = slot_enum_loop.value.replace("_", " ")
                break
        return CommandResult.success(f"Equipped {item.name} to {equipped_slot_str}.")
    else:
        return CommandResult.failure(f"Could not equip {item.name}. Check available slots or item requirements.")

def _handle_unequip_command(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles direct 'unequip' commands."""
    if not args:
        return CommandResult.invalid("Usage: unequip <slot_name_or_item_id_or_item_name>")
    
    inventory_manager = get_inventory_manager()
    identifier = args[0]
    
    # Try to interpret as slot first
    try:
        slot_to_unequip = EquipmentSlot(identifier.lower().replace(" ", "_"))
        item_id_in_slot = inventory_manager.equipment.get(slot_to_unequip)
        if not item_id_in_slot:
            return CommandResult.failure(f"No item equipped in {slot_to_unequip.value.replace('_', ' ')}.")
        
        item_name = inventory_manager.get_item(item_id_in_slot).name if item_id_in_slot else "Unknown item"
        if inventory_manager.unequip_item(slot_to_unequip):
            return CommandResult.success(f"Unequipped {item_name} from {slot_to_unequip.value.replace('_', ' ')}.")
        else: # Should not happen if item_id_in_slot was found
            return CommandResult.error(f"Failed to unequip item from {slot_to_unequip.value.replace('_', ' ')}.")

    except ValueError: # Not a valid slot name, try as item ID or name
        item_to_unequip = inventory_manager.get_item(identifier)
        if not item_to_unequip: # Try by name
            found_items = inventory_manager.find_items(name=identifier)
            if found_items:
                item_to_unequip = found_items[0]
            else:
                return CommandResult.failure(f"Item '{identifier}' not found equipped or in inventory to identify.")
        
        if not item_to_unequip: # Still not found
            return CommandResult.failure(f"Item '{identifier}' not found.")

        # Find which slot it's equipped in
        slot_equipped_in: Optional[EquipmentSlot] = None
        for slot_enum_loop, item_id_loop in inventory_manager.equipment.items():
            if item_id_loop == item_to_unequip.id:
                slot_equipped_in = slot_enum_loop
                break
        
        if not slot_equipped_in:
            return CommandResult.failure(f"{item_to_unequip.name} is not currently equipped.")
            
        if inventory_manager.unequip_item(slot_equipped_in):
            return CommandResult.success(f"Unequipped {item_to_unequip.name} from {slot_equipped_in.value.replace('_', ' ')}.")
        else:
            return CommandResult.error(f"Failed to unequip {item_to_unequip.name}.")

def _handle_music_command(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handle MUSIC control from LLM/user.
    Payload (JSON preferred): {"action": "set_mood|set_intensity|next|mute|unmute", "mood": str?, "intensity": float?, "confidence": float?}
    Fallback colon string: action:mood:intensity:confidence
    """
    payload = _parse_single_json_arg(args)
    if not payload:
        try:
            arg_str = args[0] if args else ""
            parts = arg_str.split(":") if arg_str else []
            payload = {
                "action": parts[0] if len(parts) > 0 else None,
                "mood": parts[1] if len(parts) > 1 else None,
                "intensity": parts[2] if len(parts) > 2 else None,
                "confidence": parts[3] if len(parts) > 3 else None,
            }
        except Exception:
            payload = {}
    action = (payload.get("action") or "").strip().lower()
    if not action:
        return CommandResult.invalid("MUSIC command requires 'action'.")
    md = getattr(engine, 'get_music_director', lambda: None)()
    if not md:
        return CommandResult.error("MusicDirector not available.")
    try:
        if action in ("set_mood", "set-mood", "mood"):
            mood = payload.get("mood")
            conf = payload.get("confidence")
            try:
                conf_f = float(conf) if conf is not None else 1.0
            except Exception:
                conf_f = 1.0
            intensity = payload.get("intensity")
            try:
                inten_f = float(intensity) if intensity is not None else None
            except Exception:
                inten_f = None
            md.suggest(mood or "", inten_f if inten_f is not None else md._intensity, source="llm", confidence=conf_f)  # intensity smoothing will handle None/values
            return CommandResult.success(f"Music mood suggestion applied: {mood or md._mood}")
        elif action in ("set_intensity", "intensity"):
            intensity = payload.get("intensity")
            try:
                inten_f = float(intensity)
            except Exception:
                return CommandResult.invalid("MUSIC set_intensity requires numeric 'intensity'.")
            conf = payload.get("confidence")
            try:
                conf_f = float(conf) if conf is not None else 1.0
            except Exception:
                conf_f = 1.0
            md.suggest("", inten_f, source="llm", confidence=conf_f)  # mood unchanged; EMA update
            return CommandResult.success(f"Music intensity updated: {inten_f}")
        elif action == "next":
            md.next_track("user_skip_llm")
            return CommandResult.success("Music advanced to next track.")
        elif action == "mute":
            md.set_muted(True)
            return CommandResult.success("Music muted.")
        elif action == "unmute":
            md.set_muted(False)
            return CommandResult.success("Music unmuted.")
        elif action in ("jumpscare", "spike"):
            peak = payload.get("peak")
            attack_ms = payload.get("attack_ms")
            hold_ms = payload.get("hold_ms")
            release_ms = payload.get("release_ms")
            try:
                p = float(peak) if peak is not None else 1.0
            except Exception:
                p = 1.0
            def _to_int(val, default):
                try:
                    return int(val)
                except Exception:
                    return default
            md.jumpscare(
                peak=p,
                attack_ms=_to_int(attack_ms, 60),
                hold_ms=_to_int(hold_ms, 150),
                release_ms=_to_int(release_ms, 800),
            )
            return CommandResult.success("Jumpscare triggered.")
        else:
            return CommandResult.invalid(f"Unsupported MUSIC action '{action}'.")
    except Exception as e:
        logger.exception("MUSIC command error")
        return CommandResult.error(f"MUSIC command error: {e}")

def _handle_set_context(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Apply context changes from LLM via structured JSON (SET_CONTEXT tool).
    Rules:
      - Hierarchy: biome (outdoors/wild) → major (city/camp/village/...) → venue (tavern/market/... inside a major).
      - Major may be explicitly "none": this means location is defined only by biome (and optional region).
      - If venue is "none" (or null), there is no venue; ambience prefers major if set; otherwise biome.
      - When a Major is set (non-None), biome should be "none"/ignored for ambience purposes.
      - Accepted keys (flat or nested):
        { location_major?, venue?, name?, weather?, time_of_day?, biome?, region?, interior?, underground?, crowd_level?, danger_level? }
        or { location: {name?, major?, venue?}, weather: {type?}, ... }
      - Strings "none", "no", "n/a", "null" canonically map to None for major, biome, and venue.
    Engine canonicalizes and applies policy.
    """
    payload = _parse_single_json_arg(args)
    if not isinstance(payload, dict) or not payload:
        return CommandResult.invalid("SET_CONTEXT requires a JSON payload.")
    try:
        ctx: dict = {}
        loc = {}
        we = {}
        # Nested accepts direct
        if isinstance(payload.get('location'), dict):
            loc = {k: payload['location'].get(k) for k in ('name','major','venue') if payload['location'].get(k) is not None}
        if isinstance(payload.get('weather'), dict):
            we = { 'type': payload['weather'].get('type') }
        # Flat keys
        if payload.get('location_major') is not None: loc['major'] = payload.get('location_major')
        if payload.get('venue') is not None: loc['venue'] = payload.get('venue')
        if payload.get('name') is not None: loc['name'] = payload.get('name')
        if payload.get('weather') is not None: we['type'] = payload.get('weather')
        if loc: ctx['location'] = loc
        if we: ctx['weather'] = we
        for key in ('time_of_day','biome','region','interior','underground','crowd_level','danger_level'):
            if key in payload:
                ctx[key] = payload[key]
        engine.set_game_context(ctx, source="llm_set_context")
        # Return a compact echo of applied keys
        keys_applied = list(ctx.keys()) + [f"location.{k}" for k in loc.keys()] + (["weather.type"] if we else [])
        return CommandResult.success(f"Context update requested: {', '.join(sorted(set(keys_applied)))}")
    except Exception as e:
        return CommandResult.error(f"SET_CONTEXT error: {e}")

# --- LLM Command Mapping ---

LLM_COMMAND_HANDLERS = {
    "MODE_TRANSITION": handle_mode_transition,
    "QUEST_UPDATE": None,   # placeholders; set below after function defs
    "QUEST_STATUS": None,
    "STATE_CHANGE": None,
    "MUSIC": _handle_music_command,
    "SET_CONTEXT": None,  # set below after function def
}

# register handler in table
LLM_COMMAND_HANDLERS["SET_CONTEXT"] = _handle_set_context

# --- Main Direct Command Dispatch ---

MODE_TRANSITION_COMMANDS = {
    "start_trade": handle_start_trade,
    "start_social": handle_start_social,
    "end_combat": handle_end_combat,
    "leave_trade": handle_leave_trade,
    "end_social": handle_end_social,
    "equip": _handle_equip_command,
    "unequip": _handle_unequip_command,
    # Music control (direct command): forwards to the same handler used by LLM MUSIC
    "music": _handle_music_command,
    "loot": handle_loot_command, # Added loot command registration
    # Add other mode transition commands here
}


def _parse_single_json_arg(args: List[str]) -> dict:
    try:
        import json
        if not args:
            return {}
        payload = args[0]
        if isinstance(payload, dict):
            return payload
        return json.loads(payload)
    except Exception:
        return {}


def _handle_quest_update(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles QUEST_UPDATE command with a JSON payload from LLM.
    Payload schema: {"quest_id","objective_id","new_status","confidence", "evidence": [...]}
    """
    payload = _parse_single_json_arg(args)
    try:
        from core.game_flow.quest_updates import apply_objective_update_from_llm
        ok, msg = apply_objective_update_from_llm(engine, game_state, payload)
        return CommandResult.success(msg) if ok else CommandResult.failure(msg)
    except Exception as e:
        return CommandResult.error(f"Quest update error: {e}")


def _handle_quest_status(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handles QUEST_STATUS command with a JSON payload from LLM.
    Payload schema: {"quest_id","new_status","confidence","evidence": [...]}"""
    payload = _parse_single_json_arg(args)
    try:
        from core.game_flow.quest_updates import apply_quest_status_from_llm
        ok, msg = apply_quest_status_from_llm(engine, game_state, payload)
        return CommandResult.success(msg) if ok else CommandResult.failure(msg)
    except Exception as e:
        return CommandResult.error(f"Quest status error: {e}")


def _handle_state_change(engine: 'GameEngine', game_state: 'GameState', args: List[str]) -> CommandResult:
    """Handle STATE_CHANGE requests from the LLM.

    Supports at least inventory mutations via JSON payload with schema similar to:
      {
        "action": "request_state_change",
        "target_id": "player",     # normalized by AgentManager
        "attribute": "inventory",   # or other attributes like stamina (acknowledged only)
        "change_type": "add",       # add|remove|drop|consume
        "quantity": 1,
        "template_id": "test_apple" # or item_template | item_id | item_spec
      }
    Fallback colon format is also parsed: target:attribute:change_type:value:item_identifier
    """
    import json as _json

    # Try JSON payload first
    payload = _parse_single_json_arg(args)

    if not payload:
        # Fallback: parse colon-delimited string
        arg_str = args[0] if args else ""
        parts = arg_str.split(":") if arg_str else []
        payload = {
            "target_id": parts[0] if len(parts) > 0 else None,
            "attribute": parts[1] if len(parts) > 1 else None,
            "change_type": parts[2] if len(parts) > 2 else None,
            "value": parts[3] if len(parts) > 3 else None,
            "item_id": parts[4] if len(parts) > 4 else None,
        }

    attribute = (payload.get("attribute") or "").lower()

    if attribute == "inventory":
        try:
            inventory = get_inventory_manager()
            item_factory = get_item_factory()

            change_type = (payload.get("change_type") or payload.get("change") or "add").lower()

            # Quantity may be specified as 'quantity' or (poorly) as 'value'
            q_raw = payload.get("quantity", payload.get("value", 1))
            try:
                quantity = int(q_raw)
            except Exception:
                quantity = 1
            if quantity <= 0:
                quantity = 1

            if change_type in ("add", "give", "pickup", "obtain", "create"):
                item_obj = None
                # Prefer explicit item_spec if provided
                item_spec = payload.get("item_spec") or payload.get("item_data")
                if isinstance(item_spec, dict):
                    try:
                        item_obj = item_factory.create_item_from_spec(item_spec)
                    except Exception as e:
                        logger.warning(f"STATE_CHANGE inventory add: invalid item_spec: {e}")

                if item_obj is None:
                    # template id options
                    template_id = payload.get("template_id") or payload.get("item_template")
                    # if item_id references an existing inventory item, use it as prototype
                    ref_item_id = payload.get("item_id")
                    if ref_item_id:
                        existing = inventory.get_item(ref_item_id)
                        if existing:
                            item_obj = existing
                        elif not template_id:
                            template_id = ref_item_id  # treat as template id fallback

                    if item_obj is None and template_id:
                        item_obj = item_factory.create_item_from_template(template_id, variation=False)

                if item_obj is None:
                    # Last resort: try by name among inventory (not ideal for new items)
                    item_name = payload.get("item_name") or payload.get("name")
                    if item_name:
                        found = inventory.find_items(name=item_name)
                        if found:
                            item_obj = found[0]

                if item_obj is None:
                    return CommandResult.failure("STATE_CHANGE inventory add: could not resolve item to add.")

                added_ids = inventory.add_item(item_obj, quantity=quantity)
                if not added_ids:
                    return CommandResult.failure(f"Could not add {quantity}x {getattr(item_obj, 'name', 'item')}.")
                return CommandResult.success(f"Added {quantity}x {item_obj.name} to inventory.")

            elif change_type in ("remove", "drop", "discard", "consume", "delete"):
                target_item = None
                # Identify target by item_id, template_id, or name
                ref_item_id = payload.get("item_id")
                if ref_item_id:
                    target_item = inventory.get_item(ref_item_id)

                if not target_item:
                    template_id = payload.get("template_id") or payload.get("item_template")
                    if template_id:
                        # Search inventory by template_id
                        for it in getattr(inventory, "_items", {}).values():
                            if getattr(it, "template_id", None) == template_id:
                                target_item = it
                                break

                if not target_item:
                    item_name = payload.get("item_name") or payload.get("name")
                    if item_name:
                        found = inventory.find_items(name=item_name)
                        if found:
                            target_item = found[0]

                if not target_item:
                    return CommandResult.failure("STATE_CHANGE inventory remove: target item not found in inventory.")

                ok = inventory.remove_item(target_item.id, quantity)
                return CommandResult.success(f"Removed {quantity}x {target_item.name} from inventory.") if ok else CommandResult.failure(f"Failed to remove {quantity}x {target_item.name}.")
            else:
                return CommandResult.invalid(f"STATE_CHANGE inventory: unsupported change_type '{change_type}'.")
        except Exception as e:
            logger.exception("STATE_CHANGE inventory error")
            return CommandResult.error(f"Inventory state change error: {e}")

    elif attribute == "location":
        # Developer-only direct location change for test convenience
        try:
            from PySide6.QtCore import QSettings
            q = QSettings("RPGGame", "Settings")
            dev_enabled = bool(q.value("dev/enabled", False, type=bool) or q.value("dev/quest_verbose", False, type=bool))
        except Exception:
            dev_enabled = False

        location_id = str(payload.get("value") or payload.get("location") or "").strip()
        logger.debug(f"STATE_CHANGE location requested -> '{location_id}', dev_enabled={dev_enabled}")

        if not location_id:
            return CommandResult.invalid("STATE_CHANGE location: missing 'value'.")

        if not dev_enabled:
            explanation = None
            try:
                if hasattr(engine, "_rule_checker") and engine._rule_checker is not None:
                    from core.agents.base_agent import AgentContext
                    from core.interaction.context_builder import ContextBuilder
                    from core.interaction.enums import InteractionMode
                    ctx = ContextBuilder().build_context(game_state, InteractionMode.NARRATIVE, actor_id="player")
                    validation_input = f"STATE_CHANGE location -> {location_id} (request denied in normal play)"
                    agent_ctx = AgentContext(
                        game_state=ctx,
                        player_state=ctx.get("player", {}),
                        world_state={
                            "location": ctx.get("location"),
                            "time_of_day": ctx.get("time_of_day"),
                            "environment": ctx.get("environment"),
                        },
                        player_input=validation_input,
                        conversation_history=getattr(game_state, "conversation_history", []),
                        relevant_memories=[],
                        additional_context=ctx,
                    )
                    is_valid, reason = engine._rule_checker.validate_action(agent_ctx)
                    if not is_valid and reason:
                        explanation = reason
            except Exception:
                pass
            if not explanation:
                explanation = "developer-only teleportation is disabled in normal play"
            return CommandResult.failure(f"This action is not permitted - {explanation}.")

        try:
            game_state.player.current_location = location_id
            if hasattr(game_state, "world"):
                game_state.world.current_location = location_id
            try:
                from core.game_flow.event_log import record_location_visited
                record_location_visited(game_state, location_id=location_id)
            except Exception:
                pass
            logger.info(f"STATE_CHANGE location applied (dev): {location_id}")
            return CommandResult.success(f"Location set to {location_id} (dev).")
        except Exception as e:
            logger.exception("STATE_CHANGE location error")
            return CommandResult.error(f"Failed to change location: {e}")

    # Non-inventory attributes: acknowledge but do not apply mechanics here unless explicitly supported
    return CommandResult.invalid(f"STATE_CHANGE not supported for attribute '{attribute}'.")
def process_llm_command(engine: 'GameEngine', command: str, args: List[str], game_state: 'GameState') -> CommandResult:
    """Process a command from the LLM output.
    
    Args:
        engine: The GameEngine instance.
        command: The command name (e.g., MODE_TRANSITION, STAT_CHECK)
        args: The command arguments
        game_state: The current game state
        
    Returns:
        The result of processing the command
    """
    logger.info(f"Processing LLM command: {command} with args: {args}")
    
    # Check if command is in our LLM command handlers
    if command.upper() in LLM_COMMAND_HANDLERS:
        handler = LLM_COMMAND_HANDLERS[command.upper()]
        if handler is None:
            return CommandResult.error(f"Handler not initialized for {command}")
        return handler(engine, game_state, args)
    else:
        # Fall back to CommandProcessor for unknown commands
        logger.warning(f"Unknown LLM command: {command}, falling back to CommandProcessor")
        cmd_args_str = " ".join(args) if args else ""
        result = engine._command_processor.process_llm_commands(game_state, f"{{{command} {cmd_args_str}}}")
        # Return a simple CommandResult from the tuple returned by process_llm_commands
        if isinstance(result, tuple) and len(result) == 2:
            return CommandResult.success(result[0])
        return CommandResult.success("Command processed.")

def process_direct_command(engine: 'GameEngine', command_text: str) -> CommandResult:
    """
    Process a direct command (e.g., starting with '/', 'command:', or '//').

    This function determines if it's a mode transition or should be passed
    to the core CommandProcessor.

    Args:
        engine: The GameEngine instance.
        command_text: The command text to process (without the leading '/' or 'command:').

    Returns:
        The result of executing the command.
    """
    current_state = engine._state_manager.current_state
    if current_state is None:
        return CommandResult.error("No game in progress.")

    # Handle developer commands separately first if needed
    if command_text.startswith('//'):
        logger.debug(f"Processing developer command: {command_text}")
        # Delegate directly to CommandProcessor for dev commands
        result = engine._command_processor.process_command(current_state, command_text)
        # Dev commands typically handle their own output via CommandProcessor registration
        return result

    # Parse command and arguments for regular direct commands
    parts = command_text.split()
    if not parts: # Handle empty command after stripping prefix
        return CommandResult.invalid("Empty command received.")
        
    command_verb = parts[0].lower() # Use verb for dictionary lookup
    args = parts[1:]

    # Check if it's a mode transition command handled here
    if command_verb in MODE_TRANSITION_COMMANDS:
        handler = MODE_TRANSITION_COMMANDS[command_verb]
        result = handler(engine, current_state, args)
        # Mode transition handlers (like equip/unequip) might return messages
        # that should NOT be outputted if they are purely mechanical UI feedback.
        # The individual handlers should decide if their message is for internal logging or UI.
        # For equip/unequip, they are now silent.
        if result.message and command_verb not in ["equip", "unequip"]: # Don't output for equip/unequip
            engine._output("system", result.message)
        return result
    else:
        # Otherwise, delegate to the core CommandProcessor
        logger.debug(f"Delegating direct command to CommandProcessor: {command_text}")
        result = engine._command_processor.process_command(current_state, command_text)

        # Handle side effects like exit
        if result.is_exit:
            logger.info("Exit command received via CommandProcessor")
            engine._running = False # Signal engine to stop

        # Output the result message from CommandProcessor if one exists,
        # unless it's a command that should not have direct output (like a UI-proxied drop before LLM)
        if result.message:
            # Check if the original command was a UI-proxied drop.
            # If so, and drop_command returned a message, suppress it here because LLM handles output.
            is_ui_drop_command = command_verb == "drop" and any('-' in arg for arg in args)
            
            if not (is_ui_drop_command and result.is_success): # Don't output success of mechanical drop if UI initiated and LLM handles narrative
                output_role = "gm" if result.is_success else "system"
                engine._output(output_role, result.message)

        return result

# Initialize handlers now that functions are defined
LLM_COMMAND_HANDLERS["QUEST_UPDATE"] = _handle_quest_update
LLM_COMMAND_HANDLERS["QUEST_STATUS"] = _handle_quest_status
LLM_COMMAND_HANDLERS["STATE_CHANGE"] = _handle_state_change
