#!/usr/bin/env python3
"""
NPCFamilyGenerator: Generate NPCs from families/variants configs (Phase 1).

Phase 1 goals:
- Load and merge NPC family definitions from config via GameConfig (no direct file reads)
- Generate a basic combat-ready NPC from a given family_id
- Map family stat_budgets (hp/damage/defense/initiative) to StatsManager primary/derived stats
- No equipment/ability generation yet

Note: This is a minimal generator to enable switching from legacy npc_templates
in a controlled manner (via system.npc_generation_mode = "families").
"""
from __future__ import annotations

import logging
import random
from typing import Any, Dict, Optional, Tuple

from core.base.config import get_config
from core.character.npc_base import NPC, NPCType, NPCRelationship
from core.stats.stats_manager import StatsManager
from core.stats.stats_base import StatType, DerivedStatType
from core.stats.derived_stats import get_modifier_from_stat

logger = logging.getLogger(__name__)


class NPCFamilyGenerator:
    """Generate NPCs using the new families config (Phase 1).

    This generator:
    - Merges families from npc_families and npc_families_factions
    - Ignores variants in Phase 1 (added later)
    - Maps family stat_budgets to StatsManager values in a simple, reproducible way
    """

    def __init__(self) -> None:
        self._config = get_config()
        self._families: Dict[str, Dict[str, Any]] = self._load_and_merge_families()
        self._variants: Dict[str, Dict[str, Any]] = (self._config.get("npc_variants.variants") or {})
        self._tags: Dict[str, Any] = self._config.get("npc_tags.tags", {}) or {}
        self._overlays: Dict[str, Dict[str, Any]] = (self._config.get("npc_boss_overlays.overlays") or {})
        self._rules: Dict[str, Any] = (self._config.get("npc_generation_rules") or {})
        logger.info(
            f"NPCFamilyGenerator initialized. Families loaded: {len(self._families)} Variants loaded: {len(self._variants)} Overlays loaded: {len(self._overlays)}"
        )

    def _load_and_merge_families(self) -> Dict[str, Dict[str, Any]]:
        fams_base = (self._config.get("npc_families.families") or {})
        fams_factions = (self._config.get("npc_families_factions.families") or {})
        merged: Dict[str, Dict[str, Any]] = {}
        # Base first
        for k, v in fams_base.items():
            merged[k] = v
        # Faction overwrites if duplicated keys
        for k, v in fams_factions.items():
            merged[k] = v
        return merged

    def get_family(self, family_id: str) -> Optional[Dict[str, Any]]:
        return self._families.get(family_id)

    def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        return self._variants.get(variant_id)

    def get_overlay(self, overlay_id: str) -> Optional[Dict[str, Any]]:
        return self._overlays.get(overlay_id)

    def _apply_scaling(self, values: Tuple[float, float, float, float], level: int, encounter_size: str = "solo", difficulty: str = "normal") -> Tuple[float, float, float, float]:
        """Apply generation rules scaling (difficulty, level curves, encounter size) to (hp, dmg, def, init)."""
        hp, dmg, df, ini = values
        scaling = self._rules.get("scaling", {}) or {}
        # Difficulty
        dmap = (scaling.get("difficulty", {}) or {})
        dkey = (difficulty or "normal").lower()
        if dmap and dkey not in dmap:
            logger.warning(f"Unknown difficulty '{difficulty}', defaulting to 'normal'")
            dkey = "normal" if "normal" in dmap else next(iter(dmap.keys()), "normal")
        diff = dmap.get(dkey, {})
        hp *= float(diff.get("hp", 1.0) or 1.0)
        dmg *= float(diff.get("damage", 1.0) or 1.0)
        df *= float(diff.get("defense", 1.0) or 1.0)
        ini *= float(diff.get("initiative", 1.0) or 1.0)
        # Encounter size
        emap = (scaling.get("encounter_size", {}) or {})
        ekey = (encounter_size or "solo").lower()
        if emap and ekey not in emap:
            logger.warning(f"Unknown encounter_size '{encounter_size}', defaulting to 'solo'")
            ekey = "solo" if "solo" in emap else next(iter(emap.keys()), "solo")
        enc = emap.get(ekey, {})
        hp *= float(enc.get("hp", 1.0) or 1.0)
        dmg *= float(enc.get("damage", 1.0) or 1.0)
        df *= float(enc.get("defense", 1.0) or 1.0)
        ini *= float(enc.get("initiative", 1.0) or 1.0)
        # Level curve (simple multiplier for now)
        plc = scaling.get("player_level_curve", {}) or {}
        def curve_mul(key: str) -> float:
            seg = plc.get(key, {})
            try:
                return float(seg.get("multiplier", 1.0) or 1.0)
            except Exception:
                return 1.0
        hp *= curve_mul("hp")
        dmg *= curve_mul("damage")
        df *= curve_mul("defense")
        ini *= curve_mul("initiative")
        return hp, dmg, df, ini

    def _pick_within_budget(self, budget: Dict[str, Any]) -> float:
        try:
            vmin = float(budget.get("min", 0))
            vmax = float(budget.get("max", vmin))
        except Exception:
            vmin, vmax = 0.0, 0.0
        if vmax < vmin:
            vmax = vmin
        return random.uniform(vmin, vmax)

    def _mod_to_stat(self, mod: int) -> int:
        """Convert a D&D-like modifier back to a base stat value producing that mod.
        Example: mod=0 -> 10, mod=+2 -> 14, mod=-1 -> 8
        """
        return 10 + 2 * mod

    def _select_role_and_abilities(self, fam: Dict[str, Any], variant: Optional[Dict[str, Any]] = None, overlay: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Select a role from allowed_roles and compile abilities list.
        Phase 1: simple deterministic pick (first allowed role),
        abilities = family.global + role_overrides[role] + variant.abilities_add (if any),
        truncated by rules.max_abilities if present.
        """
        allowed_roles = list(fam.get("allowed_roles", []) or [])
        selected_role = allowed_roles[0] if allowed_roles else None
        pools = fam.get("ability_pools", {}) or {}
        abilities: list[str] = []
        abilities += list(pools.get("global", []) or [])
        if selected_role and isinstance(pools.get("role_overrides"), dict):
            abilities += list(pools.get("role_overrides", {}).get(selected_role, []) or [])
        if variant:
            abilities += list((variant.get("abilities_add") or []))
        if overlay:
            abilities += list((overlay.get("bonus_abilities") or []))
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for a in abilities:
            if a not in seen:
                seen.add(a)
                deduped.append(a)
        # Truncate by max_abilities
        max_abilities = None
        rules = fam.get("rules", {}) or {}
        if isinstance(rules.get("max_abilities"), int):
            max_abilities = int(rules.get("max_abilities"))
        if max_abilities is not None and max_abilities >= 0:
            deduped = deduped[:max_abilities]
        return {"role": selected_role, "abilities": deduped}

    def generate_npc_from_family(
        self,
        family_id: str,
        name: Optional[str] = None,
        location: Optional[str] = None,
        level: int = 1,
        overlay_id: Optional[str] = None,
        difficulty: str = "normal",
        encounter_size: str = "solo",
    ) -> NPC:
        """Generate an NPC with combat-ready stats from a family definition.

        Args:
            family_id: ID of the family (key in families maps)
            name: Optional explicit NPC name; if None uses family name
            location: Optional location string
            level: NPC level (Phase 1 uses level minimally)
        """
        fam = self.get_family(family_id)
        if not fam:
            raise ValueError(f"Family '{family_id}' not found")

        fam_name = fam.get("name", family_id.replace("_", " ").title())
        npc_name = name or fam_name

        # Budgets
        # Enforce overlay allowance
        if overlay_id:
            if not fam.get("is_boss_allowed", True):
                raise ValueError(f"Overlay '{overlay_id}' not allowed: family '{family_id}' disallows bosses")
            allowed = (fam.get("rules", {}) or {}).get("allowed_overlays")
            if isinstance(allowed, list) and allowed and overlay_id not in allowed:
                raise ValueError(f"Overlay '{overlay_id}' not in allowed_overlays for family '{family_id}'")
        budgets = fam.get("stat_budgets", {}) or {}
        target_hp = self._pick_within_budget(budgets.get("hp", {}))
        target_damage = self._pick_within_budget(budgets.get("damage", {}))
        target_defense = self._pick_within_budget(budgets.get("defense", {}))
        target_initiative = self._pick_within_budget(budgets.get("initiative", {}))

        # Apply overlay multipliers if provided
        overlay = None
        if overlay_id:
            overlay = self.get_overlay(overlay_id)
            if overlay:
                mult = overlay.get("multipliers", {}) or {}
                try:
                    target_hp *= float(mult.get("hp", 1.0))
                    target_damage *= float(mult.get("damage", 1.0))
                    target_defense *= float(mult.get("defense", 1.0))
                    target_initiative *= float(mult.get("initiative", 1.0))
                except Exception:
                    pass

        # Apply global scaling from rules (difficulty/encounter/level)
        # For Phase 1, assume difficulty=normal, encounter=solo; level is passed in
        target_hp, target_damage, target_defense, target_initiative = self._apply_scaling(
            (target_hp, target_damage, target_defense, target_initiative), level=level, encounter_size=encounter_size, difficulty=difficulty
        )

        # Map budgets -> primary stats (simple heuristics)
        # Initiative = DEX_mod + floor(WIS_mod/2). Phase 1: set WIS_mod=0, so INIT ~ DEX_mod.
        dex_mod_target = int(round(target_initiative))
        dex_mod_target = max(-2, min(6, dex_mod_target))  # Clamp

        # Defense = base_defense(10) + CON_mod + min(DEX_mod, 5)
        needed_mod_sum = int(round(target_defense)) - 10
        con_mod_target = needed_mod_sum - min(dex_mod_target, 5)
        con_mod_target = max(-2, min(6, con_mod_target))

        # Damage ~ base_dice_avg(≈3 for 1d4) + STR_mod. Use 3 as rough average.
        str_mod_target = int(round(target_damage - 3))
        str_mod_target = max(-2, min(6, str_mod_target))

        # Derive base stat scores from modifiers
        str_score = self._mod_to_stat(str_mod_target)
        dex_score = self._mod_to_stat(dex_mod_target)
        con_score = self._mod_to_stat(con_mod_target)
        int_score = 10
        wis_score = 10  # Keep 0 WIS_mod for Phase 1 simplicity
        cha_score = 10

        # Create StatsManager and apply primary stats
        sm = StatsManager()
        sm.set_level(max(1, int(level)))
        sm.set_base_stat(StatType.STRENGTH, float(str_score))
        sm.set_base_stat(StatType.DEXTERITY, float(dex_score))
        sm.set_base_stat(StatType.CONSTITUTION, float(con_score))
        sm.set_base_stat(StatType.INTELLIGENCE, float(int_score))
        sm.set_base_stat(StatType.WISDOM, float(wis_score))
        sm.set_base_stat(StatType.CHARISMA, float(cha_score))

        # After derived stats computed, adjust current resources
        # Set current HP to min(target_hp, MAX_HEALTH). Keep at least 1.
        try:
            max_hp = sm.get_stat_value(DerivedStatType.MAX_HEALTH)
        except Exception:
            max_hp = 1.0
        desired_hp = max(1.0, min(float(target_hp), float(max_hp)))
        sm.set_current_stat(DerivedStatType.HEALTH, desired_hp)
        # Start stamina/mana at max/zero for Phase 1 simplicity
        try:
            max_stamina = sm.get_stat_value(DerivedStatType.MAX_STAMINA)
            sm.set_current_stat(DerivedStatType.STAMINA, max_stamina)
        except Exception:
            pass
        try:
            max_mana = sm.get_stat_value(DerivedStatType.MAX_MANA)
            sm.set_current_stat(DerivedStatType.MANA, 0.0 if max_mana > 0 else 0.0)
        except Exception:
            pass

        # Build NPC
        npc = NPC(
            name=npc_name,
            npc_type=NPCType.ENEMY,
            relationship=NPCRelationship.HOSTILE,
            location=location,
            description=fam.get("description", f"A {fam_name}"),
            is_persistent=False,
        )
        npc.stats_manager = sm
        npc.stats_generated = True

        # Remember family used
        if npc.known_information is None:
            npc.known_information = {}
        npc.known_information["family_id"] = family_id
        npc.known_information["generator"] = "families_phase1"
        if overlay and overlay.get("is_boss"):
            # Append a boss tag and overlay id
            tags = npc.known_information.get("tags", [])
            if isinstance(tags, list):
                tags = list(tags)
                tags.append("is_boss:true")
                npc.known_information["tags"] = tags
            npc.known_information["boss_overlay_id"] = overlay_id

        # Attach tags from family
        default_tags = fam.get("default_tags", []) or []
        npc.known_information["tags"] = list(default_tags)
        # Attach selected role and abilities (metadata for now)
        ra = self._select_role_and_abilities(fam, overlay=overlay)
        if ra.get("role"):
            npc.known_information["role"] = ra["role"]
        if ra.get("abilities"):
            npc.known_information["abilities"] = ra["abilities"]

        logger.info(
            f"Generated NPC from family='{family_id}' name='{npc.name}' STR={str_score} DEX={dex_score} CON={con_score} "
            f"HP={desired_hp:.0f}/{max_hp:.0f} DEF~{sm.get_stat_value(DerivedStatType.DEFENSE):.0f} INIT~{sm.get_stat_value(DerivedStatType.INITIATIVE):.0f}"
        )
        return npc

    def generate_npc_from_variant(
        self,
        variant_id: str,
        name: Optional[str] = None,
        location: Optional[str] = None,
        level: int = 1,
        overlay_id: Optional[str] = None,
        difficulty: str = "normal",
        encounter_size: str = "solo",
    ) -> NPC:
        """Generate an NPC using a variant layered on top of a family (Phase 1).

        This applies variant stat_modifiers to the family's stat budgets before
        mapping to StatsManager stats. Order of application per stat:
          1) multiply (mul), 2) add (add) if present.
        """
        var = self.get_variant(variant_id)
        if not var:
            raise ValueError(f"Variant '{variant_id}' not found")
        family_id = var.get("family_id")
        fam = self.get_family(family_id)
        if not fam:
            raise ValueError(f"Family '{family_id}' (from variant '{variant_id}') not found")

        fam_name = fam.get("name", family_id.replace("_", " ").title())
        npc_name = name or var.get("name") or fam_name

        # Base budgets from family
        budgets = fam.get("stat_budgets", {}) or {}
        target_hp = self._pick_within_budget(budgets.get("hp", {}))
        target_damage = self._pick_within_budget(budgets.get("damage", {}))
        target_defense = self._pick_within_budget(budgets.get("defense", {}))
        target_initiative = self._pick_within_budget(budgets.get("initiative", {}))

        # Apply variant modifiers
        mods = (var.get("stat_modifiers") or {})

        # Apply overlay multipliers if provided
        overlay = None
        if overlay_id:
            overlay = self.get_overlay(overlay_id)
            if overlay:
                mult = overlay.get("multipliers", {}) or {}
                try:
                    target_hp *= float(mult.get("hp", 1.0))
                    target_damage *= float(mult.get("damage", 1.0))
                    target_defense *= float(mult.get("defense", 1.0))
                    target_initiative *= float(mult.get("initiative", 1.0))
                except Exception:
                    pass

        # Apply global scaling from rules (difficulty/encounter/level)
        target_hp, target_damage, target_defense, target_initiative = self._apply_scaling(
            (target_hp, target_damage, target_defense, target_initiative), level=level, encounter_size=encounter_size, difficulty=difficulty
        )
        def apply_mod(val: float, spec: Optional[Dict[str, Any]]) -> float:
            if not spec:
                return val
            try:
                if "mul" in spec and spec["mul"] is not None:
                    val = float(val) * float(spec["mul"])
                if "add" in spec and spec["add"] is not None:
                    val = float(val) + float(spec["add"])
            except Exception:
                # Ignore malformed modifiers; keep original val
                pass
            return val

        target_hp = apply_mod(target_hp, mods.get("hp"))
        target_damage = apply_mod(target_damage, mods.get("damage"))
        target_defense = apply_mod(target_defense, mods.get("defense"))
        target_initiative = apply_mod(target_initiative, mods.get("initiative"))

        # Map budgets -> primary stats using same heuristics as family-only path
        dex_mod_target = int(round(target_initiative))
        dex_mod_target = max(-2, min(6, dex_mod_target))

        needed_mod_sum = int(round(target_defense)) - 10
        con_mod_target = needed_mod_sum - min(dex_mod_target, 5)
        con_mod_target = max(-2, min(6, con_mod_target))

        str_mod_target = int(round(target_damage - 3))
        str_mod_target = max(-2, min(6, str_mod_target))

        str_score = self._mod_to_stat(str_mod_target)
        dex_score = self._mod_to_stat(dex_mod_target)
        con_score = self._mod_to_stat(con_mod_target)
        int_score = 10
        wis_score = 10
        cha_score = 10

        sm = StatsManager()
        sm.set_level(max(1, int(level)))
        sm.set_base_stat(StatType.STRENGTH, float(str_score))
        sm.set_base_stat(StatType.DEXTERITY, float(dex_score))
        sm.set_base_stat(StatType.CONSTITUTION, float(con_score))
        sm.set_base_stat(StatType.INTELLIGENCE, float(int_score))
        sm.set_base_stat(StatType.WISDOM, float(wis_score))
        sm.set_base_stat(StatType.CHARISMA, float(cha_score))

        try:
            max_hp = sm.get_stat_value(DerivedStatType.MAX_HEALTH)
        except Exception:
            max_hp = 1.0
        desired_hp = max(1.0, min(float(target_hp), float(max_hp)))
        sm.set_current_stat(DerivedStatType.HEALTH, desired_hp)
        try:
            max_stamina = sm.get_stat_value(DerivedStatType.MAX_STAMINA)
            sm.set_current_stat(DerivedStatType.STAMINA, max_stamina)
        except Exception:
            pass
        try:
            max_mana = sm.get_stat_value(DerivedStatType.MAX_MANA)
            sm.set_current_stat(DerivedStatType.MANA, 0.0 if max_mana > 0 else 0.0)
        except Exception:
            pass

        npc = NPC(
            name=npc_name,
            npc_type=NPCType.ENEMY,
            relationship=NPCRelationship.HOSTILE,
            location=location,
            description=var.get("description") or fam.get("description", f"A {fam_name}"),
            is_persistent=False,
        )
        npc.stats_manager = sm
        npc.stats_generated = True

        if npc.known_information is None:
            npc.known_information = {}
        npc.known_information["family_id"] = family_id
        npc.known_information["variant_id"] = variant_id
        npc.known_information["generator"] = "families_phase1"
        if overlay and overlay.get("is_boss"):
            tags = npc.known_information.get("tags", [])
            if isinstance(tags, list):
                tags = list(tags)
                tags.append("is_boss:true")
                npc.known_information["tags"] = tags
            npc.known_information["boss_overlay_id"] = overlay_id

        # Attach tags: family defaults + variant tags_add (if present)
        default_tags = fam.get("default_tags", []) or []
        tags_add = (var.get("tags_add") or [])
        npc.known_information["tags"] = list(default_tags) + list(tags_add)

        # Select role and abilities including variant adds and overlay bonuses
        ra = self._select_role_and_abilities(fam, variant=var, overlay=overlay)
        if ra.get("role"):
            npc.known_information["role"] = ra["role"]
        if ra.get("abilities"):
            npc.known_information["abilities"] = ra["abilities"]
        # Also record roles_add explicitly for traceability
        if var.get("roles_add"):
            npc.known_information["roles_add"] = list(var.get("roles_add") or [])

        logger.info(
            f"Generated NPC from variant='{variant_id}' (family='{family_id}') name='{npc.name}'"
            f" HP={desired_hp:.0f}/{max_hp:.0f} DEF~{sm.get_stat_value(DerivedStatType.DEFENSE):.0f}"
            f" INIT~{sm.get_stat_value(DerivedStatType.INITIATIVE):.0f}"
        )
        return npc

