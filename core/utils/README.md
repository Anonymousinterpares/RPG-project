# Utils Module

The `utils` module contains utility functions and classes used throughout the game.

## Key Components

### dotdict.py

Provides the `DotDict` class, which is a dictionary that allows access to items using dot notation:

```python
data = DotDict({"a": 1, "b": {"c": 2}})
value = data.b.c  # Access nested values with dot notation
```

### json_utils.py

Utilities for JSON serialization and deserialization:

- `EnhancedJSONEncoder` for serializing custom objects
- Functions for loading and saving JSON files
- JSON validation utilities

### logging_config.py

Configures the logging system for the game:

- Sets up file and console logging
- Configures log rotation
- Defines log levels and formats
- Provides utility functions for logging

### save_manager.py

The `SaveManager` class handles saving and loading game states:

- Serializes and deserializes game state
- Manages save files
- Provides save file listing and metadata
- Handles save file version compatibility

### time_utils.py

Utilities for time management and conversion:

- Conversion between real time and game time
- Formatting time strings
- Time calculations
- Timestamp creation and parsing

## Current Functionality

1. Dot notation for dictionary access
2. Enhanced JSON serialization for custom objects
3. Comprehensive logging configuration
4. Save/load functionality with game state serialization
5. Time conversion and formatting utilities

## Usage Examples

### DotDict

```python
from core.utils.dotdict import DotDict

# Create a DotDict
config = DotDict({
    "game": {
        "speed": 1.0,
        "start_time": "08:00"
    }
})

# Access values with dot notation
speed = config.game.speed
```

### SaveManager

```python
from core.utils.save_manager import SaveManager
from core.base.state import StateManager

# Create state and save managers
state_manager = StateManager()
save_manager = SaveManager()

# Save the current game
save_manager.save_game(state_manager.state, "mysave")

# List available saves
saves = save_manager.list_saves()

# Load a save
loaded_state = save_manager.load_game("mysave")
state_manager.state = loaded_state
```

### Time Utils

```python
from core.utils.time_utils import format_game_time

# Format a game time
time_str = format_game_time(hours=14, minutes=30)  # "14:30"
```
