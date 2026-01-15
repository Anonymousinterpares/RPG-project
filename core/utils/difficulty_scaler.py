# core/utils/difficulty_scaler.py

def calculate_dc(tier: str, player_level: int = 1) -> int:
    """
    Calculates a numeric Difficulty Class (DC) based on a descriptive tier.
    
    Args:
        tier: The difficulty tier (trivial, easy, normal, hard, very_hard, impossible).
        player_level: The player's current level (used for scaling if desired).
        
    Returns:
        The integer DC.
    """
    # Base DCs (Standard D&D 5e style bounded accuracy)
    tier_map = {
        "trivial": 5,
        "easy": 10,
        "normal": 15,
        "hard": 20,
        "very_hard": 25,
        "impossible": 30
    }
    
    base_dc = tier_map.get(tier.lower(), 15) # Default to normal
    
    # Optional: Apply Level Scaling?
    # If we want the world to level with the player (e.g. a 'hard' lock at level 1 is DC 20,
    # but a 'hard' lock at level 10 is DC 25), we uncomment this:
    # scaling = (player_level - 1) * 0.5 
    # return int(base_dc + scaling)
    
    # For now, let's stick to static DCs for consistency
    return base_dc