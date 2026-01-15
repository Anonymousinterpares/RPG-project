#!/usr/bin/env python3
"""
Character status/stats command handlers for the RPG game.
"""

from typing import List
import math
from core.utils.logging_config import get_logger
from core.base.state import GameState
from core.base.commands import CommandResult, get_command_processor
from core.stats.stats_manager import get_stats_manager
from core.stats.stats_base import StatType, DerivedStatType

logger = get_logger("STATS_CMDS")

def status_command(game_state: GameState, args: List[str]) -> CommandResult:
    """Display character status and stats."""
    stats_mgr = get_stats_manager()
    if not stats_mgr:
        return CommandResult.error("Stats manager not available.")

    lines = []
    p = game_state.player
    
    lines.append(f"--- Character Status: {p.name} ---")
    lines.append(f"Level: {p.level} {p.race} {p.path}")
    lines.append("")

    # Vitals
    hp_curr = stats_mgr.get_current_stat_value(DerivedStatType.HEALTH)
    hp_max = stats_mgr.get_stat_value(DerivedStatType.MAX_HEALTH)
    mana_curr = stats_mgr.get_current_stat_value(DerivedStatType.MANA)
    mana_max = stats_mgr.get_stat_value(DerivedStatType.MAX_MANA)
    stamina_curr = stats_mgr.get_current_stat_value(DerivedStatType.STAMINA)
    stamina_max = stats_mgr.get_stat_value(DerivedStatType.MAX_STAMINA)
    
    lines.append(f"HP: {hp_curr:.1f}/{hp_max:.1f} | Mana: {mana_curr:.1f}/{mana_max:.1f} | Stamina: {stamina_curr:.1f}/{stamina_max:.1f}")
    
    # Check if resolve exists
    try:
        max_resolve = stats_mgr.get_stat_value(DerivedStatType.MAX_RESOLVE)
        curr_resolve = stats_mgr.get_current_stat_value(DerivedStatType.RESOLVE)
        lines.append(f"Resolve: {curr_resolve:.1f}/{max_resolve:.1f}")
    except (AttributeError, ValueError):
        pass
    
    lines.append("")
    lines.append("Primary Stats:")
    
    # Primary Stats
    for stat_type in StatType:
        val = stats_mgr.get_stat_value(stat_type)
        # Calculate modifier
        mod = math.floor((val - 10) / 2)
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        name_pretty = stat_type.value.replace("_", " ").title()
        lines.append(f"  {name_pretty:<12}: {val:>2.0f} ({mod_str})")

    # Skills section
    lines.append("")
    lines.append("Skills:")
    all_stats = stats_mgr.get_all_stats()
    skills = all_stats.get("skills", {})
    if not skills:
        lines.append("  No skills learned yet.")
    else:
        # Sort skills by value
        sorted_skills = sorted(skills.items(), key=lambda x: x[1].get('value', 0), reverse=True)
        for skill_id, skill_data in sorted_skills:
            name = skill_data.get("name", skill_id.replace("_", " ").title())
            val = skill_data.get("value", 0.0)
            lines.append(f"  {name:<15}: {val:>4.1f}")

    lines.append("")
    lines.append("Derived Stats:")
    # Some key derived stats
    display_derived = [
        DerivedStatType.INITIATIVE,
        DerivedStatType.DEFENSE,
        DerivedStatType.MAGIC_DEFENSE,
        DerivedStatType.MELEE_ATTACK,
        DerivedStatType.RANGED_ATTACK,
        DerivedStatType.MAGIC_ATTACK,
        DerivedStatType.MOVEMENT,
        DerivedStatType.CARRY_CAPACITY
    ]
    
    for dst in display_derived:
        try:
            val = stats_mgr.get_stat_value(dst)
            name = dst.value.replace("_", " ").title()
            lines.append(f"  {name:<15}: {val:>4.1f}")
        except Exception:
            continue

    return CommandResult.success("\n".join(lines))

def register_stats_commands():
    """Register stats-related commands."""
    cp = get_command_processor()
    cp.register_command(
        name="status",
        handler=status_command,
        syntax="status",
        description="Display your character's current stats and status.",
        aliases=["stats", "character", "sheet", "GET_STATS"]
    )
