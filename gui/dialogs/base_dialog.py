#gui/dialogs/base_dialog.py
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QSize
from PySide6.QtGui import QScreen # Correct import for QScreen

class BaseDialog(QDialog):
    """Base class for dialogs to enforce maximum size constraints."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Common dialog settings can go here if needed

    def showEvent(self, event):
        """Override showEvent to adjust maximum size safely."""
        # Let the default showEvent run first to ensure widgets are likely created
        super().showEvent(event)

        # Check if the dialog has already been adjusted in this show cycle
        # Use a flag that persists across show calls within a single instance lifecycle if needed,
        # but for maximum size constraint, checking per show is fine.
        # Let's rename the flag for clarity.
        if hasattr(self, '_constrained_to_screen') and self._constrained_to_screen:
             return

        try:
            screen = self.screen() # Get the screen the dialog is *currently* on
            if screen:
                available_geo = screen.availableGeometry()

                # Calculate max size (e.g., 95% of available space)
                max_w = int(available_geo.width() * 0.95)
                max_h = int(available_geo.height() * 0.95)

                # Only set maximum size if it's reasonable (avoid tiny max sizes)
                if max_w > 100 and max_h > 100:
                    self.setMaximumSize(max_w, max_h)
                else:
                    logger.warning(f"Calculated maximum size ({max_w}x{max_h}) is too small. Skipping setMaximumSize.")

                # Check current size against the calculated maximum
                current_w = self.width()
                current_h = self.height()

                # Calculate the ideal size based on content, but capped by max size
                hint_w = self.sizeHint().width()
                hint_h = self.sizeHint().height()
                ideal_w = min(max(current_w, hint_w), max_w) # Use size hint but respect current size if larger
                ideal_h = min(max(current_h, hint_h), max_h)

                # Resize *only* if the current size exceeds the calculated max size
                resize_needed = False
                if current_w > max_w:
                    current_w = max_w
                    resize_needed = True
                if current_h > max_h:
                    current_h = max_h
                    resize_needed = True

                if resize_needed:
                     logger.info(f"Dialog '{self.windowTitle()}' exceeds screen bounds. Resizing to fit ({current_w}x{current_h}).")
                     self.resize(current_w, current_h) # Resize down to max limits

            else:
                 logger.warning(f"Could not get screen for dialog '{self.windowTitle()}' during showEvent.")

            # Mark as constrained for this show event
            self._constrained_to_screen = True

        except Exception as e:
            logger.error(f"Error adjusting dialog size in BaseDialog.showEvent for '{self.windowTitle()}': {e}", exc_info=True)
            # Ensure the flag is set even on error to prevent repeated attempts
            self._constrained_to_screen = True


    def exec(self):
         """Override exec to ensure size adjustment flag is reset before showing."""
         # Reset the flag before showing modally
         self._constrained_to_screen = False
         # Let the default exec handle showing the dialog, which will trigger our showEvent
         return super().exec()

    def open(self):
        """Override open to ensure size adjustment flag is reset before showing."""
         # Reset the flag before showing modelessly
        self._constrained_to_screen = False
         # Let the default open handle showing the dialog, which will trigger our showEvent
        return super().open()