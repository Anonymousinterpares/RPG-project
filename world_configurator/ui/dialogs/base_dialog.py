"""
Base dialog class for the World Configurator Tool.
"""

import logging
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QScreen

logger = logging.getLogger("world_configurator.ui.dialogs.base_dialog")


class BaseDialog(QDialog):
    """Base class for dialogs to enforce maximum size constraints."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._constrained_to_screen = False
    
    def showEvent(self, event):
        """Override showEvent to constrain dialog size to screen dimensions."""
        try:
            if not self._constrained_to_screen:
                screen = self.screen()
                if screen:
                    screen_geometry = screen.availableGeometry()
                    max_width = int(screen_geometry.width() * 0.9)
                    max_height = int(screen_geometry.height() * 0.9)
                    
                    # Set maximum size
                    self.setMaximumSize(QSize(max_width, max_height))
                    
                    # Adjust current size if needed
                    current_size = self.size()
                    new_width = min(current_size.width(), max_width)
                    new_height = min(current_size.height(), max_height)
                    
                    if new_width != current_size.width() or new_height != current_size.height():
                        self.resize(new_width, new_height)
                    
                    # Center on screen if possible
                    self.move(
                        screen_geometry.center().x() - self.width() // 2,
                        screen_geometry.center().y() - self.height() // 2
                    )
                
                self._constrained_to_screen = True
                
        except Exception as e:
            logger.error(f"Error adjusting dialog size in BaseDialog.showEvent for '{self.windowTitle()}': {e}", exc_info=True)
            # Ensure the flag is set even on error to prevent repeated attempts
            self._constrained_to_screen = True
        
        super().showEvent(event)