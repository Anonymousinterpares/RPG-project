# Configuration Module

The `config` directory contains configuration files for various aspects of the game. This document focuses on the main configuration files located directly within this directory. Configuration for specific modules like items, combat, etc., can be found in their respective subdirectories.

## Main Configuration Files

These files control core aspects of the game and system:

*   **`game_config.json`**: Defines general game settings.
    *   `version`: The current game version.
    *   `title`: The title displayed for the game window.
    *   `default_save_slot`: The save slot used by default (e.g., for auto-saves).
    *   `auto_save_interval`: How often the game auto-saves (in seconds).
    *   `max_save_slots`: The maximum number of manual save slots available.
*   **`gui_config.json`**: Controls settings related to the Graphical User Interface (GUI).
    *   `resolution`: The display resolution (width and height).
    *   `fullscreen`: Whether the game runs in fullscreen mode.
    *   `theme`: The visual theme used for the GUI.
    *   `font_size`: The default font size for UI elements.
    *   `show_fps`: Whether to display the current frames per second.
*   **`llm_config.json`**: Manages settings for Large Language Model (LLM) integration.
    *   `enabled`: A simple flag to enable or disable all LLM features globally. More detailed LLM configurations are likely found in the `llm/` subdirectory.
*   **`system_config.json`**: Contains system-level configurations.
    *   `log_level`: The minimum severity level for log messages (e.g., INFO, DEBUG).
    *   `log_to_file`: Whether logs should be written to a file.
    *   `log_to_console`: Whether logs should be output to the console.
    *   `debug_mode`: Enables or disables general debug features.
    *   `save_dir`: The directory where save game files are stored (relative to the project root).
    *   `log_dir`: The directory where log files are stored (relative to the project root).

## Configuration Format

All configuration files use JSON format for easy editing and parsing. Most configuration files follow a similar structure:

```json
{
  "version": "1.0",
  "name": "Configuration Name",
  "description": "Description of the configuration",
  "settings": {
    "setting1": "value1",
    "setting2": "value2",
    "nested_setting": {
      "subsetting1": "value3"
    }
  }
}
```

## Usage

Configuration files are typically loaded by their respective modules at startup. For example:

*   Game configuration might be loaded by a central game manager.
*   GUI settings are likely loaded by the GUI initialization module.
*   System settings are used by logging and file management components.

## Editing Configuration

Configuration files can be edited manually with a text editor. Ensure the JSON format remains valid after editing. Some settings might also be adjustable through in-game menus.
