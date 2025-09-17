# Inventory Module

The `inventory` module manages all item-related functionality in the game, including items, equipment, and currency.

## Key Components

### Item System

- `item.py` - Defines the `Item` class and related data structures
- `item_enums.py` - Enumerations for item types, rarities, equipment slots, etc.
- `item_stat.py` - Item statistics and properties
- `item_modifier.py` - Modifiers that can be applied to items
- `item_factory.py` - Creates items from templates or specifications
- `item_template_loader.py` - Loads item templates from configuration files
- `item_variation_generator.py` - Generates variations of items with different properties
- `item_serialization.py` - Handles serialization/deserialization of items for saving/loading

### Inventory Management

- `inventory_manager.py` - Main inventory management class
- `inventory_base.py` - Base inventory functionality
- `inventory_item_operations.py` - Item operations like adding, removing, etc.
- `inventory_limits.py` - Weight and slot limits for inventory
- `equipment_manager.py` - Manages equipment slots and equipped items
- `currency_manager.py` - Manages in-game currency (copper, silver, gold)

### Narrative Item System

- `narrative_item_manager.py` - Main class for narrative-based item creation
- `narrative_item_creation.py` - Creates items from narrative descriptions
- `narrative_item_discovery.py` - Manages item discovery and property revelation
- `narrative_item_mappings.py` - Maps narrative descriptions to item properties

### Command Handlers

- `inventory_commands.py` - Command handlers for inventory-related commands
- `inventory_commands_2.py` - Additional command handlers
- `inventory_commands_3.py` - Additional command handlers

## Current Functionality

1. Item creation from templates and specifications
2. Item management (add, remove, equip, unequip)
3. Currency management
4. Equipment slot management with proper handling of two-handed weapons
5. Item damage and destruction
6. Item discovery (revealing item properties over time)
7. Narrative-driven item creation through LLM integration
8. Combat loot generation
9. Item parsing from narrative text

## Planned Features

1. Advanced item crafting
2. Item decay and maintenance
3. Magic item effects
4. More sophisticated item generation algorithms
5. Enhanced item UI representation

## Usage Example

```python
from core.inventory.inventory_manager import InventoryManager
from core.inventory.item_factory import ItemFactory

# Create an inventory manager
inventory = InventoryManager()

# Create an item factory
item_factory = ItemFactory()
item_factory.load_templates()

# Create an item
sword = item_factory.create_item_from_spec("iron_sword")

# Add to inventory
inventory.add_item(sword)

# Equip the item
inventory.equip_item(sword.id, "main_hand")
```
