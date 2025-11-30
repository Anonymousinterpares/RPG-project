#!/usr/bin/env python3
"""
Context evaluator agent for analyzing game context.

This module provides a ContextEvaluatorAgent class that analyzes the current
game context, identifies relevant memories, calculates importance scores,
and suggests potential actions to the player.
"""

import re
from typing import Dict, List, Optional, Any, Tuple

from core.utils.logging_config import get_logger
from core.agents.base_agent import BaseAgent, AgentContext, AgentResponse

# Get the module logger
logger = get_logger("AGENT")

class ContextEvaluatorAgent(BaseAgent):
    """
    Context evaluator agent for analyzing game context.
    
    This agent analyzes the current game context, identifies relevant memories,
    calculates importance scores for different context elements, and generates
    summaries for use by other agents.
    """
    
    # Command types supported by the context evaluator
    SUPPORTED_COMMANDS = [
        "CONTEXT_SUMMARIZE", "MEMORY_EVALUATE", "SUGGEST_FOCUS", 
        "IMPORTANCE_SCORE", "RELEVANCE_CHECK"
    ]
    
    def __init__(self):
        """Initialize the context evaluator agent."""
        super().__init__("context_evaluator")
        
        # Cache for context summaries
        self._context_summaries: Dict[str, Tuple[str, float]] = {}

    def reset(self) -> None:
        """Clear cached context summaries to avoid cross-session leakage."""
        try:
            self._context_summaries.clear()
        except Exception:
            self._context_summaries = {}
        logger.info("ContextEvaluator agent cache cleared")
    
    def _generate_system_prompt(self, context: AgentContext) -> str:
        """
        Generate the system prompt for the context evaluator agent.
        
        Args:
            context: The agent context.
        
        Returns:
            The system prompt string.
        """
        system_prompt = """You are the ContextEvaluator, an AI responsible for analyzing game context, evaluating memories, and determining what information is most relevant to the current situation. Your goal is to provide context awareness to both the player and other game systems.

## Your Responsibilities
1. Analyze the current game context and determine what is most relevant
2. Evaluate memory entries for their importance to the current situation
3. Generate concise, useful context summaries
4. Suggest topics, elements, or actions that might be relevant
5. Calculate importance scores for different context elements
6. Identify connections between seemingly unrelated pieces of information

## Analysis Approach
- **Situational Relevance**: Consider the player's current location, ongoing quests, recent actions, and immediate goals
- **Character Relationships**: Identify NPCs, factions, and entities relevant to the current context
- **Knowledge Continuity**: Ensure important information from past interactions is surfaced when relevant
- **Narrative Coherence**: Maintain storytelling consistency and logical progression
- **Quest Progression**: Highlight information relevant to active and nearby quests
- **Environmental Context**: Note location-specific details, hazards, or opportunities
- **Player Intent**: Consider what the player is likely trying to accomplish

## Output Format
Provide your analysis in this format:
1. Context Summary (2-3 sentences highlighting the most critical elements)
2. Key Elements (bullet points of the most important context items)
3. Suggested Focus (what the player should consider or attend to)
4. Importance Scores (numeric ratings for different context elements)

## Special Instructions
- Be concise and precise - focus on the most relevant information
- Consider both immediate and long-term relevance
- Prioritize information that might otherwise be forgotten or overlooked
- Avoid unnecessary repetition of obvious information
- When evaluating memories, consider recency, uniqueness, and narrative impact
- Use numeric scores (0-10) when evaluating importance

Analyze the provided context and respond with your evaluation.
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
        
        # Add current game state information
        state_info = self._format_game_state(context)
        if state_info:
            messages.append({"role": "user", "content": state_info})
        
        # Add memory entries if available
        memory_info = self._format_memories(context)
        if memory_info:
            messages.append({"role": "user", "content": memory_info})
        
        # Add conversation history
        history_info = self._format_conversation_summary(context)
        if history_info:
            messages.append({"role": "user", "content": history_info})
        
        # Add the evaluation request
        eval_request = self._format_evaluation_request(context)
        messages.append({"role": "user", "content": eval_request})
        
        return messages
    
    def _format_game_state(self, context: AgentContext) -> str:
        """
        Format game state information for the LLM prompt.
        
        Args:
            context: The agent context.
        
        Returns:
            Formatted game state string.
        """
        # Extract player information
        player_state = context.player_state
        if not player_state:
            return ""
        
        player_name = player_state.get("name", "Unknown")
        player_race = player_state.get("race", "Human")
        player_path = player_state.get("path", "Wanderer")
        player_location = player_state.get("current_location", "Unknown")
        player_district = player_state.get("current_district", "Unknown")
        
        # Extract world information
        world_state = context.world_state
        if not world_state:
            return ""
        
        time_of_day = world_state.get("time_of_day", "Unknown")
        weather = world_state.get("weather", "Clear")
        is_day = world_state.get("is_day", True)
        day_night = "day" if is_day else "night"
        
        # Get active quests if available
        active_quests = player_state.get("active_quests", [])
        
        # Format the information
        state_lines = [
            "## Current Game State",
            f"- Player: {player_name} the {player_race} {player_path}",
            f"- Location: {player_location}, {player_district}",
            f"- Time: {time_of_day} ({day_night})",
            f"- Weather: {weather}"
        ]
        
        # Add active quests
        if active_quests:
            state_lines.append("\n### Active Quests")
            for quest in active_quests:
                quest_name = quest.get("name", "Unknown Quest")
                quest_stage = quest.get("stage", "Unknown")
                state_lines.append(f"- {quest_name} (Stage: {quest_stage})")
        
        return "\n".join(state_lines)
    
    def _format_memories(self, context: AgentContext) -> str:
        """
        Format memory entries for the LLM prompt.
        
        Args:
            context: The agent context.
        
        Returns:
            Formatted memory entries string.
        """
        if not context.relevant_memories:
            return ""
        
        memory_lines = ["## Memory Entries to Evaluate"]
        
        # Organize memories by type
        memories_by_type = {}
        
        for memory in context.relevant_memories:
            memory_type = memory.get("type", "general")
            
            if memory_type not in memories_by_type:
                memories_by_type[memory_type] = []
            
            memories_by_type[memory_type].append(memory)
        
        # Add memories by type
        for memory_type, memories in memories_by_type.items():
            memory_lines.append(f"\n### {memory_type.title()} Memories")
            
            for i, memory in enumerate(memories):
                content = memory.get("content", "")
                timestamp = memory.get("timestamp", "")
                memory_lines.append(f"{i+1}. {content} ({timestamp})")
        
        return "\n".join(memory_lines)
    
    def _format_conversation_summary(self, context: AgentContext) -> str:
        """
        Format a summary of recent conversation for the LLM prompt.
        
        Args:
            context: The agent context.
        
        Returns:
            Formatted conversation summary string.
        """
        if not context.conversation_history:
            return ""
        
        # Get the most recent conversation entries (last 5)
        recent_conversation = context.conversation_history[-5:]
        
        summary_lines = ["## Recent Conversation"]
        
        for entry in recent_conversation:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            
            # Format based on role
            if role == "player":
                summary_lines.append(f"Player: {content}")
            elif role == "gm":
                summary_lines.append(f"Narrator: {content}")
            else:
                summary_lines.append(f"{role.title()}: {content}")
        
        return "\n".join(summary_lines)
    
    def _format_evaluation_request(self, context: AgentContext) -> str:
        """
        Format the evaluation request for the LLM prompt.
        
        Args:
            context: The agent context.
        
        Returns:
            Formatted evaluation request string.
        """
        request_lines = [
            "## Context Evaluation Request",
            "Please evaluate the current game context based on the information provided above.",
            "Consider what is most relevant to the player's current situation and goals.",
            "",
            "### Current Focus",
            f"Player's last input: \"{context.player_input}\"",
            "",
            "Provide a context summary, identify key elements, suggest a focus, and assign importance scores."
        ]
        
        return "\n".join(request_lines)
    
    def process(self, context: AgentContext) -> AgentResponse:
        """
        Process a context evaluation request.
        
        Args:
            context: The agent context.
        
        Returns:
            The agent response.
        """
        logger.info("Processing request with ContextEvaluator agent")
        
        # Use the base process method
        response = super().process(context)
        
        # Parse the evaluation result
        evaluation_result = self._parse_evaluation_result(response.content)
        
        # Add the evaluation result to the response metadata
        if evaluation_result:
            response.metadata["evaluation_result"] = evaluation_result
        
        # Cache the context summary if successful
        if evaluation_result and "context_summary" in evaluation_result:
            key = self._generate_context_key(context)
            summary = evaluation_result["context_summary"]
            timestamp = context.world_state.get("game_time", 0) if context.world_state else 0
            
            self._context_summaries[key] = (summary, timestamp)
        
        return response
    
    def _parse_evaluation_result(self, content: str) -> Dict[str, Any]:
        """
        Parse the evaluation result from the LLM response.
        
        Args:
            content: The LLM response content.
        
        Returns:
            Dictionary with evaluation result information.
        """
        result = {
            "context_summary": None,
            "key_elements": [],
            "suggested_focus": None,
            "importance_scores": {}
        }
        
        # Extract context summary
        summary_match = re.search(r"(?:Context Summary:?|Summary:?)\s*(.+?)(?:\n\n|\n#|\n\*|$)", content, re.IGNORECASE | re.DOTALL)
        if summary_match:
            result["context_summary"] = summary_match.group(1).strip()
        
        # Extract key elements
        elements_section = re.search(r"(?:Key Elements:?|Important Elements:?)(.+?)(?:\n\n|\n#|$)", content, re.IGNORECASE | re.DOTALL)
        if elements_section:
            elements_text = elements_section.group(1).strip()
            # Extract bullet points
            elements = re.findall(r"(?:^|\n)-\s*(.+?)(?:$|\n)", elements_text)
            result["key_elements"] = [e.strip() for e in elements if e.strip()]
        
        # Extract suggested focus
        focus_match = re.search(r"(?:Suggested Focus:?|Focus:?)\s*(.+?)(?:\n\n|\n#|$)", content, re.IGNORECASE | re.DOTALL)
        if focus_match:
            result["suggested_focus"] = focus_match.group(1).strip()
        
        # Extract importance scores
        scores_section = re.search(r"(?:Importance Scores:?|Scores:?)(.+?)(?:\n\n|\n#|$)", content, re.IGNORECASE | re.DOTALL)
        if scores_section:
            scores_text = scores_section.group(1).strip()
            # Extract element-score pairs
            score_patterns = [
                r"(?:^|\n)-\s*(.+?):\s*(\d+(?:\.\d+)?)",  # Bullet point format
                r"(?:^|\n)(.+?):\s*(\d+(?:\.\d+)?)"       # Regular format
            ]
            
            for pattern in score_patterns:
                scores = re.findall(pattern, scores_text)
                if scores:
                    for element, score in scores:
                        try:
                            result["importance_scores"][element.strip()] = float(score)
                        except ValueError:
                            pass
        
        return result
    
    def _generate_context_key(self, context: AgentContext) -> str:
        """
        Generate a key for caching context summaries.
        
        Args:
            context: The agent context.
        
        Returns:
            A string key representing the context.
        """
        # Create a key based on location and player input
        location = context.player_state.get("current_location", "") if context.player_state else ""
        district = context.player_state.get("current_district", "") if context.player_state else ""
        input_hash = hash(context.player_input) % 10000  # Simple hash of input
        
        return f"{location}_{district}_{input_hash}"
    
    def get_cached_summary(self, context: AgentContext) -> Optional[str]:
        """
        Get a cached context summary if available and recent.
        
        Args:
            context: The agent context.
        
        Returns:
            A cached summary string, or None if not available.
        """
        key = self._generate_context_key(context)
        
        if key in self._context_summaries:
            summary, timestamp = self._context_summaries[key]
            
            # Check if the summary is still recent enough
            current_time = context.world_state.get("game_time", 0) if context.world_state else 0
            
            # If the summary is less than 10 minutes old in game time, use it
            if current_time - timestamp < 600:
                return summary
        
        return None
    
    def evaluate_context(self, context: AgentContext) -> Dict[str, Any]:
        """
        Evaluate the current game context.
        
        Args:
            context: The agent context.
        
        Returns:
            Dictionary with evaluation results.
        """
        # Check for cached summary first
        cached_summary = self.get_cached_summary(context)
        if cached_summary:
            logger.info("Using cached context summary")
            return {
                "context_summary": cached_summary,
                "source": "cache"
            }
        
        # Otherwise, process the context evaluation
        response = self.process(context)
        
        # Return the evaluation result
        return response.metadata.get("evaluation_result", {})
    
    def supports_command(self, command: str) -> bool:
        """
        Check if the context evaluator agent supports a specific command.
        
        Args:
            command: The command name.
        
        Returns:
            True if the agent supports the command, False otherwise.
        """
        return command in self.SUPPORTED_COMMANDS


# Convenience function
def get_context_evaluator_agent() -> ContextEvaluatorAgent:
    """Get the context evaluator agent instance."""
    return ContextEvaluatorAgent()


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    get_logger.basicConfig(level=get_logger.INFO)
    
    # Create the context evaluator agent
    context_evaluator = get_context_evaluator_agent()
    
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
            "active_quests": [
                {"name": "The Lost Artifact", "stage": "Find the entrance to the ancient temple"}
            ]
        },
        world_state={
            "time_of_day": "evening",
            "weather": "Light Rain",
            "is_day": False,
            "game_time": 1000
        },
        player_input="I look around for any signs of the temple entrance.",
        conversation_history=[
            {"role": "player", "content": "I enter the Ancient Grove cautiously.", "timestamp": "2023-01-01T12:00:00"},
            {"role": "gm", "content": "The trees here are older and more gnarled, their branches forming a dense canopy above. Strange symbols are carved into some of the trunks.", "timestamp": "2023-01-01T12:00:01"},
            {"role": "player", "content": "I examine the symbols on the trees.", "timestamp": "2023-01-01T12:00:02"},
            {"role": "gm", "content": "The symbols appear to be an ancient elven script. They seem to be pointing in a specific direction deeper into the grove.", "timestamp": "2023-01-01T12:00:03"}
        ],
        relevant_memories=[
            {
                "content": "The Ancient Grove is said to contain a hidden temple dedicated to the old gods.",
                "type": "location",
                "importance": 0.9,
                "timestamp": "2023-01-01T11:30:00"
            },
            {
                "content": "The temple entrance is marked by trees with elven runes.",
                "type": "quest",
                "importance": 0.95,
                "timestamp": "2023-01-01T11:35:00"
            },
            {
                "content": "You obtained a map fragment showing part of the Ancient Grove.",
                "type": "item",
                "importance": 0.8,
                "timestamp": "2023-01-01T11:40:00"
            }
        ]
    )
    
    # Process the request
    response = context_evaluator.process(context)
    
    # Print the response
    print(f"Response: {response.content}")
    
    # Print the evaluation result
    evaluation_result = response.metadata.get("evaluation_result", {})
    if evaluation_result:
        print("\nEvaluation Result:")
        print(f"Context Summary: {evaluation_result.get('context_summary')}")
        print(f"Key Elements: {evaluation_result.get('key_elements')}")
        print(f"Suggested Focus: {evaluation_result.get('suggested_focus')}")
        print(f"Importance Scores: {evaluation_result.get('importance_scores')}")