"""
Dice rolling utilities for the game.
"""

import re
import random
from typing import List, Tuple, Dict, Any

from core.utils.logging_config import get_logger

logger = get_logger(__name__)

# Regular expression for dice notation, e.g., "2d6+3"
DICE_PATTERN = re.compile(r'(\d+)d(\d+)(?:([\+\-])(\d+))?')


def roll_die(sides: int) -> int:
    """
    Roll a single die with the given number of sides.
    
    Args:
        sides: Number of sides on the die.
        
    Returns:
        The result of the roll.
    """
    return random.randint(1, sides)


def roll_dice(num_dice: int, sides: int) -> List[int]:
    """
    Roll multiple dice with the given number of sides.
    
    Args:
        num_dice: Number of dice to roll.
        sides: Number of sides on each die.
        
    Returns:
        List of individual die results.
    """
    return [roll_die(sides) for _ in range(num_dice)]


def roll_dice_sum(num_dice: int, sides: int) -> int:
    """
    Roll multiple dice and return the sum.
    
    Args:
        num_dice: Number of dice to roll.
        sides: Number of sides on each die.
        
    Returns:
        Sum of all dice rolled.
    """
    return sum(roll_dice(num_dice, sides))


def roll_with_advantage(sides: int) -> Tuple[int, int, int]:
    """
    Roll two dice and take the higher result.
    
    Args:
        sides: Number of sides on each die.
        
    Returns:
        Tuple of (result, roll1, roll2) where result is the higher of roll1 and roll2.
    """
    roll1 = roll_die(sides)
    roll2 = roll_die(sides)
    result = max(roll1, roll2)
    return result, roll1, roll2


def roll_with_disadvantage(sides: int) -> Tuple[int, int, int]:
    """
    Roll two dice and take the lower result.
    
    Args:
        sides: Number of sides on each die.
        
    Returns:
        Tuple of (result, roll1, roll2) where result is the lower of roll1 and roll2.
    """
    roll1 = roll_die(sides)
    roll2 = roll_die(sides)
    result = min(roll1, roll2)
    return result, roll1, roll2


def parse_dice_notation(notation: str) -> Dict[str, Any]:
    """
    Parse a dice notation string (e.g., "2d6+3").
    
    Args:
        notation: The dice notation string.
        
    Returns:
        Dictionary with keys 'num_dice', 'sides', 'modifier_type', and 'modifier_value'.
        
    Raises:
        ValueError: If the notation is invalid.
    """
    match = DICE_PATTERN.match(notation)
    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")
    
    num_dice = int(match.group(1))
    sides = int(match.group(2))
    
    result = {
        'num_dice': num_dice,
        'sides': sides,
        'modifier_type': None,
        'modifier_value': 0
    }
    
    # If there's a modifier
    if match.group(3) and match.group(4):
        result['modifier_type'] = match.group(3)
        result['modifier_value'] = int(match.group(4))
    
    return result


def roll_dice_notation(notation: str, crit_roll: bool = False) -> Dict[str, Any]:
    """
    Roll dice based on D&D-style notation (e.g., "2d6+3", "1d20-1").

    Args:
        notation: The dice notation string.
        crit_roll: If true, doubles the number of dice rolled (for critical hits).

    Returns:
        A dictionary with 'total', 'rolls' (list of individual dice results),
        and 'rolls_str' (string representation of rolls).
    """
    if not isinstance(notation, str) or not notation:
        logger.warning(f"Invalid or empty dice notation received: '{notation}'. Defaulting to 0.")
        return {"total": 0, "rolls": [], "rolls_str": "[]", "modifier": 0, "num_dice": 0, "die_size": 0}

    original_notation = notation
    notation = notation.lower().strip()
    
    num_dice = 1
    die_size = 0
    modifier = 0

    # Regex to parse dice notation: (NdM)(+/-X)
    # It captures:
    #   Group 1: (optional) Number of dice (e.g., "2" in "2d6")
    #   Group 2: Die size (e.g., "6" in "2d6")
    #   Group 3: (optional) Sign of the modifier (+ or -)
    #   Group 4: (optional) Value of the modifier
    match = re.match(r"(\d*)d(\d+)(?:([+\-])(\d+))?", notation)

    if not match:
        # Check if it's just a flat number
        if notation.isdigit() or (notation.startswith('-') and notation[1:].isdigit()):
            flat_value = int(notation)
            logger.debug(f"Interpreting notation '{original_notation}' as flat value: {flat_value}")
            return {"total": flat_value, "rolls": [flat_value], "rolls_str": f"[{flat_value}]", "modifier": 0, "num_dice": 0, "die_size": 0}
        else:
            logger.error(f"Invalid dice notation format: '{original_notation}'")
            raise ValueError(f"Invalid dice notation: {original_notation}")

    groups = match.groups()

    if groups[0]:  # Number of dice specified
        num_dice = int(groups[0])
    
    die_size = int(groups[1])

    if groups[2] and groups[3]:  # Modifier specified
        mod_sign = groups[2]
        mod_value = int(groups[3])
        modifier = mod_value if mod_sign == "+" else -mod_value
        
    if crit_roll:
        num_dice *= 2 # Double the dice for a critical hit
        logger.debug(f"Critical roll: Number of dice doubled to {num_dice} for {original_notation}")

    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total_dice_roll = sum(rolls)
    final_total = total_dice_roll + modifier
    
    # --- ECFA Fix: Add 'rolls_str' ---
    rolls_str_representation = str(rolls) # e.g., "[3, 5]"
    # --- End ECFA Fix ---

    logger.debug(f"Rolled {original_notation}{' (crit)' if crit_roll else ''}: Rolls={rolls}, DiceTotal={total_dice_roll}, Mod={modifier}, Final={final_total}")
    
    return {
        "total": final_total, 
        "rolls": rolls,
        "rolls_str": rolls_str_representation, # Added
        "modifier": modifier,
        "num_dice": num_dice,
        "die_size": die_size
    }


def calculate_success_probability(
    target_number: int,
    dice_notation: str,
    advantage: bool = False,
    disadvantage: bool = False
) -> float:
    """
    Calculate the probability of rolling at or above a target number.
    
    Args:
        target_number: The number to meet or exceed.
        dice_notation: The dice notation string.
        advantage: Whether the roll has advantage (roll twice, take higher).
        disadvantage: Whether the roll has disadvantage (roll twice, take lower).
        
    Returns:
        Probability of success as a value between 0 and 1.
        
    Raises:
        ValueError: If the notation is invalid or if both advantage and disadvantage are True.
    """
    if advantage and disadvantage:
        raise ValueError("Cannot have both advantage and disadvantage")
    
    parsed = parse_dice_notation(dice_notation)
    num_dice = parsed['num_dice']
    sides = parsed['sides']
    
    # Apply modifier to target number
    if parsed['modifier_type'] == '+':
        adjusted_target = target_number - parsed['modifier_value']
    elif parsed['modifier_type'] == '-':
        adjusted_target = target_number + parsed['modifier_value']
    else:
        adjusted_target = target_number
    
    # Ensure target is within possible range
    min_roll = num_dice
    max_roll = num_dice * sides
    
    if adjusted_target <= min_roll:
        return 1.0  # Always succeed
    if adjusted_target > max_roll:
        return 0.0  # Always fail
    
    # For single die, calculation is simple
    if num_dice == 1:
        success_range = sides - adjusted_target + 1
        probability = success_range / sides
        
        if advantage:
            # Probability of at least one success in two rolls
            return 1 - (1 - probability) ** 2
        elif disadvantage:
            # Probability of success in both rolls
            return probability ** 2
        else:
            return probability
    
    # For multiple dice, use a simplified estimate for common cases
    # In a proper implementation, we'd use a more sophisticated approach
    # to calculate the exact probability distribution
    
    # Average roll for XdY is X * (Y+1)/2
    average_roll = num_dice * (sides + 1) / 2
    
    # Standard deviation (approximation for sum of dice)
    std_dev = (num_dice * (sides ** 2 - 1) / 12) ** 0.5
    
    # Normalize the target
    z_score = (adjusted_target - average_roll) / std_dev
    
    # Approximate probability using normal distribution
    # This is a rough approximation and works better with more dice
    import math
    probability = 0.5 * (1 - math.erf(z_score / math.sqrt(2)))
    
    if advantage:
        return 1 - (1 - probability) ** 2
    elif disadvantage:
        return probability ** 2
    else:
        return probability


def roll_critical(dice_notation: str, critical_multiplier: int = 2) -> Dict[str, Any]:
    """
    Roll dice with a critical hit (typically doubling the number of dice).
    
    Args:
        dice_notation: The dice notation string.
        critical_multiplier: The multiplier for the number of dice (default: 2).
        
    Returns:
        Dictionary with roll information.
        
    Raises:
        ValueError: If the notation is invalid.
    """
    parsed = parse_dice_notation(dice_notation)
    
    # For a critical hit, we multiply the number of dice
    critical_num_dice = parsed['num_dice'] * critical_multiplier
    
    # Roll the critical dice
    rolls = roll_dice(critical_num_dice, parsed['sides'])
    roll_sum = sum(rolls)
    
    # Apply modifier (usually only once, even on criticals)
    if parsed['modifier_type'] == '+':
        total = roll_sum + parsed['modifier_value']
    elif parsed['modifier_type'] == '-':
        total = roll_sum - parsed['modifier_value']
    else:
        total = roll_sum
    
    result = {
        'rolls': rolls,
        'total': total,
        'original_notation': dice_notation,
        'critical_num_dice': critical_num_dice,
        'sides': parsed['sides'],
        'modifier_type': parsed['modifier_type'],
        'modifier_value': parsed['modifier_value'],
        'critical_multiplier': critical_multiplier
    }
    
    log_str = f"Critical hit! Rolled {critical_num_dice}d{parsed['sides']}: {rolls}"
    if parsed['modifier_type']:
        log_str += f" {parsed['modifier_type']}{parsed['modifier_value']}"
    log_str += f" = {total}"
    logger.debug(log_str)
    
    return result


def check_success(roll: int, dc: int, is_attack: bool = False) -> Tuple[bool, bool, bool]:
    """
    Checks if a roll (d20 portion) is successful against a DC, 
    also determining critical success or fumble if it's an attack.

    Args:
        roll: The raw d20 dice roll result (1-20).
        dc: The difficulty class to beat.
        is_attack: If True, applies critical success (nat 20) and fumble (nat 1) rules.

    Returns:
        A tuple: (success_bool, is_critical_bool, is_fumble_bool).
        'success_bool' here is based on raw roll vs DC, primarily for non-attack skill checks.
        For attacks, the caller typically uses the total modified roll to determine final success,
        but uses is_critical and is_fumble from this function.
    """
    is_critical = False
    is_fumble = False

    if is_attack:
        if roll == 20:
            is_critical = True
          
            return True, is_critical, is_fumble
        if roll == 1:
            is_fumble = True
            return False, is_critical, is_fumble
    
 
    success = (roll >= dc)
    
    return success, is_critical, is_fumble
