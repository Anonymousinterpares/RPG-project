#!/usr/bin/env python3
"""
ReferenceResolver: resolves narrative labels to canonical references (template_id, ids) using
config-defined aliases. This is a lightweight Phase 1 resolver; LLM-assisted mapping can be
added later behind this interface.
"""
from __future__ import annotations
from typing import Dict, List, Optional

from core.base.config import GameConfig
from core.utils.logging_config import get_logger

logger = get_logger("REF_RESOLVER")

class ReferenceResolver:
    """Resolves labels to canonical IDs based on config aliases.

    Aliases config shape suggestion (config/world/aliases.json):
    {
      "entities": { "white_wolf": ["wolf_alpha", "test_wolf_alpha"] },
      "items": { "healing_herb": ["herb_healing"] },
      "locations": { "ruins": ["ancient_ruins"] },
      "dialogues": { },
      "interactions": { }
    }
    Values can be a string or list of strings (candidate canonical IDs).
    """

    def __init__(self) -> None:
        self._config = GameConfig()

    def _get_domain_aliases(self, domain: str) -> Dict[str, List[str]]:
        try:
            # Primary global aliases
            data = self._config.get("aliases", {})
            dom = data.get(domain, {}) if isinstance(data, dict) else {}
            # Optional NPC entity-specific aliases (config/aliases/entities.json)
            if domain == "entities":
                npc_aliases = self._config.get("npc_entity_aliases.entities", {}) or {}
                # Merge npc_entity_aliases into dom (prefer explicitly provided lists)
                if isinstance(npc_aliases, dict):
                    for k, v in npc_aliases.items():
                        key = str(k).lower()
                        if key not in dom:
                            dom[key] = v
                        else:
                            # Merge lists if both exist
                            try:
                                existing = dom.get(key, [])
                                if isinstance(existing, list) and isinstance(v, list):
                                    dom[key] = list({*map(str, existing), *map(str, v)})
                            except Exception:
                                pass
            # Normalize to list[str]
            out: Dict[str, List[str]] = {}
            for k, v in (dom or {}).items():
                if isinstance(v, list):
                    out[str(k).lower()] = [str(x) for x in v]
                elif isinstance(v, str):
                    out[str(k).lower()] = [v]
            return out
        except Exception:
            return {}

    def resolve(self, domain: str, label: str) -> List[str]:
        """Return candidate canonical IDs for label within domain.
        If no mapping found, return [label] as identity fallback.
        """
        if not label:
            return []
        key = str(label).lower()
        dom_aliases = self._get_domain_aliases(domain)
        mapped = dom_aliases.get(key)
        if mapped:
            return mapped
        return [label]


_resolver_instance: Optional[ReferenceResolver] = None

def get_reference_resolver() -> ReferenceResolver:
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = ReferenceResolver()
    return _resolver_instance
