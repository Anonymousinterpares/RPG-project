"""
Stats integration module for connecting the stats system to the GUI.

This module provides functionality to integrate the stats system with the GUI,
ensuring that the stats tab in the GUI is always up to date.
"""

from typing import Dict, Any, Callable
from PySide6.QtCore import QObject, Signal

from core.base.state.state_manager import get_state_manager
from core.utils.logging_config import get_logger

# Get module logger
logger = get_logger("STATS_INTEGRATION")

class StatsIntegration(QObject):
    """
    Class for integrating stats with the GUI.
    
    This class provides signals for stats changes and methods for updating the GUI.
    It acts as a bridge between the stats system and the GUI.
    """
    
    # Signal emitted when stats change
    stats_changed = Signal(dict)
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(StatsIntegration, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the stats integration."""
        if self._initialized:
            return
            
        super().__init__()
        
        # State manager reference
        self._state_manager = get_state_manager()
        
        # Last known stats state
        self._last_stats = {}
        
        # Callbacks for specific stat changes
        self._stat_callbacks = {}
        
        self._initialized = True
        
        logger.info("Stats integration initialized")
    
    def update_gui(self):
        """
        Update the GUI with the current stats.
        
        This method retrieves the current stats from the stats manager
        and emits the stats_changed signal if they have changed.
        """
        if not self._state_manager or not self._state_manager.stats_manager:
            logger.debug("Stats manager not available")
            return
        
        try:
            # Get all stats
            current_stats = self._state_manager.stats_manager.get_all_stats()
            
            # Check if stats have changed
            if current_stats != self._last_stats:
                # Store the new stats
                self._last_stats = current_stats
                
                # Emit signal with the stats
                self.stats_changed.emit(current_stats)
                
                # Call any registered callbacks
                self._call_stat_callbacks(current_stats)
                
                logger.debug("Stats updated in GUI")
        except Exception as e:
            logger.error(f"Error updating stats in GUI: {e}")
    
    def register_stat_callback(self, stat_name: str, callback: Callable[[Any], None]):
        """
        Register a callback for a specific stat.
        
        Args:
            stat_name: The name of the stat (e.g., "strength", "health").
            callback: The callback function to call when the stat changes.
                     The function should take a single argument, which is the stat value.
        """
        if stat_name not in self._stat_callbacks:
            self._stat_callbacks[stat_name] = []
        
        self._stat_callbacks[stat_name].append(callback)
        logger.debug(f"Registered callback for stat: {stat_name}")
    
    def unregister_stat_callback(self, stat_name: str, callback: Callable[[Any], None]):
        """
        Unregister a callback for a specific stat.
        
        Args:
            stat_name: The name of the stat.
            callback: The callback function to unregister.
        """
        if stat_name in self._stat_callbacks:
            if callback in self._stat_callbacks[stat_name]:
                self._stat_callbacks[stat_name].remove(callback)
                logger.debug(f"Unregistered callback for stat: {stat_name}")
    
    def _call_stat_callbacks(self, stats: Dict[str, Dict[str, Dict[str, Any]]]):
        """
        Call registered callbacks for stats that have changed.
        
        Args:
            stats: The current stats dictionary.
        """
        # Iterate through all stat categories and stats
        for category, category_stats in stats.items():
            for stat_name, stat_info in category_stats.items():
                # Check if there are callbacks for this stat
                callbacks = self._stat_callbacks.get(stat_name.lower(), [])
                
                # Call each callback with the stat value
                for callback in callbacks:
                    try:
                        callback(stat_info)
                    except Exception as e:
                        logger.error(f"Error calling callback for stat {stat_name}: {e}")
    
    def attach_to_stat_manager(self):
        """
        Attach to the stats manager to receive updates.
        
        This method should be called after the stats manager is initialized.
        """
        try:
            from core.stats.stats_manager import StatsManager
            
            # Get stats manager instance
            stats_manager = self._state_manager.stats_manager
            
            if stats_manager:
                # Add this as an observer or hook into the stats manager's update methods
                # This will depend on how the stats manager is implemented
                
                # For now, we'll need to poll regularly or integrate with the stats manager
                # when it's fully implemented
                
                logger.info("Attached to stats manager")
                return True
            else:
                logger.warning("Stats manager not available")
                return False
        except Exception as e:
            logger.error(f"Error attaching to stats manager: {e}")
            return False


# Convenience function
def get_stats_integration() -> StatsIntegration:
    """Get the stats integration instance."""
    return StatsIntegration()
