#!/usr/bin/env python3
"""
Narrator agent for generating game narrative and identifying actions.

This module provides a NarratorAgent class that generates narrative
text based on player input, game state, and context information.
It also identifies potential skill checks or state changes requested
by the player's natural language input and outputs them in a
structured format.
"""

import re
import json
from typing import Dict, List, Optional

from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext # Keep AgentContext, remove AgentResponse if not used
from core.interaction.structured_requests import AgentOutput

# Get the module logger
logger = get_logger("AGENT")

class NarratorAgent(BaseAgent):
    """
    Narrator agent for generating game narrative and identifying actions.

    This agent generates narrative text based on player input, game state,
    and context information. When the game mode is NARRATIVE, it analyzes
    player input to identify implicit requests for skill checks or state
    changes, outputting these alongside the narrative in a structured format.
    """
    
    # Define the commands that this agent supports
    SUPPORTED_COMMANDS = [
        "DESCRIBE_LOCATION",
        "NARRATE_ACTION",
        "DESCRIBE_NPC",
        "NARRATE_DIALOGUE",
        "DESCRIBE_ITEM",
        "NARRATE_DISCOVERY"
    ]

    def __init__(self):
        """Initialize the narrator agent."""
        super().__init__("Narrator")
        logger.info(f"NarratorAgent initialized with {len(self.SUPPORTED_COMMANDS)} supported commands: {', '.join(self.SUPPORTED_COMMANDS)}")
        
    def reset(self) -> None:
        """No persistent state to reset, provided for interface consistency."""
        logger.info("Narrator agent reset (no state)")

    def _generate_system_prompt(self, context: AgentContext) -> str:
        """
        Generate the system prompt for the narrator agent.
        """
        # --- Context Extraction (GameContext-aware) ---
        player_name = context.player_state.get("name", "Unknown")
        player_race = context.player_state.get("race", "Human")
        player_path = context.player_state.get("path", "Wanderer")
        player_background = context.player_state.get("background", "Commoner")
        player_id = context.player_state.get("id", "player")

        # Prefer GameContext location fields when present
        gc_loc = {}
        try:
            gc_loc = (context.additional_context.get('location') or {}) if isinstance(context.additional_context, dict) else {}
        except Exception:
            gc_loc = {}
        player_location = gc_loc.get("name") or context.player_state.get("current_location", "Unknown")
        # Use venue or region as a secondary descriptor
        player_district = gc_loc.get("venue") or context.additional_context.get("region") if isinstance(context.additional_context, dict) else None
        if not player_district:
            player_district = context.player_state.get("current_district", "Unknown")

        world_time = context.world_state.get("time_of_day", "Unknown")
        # Weather may be str or dict type in world_state; normalize to string
        _w = context.world_state.get("weather", None)
        world_weather = _w.get('type') if isinstance(_w, dict) else (_w or "Clear")
        is_day = context.world_state.get("is_day", True)
        day_night = "day" if is_day else "night"
        # Internal exact time (do not reveal to player)
        exact_game_time = context.world_state.get("exact_game_time", "Unknown")

        current_mode = context.game_state.get("mode", "NARRATIVE")
        mode_display = current_mode if isinstance(current_mode, str) else \
                    current_mode.name if hasattr(current_mode, 'name') else "NARRATIVE"

        # --- Stamina Regeneration Note ---
        stamina_note_for_prompt = ""
        if context.additional_context and "player_stamina_status" in context.additional_context:
            stamina_note_for_prompt = f"\n        - System Note: {context.additional_context['player_stamina_status']}"

        # --- Refined Prompt with JSON Emphasis and Semantic Spawning ---
        system_prompt = f"""You are the Narrator, an AI game master for a text-based RPG. Your role is to create immersive narrative based on player input and game state.

        ## Current Game State
        - Player ID: {player_id}
        - Player: {player_name} the {player_race} {player_path} ({player_background})
        - Location: {player_location}, {player_district}
        - Time: {world_time} ({day_night})
        - Weather: {world_weather}
        - Current Interaction Mode: {mode_display}{stamina_note_for_prompt}
        - Exact Game Time (internal): {exact_game_time}
        - Calendar (internal): {context.world_state.get('calendar', '')}

        ## Your Responsibilities
        1. Generate vivid narrative responses to player actions.
        2. Maintain world lore and character consistency.
        3. **CRITICAL (Especially in NARRATIVE Mode):** Analyze the player's natural language input. Identify actions implying skill checks (e.g., "I try to pick the lock"), state changes (e.g., "I drink the potion"), or **MODE TRANSITIONS** (e.g., "I attack the guard", "I want to trade").
        4. **Output JSON:** Your *ENTIRE* response MUST be a single, valid JSON object adhering *exactly* to the `AgentOutput` structure below. NO extra text, explanations, or markdown formatting outside the JSON.

        ## Required Output Format (JSON Object Only)
        ```json
        {{
        "narrative": "Your descriptive text about the situation and the player's attempted action goes here. Describe the lead-up to any requested checks or state changes.",
        "time_passage": "1m",
        "requests": [
            {{
            "action": "request_skill_check",
            "actor_id": "{{player_id}}",
            "skill_name": "LOCKPICKING",
            "stat_name": "DEXTERITY",
            "target_actor_id": null,
            "difficulty_class": 14,
            "modifiers": {{}},
            "context": "Player attempting to pick the chest lock."
            }},
            {{
            "action": "request_state_change",
            "target_entity": "{{player_id}}",
            "attribute": "stamina",
            "change_type": "add",
            "value": 5,
            "context": "Player recovered some stamina after a brief rest."
            }},
            {{
            "action": "request_mode_transition",
            "target_mode": "COMBAT",
            "origin_mode": "NARRATIVE",
            "reason": "Player initiated attack on guard.",
            "enemies": [
              {{
                "name": "City Guard",
                "description": "A well-armored watchman.",
                "keywords": ["humanoid", "soldier", "normal"]
              }}
            ]
            }},
            {{
            "action": "request_state_change",
            "target_entity": "{{player_id}}",
            "attribute": "inventory",
            "change_type": "add",
            "item_template": "test_apple",
            "quantity": 1,
            "context": "Player picks up an apple and puts it in the backpack."
            }},
            {{
            "action": "request_data_retrieval",
            "data_type": "inventory"
            }},
            {{
            "action": "request_quest_update",
            "quest_id": "the-first-exchange",
            "objective_id": "step-2",
            "new_status": "completed",
            "confidence": 0.85,
            "evidence": [
              {{ "type": "flag", "key": "elder.message_deciphered" }},
              {{ "type": "dialogue", "id": "elder_03_line_17" }}
            ]
            }},
            {{
            "action": "request_quest_status",
            "quest_id": "the-first-exchange",
            "new_status": "abandoned",
            "confidence": 0.9,
            "evidence": [ {{ "type": "flag", "key": "player.abandon_confirmed" }} ]
            }}
        ]
        }}
        ```
        
        Evidence items should reference concrete signals (flags, dialogue ids, interaction ids). Do not propose quest status changes that contradict objective-level logic; prefer proposing objective updates. Never invent quest or objective IDs.

        ## Guidelines
        - **Time Passage (MANDATORY):** Always include a compact `time_passage` value (e.g., "30s", "1m", "2h", "1d") representing the approximate time elapsed since the last user input. If uncertain, default to "1m". Do not omit this field.
        - **Time Disclosure Policy:** Do not reveal numeric clock times to the player. Use only named periods (dawn, morning, noon, afternoon, evening, sunset, night, deep night). The "Exact Game Time (internal)" is for reasoning only.
        - **NARRATIVE Mode Focus:** When mode is NARRATIVE, actively look for intents requiring skill checks, state changes, or mode transitions.
        - **Inventory Changes (CRITICAL):** When the player gives, offers, drops, leaves behind, discards, sacrifices, or consumes an item, include a `request_state_change` with `attribute: "inventory"`.
          • Prefer `template_id` if known; otherwise use `item_id` (when present) or `item_name`.
          • Use `change_type: "remove"` for removals; include `quantity`.
          • Example: {{"action":"request_state_change","target_entity":"{{player_id}}","attribute":"inventory","change_type":"remove","template_id":"ritual_dagger","quantity":1,"context":"Player offers the dagger to the Elder as part of the ritual."}}
        - **Stamina Regeneration (NARRATIVE Mode):** If the 'System Note' indicates player stamina is not full, evaluate if context (time passed, player actions) warrants regeneration. If yes, include a `request_state_change` for 'stamina' with a positive 'value' and narrate briefly (e.g., "You feel somewhat refreshed."). If not appropriate, omit this request.
        - **Mode Transitions:** If player input clearly initiates combat ("attack", "fight"), trade ("trade", "buy", "sell"), or social conflict ("confront", "intimidate"), YOU MUST include a `request_mode_transition` in the `requests` list.
        - **Combat Spawning (Simplified):** When requesting COMBAT, if new enemies are involved, provide an `enemies` list.
          * For each enemy, provide a `name` (display name, e.g., "Rabid Wolf", "Bandit Leader").
          * Provide `keywords` as a list of strings describing the enemy's nature and difficulty.
          * **Keywords:** Include the type (e.g., "beast", "humanoid", "undead"), the difficulty/role (e.g., "easy", "normal", "hard", "boss"), and any specific traits (e.g., "wolf", "archer", "fire").
          * Do NOT invent internal IDs. Just describe the enemy semantically.
        - **Skill Checks:** Identify verbs implying effort/uncertainty ("try", "attempt", "search", "sneak", "persuade"). Infer the skill (e.g., `LOCKPICKING`, `PERCEPTION`, `STEALTH`, `PERSUASION`). Use `skill_name` from the available skill list.
        - **State Changes:** Identify direct actions ("drink potion", "give item", "pull lever"). Infer target, attribute, change type, value.
        - **Data Retrieval:** Only use `request_data_retrieval` if the player *explicitly asks* for their stats, inventory, quests, etc. Do not guess. If used, the `narrative` should usually be empty or very brief (e.g., "Checking your inventory...").
        - **Narrative First:** Always provide narrative, describing the attempt or situation leading to requests. Do not determine success/failure in narrative.
        - **Environment:** Incorporate environmental tags (from context, if provided) into descriptions and consider them for checks (e.g., taking cover).
        - **Consistency & Fairness:** Maintain world/character consistency. Be descriptive but reasonably concise. Avoid explicit/harmful content.

        ### Final Checklist (before you output JSON)
        1) Did the input imply a skill check? If yes, add `request_skill_check`.
        2) Did the input imply an inventory change? If yes, add `request_state_change` with `attribute: "inventory"`.
        3) Did the input imply a mode transition (combat/trade/social)? If yes, add `request_mode_transition`.
        4) Did the player explicitly ask to list stats/inventory/quests? If yes, add `request_data_retrieval`.
        5) Keep the narrative concise (2–5 sentences) and complete the immediate outcome.

        Respond to the player's input by generating the required JSON `AgentOutput` object ONLY.
        """
        return system_prompt
    
    def _format_memories(self, context: AgentContext) -> str:
        """
        Format memory context specifically for the narrator.

        Args:
            context: The agent context.

        Returns:
            Formatted memory context string.
        """
        if not context.relevant_memories or not self._settings.get("include_memories", True):
            return ""

        memory_lines = ["## Relevant Background Information"]

        # Categorize memories
        location_memories = []
        character_memories = []
        quest_memories = []
        other_memories = []

        # Get the max number of entries to include
        max_entries = self._settings.get("max_memory_entries", 10)

        # Sort memories by importance
        sorted_memories = sorted(
            context.relevant_memories[:max_entries],
            key=lambda m: m.get("importance", 0),
            reverse=True
        )

        # Categorize and format each memory entry
        for memory in sorted_memories:
            content = memory.get("content", "")
            memory_type = memory.get("type", "general")

            formatted_memory = f"- {content}"

            if memory_type == "location":
                location_memories.append(formatted_memory)
            elif memory_type == "character":
                character_memories.append(formatted_memory)
            elif memory_type == "quest":
                quest_memories.append(formatted_memory)
            else:
                other_memories.append(formatted_memory)

        # Add categorized memories to the output
        if location_memories:
            memory_lines.append("### Locations")
            memory_lines.extend(location_memories)

        if character_memories:
            memory_lines.append("### Characters")
            memory_lines.extend(character_memories)

        if quest_memories:
            memory_lines.append("### Quests")
            memory_lines.extend(quest_memories)

        if other_memories:
            memory_lines.append("### Other Information")
            memory_lines.extend(other_memories)

        return "\n".join(memory_lines)

    def _format_character_stats(self, context: AgentContext) -> str:
        """
        Format character stats information for the LLM prompt.

        Args:
            context: The agent context.

        Returns:
            Formatted character stats string.
        """
        stats = context.additional_context.get("character_stats", {}) if context.additional_context else {}
        if not stats:
            return ""

        lines = ["## Character Stats"]

        # Check for error message
        if "error" in stats:
            lines.append(f"Error retrieving character stats: {stats['error']}")
            return "\n".join(lines)

        # Format character info
        character = stats.get("character", {})
        if character:
            lines.append("### Character Information")
            lines.append(f"- Name: {character.get('name', 'Unknown')}")
            lines.append(f"- Race: {character.get('race', 'Unknown')}")
            lines.append(f"- Class/Path: {character.get('path', 'Unknown')}")
            lines.append(f"- Background: {character.get('background', 'Unknown')}")
            lines.append(f"- Level: {character.get('level', 1)}")
            lines.append(f"- Experience: {character.get('experience', 0)}/{character.get('experience_to_next_level', 100)}")

        # Format primary stats
        primary_stats = stats.get("primary_stats", {})
        if primary_stats:
            lines.append("### Primary Stats")
            for stat_name, stat_info in primary_stats.items():
                value = stat_info.get("value", 0)
                base = stat_info.get("base", 0)
                modifier = stat_info.get("modifier", 0)

                mod_str = f"+{modifier}" if modifier > 0 else str(modifier) if modifier < 0 else ""
                base_str = f" (Base: {base}{f', Mod: {mod_str}' if mod_str else ''})" if base != value else ""

                lines.append(f"- {stat_name}: {value}{base_str}")

        # Format derived stats
        derived_stats = stats.get("derived_stats", {})
        if derived_stats:
            lines.append("### Derived Stats")
            for stat_name, stat_info in derived_stats.items():
                value = stat_info.get("value", 0)
                lines.append(f"- {stat_name}: {value}")

        # Format skills (if available)
        skills = stats.get("skills", {})
        if skills:
            lines.append("### Skills")
            for skill_name, skill_info in skills.items():
                 value = skill_info.get("value", 0)
                 lines.append(f"- {skill_name.title()}: {value}")


        # Format active modifiers
        active_modifiers = stats.get("active_modifiers", [])
        if active_modifiers:
            lines.append("### Active Modifiers")
            for mod in active_modifiers:
                stat = mod.get("stat", "Unknown")
                value = mod.get("value", 0)
                source = mod.get("source", "Unknown")
                duration = mod.get("duration", "")
                is_permanent = mod.get("is_permanent", False)

                duration_str = "Permanent" if is_permanent else f"Duration: {duration}s" if duration else ""
                lines.append(f"- {stat} {value:+g} from {source} ({duration_str})")

        return "\n".join(lines)

    def _format_quests(self, context: AgentContext) -> str:
        """
        Format quest information for the LLM prompt.

        Args:
            context: The agent context.

        Returns:
            Formatted quest information string.
        """
        quests = context.additional_context.get("quests", {}) if context.additional_context else {}
        if not quests:
            return ""

        lines = ["## Quests"]

        # Check for error message
        if "error" in quests:
            lines.append(f"Error retrieving quest data: {quests['error']}")
            return "\n".join(lines)

        # Format active quests
        active_quests = quests.get("active_quests", [])
        lines.append("### Active Quests")
        if not active_quests:
            lines.append("- No active quests")
        else:
            for quest in active_quests:
                if isinstance(quest, dict):
                    quest_name = quest.get("title") or quest.get("name", "Unknown Quest")
                    quest_desc = quest.get("description", "")
                    quest_status = quest.get("status", "In Progress")
                    lines.append(f"- {quest_name} ({quest_status})")
                    if quest_desc:
                        lines.append(f"  {quest_desc}")
                else:
                    lines.append(f"- {quest}")

        # Format completed quests
        completed_quests = quests.get("completed_quests", [])
        lines.append("\n### Completed Quests")
        if not completed_quests:
            lines.append("- No completed quests")
        else:
            for quest in completed_quests:
                if isinstance(quest, dict):
                    quest_name = quest.get("title") or quest.get("name", "Unknown Quest")
                    lines.append(f"- {quest_name}")
                else:
                    lines.append(f"- {quest}")

        # Format failed quests
        failed_quests = quests.get("failed_quests", [])
        lines.append("\n### Failed Quests")
        if not failed_quests:
            lines.append("- No failed quests")
        else:
            for quest in failed_quests:
                if isinstance(quest, dict):
                    quest_name = quest.get("title") or quest.get("name", "Unknown Quest")
                    lines.append(f"- {quest_name}")
                else:
                    lines.append(f"- {quest}")

        return "\n".join(lines)

    def _format_location_info(self, context: AgentContext) -> str:
        """
        Format location information for the LLM prompt.

        Args:
            context: The agent context.

        Returns:
            Formatted location information string.
        """
        # Prefer a compact view assembled from GameContext/ContextBuilder fields
        # Accept either 'location_info' blob or fallback to additional_context/world_state
        location_info = context.additional_context.get("location_info", {}) if context.additional_context else {}
        if not location_info and isinstance(context.additional_context, dict):
            try:
                loc = context.additional_context.get('location') or {}
                location_info = {
                    'current_location': loc.get('name'),
                    'current_district': loc.get('venue') or context.additional_context.get('region'),
                    'time_of_day': context.additional_context.get('time_of_day') or context.world_state.get('time_of_day'),
                    'weather': (context.additional_context.get('weather', {}) or {}).get('type') if isinstance(context.additional_context.get('weather'), dict) else context.world_state.get('weather'),
                    'is_day': context.world_state.get('is_day', True),
                }
            except Exception:
                location_info = {}
        if not location_info:
            return ""

        lines = ["## Current Location & Environment"]

        # Check for error message
        if "error" in location_info:
            lines.append(f"Error retrieving location information: {location_info['error']}")
            return "\n".join(lines)

        # Basic location information
        loc_name = location_info.get('current_location')
        if loc_name is None: loc_name = "Unknown"
        lines.append(f"- Location: {loc_name}")
        
        district = location_info.get('current_district')
        if district is None: district = "Unknown"
        lines.append(f"- District/Area: {district}")

        # Time and weather information
        # Format game time
        game_time = location_info.get("game_time", {})
        if game_time:
            formatted_time = game_time.get("formatted_time", "Unknown time")
            day_name = game_time.get("day_name", "")
            time_str = formatted_time
            if day_name:
                time_str = f"{day_name}, {time_str}"
            lines.append(f"- Time: {time_str}")

        # Weather and time of day
        lines.append(f"- Time of Day: {location_info.get('time_of_day', 'Unknown')}")
        lines.append(f"- Weather: {location_info.get('weather', 'Unknown')}")
        lines.append(f"- Daylight: {'Day' if location_info.get('is_day', True) else 'Night'}")

        # Add nearby interactables/entities if available
        nearby = location_info.get("nearby_entities", [])
        if nearby:
            lines.append("### Nearby")
            for entity in nearby:
                 lines.append(f"- {entity.get('name', 'Unknown Entity')} ({entity.get('type', 'object')})")

        # Add Present NPCs from ContextBuilder ---
        # This data comes from context['present_npcs'] injected by ContextBuilder
        present_npcs = context.additional_context.get("present_npcs", []) if context.additional_context else []
        if present_npcs:
            lines.append("### NPCs Present (Visible)")
            for npc_desc in present_npcs:
                lines.append(f"- {npc_desc}")

        return "\n".join(lines)

    def _format_inventory(self, context: AgentContext) -> str:
        """
        Format inventory information for the LLM prompt.

        Args:
            context: The agent context.

        Returns:
            Formatted inventory string.
        """
        inventory = context.additional_context.get("inventory", {}) if context.additional_context else {}
        if not inventory:
            return ""

        lines = ["## Current Inventory"]

        # Check for error message
        if "error" in inventory:
            lines.append(f"Error retrieving inventory data: {inventory['error']}")
            return "\n".join(lines)

        # Format equipped items
        equipped = inventory.get("equipped", {})
        if equipped:
            lines.append("### Equipped Items")
            if not equipped:
                lines.append("- Nothing equipped.")
            else:
                for slot, item in equipped.items():
                    if isinstance(item, dict):
                        item_name = item.get("name", "Unknown Item")
                        item_stats = item.get("stats", [])
                        stats_str = ", ".join(f"{stat['name']}: {stat['value']}" for stat in item_stats) if item_stats else ""
                        lines.append(f"- {slot.title()}: {item_name} {f'({stats_str})' if stats_str else ''}")
                    elif item: # Handle cases where it might be just the item name/ID
                         lines.append(f"- {slot.title()}: {item}")
                    # else: # Don't list empty slots explicitly unless needed
                    #    lines.append(f"- {slot.title()}: None")

        # Format backpack items
        backpack = inventory.get("backpack", [])
        lines.append("### Backpack")
        if not backpack:
            lines.append("- Backpack is empty.")
        else:
            # Group items by type
            items_by_type = {}
            for item in backpack:
                if isinstance(item, dict):
                    item_type = item.get("type", "Miscellaneous").title()
                    if item_type not in items_by_type:
                        items_by_type[item_type] = []
                    items_by_type[item_type].append(item)

            # Display items by type
            for item_type, items in items_by_type.items():
                lines.append(f"#### {item_type}")
                for item in items:
                    item_name = item.get("name", "Unknown Item")
                    item_rarity = item.get("rarity", "")
                    item_quantity = item.get("quantity", 1)
                    quantity_str = f" (x{item_quantity})" if item_quantity > 1 else ""
                    rarity_str = f" ({item_rarity})" if item_rarity else ""
                    lines.append(f"- {item_name}{quantity_str}{rarity_str}")

        # Format currency
        currency = inventory.get("currency", {})
        if currency:
            gold = currency.get("gold", 0)
            silver = currency.get("silver", 0)
            copper = currency.get("copper", 0)
            lines.append(f"### Currency: {gold}g {silver}s {copper}c")

        # Format inventory limits
        weight = inventory.get("weight", {})
        slots = inventory.get("slots", {})
        if weight or slots:
            lines.append("### Inventory Limits")
            if weight:
                current_weight = weight.get("current", 0)
                weight_limit = weight.get("limit", 0)
                lines.append(f"- Weight: {current_weight:.1f}/{weight_limit:.1f}")
            if slots:
                used_slots = slots.get("used", 0)
                slot_limit = slots.get("limit", 0)
                lines.append(f"- Slots: {used_slots}/{slot_limit}")

        return "\n".join(lines)


    def _prepare_messages(self, context: AgentContext) -> List[Dict[str, str]]:
        """
        Prepare the message list for the LLM request.
        """
        messages = []
        system_prompt = self._generate_system_prompt(context)
        messages.append({"role": "system", "content": system_prompt})
        # Verify time_passage directive presence in prompt
        try:
            directive_present = ("Time Passage (MANDATORY)" in system_prompt) or ("time_passage" in system_prompt)
            logger.info(f"[LLM_PROMPT_POLICY] time_passage_directive_present={directive_present}")
        except Exception:
            pass

        # Add conversation history
        history_messages = self._format_conversation_history(context)
        messages.extend(history_messages)

        # Prepare user message parts
        user_message_parts = []
        if context.context_summary: user_message_parts.append(f"## Summary\n{context.context_summary}")
        memory_context = self._format_memories(context)
        if memory_context: user_message_parts.append(memory_context)

        # Add formatted context data ONLY if specifically requested or highly relevant
        # Avoid overloading the prompt by default in Narrative mode unless needed
        # Inventory
        if "inventory" in context.player_input.lower():
             inventory_info = self._format_inventory(context)
             if inventory_info: user_message_parts.append(inventory_info)
        # Stats
        if any(kw in context.player_input.lower() for kw in ["stat", "skill", "ability", "can i"]):
             stats_info = self._format_character_stats(context)
             if stats_info: user_message_parts.append(stats_info)
        # Quests: include when user mentions quests, or when additional_context already includes quests
        if ("quest" in context.player_input.lower()) or (context.additional_context and context.additional_context.get("quests")):
             quests_info = self._format_quests(context)
             if quests_info: user_message_parts.append(quests_info)

        # Always add basic location info
        location_info = self._format_location_info(context)
        if location_info: user_message_parts.append(location_info)
        # Explicitly add environment tags
        environment_tags = context.additional_context.get("environment", []) if context.additional_context else []
        if environment_tags: user_message_parts.append(f"### Environment Tags: {', '.join(environment_tags)}")


        # Add the actual player input
        user_message_parts.append("## Player Input")
        user_message_parts.append(context.player_input)

        final_user_message = "\n\n".join(user_message_parts)
        messages.append({"role": "user", "content": final_user_message})

        logger.debug(f"Prepared messages for NarratorAgent:\nSystem Prompt Length: {len(system_prompt)}\nUser Message Length: {len(final_user_message)}")
        # logger.debug(f"Full User Message:\n{final_user_message}") # Uncomment for detailed debugging

        return messages

    def process(self, context: AgentContext) -> AgentOutput:
        """
        Process a request with the narrator agent, expecting JSON output.
        """
        mode = context.game_state.get("mode", "N/A")
        logger.info(f"Processing request with Narrator agent. Mode: {mode}, Intent: '{context.player_input[:50]}...'")

        messages = self._prepare_messages(context)
        agent_output: Optional[AgentOutput] = None

        try:
            # --- LLM Call ---
            effective_model = self._model or None
            llm_response = self._llm_manager.get_completion(
                messages=messages,
                provider_type=self._provider_type,
                model=effective_model,
                temperature=self._temperature,
                max_tokens=self._settings.get("max_tokens", 1500), # Use setting
                timeout=self._settings.get("timeout_seconds", 45) # Use setting
            )
            if not llm_response or not llm_response.content:
                raise ValueError("LLM returned empty content.")

            llm_response_content = llm_response.content.strip()
            logger.debug(f"Raw LLM Response (Narrator):\n```\n{llm_response_content}\n```")

            # --- Enhanced JSON Parsing ---
            parsed_output = None
            cleaned_response = llm_response_content
            
            # 1. Remove markdown fences
            cleaned_response = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned_response, flags=re.MULTILINE).strip()
            
            # 2. Extract JSON if embedded in text
            # Look for object {...} or list [...]
            json_match = re.search(r'({[\s\S]*})|(\[[\s\S]*\])', cleaned_response)
            
            extracted_json_str = None
            extracted_narrative = None
            
            if json_match:
                extracted_json_str = json_match.group(0)
                # If there is text BEFORE the JSON, treat it as narrative
                if json_match.start() > 0:
                    extracted_narrative = cleaned_response[:json_match.start()].strip()
            else:
                # Try parsing the whole thing
                extracted_json_str = cleaned_response

            try:
                parsed_data = json.loads(extracted_json_str)
                
                # --- FIX: Handle List vs Object ---
                # If LLM returned a list of requests [ {...} ], wrap it
                if isinstance(parsed_data, list):
                    logger.warning("Narrator returned JSON List instead of Object. Auto-wrapping.")
                    agent_output = {
                        "narrative": extracted_narrative if extracted_narrative else "Action processed.",
                        "requests": parsed_data
                    }
                elif isinstance(parsed_data, dict):
                    # Normal object path
                    # If narrative was outside JSON, prioritize it over JSON 'narrative' field if empty
                    if extracted_narrative and not parsed_data.get("narrative"):
                        parsed_data["narrative"] = extracted_narrative
                    
                    # Validate keys
                    agent_output = {
                        "narrative": parsed_data.get("narrative", extracted_narrative or "Action processed."),
                        "requests": parsed_data.get("requests", [])
                    }
                else:
                    raise ValueError("Parsed JSON was neither Dict nor List.")

                # Basic validation of request structures
                validated_requests = []
                for req in agent_output["requests"]:
                    if isinstance(req, dict) and "action" in req:
                        validated_requests.append(req)
                agent_output["requests"] = validated_requests
                
                logger.info(f"Narrator successfully parsed JSON. Requests: {len(validated_requests)}")

            except json.JSONDecodeError as e:
                logger.warning(f"Narrator: JSON decode failed; using raw text as narrative. Error: {e}")
                agent_output = {
                    "narrative": llm_response_content.strip(), # Fallback to full text
                    "requests": []
                }

        except Exception as e:
            # ... existing error handling ...
            logger.exception(f"Error during NarratorAgent processing: {e}")
            agent_output = {
                "narrative": f"[Narrator Error: {e}]",
                "requests": []
            }

        return agent_output

    def process(self, context: AgentContext) -> AgentOutput:
        """
        Process a request with the narrator agent.

        Calls the LLM, parses the expected JSON output, and returns it.

        Args:
            context: The agent context.

        Returns:
            An AgentOutput dictionary containing narrative and structured requests.
        """
        logger.info(f"Processing request with Narrator agent in mode: {context.game_state.get('mode', 'N/A')}")

        messages = self._prepare_messages(context)

        # --- LLM Call ---
        try:
            # Use the LLM manager from BaseAgent with proper parameters
            llm_response = self._llm_manager.get_completion(
                messages=messages,
                provider_type=self._provider_type,
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._settings.get("max_tokens", 1000),
                timeout=self._settings.get("timeout_seconds", 30)
            )
            if not llm_response or not llm_response.content:
                raise ValueError("LLM returned empty content.")
            llm_response_content = llm_response.content
            logger.debug(f"Raw LLM Response:\n{llm_response_content}")

            # --- Response Parsing ---
            # The LLM might return a mix of text and JSON, or just the JSON
            # We need to try multiple parsing strategies
            try:
                # First try: Look for JSON code block
                json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', llm_response_content, re.DOTALL)
                if json_match:
                    # Extract JSON from code block
                    cleaned_response = json_match.group(1).strip()
                    logger.debug(f"Found JSON in code block: {cleaned_response[:100]}...")
                else:
                    # Second try: See if the entire response is JSON
                    if llm_response_content.strip().startswith('{'):
                        cleaned_response = llm_response_content.strip()
                        logger.debug("Response appears to be raw JSON")
                    else:
                        # Third try: Look for JSON anywhere in the text
                        # More robust pattern that handles nested structures better
                        json_pattern = r'({\s*"narrative"\s*:.+?"requests"\s*:\s*\[.*?\]\s*})'
                        json_match = re.search(json_pattern, llm_response_content, re.DOTALL)
                        if json_match:
                            cleaned_response = json_match.group(1).strip()
                            logger.debug(f"Found JSON pattern in response: {cleaned_response[:100]}...")
                        else:
                            # Final fallback: Treat the whole text as narrative with no requests
                            logger.warning("No JSON found in response. Treating entire text as narrative.")
                            return {
                                "narrative": llm_response_content.strip(),
                                "requests": []
                            }
                
                # Parse the extracted JSON
                try:
                    # Log the cleaned response for debugging
                    logger.debug(f"Attempting to parse JSON: {cleaned_response[:100]}... (length: {len(cleaned_response)})")
                    parsed_output = json.loads(cleaned_response)
                    logger.debug("Successfully parsed JSON")
                except json.JSONDecodeError as json_err:
                    # One more attempt: Try to sanitize quotes and escape characters
                    sanitized_json = re.sub(r'(?<!\\)\\\'', '\'', cleaned_response)  # Fix escaped single quotes
                    sanitized_json = re.sub(r'(?<!\\)\\"', '"', sanitized_json)  # Fix escaped double quotes
                    parsed_output = json.loads(sanitized_json)

                # Validate basic structure
                if not isinstance(parsed_output, dict) or \
                "narrative" not in parsed_output or \
                "requests" not in parsed_output or \
                not isinstance(parsed_output["requests"], list):
                    raise ValueError("LLM response is not a valid AgentOutput JSON structure.")

                # Basic validation of request structures (can be expanded)
                validated_requests = []
                for req in parsed_output["requests"]:
                    if not isinstance(req, dict) or "action" not in req:
                        logger.warning(f"Skipping invalid request structure: {req}")
                        continue
                    # Add more specific validation per action type if needed
                    validated_requests.append(req)

                agent_output: AgentOutput = {
                    "narrative": parsed_output.get("narrative", "Error: Narrative missing from LLM response."),
                    "requests": validated_requests
                }

            except json.JSONDecodeError as e:
                logger.warning(f"Narrator: JSON decode failed; using raw text as narrative. Error: {e}")
                # Fallback: Treat the whole response as narrative, no requests
                agent_output: AgentOutput = {
                    "narrative": llm_response_content.strip(),
                    "requests": []
                }
            except ValueError as e:
                logger.warning(f"Narrator: Invalid AgentOutput structure; using raw text as narrative. Error: {e}")
                agent_output: AgentOutput = {
                    "narrative": (parsed_output.get('narrative', llm_response_content).strip() if isinstance(parsed_output, dict) else str(llm_response_content).strip()),
                    "requests": []
                }


        except Exception as e:
            logger.exception(f"Error during NarratorAgent processing or LLM call: {e}")
            agent_output: AgentOutput = {
                "narrative": f"[Narrator Error: An unexpected error occurred during processing: {e}]",
                "requests": []
            }

        # --- RuleChecker Integration Point (Placeholder) ---
        # In Phase B3, the core loop would take agent_output["requests"]
        # and pass them to the RuleCheckerAgent for validation before
        # executing skill checks or state changes.
        # Example:
        # validated_requests = self.rule_checker.validate(agent_output["requests"], context)
        # agent_output["requests"] = validated_requests
        logger.info(f"Narrator generated {len(agent_output['requests'])} requests.")
        # Log request types for debugging
        request_types = [req.get('action', 'unknown') for req in agent_output.get('requests', []) if isinstance(req, dict)]
        logger.info(f"Request types generated: {request_types}")
        if 'request_mode_transition' in request_types:
            mode_transitions = [req for req in agent_output.get('requests', []) if isinstance(req, dict) and req.get('action') == 'request_mode_transition']
            logger.info(f"Mode transition requests detected: {json.dumps(mode_transitions, indent=2)}")
        # logger.debug(f"Narrator Output: {agent_output}") # Be careful logging potentially large outputs

        return agent_output

    def supports_command(self, command: str) -> bool:
        """
        Check if this agent supports a specific command.
        Args: Command: The command name.
        Returns: True if the agent supports the command, False otherwise.
        """
        is_supported = command.upper() in self.SUPPORTED_COMMANDS
        logger.debug(f"NarratorAgent.supports_command check for '{command}': {is_supported}")
        return is_supported


# Convenience function
def get_narrator_agent() -> NarratorAgent:
    """Get the narrator agent instance."""
    # In a real app, LLM service would be injected here
    # For now, assume BaseAgent handles it or it's set elsewhere
    return NarratorAgent()
