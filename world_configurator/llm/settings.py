"""
LLM settings persistence using QStandardPaths.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtCore import QStandardPaths


@dataclass
class LLMSettings:
    provider: str = ""
    model: str = ""
    api_key: str = ""
    api_base: Optional[str] = None
    provider_keys: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LLMSettings":
        # Backward compatibility: if provider_keys absent, seed with api_key
        provider = d.get("provider", "")
        provider_keys = d.get("provider_keys") or {}
        if not provider_keys and d.get("api_key") and provider:
            provider_keys = {provider: d.get("api_key")}
        return cls(
            provider=provider,
            model=d.get("model", ""),
            api_key=d.get("api_key", ""),
            api_base=d.get("api_base"),
            provider_keys=provider_keys,
        )


def _settings_dir() -> Path:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    base.mkdir(parents=True, exist_ok=True)
    return base


def settings_path() -> Path:
    return _settings_dir() / "llm_settings.json"


def save_llm_settings(settings: LLMSettings) -> None:
    p = settings_path()
    p.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")


def load_llm_settings() -> LLMSettings:
    p = settings_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return LLMSettings.from_dict(data)
        except Exception:
            pass
    return LLMSettings()

