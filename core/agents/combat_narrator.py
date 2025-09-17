#!/usr/bin/env python3
"""
Combat Narrator agent for handling combat interactions.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional

from core.combat.combat_manager import CombatManager
from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext
from core.interaction.structured_requests import AgentOutput, SkillCheckRequest, StateChangeRequest
from core.interaction.enums import InteractionMode
from core.stats.stats_base import Skill

logger = get_logger("AGENT")

class CombatNarratorAgent(BaseAgent):
    """
    Agent responsible for narrating combat and interpreting player/NPC actions within combat.

    It receives combat-specific context and player/NPC input, generates narrative
    describing the action's attempt, and identifies necessary skill checks
    or state changes requested by the intent.
    """

    def __init__(self):
        """Initialize the combat narrator agent."""
        super().__init__("CombatNarrator")

    def _generate_system_prompt(self, context: AgentContext) -> str:
        """
        Generate the system prompt for the combat narrator agent.
        """
        # --- Context Extraction (Use combat_name where appropriate) ---
        player_id_internal = context.player_state.get("id", "player")
        combat_context = context.additional_context.get("combat_context", {})
        participants_data = context.additional_context.get("participants", []) # Get full participant data
        turn_order_ids = combat_context.get("turn_order", [])
        current_turn_internal_id = combat_context.get("current_turn", "Unknown")

        # Create mapping from internal ID to combat name for easier lookup
        id_to_combat_name = {p.get('id', 'N/A'): p.get('combat_name', p.get('name', 'Unknown')) for p in participants_data}

        turn_order_str = ", ".join([id_to_combat_name.get(p_id, '?') for p_id in turn_order_ids]) # Use combat names
        current_turn_combat_name = id_to_combat_name.get(current_turn_internal_id, "Unknown")

        participant_list_parts = []
        player_combat_name = "Player" # Default

        for p in participants_data:
            p_internal_id = p.get('id', 'N/A')
            p_combat_name = id_to_combat_name.get(p_internal_id, p.get('name', 'Unknown')) # Get combat name via mapping

            if p_internal_id == player_id_internal:
                player_combat_name = p_combat_name # Store player's combat name

            # Format status effects (assuming dict {name: duration/data})
            effects = p.get('status_effects', {})
            effects_str_parts = []
            if isinstance(effects, dict):
                for name, duration_data in effects.items():
                    duration = None
                    if isinstance(duration_data, int):
                        duration = duration_data
                    elif isinstance(duration_data, dict): # Handle StatusEffectData dicts
                        duration = duration_data.get('duration')

                    if duration is None:
                        effects_str_parts.append(str(name))
                    else:
                        effects_str_parts.append(f"{name}({duration}t)") # Use 't' for turns
            elif isinstance(effects, (list, set)): # Fallback for list/set format
                effects_str_parts = [str(eff) for eff in effects]

            effects_str = f" Effects: [{', '.join(effects_str_parts)}]" if effects_str_parts else ""

            # Get HP/Stamina safely
            hp = p.get('hp', '?')
            max_hp = p.get('max_hp', '?')
            stamina = p.get('stamina', '?') # Assuming stamina might be in context now
            max_stamina = p.get('max_stamina', '?')

            participant_list_parts.append(
                f"- Combat Name: '{p_combat_name}' (Original: {p.get('name', 'Unknown')}, "
                f"HP: {hp}/{max_hp}, "
                f"Stamina: {stamina}/{max_stamina})"
                f"{effects_str}"
            )
        participant_list = "\n".join(participant_list_parts)

        round_num = combat_context.get("round", 1)

        # --- Load Skills (existing logic) ---
        try:
            from core.stats.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()
            available_skills = skill_manager.get_skill_list_for_llm()
        except Exception as e:
            logger.warning(f"Could not load skills from SkillManager: {e}. Using defaults.")
            available_skills = """Available skills for checks (use exact names):
    - MELEE_ATTACK: Physical close-range combat attacks
    - RANGED_ATTACK: Physical ranged combat attacks
    - UNARMED_ATTACK: Attacking without weapons
    - SPELL_ATTACK: Magical attacks
    - DEFENSE: Blocking or parrying attacks
    - DODGE: Avoiding attacks and obstacles"""

        # --- SYSTEM PROMPT (Emphasize Combat Names) ---
        system_prompt = f"""You are the Combat Narrator AI for a text-based RPG. Your role is to process combat action INTENT, describe the attempted action, and output the corresponding game mechanics as structured requests.

        ## CRITICAL INSTRUCTION: JSON OUTPUT ONLY & COMBAT NAMES
        Your *ENTIRE* response MUST be a single, valid JSON object. NO introductory text, explanations, markdown, or other characters outside the JSON structure.
        **VERY IMPORTANT**: When referring to entities in the `"requests"` list (`actor_id`, `target_actor_id`, `target_entity`), YOU MUST use their **Combat Name** exactly as listed in the 'Participants' section below (e.g., 'Qa', 'elder', 'Goblin 1'). Do **NOT** use original names or generic terms like 'player'.

        ## Required Output Format (JSON Object Only)
        ```json
        {{
        "narrative": "Your descriptive text about the ATTEMPTED combat action. Describe the wind-up, movement, target, etc. Focus on the *attempt*, NOT the outcome (success/failure). Do NOT repeat the input intent verbatim.",
        "requests": [
            // REQUIRED: Include one or more structured requests based on the action intent.
            // Use the examples below ONLY as structural guides. DO NOT use the specific values from the examples.
            // --- Example 1: Physical Attack (Melee/Ranged/Unarmed) ---
            {{
            "action": "request_skill_check",
            "actor_id": "[ACTOR_COMBAT_NAME]", // **USE COMBAT NAME** of the entity performing the action (from Current Turn context)
            "skill_name": "[ATTACK_SKILL_NAME]", // MELEE_ATTACK, RANGED_ATTACK, or UNARMED_ATTACK
            "stat_name": "[PHYSICAL_STAT]", // Typically STRENGTH or DEXTERITY
            "target_actor_id": "[TARGET_COMBAT_NAME]", // **USE COMBAT NAME** of the target entity (from Action Intent or Participants list)
            "difficulty_class": "[ESTIMATED_DEFENSE]", // Target's Defense score - Estimate 10-15 if unknown
            "modifiers": {{}}, // Optional: {{"circumstance_bonus": 2}}
            "context": "[Brief context, e.g., 'Actor attacking Target with weapon_name']"
            }},
            // --- Example 2: Spell Attack ---
            {{
            "action": "request_skill_check",
            "actor_id": "[ACTOR_COMBAT_NAME]", // **USE COMBAT NAME**
            "skill_name": "SPELL_ATTACK",
            "stat_name": "[SPELLCASTING_STAT]", // Typically INTELLIGENCE, WISDOM, or CHARISMA
            "target_actor_id": "[TARGET_COMBAT_NAME]", // **USE COMBAT NAME**
            "difficulty_class": "[ESTIMATED_MAGIC_DEFENSE]", // Target's Magic Defense or Save DC estimate (10-15)
            "modifiers": {{}},
            "context": "[Brief context, e.g., 'Actor casting spell_name at Target']"
            }},
            // --- Example 3: Applying Status Effect ---
            {{
            "action": "request_state_change",
            "target_entity": "[TARGET_COMBAT_NAME]", // **USE COMBAT NAME**
            "attribute": "add_status_effect", // Or "remove_status_effect"
            "change_type": "set", // Usually 'set' for effects
            "value": "[EFFECT_NAME]", // String name (e.g., BURNING, STUNNED, DEFENDING)
            "duration": "[DURATION_TURNS]", // Optional: Integer number of turns
            "context": "[Brief context, e.g., 'Result of spell hitting target']"
            }}
            // Add other request types (like Defend via state change) as needed.
        ]
        }}
        ```

        ## Current Combat State (Round {round_num})
        - Participants (Use **'Combat Name'** for IDs in JSON requests):
    {participant_list}
        - Turn Order (Combat Names): {turn_order_str}
        - Current Turn: '{current_turn_combat_name}'
        - Player Combat Name: '{player_combat_name}'

        ## Available Skills for Checks (Use ONLY these skill names in `skill_name`)
    {available_skills}

        ## Task: Process Action Intent into JSON Output
        Given the current combat state and the 'Action Intent to Process' below:
        1.  **Narrate Attempt:** Describe the action attempt. DO NOT determine success/failure.
        2.  **Determine Mechanics & Target:**
            *   Analyze the 'Action Intent'. Identify the intended action type (physical attack, spell, defend, etc.) and the intended target (by name or description).
            *   Find the Target **Combat Name**: Match the intended target name/description from the intent to a participant in the 'Participants' list. Use the corresponding **Combat Name** for `target_actor_id` or `target_entity`. **CRITICAL: Use ONLY Combat Names listed in the 'Participants' section.**
            *   Find the Actor **Combat Name**: Use the name provided in 'Current Turn'.
        3.  **Select Skill & Stat:** Choose the most appropriate `skill_name` from the 'Available Skills' list. Determine the likely primary `stat_name`.
        4.  **Construct Request(s):** Create the JSON request object(s).
            *   Use the correct Actor **Combat Name** and Target **Combat Name** found in step 2.
            *   Fill in other fields (`skill_name`, `stat_name`, `difficulty_class`, etc.) based on the action. For attacks, estimate target defenses (10-15) if unknown.
        5.  **Output JSON:** Ensure the final output is ONLY the valid JSON object. NO EXTRA TEXT.

        ## Action Intent to Process:
        ```
        {context.player_input}
        ```

        ## REMEMBER: YOUR ENTIRE RESPONSE MUST BE A SINGLE VALID JSON OBJECT. USE ONLY **COMBAT NAMES** FOR IDs.
        """
        return system_prompt

    # TODO: Add method CombatNarratorAgent.narrate_outcome(action_result, combat_manager)
    # This method would take the result dictionary from perform_action and generate narrative.
    # It would need its own system prompt focused on describing outcomes.

    def _format_combat_context(self, context: AgentContext) -> str:
        """ Formats the combat specific context """
        combat_context = context.additional_context.get("combat_context", {})
        if not combat_context:
            return ""

        lines = ["## Combat Situation"]
        participants = combat_context.get("participants", [])
        turn_order = combat_context.get("turn_order", [])
        current_turn = combat_context.get("current_turn", "Unknown")
        round_num = combat_context.get("round", 1)

        lines.append(f"- Round: {round_num}")
        lines.append(f"- Current Turn: {current_turn}")
        lines.append(f"- Turn Order: {', '.join(turn_order)}")
        lines.append("### Participants:")
        for p in participants:
            # Assuming status_effects is now a dict {name: duration}
            status_str = ", ".join(p.get('status_effects', {}).keys())
            lines.append(f"- {p.get('name', 'Unknown')} (ID: {p.get('id', 'N/A')}, HP: {p.get('hp', '?')}/{p.get('max_hp', '?')}, Stamina: {p.get('stamina', '?')}/{p.get('max_stamina', '?')}, Status: {status_str or 'Normal'})") # Added Stamina

        environment_tags = context.additional_context.get("environment", [])
        if environment_tags:
            lines.append("### Environmental Features:")
            lines.append(f"- Tags: {', '.join(environment_tags)}")

        return "\n".join(lines)

    def _prepare_messages(self, context: AgentContext) -> List[Dict[str, str]]:
        """
        Prepare the message list specifically for the Combat Narrator.
        """
        messages = []
        # Generate the system prompt with the actual input substituted
        final_system_prompt = self._generate_system_prompt(context)
        messages.append({"role": "system", "content": final_system_prompt})
        # Note: We do NOT add conversation history or a separate user message here,
        # as the entire context and the specific action intent are baked into the system prompt.
        logger.debug(f"Prepared messages for CombatNarrator (System Prompt Only):\n{messages[0]['content'][:500]}...") # Log start of prompt
        return messages

    def process(self, context: AgentContext) -> Optional[AgentOutput]:
        """
        Process a combat request, expecting a structured JSON output.

        Args:
            context: The context for the request.

        Returns:
            An AgentOutput dictionary containing the narrative and structured requests, or None on failure.
        """
        # Log the mode being processed and the player input
        mode = context.additional_context.get('mode', 'N/A')
        player_input = context.player_input if hasattr(context, 'player_input') else 'No input'
        logger.info(f"Processing request with CombatNarrator agent. Mode: {mode}, Intent: '{player_input[:50]}...'")

        messages = self._prepare_messages(context)
        agent_output: Optional[AgentOutput] = None # Initialize

        try:
            # --- LLM Call ---
            effective_model = self._model or None
            llm_response = self._llm_manager.get_completion(
                messages=messages,
                provider_type=self._provider_type,
                model=effective_model,
                temperature=self._temperature,
                max_tokens=self._settings.get("max_tokens", 1000),
                timeout=self._settings.get("timeout_seconds", 30)
            )

            if not llm_response or not llm_response.content:
                raise ValueError("LLM returned empty response or content.")

            llm_response_content = llm_response.content.strip()
            logger.debug(f"Raw LLM Response (Combat):\n```\n{llm_response_content}\n```")

            # --- Enhanced JSON Parsing ---
            parsed_output = None
            cleaned_response = llm_response_content
            try:
                 # 1. Remove potential markdown fences first
                cleaned_response = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned_response, flags=re.MULTILINE).strip()

                # 2. Try direct parsing
                parsed_output = json.loads(cleaned_response)
                logger.debug("Successfully parsed JSON directly.")

            except json.JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {e}. Trying to extract JSON object...")
                # 3. If direct parsing fails, try to find the first '{' and last '}'
                start_index = cleaned_response.find('{')
                end_index = cleaned_response.rfind('}')
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    json_substring = cleaned_response[start_index : end_index + 1]
                    try:
                        parsed_output = json.loads(json_substring)
                        logger.info("Successfully parsed extracted JSON substring.")
                    except json.JSONDecodeError as e_inner:
                        logger.error(f"Failed to parse extracted JSON substring: {e_inner}")
                        logger.error(f"Substring attempted: ```\n{json_substring}\n```")
                        parsed_output = None # Ensure it's None if second parse fails
                else:
                    logger.error("Could not find valid JSON object markers '{' and '}' in the response.")
                    parsed_output = None

            # --- Validate Structure and Build Output ---
            if (isinstance(parsed_output, dict) and
                "narrative" in parsed_output and
                "requests" in parsed_output and
                isinstance(parsed_output["requests"], list)):

                # Validate requests format (basic check)
                validated_requests = []
                for req in parsed_output["requests"]:
                    if isinstance(req, dict) and "action" in req:
                        validated_requests.append(req)
                    else:
                        logger.warning(f"Skipping invalid request structure: {req}")

                agent_output = {
                    "narrative": parsed_output["narrative"],
                    "requests": validated_requests
                }
                narrative_snippet = parsed_output["narrative"][:100]
                logger.info(f"Successfully parsed valid JSON response. Narrative: '{narrative_snippet}...', Requests: {len(validated_requests)}")

            else: # Parsing failed or structure invalid
                logger.error("Failed to parse LLM response as valid JSON AgentOutput.")
                # **Fallback:** Create a default basic attack request if parsing fails during combat
                # This prevents combat from stalling completely if the LLM messes up JSON.
                if context.game_state.get("mode") == InteractionMode.COMBAT:
                    logger.warning("Applying fallback: Generating basic attack request due to JSON failure.")
                    # Find a likely target (first enemy)
                    target_id = None
                    combat_context = context.additional_context.get("combat_context", {})
                    participants = combat_context.get("participants", [])
                    player_id = context.player_state.get("id", "player")
                    for p in participants:
                        p_id = p.get('id')
                        p_type = p.get('entity_type') # Assuming type is available
                        if p_id != player_id and p_type == 'ENEMY': # Find first enemy
                             target_id = p_id
                             break

                    if target_id:
                        fallback_request = {
                            "action": "request_skill_check",
                            "actor_id": player_id,
                            "skill_name": "MELEE_ATTACK", # Assume basic melee
                            "stat_name": "STRENGTH",
                            "target_actor_id": target_id,
                            "difficulty_class": 12, # Default guess
                            "modifiers": {},
                            "context": f"Fallback: Actor basic attack on {target_id}."
                        }
                        agent_output = {
                            "narrative": f"{context.player_state.get('name', 'Actor')} attempts a basic attack on {target_id}. (LLM response parsing failed)",
                            "requests": [fallback_request]
                        }
                        logger.info("Generated fallback basic attack request.")
                    else:
                         # If no target found, return error narrative
                         agent_output = {
                             "narrative": "You attempt an action, but something goes wrong. (LLM Response Error)",
                             "requests": []
                         }
                else:
                     # If not in combat, just return error narrative
                     agent_output = {
                        "narrative": "There was an issue processing the response. (LLM Response Error)",
                        "requests": []
                     }

        except Exception as e:
            logger.exception(f"Error during CombatNarrator processing: {e}")
            agent_output = None # Indicate failure

        if agent_output:
             logger.info(f"CombatNarrator generated output with {len(agent_output['requests'])} requests.")
        else:
             logger.error("CombatNarrator failed to generate valid output.")

        return agent_output

    def supports_command(self, command: str) -> bool:
        # Combat Narrator doesn't handle direct commands, only interprets intent
        return False

    def _generate_outcome_narration_prompt(self, action_result: Dict, combat_manager: CombatManager) -> str:
        """Generates the prompt for narrating an action's outcome, focusing on the result dict."""

        prompt = f"""You are the Combat Narrator AI. Describe the outcome of the combat action based *only* on the following JSON results. Be concise and vivid. Focus on what happened, not the mechanics.

        Action Result Data:
        ```json
        {json.dumps(action_result, indent=2, default=str)}
        ```

        Describe the outcome:"""
        return prompt

    def narrate_outcome(self, action_result: Dict, combat_manager: CombatManager) -> Optional[str]:
        """Generates narrative describing the outcome of a resolved action."""
        if not action_result:
            logger.warning("narrate_outcome called with no action_result.")
            return None

        logger.info(f"Attempting to narrate outcome for action result: {action_result}")
        prompt = self._generate_outcome_narration_prompt(action_result, combat_manager)
        # Send result as JSON for the LLM to parse
        messages = [{"role": "system", "content": "You are the Combat Narrator AI. Describe the outcome of the action concisely and vividly based *only* on the provided JSON result details."},
                    {"role": "user", "content": f"Action Result Data:\n```json\n{json.dumps(action_result, indent=2, default=str)}\n```\n\nDescribe the outcome:"}]

        raw_llm_response_content = "[No LLM Response]" # Default for logging if call fails
        try:
            logger.debug(f"Calling LLM for outcome narration. Prompt implies action: {action_result.get('action_name', 'unknown')}")
            llm_response = self._llm_manager.get_completion(
                messages=messages, provider_type=self._provider_type, model=self._model,
                temperature=0.6, max_tokens=150
            )

            if llm_response and llm_response.content:
                raw_llm_response_content = llm_response.content # Store raw response for logging
                narrative = raw_llm_response_content.strip()
                # Basic cleaning
                narrative = re.sub(r'^(Outcome Description|Narrative|Result)[:\s]*', '', narrative, flags=re.IGNORECASE).strip()
                narrative = re.sub(r'^```(?:json)?\s*|\s*```$', '', narrative, flags=re.MULTILINE).strip()
                # Ensure it's not empty after cleaning
                if not narrative:
                    logger.warning("LLM returned empty content after cleaning for outcome narration.")
                    logger.debug(f"Raw response for empty outcome narration: {raw_llm_response_content}") # Log raw response if clean fails
                    return None

                logger.info(f"Generated outcome narrative: '{narrative[:100]}...'")
                return narrative
            else:
                logger.warning("LLM returned no content for outcome narration.")
                return None
        except Exception as e:
            logger.exception(f"Error generating outcome narration via LLM: {e}")
            logger.debug(f"Raw response (if any) leading to outcome narration error: {raw_llm_response_content}") # Log raw response on error
            return f"[System Error: Could not generate outcome description for {action_result.get('action_name', 'action')}.]"
        
# Convenience function
def get_combat_narrator_agent() -> CombatNarratorAgent:
    return CombatNarratorAgent()