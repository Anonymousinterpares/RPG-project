#!/usr/bin/env python3
"""
Trade agent for handling buying, selling, and bartering interactions.
"""

import re
import json
import logging
from typing import List, Dict, Any

from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext
from core.interaction.structured_requests import AgentOutput, SkillCheckRequest, StateChangeRequest
from core.interaction.enums import InteractionMode

logger = get_logger("AGENT")

class TradeAgent(BaseAgent):
    """
    Agent responsible for managing trade interactions (buying, selling, bartering).

    It receives trade context (participants, inventories, current offers) and player input,
    generates narrative describing the trade negotiation, and identifies necessary skill checks
    (e.g., Appraise, Haggle/Barter) or state changes (transferring items/currency).
    """

    def __init__(self):
        """Initialize the trade agent."""
        super().__init__("Trade") # Use "Trade" as name for settings file trade.json

    def _generate_system_prompt(self, context: AgentContext) -> str:
        """
        Generate the system prompt for the trade agent.
        """
        player_info = context.additional_context.get("player_trade_info", {})
        partner_info = context.additional_context.get("trade_partner", {})

        player_id = context.player_state.get("id", "player") # Fallback if not in player_info
        player_currency = player_info.get("currency", "N/A")
        player_inv_str = ", ".join([f"{item.get('name', '?')} (Value: {item.get('value', 0)})" for item in player_info.get("inventory", [])]) or "Empty"

        trade_partner_id = partner_info.get("id", "unknown_merchant")
        trade_partner_name = partner_info.get("name", "Unknown Merchant")
        partner_currency = partner_info.get("currency", "N/A")
        partner_inv_str = ", ".join([f"{item.get('name', '?')} (Value: {item.get('value', 0)})" for item in partner_info.get("inventory", [])]) or "Empty"

        system_prompt = f"""You are the Trade AI facilitator for a text-based RPG. Your role is to narrate trading interactions (buying, selling, bartering) and interpret player actions within this context.

## Current Trade State
- Player: ID '{player_id}', Currency: {player_currency}
  - Inventory: {player_inv_str}
- Trade Partner: {trade_partner_name} (ID: {trade_partner_id}), Currency: {partner_currency}
  - Inventory: {partner_inv_str}

## Your Responsibilities
1.  **Narrate:** Describe the player's trade action, proposal, or inquiry based on their input (e.g., "You examine the sword closely...", "You offer 5 gold pieces for the potion.", "You try to haggle for a better price...").
2.  **Analyze Intent:** Understand the player's natural language input (e.g., "I want to buy the health potion", "I offer my old dagger for that shield", "How much for the map?", "Can you do 10 gold instead?", "I accept the deal", "What do you have for sale?", "I want to sell these pelts").
3.  **Identify Mechanics:** Determine if the player's action requires:
    *   **Skill Checks:** Primarily `BARTER` (associated with Charisma) for haggling/influencing prices. Use `APPRAISE` (associated with Intelligence) if the player explicitly tries to determine an item's value.
    *   **State Changes:** Although the final transaction (item/currency transfer) is usually handled by the game engine after an agreement, you should understand the *intent* behind buy/sell/offer actions.
4.  **Output JSON:** Format your entire response as a single JSON object adhering *exactly* to the `AgentOutput` structure defined below.

## Required Output Format (JSON)
```json
{{
  "narrative": "Your descriptive text about the trade interaction. Describe the item examination, the offer being made, the haggling attempt, or the agreement.",
  "requests": [
    // Optional: Include structured requests based on player intent.
    // --- Example 1: Barter Check ---
    // Triggered by inputs like "Can you do better?", "I offer 10 gold [when value is 15]", "I try to haggle".
    {{
      "request_type": "SkillCheckRequest", // Matches class name
      "entity_id": "{player_id}", // Who is performing the check
      "skill_name": "BARTER", // Use the BARTER skill for haggling
      "target_dc": 12, // Target DC determined by game logic (e.g., based on NPC disposition, offer difference) - provide a reasonable estimate if unsure
      "advantage": false,
      "disadvantage": false,
      "modifier": 0, // Any situational modifiers?
      "context": "Player attempting to haggle for a better price on [Item Name/Offer]."
    }},
    // --- Example 2: Appraise Check ---
    // Triggered by inputs like "What's this worth?", "Is this price fair?".
    // {{
    //   "request_type": "SkillCheckRequest",
    //   "entity_id": "{player_id}",
    //   "skill_name": "APPRAISE", // Use APPRAISE skill
    //   "target_dc": 10, // DC based on item rarity/complexity
    //   "advantage": false,
    //   "disadvantage": false,
    //   "modifier": 0,
    //   "context": "Player attempting to appraise the [Item Name]."
    // }},
    // --- Example 3: Transfer Item (State Change) ---
    // NOTE: The core loop usually handles this *after* an offer is accepted based on intent ("accept", "deal").
    // Only include this if the LLM *confidently* determines a final, agreed-upon transfer.
    // {{
    //   "request_type": "StateChangeRequest", // Matches class name
    //   "target_entity": "UNUSED_FOR_TRANSFER", // Not used directly for transfer_item attribute
    //   "attribute": "transfer_item",
    //   "value": {{ // Dictionary containing transfer details
    //     "item_id": "item_id_to_transfer", // Specific ID of the item
    //     "from_owner_id": "{trade_partner_id}", // ID of the entity giving the item
    //     "to_owner_id": "{player_id}" // ID of the entity receiving the item
    //   }},
    //   "context": "Item transferred as part of accepted trade."
    // }},
    // --- Example 4: Adjust Currency (State Change) ---
    // NOTE: Similar to item transfer, usually handled by core loop post-acceptance.
    // {{
    //   "request_type": "StateChangeRequest",
    //   "target_entity": "{player_id}", // ID of the entity whose currency is changing
    //   "attribute": "adjust_currency",
    //   "value": -50, // Amount to change (positive to add, negative to remove)
    //   "context": "Currency transferred as part of accepted trade."
    // }}
    // --- Focus ---
    // Your primary job is narrative + identifying necessary skill checks (BARTER/APPRAISE).
    // Let the game engine handle the mechanics of offer proposal, acceptance, and the resulting state changes based on player intent like 'accept' or specific offers like 'I offer X for Y'.
  ]
}}
```

## Guidelines
- **Narrate Clearly:** Describe the negotiation, item inspection, offers, counter-offers, inquiries ("What do you have?", "How much is...?").
- **Identify Intent:** Determine if the player is inquiring, offering ("I offer X for Y"), buying ("I want to buy Z"), selling ("I want to sell A"), accepting ("Deal", "I accept"), rejecting ("No thanks"), or haggling ("Can you do better?").
- **Infer Checks:** Request `BARTER` checks for haggling attempts. Request `APPRAISE` only if explicitly asked about value/fairness.
- **Use Context:** Refer to the player and partner inventories and currency provided in the state.
- **State Changes:** Generate `StateChangeRequest` for item/currency transfers *only if* you are certain the interaction represents a finalized, agreed transaction (less common, usually handled by the engine).
- **Safety:** Adhere to standard content safety guidelines.

Respond to the player's trade input by generating the JSON `AgentOutput` object.
"""
        return system_prompt

    def _format_trade_context(self, context: AgentContext) -> str:
        """ Formats the trade specific context """
        trade_context = context.additional_context.get("trade_context", {})
        if not trade_context:
            return ""

        lines = ["## Trade Situation"]
        participants = trade_context.get("participants", []) # Includes player and partner
        player_offer = trade_context.get("player_offer", {"items": [], "currency": 0})
        partner_offer = trade_context.get("partner_offer", {"items": [], "currency": 0})
        trade_partner_id = trade_context.get("trade_partner_id", "unknown_merchant")
        player_inventory = trade_context.get("player_inventory_summary", "Not available") # Expect summaries
        partner_inventory = trade_context.get("partner_inventory_summary", "Not available")

        # Format offers
        def format_offer(offer):
            items_str = ", ".join([f"{i.get('name', '?')} (x{i.get('quantity', 1)})" for i in offer.get('items', [])]) or "Nothing"
            curr = offer.get('currency', 0)
            # Basic currency assumption (copper) - needs refinement based on game system
            curr_str = f"{curr} copper" if curr else ""
            if items_str != "Nothing" and curr_str:
                return f"Items: {items_str}, Currency: {curr_str}"
            elif items_str != "Nothing":
                return f"Items: {items_str}"
            elif curr_str:
                return f"Currency: {curr_str}"
            else:
                return "Offer is empty"

        lines.append(f"- Trading With: {trade_partner_id}") # Assuming partner ID is known
        lines.append(f"- Player Offer: {format_offer(player_offer)}")
        lines.append(f"- Partner Offer: {format_offer(partner_offer)}")
        lines.append("### Player Inventory (Relevant for Trade)")
        lines.append(player_inventory) # Assumes pre-formatted summary
        lines.append("### Partner Inventory (Relevant for Trade)")
        lines.append(partner_inventory) # Assumes pre-formatted summary

        return "\n".join(lines)


    def _prepare_messages(self, context: AgentContext) -> List[Dict[str, str]]:
        """ Prepare messages, adding trade context. """
        messages = super()._prepare_messages(context) # Get base messages

        # Find the user message and prepend trade context
        for msg in reversed(messages):
            if msg["role"] == "user":
                trade_context_str = self._format_trade_context(context)
                if trade_context_str:
                     original_user_content = msg["content"]
                     input_marker = "## Player Input"
                     if input_marker in original_user_content:
                         parts = original_user_content.split(input_marker, 1)
                         msg["content"] = f"{parts[0]}{trade_context_str}\n\n{input_marker}{parts[1]}"
                     else:
                         msg["content"] = f"{trade_context_str}\n\n{original_user_content}"
                break
        return messages

    def process(self, context: AgentContext) -> AgentOutput:
        """
        Process a trade request.
        """
        logger.info(f"Processing request with Trade agent in mode: {context.game_state.get('mode', 'N/A')}")

        messages = self._prepare_messages(context)

        try:
            llm_response_content = self._llm_service.generate_response(messages)
            if not llm_response_content:
                 raise ValueError("LLM returned empty content.")
            logger.debug(f"Raw LLM Response (Trade):\n{llm_response_content}")

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
                logger.error(f"Failed to parse Trade LLM response as JSON: {e}\nRaw response: {llm_response_content}")
                agent_output: AgentOutput = {
                    "narrative": f"[Trade Error: Parse failed] {llm_response_content}",
                    "requests": []
                }
            except ValueError as e:
                 logger.error(f"Invalid AgentOutput structure from Trade LLM: {e}\nParsed: {parsed_output}")
                 agent_output: AgentOutput = {
                    "narrative": f"[Trade Error: Invalid structure] {parsed_output.get('narrative', llm_response_content)}",
                    "requests": []
                 }

        except Exception as e:
            logger.exception(f"Error during Trade processing: {e}")
            agent_output: AgentOutput = {
                "narrative": f"[Trade Error: Processing failed: {e}]",
                "requests": []
            }

        logger.info(f"Trade generated {len(agent_output['requests'])} requests.")
        return agent_output

    def supports_command(self, command: str) -> bool:
        return False # Handles interactions via natural language and structured requests

# Convenience function
def get_trade_agent() -> TradeAgent:
    return TradeAgent()