#!/usr/bin/env python3
"""
Character background generation and enhancement module.

This module provides functionality for generating and enhancing character backgrounds
using LLM technology based on character attributes.
"""

from typing import Dict, Any, Optional

from core.utils.logging_config import get_logger, LogCategory
from core.llm.llm_manager import get_llm_manager, LLMRole

logger = get_logger(LogCategory.AGENT)

class BackgroundGenerator:
    """
    Handles character background generation and enhancement using LLM technology.
    """
    
    def __init__(self):
        """Initialize the background generator."""
        self.llm_manager = get_llm_manager()
        logger.info("Initialized BackgroundGenerator")
    
    def improve_background(self, background_text: str, character_data: Dict[str, Any]) -> Optional[str]:
        """
        Improve an existing character background.
        
        Args:
            background_text: The original background text to improve.
            character_data: Character data including race, class, etc.
            
        Returns:
            An improved version of the background text, or None if the request failed.
        """
        if not background_text.strip():
            logger.warning("Cannot improve empty background")
            return None
        
        try:
            logger.info("Improving character background")
            
            # Extract character info
            name = character_data.get('name', 'Character')
            race = character_data.get('race', 'Unknown')
            character_class = character_data.get('path', 'Unknown')
            background = character_data.get('background', 'Unknown')
            sex = character_data.get('sex', 'Unknown')
            
            # Create prompt for LLM
            messages = [
                {
                    "role": LLMRole.SYSTEM,
                    "content": f"""You are a creative writer specializing in fantasy RPG character backgrounds. 
                    You will be provided with a character background that needs improvement.
                    Your task is to enhance this background, making it more engaging, detailed, and aligned with fantasy RPG tropes.
                    Maintain the core elements and intentions of the original text, but improve the writing style, add depth,
                    and ensure it aligns well with the character's race, class, background, and sex.
                    
                    Your response should ONLY include the improved background text, with no additional commentary, explanations, or meta-text.
                    Keep the length reasonable - between 150-300 words is ideal."""
                },
                {
                    "role": LLMRole.USER,
                    "content": f"""Here's a character background that needs improvement:
                    
                    Character Info:
                    - Name: {name}
                    - Race: {race}
                    - Class: {character_class}
                    - Background: {background}
                    - Sex: {sex}
                    
                    Original background text:
                    "{background_text}"
                    
                    Please improve this background, making it more engaging and aligned with fantasy RPG conventions.
                    Remember to maintain the core elements while enhancing the writing style and depth.
                    Return ONLY the improved background text with no additional commentary.
                    """
                }
            ]
            
            # Get completion from LLM
            response = self.llm_manager.get_completion(messages)
            
            if response:
                improved_text = response.content.strip()
                logger.info(f"Successfully improved background (tokens: {response.total_tokens})")
                return improved_text
            else:
                logger.error("Failed to improve background: No response from LLM")
                return None
            
        except Exception as e:
            logger.error(f"Error improving background: {e}")
            return None
    
    def generate_background(self, character_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate a new character background.
        
        Args:
            character_data: Character data including race, class, etc.
            
        Returns:
            A generated background text, or None if the request failed.
        """
        try:
            logger.info("Generating new character background")
            
            # Extract character info
            name = character_data.get('name', 'Character')
            race = character_data.get('race', 'Unknown')
            character_class = character_data.get('path', 'Unknown')
            background = character_data.get('background', 'Unknown')
            sex = character_data.get('sex', 'Unknown')
            
            # Extract stats if available
            stats_text = ""
            if 'stats' in character_data:
                stats = character_data['stats']
                stats_list = []
                for stat_name, stat_info in stats.items():
                    value = stat_info.get('value', 10)
                    stats_list.append(f"{stat_name}: {value}")
                stats_text = "\n".join(stats_list)
            
            # Create prompt for LLM
            messages = [
                {
                    "role": LLMRole.SYSTEM,
                    "content": f"""You are a creative writer specializing in fantasy RPG character backgrounds. 
                    You will be provided with details about a character, and your task is to create an engaging,
                    immersive background story for them.
                    
                    Create a background that:
                    1. Fits the character's race, class, background origin, and sex
                    2. Includes formative experiences that led them to their current class/profession
                    3. Incorporates appropriate fantasy RPG tropes without being cliché
                    4. Has some interesting hook or unique aspect to make the character memorable
                    5. Could serve as the beginning of an adventure
                    
                    Your response should ONLY include the background story, with no additional commentary, explanations, or meta-text.
                    The background should be between 200-350 words."""
                },
                {
                    "role": LLMRole.USER,
                    "content": f"""Please create an interesting character background for:
                    
                    Character Info:
                    - Name: {name}
                    - Race: {race}
                    - Class: {character_class}
                    - Background Origin: {background}
                    - Sex: {sex}
                    {f"- Stats:\n{stats_text}" if stats_text else ""}
                    
                    Generate a background story for this character that fits their attributes and would be engaging in a fantasy RPG setting.
                    The character's background origin is '{background}', which should inform their upbringing and formative experiences.
                    Return ONLY the background text with no additional commentary.
                    """
                }
            ]
            
            # Get completion from LLM
            response = self.llm_manager.get_completion(messages)
            
            if response:
                background_text = response.content.strip()
                logger.info(f"Successfully generated background (tokens: {response.total_tokens})")
                return background_text
            else:
                logger.error("Failed to generate background: No response from LLM")
                return None
            
        except Exception as e:
            logger.error(f"Error generating background: {e}")
            return None

# Convenience function
def get_background_generator() -> BackgroundGenerator:
    """Get a background generator instance."""
    return BackgroundGenerator()


# Example usage
if __name__ == "__main__":
    get_logger.basicConfig(level=get_logger.INFO)
    
    generator = get_background_generator()
    
    # Example character data
    character_data = {
        'name': 'Tordek',
        'race': 'Dwarf',
        'path': 'Warrior',
        'background': 'Soldier',
        'sex': 'Male'
    }
    
    # Example of improving a background
    original_background = "Tordek was born in the mountains and became a warrior. He fought in many battles and is now seeking adventure."
    improved = generator.improve_background(original_background, character_data)
    
    if improved:
        print("Original background:")
        print(original_background)
        print("\nImproved background:")
        print(improved)
    
    # Example of generating a new background
    generated = generator.generate_background(character_data)
    
    if generated:
        print("\nGenerated background:")
        print(generated)
