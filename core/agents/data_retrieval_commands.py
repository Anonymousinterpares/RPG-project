"""
Data retrieval commands for LLM agents.

This module provides commands that allow LLM agents to request specific game data
only when needed instead of including all data in every context.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging

from core.utils.logging_config import get_logger
from core.base.state import GameState
from core.inventory import get_inventory_manager, Item # Added Item import

# Get module logger
logger = get_logger("DATA_RETRIEVAL")

def get_inventory_data(game_state: GameState) -> Dict[str, Any]:
    """
    Get detailed inventory data for an LLM agent in the simplified format.
    
    Args:
        game_state: The current game state.
    
    Returns:
        A dictionary containing inventory data with 'equipped' and 'backpack' keys.
    """
    logger.info("Retrieving inventory data for LLM agent (simplified format)")
    
    try:
        inventory_manager = get_inventory_manager()
        
        if not inventory_manager:
            logger.warning("Inventory manager not available for data retrieval.")
            return {"error": "Inventory manager not available"}
        
        equipped_items_dict: Dict[str, Dict[str, str]] = {}
        backpack_items_list: List[Dict[str, Any]] = []

        # Populate equipped items
        if hasattr(inventory_manager, 'equipment') and isinstance(inventory_manager.equipment, dict):
            for slot, item_id in inventory_manager.equipment.items():
                if item_id:
                    item_obj: Optional[Item] = inventory_manager.get_item(item_id)
                    if item_obj:
                        equipped_items_dict[slot.value] = { # Use slot.value for the key
                            "name": item_obj.name,
                            "id": item_obj.id,
                            "type": item_obj.item_type.value if hasattr(item_obj.item_type, 'value') else str(item_obj.item_type)
                        }
                    else:
                        logger.warning(f"Equipped item ID {item_id} in slot {slot.value} not found in inventory manager items.")
        else:
            logger.warning("Inventory manager 'equipment' attribute missing or not a dict.")

        # Populate backpack items
        if hasattr(inventory_manager, 'items') and isinstance(inventory_manager.items, dict): # Assuming _items is the dict
            all_items_in_inventory = inventory_manager.items.values()
        elif hasattr(inventory_manager, 'items') and isinstance(inventory_manager.items, list): # Fallback if it's a list
            all_items_in_inventory = inventory_manager.items
        else:
            all_items_in_inventory = []
            logger.warning("Inventory manager 'items' attribute missing or not a list/dict.")

        for item_obj in all_items_in_inventory:
            if not inventory_manager.is_item_equipped(item_obj.id):
                backpack_items_list.append({
                    "name": item_obj.name,
                    "id": item_obj.id,
                    "type": item_obj.item_type.value if hasattr(item_obj.item_type, 'value') else str(item_obj.item_type),
                    "quantity": item_obj.quantity if item_obj.is_stackable else 1
                })
        
        # Get currency data
        currency_data = {}
        if hasattr(inventory_manager, 'currency'):
            currency_data = inventory_manager.currency.get_currency_dict()
        else:
            logger.warning("Inventory manager 'currency' attribute missing.")

        inventory_data = {
            "equipped": equipped_items_dict,
            "backpack": backpack_items_list,
            "currency": currency_data, # Keep currency as is
            "weight": { # Keep weight/slots as is
                "current": inventory_manager.get_current_weight(),
                "limit": inventory_manager.weight_limit
            },
            "slots": {
                "used": inventory_manager.get_used_slots(),
                "limit": inventory_manager.slot_limit
            }
        }
        
        return inventory_data
        
    except Exception as e:
        logger.error(f"Error retrieving inventory data: {e}", exc_info=True)
        return {"error": f"Error retrieving inventory data: {str(e)}"}

def get_character_stats(game_state: GameState) -> Dict[str, Any]:
    """
    Get character stats data for an LLM agent.
    
    Args:
        game_state: The current game state.
    
    Returns:
        A dictionary containing character stats data.
    """
    logger.info("Retrieving character stats data for LLM agent")
    
    try:
        # Check if stats manager is available (it should be in state_manager)
        from core.base.state import get_state_manager
        
        state_manager = get_state_manager()
        stats_manager = state_manager.stats_manager
        
        if not stats_manager:
            logger.warning("Stats manager not available")
            return {"error": "Stats manager not available"}
        
        # Get basic character info
        character_info = {
            "name": game_state.player.name,
            "race": game_state.player.race,
            "path": game_state.player.path,
            "background": game_state.player.background,
            "level": game_state.player.level,
            "experience": game_state.player.experience,
            "experience_to_next_level": game_state.player.experience_to_next_level,
        }
        
        # Get primary stats
        primary_stats = {}
        
        from core.stats.stats_base import StatType
        for stat_type in StatType:
            stat_value = stats_manager.get_stat_value(stat_type)
            stat_obj = stats_manager.get_stat(stat_type)
            stat_base = stat_obj.base_value if stat_obj else 0
            # Get modifiers from the modifier manager
            mod_values = stats_manager.modifier_manager.get_stat_modifier_value(stat_type)
            stat_mod = mod_values['flat']  # Use flat modifier
            
            primary_stats[stat_type.name] = {
                "value": stat_value,
                "base": stat_base,
                "modifier": stat_mod
            }
        
        # Get derived stats
        derived_stats = {}
        
        from core.stats.stats_base import DerivedStatType
        for stat_type in DerivedStatType:
            # Get the derived stat value (fall back to get_stat_value for consistency)
            stat_value = stats_manager.get_stat_value(stat_type)
            
            derived_stats[stat_type.name] = {
                "value": stat_value
            }
        
        # Get active modifiers
        active_modifiers = []
        
        # Get all modifiers from the modifier manager
        all_modifiers = stats_manager.modifier_manager.modifiers
        for modifier in all_modifiers:
            # The modifier structure might be different than expected, handle safely
            try:
                mod_data = {
                    "stat": str(modifier.stat) if hasattr(modifier, 'stat') else "Unknown",
                    "value": modifier.value if hasattr(modifier, 'value') else 0,
                    "source": str(modifier.source_type) if hasattr(modifier, 'source_type') else str(modifier.source) if hasattr(modifier, 'source') else "Unknown",
                    "duration": modifier.duration if hasattr(modifier, 'duration') else None,
                    "is_permanent": modifier.modifier_type.name == "PERMANENT" if hasattr(modifier, 'modifier_type') else (modifier.duration is None) if hasattr(modifier, 'duration') else True,
                }
            except Exception as e:
                logger.warning(f"Error processing modifier: {e}")
                mod_data = {
                    "stat": "Unknown",
                    "value": 0,
                    "source": "Unknown",
                    "duration": None,
                    "is_permanent": True,
                }
            active_modifiers.append(mod_data)
        
        # Combine all stats data
        stats_data = {
            "character": character_info,
            "primary_stats": primary_stats,
            "derived_stats": derived_stats,
            "active_modifiers": active_modifiers
        }
        
        return stats_data
    
    except Exception as e:
        logger.error(f"Error retrieving character stats data: {e}", exc_info=True)
        return {"error": f"Error retrieving character stats data: {str(e)}"}

def get_quest_data(game_state: GameState) -> Dict[str, Any]:
    """
    Get quest data for an LLM agent from the authoritative journal.

    Returns a dict with active_quests, completed_quests, failed_quests arrays.
    Each quest entry contains id, title, description, status, and objectives
    with minimal fields needed for LLM summaries.
    """
    logger.info("Retrieving quest data for LLM agent (from journal)")

    try:
        journal = getattr(game_state, 'journal', {}) or {}
        quests_map = journal.get('quests', {}) if isinstance(journal, dict) else {}
        
        def classify_status(q: Dict[str, Any]) -> str:
            # Derive status similar to GUI logic
            try:
                status = q.get('status', 'active')
                objectives = q.get('objectives', []) or []
                mandatory_total = sum(1 for o in objectives if o.get('mandatory', True)) or 0
                mandatory_completed = sum(1 for o in objectives if o.get('mandatory', True) and o.get('completed', False))
                any_failed = any(o.get('failed', False) for o in objectives)
                fully_completed = (mandatory_total == mandatory_completed) and not any_failed
                if q.get('abandoned'):
                    return 'failed'
                if fully_completed:
                    return 'completed'
                if status in ('failed','completed','active'):
                    return status
                return 'active'
            except Exception:
                return q.get('status', 'active')
        
        def simplify_quest(qid: str, q: Dict[str, Any]) -> Dict[str, Any]:
            return {
                'id': qid,
                'title': q.get('title', qid),
                'description': q.get('description', ''),
                'status': classify_status(q),
                'objectives': [
                    {
                        'id': o.get('id'),
                        'description': o.get('description', ''),
                        'completed': bool(o.get('completed', False)),
                        'failed': bool(o.get('failed', False)),
                        'mandatory': bool(o.get('mandatory', True)),
                    } for o in (q.get('objectives', []) or [])
                ]
            }
        
        active: list[Dict[str, Any]] = []
        completed: list[Dict[str, Any]] = []
        failed: list[Dict[str, Any]] = []
        
        for qid, q in quests_map.items():
            entry = simplify_quest(qid, q if isinstance(q, dict) else {})
            st = entry['status']
            if st == 'completed':
                completed.append(entry)
            elif st == 'failed':
                failed.append(entry)
            else:
                active.append(entry)
        
        return {
            'active_quests': active,
            'completed_quests': completed,
            'failed_quests': failed,
        }
    except Exception as e:
        logger.error(f"Error retrieving quest data: {e}", exc_info=True)
        return {"error": f"Error retrieving quest data: {str(e)}"}

def get_location_info(game_state: GameState) -> Dict[str, Any]:
    """
    Get location information for an LLM agent.
    
    Args:
        game_state: The current game state.
    
    Returns:
        A dictionary containing location information.
    """
    logger.info("Retrieving location information for LLM agent")
    
    try:
        # Basic location information from player and world state
        location_data = {
            "current_location": game_state.player.current_location,
            "current_district": game_state.player.current_district,
            "time_of_day": game_state.world.time_of_day,
            "weather": game_state.world.weather,
            "is_day": game_state.world.is_day,
        }
        
        # Get game time
        from core.base.game_loop import GameTime
        game_time = GameTime(game_time=game_state.world.game_time)
        
        location_data["game_time"] = {
            "total_seconds": game_state.world.game_time,
            "formatted_time": game_time.get_formatted_time(),
            "day_name": game_time.get_day_name(),
            "hour": game_time.hour,
            "minute": game_time.minute,
            "second": game_time.second
        }
        
        return location_data
    
    except Exception as e:
        logger.error(f"Error retrieving location information: {e}", exc_info=True)
        return {"error": f"Error retrieving location information: {str(e)}"}

def process_data_retrieval_command(command: str, args: str, game_state: GameState) -> Dict[str, Any]:
    """
    Process a data retrieval command.
    
    Args:
        command: The command name (e.g., GET_INVENTORY).
        args: Command arguments (if any).
        game_state: The current game state.
    
    Returns:
        Retrieved data as a dictionary.
    """
    logger.info(f"Processing data retrieval command: {command}")
    
    # Map commands to handler functions
    command_handlers = {
        "GET_INVENTORY": get_inventory_data,
        "GET_STATS": get_character_stats,
        "GET_QUESTS": get_quest_data,
        "GET_LOCATION_INFO": get_location_info,
    }
    
    # Get handler function
    handler = command_handlers.get(command)
    
    if not handler:
        logger.warning(f"Unknown data retrieval command: {command}")
        return {"error": f"Unknown data retrieval command: {command}"}
    
    # Call the handler function
    result = handler(game_state)
    
    return result
