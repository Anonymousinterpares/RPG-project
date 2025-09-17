# Dice System

This utility module provides dice rolling functionality for the RPG game, including support for dice notation, advantage/disadvantage mechanics, and probability calculations.

## Overview

The dice system implements flexible dice rolling mechanics that support:

- Standard XdY dice notation (e.g., "2d6+3")
- Advantage/disadvantage rolls (roll twice, take higher/lower)
- Critical hit and fumble detection
- Probability calculations
- Complex dice patterns

## Functions

### Basic Dice Rolling

- `roll_die(sides)` - Roll a single die with the given number of sides
- `roll_dice(num_dice, sides)` - Roll multiple dice and return individual results
- `roll_dice_sum(num_dice, sides)` - Roll multiple dice and return the sum

### Advantage/Disadvantage

- `roll_with_advantage(sides)` - Roll a die twice and take the higher result
- `roll_with_disadvantage(sides)` - Roll a die twice and take the lower result

### Dice Notation

- `parse_dice_notation(notation)` - Parse a dice notation string (e.g., "2d6+3")
- `roll_dice_notation(notation)` - Roll dice based on a notation string

### Critical Hits

- `roll_critical(dice_notation, critical_multiplier)` - Roll dice for a critical hit
- `check_success(roll, target, critical_threshold, fumble_threshold)` - Check if a roll succeeds

### Probability

- `calculate_success_probability(target_number, dice_notation, advantage, disadvantage)` - Calculate the probability of a successful roll

## Usage Examples

### 1. Basic Dice Rolling

```python
from core.utils.dice import roll_die, roll_dice, roll_dice_sum

# Roll a d20
result = roll_die(20)  # Returns a number between 1 and 20

# Roll 3d6
dice_results = roll_dice(3, 6)  # Returns a list like [3, 5, 1]

# Roll 3d6 and get the sum
total = roll_dice_sum(3, 6)  # Returns the sum, e.g., 9
```

### 2. Using Dice Notation

```python
from core.utils.dice import roll_dice_notation, parse_dice_notation

# Roll dice using notation
result = roll_dice_notation("2d6+3")
# Returns: {
#   'rolls': [4, 6],  # Individual die results
#   'total': 13,      # Final result with modifier
#   'num_dice': 2,    # Number of dice
#   'sides': 6,       # Die size
#   'modifier_type': '+',  # Modifier type
#   'modifier_value': 3    # Modifier value
# }

# Parse notation without rolling
parsed = parse_dice_notation("3d8-2")
# Returns: {
#   'num_dice': 3,
#   'sides': 8,
#   'modifier_type': '-',
#   'modifier_value': 2
# }
```

### 3. Advantage and Disadvantage

```python
from core.utils.dice import roll_with_advantage, roll_with_disadvantage

# Roll with advantage (roll twice, take higher)
result, roll1, roll2 = roll_with_advantage(20)
# Example: result=18, roll1=18, roll2=7

# Roll with disadvantage (roll twice, take lower)
result, roll1, roll2 = roll_with_disadvantage(20)
# Example: result=3, roll1=3, roll2=15
```

### 4. Critical Hits and Success Checks

```python
from core.utils.dice import roll_critical, check_success

# Roll critical hit (typically doubles the dice)
result = roll_critical("2d8+5")
# Returns dice result with 4d8+5 instead of 2d8+5

# Check if a roll succeeds
roll = 18
target = 15
success, critical_success, critical_failure = check_success(roll, target)
# Returns: (True, False, False) - Success, but not critical
```

### 5. Probability Calculations

```python
from core.utils.dice import calculate_success_probability

# Calculate probability of rolling 15+ on 1d20+5
probability = calculate_success_probability(15, "1d20+5")
# Returns: 0.55 (55% chance)

# With advantage
probability = calculate_success_probability(15, "1d20+5", advantage=True)
# Returns higher probability

# With disadvantage
probability = calculate_success_probability(15, "1d20+5", disadvantage=True)
# Returns lower probability
```

## Integration with Combat System

The dice system integrates with the combat system for:

- Attack rolls (to determine hits)
- Damage calculation
- Critical hit detection
- Saving throws against effects
- Skill checks

## Configuration

Dice-related constants and default values are configured in:

- `config/combat/combat_config.json` - Critical thresholds, fumble thresholds, etc.

## Logging

The dice system includes logging to track important rolls:

- All dice rolls are logged at debug level
- Critical success and failures are logged at info level
- Complex roll results (with modifiers) are formatted for easy reading

## Future Enhancements

- Support for exploding dice (re-roll on maximum value)
- Success counting (e.g., World of Darkness style)
- Dice pools with target numbers
- Visual dice representation for GUI

## Testing

The dice system includes test cases to verify correct operation:
- Distribution tests to ensure randomness
- Probability calculation validation
- Edge case handling (very large dice pools, extreme modifiers)
- Parsing validation for dice notation

Note: The system is currently implemented but needs comprehensive testing.
