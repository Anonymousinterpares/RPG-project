#!/usr/bin/env python3
"""
NPC generator for creating NPCs with appropriate stats based on interaction needs.
"""

import random
import os
import json
from typing import Dict, Any, Optional

from core.character.npc_base import NPC, NPCType, NPCRelationship, NPCInteractionType
from core.stats.stats_manager import StatsManager
from core.stats.stats_base import StatType
from core.inventory.item_variation_generator import ItemVariationGenerator
from core.inventory.item_enums import ItemType, ItemRarity, EquipmentSlot
from core.inventory.equipment_manager import EquipmentManager
from core.utils.logging_config import get_logger

logger = get_logger(__name__)


class NPCGenerator:
    """
    Generator for creating NPCs with appropriate attributes and stats.
    Handles generation of NPCs based on context and interaction needs.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the NPC generator.
        
        Args:
            config_path: Path to configuration file with NPC templates and generation rules.
        """
        self.config = {}
        self.templates = {}
        self.name_pools = {}
        
        # Default config path
        if config_path is None:
            config_path = os.path.join("config", "character", "npc_templates.json")
        
        # Load configuration if it exists
        if os.path.exists(config_path):
            self._load_config(config_path)
        else:
            logger.warning(f"NPC templates configuration not found at: {config_path}")
            self._initialize_default_config()
    
    def _load_config(self, config_path: str) -> None:
        """
        Load NPC generation configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file.
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            # Extract templates and name pools
            self.templates = self.config.get("templates", {})
            self.name_pools = self.config.get("name_pools", {})
            
            logger.info(f"Loaded NPC generation config from {config_path}")
        except Exception as e:
            logger.error(f"Error loading NPC config: {e}")
            self._initialize_default_config()
    
    def _initialize_default_config(self) -> None:
        """Initialize with default configuration if no file is found."""
        self.config = {
            "templates": {
                "merchant": {
                    "npc_type": "MERCHANT",
                    "stat_distributions": {
                        "STR": {"min": 8, "max": 12},
                        "DEX": {"min": 8, "max": 14},
                        "CON": {"min": 8, "max": 12},
                        "INT": {"min": 10, "max": 16},
                        "WIS": {"min": 10, "max": 16},
                        "CHA": {"min": 12, "max": 18}
                    },
                    "personality_traits": [
                        "Shrewd", "Calculating", "Friendly", "Talkative",
                        "Suspicious", "Generous", "Greedy"
                    ]
                },
                "guard": {
                    "npc_type": "NEUTRAL",
                    "stat_distributions": {
                        "STR": {"min": 12, "max": 16},
                        "DEX": {"min": 10, "max": 14},
                        "CON": {"min": 12, "max": 16},
                        "INT": {"min": 8, "max": 12},
                        "WIS": {"min": 10, "max": 14},
                        "CHA": {"min": 8, "max": 12}
                    },
                    "personality_traits": [
                        "Dutiful", "Vigilant", "Stern", "Authoritative",
                        "Lazy", "Corrupt", "Honorable"
                    ]
                },
                "commoner": {
                    "npc_type": "BACKGROUND",
                    "stat_distributions": {
                        "STR": {"min": 8, "max": 12},
                        "DEX": {"min": 8, "max": 12},
                        "CON": {"min": 8, "max": 12},
                        "INT": {"min": 8, "max": 12},
                        "WIS": {"min": 8, "max": 12},
                        "CHA": {"min": 8, "max": 12}
                    },
                    "personality_traits": [
                        "Hardworking", "Simple", "Curious", "Suspicious",
                        "Friendly", "Reserved", "Gossipy"
                    ]
                }
            },
            "name_pools": {
                "generic": {
                    "male": ["John", "William", "Thomas", "James", "George", "Robert"],
                    "female": ["Mary", "Elizabeth", "Sarah", "Anne", "Margaret", "Jane"],
                    "surname": ["Smith", "Jones", "Brown", "Williams", "Taylor", "Davies"]
                }
            }
        }
        
        self.templates = self.config["templates"]
        self.name_pools = self.config["name_pools"]
        
        logger.info("Initialized default NPC generation config")
    
    def generate_random_name(self, gender: Optional[str] = None, name_pool: str = "generic") -> str:
        """
        Generate a random name for an NPC.
        
        Args:
            gender: Optional gender ('male', 'female', None for random)
            name_pool: Name pool to use from config
            
        Returns:
            A random name
        """
        if name_pool not in self.name_pools:
            name_pool = "generic"
            
        if name_pool not in self.name_pools:
            # Fallback if no pools are available
            return f"NPC-{random.randint(1000, 9999)}"
        
        # Select gender if not specified
        if gender is None:
            gender = random.choice(["male", "female"])
        
        # Ensure pools exist
        if gender not in self.name_pools[name_pool]:
            gender = list(self.name_pools[name_pool].keys())[0]
        
        if "surname" not in self.name_pools[name_pool]:
            return random.choice(self.name_pools[name_pool][gender])
        
        # Generate full name
        first_name = random.choice(self.name_pools[name_pool][gender])
        surname = random.choice(self.name_pools[name_pool]["surname"])
        
        return f"{first_name} {surname}"
    
    def generate_minimal_npc(self, name: Optional[str] = None, npc_type: NPCType = NPCType.BACKGROUND) -> NPC:
        """
        Generate a minimal NPC with just basic information.
        
        Args:
            name: Optional name for the NPC (generated if None)
            npc_type: Type of NPC to generate
            
        Returns:
            An NPC object with minimal details
        """
        # Generate name if not provided
        if name is None:
            name = self.generate_random_name()
        
        # Create basic NPC
        npc = NPC(
            name=name,
            npc_type=npc_type,
            description=f"A {npc_type.name.lower()} named {name}."
        )
        
        logger.debug(f"Generated minimal NPC: {npc.name}")
        return npc
    
    def _select_template(self, npc_type: NPCType, npc_subtype: Optional[str] = None) -> Dict[str, Any]:
        """
        Select an appropriate template for the NPC type.
        
        Args:
            npc_type: The type of NPC to generate
            npc_subtype: Optional subtype (e.g., 'boss_dragon', 'merchant')
            
        Returns:
            A template dictionary
        """
        # If a subtype is provided, check if it exists as a template
        if npc_subtype and npc_subtype in self.templates:
            logger.debug(f"Using specific template for subtype: {npc_subtype}")
            return self.templates[npc_subtype]
            
        # Try to find a direct match for the type
        type_name = npc_type.name.lower()
        if type_name in self.templates:
            return self.templates[type_name]
        
        # Check for boss-type NPCs
        if npc_subtype and "boss" in npc_subtype.lower():
            # Look for boss templates in specialized_types
            if "specialized_types" in self.config and "boss" in self.config["specialized_types"]:
                boss_templates = self.config["specialized_types"]["boss"].get("templates", [])
                if boss_templates:
                    boss_template = random.choice(boss_templates)
                    if boss_template in self.templates:
                        logger.info(f"Using boss template for subtype: {npc_subtype}")
                        return self.templates[boss_template]
            
            # If we still need a boss template, look for any template starting with "boss_"
            boss_templates = [t for t in self.templates.keys() if t.startswith("boss_")]
            if boss_templates:
                boss_template = random.choice(boss_templates)
                logger.info(f"Using random boss template: {boss_template}")
                return self.templates[boss_template]
        
        # Fallback templates based on NPC type
        fallbacks = {
            NPCType.MERCHANT: "merchant",
            NPCType.QUEST_GIVER: "quest_giver",
            NPCType.ALLY: "ally",
            NPCType.ENEMY: "bandit",  # Changed from generic "enemy" to "bandit"
            NPCType.NEUTRAL: "commoner",
            NPCType.SERVICE: "merchant",
            NPCType.BACKGROUND: "commoner"
        }
        
        # Try to use the fallback template for this NPC type
        if npc_type in fallbacks and fallbacks[npc_type] in self.templates:
            return self.templates[fallbacks[npc_type]]
        
        # Check for "blank_template" for unexpected NPC types
        if "blank_template" in self.templates:
            logger.info(f"Using blank template for unexpected NPC type: {npc_type} (subtype: {npc_subtype})")
            return self.templates["blank_template"]
        
        # Last resort - use commoner template
        if "commoner" in self.templates:
            logger.warning(f"Using commoner template as fallback for unexpected NPC type: {npc_type}")
            return self.templates["commoner"]
        
        # Absolute fallback - just return a basic template
        logger.warning(f"No suitable template found for NPC type: {npc_type}, using basic stats")
        return {
            "npc_type": npc_type.name,
            "stat_distributions": {
                "STR": {"min": 8, "max": 14},
                "DEX": {"min": 8, "max": 14},
                "CON": {"min": 8, "max": 14},
                "INT": {"min": 8, "max": 14},
                "WIS": {"min": 8, "max": 14},
                "CHA": {"min": 8, "max": 14}
            },
            "personality_traits": ["Unique", "Distinctive", "Individual"]
        }
    
    def _generate_stats(self, 
                       npc: NPC, 
                       interaction_type: NPCInteractionType,
                       template: Dict[str, Any]) -> None:
        """
        Generate stats for an NPC based on the interaction type and template.
        
        Args:
            npc: The NPC to generate stats for
            interaction_type: The type of interaction (determines which stats to focus on)
            template: The template to use for generation
        """
        # Create stats manager
        stats_manager = StatsManager()
        
        # Generate primary stats based on template distributions
        stat_distributions = template.get("stat_distributions", {})
        
        for stat_type in StatType:
            stat_name = stat_type.name
            if stat_name in stat_distributions:
                min_val = stat_distributions[stat_name].get("min", 8)
                max_val = stat_distributions[stat_name].get("max", 14)
                value = random.randint(min_val, max_val)
            else:
                # Default range if not specified
                value = random.randint(8, 14)
            
            # Adjust stats based on interaction type
            if interaction_type == NPCInteractionType.COMBAT:
                # For combat, boost combat-relevant stats
                if stat_type in [StatType.STRENGTH, StatType.DEXTERITY, StatType.CONSTITUTION]:
                    value = max(value, random.randint(12, 16))
            
            elif interaction_type == NPCInteractionType.SOCIAL:
                # For social, boost social stats
                if stat_type in [StatType.CHARISMA, StatType.WISDOM]:
                    value = max(value, random.randint(12, 16))
            
            elif interaction_type == NPCInteractionType.COMMERCE:
                # For commerce, boost charisma and intelligence
                if stat_type in [StatType.CHARISMA, StatType.INTELLIGENCE]:
                    value = max(value, random.randint(12, 16))
            
            elif interaction_type == NPCInteractionType.INFORMATION:
                # For information providers, boost intelligence and wisdom
                if stat_type in [StatType.INTELLIGENCE, StatType.WISDOM]:
                    value = max(value, random.randint(12, 16))
            
            # Set the stat value
            stats_manager.set_base_stat(stat_type, value)
        
        # For combat NPCs, generate some appropriate equipment modifiers
        if interaction_type == NPCInteractionType.COMBAT:
            try:
                logger.info(f"Starting equipment generation for NPC {npc.name}")
                self._generate_equipment(npc, interaction_type, template)
                logger.info(f"Completed equipment generation for NPC {npc.name}")
            except Exception as e:
                logger.error(f"Equipment generation failed for NPC {npc.name}: {e}", exc_info=True)
                # Ensure NPC has at least an empty equipment manager
                if not hasattr(npc, 'equipment_manager'):
                    npc.equipment_manager = EquipmentManager()
                logger.info(f"Created fallback equipment manager for NPC {npc.name}")
        
        # Set the stats manager on the NPC
        npc.stats_manager = stats_manager
        npc.stats_generated = True
    
    def _generate_personality(self, template: Dict[str, Any]) -> str:
        """
        Generate a personality description for an NPC.
        
        Args:
            template: The template to use for generation
            
        Returns:
            A personality description
        """
        traits = template.get("personality_traits", ["Unremarkable"])
        
        # Pick 1-3 traits
        num_traits = min(3, len(traits))
        selected_traits = random.sample(traits, random.randint(1, num_traits))
        
        # Form a simple personality description
        if len(selected_traits) == 1:
            return f"A {selected_traits[0].lower()} individual."
        else:
            traits_text = ", ".join(t.lower() for t in selected_traits[:-1])
            return f"A {traits_text} and {selected_traits[-1].lower()} individual."
    
    def generate_npc_for_interaction(self, 
                                    interaction_type: NPCInteractionType,
                                    name: Optional[str] = None,
                                    npc_type: Optional[NPCType] = None,
                                    npc_subtype: Optional[str] = None,
                                    relationship: NPCRelationship = NPCRelationship.NEUTRAL,
                                    location: Optional[str] = None,
                                    description: Optional[str] = None,
                                    occupation: Optional[str] = None,
                                    is_persistent: bool = False) -> NPC:
        """
        Generate an NPC customized for a specific type of interaction.
        
        Args:
            interaction_type: The type of interaction this NPC is for
            name: Optional name for the NPC (generated if None)
            npc_type: Type of NPC (determined from interaction if None)
            npc_subtype: Optional subtype (e.g., 'boss_dragon', 'merchant')
            relationship: Initial relationship with the player
            location: Where the NPC is located
            description: Optional description of the NPC
            occupation: Optional occupation
            is_persistent: Whether this NPC should be saved persistently
            
        Returns:
            An NPC with appropriate stats for the interaction
        """
        # Determine NPC type if not provided
        if npc_type is None:
            # Default types based on interaction
            type_mapping = {
                NPCInteractionType.COMBAT: NPCType.ENEMY,
                NPCInteractionType.SOCIAL: NPCType.NEUTRAL,
                NPCInteractionType.COMMERCE: NPCType.MERCHANT,
                NPCInteractionType.QUEST: NPCType.QUEST_GIVER,
                NPCInteractionType.INFORMATION: NPCType.NEUTRAL,
                NPCInteractionType.SERVICE: NPCType.SERVICE,
                NPCInteractionType.MINIMAL: NPCType.BACKGROUND
            }
            npc_type = type_mapping.get(interaction_type, NPCType.NEUTRAL)
        
        # Generate name if not provided
        if name is None:
            # Try to use a name pool for the subtype if specified
            if npc_subtype and npc_subtype in self.name_pools:
                name = self.generate_random_name(name_pool=npc_subtype)
            else:
                name = self.generate_random_name()
        
        # Select template based on NPC type and subtype
        template = self._select_template(npc_type, npc_subtype)
        
        # Generate personality
        personality = self._generate_personality(template)
        
        # Create the NPC
        npc = NPC(
            name=name,
            npc_type=npc_type,
            relationship=relationship,
            location=location,
            description=description or f"A {npc_subtype or npc_type.name.lower()} named {name}.",
            occupation=occupation,
            personality=personality,
            is_persistent=is_persistent
        )
        
        # Store the subtype in known_information if provided
        if npc_subtype:
            if not npc.known_information:
                npc.known_information = {}
            npc.known_information["subtype"] = npc_subtype
        
        # Generate stats appropriate for the interaction
        if interaction_type != NPCInteractionType.MINIMAL:
            self._generate_stats(npc, interaction_type, template)
        
        logger.info(f"Generated NPC for {interaction_type.name} interaction: {npc.name}")
        return npc
    
    def enhance_npc_for_new_interaction(self, 
                                       npc: NPC, 
                                       interaction_type: NPCInteractionType) -> None:
        """
        Enhance an existing NPC with additional details for a new type of interaction.
        
        Args:
            npc: The NPC to enhance
            interaction_type: The new interaction type
        """
        # Get subtype if stored in known_information
        npc_subtype = None
        if npc.known_information and "subtype" in npc.known_information:
            npc_subtype = npc.known_information["subtype"]
        
        # If stats haven't been generated yet, generate them
        if not npc.has_stats():
            template = self._select_template(npc.npc_type, npc_subtype)
            self._generate_stats(npc, interaction_type, template)
            logger.info(f"Generated stats for existing NPC {npc.name} for {interaction_type.name} interaction")
        
        # For combat interactions, ensure combat-related stats are suitable
        if (interaction_type == NPCInteractionType.COMBAT and 
            npc.has_stats() and 
            npc.get_stat(StatType.STRENGTH) < 10):
            
            # Check if this NPC should use boss stats
            is_boss = npc_subtype and "boss" in npc_subtype.lower()
            
            # Boost combat stats more significantly for bosses
            for stat_type in [StatType.STRENGTH, StatType.DEXTERITY, StatType.CONSTITUTION]:
                current_val = npc.get_stat(stat_type) or 8
                if current_val < 12:
                    if is_boss:
                        new_val = random.randint(14, 18)  # Higher stats for bosses
                    else:
                        new_val = random.randint(12, 16)
                    npc.stats_manager.set_base_stat(stat_type, new_val)
                    logger.debug(f"Boosted {stat_type.name} for NPC {npc.name} from {current_val} to {new_val}")
        
        # Similar adjustments for other interaction types
        elif (interaction_type == NPCInteractionType.SOCIAL and 
              npc.has_stats() and 
              npc.get_stat(StatType.CHARISMA) < 10):
            
            # Boost social stats
            for stat_type in [StatType.CHARISMA, StatType.WISDOM]:
                current_val = npc.get_stat(stat_type) or 8
                if current_val < 12:
                    new_val = random.randint(12, 16)
                    npc.stats_manager.set_base_stat(stat_type, new_val)
        
        # Add more personality details if needed
        if not npc.personality:
            template = self._select_template(npc.npc_type, npc_subtype)
            npc.personality = self._generate_personality(template)
    
    def generate_enemy_npc(self, 
                          name: Optional[str] = None,
                          enemy_type: str = "generic",
                          level: int = 1,
                          location: Optional[str] = None) -> NPC:
        """
        Generate an enemy NPC for combat.
        
        Args:
            name: Optional name for the enemy
            enemy_type: Type of enemy (e.g., "bandit", "wolf", "guard")
            level: Level of the enemy, affects stats
            location: Where the enemy is located
            
        Returns:
            An NPC ready for combat
        """
        # Check if we have a template for this enemy type
        if enemy_type in self.templates:
            template = self.templates[enemy_type]
        else:
            # Fallback to generic enemy template
            template = self._select_template(NPCType.ENEMY)
        
        # Generate name if not provided
        if name is None:
            if enemy_type in self.name_pools:
                name = self.generate_random_name(name_pool=enemy_type)
            else:
                name = f"{enemy_type.capitalize()} {random.choice(['Minion', 'Warrior', 'Brute', 'Thug'])}"
        
        # Create the enemy NPC
        npc = NPC(
            name=name,
            npc_type=NPCType.ENEMY,
            relationship=NPCRelationship.HOSTILE,
            location=location,
            description=f"A hostile {enemy_type} named {name}."
        )
        
        # Generate combat stats
        stats_manager = StatsManager()
        
        # Scale stats based on level
        level_modifier = max(0, (level - 1) * 2)  # +2 to stats per level
        
        # Generate primary stats based on template and level
        stat_distributions = template.get("stat_distributions", {})
        
        for stat_type in StatType:
            stat_name = stat_type.name
            if stat_name in stat_distributions:
                min_val = stat_distributions[stat_name].get("min", 8) + level_modifier
                max_val = stat_distributions[stat_name].get("max", 14) + level_modifier
                value = random.randint(min_val, max_val)
            else:
                # Default range if not specified
                value = random.randint(8 + level_modifier, 14 + level_modifier)
            
            # Set the stat value
            stats_manager.set_base_stat(stat_type, value)
        
        # Set the stats manager on the NPC
        npc.stats_manager = stats_manager
        npc.stats_generated = True
        
        logger.info(f"Generated enemy NPC: {npc.name} (Level {level})")
        return npc
    
    def _generate_equipment(self, npc: NPC, interaction_type: NPCInteractionType, template: Dict[str, Any]) -> None:
        """
        Generate and equip appropriate equipment for an NPC.
        
        Args:
            npc: The NPC to generate equipment for
            interaction_type: The type of interaction (determines equipment type)
            template: The template used for generation
        """
        logger.debug(f"Initializing equipment manager for NPC {npc.name}")
        
        # Initialize equipment manager for the NPC
        npc.equipment_manager = EquipmentManager()
        
        # For now, skip complex equipment generation to avoid hangs
        # TODO: Implement full equipment generation after fixing core issues
        if interaction_type == NPCInteractionType.COMBAT:
            logger.debug(f"Skipping complex equipment generation for combat NPC {npc.name} (temporary)")
            # Just ensure the NPC has an equipment manager
            return
            
        logger.info(f"Basic equipment manager created for NPC {npc.name}")
        return
    
    def _determine_equipment_rarity(self, npc_type: NPCType, is_boss: bool) -> ItemRarity:
        """Determine the base equipment rarity for an NPC."""
        if is_boss:
            return random.choice([ItemRarity.RARE, ItemRarity.EPIC])
        elif npc_type == NPCType.ENEMY:
            return random.choice([ItemRarity.COMMON, ItemRarity.UNCOMMON])
        elif npc_type == NPCType.NEUTRAL:
            return ItemRarity.COMMON
        else:
            return ItemRarity.COMMON
    
    def _determine_equipment_quality(self, npc_type: NPCType, is_boss: bool) -> float:
        """Determine the quality modifier for NPC equipment."""
        if is_boss:
            return random.uniform(1.1, 1.4)  # 10-40% better than base
        elif npc_type == NPCType.ENEMY:
            return random.uniform(0.9, 1.2)  # -10% to +20%
        else:
            return random.uniform(0.8, 1.1)  # -20% to +10%
    
    def _generate_npc_weapons(self, npc: NPC, template_loader, item_factory, base_rarity: ItemRarity, quality_modifier: float) -> None:
        """Generate weapons for an NPC."""
        # Get weapon templates
        weapon_templates = template_loader.get_templates_by_type(ItemType.WEAPON)
        
        if not weapon_templates:
            logger.warning("No weapon templates available for NPC equipment generation")
            return
        
        # Filter by rarity (allow up to one rarity level higher)
        suitable_templates = {}
        rarity_values = {
            ItemRarity.COMMON: 1,
            ItemRarity.UNCOMMON: 2,
            ItemRarity.RARE: 3,
            ItemRarity.EPIC: 4,
            ItemRarity.LEGENDARY: 5
        }
        
        max_rarity_value = rarity_values.get(base_rarity, 1) + 1  # Allow one level higher
        for template_id, template in weapon_templates.items():
            template_rarity_value = rarity_values.get(template.rarity, 1)
            if template_rarity_value <= max_rarity_value:
                suitable_templates[template_id] = template
        
        if not suitable_templates:
            suitable_templates = weapon_templates  # Fallback to all weapons
        
        # Select a random weapon template
        template = random.choice(list(suitable_templates.values()))
        
        # Create variation with quality modifier
        weapon = ItemVariationGenerator.create_variation(template, quality_modifier)
        
        # Try to equip the weapon
        if npc.equipment_manager.can_equip_item(weapon):
            success = npc.equipment_manager.equip_item(weapon)
            if success:
                logger.debug(f"Equipped {weapon.name} to NPC {npc.name}")
            else:
                logger.warning(f"Failed to equip {weapon.name} to NPC {npc.name}")
        else:
            logger.debug(f"Cannot equip {weapon.name} to NPC {npc.name} - requirements not met")
    
    def _generate_npc_armor(self, npc: NPC, template_loader, item_factory, base_rarity: ItemRarity, quality_modifier: float) -> None:
        """Generate armor for an NPC."""
        # Get armor templates
        armor_templates = template_loader.get_templates_by_type(ItemType.ARMOR)
        
        if not armor_templates:
            logger.warning("No armor templates available for NPC equipment generation")
            return
        
        # Filter by rarity (similar to weapons)
        rarity_values = {
            ItemRarity.COMMON: 1,
            ItemRarity.UNCOMMON: 2,
            ItemRarity.RARE: 3,
            ItemRarity.EPIC: 4,
            ItemRarity.LEGENDARY: 5
        }
        
        max_rarity_value = rarity_values.get(base_rarity, 1) + 1
        suitable_templates = {}
        for template_id, template in armor_templates.items():
            template_rarity_value = rarity_values.get(template.rarity, 1)
            if template_rarity_value <= max_rarity_value:
                suitable_templates[template_id] = template
        
        if not suitable_templates:
            suitable_templates = armor_templates  # Fallback
        
        # Try to equip armor for different slots
        armor_slots = [EquipmentSlot.CHEST, EquipmentSlot.HEAD]  # Focus on main armor pieces
        for slot in armor_slots:
            # Find suitable armor for this slot
            slot_templates = {}
            for template_id, template in suitable_templates.items():
                if hasattr(template, 'equip_slots') and template.equip_slots:
                    if slot.value in template.equip_slots or slot in template.equip_slots:
                        slot_templates[template_id] = template
            
            if not slot_templates:
                continue  # No armor for this slot
            
            # 70% chance to equip armor in each slot (not all NPCs need full armor)
            if random.random() > 0.7:
                continue
            
            # Select and create armor
            template = random.choice(list(slot_templates.values()))
            armor = ItemVariationGenerator.create_variation(template, quality_modifier)
            
            # Try to equip
            if npc.equipment_manager.can_equip_item(armor):
                success = npc.equipment_manager.equip_item(armor)
                if success:
                    logger.debug(f"Equipped {armor.name} to NPC {npc.name}")
    
    def _apply_equipment_to_stats(self, npc: NPC) -> None:
        """Apply equipment stat modifiers to the NPC's stats manager."""
        # Temporarily disabled to prevent performance issues
        # TODO: Implement proper batched modifier application
        logger.debug(f"Skipping equipment stat application for NPC {npc.name} (temporary)")
        return
