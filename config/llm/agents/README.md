# LLM Agent Configurations

This directory contains configuration files for the different LLM-powered agents used in the game.

## Agent Configuration Files

### narrator.json

Configuration for the `NarratorAgent` which generates narrative content:
- System prompts and instructions
- Context structuring guidelines
- Response formatting requirements
- Example inputs and outputs
- Special command formats for item generation

### rulechecker.json / rule_checker.json

Configuration for the `RuleCheckerAgent` which validates player actions:
- Rule definitions and constraints
- Validation criteria
- Response formats for allowed and disallowed actions
- Examples of valid and invalid actions

### contextevaluator.json / context_evaluator.json

Configuration for the `ContextEvaluatorAgent` which analyzes game context:
- Importance scoring criteria
- Context categorization rules
- Memory relevance evaluation
- Context window management guidelines

## Configuration Format

Agent configuration files follow this general structure:

```json
{
  "version": "1.0",
  "name": "Agent Name",
  "description": "Agent functionality description",
  "system_prompt": "Detailed instructions for the LLM",
  "examples": [
    {
      "input": "Example input",
      "context": "Example context",
      "output": "Example output"
    }
  ],
  "parameters": {
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 1000
  }
}
```

## Agent-Specific Parameters

Each agent may have specific parameters:

- **Narrator**: Creativity settings, command formats, narrative style
- **RuleChecker**: Strictness level, rule priorities, feedback detail
- **ContextEvaluator**: Memory weights, context categories, token budget

## Usage

These configuration files are loaded by the respective agent classes:

```python
from core.agents.narrator import NarratorAgent
from core.llm.settings_manager import SettingsManager

# Load settings
settings_manager = SettingsManager()
settings_manager.load_settings()

# Create agent with settings
narrator = NarratorAgent(settings_manager)
```

## Notes

- Duplicate files with different naming conventions exist for compatibility
- Agent configurations can be overridden at runtime for special scenarios
- Advanced settings should be modified cautiously as they affect LLM behavior
