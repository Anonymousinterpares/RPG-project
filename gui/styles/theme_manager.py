# gui/styles/theme_manager.py
"""
Manages loading and switching UI themes.
"""
import logging
import importlib
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("GUI")

class ThemeManager(QObject):
    """Singleton class to manage the application's visual theme."""
    
    theme_changed = Signal(dict)
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._current_theme_name: str = ""
        self._current_palette: dict = {}
        self._initialized = True
        logger.info("ThemeManager initialized.")

    def load_theme(self, theme_name: str):
        """
        Loads a theme palette from a module and notifies listeners.
        
        Args:
            theme_name: The name of the theme to load (e.g., 'fantasy_dark').
        """
        if self._current_theme_name == theme_name and self._current_palette:
            logger.debug(f"Theme '{theme_name}' is already loaded.")
            return

        try:
            module_path = f"gui.styles.themes.{theme_name}_theme"
            theme_module = importlib.import_module(module_path)
            # In case the file is updated, reload the module
            importlib.reload(theme_module)
            
            self._current_palette = getattr(theme_module, 'THEME')
            self._current_theme_name = theme_name
            logger.info(f"Theme '{theme_name}' loaded successfully.")
            
            # Emit the signal to notify all UI components of the change
            self.theme_changed.emit(self._current_palette)
            
        except (ImportError, AttributeError, ModuleNotFoundError) as e:
            logger.error(f"Error loading theme '{theme_name}': {e}", exc_info=True)
            # Optionally, load a fallback theme
            if self._current_theme_name != 'fantasy_dark': # Avoid recursion
                logger.warning("Falling back to 'fantasy_dark' theme.")
                self.load_theme('fantasy_dark')

    def get_current_palette(self) -> dict:
        """
        Returns the currently loaded theme palette. Loads default if none is loaded.
        """
        if not self._current_palette:
            self.load_theme('fantasy_dark') # Default theme
        return self._current_palette

# Singleton instance
_theme_manager_instance = ThemeManager()

def get_theme_manager() -> ThemeManager:
    """Returns the singleton instance of the ThemeManager."""
    return _theme_manager_instance