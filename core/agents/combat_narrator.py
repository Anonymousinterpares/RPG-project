#!/usr/bin/env python3
"""
Combat Narrator agent for handling combat interactions.
"""

import re
import json
from typing import List, Dict, Optional, TYPE_CHECKING

from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext
from core.interaction.structured_requests import AgentOutput

# Use TYPE_CHECKING to avoid circular import with CombatManager
if TYPE_CHECKING:
    from core.combat.combat_manager import CombatManager

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
        participants_data = context.additional_context.get("participants", []) 
        turn_order_ids = combat_context.get("turn_order", [])
        current_turn_internal_id = combat_context.get("current_turn", "Unknown")

        id_to_combat_name = {p.get('id', 'N/A'): p.get('combat_name', p.get('name', 'Unknown')) for p in participants_data}

        turn_order_str = ", ".join([id_to_combat_name.get(p_id, '?') for p_id in turn_order_ids])
        current_turn_combat_name = id_to_combat_name.get(current_turn_internal_id, "Unknown")

        participant_list_parts = []
        player_combat_name = "Player"
        
        # Identify the faction of the current actor to help prompt logic
        current_actor_is_player = (current_turn_internal_id == player_id_internal)
        current_actor_is_enemy = not current_actor_is_player # Simple assumption for now

        for p in participants_data:
            p_internal_id = p.get('id', 'N/A')
            p_combat_name = id_to_combat_name.get(p_internal_id, p.get('name', 'Unknown'))

            if p_internal_id == player_id_internal:
                player_combat_name = p_combat_name

            effects = p.get('status_effects', {})
            effects_str_parts = []
            if isinstance(effects, dict):
                for name, duration_data in effects.items():
                    duration = None
                    if isinstance(duration_data, int):
                        duration = duration_data
                    elif isinstance(duration_data, dict):
                        duration = duration_data.get('duration')

                    if duration is None:
                        effects_str_parts.append(str(name))
                    else:
                        effects_str_parts.append(f"{name}({duration}t)")
            elif isinstance(effects, (list, set)):
                effects_str_parts = [str(eff) for eff in effects]

            effects_str = f" Effects: [{', '.join(effects_str_parts)}]" if effects_str_parts else ""

            hp = p.get('hp', '?')
            max_hp = p.get('max_hp', '?')
            stamina = p.get('stamina', '?')
            max_stamina = p.get('max_stamina', '?')
            
            # Add Type/Faction info to the list for the LLM
            p_type = p.get('entity_type', 'UNKNOWN') # e.g. PLAYER, ENEMY
            
            participant_list_parts.append(
                f"- Combat Name: '{p_combat_name}' (Type: {p_type}, "
                f"HP: {hp}/{max_hp}, "
                f"Stamina: {stamina}/{max_stamina})"
                f"{effects_str}"
            )
        participant_list = "\n".join(participant_list_parts)

        round_num = combat_context.get("round", 1)

        try:
            from core.stats.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()
            available_skills = skill_manager.get_skill_list_for_llm()
        except Exception as e:
            logger.warning(f"Could not load skills from SkillManager: {e}. Using defaults.")
            available_skills = """Available skills: MELEE_ATTACK, RANGED_ATTACK, UNARMED_ATTACK, SPELL_ATTACK, DEFENSE, DODGE"""

        # --- SYSTEM PROMPT (Added Targeting Logic) ---
        system_prompt = f"""You are the Combat Narrator AI for a text-based RPG. Your role is to process combat action INTENT, describe the attempted action, and output the corresponding game mechanics as structured requests.

        ## CRITICAL INSTRUCTION: JSON OUTPUT ONLY & COMBAT NAMES
        Your *ENTIRE* response MUST be a single, valid JSON object. NO introductory text.
        **VERY IMPORTANT**: When referring to entities in the `"requests"` list (`actor_id`, `target_actor_id`), YOU MUST use their **Combat Name** exactly as listed below.

        ## Targeting Logic (CRITICAL)
        1. **Identify the Actor:** The actor is the entity listed in 'Current Turn'.
        2. **Identify the Target:**
           - If the Actor is an **ENEMY**, they MUST target the **PLAYER** ('{player_combat_name}') or a Player ALLY.
           - **NEVER** allow an ENEMY to target themselves or another ENEMY with an attack.
           - If the intent provided is ambiguous (e.g., "Attack"), assume the target is the primary opponent (the Player).
           - If the Actor is the **PLAYER**, they target ENEMIES.
        3. **Self-Targeting:** Only allowed for beneficial actions (Healing, Buffs, Defend).

        ## Required Output Format (JSON Object Only)
        ```json
        {{
        "narrative": "Your descriptive text about the ATTEMPTED combat action. Focus on the *attempt*, NOT the outcome (success/failure).",
        "requests": [
            // --- Example 1: Physical Attack ---
            {{
            "action": "request_skill_check",
            "actor_id": "[ACTOR_COMBAT_NAME]", 
            "skill_name": "[ATTACK_SKILL_NAME]", 
            "stat_name": "[PHYSICAL_STAT]", 
            "target_actor_id": "[TARGET_COMBAT_NAME]", 
            "difficulty_tier": "normal", 
            "modifiers": {{}}, 
            "context": "Actor attacking Target with weapon_name"
            }}
        ]
        }}
        ```

        ## Current Combat State (Round {round_num})
        - Participants (Use **'Combat Name'** for IDs):
    {participant_list}
        - Turn Order (Combat Names): {turn_order_str}
        - Current Turn: '{current_turn_combat_name}'
        - Player Combat Name: '{player_combat_name}'

        ## Available Skills for Checks
    {available_skills}

        ## Task: Process Action Intent into JSON Output
        1.  **Narrate Attempt:** Describe the action attempt.
        2.  **Determine Mechanics:** Analyze 'Action Intent'.
        3.  **Targets:** Use **Combat Names** for IDs. **ENFORCE TARGETING LOGIC.**
        4.  **Difficulty:** Assign a `difficulty_tier` (`trivial`, `easy`, `normal`, `hard`, `very_hard`, `impossible`).
        5.  **Output JSON:** Ensure valid JSON.

        ## Action Intent to Process:
        ```
        {context.player_input}
        ```
        """
        return system_prompt

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
                
                # 1.5. Remove C-style comments (// ...)
                # This is crucial because the LLM sometimes ignores the "no comments" rule.
                cleaned_response = re.sub(r'//.*$', '', cleaned_response, flags=re.MULTILINE)

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
                # Determine combat mode robustly (additional_context or game_state; enum or string)
                mode_val = context.additional_context.get('mode') if hasattr(context, 'additional_context') else None
                if not mode_val and hasattr(context, 'game_state'):
                    try:
                        mode_val = context.game_state.get('mode')
                    except Exception:
                        mode_val = None
                is_combat_mode = False
                try:
                    from core.interaction.enums import InteractionMode as _IM
                    if isinstance(mode_val, _IM):
                        is_combat_mode = (mode_val == _IM.COMBAT)
                    else:
                        is_combat_mode = str(mode_val).upper() == 'COMBAT'
                except Exception:
                    is_combat_mode = str(mode_val).upper() == 'COMBAT'

                if is_combat_mode:
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

    def _generate_outcome_narration_prompt(self, action_result: Dict, combat_manager: 'CombatManager') -> str:
        """Generates the prompt for narrating an action's outcome, focusing on the result dict."""

        prompt = f"""You are the Combat Narrator AI. Describe the outcome of the combat action based *only* on the following JSON results. Be concise and vivid. Focus on what happened, not the mechanics.

        Action Result Data:
        ```json
        {json.dumps(action_result, indent=2, default=str)}
        ```

        Describe the outcome:"""
        return prompt

    def narrate_outcome(self, action_result: Dict, combat_manager: 'CombatManager') -> Optional[str]:
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