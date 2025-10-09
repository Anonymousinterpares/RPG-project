#!/usr/bin/env python3
"""
Time utilities for the RPG game.

This module provides utility functions for manipulating and formatting
time in the game world, including conversions between game time and
real time, and human-readable time formatting.
"""

import time
import datetime
from typing import Optional, Tuple, Union, Dict, Any
import logging

from core.utils.logging_config import get_logger

# Get the module logger
logger = get_logger("SYSTEM")

# Constants for time units in seconds
SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY
MONTH = 30 * DAY  # Approximation
YEAR = 365 * DAY  # Approximation

# Default game time scale (1 real second = 60 game seconds)
DEFAULT_TIME_SCALE = 60.0

# Game time epoch (reference point for game time)
# Using Jan 1, 1000 as a default fantasy setting start date
GAME_EPOCH = datetime.datetime(year=1000, month=1, day=1)


def game_time_to_datetime(game_time: float, epoch: datetime.datetime = None) -> datetime.datetime:
    """
    Convert game time (seconds since game epoch) to a datetime object.
    
    Args:
        game_time: The game time in seconds since the epoch.
        epoch: The reference epoch datetime. If None, uses GAME_EPOCH.
    
    Returns:
        A datetime object representing the game time.
    """
    epoch = epoch or GAME_EPOCH
    
    # Calculate days and remaining seconds
    days = int(game_time / DAY)
    remaining_seconds = game_time % DAY
    
    # Add to the epoch
    return epoch + datetime.timedelta(days=days, seconds=remaining_seconds)


def datetime_to_game_time(dt: datetime.datetime, epoch: datetime.datetime = None) -> float:
    """
    Convert a datetime object to game time (seconds since game epoch).
    
    Args:
        dt: The datetime to convert.
        epoch: The reference epoch datetime. If None, uses GAME_EPOCH.
    
    Returns:
        The game time in seconds.
    """
    epoch = epoch or GAME_EPOCH
    
    # Calculate the difference
    delta = dt - epoch
    
    # Convert to seconds
    return delta.total_seconds()


def format_game_time(game_time: float, format_str: str = "%Y-%m-%d %H:%M:%S", 
                   epoch: datetime.datetime = None) -> str:
    """
    Format game time as a string using a datetime format string.
    
    Args:
        game_time: The game time in seconds since the epoch.
        format_str: The format string to use.
        epoch: The reference epoch datetime. If None, uses GAME_EPOCH.
    
    Returns:
        A formatted string representing the game time.
    """
    dt = game_time_to_datetime(game_time, epoch)
    return dt.strftime(format_str)


def format_time_of_day(game_time: float, epoch: datetime.datetime = None) -> str:
    """
    DEPRECATED: Use enhanced_time_manager.get_simple_time() instead.
    
    Get the time of day as a string (e.g., "Morning", "Afternoon").
    This function is kept for backward compatibility but now delegates
    to the enhanced time manager for better narrative descriptions.
    
    Args:
        game_time: The game time in seconds since the epoch.
        epoch: The reference epoch datetime. If None, uses GAME_EPOCH.
    
    Returns:
        A string representing the time of day.
    """
    logger.warning("format_time_of_day() is deprecated, use enhanced_time_manager.get_simple_time() instead")
    
    # Use enhanced time manager for better descriptions
    try:
        from core.utils.enhanced_time_manager import get_simple_time
        return get_simple_time(game_time)
    except ImportError:
        # Fallback to old logic if enhanced time manager not available
        dt = game_time_to_datetime(game_time, epoch)
        hour = dt.hour
        
        if 5 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 17:
            return "Afternoon"
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"


def format_date(game_time: float, epoch: datetime.datetime = None) -> str:
    """
    Format the game date in a human-readable way.
    
    Args:
        game_time: The game time in seconds since the epoch.
        epoch: The reference epoch datetime. If None, uses GAME_EPOCH.
    
    Returns:
        A formatted date string (e.g., "January 1, 1000").
    """
    dt = game_time_to_datetime(game_time, epoch)
    return dt.strftime("%B %d, %Y")


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds as a human-readable string.
    
    Args:
        seconds: The duration in seconds.
    
    Returns:
        A formatted duration string (e.g., "2 days, 3 hours, 45 minutes").
    """
    # Handle negative durations
    is_negative = seconds < 0
    seconds = abs(seconds)
    
    # Calculate time units
    days, remainder = divmod(seconds, DAY)
    hours, remainder = divmod(remainder, HOUR)
    minutes, seconds = divmod(remainder, MINUTE)
    
    # Build the string
    parts = []
    
    if days > 0:
        parts.append(f"{int(days)} day{'' if days == 1 else 's'}")
    
    if hours > 0:
        parts.append(f"{int(hours)} hour{'' if hours == 1 else 's'}")
    
    if minutes > 0:
        parts.append(f"{int(minutes)} minute{'' if minutes == 1 else 's'}")
    
    if seconds > 0 or not parts:
        # Only include seconds if it's the only component or if there are some
        parts.append(f"{int(seconds)} second{'' if seconds == 1 else 's'}")
    
    # Join with commas and add negative sign if needed
    result = ", ".join(parts)
    if is_negative:
        result = f"negative {result}"
    
    return result


def parse_time_string(time_str: str) -> Optional[float]:
    """
    Parse a time string into seconds.
    
    Supports formats like:
    - "10s" (10 seconds)
    - "5m" (5 minutes)
    - "2h" (2 hours)
    - "1d" (1 day)
    - "1h30m" (1 hour and 30 minutes)
    
    Args:
        time_str: The time string to parse.
    
    Returns:
        The time in seconds, or None if parsing failed.
    """
    try:
        # Replace common variations
        time_str = time_str.lower().replace(" ", "")
        
        # Initialize total seconds
        total_seconds = 0
        
        # Parse different units
        units = {
            "s": SECOND,
            "m": MINUTE,
            "h": HOUR,
            "d": DAY,
            "w": WEEK,
            "mo": MONTH,
            "y": YEAR
        }
        
        # Extract numbers followed by units
        import re
        pattern = r"(\d+)([a-z]+)"
        matches = re.findall(pattern, time_str)
        
        if not matches:
            # Try to parse as a plain number (assumed to be seconds)
            try:
                return float(time_str)
            except ValueError:
                return None
        
        # Sum up all parts
        for value_str, unit in matches:
            value = float(value_str)
            
            if unit not in units:
                logger.warning(f"Unknown time unit: {unit}")
                return None
            
            total_seconds += value * units[unit]
        
        return total_seconds
    
    except Exception as e:
        logger.warning(f"Error parsing time string '{time_str}': {e}")
        return None


def real_to_game_time(real_seconds: float, time_scale: float = DEFAULT_TIME_SCALE) -> float:
    """
    DEPRECATED (Phase 1): Real-time based conversions are no longer used to advance
    world time. This function remains for legacy compatibility only.
    
    Args:
        real_seconds: The real time in seconds.
        time_scale: The time scale (game seconds per real second).
    
    Returns:
        The game time in seconds.
    """
    logger.warning("time_utils.real_to_game_time called (DEPRECATED in Phase 1)")
    return real_seconds * time_scale


def game_to_real_time(game_seconds: float, time_scale: float = DEFAULT_TIME_SCALE) -> float:
    """
    DEPRECATED (Phase 1): Real-time based conversions are no longer used to advance
    world time. This function remains for legacy compatibility only.
    
    Args:
        game_seconds: The game time in seconds.
        time_scale: The time scale (game seconds per real second).
    
    Returns:
        The real time in seconds.
    """
    logger.warning("time_utils.game_to_real_time called (DEPRECATED in Phase 1)")
    if time_scale <= 0:
        logger.warning(f"Invalid time scale: {time_scale}")
        return 0
    
    return game_seconds / time_scale


def get_current_game_time(start_time: float, elapsed_real: float, 
                        time_scale: float = DEFAULT_TIME_SCALE) -> float:
    """
    DEPRECATED (Phase 1): Real-time based calculations are no longer used to
    determine world time. This function remains for legacy compatibility only.
    
    Args:
        start_time: The starting game time.
        elapsed_real: The elapsed real time since the game started.
        time_scale: The time scale (game seconds per real second).
    
    Returns:
        The current game time.
    """
    logger.warning("time_utils.get_current_game_time called (DEPRECATED in Phase 1)")
    return start_time + real_to_game_time(elapsed_real, time_scale)


def is_daytime(game_time: float, epoch: datetime.datetime = None) -> bool:
    """
    Check if the current game time is daytime (between 6 AM and 6 PM).
    
    Args:
        game_time: The game time in seconds since the epoch.
        epoch: The reference epoch datetime. If None, uses GAME_EPOCH.
    
    Returns:
        True if it's daytime, False otherwise.
    """
    dt = game_time_to_datetime(game_time, epoch)
    hour = dt.hour
    return 6 <= hour < 18


def get_season(game_time: float, epoch: datetime.datetime = None) -> str:
    """
    Get the current season based on the game time.
    
    Args:
        game_time: The game time in seconds since the epoch.
        epoch: The reference epoch datetime. If None, uses GAME_EPOCH.
    
    Returns:
        The current season ("Spring", "Summer", "Fall", or "Winter").
    """
    dt = game_time_to_datetime(game_time, epoch)
    month = dt.month
    
    if 3 <= month < 6:
        return "Spring"
    elif 6 <= month < 9:
        return "Summer"
    elif 9 <= month < 12:
        return "Fall"
    else:
        return "Winter"


def time_until(target_game_time: float, current_game_time: float) -> float:
    """
    Calculate the game time until a target time.
    
    Args:
        target_game_time: The target game time.
        current_game_time: The current game time.
    
    Returns:
        The game time until the target time (negative if in the past).
    """
    return target_game_time - current_game_time


def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a Unix timestamp as a datetime string.
    
    Args:
        timestamp: The Unix timestamp (seconds since Jan 1, 1970).
        format_str: The format string to use.
    
    Returns:
        A formatted datetime string.
    """
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime(format_str)


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Example game time (1 day and 12 hours from epoch)
    game_time = DAY + 12 * HOUR
    
    # Convert to datetime
    dt = game_time_to_datetime(game_time)
    print(f"Game time {game_time} is datetime: {dt}")
    
    # Format as string
    formatted = format_game_time(game_time)
    print(f"Formatted: {formatted}")
    
    # Get time of day
    time_of_day = format_time_of_day(game_time)
    print(f"Time of day: {time_of_day}")
    
    # Parse a time string
    parsed = parse_time_string("2h30m15s")
    print(f"Parsed '2h30m15s': {parsed} seconds")
    
    # Convert real time to game time
    real_time = 60  # 1 minute real time
    converted = real_to_game_time(real_time)
    print(f"{real_time} seconds real time = {converted} seconds game time")
    
    # Format a duration
    duration = format_duration(parsed)
    print(f"Duration: {duration}")