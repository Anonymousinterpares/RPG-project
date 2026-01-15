#!/usr/bin/env python3
"""
Social Conflict agent for handling non-combat confrontations.
"""

import re
import json
from typing import List, Dict

from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext
from core.interaction.structured_requests import AgentOutput
from core.interaction.social_effects import SocialStatusEffect # Make sure SocialStatusEffect is imported
from core.stats.stats_base import Skill # Corrected: Import Skill from stats_base
get_logger
logger = get_logger("AGENT")

class SocialConflictAgent(BaseAgent):
    """
    Agent responsible for managing social conflicts (debates, negotiations, interrogations).

    It receives social context (participants, relationships, goals, resolve) and player input,
    generates narrative describing the social exchange, and identifies necessary skill checks
    (e.g., Persuasion, Deception, Intimidation, Insight) or state changes (e.g., changing
    relationship stance, reducing Resolve/Composure).
    """

    def __init__(self):
        """Initialize the social conflict agent."""
        super().__init__("SocialConflict")

    def _generate_system_prompt(self, context: AgentContext) -> str:
        """
        Generate the system prompt for the social conflict agent.
        """
        player_id = context.player_state.get("id", "player")
        # Extract social-specific context
        social_context = context.additional_context.get("social_context", {})
        participants_data = social_context.get("participants", []) 
        conflict_goal = social_context.get("goal", "Resolve the situation")
        current_topic = social_context.get("topic", "General discussion")

        # D3: Enhance participant list to show effects
        participant_list_parts = []
        for p in participants_data:
            effects = p.get('active_social_effects', [])
            effects_str = f" Effects: [{', '.join(map(str, effects))}]" if effects else ""
            participant_list_parts.append(
                f"- {p.get('name', 'Unknown')} (ID: {p.get('id', 'N/A')}, "
                f"Stance: {p.get('stance', 'Neutral')}, "
                f"Resolve: {p.get('resolve', '?')}/{p.get('max_resolve', '?')})"
                f"{effects_str}"
            )
        participant_list = "\n".join(participant_list_parts)

        system_prompt = f"""You are the Social Conflict AI moderator for a text-based RPG. Your role is to narrate social interactions like debates, negotiations, interrogations, or persuasion attempts, and interpret player actions within this context.
You will receive the current social situation and the player's input describing their intended social action.
Your output MUST be a single JSON object adhering *exactly* to the `AgentOutput` structure defined below.

## Current Social Conflict State
- Participants:
{participant_list}
- Conflict Goal: {conflict_goal}
- Current Topic: {current_topic}
- Player ID: {player_id}

## Your Responsibilities
1.  **Narrate the Attempt:** Generate engaging narrative describing the player's *attempted* social maneuver based on their input. **Do not state success or failure.**
2.  **Analyze Intent:** Analyze the player's natural language input.
3.  **Request Actions (Skill Checks & State Changes):**
    *   **Skill Checks (`request_skill_check`):**
        *   **When:** Request a skill check when success is uncertain.
        *   **Which Skill:** Use `{Skill.PERSUASION.name}`, `{Skill.INTIMIDATION.name}`, `{Skill.DECEPTION.name}`, `{Skill.INSIGHT.name}`, etc.
        *   **Target:** Specify `target_actor_id`.
        *   **Difficulty:** Instead of a number, assign a **`difficulty_tier`**: `trivial`, `easy`, `normal`, `hard`, `very_hard`, `impossible`. Base this on the target's resistance (Resolve, Stance) and the plausibility of the request.
    *   **State Changes (`request_state_change`):**
        *   **Resolve:** Reduce `current_resolve` (social HP) via `value: -5`, etc.
        *   **Social Status Effects:** Add/remove effects like `{SocialStatusEffect.CHARMED.name}`.

## Required Output Format (JSON)
```json
{{
  "narrative": "Your descriptive text...",
  "requests": [
    // Example 1: Persuasion Check
    {{
      "action": "request_skill_check",
      "actor_id": "{player_id}",
      "skill_name": "{Skill.PERSUASION.name}",
      "target_actor_id": "guard_captain",
      "difficulty_tier": "hard", // CHANGED: Use tier string
      "context": "Player attempting to persuade the captain."
    }},
    // Example 2: State Change (Resolve)
     {{
      "action": "request_state_change",
      "target_entity": "stubborn_noble",
      "attribute": "current_resolve",
      "change_type": "add",
      "value": -5,
      "context": "Result of successful intimidation."
    }},
    // Example 3: Applying 'Charmed' Status (State Change - often follows successful Persuasion/Charm check)
    {{
      "action": "request_state_change",
      "target_entity": "merchant_guildmaster",
      "attribute": "add_social_effect", // Use 'add_social_effect'
      "change_type": "set", // Type is less relevant here, but 'set' or 'add' is fine
      "value": "{SocialStatusEffect.CHARMED.name}", // String name of the SocialStatusEffect enum member
      "context": "Result of successful charm attempt."
    }},
    // Example 4: Removing 'Intimidated' Status (State Change)
    {{
      "action": "request_state_change",
      "target_entity": "frightened_peasant",
      "attribute": "remove_social_effect", // Use 'remove_social_effect'
      "change_type": "set", // Type is less relevant here
      "value": "{SocialStatusEffect.INTIMIDATED.name}", // String name of the effect to remove
      "context": "Player successfully calmed the peasant."
    }}
    // Add more requests here if the player's action involves multiple steps/effects
  ]
}}
```

## Guidelines
- **Interpret Intent:** Focus on the player's goal and the *implied* social tactic (persuade, intimidate, deceive, etc.) even if they don't use specific keywords.
- **Context is Key:** Base your requested checks and changes on the provided participant details (Resolve, Stance, Effects) and the overall situation. A high-Resolve character might require a higher DC to intimidate. An already 'Friendly' character might be easier to persuade.
- **Clarity & Precision:** Ensure `requests` use the correct IDs, attribute names (`current_resolve`, `add_social_effect`, `remove_social_effect`), skill names (`{Skill.PERSUASION.name}`, etc.), and effect names (`{SocialStatusEffect.CHARMED.name}`, etc.).
- **Multi-Step Actions:** If the player describes a complex action (e.g., "I flatter him then ask for the key"), break it down into multiple requests if necessary (e.g., a Persuasion check for flattery potentially followed by another Persuasion check for the key, maybe with a modifier).
- **Safety:** Adhere to standard content safety guidelines.

Respond to the player's social input by generating the JSON `AgentOutput` object.
"""
        return system_prompt

    # D3: Update _format_social_context to potentially include effects if available in context data
    def _format_social_context(self, context: AgentContext) -> str:
        """ Formats the social conflict specific context """
        social_context = context.additional_context.get("social_context", {})
        if not social_context:
            return ""

        lines = ["## Social Conflict Situation"]
        participants_data = social_context.get("participants", [])
        conflict_goal = social_context.get("goal", "Resolve the situation")
        current_topic = social_context.get("topic", "General discussion")
        recent_exchange = social_context.get("recent_exchange", "N/A") # Last significant statement/action

        lines.append(f"- Goal: {conflict_goal}")
        lines.append(f"- Topic: {current_topic}")
        lines.append(f"- Recent Exchange: {recent_exchange}")
        lines.append("### Participants:")
        for p in participants_data:
            # D3: Include active effects in the formatted context string
            effects = p.get('active_social_effects', []) # Get effects list/set
            # Ensure effects are strings before joining
            effects_str = f" Effects: [{', '.join(map(str, effects))}]" if effects else ""
            lines.append(
                f"- {p.get('name', 'Unknown')} (ID: {p.get('id', 'N/A')}, "
                f"Stance: {p.get('stance', 'Neutral')}, "
                f"Resolve: {p.get('resolve', '?')}/{p.get('max_resolve', '?')}, "
                f"Goal: {p.get('goal', 'Unknown')})"
                f"{effects_str}" # Append formatted effects
            )
        return "\n".join(lines)

    def _prepare_messages(self, context: AgentContext) -> List[Dict[str, str]]:
        """ Prepare messages, adding social context. """
        messages = super()._prepare_messages(context) # Get base messages

        # Find the user message and prepend social context
        for msg in reversed(messages):
            if msg["role"] == "user":
                social_context_str = self._format_social_context(context)
                if social_context_str:
                     original_user_content = msg["content"]
                     input_marker = "## Player Input"
                     if input_marker in original_user_content:
                         parts = original_user_content.split(input_marker, 1)
                         msg["content"] = f"{parts[0]}{social_context_str}\n\n{input_marker}{parts[1]}"
                     else:
                         msg["content"] = f"{social_context_str}\n\n{original_user_content}"
                break
        return messages

    def process(self, context: AgentContext) -> AgentOutput:
        """
        Process a social conflict request.
        """
        logger.info(f"Processing request with SocialConflict agent in mode: {context.game_state.get('mode', 'N/A')}")

        messages = self._prepare_messages(context)

        try:
            llm_response_content = self._llm_service.generate_response(messages)
            if not llm_response_content:
                 raise ValueError("LLM returned empty content.")
            logger.debug(f"Raw LLM Response (Social):\n{llm_response_content}")

            try:
                cleaned_response = re.sub(r'^```json\s*|\s*```$', '', llm_response_content, flags=re.MULTILINE | re.DOTALL).strip()
                parsed_output = json.loads(cleaned_response)

                if not isinstance(parsed_output, dict) or \
                   "narrative" not in parsed_output or \
                   "requests" not in parsed_output or \
                   not isinstance(parsed_output["requests"], list):
                    raise ValueError("LLM response is not a valid AgentOutput JSON structure.")

                validated_requests = []
                for req in parsed_output["requests"]:
                    if not isinstance(req, dict) or "action" not in req:
                        logger.warning(f"Skipping invalid request structure: {req}")
                        continue
                    validated_requests.append(req)

                agent_output: AgentOutput = {
                    "narrative": parsed_output.get("narrative", "Error: Narrative missing."),
                    "requests": validated_requests
                }

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Social LLM response as JSON: {e}\nRaw response: {llm_response_content}")
                agent_output: AgentOutput = {
                    "narrative": f"[SocialConflict Error: Parse failed] {llm_response_content}",
                    "requests": []
                }
            except ValueError as e:
                 logger.error(f"Invalid AgentOutput structure from Social LLM: {e}\nParsed: {parsed_output}")
                 agent_output: AgentOutput = {
                    "narrative": f"[SocialConflict Error: Invalid structure] {parsed_output.get('narrative', llm_response_content)}",
                    "requests": []
                 }

        except Exception as e:
            logger.exception(f"Error during SocialConflict processing: {e}")
            agent_output: AgentOutput = {
                "narrative": f"[SocialConflict Error: Processing failed: {e}]",
                "requests": []
            }

        logger.info(f"SocialConflict generated {len(agent_output['requests'])} requests.")
        return agent_output

    def supports_command(self, command: str) -> bool:
        return False # Handles interactions via natural language and structured requests

# Convenience function
def get_social_conflict_agent() -> SocialConflictAgent:
    return SocialConflictAgent()