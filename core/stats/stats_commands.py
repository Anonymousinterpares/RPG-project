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
    hp_max = stats_mgr.get_stat_value(DerivedStatType.MAX_HEALTH)
    mana_max = stats_mgr.get_stat_value(DerivedStatType.MAX_MANA)
    stamina_max = stats_mgr.get_stat_value(DerivedStatType.MAX_STAMINA)
    
    lines.append(f"HP: {p.hp:.1f}/{hp_max:.1f} | Mana: {p.mana:.1f}/{mana_max:.1f} | Stamina: {p.stamina:.1f}/{stamina_max:.1f}")
    
    # Check if resolve exists
    try:
        max_resolve = stats_mgr.get_stat_value(DerivedStatType.MAX_RESOLVE)
        curr_resolve = getattr(p, 'resolve', 0.0)
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
