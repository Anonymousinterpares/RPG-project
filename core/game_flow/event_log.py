#!/usr/bin/env python3
"""
Event log utilities for recording game-time receipts of player/world actions.
"""
from __future__ import annotations
from typing import Dict, Any, Optional

from core.utils.logging_config import get_logger

logger = get_logger("EVENT_LOG")

# Event types (string constants to keep it simple and JSON-friendly)
EV_ENEMY_DEFEATED = "EnemyDefeated"
EV_ITEM_DELTA = "ItemDelta"
EV_LOCATION_VISITED = "LocationVisited"
EV_DIALOGUE = "DialogueCompleted"
EV_INTERACTION = "InteractionCompleted"
EV_FLAG_SET = "FlagSet"
EV_OBJECTIVE_STATUS = "ObjectiveStatusChange"
EV_QUEST_STATUS = "QuestStatusChange"


def _append(game_state, event: Dict[str, Any]) -> None:
    try:
        if not hasattr(game_state, 'event_log') or not isinstance(game_state.event_log, list):
            game_state.event_log = []
        game_state.event_log.append(event)
    except Exception as e:
        logger.warning(f"Failed to append event: {e}")
        return

    # Phase 1: trigger quest evaluation after appending relevant events
    try:
        from core.base.engine import get_game_engine
        from core.game_flow.quest_updates import process_event_for_quests
        engine = get_game_engine()
        if engine is not None:
            process_event_for_quests(engine, game_state, event)
    except Exception as e:
        # Non-fatal: continue
        logger.debug(f"Quest evaluation hook error (ignored): {e}")


def record_enemy_defeated(game_state, *, entity_id: str, template_id: Optional[str], tags: Dict[str, Any], location_id: Optional[str]) -> None:
    ev = {
        'type': EV_ENEMY_DEFEATED,
        'entity_id': entity_id,
        'template_id': template_id,
        'tags': tags or {},
        'location_id': location_id,
        'game_time': getattr(game_state.world, 'game_time', 0.0),
    }
    _append(game_state, ev)


def record_item_delta(game_state, *, item_id: str, delta: int, source: str) -> None:
    ev = {
        'type': EV_ITEM_DELTA,
        'item_id': item_id,
        'delta': int(delta),
        'source': source,
        'game_time': getattr(game_state.world, 'game_time', 0.0),
    }
    _append(game_state, ev)


def record_location_visited(game_state, *, location_id: str) -> None:
    ev = {
        'type': EV_LOCATION_VISITED,
        'location_id': location_id,
        'game_time': getattr(game_state.world, 'game_time', 0.0),
    }
    _append(game_state, ev)


def record_dialogue(game_state, *, dialogue_id: str, npc_id: Optional[str] = None) -> None:
    ev = {
        'type': EV_DIALOGUE,
        'dialogue_id': dialogue_id,
        'npc_id': npc_id,
        'game_time': getattr(game_state.world, 'game_time', 0.0),
    }
    _append(game_state, ev)


def record_interaction(game_state, *, interaction_id: str, meta: Optional[Dict[str, Any]] = None) -> None:
    ev = {
        'type': EV_INTERACTION,
        'interaction_id': interaction_id,
        'meta': meta or {},
        'game_time': getattr(game_state.world, 'game_time', 0.0),
    }
    _append(game_state, ev)


def record_flag_set(game_state, *, key: str, value: Any) -> None:
    ev = {
        'type': EV_FLAG_SET,
        'key': key,
        'value': value,
        'game_time': getattr(game_state.world, 'game_time', 0.0),
    }
    _append(game_state, ev)


def record_objective_status(game_state, *, quest_id: str, objective_id: str, new_status: str) -> None:
    ev = {
        'type': EV_OBJECTIVE_STATUS,
        'quest_id': quest_id,
        'objective_id': objective_id,
        'new_status': new_status,
        'game_time': getattr(game_state.world, 'game_time', 0.0),
    }
    _append(game_state, ev)


def record_quest_status(game_state, *, quest_id: str, new_status: str) -> None:
    ev = {
        'type': EV_QUEST_STATUS,
        'quest_id': quest_id,
        'new_status': new_status,
        'game_time': getattr(game_state.world, 'game_time', 0.0),
    }
    _append(game_state, ev)

