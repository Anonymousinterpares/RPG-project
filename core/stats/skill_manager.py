"""
Skill Manager for loading and managing skills from external JSON files.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List, Set, Tuple

from core.stats.stats_base import StatType

logger = logging.getLogger(__name__)

class SkillManager:
    """
    Manages skills loaded from external definitions.
    
    This class handles loading skill definitions from JSON files,
    checking skill validity, and providing access to skill data.
    It also supports generating and managing custom skills.
    """
    
    def __init__(self, filepath="config/skills.json"):
        """Initialize the skill manager with skills from a JSON file."""
        self.skills = {}
        self.custom_skills = {}  # Character-specific custom skills
        self.load_skills(filepath)
        logger.info(f"SkillManager initialized with {len(self.skills)} skills")
    
    def load_skills(self, filepath: str) -> None:
        """
        Load skills from a JSON file.
        
        Args:
            filepath: Path to the skills JSON file.
        """
        try:
            full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), filepath)
            with open(full_path, 'r') as f:
                data = json.load(f)
                self.skills = data.get("skills", {})
            logger.info(f"Successfully loaded {len(self.skills)} skills from {filepath}")
        except Exception as e:
            logger.error(f"Error loading skills from {filepath}: {e}")
            # Fall back to default skills if file can't be loaded
            self._load_default_skills()
    
    def _load_default_skills(self) -> None:
        """Load default skills if JSON fails."""
        # Hardcoded fallback skills
        self.skills = {
            "melee_attack": {
                "name": "Melee Attack",
                "primary_stat": "STRENGTH",
                "category": "COMBAT",
                "description": "Physical close-range combat attacks"
            },
            "ranged_attack": {
                "name": "Ranged Attack",
                "primary_stat": "DEXTERITY",
                "category": "COMBAT",
                "description": "Physical ranged combat attacks"
            },
            "dodge": {
                "name": "Dodge",
                "primary_stat": "DEXTERITY",
                "category": "COMBAT",
                "description": "Avoiding attacks and obstacles"
            }
        }
        logger.warning(f"Loaded {len(self.skills)} default skills as fallback")
    
    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a skill by name (case-insensitive).
        
        Args:
            skill_name: The name of the skill to get.
            
        Returns:
            The skill data if found, None otherwise.
        """
        if not skill_name:
            return None
            
        # Normalize the skill name: lowercase and replace spaces with underscores
        normalized_name = skill_name.lower().replace(" ", "_")
        
        # Check in standard skills
        if normalized_name in self.skills:
            return self.skills[normalized_name]
        
        # Check in all character custom skills
        for char_id, char_skills in self.custom_skills.items():
            if normalized_name in char_skills:
                return char_skills[normalized_name]
        
        # Check for partial matches
        for skill_id, skill in self.skills.items():
            if normalized_name in skill_id or normalized_name in skill['name'].lower():
                logger.debug(f"Partial match for '{skill_name}': found '{skill['name']}'")
                return skill
        
        # No match found
        logger.debug(f"No skill found for '{skill_name}'")
        return None
    
    def get_character_skill(self, character_id: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a character-specific skill by name.
        
        Args:
            character_id: The ID of the character.
            skill_name: The name of the skill to get.
            
        Returns:
            The skill data if found, None otherwise.
        """
        normalized_name = skill_name.lower().replace(" ", "_")
        
        # Check if this character has custom skills
        char_skills = self.custom_skills.get(character_id, {})
        
        # Try exact match first
        if normalized_name in char_skills:
            return char_skills[normalized_name]
        
        # Then try partial match
        for skill_id, skill in char_skills.items():
            if normalized_name in skill_id or normalized_name in skill['name'].lower():
                return skill
        
        # If not found in character skills, try standard skills
        return self.get_skill(skill_name)
    
    def is_valid_skill(self, skill_name: str) -> bool:
        """
        Check if a skill name is valid.
        
        Args:
            skill_name: The name of the skill to check.
            
        Returns:
            True if the skill is valid, False otherwise.
        """
        return self.get_skill(skill_name) is not None
    
    def get_all_skills(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all skills.
        
        Returns:
            Dictionary of all skills.
        """
        return self.skills
    
    def get_skills_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """
        Get skills filtered by category.
        
        Args:
            category: The category to filter by.
            
        Returns:
            Dictionary of skills in the specified category.
        """
        result = {}
        for skill_id, skill in self.skills.items():
            if skill.get('category', '').upper() == category.upper():
                result[skill_id] = skill
        return result
    
    def get_character_skills(self, character_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all custom skills for a character.
        
        Args:
            character_id: The ID of the character.
            
        Returns:
            Dictionary of custom skills for the character.
        """
        return self.custom_skills.get(character_id, {})
    
    def get_skill_list_for_llm(self) -> str:
        """
        Generate a formatted string of skills for LLM prompts.
        
        Returns:
            Formatted string listing all available skills.
        """
        result = "Available skills:\n"
        for skill_id, skill in self.skills.items():
            result += f"- {skill['name']} ({skill_id}): {skill.get('description', '')}\n"
        return result
    
    def get_primary_stat_for_skill(self, skill_name: str) -> Optional[StatType]:
        """
        Get the primary stat type for a skill.
        
        Args:
            skill_name: The name of the skill.
            
        Returns:
            The StatType for the skill's primary stat, or None if not found.
        """
        skill = self.get_skill(skill_name)
        if not skill or 'primary_stat' not in skill:
            return None
            
        try:
            # Convert string stat name to StatType enum
            stat_name = skill['primary_stat']
            from core.stats.stats_base import StatType
            return StatType.from_string(stat_name)
        except (ValueError, ImportError) as e:
            logger.error(f"Error getting primary stat for skill '{skill_name}': {e}")
            return None
    
    def generate_custom_skill(self, character_id: str, skill_data: Dict[str, Any], context: str = "") -> Optional[str]:
        """
        Generate a custom skill for a character.
        
        Args:
            character_id: The ID of the character.
            skill_data: The base data for the skill (name, primary_stat, etc.)
            context: Optional context about how/why the skill was generated.
            
        Returns:
            The ID of the generated skill, or None if generation failed.
        """
        try:
            # Validate required fields
            required_fields = ['name', 'primary_stat', 'description']
            for field in required_fields:
                if field not in skill_data:
                    logger.error(f"Missing required field '{field}' for custom skill")
                    return None
            
            # Generate a unique ID for the skill
            skill_id = f"custom_{character_id}_{int(time.time())}"
            
            # Initialize character's custom skills dict if needed
            if character_id not in self.custom_skills:
                self.custom_skills[character_id] = {}
            
            # Create the skill with the provided data
            self.custom_skills[character_id][skill_id] = {
                "name": skill_data["name"],
                "primary_stat": skill_data["primary_stat"],
                "category": skill_data.get("category", "CUSTOM"),
                "description": skill_data["description"],
                "generation_context": context,
                "created_at": time.time()
            }
            
            logger.info(f"Generated custom skill '{skill_data['name']}' ({skill_id}) for character {character_id}")
            
            # TODO: Save custom skills to disk when persistence is implemented
            
            return skill_id
        except Exception as e:
            logger.error(f"Error generating custom skill: {e}")
            return None
    
    def find_closest_skill(self, intent: str) -> Optional[str]:
        """
        Find the closest matching skill for a given player intent.
        
        Args:
            intent: The player's intention description.
            
        Returns:
            The ID of the closest matching skill, or None if no match.
        """
        intent_lower = intent.lower()
        
        # Define common action keywords and their associated skills
        keyword_mappings = {
            # Attack keywords
            "attack": "melee_attack",
            "hit": "melee_attack",
            "strike": "melee_attack",
            "slash": "melee_attack",
            "stab": "melee_attack",
            "bash": "melee_attack",
            
            # Ranged keywords
            "shoot": "ranged_attack",
            "fire": "ranged_attack",
            "throw": "ranged_attack",
            "aim": "ranged_attack",
            
            # Magic keywords
            "cast": "spell_attack",
            "spell": "spell_attack",
            
            # Evasion keywords
            "dodge": "dodge",
            "evade": "dodge",
            "avoid": "dodge",
            "duck": "dodge",
            "jump": "acrobatics",
            "flip": "acrobatics",
            "somersault": "acrobatics",
            "roll": "acrobatics",
            
            # Unarmed keywords
            "punch": "unarmed_attack",
            "kick": "unarmed_attack",
            "knee": "unarmed_attack",
            "elbow": "unarmed_attack",
            "headbutt": "unarmed_attack"
        }
        
        # Check for direct keyword matches
        for keyword, skill_id in keyword_mappings.items():
            if keyword in intent_lower and skill_id in self.skills:
                return skill_id
        
        # If no match found, try broader categories
        if any(word in intent_lower for word in ["punch", "kick", "unarmed"]):
            return "unarmed_attack"
        
        if any(word in intent_lower for word in ["flip", "jump", "roll", "agile"]):
            return "acrobatics"
            
        if any(word in intent_lower for word in ["attack", "fight", "hit", "combat"]):
            return "melee_attack"
        
        if any(word in intent_lower for word in ["dodge", "avoid", "evade"]):
            return "dodge"
        
        # Default fallback
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the skill manager.
        """
        return {
            "skills": self.skills,
            "custom_skills": self.custom_skills
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillManager':
        """
        Create a SkillManager from a dictionary.
        
        Args:
            data: Dictionary representation of a skill manager.
            
        Returns:
            A new SkillManager instance.
        """
        manager = cls()
        
        # Only load from file if no skills in the data
        if not data.get("skills"):
            # This keeps the default behavior of loading from file
            pass
        else:
            # Override with provided data
            manager.skills = data.get("skills", {})
            manager.custom_skills = data.get("custom_skills", {})
        
        return manager


# Singleton instance
_skill_manager_instance = None

def get_skill_manager() -> SkillManager:
    """
    Get the skill manager instance.
    
    Returns:
        The singleton SkillManager instance.
    """
    global _skill_manager_instance
    if _skill_manager_instance is None:
        _skill_manager_instance = SkillManager()
    
    return _skill_manager_instance
