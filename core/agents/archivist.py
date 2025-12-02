"""
Archivist agent for managing the persistent Codex/Journal.
"""

from typing import Dict, List, Any

from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext

logger = get_logger("ARCHIVIST")

class ArchivistAgent(BaseAgent):
    """
    The Archivist is responsible for maintaining the Game Codex and Character Biography.
    It takes new narrative events and updates specific journal entries
    without losing previously established facts.
    """

    def __init__(self):
        super().__init__("Archivist")
        # Low temperature for factual consistency
        self._temperature = 0.1 

    def _generate_system_prompt(self, context: AgentContext) -> str:
        """
        Default system prompt for general Codex updates.
        """
        return (
            "You are the Archivist, the keeper of lore for a fantasy RPG. "
            "Your task is to maintain concise, encyclopedic entries for the game's Codex.\n"
            "You will receive:\n"
            "1. An Existing Entry (if any).\n"
            "2. Recent Game Events (narrative log).\n"
            "3. A Target Topic (e.g., a location or person).\n\n"
            "Your Goal: Synthesize the new information into the Existing Entry.\n"
            "Rules:\n"
            "- Do NOT delete established facts unless the new events explicitly contradict them (e.g., a destroyed city).\n"
            "- Add new details revealed in the Game Events.\n"
            "- Write in a neutral, scholarly, or diary style (consistent with the existing entry).\n"
            "- Keep it concise. Focus on lore, location details, and character traits.\n"
            "- Return ONLY the updated text for the entry."
        )

    def process_update(self, existing_entry: str, recent_history: List[Dict[str, str]], topic: str) -> str:
        """
        Specialized process method for updating specific Codex entries.
        """
        # 1. Format the full recent history (Player + GM)
        formatted_history = ""
        for msg in recent_history[-10:]: 
            role = msg.get('role', 'unknown').upper()
            content = msg.get('content', '')
            formatted_history += f"[{role}]: {content}\n"

        # 2. Build the specific prompt
        user_prompt = (
            f"### Target Topic: {topic}\n\n"
            f"### Existing Entry:\n{existing_entry if existing_entry else '(New Entry)'}\n\n"
            f"### Recent Game Events:\n{formatted_history}\n\n"
            f"### Instruction:\n"
            f"Rewrite the entry for '{topic}' incorporating relevant details from the Recent Game Events. "
            f"Output the full updated entry text only."
        )

        # 3. Create a temporary context for the BaseAgent
        dummy_context = AgentContext(
            game_state={}, player_state={}, world_state={}, 
            player_input=user_prompt, conversation_history=[]
        )

        # 4. Call LLM
        response = self.process(dummy_context)
        
        # 5. Clean output
        return response.content.strip()

    def process_character_update(self, existing_bio: str, existing_traits: List[str], recent_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Specialized process method for updating Character Biography and Traits.
        Returns a dictionary with 'biography' and 'traits'.
        """
        # 1. Format history
        formatted_history = ""
        for msg in recent_history[-15:]:  # Slightly longer context for character analysis
            role = msg.get('role', 'unknown').upper()
            content = msg.get('content', '')
            formatted_history += f"[{role}]: {content}\n"

        # 2. Custom System Prompt override for this specific call is handled via the specific user prompt instructions
        # because BaseAgent.process uses _generate_system_prompt. We can override the behavior by explicit instruction.
        
        traits_str = ", ".join(existing_traits) if existing_traits else "None"

        user_prompt = (
            f"### Task: Update Character Profile\n"
            f"Analyze the recent game events to see if the player character's biography or personality traits should evolve.\n\n"
            f"### Existing Biography:\n{existing_bio}\n\n"
            f"### Existing Traits:\n{traits_str}\n\n"
            f"### Recent Game Events:\n{formatted_history}\n\n"
            f"### Instructions:\n"
            f"1. Update the Biography to include major recent accomplishments or changes in status. Keep it narrative.\n"
            f"2. Update the Traits list if the player has demonstrated new personality quirks or significant shifts in alignment/behavior.\n"
            f"3. Return the result strictly as a JSON object with keys 'biography' (string) and 'traits' (list of strings).\n"
            f"4. If no significant changes occurred, return the existing data structure unchanged."
        )

        dummy_context = AgentContext(
            game_state={}, player_state={}, world_state={}, 
            player_input=user_prompt, conversation_history=[]
        )

        # We need to temporarily swap the system prompt logic or rely on the LLM obeying the user prompt.
        # Since BaseAgent is rigid, we rely on the strong user prompt instructions.
        
        response = self.process(dummy_context)
        
        # Parse JSON output
        import json
        import re
        
        content = response.content.strip()
        # Attempt to find JSON block
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                data = json.loads(json_str)
                return {
                    "biography": data.get("biography", existing_bio),
                    "traits": data.get("traits", existing_traits)
                }
            except Exception:
                logger.error("Failed to parse Character Update JSON.")
        
        return {"biography": existing_bio, "traits": existing_traits}

    def supports_command(self, command: str) -> bool:
        """
        Check if this agent supports a specific command.
        The Archivist is triggered via internal logic, not player commands directly.
        """
        return False