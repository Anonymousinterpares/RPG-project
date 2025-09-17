"""
Prompt builders for different assistant modes and domains.
"""
from __future__ import annotations

import json
from typing import List

from .context import AssistantContext

ANALYZE_CONTRACT = (
    "Return JSON with keys: intent='analyze', analysis (string), recommendations (list of strings),"
    " optional suggested_patch (list of RFC6902 ops)."
)

MODIFY_CONTRACT = (
    "Return JSON with keys: intent='modify_selection', rationale (string), patch (list of RFC6902 ops)."
    " Allowed ops: add, replace, remove only."
    " Do not return a full replacement object; only patch the requested sections."
)

CREATE_CONTRACT = (
    "Return JSON with keys: intent='create_entry', entity_type (string), rationale (string), entry (object)."
    " The entry must conform to the domain structure and avoid placeholders."
    " The new entry's name MUST NOT exactly match any existing entry in the domain."
)


def build_system_prompt(mode: str, ctx: AssistantContext) -> str:
    base = [
        "You are a world-building design assistant for an RPG world configurator.",
        "You will receive domain data (e.g., classes, origins) and MUST follow constraints:",
        "- For modifications, ONLY modify whitelisted JSON Pointer paths.",
        "- Prefer precise RFC6902 JSON Patch ops (add/replace/remove).",
        "- Maintain data consistency and avoid inventing unknown keys.",
        "- Do not return a full replacement object for modify_selection; only return patch ops.",
        "- When creating a new entry, ensure the new name is unique within the domain.",
    ]

    if mode == "analyze":
        base.append(ANALYZE_CONTRACT)
    elif mode == "modify":
        base.append("Allowed edit paths: " + ", ".join(ctx.allowed_paths))
        base.append(MODIFY_CONTRACT)
    elif mode == "create":
        # If existing names are provided in references, emphasize not to reuse them
        if ctx.references and isinstance(ctx.references, dict):
            existing = ctx.references.get("existing_names") or ctx.references.get("existing_names_list")
            if existing and isinstance(existing, list) and existing:
                base.append("Do not reuse any of these existing names: " + ", ".join(existing[:50]))
        base.append(CREATE_CONTRACT)
    else:
        base.append("Unknown mode; still follow JSON output contracts strictly.")

    return "\n".join(base)


def build_messages(mode: str, ctx: AssistantContext, user_text: str) -> List[dict]:
    """Constructs a list of chat messages for the LLM (single-turn)."""
    sys = build_system_prompt(mode, ctx)

    content_blocks = [
        f"Domain: {ctx.domain}",
        f"Selection ID: {ctx.selection_id or 'N/A'}",
        "Current Selection JSON:\n" + (json.dumps(ctx.content, ensure_ascii=False, indent=2) if ctx.content else "N/A"),
    ]

    if ctx.schema:
        content_blocks.append("Schema Hints:\n" + json.dumps(ctx.schema, ensure_ascii=False, indent=2))
    if ctx.exemplars:
        content_blocks.append("Examples (may inspire new entries):\n" + json.dumps(ctx.exemplars[:1], ensure_ascii=False, indent=2))
    if ctx.references:
        content_blocks.append("Reference Catalogs:\n" + json.dumps(ctx.references, ensure_ascii=False, indent=2))

    user_context = "\n\n".join(content_blocks)

    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": user_context},
        {"role": "user", "content": "My request:\n" + user_text},
    ]


def build_messages_analyze(history: List[dict], ctx: AssistantContext, user_text: str, lean: bool = True) -> List[dict]:
    """Construct multi-turn messages for Analyze mode.

    - First turn (no history): include system + selection JSON + references + user request.
    - Follow-ups: include system + prior history + new user_text.
      If lean is False, we also resend the selection JSON block before the new user_text.
    """
    sys = build_system_prompt("analyze", ctx)

    if not history:
        # First turn: seed with selection JSON and references
        content_blocks = [
            f"Domain: {ctx.domain}",
            f"Selection ID: {ctx.selection_id or 'N/A'}",
            "Current Selection JSON:\n" + (json.dumps(ctx.content, ensure_ascii=False, indent=2) if ctx.content else "N/A"),
        ]
        if ctx.schema:
            content_blocks.append("Schema Hints:\n" + json.dumps(ctx.schema, ensure_ascii=False, indent=2))
        if ctx.references:
            content_blocks.append("Reference Catalogs:\n" + json.dumps(ctx.references, ensure_ascii=False, indent=2))
        user_context = "\n\n".join(content_blocks)
        return [
            {"role": "system", "content": sys},
            {"role": "user", "content": user_context},
            {"role": "user", "content": "My request:\n" + user_text},
        ]

    # Follow-up turns
    messages: List[dict] = [
        {"role": "system", "content": sys}
    ]
    messages.extend(history)
    if not lean:
        # Re-ground with selection JSON again if not leaning
        rectx = [
            f"Domain: {ctx.domain}",
            f"Selection ID: {ctx.selection_id or 'N/A'}",
            "Current Selection JSON:\n" + (json.dumps(ctx.content, ensure_ascii=False, indent=2) if ctx.content else "N/A"),
        ]
        if ctx.references:
            rectx.append("Reference Catalogs:\n" + json.dumps(ctx.references, ensure_ascii=False, indent=2))
        messages.append({"role": "user", "content": "\n\n".join(rectx)})
    messages.append({"role": "user", "content": user_text})
    return messages

