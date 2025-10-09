# NPC Variants Editor AI Assistant Improvements

## Overview

The NPC Variants Editor now features enhanced AI assistant integration with improved UI synchronization. These changes address the culture bias issue where AI-created variants didn't align with the quick creation UI defaults.

## Key Improvements

### 1. Enhanced AI Context Awareness

The `get_assistant_context()` method now includes current UI state:
- Current culture and role filter selections
- Quick creation UI culture/role settings
- UI context information to guide AI suggestions

This helps the AI make more contextually appropriate suggestions that align with what the user is currently viewing or working with.

### 2. Automatic UI Synchronization

After the AI creates a new variant, the `_sync_ui_to_variant()` method:
- Automatically detects the culture and role from the newly created variant
- Updates the quick creation UI controls to match the variant's attributes
- Ensures consistency between AI suggestions and UI state

### 3. Improved AI Guidance

The `get_reference_catalogs()` method now provides:
- Current UI context for better AI understanding
- Social role patterns and typical attributes
- Culture to family ID mapping
- Contextual guidance based on current filter selections

## How It Works

### Culture Detection
The system detects culture from multiple sources:
1. `family_id` field (e.g., "tempest_swashbuckler" → "tempest")
2. Variant name (e.g., "Tempest Navigator" → "tempest")  
3. Variant ID (e.g., "tempest_guard" → "tempest")

### Role Detection
The system detects social roles from:
1. `roles_add` array (direct role matches)
2. Variant name patterns (e.g., "Guard" → "guard")
3. Variant ID patterns (e.g., "concordant_official" → "official")

### UI Synchronization Flow
1. User requests AI to create a new variant in analyze mode
2. AI creates variant with appropriate culture/role based on context
3. Variant is added to the manager and UI is refreshed
4. `_sync_ui_to_variant()` analyzes the new variant's attributes
5. Quick creation UI controls are updated to match the variant
6. User sees consistent UI state aligned with AI suggestions

## Example Usage

### Before Improvements
- User requests "Create a Tempest Navigator variant" via AI
- AI creates variant with tempest culture correctly
- Quick creation UI still shows "concordant" culture (default)
- User confusion about culture mismatch

### After Improvements  
- User requests "Create a Tempest Navigator variant" via AI
- AI receives context about current UI state and user preferences
- AI creates variant with tempest culture and appropriate attributes
- Quick creation UI automatically switches to "tempest" culture
- UI remains consistent with AI-created content

## Benefits

1. **Reduced Confusion**: UI controls reflect the actual variants being worked with
2. **Better Context**: AI makes suggestions aligned with current user focus  
3. **Improved Workflow**: Seamless transition between AI creation and manual editing
4. **Consistent UX**: Quick creation defaults match recent AI activity

## Technical Details

### New Methods
- `_sync_ui_to_variant(variant_data: dict)`: Synchronizes UI controls to match variant attributes
- Enhanced `get_assistant_context()`: Includes UI state in AI context
- Enhanced `get_reference_catalogs()`: Provides contextual guidance to AI

### Culture Detection Patterns
- concordant → concordant_citizen family
- verdant → verdant_wanderer family  
- crystalline → crystalline_adept family
- ashen → ashen_nomad family
- tempest → tempest_swashbuckler family

### Social Role Patterns
- guard: tank/controller roles, shield abilities, watch duties
- official: support/controller roles, rally abilities, official role tags
- scholar: controller/support roles, knowledge abilities, scholar role tags

## Explanation of Variant System

### How Roles, Abilities, and Tags Work in Game

**Roles** define behavioral archetypes:
- `striker`: High damage, single-target focus
- `tank`: High HP/defense, damage absorption  
- `controller`: Area control, crowd management
- `support`: Healing, buffs, utility
- `skirmisher`: Mobile, hit-and-run tactics
- `scout`: Reconnaissance, mobility, stealth

**Abilities** are special NPC capabilities:
- Combat abilities (e.g., "lightning_strike", "resonant_shield")
- Utility abilities (e.g., "nature_stride", "camouflage")
- Social abilities (e.g., "rally_shout", "chorus_of_clarity")

**Tags** provide flexible categorization:
- Role tags: "role:guard", "role:scholar", "role:pathfinder"
- Duty tags: "duty:watch", "duty:patrol" 
- Specialization tags: "specialization:predictive_geometry"
- Style tags: "style:duelist"
- Rank tags: "rank:alpha"

### Gameplay Impact
When the game engine spawns NPCs:
1. **Roles** influence AI behavior patterns and combat tactics
2. **Abilities** determine available actions and special moves
3. **Tags** trigger conditional behaviors, dialogue options, and event interactions
4. **Stat modifiers** adjust base family stats for variant-specific strengths/weaknesses

### Variant Creation Guidelines
- **Family ID**: Links to base NPC family (concordant_citizen, tempest_swashbuckler, etc.)
- **Roles Add**: Augment base roles with variant-specific behavioral patterns
- **Abilities Add**: Grant additional capabilities beyond base family abilities  
- **Tags Add**: Add metadata for special interactions and triggers
- **Stat Modifiers**: Fine-tune stats with additive and multiplicative adjustments

This system allows for rich NPC diversity where a single base family can have multiple specialized variants, each with unique behaviors, capabilities, and gameplay interactions.
