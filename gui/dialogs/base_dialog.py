#gui/dialogs/base_dialog.py
from typing import Any, Dict, Optional
from PySide6.QtWidgets import QDialog, QPushButton, QToolButton, QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget, QComboBox
from PySide6.QtCore import Slot
from core.utils.logging_config import get_logger
from gui.styles.stylesheet_factory import create_dialog_style
from gui.styles.theme_manager import get_theme_manager

logger = get_logger("BASE_DIALOG")
class BaseDialog(QDialog):
    """Base class for dialogs to enforce maximum size constraints and styling."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        main_window = self
        while hasattr(main_window, 'parent') and main_window.parent():
            main_window = main_window.parent()
            # Once we find an object that has the cursor attributes, we've found our source.
            if hasattr(main_window, 'normal_cursor'):
                break
        
        if hasattr(main_window, 'normal_cursor'):
            self.setCursor(main_window.normal_cursor)
            self._apply_cursors_to_children(main_window)

        # Apply initial theme
        self._update_theme()

    @Slot(dict)
    def _update_theme(self, palette: Optional[Dict[str, Any]] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        # Apply the standard dialog style
        self.setStyleSheet(create_dialog_style(self.palette))
        
        # Propagate theme update to any children that support it
        # This is useful for complex dialogs composed of other custom widgets
        for child in self.findChildren(object): # Iterate all QObjects
            if hasattr(child, '_update_theme') and callable(child._update_theme):
                # Avoid infinite recursion if child is self (shouldn't happen with findChildren but safe to check)
                if child is not self:
                     child._update_theme(self.palette)

    def _apply_cursors_to_children(self, main_window):
        """Finds all relevant child widgets and applies custom cursors from the main window."""
        if not hasattr(main_window, 'link_cursor'):
            return

        # --- LINK CURSOR ---
        link_widgets = self.findChildren(QPushButton) + \
                       self.findChildren(QToolButton) + \
                       self.findChildren(QListWidget) + \
                       self.findChildren(QTableWidget)
        for widget in link_widgets:
            widget.setCursor(main_window.link_cursor)
            # For lists/tables, the viewport is what matters for the item area
            if hasattr(widget, 'viewport'):
                widget.viewport().setCursor(main_window.link_cursor)

        # Special handling for ComboBox popups (which are QListViews)
        combos = self.findChildren(QComboBox)
        for combo in combos:
            combo.setCursor(main_window.link_cursor)
            if hasattr(combo, 'view') and combo.view():
                combo.view().setCursor(main_window.link_cursor)

        # --- TEXT CURSOR ---
        if hasattr(main_window, 'text_cursor'):
            # QLineEdit
            line_edits = [w for w in self.findChildren(QLineEdit) if not w.isReadOnly()]
            for widget in line_edits:
                widget.setCursor(main_window.text_cursor)

            # QTextEdit and QPlainTextEdit
            text_areas = self.findChildren(QTextEdit) + self.findChildren(QPlainTextEdit)
            editable_text_areas = [widget for widget in text_areas if not widget.isReadOnly()]
            for widget in editable_text_areas:
                widget.viewport().setCursor(main_window.text_cursor)
        
        # --- NORMAL CURSOR for Read-Only Text ---
        if hasattr(main_window, 'normal_cursor'):
            text_areas = self.findChildren(QTextEdit) + self.findChildren(QPlainTextEdit)
            read_only_areas = [widget for widget in text_areas if widget.isReadOnly()]
            for widget in read_only_areas:
                widget.viewport().setCursor(main_window.normal_cursor)

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