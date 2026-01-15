#!/usr/bin/env python3
import sys
import os
import re
import json
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.curdir))

from core.agents.narrator import NarratorAgent
from core.agents.base_agent import AgentContext

def test_parsing():
    agent = NarratorAgent()
    
    # Test 1: Clean JSON (Standard)
    print("Test 1: Clean JSON")
    resp_clean = '{"narrative": "Hello world", "requests": [{"action": "request_skill_check", "skill_name": "LOCKPICKING"}]}'
    
    agent._llm_manager.get_completion = MagicMock()
    agent._llm_manager.get_completion.return_value.content = resp_clean
    
    context = AgentContext(game_state={}, player_state={}, world_state={}, player_input="hi", conversation_history=[])
    parsed1 = agent.process(context)
    assert parsed1["narrative"] == "Hello world"
    assert len(parsed1["requests"]) == 1
    print("Test 1 Passed")

    # Test 2: Markdown wrapped JSON
    print("\nTest 2: Markdown wrapped JSON")
    resp_md = 'Certainly! Here is the response:\n```json\n{"narrative": "MD hello", "requests": []}\n```\nHope this helps!'
    # We need a way to call the parsing logic. In narrator.py, it's inside process() but I can mock the LLM call or extract it.
    # Looking at narrator.py again, I can see the logic is now robust.
    
    # Let's mock get_completion to return resp_md
    agent._llm_manager.get_completion = MagicMock()
    agent._llm_manager.get_completion.return_value.content = resp_md
    
    context = AgentContext(game_state={}, player_state={}, world_state={}, player_input="hi", conversation_history=[])
    output2 = agent.process(context)
    assert output2["narrative"] == "MD hello"
    print("Test 2 Passed")

    # Test 3: Mixed text and JSON (no code block)
    print("\nTest 3: Mixed text and JSON (no code block)")
    resp_mixed = 'Narrative preamble. {"narrative": "Mixed hello", "requests": [{"action": "request_mode_transition"}]} Postscript.'
    agent._llm_manager.get_completion.return_value.content = resp_mixed
    output3 = agent.process(context)
    assert output3["narrative"] == "Mixed hello"
    assert output3["requests"][0]["action"] == "request_mode_transition"
    print("Test 3 Passed")

    print("\nAll Parsing Tests Passed!")

if __name__ == "__main__":
    # Add a helper method to NarratorAgent for testing if needed, or just use process()
    # The current NarratorAgent.process() uses self._llm_manager.get_completion
    test_parsing()
