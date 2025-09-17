# GUI Components

The `components` directory contains reusable UI components used in the game's graphical interface.

## Available Components

### character_sheet.py

The `CharacterSheet` component displays character information:
- Name, level, and basic stats
- Health, mana, and other resources
- Character attributes and skills
- Experience and progression

### command_input.py

The `CommandInput` component manages player input:
- Command text entry
- Command history navigation
- Auto-completion (if implemented)
- Command validation and feedback

### game_menu.py

The `GameMenu` component provides game menu functionality:
- New game, save, load options
- Settings and configuration
- Help and information
- Exit game functionality

### game_output.py

The `GameOutput` component displays game text and narrative:
- Scrollable text area for game output
- Formatting for different message types
- Image embedding (if applicable)
- History retention

### inventory_panel.py

The `InventoryPanel` component displays the player's inventory:
- Item listing with icons and basic info
- Equipment slots and equipped items
- Item interaction (use, equip, examine, etc.)
- Item filtering and sorting

### status_bar.py

The `StatusBar` component shows game status information:
- Current time and location
- Character status indicators
- Game mode indicators (LLM status, etc.)
- Quick access to common functions

## Implementation

All components are implemented using PySide6 (Qt) and follow a consistent pattern:
- Inherit from appropriate Qt widget classes
- Implement signals for event communication
- Provide public methods for external control
- Maintain internal state as needed

## Signals and Slots

Components communicate using Qt's signals and slots mechanism:
- Components emit signals when important events occur
- Other components or the main window connect to these signals
- Connected slots handle the events and update accordingly

## Styling

Components use stylesheets for visual styling:
- Common styles are defined in a central location
- Components can have specific style overrides
- Theme support is partially implemented

## Future Enhancements

1. Enhanced inventory visualization
2. More detailed character information display
3. Expandable panels and resizing
4. Theme selection and customization
5. Animated transitions and effects
