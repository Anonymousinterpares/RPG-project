"""
Provider registry that reads providers and models from the project's config.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from utils.file_manager import get_config_dir

class ProviderRegistry:
    def __init__(self) -> None:
        self.providers: Dict[str, dict] = {}

    def load(self) -> None:
        cfg = Path(get_config_dir())
        prov_path = cfg / "llm" / "providers.json"
        if prov_path.exists():
            self.providers = json.loads(prov_path.read_text(encoding="utf-8"))

    def list_providers(self) -> List[str]:
        return [k for k, v in self.providers.items() if v.get("enabled", True)]

    def provider_info(self, provider: str) -> Optional[dict]:
        return self.providers.get(provider)

    def list_models_for(self, provider: str) -> List[dict]:
        # Source models strictly from providers.json as requested.
        prov = self.providers.get(provider, {})
        ids = prov.get("available_models", [])
        return [{"id": mid, "name": mid, "description": ""} for mid in ids]

