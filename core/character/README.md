# Core Character Module: Just-in-Time NPC System

This module (`core/character`) implements a dynamic system for managing Non-Player Characters (NPCs) within the game. Its core feature is a "just-in-time" generation approach, where NPCs are created and enhanced only when needed for specific interactions. This allows the game to efficiently manage a potentially large number of NPCs without requiring full generation of all characters at the start, optimizing performance and memory usage.

## Core Concept: Just-in-Time Generation

The primary innovation of this system is the "just-in-time" generation of NPCs. Instead of generating all NPCs with complete details up front, the system:

1.  Creates NPCs with minimal information when they are first encountered or mentioned (e.g., by name).
2.  Generates or enhances NPC stats, personality, and other details only when required for a specific type of interaction (e.g., combat, social dialogue, trading).
3.  Persists only the information that matters for future interactions, focusing on NPCs designated as `is_persistent`.

This approach offers several benefits:
-   Optimizes memory usage by only storing necessary information for active or important NPCs.
-   Creates more appropriate NPCs tailored to specific interaction types (e.g., stronger combat stats for enemies, higher charisma for merchants).
-   Allows narrative systems (like an LLM) to freely introduce NPCs without worrying about immediate, detailed implementation.
-   Saves processing time by avoiding the generation of unused NPCs or attributes.

## System Components

The `core/character` module is divided into several Python files for better organization and maintainability:

### 1. `npc_base.py`
-   **Purpose:** Defines the core data structures for NPCs.
-   **Key Classes/Enums:**
    -   `NPC`: The central dataclass representing an NPC, holding attributes like `id`, `name`, `npc_type`, `relationship`, `location`, `description`, `stats_manager`, `memories`, `inventory` (basic list), etc.
    -   `NPCMemory`: Dataclass representing a recorded interaction or event involving an NPC.
    -   `NPCType`: Enum defining NPC roles (MERCHANT, ENEMY, QUEST_GIVER, etc.).
    -   `NPCRelationship`: Enum defining the NPC's disposition towards the player (HOSTILE, FRIENDLY, NEUTRAL, etc.).
    -   `NPCInteractionType`: Enum defining the context of an interaction (COMBAT, SOCIAL, COMMERCE, etc.), used to determine necessary stats/details.
-   **Functionality:** Basic serialization (`to_dict`) and deserialization (`from_dict`) methods for `NPC` and `NPCMemory`.

### 2. `npc_manager.py`
-   **Purpose:** Manages the collection of active `NPC` objects currently loaded in memory.
-   **Key Class:** `NPCManager`.
-   **Functionality:** Acts as a central registry, providing methods for adding, removing, and retrieving NPCs using indices for ID, name (case-insensitive), and location.

### 3. `npc_generator.py`
-   **Purpose:** Responsible for generating NPC details, including stats, personality, and names.
-   **Key Class:** `NPCGenerator`.
-   **Functionality:**
    -   Loads NPC templates from configuration (`config/character/npc_templates.json`). Templates define stat ranges, personality traits, and name pools.
    -   Generates random names based on pools.
    -   Generates stats (`StatsManager` instance) appropriate for a given `NPCInteractionType` using template distributions.
    -   Enhances stats of existing NPCs for new interaction types.
    -   Generates basic personality descriptions.
-   **Dependencies:** `core.stats.stats_manager`, `config/character/npc_templates.json`.

### 4. `npc_creator.py`
-   **Purpose:** Provides a higher-level interface for creating and enhancing NPCs.
-   **Key Class:** `NPCCreator`.
-   **Functionality:**
    -   Uses `NPCGenerator` and `NPCManager`.
    -   Provides methods to create specific NPC types (`create_enemy`, `create_merchant`, etc.).
    -   Implements the core "get or create" logic (`get_or_create_npc`) for just-in-time instantiation.
    -   Handles enhancing existing NPCs when they are needed for a new interaction context (`enhance_npc_for_interaction`).

### 5. `npc_persistence.py`
-   **Purpose:** Manages the saving and loading of *persistent* NPCs to/from disk storage.
-   **Key Class:** `NPCPersistence`.
-   **Functionality:**
    -   Saves individual persistent NPCs (`save_npc`) or all persistent NPCs (`save_all_persistent_npcs`) to JSON files (named `{npc_id}.json`) in a specified directory (e.g., `saves/npcs/`).
    -   Loads NPCs from these files (`load_npc`, `load_all_npcs`).
    -   Handles cleanup of old/unused NPC files.
    -   Provides import/export functionality for NPC data.

### 6. `npc_memory.py`
-   **Purpose:** Manages the recording, retrieval, and lifecycle of NPC memories.
-   **Key Class:** `NPCMemoryManager`.
-   **Functionality:**
    -   Records new `NPCMemory` instances associated with an NPC (`record_interaction`).
    -   Retrieves memories based on recency, importance, location, or specific events (like relationship changes).
    -   Summarizes interactions with an NPC.
    -   Provides relevant memories as context for new interactions (`get_relevant_context_for_interaction`).
    -   Prunes old or unimportant memories to manage data size.

### 7. `background_generator.py`
-   **Purpose:** Generates or enhances narrative backgrounds for characters using an external LLM.
-   **Key Class:** `BackgroundGenerator`.
-   **Functionality:** Constructs prompts based on character data (race, class, etc.) and sends requests to the `LLMManager` to generate or improve background text.
-   **Dependencies:** `core.llm.llm_manager`.

### 8. `npc_system.py`
-   **Purpose:** Acts as a facade, integrating all the above components into a unified interface.
-   **Key Class:** `NPCSystem`.
-   **Functionality:**
    -   Initializes and provides access to the `NPCManager`, `NPCCreator`, `NPCPersistence`, and `NPCMemoryManager`.
    -   Provides high-level methods for common operations like loading/saving state, getting/creating NPCs (`get_or_create_npc`), preparing NPCs for interaction (`prepare_npc_for_interaction`), recording interactions, and retrieving interaction context.
    -   Simplifies interaction with the NPC subsystem for other parts of the game.

## Key Concepts & Data Flow

-   **NPC Representation:** The `NPC` class is the core data structure, holding all information about a non-player character. It relies on `core.stats.StatsManager` to handle numerical attributes and derived stats.
-   **Dynamic Stats:** Stats are not always pre-defined. `NPCGenerator` creates or enhances the `StatsManager` instance for an NPC based on the `NPCInteractionType` when needed.
-   **Memory:** Interactions are logged as `NPCMemory` objects, managed by `NPCMemoryManager`. These memories inform future interactions and can provide context to narrative systems.
-   **Persistence:** NPCs marked with `is_persistent=True` are saved by `NPCPersistence` to JSON files in the `saves/npcs/` directory (or as configured). `NPCSystem` orchestrates loading and saving the overall state.
-   **Configuration:** NPC generation relies heavily on templates defined in `config/character/npc_templates.json`.

## Interaction Types

The system uses `NPCInteractionType` to determine the necessary level of detail and specific stats required for an NPC:

-   **COMBAT**: Requires full combat stats (STR, DEX, CON, HP, Attack, Defense, etc.).
-   **SOCIAL**: Focuses on social stats (CHA, WIS).
-   **COMMERCE**: Focuses on relevant stats for trading (CHA, INT).
-   **QUEST**: May require specific knowledge or flags related to quests.
-   **INFORMATION**: Focuses on knowledge-related stats (INT, WIS).
-   **SERVICE**: May require specific skills or flags related to services offered.
-   **MINIMAL**: Requires only basic identification information; no stats are generated initially.

## Using the NPC System

The primary interface is the `NPCSystem` class, typically accessed via a central game state manager or a dedicated function like `get_npc_system()`.

```python
# Example: Assuming npc_system is an instance of NPCSystem

# Get or create an NPC for a specific interaction
# If "Guard Captain" exists, enhance for combat if needed. If not, create him.
npc, is_new = npc_system.get_or_create_npc(
    name="Guard Captain",
    interaction_type=NPCInteractionType.COMBAT,
    location="City Gates",
    npc_subtype="guard_captain" # Optional: uses specific template if available
)

# Record an interaction
memory = npc_system.record_interaction(
    npc_or_name="Guard Captain", # Can use name or NPC object
    interaction_type=NPCInteractionType.SOCIAL,
    description="Player asked about recent patrols.",
    location="City Gates",
    importance=5
)

# Get context for an LLM or dialogue system
context = npc_system.get_context_for_interaction(
    "Guard Captain",
    NPCInteractionType.SOCIAL
)
# context dictionary contains npc details, relevant stats, and recent/important memories
```

## Integration with LLM & Narrative

The just-in-time approach is well-suited for integration with LLM-driven narrative engines:

1.  The LLM can mention NPCs by name without needing them to exist beforehand.
2.  `npc_system.get_or_create_npc` handles creating a minimal NPC record.
3.  When an interaction occurs (e.g., player talks to the NPC), `npc_system.prepare_npc_for_interaction` ensures the NPC has the necessary details (like social stats).
4.  `npc_system.get_context_for_interaction` provides the LLM with the NPC's current state, relevant stats, and past interactions (memories) to inform its response generation.
5.  `BackgroundGenerator` can be invoked to create richer backstories for important NPCs introduced by the LLM.

This allows the narrative engine to dynamically populate the world with characters without the burden of pre-defining every detail.
