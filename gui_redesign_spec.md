# GUI Redesign Specification

## Overview

This document outlines the redesign of the RPG Game GUI based on discussions and analysis of both the current implementation and legacy version. The goal is to create a more immersive, visually appealing, and functional interface that supports all game features while maintaining an RPG atmosphere.

## Visual Theme

- **Style**: Medieval/fantasy themed with parchment, scrolls, and wooden/stone elements
- **Color Scheme**: Warm colors (browns, golds, amber) with dark accents
- **Font**: Fantasy-style font for headings, readable serif font for game text
- **Assets**: Custom PNG images for all UI elements stored in `images/gui/` folder

## Core Layout Structure

1. **Main Background**: Full window background image
2. **Left Panel**: Collapsible menu for game controls
3. **Center Area**: Game output with scroll background
4. **Bottom Area**: Command input panel
5. **Right Panel**: Collapsible tabbed panel for character info, inventory, and journal
6. **Top Bar**: Game title and music controls

## Detailed Component Specifications

### Main Window

- Fixed size window with configurable resolution settings
- Cannot be manually resized by user
- Recommended default size: 1280x720px
- All components scale proportionally with resolution changes

### Left Menu Panel

- Width: ~100px when expanded, ~30px when collapsed
- Height: Full height of window (minus any top/bottom bars)
- Toggle Button: Small icon at top of panel
- Slide animation: 300ms duration, ease-in-out
- Menu Buttons:
  - New Game
  - Load Game
  - Save Game
  - Settings
  - Quit
- Each button uses custom PNG with normal/hover/pressed states
- Vertical arrangement with equal spacing

### Game Output Area

- Background: Scroll/parchment image
- Text: Dark color on light parchment background
- Size: Fills main area (center of screen)
- Scrolling: Automatic to newest content
- Fade effect at bottom for new text appearance
- Higher vertical space than current implementation
- Skill Check Display: Appears centered in this area when triggered

### Command Input Panel

- Position: Bottom of window, full width
- Height: ~40-50px
- Background: Themed input background image
- Text input: Left-aligned
- Send button: Right-aligned with themed design
- No spacing between this and the game output area

### Right Panel (Tabbed Interface)

- Width: ~250-300px when expanded, ~30px when collapsed
- Height: Full height of window (minus any top/bottom bars)
- Tab Headers: Character, Inventory, Journal
- Clicking active tab header: Toggles panel collapse/expand
- Collapse Animation: 300ms slide effect
- Default State: Expanded with Character tab active

### Character Tab
- Maintains current functionality with improved theming
- Character portrait and basic info at top
- Primary stats grouped with appropriate styling
- Resource bars (Health, Mana, Stamina) with themed styling
- Derived stats section
- Equipment section with improved visual representation

### Inventory Tab
- Maintains current functionality with improved theming
- Equipment slots with visual representation
- Item list with icons and descriptions
- Item details panel
- Currency display in themed format

### Journal Tab (New)
- Three sections with tab or dropdown navigation:
  1. **Character Information**: Persistent biography that evolves with gameplay
  2. **Quests**: Lists of active, completed, and failed quests
  3. **Personal Notes**: Player-created or automatically added from gameplay
- Each section should have appropriate styling
- Notes should be editable by player
- Save/load functionality tied to game state

### Title and Music Controls

- Game title: Centered at top with banner image
- Music controls: Top-right corner with themed icons
  - Play/Pause button
  - Next Track button
  - Volume slider with themed track/thumb

### Status Bar

- Position: Bottom of window, below command input
- Height: ~20px
- Content: Current location, in-game time, game speed indicator
- Style: Subtle, non-distracting

## Time Progression System

- Normal mode: Each command advances time by 1 minute
- Combat mode: Each action advances time by seconds
- Barter mode: One-time advancement of 1-5 minutes for entire transaction
- Display current in-game time in status bar
- Time format: "Day X, HH:MM" (24-hour format)

## Resource Management

### Image Files (`images/gui/` folder)
- `main_background.png` - Full window background
- `scroll_background.png` - Text output area background
- `button_normal.png`, `button_hover.png`, `button_pressed.png` - Button states
- `panel_background.png` - Right panel background
- `tab_active.png`, `tab_inactive.png` - Tab header states
- `title_banner.png` - Game title banner
- `input_background.png` - Command input area background
- `toggle_button_left.png`, `toggle_button_right.png` - Panel toggle buttons
- Music control icons:
  - `music_play.png`, `music_pause.png` - Play/pause toggle
  - `music_next.png` - Next track button
  - `music_volume.png` - Volume slider thumb

### Components to Create/Update
- `gui/components/menu_panel.py` - Collapsible left menu
- `gui/components/game_output.py` - Enhanced output area (update existing)
- `gui/components/command_input.py` - Styled command input (update existing)
- `gui/components/character_sheet.py` - Enhanced character panel (update existing)
- `gui/components/inventory_panel.py` - Enhanced inventory panel (update existing)
- `gui/components/journal_panel.py` - New journal panel (create new)
- `gui/components/skill_check_display.py` - Already implemented
- `gui/components/status_bar.py` - Update with time progression display
- `gui/main_window.py` - Update to integrate all components

## Implementation Strategy

1. Create a ResourceManager class to handle all image loading
2. Implement each component individually, testing as you go
3. Use absolute positioning with QStackedLayout to ensure proper layering
4. Implement animations using QPropertyAnimation
5. Create a theme system that can be easily modified
6. Ensure all components scale proportionally with resolution changes
7. Implement save/load for journal content
8. Connect the journal system to the LLM for information access

## Integration with LLM

- Journal content should be serializable and loadable for LLM access
- Add special commands for LLM to access journal content:
  - `{JOURNAL_READ:section:topic}` - Read specific journal entries
  - `{JOURNAL_WRITE:section:topic:content}` - Update journal entries
- LLM should be able to reference character info, quest details, and player notes
- System prompt updates needed to inform LLM of journal capability

## Time Progression Integration

- Update GameLoop to handle different time advancement rates based on game mode
- Add event system to notify UI of time changes
- Implement mode tracking system (normal, combat, barter)

## User Experience Considerations

- All transitions should be smooth and responsive
- Text should be easily readable against backgrounds
- Critical information should be immediately visible
- Theming should enhance immersion without sacrificing usability
- Journal system should feel integrated with gameplay, not a separate feature
- Panel collapse/expand should not disrupt ongoing gameplay

## Next Steps

1. Create the necessary folder structure in `images/gui/`
2. Design and create all required image assets
3. Implement the left menu panel and collapsible functionality
4. Update the game output area with new styling
5. Implement the right panel tab system with collapsible functionality
6. Create the journal panel component
7. Integrate time progression display in the status bar
8. Add music controls
9. Test all components together in the main window
10. Connect journal system to LLM
