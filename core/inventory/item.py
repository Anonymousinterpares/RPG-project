"""
Item data structure module.

This module defines the core Item class used to represent
game items with their properties, stats, and behaviors.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Union, Any
import uuid
from datetime import datetime

from core.inventory.item_enums import ItemType, ItemRarity, EquipmentSlot
from core.inventory.item_stat import ItemStat
from core.inventory.item_effect import DiceRollEffect # Added import


@dataclass
class Item:
    """
    A game item with properties and stats.
    
    This class represents items that can be acquired, used, and equipped by the player.
    Items can have various types, rarities, and statistics.
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    item_type: ItemType = ItemType.MISCELLANEOUS
    rarity: ItemRarity = ItemRarity.COMMON
    weight: float = 0.0
    value: int = 0  # Value in copper coins
    icon_path: Optional[str] = None
    
    # Equipment-specific properties
    is_equippable: bool = False
    equip_slots: List[EquipmentSlot] = field(default_factory=list)
    
    # Item stats and modifiers
    stats: List[ItemStat] = field(default_factory=list)
    dice_roll_effects: List[DiceRollEffect] = field(default_factory=list) # New field
    
    # Usage properties
    is_consumable: bool = False
    is_stackable: bool = False
    stack_limit: int = 1
    quantity: int = 1
    is_quest_item: bool = False
    
    # Item condition
    durability: Optional[int] = None
    current_durability: Optional[int] = None
    is_destroyed: bool = False
    
    # Item knowledge tracking
    known_properties: Set[str] = field(default_factory=set)
    discovered_at: Optional[str] = None  # ISO format datetime
    
    # Meta properties
    tags: List[str] = field(default_factory=list)
    template_id: Optional[str] = None
    is_template: bool = False
    source: str = "template"  # "template", "loot", "quest", "narrative", "player_created", etc.
    
    # Custom properties for narrative items
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize derived properties and defaults."""
        if isinstance(self.item_type, str):
            try:
                self.item_type = ItemType(self.item_type)
            except ValueError:
                self.item_type = ItemType.MISCELLANEOUS
        if isinstance(self.rarity, str):
            try:
                self.rarity = ItemRarity(self.rarity)
            except ValueError:
                self.rarity = ItemRarity.COMMON
            
        processed_equip_slots = []
        for slot_val in self.equip_slots:
            if isinstance(slot_val, str):
                try:
                    processed_equip_slots.append(EquipmentSlot(slot_val))
                except ValueError:
                    pass 
            elif isinstance(slot_val, EquipmentSlot):
                processed_equip_slots.append(slot_val)
        self.equip_slots = processed_equip_slots
            
        if not self.discovered_at:
            self.discovered_at = datetime.now().isoformat()
            
        if not self.known_properties:
            self.known_properties = {
                "name", "item_type", "weight", "is_stackable", "quantity",
                "is_quest_item", "tags", "icon_path", "rarity"
            }
            if self.is_equippable:
                self.known_properties.add("is_equippable")
                self.known_properties.add("equip_slots")
            
        if not self.is_template:
            self.known_properties.add("description")
            self.known_properties.add("value")
            if self.durability is not None: 
                self.known_properties.add("durability")
                self.known_properties.add("current_durability")
            
            # Automatically make core combat effects/stats known for instances
            # This ensures players can see what their items do by default
            if self.dice_roll_effects:
                self.known_properties.add("dice_roll_effects")
            
            if self.stats:
                self.known_properties.add("stats")
                for stat_obj in self.stats:
                    self.known_properties.add(f"stat_{stat_obj.name}")
            
            # Ensure custom properties that act as stats are also known by default
            # This covers the gap where resist properties were hidden
            if self.custom_properties:
                    self.known_properties.add("custom_properties")
                    for key in self.custom_properties.keys():
                        self.known_properties.add(f"custom_{key}")

        if self.durability is not None and self.current_durability is None:
            self.current_durability = self.durability
            
    def get_stat(self, name: str) -> Optional[ItemStat]:
        """Get a stat by name."""
        for stat in self.stats:
            if stat.name == name:
                return stat
        return None
    
    def add_stat(self, name: str, value: Union[int, float, str, bool], 
                display_name: Optional[str] = None, is_percentage: bool = False) -> None:
        """Add or update a stat."""
        existing_stat = self.get_stat(name)
        if existing_stat:
            existing_stat.value = value
            if display_name:
                existing_stat.display_name = display_name
            existing_stat.is_percentage = is_percentage
        else:
            new_stat = ItemStat(name, value, display_name, is_percentage)
            self.stats.append(new_stat)
    
    def remove_stat(self, name: str) -> bool:
        """Remove a stat by name. Returns True if successful."""
        for i, stat in enumerate(self.stats):
            if stat.name == name:
                self.stats.pop(i)
                return True
        return False
    
    def damage(self, amount: int) -> bool:
        """Apply damage to the item. Returns True if the item was destroyed."""
        if self.durability is None or self.current_durability is None:
            return False  # Item doesn't have durability
            
        self.current_durability = max(0, self.current_durability - amount)
        
        if self.current_durability == 0:
            self.is_destroyed = True
            return True
            
        return False
    
    def repair(self, amount: int) -> int:
        """Repair the item. Returns the amount of durability restored."""
        if (self.durability is None or self.current_durability is None 
            or self.is_destroyed):
            return 0  # Item can't be repaired
            
        old_durability = self.current_durability
        self.current_durability = min(self.durability, self.current_durability + amount)
        
        return self.current_durability - old_durability
    
    def discover_property(self, property_name: str) -> bool:
        """Mark a property as known to the player. Returns True if newly discovered."""
        if property_name in self.known_properties:
            return False
            
        self.known_properties.add(property_name)
        return True
    
    def is_property_known(self, property_name: str) -> bool:
        """Check if a property is known to the player."""
        return property_name in self.known_properties
    
    def get_known_value(self, property_name: str) -> Any:
        """Get a property value if it's known, otherwise None."""
        if not self.is_property_known(property_name):
            return None
            
        if property_name == "stats":
            return [stat for stat in self.stats 
                   if f"stat_{stat.name}" in self.known_properties]
        
        return getattr(self, property_name, None)
    
    def discover_stat(self, stat_name: str) -> bool:
        """Mark a stat as known to the player."""
        property_name = f"stat_{stat_name}"
        return self.discover_property(property_name)
    
    def is_stat_known(self, stat_name: str) -> bool:
        """Check if a stat is known to the player."""
        property_name = f"stat_{stat_name}"
        return self.is_property_known(property_name)
    
    def get_value_in_currency(self) -> Dict[str, int]:
        """Convert the value (in copper) to gold, silver, copper."""
        gold = self.value // 10000
        silver = (self.value % 10000) // 100
        copper = self.value % 100
        
        return {
            "gold": gold,
            "silver": silver,
            "copper": copper
        }