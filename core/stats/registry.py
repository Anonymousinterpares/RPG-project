#!/usr/bin/env python3
"""
Unified stat registry access and alias resolution.

- Loads config/character/stat_registry.json via GameConfig (get_config()).
- Builds alias mappings for both primary (StatType) and derived (DerivedStatType) stats.
- Exposes helpers to normalize stat identifiers and resolve to Enums.

IMPORTANT:
- This module must not import StatsManager to avoid circular dependencies.
- Only import enums from core.stats.stats_base and get_config from core.base.config.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple, Union, List

from core.base.config import get_config
from core.utils.logging_config import get_logger
from core.stats.stats_base import StatType, DerivedStatType

logger = get_logger("STATS")

# Internal caches (populated on first use)
_ALIAS_TO_CANONICAL: Optional[Dict[str, str]] = None  # alias -> canonical enum name (e.g., 'armor' -> 'DEFENSE')
_CANONICAL_TO_ENUM: Optional[Dict[str, Union[StatType, DerivedStatType]]] = None  # 'STRENGTH' -> StatType.STRENGTH
_SUPPORTED_FLAGS: Optional[Dict[str, bool]] = None  # canonical enum name -> supported flag


def _load_registry_raw() -> List[dict]:
    """Load the raw list of stat entries from config (unified list)."""
    try:
        cfg = get_config()
        stats = cfg.get("stat_registry.stats", [])
        if not isinstance(stats, list):
            return []
        return stats
    except Exception as e:
        logger.warning(f"Failed to load stat_registry.stats from config: {e}")
        return []


def _build_caches_if_needed() -> None:
    global _ALIAS_TO_CANONICAL, _CANONICAL_TO_ENUM, _SUPPORTED_FLAGS
    if _ALIAS_TO_CANONICAL is not None and _CANONICAL_TO_ENUM is not None and _SUPPORTED_FLAGS is not None:
        return

    alias_to_canonical: Dict[str, str] = {}
    canonical_to_enum: Dict[str, Union[StatType, DerivedStatType]] = {}
    supported_flags: Dict[str, bool] = {}

    raw = _load_registry_raw()
    for entry in raw:
        try:
            key = str(entry.get("key", "")).strip().lower()
            category = str(entry.get("category", "")).strip().lower()
            supported = bool(entry.get("supported", False))
            aliases = entry.get("aliases", []) or []
            if not key or category not in ("primary", "derived"):
                continue

            # Determine canonical enum name (UPPERCASE, matching StatType/DerivedStatType members)
            canonical_enum_name = key.upper()
            enum_val: Optional[Union[StatType, DerivedStatType]] = None
            try:
                if category == "primary":
                    enum_val = StatType[canonical_enum_name]
                else:
                    enum_val = DerivedStatType[canonical_enum_name]
            except KeyError:
                # If not found in enums and not supported, keep as unsupported only
                enum_val = None

            # Record supported flags only for canonical keys
            supported_flags[canonical_enum_name] = supported and (enum_val is not None)

            # Only map to enum if it exists
            if enum_val is not None:
                canonical_to_enum[canonical_enum_name] = enum_val

            # Map key itself and its aliases to canonical
            for al in [key] + [str(a or "").strip().lower() for a in aliases if isinstance(a, str)]:
                if not al:
                    continue
                alias_to_canonical[al] = canonical_enum_name
        except Exception as e:
            logger.warning(f"Error processing stat registry entry {entry}: {e}")
            continue

    _ALIAS_TO_CANONICAL = alias_to_canonical
    _CANONICAL_TO_ENUM = canonical_to_enum
    _SUPPORTED_FLAGS = supported_flags


def normalize_to_canonical_id(name: str) -> Optional[str]:
    """Return canonical enum name (e.g., 'DEFENSE') for a given alias/id string, if known."""
    if not isinstance(name, str):
        return None
    _build_caches_if_needed()
    assert _ALIAS_TO_CANONICAL is not None
    key = name.strip().lower().replace(" ", "_")
    return _ALIAS_TO_CANONICAL.get(key)


def resolve_stat_enum(name: str) -> Optional[Union[StatType, DerivedStatType]]:
    """Resolve a string (alias or canonical) to a StatType/DerivedStatType enum, or None if unknown/unsupported."""
    canonical = normalize_to_canonical_id(name)
    if not canonical:
        # Try direct enum names for backward compat (e.g., 'STRENGTH', 'MELEE_ATTACK')
        try:
            return StatType[name.upper()]
        except Exception:
            try:
                return DerivedStatType[name.upper()]
            except Exception:
                return None

    _build_caches_if_needed()
    assert _CANONICAL_TO_ENUM is not None
    enum_val = _CANONICAL_TO_ENUM.get(canonical)
    if enum_val is None:
        # Known alias mapped to a canonical key that is not an engine enum (unsupported)
        return None
    return enum_val


def is_supported(name: str) -> bool:
    """Return True if the provided alias/canonical refers to a supported engine-recognized stat."""
    canonical = normalize_to_canonical_id(name)
    if not canonical:
        # Attempt direct enum name
        try:
            _ = StatType[name.upper()]
            return True
        except Exception:
            try:
                _ = DerivedStatType[name.upper()]
                return True
            except Exception:
                return False
    _build_caches_if_needed()
    assert _SUPPORTED_FLAGS is not None
    return bool(_SUPPORTED_FLAGS.get(canonical, False))


def all_canonical_ids(include_unsupported: bool = False) -> List[str]:
    """Return a list of canonical enum names known to the registry."""
    _build_caches_if_needed()
    assert _SUPPORTED_FLAGS is not None
    if include_unsupported:
        return list(_SUPPORTED_FLAGS.keys())
    return [k for k, v in _SUPPORTED_FLAGS.items() if v]
