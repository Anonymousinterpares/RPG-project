This is a solid plan. Merging **Point Buy** (for initial customization) with **Usage-Based Growth** (for long-term progression) creates a very organic RPG feel: "I started as a soldier (Point Buy), but I became a diplomat because I kept talking my way out of trouble (Usage)."

Here is the structured brainstorm for implementing this system, covering the UI, the Data/Lore, and the Mechanics.

---

### 1. GUI & UX Redesign: "Stats & Skills" (Tab 2)

Since `CharacterCreationDialog` currently has Tab 1 (Basic Info/Origin) and Tab 3 (Stats), we will consolidate.

**The New Layout (Tab 2: "Attributes & Skills"):**
Instead of just a list of stats, we split the screen into two interactive columns.

*   **Left Column: Attributes (Stats)**
    *   Current `StatAllocationWidget` logic (STR, DEX, INT...).
    *   Header: "Attribute Points: X".
*   **Right Column: Skills (New)**
    *   Header: "Skill Points: Y" (Calculated: `Class Base + INT Mod`).
    *   A Scrollable List (`QScrollArea`) of Skill Rows.
*   **Visual Logic:**
    *   **Class Skills:** Highlighted in **Green**. Cost: 1 Point.
    *   **Cross-Class Skills:** Standard Color. Cost: 2 Points.
    *   **Origin Skills:** Highlighted in **Gold**. These come pre-filled with Rank 1 (or 2) and cannot be lowered below that free rank.

**User Experience (UX):**
*   **The "Glance" View:** Each row looks like:
    `[?] Acrobatics | Rank: 0 | [ - ] [ + ]`
*   **The "Detail" View:** Hovering over the `[?]` or the Name shows a Tooltip:
    > **Acrobatics (DEX)**
    > *Class Skill (Cost: 1)*
    > Ability to keep balance and tumble.
*   **Right-Click:** Opens a `StatInfoDialog` (reusing your existing class) with detailed Lore and mechanics.

---

### 2. Skill Definitions & Lore Expansion

We need to update `skills.json`. Your current list is good generic fantasy, but *Aetheris* needs specific flavor.

**Proposed New/Refined Skills (15 examples):**

| Skill Name | Attribute | Class/Origin Affinity | Lore / Mechanical Reasoning |
| :--- | :--- | :--- | :--- |
| **Resonance Sensing** | INS | Mage, Maelstri | **Lore:** Sensing upcoming Resonance Events or weak planar boundaries. <br>**Mech:** Prevents surprise attacks from planar rifts; helps finding hidden paths in bleed zones. |
| **Ash Walking** | DEX | Rogue, Cinderspawn | **Lore:** Moving silently specifically over brittle/noisy terrain (ash, glass). <br>**Mech:** Stealth bonus in Ashen/Crystalline biomes where normal Stealth fails. |
| **Facet Logic** | INT | Mage, Prismal | **Lore:** The mathematical magic of the Consortium. <br>**Mech:** Deciphering geometric puzzles; required for advanced Facet Magic spells. |
| **Green Speech** | CHA | Druid, Verdant | **Lore:** Non-verbal communication with flora. <br>**Mech:** Gathering info from plants; calming aggressive plant-beasts. |
| **Echo Navigation** | WIS | Ranger, Wanderer | **Lore:** Navigating the shifting, non-Euclidean layouts of the Ghost Markets. <br>**Mech:** Reduces travel time; prevents getting lost in unstable zones. |
| **Scavenging** | WIS | Wanderer, Ashen | **Lore:** Finding use in the decay of the Shattering. <br>**Mech:** Higher loot drop rates; finding food in wastelands. |
| **Planar Anchoring** | WIL | Cleric, Concordant | **Lore:** Resisting the mental drift caused by plane-shifting. <br>**Mech:** Saving throw vs. planar displacement or madness. |
| **Attunement** | CON | Warrior, Concordant | **Lore:** Physically adapting body rhythm to the current plane. <br>**Mech:** Reduces stamina drain in hostile planar environments. |
| **Storm Riding** | DEX | Rogue, Tempest | **Lore:** Moving with the chaotic flow of probability. <br>**Mech:** Initiative bonus; traverse hazardous weather effects safely. |
| **Oral History** | CHA | Bard, Ashen | **Lore:** Remembering knowledge that cannot be written down (Ashen tradition). <br>**Mech:** Unlock lore hints without books; improves reputation with nomadic tribes. |
| **Barter** | CHA | Merchant, Rogue | **Lore:** The universal language of the Nexus. <br>**Mech:** Better prices; unlocking "special stock" in shops. |
| **Intimidation** | STR | Warrior, Orc | **Lore:** Physical coercion. <br>**Mech:** Force enemies to flee combat; bypass social checks via fear. |
| **Tinkering** | INT | Dwarf, Gnome | **Lore:** Maintaining gear in a world where physics glitch. <br>**Mech:** Repair equipment; craft improvised traps. |
| **First Aid** | WIS | Cleric, Medic | **Lore:** Non-magical healing. <br>**Mech:** Stop bleeding; stabilize dying allies without mana. |
| **Focus** | WIL | Mage, Monk | **Lore:** Maintaining spell concentration amidst chaos. <br>**Mech:** Interrupt resistance; mental defense. |

**Locked Skills:**
*   *Facet Logic* and *Green Speech* should be locked (Rank 0 and un-allocatable) unless you have the specific Race (Prismal/Mycora) OR the specific Class (Mage/Druid) OR an Origin that justifies it. This makes choices feel impactful.

---

### 3. The Experience (EXP) System Architecture

We need a two-tier EXP system to support "Leveling Up" (HP/Stats) and "Skill Usage" (Proficiency).

**A. Global Experience (Character Level)**
*   **Source:** Quest completion, Discovery (new locations), Defeating Bosses/Elites.
*   **Effect:** When threshold reached -> Level Up.
    *   +HP/Mana/Stamina (Fixed by Class).
    *   +1 Attribute Point (Rare, maybe every 4 levels).
    *   +X Skill Points (To distribute manually, representing "training").

**B. Skill Experience (Usage Mastery)**
*   **Source:** Performing actions (Skill Checks).
*   **Storage:** In `StatsManager`, every skill entry in the dictionary needs a structure like:
    ```json
    "stealth": {
        "value": 5,          // Current Rank
        "exp": 120,          // Current XP
        "next_level": 500    // XP needed for Rank 6
    }
    ```
*   **Scaling:** Use a non-linear curve. Rank 1->2 is easy. Rank 19->20 is a masterwork.

---

### 4. Usage Mechanics (Brainstorming Implementation)

How do we handle "Usage" in a turn-based/text game without it becoming a grind-fest?

**The "Meaningful Check" Rule:**
We only award EXP if the check had a *Failure Consequence* or a *Resource Cost*.
*   *Example:* Casting a spell costs Mana. Grants Magic XP.
*   *Example:* Picking a lock carries risk of breaking the pick or alerting guards. Grants Thievery XP.
*   *Counter-Example:* Shooting an arrow at a wall in an empty room. No cost/risk? No XP.

**XP Calculation Formula:**
When `perform_skill_check(skill, difficulty)` is called:

1.  **Base XP:** Fixed amount based on Difficulty (DC).
    *   `Base = DC * 2`
2.  **Outcome Multiplier:**
    *   **Success:** `1.0x`
    *   **Failure:** `1.5x` (You learn more from mistakes! This is a popular modern RPG mechanic).
    *   **Critical Success/Fail:** `2.0x`.
3.  **Diminishing Returns (Optional but Recommended):**
    *   If `Skill Rank` >> `Difficulty` (e.g., Rank 10 vs DC 5), XP = 0. You don't learn from trivial tasks.

**Integration with LLM/Narrative:**
Since entities are created just-in-time, the `NPCManager` needs to feedback into the Skill System.
*   **Scenario:** Player tries to persuade a guard.
*   **Code:**
    ```python
    # Narrative Engine decides this is a "Persuasion" check vs Guard's Resolve
    difficulty = guard.get_stat("RESOLVE") + 10 # Base DC 10
    result = player.perform_skill_check("Persuasion", difficulty)
    
    if result.success:
        # LLM generates success narrative
        player.award_skill_exp("Persuasion", difficulty * 1.0)
    else:
        # LLM generates failure narrative
        player.award_skill_exp("Persuasion", difficulty * 1.5)
    ```

---

### 5. Implementation Plan (Next Steps)

1.  **Update `classes.json`**: Add `class_skills` (list) and `skill_points_base` (int) to every class.
2.  **Update `skills.json`**: Populate with the new Lore skills and add `attribute` mapping.
3.  **Backend (`StatsManager.py`)**:
    *   Add `skill_exp` dictionary.
    *   Add `award_skill_exp(skill_name, amount)` method.
    *   Update `perform_skill_check` to call `award_skill_exp` automatically (or return data for the engine to do it).
4.  **GUI (`CharacterCreationDialog.py` & `StatAllocationWidget.py`)**:
    *   Modify `StatAllocationWidget` to accept a mode (Attribute vs Skill) or create a parallel `SkillAllocationWidget`.
    *   Implement the "Points Remaining" logic (Class Skill = 1, Cross = 2).

**Which part would you like to tackle first?** I recommend starting with **Step 1 & 2 (Data Configuration)** so we have the concrete data structures ready for the GUI work.


# Comprehensive Redesign Report: Hybrid Skill System

## 1. Executive Summary
We are implementing a **Hybrid Skill System** that combines **Point Buy** (for character creation/customization) with **Usage-Based Growth** (organic progression during gameplay).

*   **Creation Phase:** Players spend a pool of "Skill Points" to buy ranks. Costs are determined by Class (Class Skills = Cheap, Cross-Class = Expensive). Origins provide free starting ranks.
*   **Gameplay Phase:** Successful or failed skill checks generate "Skill XP". Accumulating XP increases the Skill Rank automatically.
*   **Level-Up Phase:** Global Character Leveling grants attribute boosts and potentially a small injection of "Training Points" (Skill Points) to represent downtime study.

This report analyzes the existing codebase (`core/stats/*`, `gui/components/*`) and outlines the specific architectural changes required.

---

## 2. Data Architecture (JSON Configuration)

We need to expand the static definitions to support the logic of "Class Skills" vs "Cross-Class Skills" and free Origin ranks.

### A. `config/skills.json` (Update)
We need to define the master list of skills, including the new Lore-specific ones.
*   **Action:** Add new entries. Ensure every skill has a `primary_stat`.
*   **New Fields:** None strictly required, but `can_be_default` (bool) could help filter list size.
*   **Lore Additions:** *Ash Walking, Resonance Sensing, Facet Logic, Green Speech, Barter, Scavenging.*

### B. `config/classes.json` (Update)
Classes currently define Attribute modifiers. They must now define Skill affinities.
*   **New Field:** `class_skills` (List[str]). A list of IDs (e.g., `["melee_attack", "athletics", "intimidation"]`).
*   **New Field:** `skill_points_per_level` (int). Base points granted (e.g., 4). The formula will be `Base + INT_MOD`.

### C. `config/origins.json` (Existing)
*   **Current State:** Already has `skill_proficiencies` (List[str]).
*   **Logic Update:** These skills will be granted at **Rank 1 (Free)**. If the player wants to raise them higher, they pay normal costs.

---

## 3. Backend Architecture (`core/stats/`)

The Python backend needs to store Skill XP and handle the math of two different allocation systems (Attributes vs. Skills).

### A. `stats_base.py`
The `Stat` dataclass is the atomic unit of storage. We need to enable it to store progression data without breaking existing Attribute logic.

*   **Modification:** Update `Stat` dataclass.
    ```python
    @dataclass
    class Stat:
        # ... existing fields ...
        exp: float = 0.0          # Current XP (for Skills)
        exp_to_next: float = 100.0 # XP needed for next rank (scaling)
    ```

### B. `stats_manager.py`
This is the engine room. It currently holds `self.skills`.

*   **New Method:** `award_skill_exp(self, skill_name: str, amount: float)`
    *   Logic: `stat.exp += amount`. If `stat.exp >= stat.exp_to_next`, increment `stat.base_value`, reset `exp`, and increase `exp_to_next` (curved scaling).
    *   Emit: `stats_changed` signal.
*   **Update Method:** `perform_skill_check`
    *   Current: Calculates roll.
    *   New: After calculating `SkillCheckResult`, call `self._process_skill_usage(skill_name, difficulty, result)`.
    *   **Logic:** If `result.skill_exists` is True, calculate XP yield (Failure gives XP too!) and call `award_skill_exp`.

### C. `stat_allocation.py`
Currently, `StatPointAllocator` handles the D&D-style "Cost increases as Stat increases" logic (8->9 costs 1, 14->15 costs 2). Skills need a different logic.

*   **Refactor:** Rename current class to `AttributeAllocator`.
*   **New Class:** `SkillAllocator`
    *   **Input:** `StatsManager`, `class_skills` (list), `origin_skills` (list), `available_points`.
    *   **Cost Logic:**
        *   If skill in `class_skills`: Cost = 1.
        *   If skill NOT in `class_skills`: Cost = 2 (or 1.5 rounded up).
        *   If skill in `origin_skills`: Minimum Rank is 1 (cannot decrease below 1).
    *   **Cap Logic:** Max Rank at creation = Level + 3 (or a fixed cap like 5).

### D. `stat_modifier_info.py`
This file loads race/class config.
*   **Update:** Add methods to load and return `class_skills` lists so the UI can highlight them.

---

## 4. GUI Implementation (`gui/`)

The goal is to consolidate everything into a comprehensive **"Attributes & Skills"** tab.

### A. `gui/components/stat_allocation_widget.py`
This widget currently handles the Attribute grid. We need to make it modular or create a sibling.

*   **Plan:** Keep `StatAllocationWidget` for the Left Column (Attributes).
*   **New Widget:** `SkillAllocationWidget` (Right Column).
    *   **Visuals:** A `QScrollArea` containing a `QGridLayout`.
    *   **Rows:** `[Icon] [Name] [Rank] [-] [+] [Cost]`.
    *   **Color Coding:**
        *   Class Skill: Green text.
        *   Origin Skill: Gold border/text (Tooltip: "Granted by Origin").
    *   **Header:** "Skill Points: X".
    *   **Interaction:** Clicking `+` calls `SkillAllocator.increase_skill()`.

### B. `gui/dialogs/character_creation_dialog.py`
*   **Tab Logic:**
    *   Tab 1: Basic Info (Name, Race, Class, Origin).
    *   **Tab 2 (New):** "Attributes & Skills".
        *   Layout: `QHBoxLayout`.
        *   Left: `StatAllocationWidget` (Existing).
        *   Right: `SkillAllocationWidget` (New).
    *   Tab 3: (Removed/Merged).
*   **Integration:** When Race/Class changes on Tab 1:
    *   Update Attribute Modifiers (existing functionality).
    *   **New:** Update `SkillAllocationWidget` with the new list of `class_skills` and reset points pool based on new Intelligence score.

---

## 5. The Gameplay Loop (XP & Usage)

This logic ensures the "Idea 3" (Usage-Based Growth) works within the `core/stats` system.

### A. The XP Formula
In `stats_manager.py`, define the formula.
*   **Check Difficulty (DC):** The baseline for XP.
*   **Formula:** `XP = (DC * Multiplier) / (Current_Rank + 1)`
    *   *Diminishing Returns:* Hard tasks give less XP if you are already a master.
    *   *Failure:* `Multiplier = 1.5` (You learn from mistakes).
    *   *Success:* `Multiplier = 1.0`.
*   **Threshold:** `Next_Level_XP = Previous_Level_XP * 1.5`.

### B. LLM Integration
Since enemies/situations are LLM-generated, the game engine needs to parse the *attempt*.

1.  **Player Input:** "I try to decipher the runes."
2.  **Game Engine:** Resolves this to `INT` check or `Facet Logic` skill check. DC 15.
3.  **StatsManager:** Rolls. Result: 12 (Fail).
4.  **Auto-Trigger:** `StatsManager` calculates XP for `Facet Logic`. Adds e.g., 20 XP.
5.  **Notification:** If Rank Up occurs, return a flag so the UI can show a "Skill Up!" toast notification.

---

## 6. Detailed Implementation Roadmap

### Phase 1: Data & Backend (The Foundation)
1.  **Modify `stats_base.py`**: Add `exp` fields to `Stat`.
2.  **Modify `config/classes.json`**: Add `class_skills` and `skill_points` entries.
3.  **Modify `config/skills.json`**: Add the new Lore skills (Ash Walking, etc.).
4.  **Update `StatsManager`**: Implement `award_skill_exp` and update `perform_skill_check`.
5.  **Create `core/stats/skill_allocation.py`**: Implement the logic for point buying skills (costs and caps).

### Phase 2: GUI Components (The Widget)
1.  **Create `gui/components/skill_allocation_widget.py`**:
    *   Copy the structure of `stat_allocation_widget.py`.
    *   Adapt it to use `SkillAllocator`.
    *   Implement the visual highlighting (Green/Gold) for Class/Origin skills.
    *   Add tooltips explaining *why* a skill is highlighted.

### Phase 3: Integration (The Dialog)
1.  **Update `CharacterCreationDialog`**:
    *   Combine the layouts.
    *   Ensure `INT` stat changes on the left immediately update "Skill Points" available on the right.
    *   Ensure selecting an "Origin" on Tab 1 pre-populates the specific skills on Tab 2 to Rank 1.

### Phase 4: Gameplay Hook (The Loop)
1.  **Update `SkillCheckDisplay`**: Add a small progress bar or "+XP" floating text when a check completes to visualize the growth.

This plan leverages 90% of your existing code structure, adding the "Skill" layer as a parallel system to "Attributes" without breaking the existing `Stat` logic.