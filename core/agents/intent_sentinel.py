"""
Intent Sentinel agent for classifying player input.
"""

from typing import Dict, List, Any, Optional
import json
import re

from core.agents.base_agent import BaseAgent, AgentContext
from core.utils.logging_config import get_logger

logger = get_logger("SENTINEL")

class IntentSentinelAgent(BaseAgent):
    """
    The Intent Sentinel is a fast, specialized agent that classifies player input
    to route it to the appropriate specialized agent or logic branch.
    """

    def __init__(self):
        super().__init__("IntentSentinel")
        # Low temperature for strict classification
        self._temperature = 0.0 

    def _generate_system_prompt(self, context: AgentContext) -> str:
        """
        Generate the system prompt for intent classification.
        """
        return (
            "You are the Intent Sentinel, a high-speed classifier for a text-based RPG. "
            "Your sole task is to analyze player input and classify it into EXACTLY ONE of the following categories:\n\n"
            "CATEGORIES:\n"
            "- ROLEPLAY: General conversation, description, movement, or ambiguous actions that require full narrative generation.\n"
            "- COMBAT: Direct intent to attack, initiate combat, or use offensive magic against a target.\n"
            "- LOOT: Intent to search a body, open a chest, pick a lock, or take items from the environment.\n"
            "- TRADE: Intent to buy, sell, or barter with an NPC.\n"
            "- SOCIAL: Intent to formally debate, intimidate, or negotiate in a specialized social challenge.\n"
            "- STATUS: Intent to check inventory, character stats, quest log, or journal.\n"
            "- TRAVEL: Intent to leave the current area, enter a building, or travel to a new district.\n\n"
            "RULES:\n"
            "1. Output MUST be a compact JSON object only.\n"
            "2. Include 'intent' (the category name), 'confidence' (0.0 to 1.0), and 'reason' (short string).\n"
            "3. Do NOT include any other text or markdown formatting.\n"
            "4. If ambiguous, default to ROLEPLAY.\n"
        )

    def classify(self, context: AgentContext) -> Dict[str, Any]:
        """
        Specialized process method for classification.
        Returns a dictionary with 'intent', 'confidence', and 'reason'.
        """
        logger.info(f"Classifying intent for: '{context.player_input[:50]}...'")
        
        # Call the base process method
        response = self.process(context)
        content = response.content.strip()
        
        # Attempt to parse JSON output
        try:
            # Look for JSON block
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                intent = data.get("intent", "ROLEPLAY").upper()
                confidence = float(data.get("confidence", 0.0))
                reason = data.get("reason", "N/A")
                
                logger.debug(f"Sentinel Decision: {intent} (Confidence: {confidence}) - {reason}")
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "reason": reason
                }
        except Exception as e:
            logger.error(f"Failed to parse Sentinel output: {content}. Error: {e}")
        
        # Default fallback if parsing fails or LLM misbehaves
        return {
            "intent": "ROLEPLAY",
            "confidence": 0.0,
            "reason": "Classification/Parsing Failure"
        }

    def supports_command(self, command: str) -> bool:
        """
        The Sentinel is triggered via internal logic, not player commands directly.
        """
        return False

# Global singleton or generator function
_instance = None

def get_intent_sentinel() -> IntentSentinelAgent:
    """Get or create the IntentSentinelAgent instance."""
    global _instance
    if _instance is None:
        _instance = IntentSentinelAgent()
    return _instance
