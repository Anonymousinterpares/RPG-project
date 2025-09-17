#!/usr/bin/env python3
"""
Enhanced time management system for the RPG game.

This module provides rich, narrative time descriptions while keeping 
actual game time tracking in the background. It replaces clock-based
time references with immersive descriptive periods.
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.utils.logging_config import get_logger
from core.utils.time_utils import game_time_to_datetime, GAME_EPOCH

logger = get_logger("TIME_MANAGER")


class TimePeriod(Enum):
    """Time periods for narrative descriptions."""
    DEEP_NIGHT = "deep_night"        # 0:00-4:00
    PRE_DAWN = "pre_dawn"            # 4:00-5:00  
    DAWN = "dawn"                    # 5:00-7:00
    MORNING = "morning"              # 7:00-11:00
    NOON = "noon"                    # 11:00-13:00
    AFTERNOON = "afternoon"          # 13:00-17:00
    EVENING = "evening"              # 17:00-20:00
    SUNSET = "sunset"                # 20:00-21:00
    NIGHT = "night"                  # 21:00-24:00


@dataclass
class TimeDescription:
    """A rich time description with multiple variants."""
    primary: str                     # Main description
    variants: List[str]             # Alternative descriptions
    atmospheric: List[str]          # Atmospheric descriptions
    seasonal_modifiers: Dict[str, List[str]]  # Season-specific variants


class EnhancedTimeManager:
    """
    Manages rich, narrative time descriptions for the RPG game.
    
    This class converts game time into immersive narrative descriptions,
    avoiding clock-based references that break immersion.
    """
    
    def __init__(self):
        """Initialize the enhanced time manager."""
        self._time_descriptions = self._initialize_time_descriptions()
        self._last_description_cache = {}  # Cache to avoid repetition
        
    def _initialize_time_descriptions(self) -> Dict[TimePeriod, TimeDescription]:
        """Initialize the comprehensive time description database."""
        return {
            TimePeriod.DEEP_NIGHT: TimeDescription(
                primary="deep night",
                variants=[
                    "the depths of night",
                    "the small hours", 
                    "the darkest hours",
                    "the dead of night",
                    "the quiet hours"
                ],
                atmospheric=[
                    "when shadows reign supreme",
                    "while the world sleeps",
                    "in the hushed darkness",
                    "beneath the star-filled sky",
                    "when only creatures of the night stir"
                ],
                seasonal_modifiers={
                    "Winter": ["the bitter night", "the frost-touched darkness"],
                    "Summer": ["the warm night air", "the gentle darkness"],
                    "Spring": ["the crisp night", "the awakening darkness"], 
                    "Fall": ["the cool night", "the harvest-time darkness"]
                }
            ),
            
            TimePeriod.PRE_DAWN: TimeDescription(
                primary="the hours before dawn",
                variants=[
                    "the pre-dawn darkness",
                    "the final hours of night",
                    "just before daybreak",
                    "the threshold of dawn"
                ],
                atmospheric=[
                    "when the world holds its breath",
                    "as night prepares to yield to day",
                    "in the expectant darkness",
                    "when the eastern sky begins to stir"
                ],
                seasonal_modifiers={
                    "Winter": ["the bitter pre-dawn", "before winter's pale sunrise"],
                    "Summer": ["the gentle pre-dawn", "before summer's golden sunrise"],
                    "Spring": ["the fresh pre-dawn", "before spring's bright sunrise"],
                    "Fall": ["the crisp pre-dawn", "before autumn's misty sunrise"]
                }
            ),
            
            TimePeriod.DAWN: TimeDescription(
                primary="dawn",
                variants=[
                    "daybreak",
                    "sunrise", 
                    "the break of day",
                    "first light",
                    "the dawn's early light",
                    "the morning's first breath"
                ],
                atmospheric=[
                    "as the first rays pierce the darkness",
                    "when the eastern sky blooms with color",
                    "as night surrenders to day",
                    "when shadows begin their retreat",
                    "as the world awakens from slumber"
                ],
                seasonal_modifiers={
                    "Winter": ["the pale winter dawn", "dawn's cold embrace"],
                    "Summer": ["the golden summer sunrise", "dawn's warm caress"],
                    "Spring": ["the vibrant spring daybreak", "dawn's fresh kiss"],
                    "Fall": ["the misty autumn sunrise", "dawn's gentle touch"]
                }
            ),
            
            TimePeriod.MORNING: TimeDescription(
                primary="morning",
                variants=[
                    "early morning",
                    "mid-morning", 
                    "late morning",
                    "the morning hours",
                    "forenoon"
                ],
                atmospheric=[
                    "as the day gains strength",
                    "when morning mist dances",
                    "while dew still glitters",
                    "as the world comes alive",
                    "when birdsong fills the air"
                ],
                seasonal_modifiers={
                    "Winter": ["the crisp winter morning", "morning's frost-kissed air"],
                    "Summer": ["the bright summer morning", "morning's warm embrace"],
                    "Spring": ["the fresh spring morning", "morning's renewed energy"],
                    "Fall": ["the cool autumn morning", "morning's harvest scents"]
                }
            ),
            
            TimePeriod.NOON: TimeDescription(
                primary="midday",
                variants=[
                    "noon",
                    "the height of day",
                    "high noon",
                    "the meridian hour",
                    "when the sun stands highest"
                ],
                atmospheric=[
                    "when shadows grow short",
                    "as the sun reaches its peak",
                    "when the day blazes brightest",
                    "at the pinnacle of daylight",
                    "when the world basks in full sunlight"
                ],
                seasonal_modifiers={
                    "Winter": ["the pale winter noon", "midday's weak warmth"],
                    "Summer": ["the blazing summer noon", "midday's intense heat"],
                    "Spring": ["the pleasant spring midday", "noon's gentle warmth"],
                    "Fall": ["the mellow autumn noon", "midday's golden light"]
                }
            ),
            
            TimePeriod.AFTERNOON: TimeDescription(
                primary="afternoon",
                variants=[
                    "early afternoon",
                    "mid-afternoon",
                    "late afternoon", 
                    "the afternoon hours",
                    "post-meridian"
                ],
                atmospheric=[
                    "as the day matures",
                    "when shadows begin to lengthen",
                    "while warmth lingers in the air",
                    "as the sun starts its descent",
                    "when the day grows contemplative"
                ],
                seasonal_modifiers={
                    "Winter": ["the short winter afternoon", "afternoon's fleeting warmth"],
                    "Summer": ["the long summer afternoon", "afternoon's lingering heat"],
                    "Spring": ["the pleasant spring afternoon", "afternoon's mild air"],
                    "Fall": ["the golden autumn afternoon", "afternoon's harvest light"]
                }
            ),
            
            TimePeriod.EVENING: TimeDescription(
                primary="evening",
                variants=[
                    "early evening",
                    "late evening",
                    "the evening hours",
                    "eventide",
                    "vespers"
                ],
                atmospheric=[
                    "as day begins to fade",
                    "when shadows grow long",
                    "as the world prepares for rest",
                    "while daylight softens",
                    "when peace settles over the land"
                ],
                seasonal_modifiers={
                    "Winter": ["the early winter evening", "evening's cold embrace"],
                    "Summer": ["the long summer evening", "evening's gentle coolness"],
                    "Spring": ["the mild spring evening", "evening's fresh air"],
                    "Fall": ["the crisp autumn evening", "evening's harvest moon"]
                }
            ),
            
            TimePeriod.SUNSET: TimeDescription(
                primary="sunset",
                variants=[
                    "dusk",
                    "twilight",
                    "gloaming", 
                    "the dying of the light",
                    "day's end",
                    "the sunset hour"
                ],
                atmospheric=[
                    "as the sky burns with color",
                    "when day surrenders to night",
                    "as golden light fades to purple",
                    "while the sun kisses the horizon",
                    "when the world is painted in fire"
                ],
                seasonal_modifiers={
                    "Winter": ["the brief winter sunset", "dusk's cold beauty"],
                    "Summer": ["the spectacular summer sunset", "twilight's warm glow"],
                    "Spring": ["the hopeful spring sunset", "dusk's fresh promise"],
                    "Fall": ["the magnificent autumn sunset", "twilight's golden glory"]
                }
            ),
            
            TimePeriod.NIGHT: TimeDescription(
                primary="night",
                variants=[
                    "early night",
                    "nightfall",
                    "the night hours",
                    "darkness",
                    "nocturne"
                ],
                atmospheric=[
                    "as darkness claims the land",
                    "when stars begin to twinkle",
                    "while night creatures stir",
                    "as the moon rises",
                    "when the world grows quiet"
                ],
                seasonal_modifiers={
                    "Winter": ["the long winter night", "night's frozen stillness"],
                    "Summer": ["the short summer night", "night's gentle coolness"],
                    "Spring": ["the mild spring night", "night's awakening energy"],
                    "Fall": ["the crisp autumn night", "night's harvest mystery"]
                }
            )
        }
    
    def get_time_period(self, game_time: float) -> TimePeriod:
        """
        Determine the narrative time period from game time.
        
        Args:
            game_time: Game time in seconds since epoch
            
        Returns:
            The appropriate TimePeriod enum value
        """
        dt = game_time_to_datetime(game_time, GAME_EPOCH)
        hour = dt.hour
        
        if 0 <= hour < 4:
            return TimePeriod.DEEP_NIGHT
        elif 4 <= hour < 5:
            return TimePeriod.PRE_DAWN
        elif 5 <= hour < 7:
            return TimePeriod.DAWN
        elif 7 <= hour < 11:
            return TimePeriod.MORNING
        elif 11 <= hour < 13:
            return TimePeriod.NOON
        elif 13 <= hour < 17:
            return TimePeriod.AFTERNOON
        elif 17 <= hour < 20:
            return TimePeriod.EVENING
        elif 20 <= hour < 21:
            return TimePeriod.SUNSET
        else:  # 21 <= hour < 24
            return TimePeriod.NIGHT
    
    def get_time_description(self, game_time: float, 
                           style: str = "primary", 
                           season: Optional[str] = None,
                           avoid_repetition: bool = True) -> str:
        """
        Get a rich narrative description of the current time.
        
        Args:
            game_time: Game time in seconds since epoch
            style: Description style - "primary", "variant", "atmospheric", "seasonal"
            season: Current season for seasonal modifiers
            avoid_repetition: Whether to avoid recently used descriptions
            
        Returns:
            A narrative time description string
        """
        period = self.get_time_period(game_time)
        description_data = self._time_descriptions[period]
        
        # Build available descriptions based on style
        available_descriptions = []
        
        if style in ["primary", "any"]:
            available_descriptions.append(description_data.primary)
            
        if style in ["variant", "any"]:
            available_descriptions.extend(description_data.variants)
            
        if style in ["atmospheric", "any"]:
            available_descriptions.extend(description_data.atmospheric)
            
        if style == "seasonal" and season and season in description_data.seasonal_modifiers:
            available_descriptions.extend(description_data.seasonal_modifiers[season])
        elif style == "any" and season and season in description_data.seasonal_modifiers:
            available_descriptions.extend(description_data.seasonal_modifiers[season])
        
        # If no descriptions available, fall back to primary
        if not available_descriptions:
            available_descriptions = [description_data.primary]
        
        # Avoid repetition if requested
        if avoid_repetition:
            cache_key = f"{period.value}_{style}"
            recently_used = self._last_description_cache.get(cache_key, [])
            
            # Filter out recently used descriptions
            fresh_descriptions = [d for d in available_descriptions if d not in recently_used]
            if fresh_descriptions:
                available_descriptions = fresh_descriptions
            
            # Select description
            selected = random.choice(available_descriptions)
            
            # Update cache (keep last 3 descriptions)
            recently_used.append(selected)
            if len(recently_used) > 3:
                recently_used.pop(0)
            self._last_description_cache[cache_key] = recently_used
            
            return selected
        else:
            return random.choice(available_descriptions)
    
    def get_contextual_time(self, game_time: float, 
                          context: str = "general",
                          season: Optional[str] = None) -> str:
        """
        Get a contextually appropriate time description.
        
        Args:
            game_time: Game time in seconds since epoch
            context: Context type - "general", "narrative", "combat", "social"
            season: Current season
            
        Returns:
            A contextually appropriate time description
        """
        if context == "narrative":
            return self.get_time_description(game_time, "atmospheric", season)
        elif context == "combat":
            return self.get_time_description(game_time, "primary", season)
        elif context == "social":
            return self.get_time_description(game_time, "variant", season)
        else:
            return self.get_time_description(game_time, "any", season)
    
    def is_daylight_period(self, game_time: float) -> bool:
        """
        Check if the current time is considered daylight.
        
        Args:
            game_time: Game time in seconds since epoch
            
        Returns:
            True if it's a daylight period, False otherwise
        """
        period = self.get_time_period(game_time)
        daylight_periods = {
            TimePeriod.DAWN, TimePeriod.MORNING, 
            TimePeriod.NOON, TimePeriod.AFTERNOON
        }
        return period in daylight_periods
    
    def is_night_period(self, game_time: float) -> bool:
        """
        Check if the current time is considered nighttime.
        
        Args:
            game_time: Game time in seconds since epoch
            
        Returns:
            True if it's a night period, False otherwise
        """
        period = self.get_time_period(game_time)
        night_periods = {
            TimePeriod.DEEP_NIGHT, TimePeriod.PRE_DAWN,
            TimePeriod.SUNSET, TimePeriod.NIGHT
        }
        return period in night_periods
    
    def is_transition_period(self, game_time: float) -> bool:
        """
        Check if the current time is a transition period (dawn/dusk).
        
        Args:
            game_time: Game time in seconds since epoch
            
        Returns:
            True if it's a transition period, False otherwise
        """
        period = self.get_time_period(game_time)
        return period in {TimePeriod.DAWN, TimePeriod.SUNSET}
    
    def get_period_info(self, game_time: float) -> Dict[str, any]:
        """
        Get comprehensive information about the current time period.
        
        Args:
            game_time: Game time in seconds since epoch
            
        Returns:
            Dictionary with period information
        """
        period = self.get_time_period(game_time)
        
        return {
            "period": period.value,
            "is_daylight": self.is_daylight_period(game_time),
            "is_night": self.is_night_period(game_time),
            "is_transition": self.is_transition_period(game_time),
            "description": self.get_time_description(game_time),
            "atmospheric_description": self.get_time_description(game_time, "atmospheric"),
        }


# Singleton instance
_time_manager_instance = None


def get_enhanced_time_manager() -> EnhancedTimeManager:
    """
    Get the singleton instance of the Enhanced Time Manager.
    
    Returns:
        The EnhancedTimeManager singleton instance
    """
    global _time_manager_instance
    if _time_manager_instance is None:
        _time_manager_instance = EnhancedTimeManager()
        logger.info("Enhanced Time Manager initialized")
    return _time_manager_instance


# Convenience functions for easy integration
def get_narrative_time(game_time: float, season: Optional[str] = None) -> str:
    """Get a narrative time description for the given game time."""
    return get_enhanced_time_manager().get_contextual_time(game_time, "narrative", season)


def get_simple_time(game_time: float, season: Optional[str] = None) -> str:
    """Get a simple time description for the given game time."""
    return get_enhanced_time_manager().get_time_description(game_time, "primary", season)


def is_daylight(game_time: float) -> bool:
    """Check if the given game time is during daylight hours."""
    return get_enhanced_time_manager().is_daylight_period(game_time)


def is_nighttime(game_time: float) -> bool:
    """Check if the given game time is during nighttime hours."""
    return get_enhanced_time_manager().is_night_period(game_time)


if __name__ == "__main__":
    # Example usage and testing
    import time
    from core.utils.time_utils import DAY, HOUR
    
    # Test different times of day
    test_times = [
        (2 * HOUR, "Deep Night"),
        (5 * HOUR, "Dawn"), 
        (9 * HOUR, "Morning"),
        (12 * HOUR, "Noon"),
        (15 * HOUR, "Afternoon"),
        (18 * HOUR, "Evening"),
        (20.5 * HOUR, "Sunset"),
        (22 * HOUR, "Night")
    ]
    
    manager = get_enhanced_time_manager()
    
    print("=== Enhanced Time Manager Test ===\n")
    
    for game_time, label in test_times:
        print(f"{label} ({game_time/HOUR:.1f}h):")
        print(f"  Primary: {manager.get_time_description(game_time, 'primary')}")
        print(f"  Variant: {manager.get_time_description(game_time, 'variant')}")
        print(f"  Atmospheric: {manager.get_time_description(game_time, 'atmospheric')}")
        print(f"  Seasonal (Spring): {manager.get_time_description(game_time, 'seasonal', 'Spring')}")
        print(f"  Contextual: {manager.get_contextual_time(game_time, 'narrative', 'Spring')}")
        print(f"  Is Daylight: {manager.is_daylight_period(game_time)}")
        print()