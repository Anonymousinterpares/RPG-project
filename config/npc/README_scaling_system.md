# NPC Scaling System Documentation

This document describes the NPC scaling system used in the families-based NPC generation mode.

## Overview

The NPC scaling system applies multiple layers of modifiers to create NPCs appropriate for different difficulty levels, encounter types, and player levels. The system uses a deterministic order of operations to ensure consistent results.

## Scaling Order of Operations

When generating an NPC, scaling modifiers are applied in this specific order:

1. **Base Family Stats**: Start with family `stat_budgets` (hp, damage, defense, initiative)
2. **Boss Overlay Multipliers**: Apply overlay multipliers if an overlay_id is specified
3. **Global Scaling Rules**: Apply difficulty, encounter_size, and level curve modifiers
4. **Variant Modifiers**: Apply variant stat_modifiers (multiply first, then add)

### Why This Order Matters

- **Overlays before Global**: Boss overlays represent fundamental power increases that should be scaled by difficulty
- **Global before Variants**: Variants represent role-specific adjustments that should be applied to already-scaled base stats
- **Multiply before Add**: Within variant modifiers, multiplication happens before addition for predictable results

## Configuration Structure

The scaling system is configured in `config/npc/generation_rules.json`:

```json
{
  "scaling": {
    "difficulty": {
      "story": {"hp": 0.9, "damage": 0.9, "defense": 0.9, "initiative": 1.0},
      "normal": {"hp": 1.0, "damage": 1.0, "defense": 1.0, "initiative": 1.0},
      "hard": {"hp": 1.15, "damage": 1.1, "defense": 1.1, "initiative": 1.0},
      "expert": {"hp": 1.3, "damage": 1.2, "defense": 1.15, "initiative": 1.05}
    },
    "encounter_size": {
      "solo": {"hp": 1.0, "damage": 1.0, "defense": 1.0, "initiative": 1.0},
      "pack": {"hp": 0.9, "damage": 0.95, "defense": 1.0, "initiative": 1.0},
      "mixed": {"hp": 0.95, "damage": 1.0, "defense": 1.0, "initiative": 1.0}
    },
    "player_level_curve": {
      "hp": {"start_level": 1, "end_level": 20, "curve": "linear", "multiplier": 1.0},
      "damage": {"start_level": 1, "end_level": 20, "curve": "linear", "multiplier": 1.0},
      "defense": {"start_level": 1, "end_level": 20, "curve": "linear", "multiplier": 1.0},
      "initiative": {"start_level": 1, "end_level": 20, "curve": "linear", "multiplier": 1.0}
    }
  }
}
```

## Difficulty Scaling

Difficulty multipliers affect the overall power level of NPCs:

- **story**: Reduced difficulty (0.9x hp/damage/defense)
- **normal**: Baseline (1.0x - no change)  
- **hard**: Increased difficulty (1.15x hp, 1.1x damage/defense)
- **expert**: High difficulty (1.3x hp, 1.2x damage, 1.15x defense, 1.05x initiative)

## Encounter Size Scaling

Encounter size modifiers balance individual NPC power based on expected group composition:

- **solo**: Single powerful enemy (1.0x - no reduction)
- **pack**: Multiple weaker enemies (0.9x hp, 0.95x damage)
- **mixed**: Mixed encounter types (0.95x hp)

## Level Curve System

Level curves provide progressive scaling as player level increases. Each stat can have its own curve configuration.

### Curve Parameters

- **start_level**: Level where scaling begins (default: 1)
- **end_level**: Level where scaling reaches full effect (default: 20)
- **curve**: Interpolation method (see below)
- **multiplier**: Target multiplier at end_level

### Supported Curve Types

#### Linear (`"linear"`)
Straight-line interpolation from start_level to end_level.
- **Use case**: Steady, predictable progression
- **Formula**: `progress = (level - start_level) / (end_level - start_level)`

#### Logarithmic (`"log"`)
Faster scaling at lower levels, slower at higher levels.
- **Use case**: Diminishing returns, early game emphasis
- **Formula**: `progress = log₁₀(1 + 9t) where t is linear progress`

#### Exponential (`"exp"`)
Slower scaling at lower levels, faster at higher levels.
- **Use case**: Accelerating difficulty, late game emphasis
- **Formula**: `progress = (10^t - 1) / 9 where t is linear progress`

#### Ease In (`"ease_in"`)
Cubic curve starting slowly, accelerating toward the end.
- **Use case**: Gradual introduction of scaling effects
- **Formula**: `progress = t³ where t is linear progress`

#### Ease Out (`"ease_out"`)
Cubic curve starting quickly, decelerating toward the end.
- **Use case**: Front-loaded scaling that levels off
- **Formula**: `progress = 1 - (1-t)³ where t is linear progress`

### Multiplier Interpretation

- **multiplier >= 1.0**: Scaling increases stat (e.g., 1.5 = 50% increase at end_level)
- **multiplier < 1.0**: Scaling decreases stat (e.g., 0.8 = 20% decrease at end_level)
- **multiplier = 1.0**: No scaling applied regardless of level

### Level Clamping

- Levels below start_level use the base multiplier (1.0)
- Levels above end_level use the full configured multiplier
- Levels between start_level and end_level use interpolated values

## Family Integration

### Base Family Stats

Families define `stat_budgets` with min/max ranges:

```json
{
  "stat_budgets": {
    "hp": {"min": 8, "max": 12},
    "damage": {"min": 2, "max": 4},
    "defense": {"min": 10, "max": 14},
    "initiative": {"min": 0, "max": 2}
  }
}
```

A random value is picked from each range, then scaling is applied.

### Boss Overlays

Overlays provide multiplicative bonuses before global scaling:

```json
{
  "overlays": {
    "default_boss": {
      "multipliers": {
        "hp": 2.0,
        "damage": 1.5,
        "defense": 1.2,
        "initiative": 1.1
      }
    }
  }
}
```

### Variants

Variants apply role-specific adjustments after global scaling:

```json
{
  "variants": {
    "concordant_guard": {
      "stat_modifiers": {
        "hp": {"mul": 1.1, "add": 5},
        "defense": {"mul": 1.2}
      }
    }
  }
}
```

Order within variant modifiers: multiply first, then add.

## Example Scaling Calculation

For a level 10 NPC with hard difficulty, solo encounter, using a boss overlay:

1. **Family Base**: hp budget picks 10
2. **Boss Overlay**: 10 × 2.0 = 20
3. **Difficulty**: 20 × 1.15 = 23
4. **Encounter Size**: 23 × 1.0 = 23 (solo = no change)
5. **Level Curve**: 23 × level_multiplier (depends on curve config)
6. **Variant** (if applicable): Apply mul then add modifiers

## Configuration Guidelines

### Difficulty Balance

- **story**: Should feel easier than normal without being trivial
- **normal**: Baseline for your intended game experience
- **hard**: Challenging but fair increase
- **expert**: Significant challenge for experienced players

### Encounter Size Balance

- **pack**: Reduce individual power since there will be more enemies
- **mixed**: Moderate reduction for varied encounter composition
- **solo**: Full power for single-enemy encounters

### Level Curve Design

- Use **linear** for steady progression
- Use **logarithmic** to front-load difficulty increases
- Use **exponential** for late-game challenge spikes
- Use **ease_in/ease_out** for smooth difficulty transitions

## Testing and Validation

Use `test_difficulty_encounter_scaling.py` to verify scaling behavior:

```bash
python test_difficulty_encounter_scaling.py
```

The test suite validates:
- Difficulty multipliers affect stats as expected
- Encounter size modifiers work correctly
- Level curves interpolate properly
- Parameter propagation through NPCCreator works
- Variants respect the scaling order

## Integration Points

The scaling system integrates with:

- **NPCCreator**: Reads difficulty/encounter_size from game config
- **NPCFamilyGenerator**: Applies scaling in generate_npc_from_family/variant
- **Combat System**: Uses scaled NPC stats for encounters
- **World Configurator**: Can preview scaled results (future enhancement)

## Troubleshooting

### Scaling Not Applied
- Verify `system.npc_generation_mode = "families"` in config
- Check that generation_rules.json is properly loaded
- Ensure difficulty/encounter_size values match config keys

### Unexpected Results
- Verify scaling order matches documentation
- Check for stat clamping in StatsManager (e.g., MAX_HEALTH limits)
- Use test suite to isolate scaling layer issues

### Configuration Errors
- Validate JSON syntax in generation_rules.json
- Ensure curve parameters have valid start_level < end_level
- Check that multiplier values are reasonable (0.1 to 10.0 range typically)
