"""
Archivist agent for managing the persistent Codex/Journal.
"""

from typing import Dict, List

from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext

logger = get_logger("ARCHIVIST")

class ArchivistAgent(BaseAgent):
    """
    The Archivist is responsible for maintaining the Game Codex.
    It takes new narrative events and updates specific journal entries
    without losing previously established facts.
    """

    def __init__(self):
        super().__init__("Archivist")
        # Low temperature for factual consistency
        self._temperature = 0.1 

    def _generate_system_prompt(self, context: AgentContext) -> str:
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
        Specialized process method for updating specific entries.
        """
        # 1. Format the full recent history (Player + GM)
        # We take a generous amount of history to ensure context (e.g., last 10 turns)
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
        # We mock the context structure required by BaseAgent
        dummy_context = AgentContext(
            game_state={}, player_state={}, world_state={}, 
            player_input=user_prompt, conversation_history=[]
        )

        # 4. Call LLM
        response = self.process(dummy_context)
        
        # 5. Clean output
        return response.content.strip()

    def supports_command(self, command: str) -> bool:
        """
        Check if this agent supports a specific command.
        The Archivist is triggered via internal logic, not player commands directly.
        """
        return False