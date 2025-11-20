# Hybrid Skill System Implementation Report

## Executive Summary
A comprehensive **Hybrid Skill System** has been successfully implemented, combining **Point Buy** mechanics for character creation with **Usage-Based Growth** for organic progression. This system is fully integrated into the backend engine and the frontend GUI.

## Key Components Implemented

### 1. Data & Backend (`core/stats/`)
*   **Enhanced `Stat` Model:** The `Stat` dataclass now tracks `exp` (current experience) and `exp_to_next` (threshold for leveling).
*   **Extended Configuration:**
    *   `config/skills.json`: Added 15 new lore-specific skills (e.g., *Facet Logic*, *Ash Walking*, *Resonance Sensing*).
    *   `config/character/classes.json`: Added `class_skills` lists and `skill_points_per_level` for all classes.
*   **Logic Updates in `StatsManager`:**
    *   `award_skill_exp(skill_name, amount)`: Handles XP accumulation and rank-up logic (exponential scaling).
    *   `perform_skill_check(...)`: Now calculates and awards XP automatically based on Difficulty and Outcome (Failure yields 1.5x XP).
*   **New `SkillAllocator` Class:** Manages the "Point Buy" logic:
    *   **Class Skills:** Cost 1 Point.
    *   **Cross-Class Skills:** Cost 2 Points.
    *   **Origin Skills:** Start at Rank 1 (Free).

### 2. GUI Components (`gui/components/`)
*   **New `SkillAllocationWidget`:** A dedicated widget for the creation wizard.
    *   Lists all skills dynamically.
    *   Highlights Class Skills (Green) and Origin Skills (Gold).
    *   Displays real-time point costs and remaining pool.
    *   Fully integrated with the theme manager.
*   **Updated `SkillCheckDisplay`:** Now visualizes XP gains after a check, including a "LEVEL UP!" notification.

### 3. Integration (`gui/dialogs/`)
*   **Updated `CharacterCreationDialog`:**
    *   Redesigned "Tab 3" (formerly just Stats) to be a **Split View**: "Stats & Skills".
    *   Left Column: Attribute Allocation (STR, DEX, etc.).
    *   Right Column: Skill Allocation (Stealth, Arcana, etc.).
    *   Seamlessly updates available skills and points based on Race, Class, Origin, and Intelligence score changes.
    *   Validation logic ensures all skill points are spent before creation.

## Usage Instructions

### For Players
1.  **New Game:** Navigate to the "Stats & Skills" tab.
2.  **Customize:** Spend your "Skill Points". Notice that skills relevant to your Class are cheaper.
3.  **Play:** Use skills during gameplay. You will see XP gains in the result window. Use a skill enough times, and it will Rank Up automatically!

### For Developers
*   **Adding Skills:** Simply add entries to `config/skills.json`.
*   **Tuning XP:** Modify the formula in `StatsManager.perform_skill_check`.
*   **Tuning Costs:** Modify `SkillAllocator.get_skill_cost`.