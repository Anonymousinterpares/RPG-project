#!/usr/bin/env python3
"""
Spell catalog loader and accessors (Phase 3, additive).

- Loads authored magic systems and spells via GameConfig (domain: magic_systems)
- Exposes simple getters and in-memory cache
- Supports spells that already include effect_atoms; optional best-effort mapping from legacy 'effects' is left for a future pass
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from difflib import get_close_matches

from core.base.config import get_config
from core.utils.logging_config import get_logger

logger = get_logger("SPELLS")


@dataclass
class Spell:
    id: str
    name: str
    system_id: str
    data: Dict[str, Any]

    @property
    def combat_role(self) -> str:
        try:
            role = str(self.data.get("combat_role", "offensive")).strip().lower()
            if role in ("offensive", "defensive", "utility"):
                return role
        except Exception:
            pass
        return "offensive"

    @property
    def effect_atoms(self) -> List[Dict[str, Any]]:
        atoms = self.data.get("effect_atoms")
        if isinstance(atoms, list):
            # Assume valid atoms; schema validation happens at authoring time
            return atoms
        # Legacy: some spells might use 'effects' with effect_type; skip mapping here for safety
        return []


class SpellCatalog:
    def __init__(self, systems: List[Dict[str, Any]]):
        self._systems = systems
        self._spells_by_id: Dict[str, Spell] = {}
        self._index()

    def _iter_scope_ids(self, scope_ids: Optional[List[str]], allow_broad_scope: bool) -> List[str]:
        if scope_ids and not allow_broad_scope:
            return [sid for sid in scope_ids if sid in self._spells_by_id]
        # Broad scope: all known catalog ids
        return list(self._spells_by_id.keys())

    def resolve_spell_id(self, query: str, scope_ids: Optional[List[str]] = None, allow_broad_scope: bool = False) -> Optional[str]:
        """Resolve a spell id from a user query by id or name with fuzzy matching.
        - scope_ids limits candidates (e.g., player.known_spells). When allow_broad_scope is True, falls back to all catalog spells.
        - returns canonical spell id or None if not resolved.
        """
        try:
            if not isinstance(query, str) or not query.strip():
                return None
            q = query.strip().lower()
            candidates = self._iter_scope_ids(scope_ids, allow_broad_scope)
            if not candidates:
                return None
            # Exact id (case-insensitive)
            for sid in candidates:
                if sid.lower() == q:
                    return sid
            # Exact name (case-insensitive)
            for sid in candidates:
                sp = self._spells_by_id.get(sid)
                if sp and sp.name and sp.name.strip().lower() == q:
                    return sid
            # Fuzzy match among ids and names
            keys: List[Tuple[str, str]] = []  # (display_key, spell_id)
            for sid in candidates:
                sp = self._spells_by_id.get(sid)
                if not sp:
                    continue
                keys.append((sid.lower(), sid))
                if sp.name:
                    keys.append((sp.name.strip().lower(), sid))
            key_strings = [k for (k, _) in keys]
            close = get_close_matches(q, key_strings, n=1, cutoff=0.7)
            if close:
                picked = close[0]
                for k, sid in keys:
                    if k == picked:
                        return sid
        except Exception as e:
            logger.warning(f"resolve_spell_id error for '{query}': {e}")
        return None

    def resolve_spell_from_text(self, text: str, scope_ids: Optional[List[str]] = None, allow_broad_scope: bool = False) -> Optional[str]:
        """Resolve a spell id by scanning free-form text for known spell names/ids.
        Prefers exact substring matches (case-insensitive) within the provided scope; can fall back to the entire catalog if allow_broad_scope is True.
        Returns the canonical spell id on success or None.
        """
        try:
            if not isinstance(text, str) or not text.strip():
                return None
            t = text.lower()
            candidates = self._iter_scope_ids(scope_ids, allow_broad_scope)
            if not candidates:
                return None
            best_sid = None
            best_len = 0
            for sid in candidates:
                sp = self._spells_by_id.get(sid)
                if not sp:
                    continue
                # Check id substring
                sid_l = sid.lower()
                if sid_l in t and len(sid_l) > best_len:
                    best_sid = sid
                    best_len = len(sid_l)
                # Check name substring
                name_l = (sp.name or '').strip().lower()
                if name_l and name_l in t and len(name_l) > best_len:
                    best_sid = sid
                    best_len = len(name_l)
            return best_sid
        except Exception as e:
            logger.warning(f"resolve_spell_from_text error: {e}")
            return None

    def _index(self) -> None:
        try:
            iterable = []
            if isinstance(self._systems, list):
                iterable = self._systems
            elif isinstance(self._systems, dict):
                iterable = list(self._systems.values())
            for sys_entry in (iterable or []):
                if not isinstance(sys_entry, dict):
                    continue
                system_id = str(sys_entry.get("id") or "").strip()
                spells = sys_entry.get("spells") or []
                # Support both list or dict for spells
                if isinstance(spells, dict):
                    spells = list(spells.values())
                if not system_id or not isinstance(spells, list):
                    continue
                for sp in spells:
                    try:
                        sid = str(sp.get("id") or "").strip()
                        name = str(sp.get("name") or sid)
                        if not sid:
                            continue
                        self._spells_by_id[sid] = Spell(id=sid, name=name, system_id=system_id, data=sp)
                    except Exception as e:
                        logger.warning(f"Skipping malformed spell in system {system_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to index spells: {e}")

    def get_spell_by_id(self, spell_id: str) -> Optional[Spell]:
        return self._spells_by_id.get(str(spell_id).strip())

    def list_known_spells(self) -> List[str]:
        return sorted(self._spells_by_id.keys())


# Singleton access
_catalog: Optional[SpellCatalog] = None


def get_spell_catalog(force_reload: bool = False) -> SpellCatalog:
    global _catalog
    if _catalog is not None and not force_reload:
        return _catalog
    try:
        cfg = get_config()
        systems = cfg.get("magic_systems")
        if isinstance(systems, dict) and "magic_systems" in systems:
            # Some files are wrapped; accept top-level key as well
            systems = systems["magic_systems"]
        # Normalize to a list of system dicts
        if systems is None:
            systems_list: List[Dict[str, Any]] = []
        elif isinstance(systems, list):
            systems_list = systems  # already list of system entries
        elif isinstance(systems, dict):
            # Convert mapping (id -> system_dict) to a list of dicts
            try:
                systems_list = list(systems.values())
            except Exception:
                systems_list = []
        else:
            systems_list = []
        _catalog = SpellCatalog(systems=systems_list)
        logger.info(f"SpellCatalog loaded with {len(_catalog.list_known_spells())} spells")
    except Exception as e:
        logger.error(f"Failed to load SpellCatalog: {e}")
        _catalog = SpellCatalog(systems=[])
    return _catalog
