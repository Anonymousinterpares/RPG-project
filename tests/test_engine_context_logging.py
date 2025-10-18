#!/usr/bin/env python3
import json
import logging
import re

import pytest

from core.base.engine import GameEngine


def test_context_structured_log_emitted(caplog):
    eng = GameEngine()
    with caplog.at_level(logging.INFO):
        eng.set_game_context({"location": {"name": "Ashen Camp", "major": "camp"}, "weather": {"type": "clear"}}, source="test")
    # Find CONTEXT logger record
    found = False
    for rec in caplog.records:
        if rec.name == 'CONTEXT':
            try:
                payload = json.loads(rec.message)
                assert payload.get('event') == 'ContextUpdate'
                assert payload.get('source') == 'test'
                assert 'new' in payload
                assert 'changed_keys' in payload
                found = True
                break
            except Exception:
                # Some other CONTEXT lines may be non-JSON; ignore
                continue
    assert found, "Expected CONTEXT JSON log not found"
