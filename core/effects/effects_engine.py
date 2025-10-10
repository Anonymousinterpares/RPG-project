#!/usr/bin/env python3
"""
Minimal effects interpreter (Phase 2) — additive and non-invasive.

- Consumes validated effect atoms (see config/gameplay/effect_atoms.schema.json)
- Applies deterministic changes via managers (StatsManager, ModifierManager, StatusEffectManager)
- No UI calls; caller is responsible for emitting DisplayEvents
- Target resolution is left to the caller (provide targets with their stats managers)

NOTE: Out-of-combat minute-based durations are recorded in custom_data for future handling.
      In-combat turn-based durations use existing duration decrement logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.utils.logging_config import get_logger
from core.stats.stats_base import DerivedStatType
from core.stats.modifier import ModifierGroup, ModifierSource, ModifierType
from core.stats.combat_effects import StatusEffect, StatusEffectType
from core.stats.registry import resolve_stat_enum
from core.utils.dice import roll_dice_notation

logger = get_logger("EFFECTS")


@dataclass
class TargetContext:
    """Represents a target with a StatsManager-like interface."""
    id: str
    name: Optional[str]
    stats_manager: Any  # Expecting an object exposing get_stat_value, get_current_stat_value, set_current_stat, add_modifier_group, status_effect_manager


@dataclass
class AppliedAtomResult:
    atom_index: int
    atom_type: str
    target_ids: List[str] = field(default_factory=list)
    amount: Optional[float] = None  # For damage/heal/resource_change
    modifiers_applied: int = 0
    status_name: Optional[str] = None
    error: Optional[str] = None


@dataclass
class EffectResult:
    success: bool
    applied: List[AppliedAtomResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _compute_magnitude(atom: Dict[str, Any], caster: Optional[TargetContext]) -> float:
    """Compute a numeric magnitude from the atom's magnitude spec.
    Supports dice, flat, and stat_based (stat * coeff + base, clamped by optional min/max).
    """
    mag = atom.get("magnitude") or {}
    # Dice
    if isinstance(mag, dict) and "dice" in mag:
        try:
            res = roll_dice_notation(str(mag["dice"]))
            return float(res.get("total", 0))
        except Exception as e:
            logger.warning(f"Invalid dice magnitude {mag!r}: {e}")
            return 0.0
    # Flat
    if isinstance(mag, dict) and "flat" in mag:
        try:
            return float(mag["flat"])
        except Exception:
            return 0.0
    # Stat-based
    if isinstance(mag, dict) and "stat" in mag and "coeff" in mag:
        try:
            stat_key = str(mag["stat"]).strip()
            coeff = float(mag.get("coeff", 0))
            base = float(mag.get("base", 0))
            val = 0.0
            if caster and caster.stats_manager:
                enum_val = resolve_stat_enum(stat_key)  # StatType or DerivedStatType
                if enum_val is not None:
                    try:
                        val = float(caster.stats_manager.get_stat_value(enum_val))
                    except Exception:
                        val = 0.0
            total = (val * coeff) + base
            if "min" in mag:
                total = max(float(mag["min"]), total)
            if "max" in mag:
                total = min(float(mag["max"]), total)
            return float(total)
        except Exception as e:
            logger.warning(f"stat_based magnitude failed: {e}")
            return 0.0
    # Default
    return 0.0


def _apply_resource_change(target: TargetContext, resource: str, delta: float) -> float:
    """Apply a delta to the specified resource on the target and return applied amount."""
    try:
        dt = DerivedStatType[resource.upper()]
    except Exception:
        # Support convenience for heal/damage mapping
        if resource.upper() in ("HEALTH", "HP"):
            dt = DerivedStatType.HEALTH
        elif resource.upper() in ("MANA", "MP"):
            dt = DerivedStatType.MANA
        elif resource.upper() == "STAMINA":
            dt = DerivedStatType.STAMINA
        elif resource.upper() == "RESOLVE":
            dt = DerivedStatType.RESOLVE
        else:
            raise ValueError(f"Unknown resource '{resource}'")

    sm = target.stats_manager
    current = float(sm.get_current_stat_value(dt))
    new_val = current + float(delta)
    # set_current_stat will clamp internally using MAX_ counterpart
    sm.set_current_stat(dt, new_val)
    return float(delta)


def _apply_modifiers_group(target: TargetContext, atom: Dict[str, Any], source_name: str) -> int:
    """Apply a group of stat modifiers to the target. Returns count of modifiers applied."""
    duration = atom.get("duration")
    dur_val: Optional[int] = None
    dur_unit: Optional[str] = None
    if isinstance(duration, dict):
        dur_unit = str(duration.get("unit") or "").strip().lower()
        try:
            dur_val = int(duration.get("value"))
        except Exception:
            dur_val = None

    mod_type = ModifierType.TEMPORARY if dur_val else ModifierType.PERMANENT
    group = ModifierGroup(
        name=source_name,
        source_type=ModifierSource.SPELL,
        modifier_type=mod_type,
        duration=dur_val,
        description=atom.get("notes", "")
    )
    mods = atom.get("modifiers") or []
    count = 0
    for m in mods:
        try:
            stat_key = str(m.get("stat", "")).strip()
            enum_val = resolve_stat_enum(stat_key)
            if enum_val is None:
                logger.warning(f"Unknown stat in modifier: {stat_key}")
                continue
            value = float(m.get("value", 0))
            is_pct = bool(m.get("is_percentage", False))
            desc = str(m.get("description", ""))
            group.add_modifier(enum_val, value, is_percentage=is_pct, stacks=False, description=desc)
            count += 1
        except Exception as e:
            logger.warning(f"Failed to add modifier {m}: {e}")
    if count > 0:
        try:
            target.stats_manager.add_modifier_group(group)
        except Exception as e:
            logger.error(f"Failed to apply modifier group: {e}")
    return count


def _apply_status_apply(target: TargetContext, atom: Dict[str, Any], source_name: str) -> str:
    name = str(atom.get("status", "")).strip()
    duration = atom.get("duration")
    dur_val = 1
    dur_unit = None
    if isinstance(duration, dict):
        try:
            dur_val = int(duration.get("value", 1))
        except Exception:
            dur_val = 1
        dur_unit = str(duration.get("unit") or "").strip().lower()

    eff_type = StatusEffectType.SPECIAL
    try:
        # Optional: support quick type hints via atom.tags like 'debuff'
        tag_types = {"buff": StatusEffectType.BUFF, "debuff": StatusEffectType.DEBUFF,
                     "crowd_control": StatusEffectType.CROWD_CONTROL, "damage_over_time": StatusEffectType.DAMAGE_OVER_TIME}
        for t in atom.get("tags", []) or []:
            k = str(t).strip().lower()
            if k in tag_types:
                eff_type = tag_types[k]
                break
    except Exception:
        pass

    mg_count = 0
    # Some statuses carry modifiers inline
    if atom.get("modifiers"):
        mg_count = _apply_modifiers_group(target, atom, source_name=f"Status:{name}")

    custom_data = {}
    if dur_unit and dur_unit != "turns":
        custom_data["duration_unit"] = dur_unit
        custom_data["duration_value"] = dur_val

    effect = StatusEffect(
        name=name or source_name,
        description=atom.get("notes", ""),
        effect_type=eff_type,
        duration=max(1, int(dur_val)),
        modifier_group=None,  # modifiers already applied as a separate group when present
        buff_is_visible=True,
        custom_data=custom_data or None
    )
    try:
        target.stats_manager.add_status_effect(effect)
    except Exception as e:
        logger.error(f"Failed to add status effect '{name}': {e}")
    return name


def _apply_status_remove_or_cleanse(target: TargetContext, atom: Dict[str, Any]) -> int:
    sm = target.stats_manager
    removed = 0
    try:
        if atom.get("status"):
            name = str(atom.get("status")).strip()
            removed += sm.status_effect_manager.remove_effects_by_name(name)
        elif atom.get("status_types"):
            for t in atom.get("status_types"):
                try:
                    et = StatusEffectType[str(t).strip().upper()]
                except Exception:
                    continue
                removed += sm.status_effect_manager.remove_effects_by_type(et)
    except Exception as e:
        logger.error(f"Failed to remove/cleanse statuses: {e}")
    return removed


def apply_effects(
    atoms: List[Dict[str, Any]],
    caster: Optional[TargetContext],
    targets: List[TargetContext]
) -> EffectResult:
    """
    Apply a sequence of effect atoms to targets.

    Args:
      atoms: list of effect atom dicts (validated against the schema)
      caster: the caster context (can be None if not needed for stat_based)
      targets: resolved target contexts (caller decides selector semantics)

    Returns:
      EffectResult with per-atom summaries and any errors encountered.
    """
    result = EffectResult(success=True)
    if not isinstance(atoms, list) or not atoms:
        return EffectResult(success=False, errors=["No atoms provided."])

    # Simple fan-out: apply each atom to all provided targets; caller decides routing by selector
    for idx, atom in enumerate(atoms):
        a_type = str(atom.get("type", "")).strip().lower()
        applied = AppliedAtomResult(atom_index=idx, atom_type=a_type, target_ids=[t.id for t in targets])
        try:
            if a_type in ("damage", "heal", "resource_change"):
                # Map heal/damage to resource_change on HEALTH
                resource = atom.get("resource")
                if a_type == "heal":
                    resource = resource or "HEALTH"
                elif a_type == "damage":
                    resource = resource or "HEALTH"
                mag = _compute_magnitude(atom, caster)
                # damage should subtract health; heal adds
                if a_type == "damage":
                    mag = -abs(mag)
                # resource_change uses magnitude sign as-is
                total_applied = 0.0
                for tgt in targets:
                    total_applied += _apply_resource_change(tgt, str(resource), float(mag))
                applied.amount = float(total_applied)

            elif a_type in ("buff", "debuff"):
                count_total = 0
                source_name = atom.get("notes") or ("Buff" if a_type == "buff" else "Debuff")
                for tgt in targets:
                    count_total += _apply_modifiers_group(tgt, atom, source_name)
                applied.modifiers_applied = count_total

            elif a_type == "status_apply":
                last_name = None
                for tgt in targets:
                    last_name = _apply_status_apply(tgt, atom, source_name="Status")
                applied.status_name = last_name

            elif a_type in ("status_remove", "cleanse"):
                removed_total = 0
                for tgt in targets:
                    removed_total += _apply_status_remove_or_cleanse(tgt, atom)
                applied.modifiers_applied = removed_total  # reuse field to indicate count

            elif a_type == "shield":
                # For now treat as a buff placeholder (future: temp HP/absorb pool tracked elsewhere)
                count_total = 0
                for tgt in targets:
                    count_total += _apply_modifiers_group(tgt, atom, source_name="Shield")
                applied.modifiers_applied = count_total

            else:
                msg = f"Unknown atom type '{a_type}'"
                logger.warning(msg)
                applied.error = msg
                result.errors.append(msg)

        except Exception as e:
            applied.error = str(e)
            result.errors.append(f"Atom {idx} failed: {e}")
            logger.error(f"Failed to apply atom {idx}: {e}", exc_info=True)
        finally:
            result.applied.append(applied)

    if result.errors:
        result.success = False
    return result
