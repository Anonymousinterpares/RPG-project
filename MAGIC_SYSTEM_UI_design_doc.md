# Design Document: Magic System UI/UX & Gameplay Integration

This document outlines the user interface, user experience, and gameplay mechanics for the magic system in Aetheris: The Shattered Planes. The design prioritizes a simple, elegant UI while enabling both deterministic, UI-driven actions and flexible, LLM-assisted text commands.

## 1. The Grimoire: A Dedicated UI for Magic

To provide a clean and organized space for spell management, a new "Grimoire" tab will be added to the main UI.

### 1.1. Location and Access

*   **Python & Web UI:** A new tab labeled "Grimoire" will be added to the right-hand panel, alongside "Character," "Inventory," and "Journal."

### 1.2. Layout and Interaction

The Grimoire will feature an **Animated Accordion List** for spell organization, following Concept A but with refined interactions.

*   **Structure:**
    *   The list will be organized by **Magic Systems** (e.g., "Song Weaving," "Ash Walking," "Planar Anchoring"). These act as collapsible headers.
    *   Clicking a Magic System header will smoothly expand or collapse its section, revealing the spells known within that system. This will be animated to create a fluid user experience.
        *   **GUI:** Implemented using `QPropertyAnimation` on the section's height.
        *   **WebUI:** Implemented using CSS transitions on `max-height`.
*   **Spell Display:**
    *   **Tooltip on Hover:** Hovering over a spell name will instantly display a clean, simple tooltip containing essential information: **Mana Cost**, **Casting Time**, and a brief **Effect Summary**.
    *   **Details on Double-Click:** Double-clicking a spell name will open a dedicated, non-modal **Spell Details Dialog**.

### 1.3. Spell Details Dialog

This popup provides an in-depth look at a selected spell.

*   **Behavior:**
    *   The dialog is "singleton" in nature; only one can be open at a time. If a player double-clicks another spell while one is open, the first dialog will close, and a new one will open for the second spell.
    *   It can be closed independently by clicking an "X" icon in its top-right corner.
*   **Content:** The dialog will clearly present all relevant spell data from `magic_systems.json`, such as:
    *   **Spell Name & Thematic Description**
    *   **Mana Cost**
    *   **Casting Time**, **Range**, and **Target Type**
    *   **Detailed Effects:** A clear, player-friendly breakdown of what the spell does (e.g., "Deals 20-28 Radiant Damage," "Reduces target's Defense for 2 rounds").
    *   **Magic System & School Tags**

### 1.4. The "Cast" Button

A "Cast" button will be present within the Grimoire tab, likely next to the spell details area.

*   **State:**
    *   **In-Combat:** The button is **enabled**.
    *   **Narrative Mode:** The button is **disabled** and greyed out.

## 2. Casting Mechanics: In-Combat

During combat, players have two distinct methods for casting spells.

### 2.1. Method 1: Casting via Text Input (LLM-Assisted)

This method provides flexibility and accommodates natural player language.

1.  **Player Input:** The player types a command like `cast sun lance on the ghoul` or simply `cast sunlance`.
2.  **LLM Agent Interception:** The input is routed to the appropriate LLM Agent (e.g., `CombatNarrator`).
3.  **Spell Verification:**
    *   The Agent requests a list of the player's currently known spells from the Game Engine.
    *   It performs a **fuzzy match** on the spell name provided by the player against the known spell list.
    *   **Guardrails:** The matching will have a confidence threshold to prevent over-matching (e.g., matching "Fireball" to "Ice Storm"). It should be robust enough to handle common typos (e.g., "sunlance" vs. "Sun Lance").
4.  **Target Resolution:**
    *   If the player specifies a target, the Agent uses it.
    *   If no target is specified, **automatic targeting** rules apply:
        *   **Hostile Spell:** If there is only one enemy, it becomes the target. If there are multiple enemies, a **random enemy is chosen** as a fallback.
        *   **Friendly/Self Spell:** If there are no other allies, the player is the target. If allies are present, the **player is the default fallback target**.
5.  **Execution:** If a valid spell and target are determined, the Agent issues a structured, internal command to the Game Engine (e.g., `execute_cast("sun_lance", "ghoul_1")`) to apply the spell's mechanical effects.
6.  **Failure:** If no reasonably close spell match is found, the Agent outputs a system message to the combat log: "Spell not found. Please check your Grimoire and try again."

### 2.2. Method 2: Casting via UI Button (Deterministic)

This method provides a reliable, error-free way to cast spells.

1.  **Player Action:** The player selects a spell in the Grimoire tab and clicks the enabled "Cast" button.
2.  **Target Selection:** A dropdown menu or context menu appears next to the "Cast" button.
    *   If the spell is hostile, the list contains the names of all **active enemies** in the combat.
    *   If the spell is friendly or self-targeted, the list contains the player's name and the names of all **active allies**.
3.  **Execution:** The player clicks a target from the list. This action sends a direct, structured command to the Game Engine (`execute_cast("sun_lance", "ghoul_2")`), bypassing the LLM for interpretation.

## 3. Casting Mechanics: Narrative Mode

Outside of combat, magic is a tool for storytelling and problem-solving, driven entirely by text input.

1.  **UI State:** The "Cast" button in the Grimoire is **disabled**.
2.  **Player Input:** The player types a command, such as `cast song of mending on the broken amulet` or `I use planar sight to look for magical auras`.
3.  **LLM Agent Evaluation:** The `NarratorAgent` processes the input.
    *   It performs the same **fuzzy match** for the spell name as in combat.
    *   Crucially, it **evaluates the narrative context** to determine if a suitable target exists. This context includes the current location description, present NPCs, and key items mentioned in recent text.
4.  **Narrative Outcome:**
    *   **Success:** If a suitable spell and target are found, the LLM narrates the action and its outcome (e.g., "You hum the Song of Mending, and the fractured pieces of the amulet slowly knit back together.").
    *   **Partial Success/Failure:** If the spell is valid but the target is inappropriate or circumstances are not right, the LLM narrates a logical outcome (e.g., "You attempt to cast Sun Lance at the sky, but the brilliant beam dissipates harmlessly into the clouds.").
    *   **Spell Not Found:** If the spell is not recognized, a system message informs the player.

## 4. Engine & Data Integration Requirements

To support this system, the core game engine must provide the following functionalities, accessible to both the UI and the LLM Agents:

*   **`get_known_spells(character_id)`:** Returns a list of spell objects or dictionaries for the given character, containing all necessary data for the UI and for LLM verification.
*   **`get_combat_targets(target_type)`:** Returns a list of valid targets currently in combat, filtered by type (e.g., `ENEMY`, `ALLY`).
*   **`execute_cast_spell(spell_id, target_id)`:** A core command that takes a spell ID and a target ID, resolves all mechanical effects (resource costs, damage, status effects), and updates the game state.
*   **`get_narrative_context_entities()`:** Returns a list of NPCs, key items, and interactable objects currently present in the narrative scene for the LLM to use for targeting in Narrative Mode.

***