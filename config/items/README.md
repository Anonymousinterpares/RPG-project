# Item Configuration

This directory contains JSON configuration files that define the various items available in the game. These files serve as templates from which specific item instances are created.

## Item Configuration Files

The item definitions are categorized into the following files:

### base_weapons.json

Defines weapon templates including:
- Basic weapons (swords, bows, daggers, etc.)
- Weapon properties (damage, range, speed)
- Weapon categories and types
- Required attributes and restrictions (implicitly via stats or tags)
- Equip slots (e.g., main_hand, off_hand, two_hand)

### base_armor.json

Defines armor templates including:
- Armor types (light, medium, heavy - often indicated by tags or stats)
- Armor pieces (helmet, chest, gloves, etc.)
- Protection values and resistance stats
- Weight and mobility effects
- Equip slots

### consumables.json

Defines consumable items including:
- Potions and elixirs
- Food and drinks
- Scrolls and magical consumables
- Temporary effect items (defined via stats/effects)
- Crafting materials (if applicable)

### miscellaneous.json

Defines miscellaneous items including:
- Quest items
- Valuables and currency items (if not handled separately)
- Tools and utilities
- Decorative items
- Container items

## Item Definition Format

Each JSON file contains a list of item objects. Each item object defines a specific item template using the following key-value pairs:

*   `id` (String, Required): A unique identifier for the item template. Used internally to reference the item. Conventionally includes `template_` prefix.
*   `name` (String, Required): The display name of the item shown to the player.
*   `description` (String, Required): A textual description of the item shown to the player.
*   `item_type` (String, Required): The general category of the item (e.g., "weapon", "armor", "consumable", "misc").
*   `rarity` (String, Required): The rarity level of the item (e.g., "common", "uncommon", "rare", "epic", "legendary"). Affects drop rates, value, and potentially stats.
*   `weight` (Float, Required): The weight of the item, affecting inventory capacity.
*   `value` (Integer, Required): The base monetary value of the item in the smallest currency unit (e.g., copper).
*   `is_equippable` (Boolean, Required): Whether the item can be equipped by the player character.
*   `equip_slots` (List of Strings, Required if `is_equippable` is true): A list of equipment slots the item can occupy (e.g., `["main_hand", "off_hand"]`, `["chest"]`, `["two_hand"]`).
*   `stats` (List of Objects, Optional): A list defining the item's effects on character statistics or other properties. Each stat object contains:
    *   `name` (String, Required): The internal name of the stat being modified (e.g., "damage", "defense", "health_regen").
    *   `value` (Number, Required): The magnitude of the stat modification.
    *   `display_name` (String, Required): How the stat is presented to the player (e.g., "Damage", "Armor Class").
    *   `is_percentage` (Boolean, Optional): If true, the `value` is treated as a percentage modifier. Defaults to false if omitted.
*   `is_stackable` (Boolean, Required): Whether multiple instances of this item can occupy a single inventory slot.
*   `durability` (Integer, Optional): The maximum durability of the item. If omitted, the item may be considered indestructible or durability is not applicable.
*   `tags` (List of Strings, Optional): A list of tags used for categorization, filtering, or applying specific game logic (e.g., `["metal", "sword", "quest_item"]`).

### Example (Short Sword from base_weapons.json)

```json
 {
     "id": "template_sword_short",
     "name": "Short Sword",
     "description": "A simple one-handed sword designed for close combat.",
     "item_type": "weapon",
     "rarity": "common",
     "weight": 2.0,
     "value": 1000,
     "is_equippable": true,
     "equip_slots": ["main_hand", "off_hand"],
     "stats": [
         {
             "name": "damage",
             "value": 5,
             "display_name": "Damage"
         },
         {
             "name": "attack_speed",
             "value": 1.2,
             "display_name": "Attack Speed"
         }
     ],
     "is_stackable": false,
     "durability": 100,
     "tags": ["weapon", "sword", "metal", "one-handed"]
 }
```

## Adding or Modifying Items

To add a new item:
1.  Determine the appropriate category (weapon, armor, consumable, misc) and open the corresponding `.json` file (e.g., `base_weapons.json`).
2.  Add a new JSON object to the list, following the format described above.
3.  Ensure the `id` field is unique across all item configuration files.
4.  Fill in all required fields and any relevant optional fields.

To modify an existing item:
1.  Locate the item's definition within the relevant `.json` file using its `id` or `name`.
2.  Modify the desired key-value pairs, ensuring the structure remains valid JSON.

## Usage

These item templates are typically loaded by an `ItemFactory` or similar system at game startup. This factory is then used to create specific instances of items based on their template `id`.

Example (Conceptual Python):
```python
from core.inventory.item_factory import ItemFactory # Assuming this path

# Create an item factory instance
item_factory = ItemFactory()

# Load item templates from the config/items directory
item_factory.load_templates_from_directory("config/items")

# Create an item instance from a template
short_sword_instance = item_factory.create_item("template_sword_short")

print(f"Created item: {short_sword_instance.name}")
```
*(Note: The exact class names and methods might differ in the actual implementation.)*

## Item Generation

The game uses these templates in several ways:

1.  Direct creation of specific items (e.g., quest rewards, shop inventory).
2.  As a base for generating variations with randomized properties (e.g., magical affixes).
3.  As base templates or references for LLM-generated items, ensuring consistency.
4.  Populating loot tables and treasure chests.

## Narrative Item Integration

Templates can serve as references for systems like a `NarrativeItemManager` when creating items based on narrative descriptions or player actions. This helps to:

1.  Match narrative descriptions to existing item types.
2.  Determine appropriate stats and properties based on the template.
3.  Generate variations consistent with the game world and narrative context.
4.  Maintain game balance and item consistency.
