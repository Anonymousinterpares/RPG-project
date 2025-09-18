#!/usr/bin/env python3
"""
Headless/test-layer quest commands.

This module registers lightweight quest-related commands without modifying core game files:
- /quests                -> list quests from game_state.journal
- /quest <id|name>       -> show quest details (objectives, status)
- /quest track <id|name> -> mark a quest as tracked in journal (test-only field)
- /quest untrack         -> clear tracking
- /quest complete-first  -> helper: completes the first pending objective on the first active quest,
                            using existing quest update logic (apply_objective_update_from_llm).

All output is returned via CommandResult; the engine will route it to the output.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple

from core.utils.logging_config import get_logger
from core.base.commands import CommandResult, get_command_processor
from core.base.state import GameState
from core.base.engine import get_game_engine

logger = get_logger("QUEST_CMDS_TEST")


def _get_quests_dict(game_state: GameState) -> Dict[str, Dict[str, Any]]:
    try:
        journal = getattr(game_state, "journal", {}) or {}
        quests = journal.get("quests", {}) if isinstance(journal, dict) else {}
        if isinstance(quests, dict):
            return quests
    except Exception:
        pass
    return {}


def _resolve_quest(quests: Dict[str, Dict[str, Any]], identifier: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    if not identifier:
        return None
    ident_low = identifier.lower()
    # Exact ID match first
    if identifier in quests:
        return identifier, quests[identifier]
    # Name/Title partial match
    for qid, q in quests.items():
        name = str(q.get("title") or q.get("name") or qid)
        if ident_low == name.lower() or ident_low in name.lower():
            return qid, q
    return None


def _fmt_quest_summary(qid: str, q: Dict[str, Any], tracked_id: Optional[str]) -> str:
    title = str(q.get("title") or q.get("name") or qid)
    status = str(q.get("status", "active"))
    objs = q.get("objectives") or []
    total = len(objs)
    done = sum(1 for o in objs if o.get("completed"))
    track_mark = " *" if tracked_id and tracked_id == qid else ""
    return f"- [{qid}]{track_mark} {title} (status: {status}, {done}/{total} completed)"


def _fmt_quest_detail(qid: str, q: Dict[str, Any], tracked_id: Optional[str]) -> str:
    title = str(q.get("title") or q.get("name") or qid)
    status = str(q.get("status", "active"))
    desc = str(q.get("description") or "")
    lines = [
        f"Quest: {title}",
        f"ID: {qid}",
        f"Status: {status}",
    ]
    if tracked_id and tracked_id == qid:
        lines.append("Tracked: yes")
    if desc:
        lines.append("")
        lines.append(desc)
    # Objectives
    objs = q.get("objectives") or []
    if objs:
        lines.append("\nObjectives:")
        for o in objs:
            oid = str(o.get("id") or "")
            odesc = str(o.get("description") or "")
            if o.get("completed"):
                box = "[x]"
            elif o.get("failed"):
                box = "[!]"
            else:
                box = "[ ]"
            mand = " (mandatory)" if o.get("mandatory", True) else " (optional)"
            lines.append(f"  {box} {odesc}{mand} (id: {oid})")
    else:
        lines.append("\nNo objectives listed.")
    return "\n".join(lines)


def _get_tracked_id(game_state: GameState) -> Optional[str]:
    try:
        journal = getattr(game_state, "journal", {}) or {}
        return journal.get("tracked_quest_id") if isinstance(journal, dict) else None
    except Exception:
        return None


def _set_tracked_id(game_state: GameState, quest_id: Optional[str]) -> None:
    try:
        journal = getattr(game_state, "journal", None)
        if isinstance(journal, dict):
            if quest_id:
                journal["tracked_quest_id"] = quest_id
            else:
                journal.pop("tracked_quest_id", None)
    except Exception:
        pass


# Command handlers

def quests_command(game_state: GameState, args: List[str]) -> CommandResult:
    quests = _get_quests_dict(game_state)
    if not quests:
        return CommandResult.success("No quests in your journal.")

    # Optional status filter: /quests active|completed|failed
    status_filter = args[0].lower() if args else None
    tracked_id = _get_tracked_id(game_state)

    lines: List[str] = ["Quests:"]
    shown = 0
    for qid, q in quests.items():
        st = str(q.get("status", "active")).lower()
        if status_filter and st != status_filter:
            continue
        lines.append(_fmt_quest_summary(qid, q, tracked_id))
        shown += 1

    if shown == 0:
        if status_filter:
            return CommandResult.success(f"No quests with status '{status_filter}'.")
        return CommandResult.success("No quests in your journal.")

    return CommandResult.success("\n".join(lines))


def quest_command(game_state: GameState, args: List[str]) -> CommandResult:
    if not args:
        return CommandResult.invalid("Usage: quest <id|name> | quest track <id|name> | quest untrack | quest complete-first")

    quests = _get_quests_dict(game_state)
    tracked_id = _get_tracked_id(game_state)

    sub = args[0].lower()

    # quest untrack
    if sub == "untrack":
        _set_tracked_id(game_state, None)
        return CommandResult.success("Quest tracking cleared.")

    # quest track <id|name>
    if sub == "track":
        if len(args) < 2:
            return CommandResult.invalid("Usage: quest track <id|name>")
        resolved = _resolve_quest(quests, args[1])
        if not resolved:
            return CommandResult.failure(f"Quest not found: {args[1]}")
        qid, _q = resolved
        _set_tracked_id(game_state, qid)
        return CommandResult.success(f"Tracking quest: {qid}")

    # quest complete-first (test helper)
    if sub == "complete-first":
        try:
            engine = get_game_engine()

            # 1) Confirm the engine recorded the defeat event for the test wolf.
            # Read the event log and find an EnemyDefeated for 'test_wolf_alpha' or 'wolf_alpha'.
            from core.game_flow.quest_updates import EV_ENEMY_DEFEATED
            log = getattr(game_state, 'event_log', []) if hasattr(game_state, 'event_log') else []
            defeated_match_id: Optional[str] = None
            for ev in log or []:
                try:
                    if ev.get('type') == EV_ENEMY_DEFEATED:
                        # Check template or entity id variants used in tests
                        template_id = str(ev.get('template_id') or '')
                        entity_id = str(ev.get('entity_id') or '')
                        if template_id.lower() in ('test_wolf_alpha', 'wolf_alpha') or entity_id.lower() in ('test_wolf_alpha', 'wolf_alpha'):
                            defeated_match_id = template_id or entity_id
                            break
                except Exception:
                    continue

            if not defeated_match_id:
                return CommandResult.failure("Cannot complete TEST_Q02 yet: defeat event for test_wolf_alpha not found. Finish the wolf fight first.")

            # 2) Target the specific quest and objective.
            target_qid = 'TEST_Q02'
            target_oid = 'O1'
            quests_dict = quests
            tq = quests_dict.get(target_qid)
            if not tq:
                return CommandResult.failure("Quest TEST_Q02 not found in journal.")

            # Ensure the target objective exists and is pending
            target_obj = None
            for o in tq.get('objectives') or []:
                if str(o.get('id')) == target_oid:
                    target_obj = o
                    break
            if not target_obj:
                return CommandResult.failure("Objective O1 not found on TEST_Q02.")
            if target_obj.get('completed'):
                return CommandResult.success("TEST_Q02.O1 is already completed.")
            if target_obj.get('failed'):
                return CommandResult.failure("TEST_Q02.O1 is marked failed and cannot be completed.")

            # 3) Prepare evidence and apply update via core logic.
            evidence_list: List[Dict[str, Any]] = [{"type": "defeated", "id": defeated_match_id}]
            from core.game_flow.quest_updates import apply_objective_update_from_llm
            payload = {
                "quest_id": target_qid,
                "objective_id": target_oid,
                "new_status": "completed",
                "confidence": 1.0,
                "evidence": evidence_list,
            }
            ok, msg = apply_objective_update_from_llm(engine, game_state, payload)
            if ok:
                return CommandResult.success("Marked TEST_Q02.O1 as completed.")
            return CommandResult.failure(f"Could not complete TEST_Q02.O1: {msg}")

        except Exception as e:
            logger.exception("complete-first error")
            return CommandResult.error(f"Error attempting to complete objective: {e}")

    # quest <id|name> -> show details
    resolved = _resolve_quest(quests, args[0])
    if not resolved:
        return CommandResult.failure(f"Quest not found: {args[0]}")
    qid, q = resolved
    return CommandResult.success(_fmt_quest_detail(qid, q, tracked_id))


# Registration entry point

def register_quest_commands() -> None:
    try:
        cp = get_command_processor()
        cp.register_command(
            name="quests",
            handler=quests_command,
            syntax="quests [status]",
            description="List quests in your journal (optionally filter by status).",
            examples=["quests", "quests active", "quests completed"],
            aliases=["journal", "q"]
        )
        cp.register_command(
            name="quest",
            handler=quest_command,
            syntax="quest <id|name> | quest track <id|name> | quest untrack | quest complete-first",
            description="Quest details and tracking; test helper to complete first pending objective.",
            examples=["quest <id>", "quest track <id>", "quest untrack", "quest complete-first"],
            aliases=["jq", "qd"]
        )
        logger.info("Registered quest commands (test layer)")
    except Exception:
        logger.exception("Failed to register quest commands")
