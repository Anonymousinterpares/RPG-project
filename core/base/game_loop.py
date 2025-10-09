#!/usr/bin/env python3
"""
Game loop and time management for the RPG game.

This module provides classes for managing the game loop, 
game time, and tick processing. It handles advancing time
in the game world and executing scheduled events.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Union, Callable
from enum import Enum, auto
import datetime
import logging

from core.utils.logging_config import get_logger
from core.base.state import WorldState

# Get the module logger
logger = get_logger("GAME")

class GameSpeed(Enum):
    """Game speed settings."""
    PAUSED = 0
    NORMAL = 1
    FAST = 3
    SUPER_FAST = 10


@dataclass
class GameTime:
    """
    Game time management.
    
    This class handles tracking and manipulating the game time,
    including conversions between real time and game time.
    
    NOTE: DEPRECATED (Phase 1): The project no longer advances time based on
    real-world passage. Fields like `time_scale` and `start_time` are kept
    for backward compatibility and serialization only and should not be used
    to compute world time. Game time now advances only via explicit
    game context (LLM `time_passage`) and the fixed post-combat increment.
    """
    # Current game time in seconds
    game_time: float = 0.0
    
    # Time scale (game seconds per real second)
    # DEPRECATED: Retained for backward compatibility. Do not use.
    time_scale: float = 60.0  # Default preserved for legacy reads
    
    # Game start timestamp (real time)
    # DEPRECATED: Retained for backward compatibility. Do not use.
    start_time: float = field(default_factory=time.time)
    
    # Day cycle in seconds (24 hours)
    DAY_CYCLE: float = 24 * 60 * 60  # 86400 seconds
    
    # Hour in seconds
    HOUR: float = 60 * 60  # 3600 seconds
    
    # Minute in seconds
    MINUTE: float = 60  # 60 seconds
    
    def get_game_datetime(self) -> datetime.datetime:
        """
        Get the current game time as a datetime object.
        
        Returns:
            A datetime object representing the current game time.
        """
        # Use a fixed start date for the game world
        start_date = datetime.datetime(year=1000, month=1, day=1)
        
        # Calculate the total days that have passed
        days_passed = int(self.game_time / self.DAY_CYCLE)
        
        # Calculate the remaining seconds in the current day
        day_seconds = self.game_time % self.DAY_CYCLE
        
        # Create a timedelta and add it to the start date
        delta = datetime.timedelta(days=days_passed, seconds=day_seconds)
        return start_date + delta
    
    def get_formatted_time(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Get the current game time as a formatted string.
        
        Args:
            format_str: The format string to use.
        
        Returns:
            A formatted string representing the current game time.
        """
        return self.get_game_datetime().strftime(format_str)
    
    def get_time_of_day(self) -> str:
        """
        Get the current time of day as a narrative description.
        
        DEPRECATED: This method now uses enhanced time descriptions.
        
        Returns:
            A narrative description of the time of day (e.g., "morning", "sunset", "deep night").
        """
        try:
            from core.utils.enhanced_time_manager import get_simple_time
            return get_simple_time(self.game_time)
        except ImportError:
            # Fallback to old logic if enhanced time manager not available
            hour = self.get_game_datetime().hour
            
            if 5 <= hour < 12:
                return "Morning"
            elif 12 <= hour < 17:
                return "Afternoon"
            elif 17 <= hour < 21:
                return "Evening"
            else:
                return "Night"
    
    def advance(self, seconds: float) -> None:
        """
        Advance the game time by the specified number of seconds.
        
        Args:
            seconds: The number of seconds to advance.
        """
        self.game_time += seconds
        logger.debug(f"Game time advanced by {seconds} seconds to {self.get_formatted_time()}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert GameTime to a dictionary for serialization."""
        return {
            "game_time": self.game_time,
            "time_scale": self.time_scale,
            "start_time": self.start_time,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameTime':
        """Create a GameTime from a dictionary."""
        return cls(
            game_time=data.get("game_time", 0.0),
            time_scale=data.get("time_scale", 60.0),
            start_time=data.get("start_time", time.time()),
        )


@dataclass
class ScheduledEvent:
    """
    An event scheduled to occur at a specific game time.
    
    This dataclass represents a function to be called when the game
    time reaches a specific value.
    """
    time: float  # Game time when the event should occur
    callback: Callable[[], None]  # Function to call
    id: str  # Unique identifier
    repeats: bool = False  # Whether the event repeats
    interval: Optional[float] = None  # Interval for repeating events


class GameLoop:
    """
    Game loop manager.
    
    This class manages the game loop, including tick processing,
    time advancement, and scheduled events. It provides control
    over game speed and pausing.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(GameLoop, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, world_state = None):
        """Initialize the game loop."""
        if self._initialized:
            return
        
        # Game time
        self._game_time = GameTime()
        
        # Game speed
        self._speed = GameSpeed.NORMAL
        
        # Paused state
        self._paused = True
        
        # Tick counter
        self._tick_count = 0
        
        # Last real-time tick
        self._last_tick_time = time.time()
        
        # Callbacks for tick events
        self._tick_callbacks: List[Callable[[float], None]] = []
        
        # Scheduled events
        self._events: Dict[str, ScheduledEvent] = {}
        
        # Reference to the world state (for time updates)
        self._world_state = world_state
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Phase 1: Disable real-time advancement of game time.
        # Time now advances only via explicit engine calls (LLM time_passage, post-combat increment).
        self._time_advance_disabled: bool = True
        logger.info("GameLoop initialized with time advancement DISABLED (Phase 1).")
        
        self._initialized = True
    
    @property
    def game_time(self) -> GameTime:
        """Get the game time."""
        return self._game_time
    
    @property
    def is_paused(self) -> bool:
        """Check if the game is paused."""
        return self._paused
    
    @property
    def is_running(self) -> bool:
        """Compatibility property for web server - checks if game is running (not paused)."""
        return not self._paused
    
    @property
    def speed(self) -> GameSpeed:
        """Get the game speed."""
        return self._speed
    
    @speed.setter
    def speed(self, value: GameSpeed) -> None:
        """Set the game speed.
        NOTE: Phase 1 – time advancement is disabled; speed changes have no effect on time.
        """
        if not isinstance(value, GameSpeed):
            raise TypeError(f"Expected GameSpeed, got {type(value)}")
        
        with self._lock:
            self._speed = value
            logger.debug(f"Game speed set to {value.name}")
            if self._time_advance_disabled:
                logger.warning("GameLoop speed changed while time advancement is DISABLED. This does not affect world time (Phase 1).")
    
    def set_world_state(self, world_state: WorldState) -> None:
        """
        Set the world state reference.
        
        Args:
            world_state: The world state to reference.
        """
        with self._lock:
            self._world_state = world_state
    
    def pause(self) -> None:
        """Pause the game loop."""
        with self._lock:
            if not self._paused:
                self._paused = True
                logger.debug("Game paused")
    
    def unpause(self) -> None:
        """Unpause the game loop.
        NOTE: Phase 1 – unpausing does not cause time progression by itself.
        """
        with self._lock:
            if self._paused:
                self._paused = False
                self._last_tick_time = time.time()  # Reset the tick timer
                logger.debug("Game unpaused")
                if self._time_advance_disabled:
                    logger.warning("GameLoop unpaused while time advancement is DISABLED. No time progression will occur (Phase 1).")
    
    def toggle_pause(self) -> bool:
        """
        Toggle the pause state.
        
        Returns:
            The new pause state (True if paused, False if unpaused).
        """
        with self._lock:
            if self._paused:
                self.unpause()
            else:
                self.pause()
            return self._paused
    
    def add_tick_callback(self, callback: Callable[[float], None]) -> None:
        """
        Add a callback to be called on every tick.
        
        Args:
            callback: A function that takes the elapsed game time as an argument.
        """
        with self._lock:
            self._tick_callbacks.append(callback)
    
    def remove_tick_callback(self, callback: Callable[[float], None]) -> None:
        """
        Remove a tick callback.
        
        Args:
            callback: The callback to remove.
        """
        with self._lock:
            if callback in self._tick_callbacks:
                self._tick_callbacks.remove(callback)
    
    def schedule_event(self, game_time: float, callback: Callable[[], None], 
                      event_id: str, repeats: bool = False, 
                      interval: Optional[float] = None) -> None:
        """
        Schedule an event to occur at a specific game time.
        
        Args:
            game_time: The game time when the event should occur.
            callback: The function to call when the event occurs.
            event_id: A unique identifier for the event.
            repeats: Whether the event repeats.
            interval: The interval for repeating events.
        """
        with self._lock:
            if event_id in self._events:
                logger.warning(f"Replacing existing event with ID {event_id}")
            
            self._events[event_id] = ScheduledEvent(
                time=game_time,
                callback=callback,
                id=event_id,
                repeats=repeats,
                interval=interval
            )
            
            logger.debug(f"Scheduled event {event_id} at game time {game_time}")
    
    def cancel_event(self, event_id: str) -> bool:
        """
        Cancel a scheduled event.
        
        Args:
            event_id: The ID of the event to cancel.
        
        Returns:
            True if the event was cancelled, False if not found.
        """
        with self._lock:
            if event_id in self._events:
                del self._events[event_id]
                logger.debug(f"Cancelled event {event_id}")
                return True
            return False
    
    def tick(self) -> None:
        """
        Process a single tick.
        
        Phase 1: Real-time based advancement is DISABLED. This tick will not advance
        world time. It will only notify callbacks with 0 elapsed time to avoid
        breaking any auxiliary logic that may still listen to ticks.
        """
        with self._lock:
            # Skip if paused
            if self._paused:
                self._last_tick_time = time.time()
                return
            
            # Update last tick time to avoid drift in any external references
            self._last_tick_time = time.time()
            
            elapsed_game = 0.0
            old_game_time = self._game_time.game_time
            
            if not self._time_advance_disabled:
                # Defensive: If someone re-enabled it, warn and still prevent advancement.
                logger.error("GameLoop time advancement was re-enabled unexpectedly. Preventing advancement (Phase 1 invariant).")
                self._time_advance_disabled = True
            
            # Do NOT advance self._game_time or world_state here.
            # Do NOT process scheduled events that depend on time progression.
            # (If event processing by absolute time is needed in future, it must be driven by explicit time passage.)
            
            # Call tick callbacks with 0 elapsed
            for callback in self._tick_callbacks:
                try:
                    callback(elapsed_game)
                except Exception as e:
                    logger.error(f"Error in tick callback: {e}", exc_info=True)
            
            # Increment tick counter
            self._tick_count += 1
            
            # Log tick data at debug level periodically
            if self._tick_count % 100 == 0:
                logger.debug(f"Tick {self._tick_count} (no-op advancement). Game time remains: {self._game_time.get_formatted_time()}")
    
    def _process_events(self, from_time: float, to_time: float) -> None:
        """
        Process events that should occur between the specified times.
        
        Args:
            from_time: The start of the time range.
            to_time: The end of the time range.
        """
        # Collect events to reschedule
        reschedule = []
        
        # Process each event
        for event_id, event in list(self._events.items()):
            # Check if the event time is in the range [from_time, to_time]
            if from_time <= event.time <= to_time:
                # Execute the event
                try:
                    event.callback()
                    logger.debug(f"Executed event {event_id}")
                except Exception as e:
                    logger.error(f"Error executing event {event_id}: {e}", exc_info=True)
                
                # Handle repeating events
                if event.repeats and event.interval is not None:
                    # Schedule the next occurrence
                    next_time = event.time + event.interval
                    reschedule.append((event_id, event.callback, next_time, event.repeats, event.interval))
                
                # Remove the event
                del self._events[event_id]
        
        # Reschedule repeating events
        for event_id, callback, next_time, repeats, interval in reschedule:
            self.schedule_event(next_time, callback, event_id, repeats, interval)
    
    def run(self, target_fps: int = 30) -> None:
        """
        Run the game loop at the specified framerate.
        
        Phase 1: Time advancement is disabled. This loop will not advance world time.
        
        Args:
            target_fps: The target frames per second.
        """
        target_frame_time = 1.0 / target_fps
        running = True
        
        logger.warning(f"Starting GameLoop.run() with time advancement DISABLED (Phase 1). target_fps={target_fps}")
        
        try:
            while running:
                # Record the start time
                start_time = time.time()
                
                # Process a tick (no-op advancement)
                self.tick()
                
                # Calculate how long to sleep
                elapsed = time.time() - start_time
                sleep_time = max(0, target_frame_time - elapsed)
                
                # Sleep to maintain the target FPS
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            logger.info("Game loop interrupted")
        except Exception as e:
            logger.error(f"Error in game loop: {e}", exc_info=True)
        finally:
            logger.info("Game loop stopped")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert GameLoop state to a dictionary for serialization."""
        with self._lock:
            return {
                "game_time": self._game_time.to_dict(),
                "speed": self._speed.name,
                "paused": self._paused,
                "tick_count": self._tick_count,
                # Phase 1 flag (for diagnostics only; not required for load)
                "time_advance_disabled": True,
                # Note: We don't serialize callbacks or events as they are function references
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], world_state = None) -> 'GameLoop':
        """Create a GameLoop from a dictionary."""
        instance = cls(world_state)
        
        with instance._lock:
            if "game_time" in data:
                instance._game_time = GameTime.from_dict(data["game_time"])
            
            if "speed" in data:
                instance._speed = GameSpeed[data["speed"]]
            
            if "paused" in data:
                instance._paused = data["paused"]
            
            if "tick_count" in data:
                instance._tick_count = data["tick_count"]
            
            # Enforce Phase 1 invariant regardless of persisted data
            instance._time_advance_disabled = True
        
        return instance


# Convenience function
def get_game_loop() -> GameLoop:
    """Get the game loop instance."""
    return GameLoop()


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create a game loop
    loop = get_game_loop()
    
    # Add a tick callback
    def on_tick(elapsed_game_time):
        if loop.game_time.game_time % 3600 < elapsed_game_time:  # Every hour of game time
            print(f"Game time: {loop.game_time.get_formatted_time()}")
    
    loop.add_tick_callback(on_tick)
    
    # Schedule an event
    def test_event():
        print("Test event executed!")
    
    # Schedule to occur after 10 seconds of game time
    loop.schedule_event(
        loop.game_time.game_time + 10,
        test_event,
        "test_event"
    )
    
    # Start the game loop
    print("Starting game loop, press Ctrl+C to stop")
    loop.unpause()
    loop.run()