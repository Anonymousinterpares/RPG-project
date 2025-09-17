# LLM Module

The `llm` module manages the integration with large language models (LLMs) for narrative generation and game content creation.

## Key Components

### llm_manager.py

The `LLMManager` class is the main interface for LLM interactions:

- Sends prompts to LLM providers
- Receives and processes LLM responses
- Manages context window size and token usage
- Handles rate limiting and retries
- Provides diagnostic functions

### provider_manager.py

The `ProviderManager` class manages different LLM providers:

- Initializes provider clients with appropriate API keys
- Selects the appropriate provider based on configuration
- Handles provider-specific parameters and features
- Manages fallback between providers
- Validates provider availability

### settings_manager.py

The `SettingsManager` class manages LLM settings:

- Loads settings from configuration files
- Provides access to LLM parameters (temperature, top_p, etc.)
- Validates and sanitizes settings
- Manages provider-specific settings

### settings_cli.py

Provides a command-line interface for managing LLM settings:

- Viewing current settings
- Modifying provider settings
- Testing provider connections
- Running diagnostics

## Current Functionality

1. Support for multiple LLM providers (OpenAI, Anthropic, Google)
2. Configuration management for LLM parameters
3. Fallback mechanisms when providers are unavailable
4. Diagnostic tools for testing and troubleshooting
5. Token usage tracking and optimization
6. Command-line utility for settings management

## Planned Features

1. More sophisticated context management
2. Dynamic prompt generation based on game state
3. Enhanced error handling and recovery
4. Support for additional LLM providers
5. Better token usage optimization

## Usage Example

```python
from core.llm.llm_manager import LLMManager
from core.llm.settings_manager import SettingsManager

# Create a settings manager
settings_manager = SettingsManager()
settings_manager.load_settings()

# Create an LLM manager
llm_manager = LLMManager(settings_manager)

# Get a completion
prompt = "Describe a dark forest at night."
response = llm_manager.get_completion(prompt)

# Display the response
print(response)
```

## LLM Toggle Command

The game includes a special command `/llm` that can be used to:

- Check the current LLM status
- Toggle LLM on/off during gameplay
- Switch between different LLM providers

This allows for fallback to a non-LLM gameplay mode when needed.
