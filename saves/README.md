# Saves Directory

The `saves` directory contains saved game files.

## Save File Format

Save files are stored as JSON files with a `.save` extension. Each save file contains:

- Player state (character information, inventory, etc.)
- World state (location, time, quest status, etc.)
- Game state (settings, flags, etc.)
- Memory context (dialogue history, important events, etc.)

## File Naming

Save files follow the naming convention:

```
playername_YYYY-MM-DD_HHMMSS.save
```

For example:
```
Adventurer_2023-09-10_143245.save
```

## Save Management

Save files are managed by the `SaveManager` class in `core/utils/save_manager.py`, which provides functions for:

- Saving games
- Loading games
- Listing available saves
- Retrieving save metadata
- Deleting saves

## Manual Backup

It's recommended to periodically back up the contents of this directory to prevent loss of save data.

## In-Game Usage

Saves can be created and loaded using the following in-game commands:

- `save [name]` - Save the current game with an optional name
- `load [name]` - Load a game by name or show a list if no name is provided
- `list_saves` - List all available save files
