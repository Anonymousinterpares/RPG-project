"""
JSON Patch helpers with allowed-path validation.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Tuple
from copy import deepcopy

from .context import AssistantContext, PatchOp

JsonObj = Dict[str, Any]


def _split_pointer(path: str) -> List[str]:
    if not path or path == "/":
        return []
    assert path.startswith("/")
    parts = path.split("/")[1:]
    # unescape ~1 and ~0 per RFC6901
    return [p.replace("~1", "/").replace("~0", "~") for p in parts]


def _get_parent_and_key(doc: Any, path: str) -> Tuple[Any, str]:
    parts = _split_pointer(path)
    if not parts:
        return None, ""  # root
    parent = doc
    for key in parts[:-1]:
        if isinstance(parent, list):
            idx = int(key)
            parent = parent[idx]
        else:
            parent = parent.setdefault(key, {})
    return parent, parts[-1]


def _set_pointer(doc: Any, path: str, value: Any, create: bool = False) -> None:
    parent, key = _get_parent_and_key(doc, path)
    if parent is None:
        raise ValueError("Cannot set the document root directly")
    if isinstance(parent, list):
        if key == "-":
            parent.append(value)
        else:
            idx = int(key)
            if create and idx == len(parent):
                parent.append(value)
            else:
                parent[idx] = value
    else:
        if not create and key not in parent:
            # For replace when key is missing
            pass
        parent[key] = value


def _remove_pointer(doc: Any, path: str) -> None:
    parent, key = _get_parent_and_key(doc, path)
    if parent is None:
        raise ValueError("Cannot remove the document root")
    if isinstance(parent, list):
        idx = int(key)
        parent.pop(idx)
    else:
        parent.pop(key, None)


def is_allowed_path(path: str, allowed: List[str]) -> bool:
    return any(path == a or path.startswith(a + "/") for a in allowed)


def apply_patch_with_validation(ctx: AssistantContext, content: JsonObj, patch_ops: List[PatchOp]) -> Tuple[bool, str, JsonObj]:
    # Validate ops
    for op in patch_ops:
        if op.op not in ("add", "replace", "remove"):
            return False, f"Unsupported op: {op.op}", content
        if not is_allowed_path(op.path, ctx.allowed_paths):
            return False, f"Disallowed path: {op.path}", content

    candidate = deepcopy(content)
    try:
        for op in patch_ops:
            if op.op in ("add", "replace"):
                _set_pointer(candidate, op.path, op.value, create=(op.op == "add"))
            elif op.op == "remove":
                _remove_pointer(candidate, op.path)
        return True, "OK", candidate
    except Exception as e:
        return False, f"Patch error: {e}", content


def _resolve_pointer(doc: Any, path: str) -> Tuple[bool, Any]:
    if path == "/" or path == "":
        return True, doc
    try:
        parent = doc
        for key in _split_pointer(path):
            if isinstance(parent, list):
                idx = int(key)
                parent = parent[idx]
            else:
                if key not in parent:
                    return False, None
                parent = parent[key]
        return True, parent
    except Exception:
        return False, None


def compute_allowed_path_replacements(old: JsonObj, new: JsonObj, allowed_paths: List[str]) -> List[PatchOp]:
    """Compute a minimal set of replace/add/remove ops by comparing allowed path roots.
    For each allowed path prefix, if the subtree differs, emit a single op:
    - add if missing in old and present in new
    - remove if present in old and missing in new
    - replace if both present and differ
    """
    ops: List[PatchOp] = []
    for p in allowed_paths:
        old_exists, old_val = _resolve_pointer(old, p)
        new_exists, new_val = _resolve_pointer(new, p)
        if not old_exists and new_exists:
            ops.append(PatchOp(op="add", path=p, value=new_val))
        elif old_exists and not new_exists:
            ops.append(PatchOp(op="remove", path=p))
        elif old_exists and new_exists:
            if old_val != new_val:
                ops.append(PatchOp(op="replace", path=p, value=new_val))
        # if neither exists, nothing to do
    return ops

