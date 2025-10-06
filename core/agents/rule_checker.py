#!/usr/bin/env python3
"""
Rule checker agent for validating player actions.

This module provides a RuleCheckerAgent class that validates player
actions against game rules, prevents cheating, and ensures game fairness.
"""

import os
import re
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
import logging

from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext, AgentResponse

# Get the module logger
logger = get_logger("AGENT")

class RuleCheckerAgent(BaseAgent):
    """
    Rule checker agent for validating player actions.
    
    This agent validates player actions against game rules, provides feedback
    on invalid actions, and implements anti-cheat measures to ensure a fair
    and balanced game experience.
    """
    
    # Command types that can be validated
    SUPPORTED_COMMANDS = [
        "ACTION_VALIDATE", "COMBAT_VALIDATE", "LOOT_VALIDATE",
        "QUEST_VALIDATE", "RULE_QUERY", "ANTICHEAT_CHECK",
        "STAT_CHECK", "RULE_CHECK"
    ]
    
    def __init__(self, entity_manager=None, item_manager=None, stats_manager=None, world_manager=None):
        """Initialize the rule checker agent."""
        super().__init__("rule_checker")
        
        # Store the managers passed from the engine
        self._entity_manager = entity_manager
        self._item_manager = item_manager
        self._stats_manager = stats_manager
        self._world_manager = world_manager
        
        # Track entities that have already been looted
        self._looted_entities: Set[str] = set()
        
        # Track time-limited events that have been completed
        self._completed_events: Dict[str, float] = {}
        
        # Track action history for anti-cheat detection
        self._action_history: List[Dict[str, Any]] = []

    def reset(self) -> None:
        """Reset in-memory caches and histories so no state leaks between sessions."""
        try:
            if hasattr(self, "_looted_entities") and isinstance(self._looted_entities, set):
                self._looted_entities.clear()
            else:
                self._looted_entities = set()
            if hasattr(self, "_completed_events") and isinstance(self._completed_events, dict):
                self._completed_events.clear()
            else:
                self._completed_events = {}
            if hasattr(self, "_action_history") and isinstance(self._action_history, list):
                self._action_history.clear()
            else:
                self._action_history = []
            logger.info("RuleChecker agent state reset")
        except Exception:
            # Fall back to reinitializing the containers
            self._looted_entities = set()
            self._completed_events = {}
            self._action_history = []
            logger.info("RuleChecker agent state reset (containers reinitialized)")
    
    def _generate_system_prompt(self, context: AgentContext) -> str:
        """
        Generate the system prompt for the rule checker agent.
        
        Args:
            context: The agent context.
        
        Returns:
            The system prompt string.
        """
        system_prompt = """You are the RuleChecker, an AI responsible for validating player actions against game rules and preventing cheating. Your role is to ensure fair play while maintaining immersion.

## Your Responsibilities
1. Validate player actions against game rules and mechanics
2. Identify and prevent exploits and cheating
3. Provide clear feedback when actions are invalid
4. Ensure consistent application of rules
5. Track entities that have been looted to prevent double-looting
6. Monitor time-limited events to prevent replaying
7. Analyze patterns of behavior for potential cheating

## Key Rules to Enforce
- **Physics and Realism**: Actions must be physically possible within the game world
- **Character Capabilities**: Actions must be within the character's abilities
- **Resource Limits**: Players cannot exceed inventory weight, size limits, or currency caps
- **Consequence Consistency**: Similar actions should have similar consequences
- **Anti-Exploitation**: Prevent looting the same entity multiple times
- **Time Integrity**: Prevent replaying time-limited events
- **Action Atomicity**: Ensure actions are completed properly with all side effects

## Response Format
Your response MUST follow this exact format with these exact section markers to be properly processed:

<REASONING>
Provide your detailed reasoning process here (for development purposes).
</REASONING>

<DECISION>
YES or NO (write only one of these words)
</DECISION>

<EXPLANATION>
If NO, explain why the action is invalid in a clear, helpful manner.
If YES, briefly explain why the action is valid.
</EXPLANATION>

<SUGGESTIONS>
If NO, suggest alternatives when appropriate.
If YES, this section can be brief or empty.
</SUGGESTIONS>

## Special Instructions
- Balance strictness with fun - apply rules consistently but don't be pedantic
- Focus on significant rule violations, not minor inconsistencies
- Consider character attributes and skills when evaluating actions
- Flag suspicious behavior patterns for further review
- Always prioritize game balance and fair play
- Always include all four sections in your response, even if some are empty

## Mode Transition Validation
- **Contextual Sense:** Does the requested transition make sense given the current situation, location, and participants? (e.g., initiating trade during a fight is invalid).
- **Target Validity:** For the requested mode transition, check if the target entity (if any) exists. If target entity is mentioned by name but not found in context, do not immediately reject the transition - assume the entity *could* be created dynamically for combat.
- **Combat Fleeing:** Attempting to flee combat (`request_mode_transition` to NARRATIVE from COMBAT) is generally a valid *attempt*, but the success is determined by a later skill check. Validate the *attempt* itself (e.g., is the player prevented from moving?).  
- **Initiating Combat:** Ensure combat is initiated against valid targets. If target is not found in current context but has a name that could be an enemy (like "goblin", "bandit", "guard", "elder", etc.), assume it's a potentially valid target that will be created dynamically. 
- **Initiating Trade/Social:** Ensure the target is present and capable of participating.

Respond with your validation assessment of the player's proposed action.
"""
        
        return system_prompt
    
    def _prepare_messages(self, context: AgentContext) -> List[Dict[str, str]]:
        """
        Prepare the message list for the LLM request.
        
        Args:
            context: The agent context.
        
        Returns:
            List of message dictionaries (role, content).
        """
        messages = []
        
        # Add system prompt
        system_prompt = self._generate_system_prompt(context)
        messages.append({"role": "system", "content": system_prompt})
        
        # Add player stats and capabilities
        player_info = self._format_player_info(context)
        if player_info:
            messages.append({"role": "user", "content": player_info})
        
        # Add recent action history for context
        action_history = self._format_action_history()
        if action_history:
            messages.append({"role": "user", "content": action_history})
        
        # Add the validation request with player input
        validation_request = self._format_validation_request(context)
        messages.append({"role": "user", "content": validation_request})
        
        return messages
    
    def _format_player_info(self, context: AgentContext) -> str:
        """
        Format player information for the LLM prompt.
        
        Args:
            context: The agent context.
        
        Returns:
            Formatted player information string.
        """
        player_state = context.player_state
        if not player_state:
            return ""
        
        # Extract player information
        player_name = player_state.get("name", "Unknown")
        player_race = player_state.get("race", "Human")
        player_path = player_state.get("path", "Wanderer")
        player_level = player_state.get("level", 1)
        
        # Extract player stats
        strength = player_state.get("strength", 10)
        agility = player_state.get("agility", 10)
        constitution = player_state.get("constitution", 10)
        intelligence = player_state.get("intelligence", 10)
        wisdom = player_state.get("wisdom", 10)
        charisma = player_state.get("charisma", 10)
        
        # Extract player status
        health = player_state.get("health", 100)
        max_health = player_state.get("max_health", 100)
        stamina = player_state.get("stamina", 100)
        max_stamina = player_state.get("max_stamina", 100)
        mana = player_state.get("mana", 100)
        max_mana = player_state.get("max_mana", 100)
        
        # Format the information
        info_lines = [
            "## Player Information",
            f"- Name: {player_name}",
            f"- Race: {player_race}",
            f"- Path: {player_path}",
            f"- Level: {player_level}",
            "",
            "### Stats",
            f"- Strength: {strength}",
            f"- Agility: {agility}",
            f"- Constitution: {constitution}",
            f"- Intelligence: {intelligence}",
            f"- Wisdom: {wisdom}",
            f"- Charisma: {charisma}",
            "",
            "### Status",
            f"- Health: {health}/{max_health}",
            f"- Stamina: {stamina}/{max_stamina}",
            f"- Mana: {mana}/{max_mana}"
        ]
        
        # Add inventory details if available for more accurate validation
        inventory_info = context.additional_context.get("inventory", {}) if context.additional_context else {}
        if inventory_info:
            # Weight/slots summary (robust to nested structure in data_retrieval)
            try:
                weight_current = inventory_info.get("weight", {}).get("current", inventory_info.get("current_weight", 0))
                weight_limit = inventory_info.get("weight", {}).get("limit", inventory_info.get("weight_limit", 0))
                info_lines.append(f"- Inventory Weight: {weight_current}/{weight_limit} units")
                slots_used = inventory_info.get("slots", {}).get("used")
                slots_limit = inventory_info.get("slots", {}).get("limit")
                if slots_used is not None and slots_limit is not None:
                    info_lines.append(f"- Inventory Slots: {slots_used}/{slots_limit}")
            except Exception:
                pass

            # Equipped items
            try:
                equipped = inventory_info.get("equipped", {}) or {}
                if equipped:
                    info_lines.append("")
                    info_lines.append("### Equipped Items")
                    for slot, item in equipped.items():
                        if isinstance(item, dict):
                            name = item.get("name", "Unknown Item")
                            iid = item.get("id", "?")
                            info_lines.append(f"- {slot}: {name} (id: {iid})")
                        else:
                            info_lines.append(f"- {slot}: {str(item)}")
            except Exception:
                pass

            # Backpack items
            try:
                backpack = inventory_info.get("backpack", []) or []
                if backpack:
                    info_lines.append("")
                    info_lines.append("### Backpack Items")
                    # List at most the first 25 to keep prompts concise
                    for idx, item in enumerate(backpack[:25]):
                        if isinstance(item, dict):
                            name = item.get("name", "Unknown Item")
                            iid = item.get("id", "?")
                            qty = item.get("quantity", 1)
                            qstr = f" x{qty}" if isinstance(qty, int) and qty > 1 else ""
                            info_lines.append(f"- {name}{qstr} (id: {iid})")
                        else:
                            info_lines.append(f"- {str(item)}")
                    if len(backpack) > 25:
                        info_lines.append(f"...and {len(backpack)-25} more items")
            except Exception:
                pass
        
        return "\n".join(info_lines)
    
    def _format_action_history(self) -> str:
        """
        Format recent action history for context.
        
        Returns:
            Formatted action history string.
        """
        if not self._action_history:
            return ""
        
        # Get the last 5 actions for context
        recent_actions = self._action_history[-5:]
        
        lines = ["## Recent Action History"]
        
        for action in recent_actions:
            action_type = action.get("type", "Unknown")
            action_desc = action.get("description", "")
            timestamp = action.get("timestamp", "")
            lines.append(f"- {timestamp}: {action_type} - {action_desc}")
        
        return "\n".join(lines)
    
    def _format_validation_request(self, context: AgentContext) -> str:
        """
        Format the validation request for the LLM prompt.
        
        Args:
            context: The agent context.
        
        Returns:
            Formatted validation request string.
        """
        # Extract world information
        world_state = context.world_state
        location = context.player_state.get("current_location", "Unknown")
        district = context.player_state.get("current_district", "Unknown")
        time_of_day = world_state.get("time_of_day", "Unknown") if world_state else "Unknown"
        weather = world_state.get("weather", "Clear") if world_state else "Clear"
        
        request_lines = [
            "## Action Validation Request",
            f"- Location: {location}, {district}",
            f"- Time: {time_of_day}",
            f"- Weather: {weather}",
            "",
            "### Player's Proposed Action",
            f"{context.player_input}",
            "",
            "Please validate this action against game rules and provide your assessment."
        ]
        
        return "\n".join(request_lines)
    
    def process(self, context: AgentContext) -> AgentResponse:
        """
        Process a validation request with the rule checker agent.
        
        Args:
            context: The agent context.
        
        Returns:
            The agent response.
        """
        logger.info("Processing request with RuleChecker agent")
        
        # Use the base process method
        response = super().process(context)
        
        # Extract validation result
        validation_result = self._parse_validation_result(response.content)
        
        # Add the validation result to the response metadata
        if validation_result:
            response.metadata["validation_result"] = validation_result
        
        # If this is a loot validation, track the entity if approved
        if "loot" in context.player_input.lower() and validation_result.get("is_valid", False):
            self._track_looted_entity(context)
        
        # Add the action to history
        self._add_to_action_history(context, validation_result)
        
        return response
    
    def _parse_validation_result(self, content: str) -> Dict[str, Any]:
        """Parse the validation result from the LLM response."""
        result = {
            "is_valid": False,
            "reason": "Unspecified rule violation",  # Default reason if not extracted
            "suggestions": []
        }
        
        # Log the content length for debugging
        logger.debug(f"Parsing validation result from content of length {len(content)}")
        
        # Extract sections using the exact markers
        decision_match = re.search(r'<DECISION>\s*(.+?)\s*</DECISION>', content, re.DOTALL)
        explanation_match = re.search(r'<EXPLANATION>\s*(.+?)\s*</EXPLANATION>', content, re.DOTALL)
        suggestions_match = re.search(r'<SUGGESTIONS>\s*(.+?)\s*</SUGGESTIONS>', content, re.DOTALL)
        
        # Process decision
        if decision_match:
            decision_text = decision_match.group(1).strip().upper()
            logger.debug(f"Found decision: {decision_text}")
            
            if 'YES' in decision_text:
                result["is_valid"] = True
                result["reason"] = None  # No reason needed for valid actions
            elif 'NO' in decision_text:
                result["is_valid"] = False
                # Reason will be extracted from explanation
            else:
                # This is a common issue with the LLM where it says the action is valid but marks it as NO
                # Check if the explanation actually contains a positive validation
                if explanation_match:
                    explanation_text = explanation_match.group(1).strip()
                    if explanation_text and any(positive_term in explanation_text.lower() for positive_term in 
                                              ['valid', 'allowed', 'acceptable', 'is valid', 'can be performed']):
                        logger.warning(f"Decision says NO but explanation indicates validity. Setting to valid.")
                        result["is_valid"] = True
                        result["reason"] = None
                    else:
                        logger.warning(f"Unclear decision text: '{decision_text}'")
                else:
                    logger.warning(f"Unclear decision text: '{decision_text}'")
        else:
            logger.warning("No <DECISION> section found in response")
        
        # Process explanation (reason for decision)
        if explanation_match:
            explanation_text = explanation_match.group(1).strip()
            logger.debug(f"Found explanation: {explanation_text[:100]}...")
            
            # Special case: explanation contradicts decision
            is_positive_explanation = any(positive_term in explanation_text.lower() for positive_term in 
                                         ['valid', 'allowed', 'acceptable', 'is valid', 'can be performed'])
            
            # If explanation says it's valid but decision says it's not, override
            if is_positive_explanation and not result["is_valid"]:
                logger.warning("Explanation contradicts decision: Explanation says action is valid, overriding decision")
                result["is_valid"] = True
                result["reason"] = None
            # If explanation says it's invalid but decision says it's valid, don't override
            # (This is a safety feature - we prefer to allow actions on ambiguity)
            
            # For invalid actions, set the reason
            if not result["is_valid"] and explanation_text:  
                result["reason"] = explanation_text
        else:
            logger.warning("No <EXPLANATION> section found in response")
        
        # Process suggestions
        if suggestions_match:
            suggestions_text = suggestions_match.group(1).strip()
            logger.debug(f"Found suggestions: {suggestions_text[:100]}...")
            
            if suggestions_text:
                # Split by lines or sentences to get individual suggestions
                suggestions_lines = re.split(r'[\n\r]+|(?<=\.)\s+', suggestions_text)
                result["suggestions"] = [s.strip() for s in suggestions_lines if s.strip()]
        else:
            logger.warning("No <SUGGESTIONS> section found in response")
        
        # Ensure we have a reason for invalid actions
        if not result["is_valid"] and (not result["reason"] or result["reason"] == "Unspecified rule violation"):
            # If explanation was missing but we have suggestions, use first suggestion as reason
            if result["suggestions"]:
                result["reason"] = f"Action invalid. {result['suggestions'][0]}"
                logger.debug(f"Using first suggestion as reason: {result['reason']}")
        
        return result
    
    def _track_looted_entity(self, context: AgentContext) -> None:
        """
        Track an entity that has been looted to prevent double-looting.
        
        Args:
            context: The agent context with the entity being looted.
        """
        # Extract entity information from input
        player_input = context.player_input.lower()
        
        # Create a simple hash of the input and location to identify the entity
        location = context.player_state.get("current_location", "") if context.player_state else ""
        district = context.player_state.get("current_district", "") if context.player_state else ""
        
        entity_hash = hashlib.md5(f"{player_input}|{location}|{district}".encode()).hexdigest()
        
        # Add to the looted entities set
        self._looted_entities.add(entity_hash)
        logger.debug(f"Tracked looted entity: {entity_hash}")
    
    def _add_to_action_history(self, context: AgentContext, validation_result: Dict[str, Any]) -> None:
        """
        Add an action to the history for anti-cheat tracking.
        
        Args:
            context: The agent context.
            validation_result: The validation result.
        """
        import datetime
        
        action_entry = {
            "type": self._determine_action_type(context.player_input),
            "description": context.player_input,
            "location": context.player_state.get("current_location", "") if context.player_state else "",
            "district": context.player_state.get("current_district", "") if context.player_state else "",
            "is_valid": validation_result.get("is_valid", False),
            "reason": validation_result.get("reason"),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Add to action history
        self._action_history.append(action_entry)
        
        # Limit history size
        if len(self._action_history) > 100:
            self._action_history = self._action_history[-100:]
    
    def _determine_action_type(self, input_text: str) -> str:
        """
        Determine the type of action from the input text.
        
        Args:
            input_text: The player input text.
        
        Returns:
            The action type.
        """
        input_lower = input_text.lower()
        
        if any(word in input_lower for word in ["attack", "fight", "hit", "strike", "combat"]):
            return "COMBAT"
        elif any(word in input_lower for word in ["loot", "take", "grab", "steal", "pick up"]):
            return "LOOT"
        elif any(word in input_lower for word in ["cast", "spell", "magic"]):
            return "MAGIC"
        elif any(word in input_lower for word in ["talk", "speak", "ask", "tell"]):
            return "DIALOGUE"
        elif any(word in input_lower for word in ["move", "go", "walk", "run", "travel"]):
            return "MOVEMENT"
        elif any(word in input_lower for word in ["use", "activate", "trigger"]):
            return "USE"
        elif any(word in input_lower for word in ["search", "look", "examine", "inspect"]):
            return "OBSERVATION"
        else:
            return "OTHER"
    
    def supports_command(self, command: str) -> bool:
        """
        Check if the rule checker agent supports a specific command.
        
        Args:
            command: The command name.
        
        Returns:
            True if the agent supports the command, False otherwise.
        """
        return command in self.SUPPORTED_COMMANDS
    
    def validate_action(self, context: AgentContext) -> Tuple[bool, Optional[str]]:
        """
        Validate a player action against game rules.
        
        Args:
            context: The agent context.
        
        Returns:
            A tuple of (is_valid, reason) where reason is None if valid.
        """
        # Log the action being validated
        logger.info(f"Validating action: {context.player_input[:100]}...")
        
        # Process the validation request
        response = self.process(context)
        
        # Get the validation result
        validation_result = response.metadata.get("validation_result", {})
        is_valid = validation_result.get("is_valid", False)
        reason = validation_result.get("reason")
        
        # Log more details about the validation result
        logger.info(f"Validation result: valid={is_valid}, reason={reason}")
        
        # If it's invalid but reason is None, provide a default
        if not is_valid and reason is None:
            reason = "Unspecified rule violation - rule checker could not determine specific reason"
            logger.warning(f"Rule checker returned invalid action with no reason. Using default: {reason}")
        
        # Debug log the full validation response if the result seems problematic
        if not is_valid or reason is None:
            # Log first 500 chars of the response content for debugging
            logger.debug(f"Rule checker response content (excerpt): {response.content[:500]}...")
        
        return is_valid, reason
    
    def is_already_looted(self, entity_description: str, location: str, district: str) -> bool:
        """
        Check if an entity has already been looted.
        
        Args:
            entity_description: Description of the entity.
            location: The location of the entity.
            district: The district within the location.
        
        Returns:
            True if the entity has already been looted, False otherwise.
        """
        # Create a hash of the entity
        entity_hash = hashlib.md5(f"{entity_description.lower()}|{location}|{district}".encode()).hexdigest()
        
        # Check if the entity is in the looted entities set
        return entity_hash in self._looted_entities
        
    def perform_skill_check(self, stat_type: str, difficulty: int, context: str = "") -> Dict[str, Any]:
        """
        Perform a skill check against a character stat.
        
        Args:
            stat_type: The type of stat to check (e.g., STR, DEX, INT)
            difficulty: The difficulty class (DC) of the check
            context: Optional description of the check context
            
        Returns:
            Dictionary with skill check results
        """
        from core.base.state import get_state_manager
        from core.stats.stats_base import StatType, DerivedStatType
        
        # Get the stats manager from the state manager
        state_manager = get_state_manager()
        if not state_manager or not state_manager.stats_manager:
            logger.warning("Stats manager not available for skill check")
            return {
                "success": False,
                "error": "Stats system not available"
            }
            
        stats_manager = state_manager.stats_manager
        
        try:
            # Convert string stat type to enum if needed
            if isinstance(stat_type, str):
                # Try to match with primary stat first
                try:
                    stat_enum = StatType.from_string(stat_type)
                except ValueError:
                    # Then try derived stat
                    try:
                        stat_enum = DerivedStatType.from_string(stat_type)
                    except ValueError:
                        logger.warning(f"Unknown stat type: {stat_type}")
                        return {
                            "success": False,
                            "error": f"Unknown stat type: {stat_type}"
                        }
            else:
                stat_enum = stat_type
                
            # Perform the skill check
            result = stats_manager.perform_skill_check(
                stat_type=stat_enum,
                difficulty=difficulty
            )
            
            # Return the result as a dictionary
            return {
                "success": True,
                "result": result,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"Error performing skill check: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Convenience function
def get_rule_checker_agent() -> RuleCheckerAgent:
    """Get the rule checker agent instance."""
    return RuleCheckerAgent()


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Create the rule checker agent
    rule_checker = get_rule_checker_agent()
    
    # Create a test context
    context = AgentContext(
        game_state={},
        player_state={
            "name": "Thorn",
            "race": "Elf",
            "path": "Ranger",
            "background": "Outcast",
            "current_location": "Whispering Woods",
            "current_district": "Ancient Grove",
            "strength": 12,
            "agility": 15,
            "constitution": 10,
            "intelligence": 13,
            "wisdom": 14,
            "charisma": 9,
            "health": 80,
            "max_health": 100,
            "stamina": 60,
            "max_stamina": 100,
            "mana": 90,
            "max_mana": 100
        },
        world_state={
            "time_of_day": "evening",
            "weather": "Light Rain",
            "is_day": False
        },
        player_input="I want to lift the boulder that's blocking the entrance to the cave.",
        conversation_history=[],
        relevant_memories=[],
        additional_context={
            "inventory": {
                "current_weight": 25,
                "weight_limit": 50
            }
        }
    )
    
    # Process the request
    response = rule_checker.process(context)
    
    # Print the response
    print(f"Response: {response.content}")
    print(f"Validation result: {response.metadata.get('validation_result')}")