# GUI Module

## Purpose

The `gui` module provides the primary desktop graphical user interface (GUI) for the RPG game. It allows players to interact with the game world, manage their character, view game output, and access various game functions like saving, loading, and settings configuration.

## Framework and Dependencies

*   **Framework:** The GUI is built using the **PySide6** library, the official Python bindings for the Qt framework.
*   **Core Dependency:** It relies heavily on the `core` module, particularly `core.base.engine.GameEngine`, for game logic, state management, and processing player commands.
*   **Other Libraries:** Standard Python libraries (`os`, `logging`, `concurrent.futures`, etc.).

## GUI Structure

The main interface is organized within the `MainWindow` (`main_window.py`) and consists of several key areas:

1.  **Main Window (`MainWindow`):** The top-level container holding all other UI elements. It manages the overall layout, window properties, and connections between components and the game engine.
2.  **Left Menu Panel (`components/menu_panel.py`):** A collapsible panel on the left side providing access to main game actions: New Game, Save Game, Load Game, Settings, LLM Settings, and Exit.
3.  **Center Area:**
    *   **Game Output (`components/game_output.py`):** A styled, scrollable text area displaying narrative, system messages, and game master descriptions.
    *   **Command Input (`components/command_input.py`):** A text field at the bottom for players to enter commands, with history functionality.
4.  **Right Panel (`components/right_panel.py`):** A collapsible, tabbed panel on the right side displaying dynamic game information:
    *   Character Sheet (`components/character_sheet.py`)
    *   Inventory (`components/inventory_panel.py`)
    *   Journal (`components/journal_panel.py`)
5.  **Status Bar (`components/status_bar.py`):** Located at the bottom of the window, displaying current game status like location, time, and game speed.
6.  **Dialogs (`dialogs/`):** Modal windows for specific interactions like character creation, saving/loading, and configuring settings.

## Directory Structure

*   **`main_window.py`**: Defines the `MainWindow` class, the central hub of the GUI application.
*   **`components/`**: Contains reusable UI widgets that make up the main interface:
    *   `character_sheet.py`: Displays player character stats, attributes, and other details.
    *   `combat_display.py`: (Likely) Widget for displaying combat information.
    *   `command_input.py`: The input field for player commands.
    *   `game_menu.py`: (Likely related to the main menu panel or in-game menus).
    *   `game_output.py`: The styled text area for displaying game narrative and messages.
    *   `inventory_panel.py`: Displays and manages the player's inventory.
    *   `journal_panel.py`: Displays quests and player notes.
    *   `menu_panel.py`: The main collapsible menu on the left.
    *   `right_panel.py`: The collapsible, tabbed panel on the right.
    *   `skill_check_display.py`: (Likely) Widget for displaying skill check results.
    *   `stat_allocation_widget.py`: Interactive widget for allocating stat points during character creation.
    *   `status_bar.py`: The status bar at the bottom of the window.
*   **`dialogs/`**: Contains modal dialog windows for specific tasks:
    *   `character_creation_dialog.py`: Handles the process of creating a new character, including stat allocation.
    *   `load_game_dialog.py`: Allows players to select and load a saved game.
    *   `new_game_dialog.py`: (Potentially simpler or older version of character creation).
    *   `save_game_dialog.py`: Allows players to name and save the current game state.
    *   `settings/`: Subdirectory containing dialogs and components for configuring game and LLM settings (`settings_dialog.py`, `llm_settings_dialog.py`, etc.).
*   **`utils/`**: Contains utility functions and classes supporting the GUI:
    *   `init_settings.py`: Initializes default application settings.
    *   `resource_manager.py`: Manages loading and access to UI resources like icons and images.

## Interaction with Core Engine

The GUI interacts with the `core.base.engine.GameEngine` in the following ways:

1.  **Sending Commands:** User input from `CommandInputWidget` is sent to the `GameEngine.process_command()` method. This processing happens in a separate thread (`CommandWorker` in `main_window.py`) using `QThread` to prevent freezing the UI during potentially long operations (like LLM calls).
2.  **Receiving Updates:** The `GameEngine` uses signals (specifically `output_generated`) to send game output (narrative, system messages) back to the `MainWindow`. The `MainWindow` then directs this output to the appropriate widget (`GameOutputWidget`).
3.  **State Display:** The `MainWindow` periodically checks the `GameEngine`'s state (`state_manager`) to update UI elements like the character sheet, inventory, journal (in the `RightPanel`), and the `StatusBar`. Signals/slots and timers (`QTimer`) are used for efficient updates.

## Current Functionality

*   **Themed Game Interface:** Stylized with thematic elements, custom graphics, and configurable appearance via settings.
*   **Character Creation System:** Full character creation with race/path selection, stat allocation, descriptions, and optional LLM integration.
*   **Main Game Loop Interface:** Displays game output, accepts player commands.
*   **Dynamic Information Panels:** Collapsible right panel with tabs for Character Sheet, Inventory, and Journal, updated based on game state.
*   **Game Management:** Dialogs for starting new games, saving progress, and loading saved games.
*   **Settings Configuration:** Dialogs to adjust display, style, and LLM provider settings.
*   **LLM Integration:** Threaded AI processing for narrative generation and gameplay assistance, toggleable via settings.
*   **Status Display:** Status bar showing current location, game time, and speed.
*   **Music Controls:** Basic controls for background music playback.

## Planned Features (Review Needed)

*   Level-up stat allocation dialog.
*   Enhanced inventory visualization with equipment slots.
*   Quest log interface with filtering.
*   Map/location visualization.
*   Additional character appearance customization.
*   (Time progression system with visual indicators - Already partially implemented in status bar).
*   (Journal system with categorized entries - Basic journal exists).

## Usage

The GUI is typically launched using the main project entry point or a dedicated script:

```bash
python main.py
```

or

```bash
python run_gui.py
```

## Implementation Details

*   **Pattern:** Follows principles similar to Model-View-Controller (MVC), where the `GameEngine` acts as the Model, UI components are the View, and `MainWindow` and component logic serve as Controllers.
*   **Asynchronicity:** Uses PySide6's signal/slot mechanism and `QThread` for handling background tasks (like command processing) without blocking the main UI thread.
*   **Styling:** Leverages Qt's stylesheet system (`.qss`, similar to CSS) and custom widgets for a consistent and themeable look and feel, managed partly through `utils/resource_manager.py` and settings.
*   **Modularity:** UI elements are broken down into reusable components within the `components/` directory.
