"""
Assistant context dataclasses and provider protocol.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

JsonObj = Dict[str, Any]

@dataclass
class AssistantContext:
    """Serializable context for the LLM assistant.

    domain: logical domain (e.g., "classes", "origins").
    selection_id: stable identifier for the selected entry.
    content: the current JSON for the selected entry.
    schema: optional JSON schema-like hints.
    allowed_paths: JSON Pointer prefixes that the LLM is allowed to modify.
    exemplars: optional example objects for create-entry tasks.
    references: optional catalogs (skills/items/quests/etc.) to reduce hallucinations.
    """
    domain: str
    selection_id: Optional[str]
    content: Optional[JsonObj]
    schema: Optional[JsonObj]
    allowed_paths: List[str]
    exemplars: Optional[List[JsonObj]] = None
    references: Optional[JsonObj] = None


@dataclass
class PatchOp:
    op: str
    path: str
    value: Any = None
    from_: Optional[str] = None  # reserved for move/copy if needed later


class AssistantContextProvider(Protocol):
    """Interface editors implement to integrate with the assistant."""
    def get_assistant_context(self) -> AssistantContext: ...
    def apply_assistant_patch(self, patch_ops: List[PatchOp]) -> Tuple[bool, str]: ...
    def get_domain_examples(self) -> List[JsonObj]: ...
    def get_reference_catalogs(self) -> JsonObj: ...
    def create_entry_from_llm(self, entry: JsonObj) -> Tuple[bool, str, Optional[str]]: ...

