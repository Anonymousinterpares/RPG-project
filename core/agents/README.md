# Agents Module

The `core/agents` module provides a system of specialized, LLM-powered agents designed to manage different aspects of the game's narrative, rules, and context. These agents work together, coordinated by the `AgentManager`, to create a dynamic and interactive game experience.

## Purpose

The primary goal of the agent system is to leverage Large Language Models (LLMs) to:

*   Generate rich, descriptive, and contextually relevant game narrative.
*   Interpret player input and translate it into game actions and narrative consequences.
*   Enforce game rules consistently and fairly.
*   Manage the flow of information, ensuring agents have the necessary context (game state, memories, etc.) to perform their tasks.
*   Allow for modular design, where different agents handle specific responsibilities.

## Key Components

### `base_agent.py`

Defines the foundational elements for all agents:

*   **`BaseAgent`**: An abstract base class providing common functionality like configuration loading (`config/llm/agents/<agent_name>.json`), interaction with the `LLMManager`, basic prompt construction, and settings reloading. All specific agents inherit from this class.
*   **`AgentContext`**: A dataclass holding the information passed to an agent for processing a request. This includes game state, player state, world state, player input, conversation history, relevant memories, and potentially additional context retrieved during processing.
*   **`AgentResponse`**: A dataclass containing the output from an agent, including the generated text (`content`), any extracted commands (`commands`), and metadata (like LLM usage details).

### `agent_manager.py`

*   **`AgentManager`**: A singleton class that acts as the central coordinator for the agent system. It orchestrates the processing pipeline for player input:
    1.  Creates the initial `AgentContext`.
    2.  (Optional) Calls the `ContextEvaluatorAgent` to enrich the context with summaries or relevant memories.
    3.  (Optional) Calls the `RuleCheckerAgent` to validate the player's intended action based on game rules and state. If invalid, the process stops and returns feedback.
    4.  Calls the `NarratorAgent` to generate an initial narrative response.
    5.  Checks the Narrator's response for specific data retrieval commands (e.g., `{GET_INVENTORY}`, `{GET_STATS}`).
    6.  If data retrieval commands are present, it uses `data_retrieval_commands.py` to fetch the required data from the `GameState`.
    7.  Calls the `NarratorAgent` *again* with the enhanced context (including the retrieved data) to generate the final narrative.
    8.  Processes any narrative item commands (e.g., `{ITEM:potion}`) using the `NarrativeItemManager`.
    9.  Extracts remaining commands (e.g., `{STAT_CHECK}`, `{QUEST_UPDATE}`) from the final narrative.
    10. Returns the final narrative text and the list of commands to the game loop for execution.

### `narrator.py`

*   **`NarratorAgent`**: Responsible for generating the game's narrative content.
    *   Takes the `AgentContext` (potentially enriched by the `AgentManager`) and crafts descriptive text based on player actions, game state, and world events.
    *   Instructed via its system prompt to use specific data retrieval commands (`{GET_INVENTORY}`, `{GET_STATS}`, `{GET_QUESTS}`, `{GET_LOCATION_INFO}`) when the player asks for game information, rather than hallucinating details.
    *   Can embed other commands (e.g., `{ITEM_CREATE}`, `{STAT_CHECK}`, `{MUSIC_MOOD}`) within its narrative to trigger game state changes or checks.

### `rule_checker.py`

*   **`RuleCheckerAgent`**: Enforces game rules and validates player actions.
    *   Receives the `AgentContext` and evaluates if the player's input/action is permissible based on game rules, physics, character capabilities, and current state.
    *   Provides feedback if an action is invalid.
    *   Includes logic to prevent cheating (e.g., tracking looted entities).
    *   Can perform skill checks (`perform_skill_check`) when triggered by commands like `{STAT_CHECK}`.

### `context_evaluator.py`

*   **`ContextEvaluatorAgent`**: Analyzes the game context to determine relevance and provide summaries.
    *   Evaluates the current `AgentContext`, including game state, conversation history, and potentially memories.
    *   Generates concise context summaries to help other agents (especially the `NarratorAgent`) focus on the most relevant information.
    *   Can identify key elements in the context and evaluate the importance of memories.
    *   Includes basic caching for context summaries based on location and input hash.

### `data_retrieval_commands.py`

*   Contains helper functions used by the `AgentManager` to process data retrieval commands issued by the `NarratorAgent`. It fetches specific information (like inventory lists, character stats, quest details, location info) directly from the `GameState`.

## Interaction Flow

1.  Player input is received by the main game loop.
2.  The game loop calls `AgentManager.process_input()`, passing the current `GameState` and player input.
3.  `AgentManager` creates an `AgentContext`.
4.  `AgentManager` optionally calls `ContextEvaluatorAgent` and `RuleCheckerAgent`.
5.  `AgentManager` calls `NarratorAgent` (potentially twice if data retrieval is needed).
6.  `AgentManager` processes narrative items and extracts final commands.
7.  `AgentManager` returns the final narrative text and commands to the game loop.
8.  The game loop displays the narrative and executes the commands using the `CommandProcessor`.

## Dependencies

The `agents` module primarily depends on:

*   `core.base`: For `GameState`, `CommandProcessor`, configuration (`get_config`).
*   `core.llm`: For `LLMManager`, `LLMResponse`, `ProviderType`.
*   `core.inventory`: For `NarrativeItemManager` (used by `AgentManager`).
*   `core.stats`: For `StatsManager` (used by `RuleCheckerAgent` for skill checks).
*   `core.utils`: For logging configuration.

## Configuration

Each agent type (`Narrator`, `RuleChecker`, `ContextEvaluator`) loads its specific settings from a corresponding JSON file in `config/llm/agents/` (e.g., `config/llm/agents/narrator.json`). These files control:

*   LLM provider and model selection (or defaults).
*   LLM parameters (temperature, max tokens).
*   System prompt templates.
*   Inclusion/exclusion of context elements (history, memories).

## Extending the System

To create a new type of agent:

1.  Create a new Python file (e.g., `my_new_agent.py`).
2.  Define a class that inherits from `BaseAgent`.
3.  Implement the required abstract methods (`_generate_system_prompt`, `supports_command`).
4.  Override other methods (`_prepare_messages`, `process`) as needed for custom logic.
5.  Create a configuration file in `config/llm/agents/my_new_agent.json`.
6.  Integrate the new agent into the `AgentManager`'s workflow if necessary.

## Usage Example

```python
from core.agents.agent_manager import get_agent_manager
from core.base.state import get_state_manager # Assuming state is managed

# Get the singleton instances
agent_manager = get_agent_manager()
state_manager = get_state_manager()

# Ensure game state is loaded or initialized
# state_manager.load_game(...) or state_manager.new_game(...)

# Process player input
player_input = "I search the chest for traps"
narrative_text, commands = agent_manager.process_input(
    game_state=state_manager.state,
    player_input=player_input
)

# Display the narrative
print(narrative_text)

# Process any commands returned by the agents
if commands:
    results = agent_manager.process_commands(state_manager.state, commands)
    # Handle command results...
