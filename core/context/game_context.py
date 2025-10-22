#!/usr/bin/env python3
"""
GameContext model and canonicalization for extended location/context management.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.utils.logging_config import get_logger
from core.base.config import get_config

# Defaults (used if config files are missing)
_DEFAULT_ENUMS: Dict[str, Any] = {
    "location": {
        "major": ["city", "forest", "camp", "village", "castle", "dungeon", "seaside", "desert", "mountain", "swamp", "ruins", "port", "temple"],
        "venue": ["tavern", "market", "blacksmith", "inn", "chapel", "library", "manor", "arena", "camp", "fireplace", "bridge", "tower", "cave", "farm"],
    },
    "weather": {"type": ["clear", "overcast", "rain", "storm", "snow", "blizzard", "fog", "windy", "sandstorm"]},
    "time_of_day": ["deep_night", "pre_dawn", "dawn", "morning", "noon", "afternoon", "evening", "sunset", "night"],
    "biome": ["forest", "desert", "swamp", "mountain", "seaside", "plains", "ruins"],
    "crowd_level": ["empty", "sparse", "busy"],
    "danger_level": ["calm", "tense", "deadly"],
    "booleans": ["interior", "underground"],
}

_DEFAULT_SYNONYMS: Dict[str, Any] = {
    "location": {
        "major": {"town": "city", "hamlet": "village", "port town": "port", "camp": "camp", "none": "", "no": "", "n/a": "", "null": ""},
        "venue": {"pub": "tavern", "smith": "blacksmith", "church": "chapel", "marketplace": "market", "none": "", "no": "", "n/a": "", "null": ""},
    },
    "weather": {"type": {"rainy": "rain", "snowing": "snow", "clear skies": "clear"}},
    "time_of_day": {"morning": "day", "afternoon": "day", "evening": "dusk", "nighttime": "night", "midnight": "night", "sunrise": "dawn", "sunset": "dusk"},
    "biome": {"shore": "seaside", "coast": "seaside", "woods": "forest", "jungle": "forest", "none": "", "no": "", "n/a": "", "null": ""},
    "crowd_level": {"crowded": "busy", "packed": "busy", "empty streets": "empty"},
    "danger_level": {"safe": "calm", "high": "deadly", "dangerous": "tense"},
}


def _project_root() -> Path:
    # core/context/game_context.py -> project root is parents[2]
    return Path(__file__).resolve().parents[2]


def _load_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def load_context_enums() -> Dict[str, Any]:
    cfg_path = _project_root() / "config" / "audio" / "context_enums.json"
    return _load_json(cfg_path) or _DEFAULT_ENUMS


def load_context_synonyms() -> Dict[str, Any]:
    syn_path = _project_root() / "config" / "audio" / "context_synonyms.json"
    return _load_json(syn_path) or _DEFAULT_SYNONYMS


def _load_locations_catalog() -> Optional[Dict[str, Any]]:
    try:
        p = _project_root() / "config" / "world" / "locations" / "locations.json"
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None


def _derive_major_from_type(name: str, typ: Optional[str]) -> Optional[str]:
    s = (typ or '').strip().lower()
    name_lc = (name or '').strip().lower()
    if s == 'city':
        return 'city'
    if s == 'forest':
        return 'forest'
    if s == 'harbor':
        return 'port'
    if s == 'settlement':
        # Heuristic: if name suggests a camp, prefer camp; else village
        return 'camp' if 'camp' in name_lc else 'village'
    if s == 'outpost':
        return 'camp'
    if s in ('dungeon','cave','cavern'):
        return 'dungeon'
    if s in ('temple','chapel'):
        return 'temple'
    if s in ('ruins','anomaly'):
        return 'ruins'
    # Unknown or venue-like types -> leave None so venue can carry meaning
    return None


def _derive_biome_from_type(typ: Optional[str]) -> Optional[str]:
    s = (typ or '').strip().lower()
    if s == 'forest':
        return 'forest'
    if s == 'harbor':
        return 'seaside'
    # Leave others None unless explicit
    return None


def _build_automap_from_locations() -> Dict[str, Any]:
    """Build a mapping from the locations catalog, used to auto-augment context mapping at runtime.
    Non-overwriting fields supported (if present in catalog):
    - major, venue, biome, region
    - weather.type, interior, underground, crowd_level, danger_level
    Note: time_of_day intentionally NOT provided by automap; it's sourced from origins/GameContext.
    """
    automap = { 'by_id': {}, 'by_name': {} }
    cat = _load_locations_catalog() or {}
    locs = (cat.get('locations') or {}) if isinstance(cat, dict) else {}
    for _id, entry in locs.items():
        try:
            name = str(entry.get('name', '')).strip()
            typ = entry.get('type')
            region = entry.get('region')
            major = _derive_major_from_type(name, typ)
            venue = None
            # Treat certain types as venues when major doesn't fit whitelist
            if (typ or '').strip().lower() in ('library','market'):
                venue = (typ or '').strip().lower()
            biome = _derive_biome_from_type(typ)

            # Optional extended fields (pass-through if present in catalog)
            interior = entry.get('interior') if isinstance(entry, dict) else None
            underground = entry.get('underground') if isinstance(entry, dict) else None
            crowd_level = entry.get('crowd_level') if isinstance(entry, dict) else None
            danger_level = entry.get('danger_level') if isinstance(entry, dict) else None
            # Weather may be nested or flat in future catalogs
            weather_type = None
            try:
                if isinstance(entry.get('weather'), dict):
                    weather_type = entry.get('weather', {}).get('type')
                if weather_type is None and entry.get('weather_type') is not None:
                    weather_type = entry.get('weather_type')
            except Exception:
                weather_type = None

            payload = {
                'major': major,
                'venue': venue,
                'biome': biome,
                'region': region,
            }
            # Only include extended keys if present (non-None)
            if weather_type is not None:
                payload['weather'] = { 'type': str(weather_type).strip().lower() } if str(weather_type).strip() else None
            if interior is not None:
                payload['interior'] = bool(interior)
            if underground is not None:
                payload['underground'] = bool(underground)
            if crowd_level is not None:
                s = str(crowd_level).strip().lower()
                payload['crowd_level'] = s if s else None
            if danger_level is not None:
                s = str(danger_level).strip().lower()
                payload['danger_level'] = s if s else None

            # Drop keys with None to keep output compact
            payload = {k:v for k,v in payload.items() if v is not None}
            if not payload:
                continue
            if _id:
                automap['by_id'][_id] = payload
            if name:
                automap['by_name'][name] = payload
        except Exception:
            continue
    return automap


def _merge_context_maps(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    """Merge secondary into primary without overwriting existing non-empty fields."""
    out = { 'by_id': {}, 'by_name': {} }
    for key in ('by_id','by_name'):
        base = primary.get(key) or {}
        add  = secondary.get(key) or {}
        merged = {}
        # Start with base
        for k, v in base.items():
            merged[k] = dict(v) if isinstance(v, dict) else v
        # Add from secondary if missing or to fill missing fields
        for k, v in add.items():
            if k not in merged:
                merged[k] = dict(v) if isinstance(v, dict) else v
            else:
                # Fill missing fields only
                if isinstance(merged[k], dict) and isinstance(v, dict):
                    for f, fv in v.items():
                        if fv is not None and (merged[k].get(f) is None):
                            merged[k][f] = fv
        out[key] = merged
    return out


def load_location_context_map() -> Dict[str, Any]:
    p = _project_root() / "config" / "audio" / "context_location_map.json"
    data = _load_json(p) or {}
    data = data if isinstance(data, dict) else {}
    try:
        auto_map = _build_automap_from_locations()
        merged = _merge_context_maps(data, auto_map)
        # Dev log for visibility
        get_logger('GAME').info(
            "LOCATION_MGMT: mapping loaded explicit_ids=%s auto_ids=%s merged_ids=%s",
            len((data.get('by_id') or {})), len((auto_map.get('by_id') or {})), len((merged.get('by_id') or {}))
        )
        return merged
    except Exception:
        return data


@dataclass
class GameContext:
    location_name: str = ""
    location_major: Optional[str] = None
    location_venue: Optional[str] = None
    weather_type: Optional[str] = None
    time_of_day: Optional[str] = None
    biome: Optional[str] = None
    region: Optional[str] = None
    interior: Optional[bool] = None
    underground: Optional[bool] = None
    crowd_level: Optional[str] = None
    danger_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # Nested shape for API/UI
        d = asdict(self)
        return {
            "location": {
                "name": d.pop("location_name", ""),
                "major": d.pop("location_major", None),
                "venue": d.pop("location_venue", None),
            },
            "weather": {
                "type": d.pop("weather_type", None),
            },
            **d,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameContext":
        loc = data.get("location", {}) or {}
        w = data.get("weather", {}) or {}
        kwargs = {
            "location_name": loc.get("name", ""),
            "location_major": loc.get("major"),
            "location_venue": loc.get("venue"),
            "weather_type": w.get("type"),
            "time_of_day": data.get("time_of_day"),
            "biome": data.get("biome"),
            "region": data.get("region"),
            "interior": data.get("interior"),
            "underground": data.get("underground"),
            "crowd_level": data.get("crowd_level"),
            "danger_level": data.get("danger_level"),
        }
        return cls(**kwargs)


def _canon_str(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    try:
        return str(val).strip().lower() or None
    except Exception:
        return None


def canonicalize_context(input_data: Dict[str, Any]) -> Tuple[GameContext, Dict[str, str]]:
    enums = load_context_enums()
    syn = load_context_synonyms()
    warnings: Dict[str, str] = {}

    # Flatten input
    loc_in = input_data.get("location", {}) or {}
    w_in = input_data.get("weather", {}) or {}

    location_name = input_data.get("location_name") or loc_in.get("name") or ""

    def canon_enum(domain: str, key: str, raw: Optional[str]) -> Optional[str]:
        s = _canon_str(raw)
        if not s:
            return None
        # synonyms
        try:
            s = syn.get(domain, {}).get(key, {}).get(s, s)
        except Exception:
            pass
        # Treat explicit empty-string mapping as None (no warning)
        if s == "":
            return None
        # whitelist
        allowed = []
        try:
            if domain == "weather" and key == "type":
                allowed = enums.get("weather", {}).get("type", [])
            elif domain == "location":
                allowed = enums.get("location", {}).get(key, [])
            else:
                allowed = enums.get(key, [])
        except Exception:
            allowed = []
        if allowed and s not in allowed:
            warnings[f"{domain}.{key}"] = f"Unrecognized '{s}', set to None"
            return None
        return s

    def canon_simple(key: str, raw: Optional[str]) -> Optional[str]:
        s = _canon_str(raw)
        if not s:
            return None
        # synonyms (top-level like time_of_day, biome, crowd_level, danger_level)
        mapped = syn.get(key, {}).get(s, s) if isinstance(syn.get(key, {}), dict) else s
        # Treat explicit empty-string mapping as None (no warning)
        if mapped == "":
            return None
        allowed = enums.get(key, []) if isinstance(enums.get(key, []), list) else []
        if allowed and mapped not in allowed:
            warnings[key] = f"Unrecognized '{mapped}', set to None"
            return None
        return mapped

    gc = GameContext(
        location_name=str(location_name),
        location_major=canon_enum("location", "major", input_data.get("location_major") or loc_in.get("major")),
        location_venue=canon_enum("location", "venue", input_data.get("location_venue") or loc_in.get("venue")),
        weather_type=canon_enum("weather", "type", input_data.get("weather_type") or w_in.get("type")),
        time_of_day=canon_simple("time_of_day", input_data.get("time_of_day")),
        biome=canon_simple("biome", input_data.get("biome")),
        region=_canon_str(input_data.get("region")) or None,
        interior=bool(input_data.get("interior")) if input_data.get("interior") is not None else None,
        underground=bool(input_data.get("underground")) if input_data.get("underground") is not None else None,
        crowd_level=canon_simple("crowd_level", input_data.get("crowd_level")),
        danger_level=canon_simple("danger_level", input_data.get("danger_level")),
    )
    return gc, warnings


def enrich_context_from_location(ctx: GameContext, location_name: Optional[str] = None, location_id: Optional[str] = None) -> GameContext:
    """Enrich GameContext with mapping-derived fields if available.
    Non-overwriting fill for: major, venue, biome, region, weather.type, interior, underground, crowd_level, danger_level.
    Note: time_of_day remains sourced from origins/GameContext, not the map.
    """
    logger = get_logger("GAME")
    try:
        m = load_location_context_map()
        entry = None
        if location_id and isinstance(m.get('by_id'), dict):
            entry = m['by_id'].get(location_id)
        if not entry and location_name and isinstance(m.get('by_name'), dict):
            entry = m['by_name'].get(location_name)
        if not entry:
            logger.info("LOCATION_MGMT: mapping not found for location id=%s name=%s", location_id, location_name)
            return ctx
        # Apply non-None fields only if ctx fields are empty
        if entry.get('major') and not ctx.location_major:
            ctx.location_major = str(entry['major']).strip().lower()
        if entry.get('venue') and not ctx.location_venue:
            ctx.location_venue = str(entry['venue']).strip().lower()
        if entry.get('biome') and not ctx.biome:
            ctx.biome = str(entry['biome']).strip().lower()
        if entry.get('region') and not ctx.region:
            ctx.region = str(entry['region']).strip()
        # Extended fields
        try:
            # weather.type (support nested or flat key)
            weather_obj = entry.get('weather') if isinstance(entry, dict) else None
            weather_type = None
            if isinstance(weather_obj, dict):
                weather_type = weather_obj.get('type')
            if weather_type is None:
                weather_type = entry.get('weather_type') if isinstance(entry, dict) else None
            if weather_type and not ctx.weather_type:
                ctx.weather_type = str(weather_type).strip().lower()
            # interior / underground
            if (entry.get('interior') is not None) and (ctx.interior is None):
                try:
                    ctx.interior = bool(entry.get('interior'))
                except Exception:
                    pass
            if (entry.get('underground') is not None) and (ctx.underground is None):
                try:
                    ctx.underground = bool(entry.get('underground'))
                except Exception:
                    pass
            # crowd_level / danger_level
            cl = entry.get('crowd_level') if isinstance(entry, dict) else None
            if cl and not ctx.crowd_level:
                ctx.crowd_level = str(cl).strip().lower()
            dl = entry.get('danger_level') if isinstance(entry, dict) else None
            if dl and not ctx.danger_level:
                ctx.danger_level = str(dl).strip().lower()
        except Exception:
            pass
        logger.info(
            "LOCATION_MGMT: enriched mapping id=%s name=%s => major=%s venue=%s biome=%s region=%s weather=%s interior=%s underground=%s crowd=%s danger=%s",
            location_id, location_name, ctx.location_major, ctx.location_venue, ctx.biome, ctx.region,
            ctx.weather_type, ctx.interior, ctx.underground, ctx.crowd_level, ctx.danger_level
        )
    except Exception as e:
        logger.warning("LOCATION_MGMT: enrich_context_from_location failed: %s", e)
    return ctx
