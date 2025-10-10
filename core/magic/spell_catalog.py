#!/usr/bin/env python3
"""
Spell catalog loader and accessors (Phase 3, additive).

- Loads authored magic systems and spells via GameConfig (domain: magic_systems)
- Exposes simple getters and in-memory cache
- Supports spells that already include effect_atoms; optional best-effort mapping from legacy 'effects' is left for a future pass
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
