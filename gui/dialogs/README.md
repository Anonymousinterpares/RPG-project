# GUI Dialogs

The `dialogs` directory contains dialog windows used in the game's graphical interface.

## Available Dialogs

### new_game_dialog.py

The `NewGameDialog` handles new game creation:
- Character name input
- Starting options selection
- Game difficulty settings (if applicable)
- Character customization options

### load_game_dialog.py

The `LoadGameDialog` provides save game loading functionality:
- Lists available save files
- Displays save metadata (character, date, location)
- Allows selection and loading of saves
- Delete save option

### save_game_dialog.py

The `SaveGameDialog` handles game saving:
- Save name input
- Overwrite confirmation
- Save metadata preview
- Quick save option

### settings/ (directory)

Contains dialogs for various settings:
- Game settings (difficulty, time scale, etc.)
- Graphics settings (resolution, effects, etc.)
- Sound settings (volume, music, effects)
- LLM settings (provider, model, parameters)

## Implementation

All dialogs are implemented as modal windows using PySide6 (Qt):
- Inherit from `QDialog`
- Provide result handling through `accept()` and `reject()`
- Include validation for user input
- Maintain consistent styling

## Common Features

All dialogs share these common features:
- Consistent styling and layout
- Cancel and confirm buttons
- Input validation
- Error and notification handling
- Persistence of settings

## Usage

Dialogs are typically shown from the main window or game menu:

```python
from gui.dialogs.new_game_dialog import NewGameDialog

# Create and show the dialog
dialog = NewGameDialog(parent=self)
result = dialog.exec_()

if result == QDialog.Accepted:
    # Get dialog data
    player_name = dialog.get_player_name()
    
    # Use the data
    self.engine.initialize(new_game=True, player_name=player_name)
```

## Future Enhancements

1. More comprehensive settings dialogs
2. Advanced character creation options
3. Save file management (backup, restore, etc.)
4. Configuration editors for game data
5. Help and tutorial dialogs
