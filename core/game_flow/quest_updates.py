#!/usr/bin/env python3
"""
Quest update application module: validates and applies LLM-proposed quest/objective updates.
Includes a minimal DSL evaluator for deterministic objectives and orchestrated messages.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple, Optional, List

from core.utils.logging_config import get_logger
from core.base.config import get_config
import re

# Event log recorders
try:
    from core.game_flow.event_log import (
        record_objective_status,
        record_quest_status,
        EV_ENEMY_DEFEATED,
        EV_ITEM_DELTA,
        EV_LOCATION_VISITED,
        EV_DIALOGUE,
        EV_INTERACTION,
        EV_FLAG_SET,
    )
except Exception:  # fallback if not yet available
    record_objective_status = lambda *args, **kwargs: None
    record_quest_status = lambda *args, **kwargs: None
    EV_ENEMY_DEFEATED = "EnemyDefeated"
    EV_ITEM_DELTA = "ItemDelta"
    EV_LOCATION_VISITED = "LocationVisited"
    EV_DIALOGUE = "DialogueCompleted"
    EV_INTERACTION = "InteractionCompleted"
    EV_FLAG_SET = "FlagSet"

logger = get_logger("QUESTS")

# Developer-verbose quest logging toggle (read from config)

def _dev_quest_verbose() -> bool:
    """Return True if developer quest logs should be shown in the UI.
    Checks config dev.quest_verbose first; falls back to QSettings dev/enabled or dev/quest_verbose.
    """
    try:
        cfg = get_config()
        val = cfg.get("dev.quest_verbose", None)
        if isinstance(val, bool):
            return val
    except Exception:
        pass
    # Fallback to QSettings (GUI toggle)
    try:
        from PySide6.QtCore import QSettings
        s = QSettings("RPGGame", "Settings")
        # Respect dedicated quest verbose flag if set; otherwise use dev/enabled as a coarse switch
        if s.contains("dev/quest_verbose"):
            return bool(s.value("dev/quest_verbose", False, type=bool))
        return bool(s.value("dev/enabled", False, type=bool))
    except Exception:
        return False


def _queue_dev(engine, text: str) -> None:
    """Queue a dev quest message to MAIN_GAME_OUTPUT if dev.quest_verbose is enabled."""
    if not _dev_quest_verbose():
        return
    try:
        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        engine._combat_orchestrator.add_event_to_queue(
            DisplayEvent(
                type=DisplayEventType.SYSTEM_MESSAGE,
                content=f"[DEV][QUEST] {text}",
                target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                gradual_visual_display=False,
                tts_eligible=False,
            )
        )
    except Exception:
        # Swallow errors to avoid impacting gameplay
        pass

# --- Minimal DSL evaluator ---

def _eval_condition_dsl(dsl: Any, signals: Dict[str, Any]) -> Optional[bool]:
    """Evaluate minimal boolean DSL against signals. Return True/False/None (unknown)."""
    try:
        if dsl is None:
            return None
        if isinstance(dsl, bool):
            return dsl
        if isinstance(dsl, dict):
            # Supported forms: {op: args}
            if 'all' in dsl:
                return all(_eval_condition_dsl(x, signals) is True for x in dsl['all'])
            if 'any' in dsl:
                return any(_eval_condition_dsl(x, signals) is True for x in dsl['any'])
            if 'none' in dsl:
                return all(_eval_condition_dsl(x, signals) is False for x in dsl['none'])
            if 'inventory_has' in dsl:
                item_id = dsl['inventory_has'].get('item_id')
                count = int(dsl['inventory_has'].get('count', 1))
                inv = signals.get('inventory', {})
                have = inv.get(item_id, 0)
                return bool(have >= count)
            if 'defeated' in dsl:
                entity_id = dsl['defeated']
                return bool(entity_id in (signals.get('defeated', [])))
            if 'visited' in dsl:
                loc_id = dsl['visited']
                return bool(loc_id in (signals.get('visited', [])))
            if 'flag' in dsl:
                key = dsl['flag'].get('key')
                val = dsl['flag'].get('value', True)
                return bool(signals.get('flags', {}).get(key) == val)
            if 'time_before' in dsl:
                t = float(dsl['time_before'])
                return bool(signals.get('time', 0.0) < t)
            if 'time_after' in dsl:
                t = float(dsl['time_after'])
                return bool(signals.get('time', 0.0) > t)
        return None
    except Exception as e:
        logger.warning(f"DSL eval error: {e}")
        return None

# --- Signals builder (phase 1: derive from current state and event log) ---

def _build_signals(game_state) -> Dict[str, Any]:
    """Construct signals snapshot used by the DSL evaluator.
    Phase 1: build from inventory and event_log (defeats, visits, flags, time).
    """
    inv_counts: Dict[str, int] = {}
    try:
        from core.inventory import get_inventory_manager
        im = get_inventory_manager()
        # Aggregate inventory by template_id (fallback to name) and sum quantities
        for itm in getattr(im, 'items', []) or []:
            try:
                tid = getattr(itm, 'template_id', None) or getattr(itm, 'name', None)
                if not tid:
                    continue
                qty = int(getattr(itm, 'quantity', 1) or 1)
                inv_counts[tid] = inv_counts.get(tid, 0) + qty
            except Exception:
                continue
    except Exception:
        pass

    defeated_ids: List[str] = []
    visited_ids: List[str] = []
    try:
        log = getattr(game_state, 'event_log', []) or []
        # Include template_id, entity_id, and normalized combat names for defeated
        for ev in log:
            et = ev.get('type')
            if et == EV_ENEMY_DEFEATED:
                eid = ev.get('entity_id'); tid = ev.get('template_id')
                tags = ev.get('tags', {}) or {}
                cname = str(tags.get('combat_name', '') or '').strip()
                # Lowercase all candidates
                if tid:
                    defeated_ids.append(str(tid).lower())
                if eid:
                    defeated_ids.append(str(eid).lower())
                if cname:
                    defeated_ids.append(cname.lower())
                    # Base name by stripping trailing _<digits>
                    base = re.sub(r'_[0-9]+$', '', cname.lower())
                    if base and base != cname.lower():
                        defeated_ids.append(base)
            elif et == EV_LOCATION_VISITED:
                lid = ev.get('location_id')
                if lid: visited_ids.append(str(lid).lower())
    except Exception:
        pass

    # Build flags/time
    try:
        flags = getattr(game_state.world, 'global_vars', {}) if hasattr(game_state, 'world') else {}
    except Exception:
        flags = {}
    try:
        tnow = getattr(game_state.world, 'game_time', 0.0)
    except Exception:
        tnow = 0.0

    signals = {
        'inventory': inv_counts,            # Dict[template_id_or_name, count]
        'defeated': defeated_ids,           # List of ids/templates seen defeated
        'visited': visited_ids,             # List of visited location ids
        'flags': flags or {},
        'time': tnow,
    }
    return signals

# --- Evidence verification ---

def _verify_evidence(game_state, payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Verify at least one piece of evidence against engine records.
    Evidence schema examples:
      {"type":"defeated","id":"entity_or_template_id"}
      {"type":"item","id":"item_id","count":1}
      {"type":"visited","id":"location_id"}
      {"type":"flag","key":"flag.key","value":true}
      {"type":"dialogue","id":"dialogue_id"}
      {"type":"interaction","id":"interaction_id"}
    """
    evid = payload.get('evidence')
    if not isinstance(evid, list) or not evid:
        return False, 'No evidence provided'

    log: List[Dict[str, Any]] = getattr(game_state, 'event_log', []) if hasattr(game_state, 'event_log') else []

    # Access inventory and flags if needed
    inv_counts: Dict[str, int] = {}
    try:
        from core.inventory import get_inventory_manager
        im = get_inventory_manager()
        # Aggregate by template_id (fallback to name) and sum quantities
        for itm in getattr(im, 'items', []):
            try:
                tid = getattr(itm, 'template_id', None) or getattr(itm, 'name', None)
                if not tid:
                    continue
                qty = int(getattr(itm, 'quantity', 1) or 1)
                inv_counts[tid] = inv_counts.get(tid, 0) + qty
            except Exception:
                continue
    except Exception:
        pass
    flags = {}
    try:
        flags = getattr(game_state.world, 'global_vars', {}) if hasattr(game_state, 'world') else {}
    except Exception:
        flags = {}

    def any_log(predicate) -> bool:
        try:
            return any(predicate(ev) for ev in log)
        except Exception:
            return False

    for evref in evid:
        if not isinstance(evref, dict):
            continue
        etype = str(evref.get('type', '')).lower()
        # defeated
        if etype == 'defeated':
            rid = evref.get('id')
            if not rid: 
                continue
            found = any_log(lambda ev: ev.get('type') == EV_ENEMY_DEFEATED and (ev.get('entity_id') == rid or ev.get('template_id') == rid))
            if found:
                return True, 'Evidence verified: defeated'
        # item
        elif etype == 'item':
            iid = evref.get('id'); need = int(evref.get('count', 1))
            have = inv_counts.get(iid, 0)
            if iid and have >= need:
                return True, 'Evidence verified: item in inventory'
            # fallback: check logs for positive deltas
            if iid:
                gained = sum(ev.get('delta', 0) for ev in log if ev.get('type') == EV_ITEM_DELTA and ev.get('item_id') == iid and ev.get('delta', 0) > 0)
                if gained >= need:
                    return True, 'Evidence verified: item gained in log'
        # visited
        elif etype == 'visited':
            lid = evref.get('id')
            if not lid:
                continue
            found = any_log(lambda ev: ev.get('type') == EV_LOCATION_VISITED and ev.get('location_id') == lid)
            if found:
                return True, 'Evidence verified: visited'
        # flag
        elif etype == 'flag':
            key = evref.get('key'); val = evref.get('value', True)
            if key is not None and flags.get(key) == val:
                return True, 'Evidence verified: flag'
            # fallback: presence in event log
            found = any_log(lambda ev: ev.get('type') == EV_FLAG_SET and ev.get('key') == key and ev.get('value') == val)
            if found:
                return True, 'Evidence verified: flag set (log)'
        # dialogue
        elif etype == 'dialogue':
            did = evref.get('id')
            found = did and any_log(lambda ev: ev.get('type') == EV_DIALOGUE and ev.get('dialogue_id') == did)
            if found:
                return True, 'Evidence verified: dialogue'
        # interaction
        elif etype == 'interaction':
            iid = evref.get('id')
            found = iid and any_log(lambda ev: ev.get('type') == EV_INTERACTION and ev.get('interaction_id') == iid)
            if found:
                return True, 'Evidence verified: interaction'

    return False, 'No verifying evidence found'

# --- Validation helpers ---

def _allowed_objective_transition(old: str, new: str) -> bool:
    if old in (None, '', 'pending', 'active'):
        return new in ('completed', 'failed')
    # Disallow regressions by default
    return False

# --- Orchestrated messages ---

def _queue_system(engine, text: str):
    try:
        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        engine._combat_orchestrator.add_event_to_queue(
            DisplayEvent(
                type=DisplayEventType.SYSTEM_MESSAGE,
                content=text,
                target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                gradual_visual_display=False,
                tts_eligible=False,
            )
        )
    except Exception as e:
        logger.warning(f"Failed to queue system message: {e}")

# --- Apply objective update from LLM ---

def apply_objective_update_from_llm(engine, game_state, payload: Dict[str, Any]) -> Tuple[bool, str]:
    quest_id = payload.get('quest_id')
    objective_id = payload.get('objective_id')
    new_status = payload.get('new_status')
    confidence = float(payload.get('confidence', 0.0))

    if not quest_id or not objective_id or new_status not in ('completed','failed'):
        return False, 'Invalid quest update payload'

    journal = getattr(game_state, 'journal', {})
    quests = journal.get('quests', {}) if isinstance(journal, dict) else {}
    q = quests.get(quest_id)
    if not q:
        return False, f'Unknown quest id: {quest_id}'

    obj = None
    for o in q.get('objectives', []) or []:
        if o.get('id') == objective_id:
            obj = o; break
    if not obj:
        return False, f'Unknown objective id: {objective_id}'

    # Check current status
    old_status = 'completed' if obj.get('completed') else 'failed' if obj.get('failed') else 'pending'
    if not _allowed_objective_transition(old_status, new_status):
        return False, f'Illegal transition from {old_status} to {new_status}'

    # If DSL exists and contradicts proposal, reject
    dsl = obj.get('condition_dsl')
    signals = _build_signals(game_state)
    dsl_eval = _eval_condition_for_quest(dsl, signals, q)
    if new_status == 'completed' and dsl_eval is False:
        return False, 'Contradicts DSL (not satisfied)'

    # Confidence threshold for semantic (when DSL is None)
    if dsl is None:
        if confidence < 0.9:
            return False, 'Confidence too low for semantic objective update'
        ev_ok, ev_msg = _verify_evidence(game_state, payload)
        if not ev_ok:
            return False, f'Evidence check failed: {ev_msg}'

    # Apply update
    if new_status == 'completed':
        obj['completed'] = True; obj['failed'] = False
        _queue_system(engine, f"Objective completed: {obj.get('description','')}" )
    else:
        obj['failed'] = True; obj['completed'] = False
        _queue_system(engine, f"Objective failed: {obj.get('description','')}" )

    # Record event
    try:
        record_objective_status(game_state, quest_id=quest_id, objective_id=objective_id, new_status=new_status)
    except Exception:
        pass

    # Recompute quest status (mandatory logic)
    _recompute_quest_status(engine, q)
    return True, 'Objective update applied'


def _recompute_quest_status(engine, q: Dict[str, Any]) -> None:
    objs = q.get('objectives', []) or []
    mandatory_total = sum(1 for o in objs if o.get('mandatory', True)) or 0
    mandatory_completed = sum(1 for o in objs if o.get('mandatory', True) and o.get('completed', False))
    any_failed = any(o.get('failed', False) for o in objs if o.get('mandatory', True))
    if q.get('abandoned'):
        q['status'] = 'failed'
        return
    if mandatory_total > 0 and mandatory_completed == mandatory_total and not any_failed:
        if q.get('status') != 'completed':
            q['status'] = 'completed'
            _queue_system(engine, f"Quest Completed: {q.get('title','')}" )
    else:
        if q.get('status') == 'completed':
            # Do not regress
            return
        # keep active or failed as is
        if q.get('status') not in ('failed','active'):
            q['status'] = 'active'

# --- Quest-aware DSL evaluation helpers (aliases and resolver) ---

def _quest_alias_candidates(q: Dict[str, Any], domain: str, label: str) -> List[str]:
    """Return candidate canonical IDs for a label using quest-local aliases or global resolver."""
    try:
        if not label:
            return []
        # Quest-local aliases structure suggestion: q['aliases'] = { 'entities': { 'white_wolf': ['wolf_alpha'] }, ...}
        aliases = q.get('aliases', {}) if isinstance(q, dict) else {}
        dom = aliases.get(domain, {}) if isinstance(aliases, dict) else {}
        # Normalize
        if isinstance(dom, dict):
            v = dom.get(label) or dom.get(str(label).lower())
            if isinstance(v, list):
                return [str(x) for x in v]
            if isinstance(v, str):
                return [v]
        # Fall back to global resolver
        try:
            from core.game_flow.reference_resolver import get_reference_resolver
            resolver = get_reference_resolver()
            return resolver.resolve(domain, label)
        except Exception:
            return [label]
    except Exception:
        return [label]


def _label_matches_any(candidates: List[str], haystack: List[str]) -> bool:
    if not candidates or not haystack:
        return False
    hs = set(str(x).lower() for x in haystack)
    for c in candidates:
        if str(c).lower() in hs:
            return True
    return False


def _eval_condition_for_quest(dsl: Any, signals: Dict[str, Any], q: Dict[str, Any]) -> Optional[bool]:
    """Evaluate DSL with quest-aware alias resolution for defeated/visited/inventory_has."""
    try:
        if dsl is None:
            return None
        if isinstance(dsl, bool):
            return dsl
        if isinstance(dsl, dict):
            # Composition
            if 'all' in dsl:
                return all(_eval_condition_for_quest(x, signals, q) is True for x in dsl['all'])
            if 'any' in dsl:
                return any(_eval_condition_for_quest(x, signals, q) is True for x in dsl['any'])
            if 'none' in dsl:
                return all(_eval_condition_for_quest(x, signals, q) is False for x in dsl['none'])
            # Inventory has
            if 'inventory_has' in dsl:
                spec = dsl['inventory_has'] or {}
                item_id = spec.get('item_id')
                count = int(spec.get('count', 1))
                inv = signals.get('inventory', {})
                if item_id:
                    candidates = _quest_alias_candidates(q, 'items', item_id)
                    # sum counts for any candidate
                    have = sum(inv.get(c, 0) for c in candidates)
                    return bool(have >= count)
                return False
            # Defeated
            if 'defeated' in dsl:
                label = dsl['defeated']
                defeated_list = signals.get('defeated', [])
                if label:
                    candidates = _quest_alias_candidates(q, 'entities', label)
                    return _label_matches_any(candidates, defeated_list)
                return False
            # Visited
            if 'visited' in dsl:
                label = dsl['visited']
                visited_list = signals.get('visited', [])
                if label:
                    candidates = _quest_alias_candidates(q, 'locations', label)
                    return _label_matches_any(candidates, visited_list)
                return False
            # Flags and time remain the same
            if 'flag' in dsl:
                key = dsl['flag'].get('key')
                val = dsl['flag'].get('value', True)
                return bool(signals.get('flags', {}).get(key) == val)
            if 'time_before' in dsl:
                t = float(dsl['time_before'])
                return bool(signals.get('time', 0.0) < t)
            if 'time_after' in dsl:
                t = float(dsl['time_after'])
                return bool(signals.get('time', 0.0) > t)
        return None
    except Exception as e:
        logger.warning(f"Quest-aware DSL eval error: {e}")
        return None

# --- Automatic evaluation on events (Phase 1) ---

def _derive_dsl_from_objective(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Derive a minimal DSL from basic objective fields when none is provided."""
    try:
        otype = (obj.get('type') or '').lower()
        target = obj.get('target_id') or obj.get('target')
        if otype == 'kill' and target:
            return {'defeated': target}
        if otype == 'fetch' and target:
            return {'inventory_has': {'item_id': target, 'count': int(obj.get('count', 1))}}
        if otype in ('explore', 'visit') and target:
            return {'visited': target}
        # Interaction/objectives without clear deterministic signals remain semantic-only
        return None
    except Exception:
        return None


def _evaluate_and_update_all(engine, game_state, objective_type_filter: Optional[List[str]] = None) -> None:
    """Evaluate all quest objectives using the DSL and update statuses.
    Non-regressive: once completed/failed, we do not regress here.
    """
    journal = getattr(game_state, 'journal', {}) or {}
    quests = journal.get('quests', {}) if isinstance(journal, dict) else {}
    if not isinstance(quests, dict) or not quests:
        return

    signals = _build_signals(game_state)

    # Evaluate each quest/objective
    for qid, q in quests.items():
        try:
            changed = False
            for obj in (q.get('objectives') or []):
                if not isinstance(obj, dict):
                    continue
                # Optional filter by objective type (event-driven bucketing)
                if objective_type_filter:
                    otype = str(obj.get('type', '')).lower()
                    if otype not in [t.lower() for t in objective_type_filter]:
                        continue
                # Skip if already terminal
                if obj.get('completed') or obj.get('failed'):
                    continue
                # DEV: log objective scan line
                if _dev_quest_verbose():
                    try:
                        _queue_dev(engine, f"Check objective q='{qid}' id='{obj.get('id')}' type='{obj.get('type')}' target='{obj.get('target_id')}'")
                    except Exception:
                        pass
                # Ensure activation_time is set when we first see the objective
                try:
                    if 'activation_time' not in obj or obj.get('activation_time') is None:
                        obj['activation_time'] = getattr(game_state.world, 'game_time', 0.0)
                except Exception:
                    pass
                # Time-based failure via time_limit_s
                try:
                    time_limit = obj.get('time_limit_s')
                    if time_limit is not None:
                        activation = float(obj.get('activation_time', getattr(game_state.world, 'game_time', 0.0)))
                        now = getattr(game_state.world, 'game_time', 0.0)
                        if now >= activation + float(time_limit):
                            obj['failed'] = True
                            obj['completed'] = False
                            try:
                                record_objective_status(game_state, quest_id=qid, objective_id=str(obj.get('id')), new_status='failed')
                            except Exception:
                                pass
                            changed = True
                            # No further evaluation if failed by time
                            continue
                except Exception:
                    pass
                # Completion DSL
                dsl = obj.get('condition_dsl')
                # Derive a minimal DSL when not provided for basic objective types
                if dsl is None:
                    dsl = _derive_dsl_from_objective(obj)
                    if _dev_quest_verbose() and dsl is not None:
                        try:
                            _queue_dev(engine, f"Derived DSL for objective '{obj.get('id')}' -> {dsl}")
                        except Exception:
                            pass
                    if dsl is None:
                        continue  # semantic-only; skip auto when still None
                ev = _eval_condition_dsl(dsl, signals)
                # Dev-verbose: log evaluation result per objective and a small defeated snapshot
                if _dev_quest_verbose():
                    try:
                        defeated_snapshot = signals.get('defeated', [])[:6]
                        _queue_dev(engine, f"Objective eval: id='{obj.get('id')}', desc='{obj.get('description','')}', result={ev}, defeated~={defeated_snapshot}")
                    except Exception:
                        pass
                if ev is True:
                    obj['completed'] = True; obj['failed'] = False
                    try:
                        record_objective_status(game_state, quest_id=qid, objective_id=str(obj.get('id')), new_status='completed')
                    except Exception:
                        pass
                    changed = True
            if changed:
                _recompute_quest_status(engine, q)
                if _dev_quest_verbose():
                    try:
                        _queue_dev(engine, f"Quest '{q.get('title','')}' status recomputed: {q.get('status')}")
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Quest evaluation error for {qid}: {e}")


def process_event_for_quests(engine, game_state, event: Dict[str, Any]) -> None:
    """Phase 1 hook: after an event is logged, re-evaluate quest objectives.
    For now, re-evaluate all quests for simplicity. Later, index by event type.
    """
    try:
        et = event.get('type')
        # Suppress noisy dev logs during startup before quests are activated
        try:
            journal = getattr(game_state, 'journal', {}) or {}
            quests = journal.get('quests', {}) if isinstance(journal, dict) else {}
            quests_empty = not bool(quests)
        except Exception:
            quests_empty = True
        if quests_empty:
            # No quests to evaluate yet; skip dev logs and evaluation safely
            return
        if _dev_quest_verbose():
            try:
                _queue_dev(engine, f"Quest evaluation triggered by event: {et}")
            except Exception:
                pass
        # Map events to objective type filters (bucketing)
        type_map = {
            EV_ENEMY_DEFEATED: ["kill"],
            EV_ITEM_DELTA: ["fetch"],
            EV_LOCATION_VISITED: ["explore", "visit"],
            EV_DIALOGUE: ["interact"],
            EV_INTERACTION: ["interact"],
            EV_FLAG_SET: ["flag"],
        }
        filt = type_map.get(et)
        if et in (EV_ENEMY_DEFEATED, EV_ITEM_DELTA, EV_LOCATION_VISITED, EV_DIALOGUE, EV_INTERACTION, EV_FLAG_SET,):
            # DEV: show event normalization snapshot for EnemyDefeated
            if _dev_quest_verbose() and et == EV_ENEMY_DEFEATED:
                try:
                    tid = (event.get('template_id') or '')
                    tags = event.get('tags', {}) or {}
                    cname = str(tags.get('combat_name', '') or '')
                    tid_l = tid.lower() if tid else ''
                    cname_l = cname.lower() if cname else ''
                    base = re.sub(r'_[0-9]+$', '', cname_l) if cname_l else ''
                    _queue_dev(engine, f"EnemyDefeated norm: template_id='{tid_l}', combat_name='{cname_l}', base='{base}'")
                except Exception:
                    pass
            # Evaluate only relevant objectives
            if _dev_quest_verbose():
                try:
                    filt_str = ",".join(filt) if filt else "all"
                    from collections import Counter
                    journal = getattr(game_state, 'journal', {}) or {}
                    quests = journal.get('quests', {}) if isinstance(journal, dict) else {}
                    total = 0
                    types = []
                    for _, q in quests.items():
                        for obj in (q.get('objectives') or []):
                            if isinstance(obj, dict):
                                types.append(str(obj.get('type','')).lower())
                                total += 1
                    counts = dict(Counter(types))
                    _queue_dev(engine, f"Objective scan: total={total}, types={counts}, filter={filt_str}")
                except Exception:
                    pass
            _evaluate_and_update_all(engine, game_state, objective_type_filter=filt)
            # Optional LLM fallback for near-match kill objectives
            try:
                if et == EV_ENEMY_DEFEATED and get_config().get("quests.llm_fallback.enabled", False):
                    _attempt_llm_fallback_for_kill(engine, game_state, event)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"process_event_for_quests failed: {e}")


# --- LLM Fallback (Last Resort) ---

def _attempt_llm_fallback_for_kill(engine, game_state, event: Dict[str, Any]) -> None:
    """As a last resort, ask the LLM to confirm if a 'kill' objective is satisfied given a near match.
    Debounced implicitly by only running once per EnemyDefeated event.
    """
    try:
        # Extract normalized labels from event
        tid = (event.get('template_id') or '')
        tags = event.get('tags', {}) or {}
        cname = str(tags.get('combat_name', '') or '')
        tid_l = tid.lower() if tid else ''
        cname_l = cname.lower() if cname else ''
        base = re.sub(r'_[0-9]+$', '', cname_l) if cname_l else ''
        if not (tid_l or base or cname_l):
            return
        # Iterate active quests and kill objectives that are not completed/failed
        journal = getattr(game_state, 'journal', {}) or {}
        quests = journal.get('quests', {}) if isinstance(journal, dict) else {}
        for qid, q in quests.items():
            for obj in (q.get('objectives') or []):
                if not isinstance(obj, dict):
                    continue
                if obj.get('completed') or obj.get('failed'):
                    continue
                if str(obj.get('type','')).lower() != 'kill':
                    continue
                label = str(obj.get('target_id') or '').lower()
                if not label:
                    continue
                # Near match heuristic
                if label in (tid_l, base, cname_l):
                    # Ask LLM once for confirmation
                    try:
                        from core.game_flow.interaction_core import process_with_llm
                        prompt = (
                            "You are verifying a quest objective.\n"
                            f"Objective: defeat '{label}'.\n"
                            f"Recent event: enemy defeated with template_id='{tid_l}', combat_name='{cname_l}'.\n"
                            "Question: Has the objective been satisfied?\n"
                            "Reply with exactly one word: YES or NO."
                        )
                        result = process_with_llm(game_state, prompt)
                        if getattr(result, 'is_success', False) and isinstance(result.message, str):
                            ans = result.message.strip().lower()
                            if ans.startswith('yes'):
                                obj['completed'] = True; obj['failed'] = False
                                try:
                                    record_objective_status(game_state, quest_id=qid, objective_id=str(obj.get('id')), new_status='completed')
                                except Exception:
                                    pass
                                _recompute_quest_status(engine, q)
                                if _dev_quest_verbose():
                                    _queue_dev(engine, f"LLM fallback confirmed completion for kill objective '{obj.get('id')}'.")
                    except Exception as e:
                        logger.warning(f"LLM fallback error: {e}")
    except Exception as e:
        logger.warning(f"fallback_for_kill failed: {e}")

# --- Apply quest status from LLM ---

def apply_quest_status_from_llm(engine, game_state, payload: Dict[str, Any]) -> Tuple[bool, str]:
    quest_id = payload.get('quest_id')
    new_status = payload.get('new_status')
    confidence = float(payload.get('confidence', 0.0))

    if not quest_id or new_status not in ('active','completed','failed','abandoned'):
        return False, 'Invalid quest status payload'

    journal = getattr(game_state, 'journal', {})
    quests = journal.get('quests', {}) if isinstance(journal, dict) else {}
    q = quests.get(quest_id)
    if not q:
        return False, f'Unknown quest id: {quest_id}'

    # Enforce policy: completed derived from mandatory objectives; abandoned/failed allowed with high confidence
    if new_status == 'completed':
        # Derive rather than accept
        _recompute_quest_status(engine, q)
        try:
            record_quest_status(game_state, quest_id=quest_id, new_status=q.get('status','active'))
        except Exception:
            pass
        return True, 'Quest status derived from objectives'

    if new_status in ('failed','abandoned'):
        if confidence < 0.95:
            return False, 'Confidence too low for failing/abandoning quest'
        # Require at least one piece of evidence
        ev_ok, ev_msg = _verify_evidence(game_state, payload)
        if not ev_ok:
            return False, f'Evidence check failed: {ev_msg}'
        q['status'] = 'failed'
        if new_status == 'abandoned':
            q['abandoned'] = True
            _queue_system(engine, f"Quest Abandoned: {q.get('title','')}" )
        else:
            _queue_system(engine, f"Quest Failed: {q.get('title','')}" )
        try:
            record_quest_status(game_state, quest_id=quest_id, new_status=q['status'])
        except Exception:
            pass
        return True, 'Quest status update applied'

    if new_status == 'active':
        # Disallow reopen by default
        return False, 'Reopening quests not allowed by default'

    return False, 'Unhandled quest status'

# --- Time-based processing on tick ---

def process_time_for_quests(engine, game_state) -> None:
    """Checks time-based failure conditions (deadlines) on tick.
    Lightweight scan of active objectives that have time_limit_s.
    """
    try:
        journal = getattr(game_state, 'journal', {}) or {}
        quests = journal.get('quests', {}) if isinstance(journal, dict) else {}
        now = getattr(game_state.world, 'game_time', 0.0)
        any_changed = False
        for qid, q in quests.items():
            changed_q = False
            for obj in (q.get('objectives') or []):
                if not isinstance(obj, dict):
                    continue
                if obj.get('completed') or obj.get('failed'):
                    continue
                time_limit = obj.get('time_limit_s')
                if time_limit is None:
                    continue
                activation = float(obj.get('activation_time', now))
                if now >= activation + float(time_limit):
                    obj['failed'] = True
                    obj['completed'] = False
                    try:
                        record_objective_status(game_state, quest_id=qid, objective_id=str(obj.get('id')), new_status='failed')
                    except Exception:
                        pass
                    changed_q = True
                    any_changed = True
            if changed_q:
                _recompute_quest_status(engine, q)
        if any_changed and _dev_quest_verbose():
            _queue_dev(engine, "Processed time-based objective failures on tick.")
    except Exception as e:
        logger.warning(f"process_time_for_quests error: {e}")

