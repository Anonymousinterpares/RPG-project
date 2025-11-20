#!/usr/bin/env python3
"""
Skill check display widget for the RPG game GUI.
This module provides a widget for displaying skill check results in a visual way.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, Slot, QPropertyAnimation, QTimer, Property
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush

from core.stats.skill_check import SkillCheckResult
from gui.styles.theme_manager import get_theme_manager


class DiceWidget(QWidget):
    """Widget for displaying a dice roll result with animation."""
    
    def __init__(self, parent=None):
        """Initialize the dice widget."""
        super().__init__(parent)
        self.setMinimumSize(60, 60)
        self.setMaximumSize(60, 60)
        
        self._value = 1
        self._rolling = False
        self._roll_timer = QTimer(self)
        self._roll_timer.timeout.connect(self._update_rolling_value)
        
        # Set the background to be transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Theme
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self.update_theme)
    
    @Slot(dict)
    def update_theme(self, palette: Optional[dict] = None):
        """Update colors from the theme palette."""
        if palette:
            self.palette = palette
        self.update() # Trigger repaint with new colors

    def get_value(self) -> int:
        """Get the current dice value."""
        return self._value
    
    def set_value(self, value: int) -> None:
        """Set the dice value."""
        self._value = max(1, min(value, 20))  # Ensure value is between 1 and 20
        self.update()
    
    value = Property(int, get_value, set_value)
    
    def roll_animation(self, final_value: int, duration_ms: int = 1000) -> None:
        """
        Animate a dice roll to the final value.
        
        Args:
            final_value: The final dice value to show
            duration_ms: Duration of the animation in milliseconds
        """
        self._rolling = True
        self._final_value = max(1, min(final_value, 20))
        self._roll_timer.start(50)  # Update every 50ms
        
        # Set a timer to stop the rolling animation
        QTimer.singleShot(duration_ms, self._stop_rolling)
    
    def _update_rolling_value(self) -> None:
        """Update the dice value during rolling animation."""
        import random
        self.set_value(random.randint(1, 20))
    
    def _stop_rolling(self) -> None:
        """Stop the rolling animation and set the final value."""
        self._rolling = False
        self._roll_timer.stop()
        self.set_value(self._final_value)
    
    def paintEvent(self, event) -> None:
        """Paint the dice."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        colors = self.palette['colors']
        
        # Define the dice colors based on the value and theme
        if self._value == 20:
            # Critical success - gold
            bg_color = QColor(colors.get('text_primary', '#c9a875'))
            text_color = QColor(colors.get('bg_dark', '#1a1410'))
        elif self._value == 1:
            # Critical failure - red
            bg_color = QColor(colors.get('accent_negative', '#D94A38'))
            text_color = QColor(colors.get('text_bright', '#e8d4b8'))
        else:
            # Normal roll - white/bright text color
            bg_color = QColor(colors.get('text_bright', '#e8d4b8'))
            text_color = QColor(colors.get('bg_dark', '#1a1410'))
        
        # Draw the dice
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        # Draw the background
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(QColor(colors.get('bg_dark', '#1a1410')), 2))
        
        # Draw a circle as the dice
        painter.drawEllipse(rect)
        
        # Draw the value
        painter.setPen(QPen(text_color))
        font = QFont("Arial", 18, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, str(self._value))


class SkillCheckDisplay(QWidget):
    """Widget for displaying skill check results."""
    
    # Signal emitted when the display is finished
    display_finished = Signal()
    
    def __init__(self, parent=None):
        """Initialize the skill check display widget."""
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        # Set up the UI
        self._setup_ui()
        
        # Apply initial theme
        self._update_theme()
        
        # Hide the widget by default
        self.setVisible(False)
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)
        
        # Create the title label
        self.title_label = QLabel("Skill Check")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # Create the stat and difficulty display
        self.stat_layout = QHBoxLayout()
        
        self.stat_label = QLabel("Stat: STR")
        self.difficulty_label = QLabel("Difficulty: 15")
        
        self.stat_layout.addWidget(self.stat_label)
        self.stat_layout.addStretch(1)
        self.stat_layout.addWidget(self.difficulty_label)
        
        # Create the dice display
        self.dice_layout = QHBoxLayout()
        self.dice_layout.setAlignment(Qt.AlignCenter)
        
        self.dice_widget = DiceWidget()
        
        self.dice_layout.addWidget(self.dice_widget)
        
        # Create the result display
        self.result_layout = QHBoxLayout()
        
        self.mod_label = QLabel("Modifier: +0")
        self.total_label = QLabel("Total: 10")
        self.success_label = QLabel("SUCCESS")
        self.success_label.setAlignment(Qt.AlignCenter)
        
        self.result_layout.addWidget(self.mod_label)
        self.result_layout.addStretch(1)
        self.result_layout.addWidget(self.total_label)
        
        # Create the context display
        self.context_label = QLabel("Attempting to climb the steep cliff")
        self.context_label.setAlignment(Qt.AlignCenter)
        self.context_label.setWordWrap(True)
        
        # Create the XP display
        self.xp_label = QLabel("+0 XP")
        self.xp_label.setAlignment(Qt.AlignCenter)
        self.xp_label.setVisible(False)
        
        # Add all elements to the main layout
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addLayout(self.stat_layout)
        self.main_layout.addLayout(self.dice_layout)
        self.main_layout.addLayout(self.result_layout)
        self.main_layout.addWidget(self.success_label)
        self.main_layout.addWidget(self.xp_label)
        self.main_layout.addWidget(self.context_label)
        
        # Set a fixed size for the widget
        self.setFixedSize(300, 280) # Increased height slightly

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
            
        colors = self.palette['colors']
        
        self.setStyleSheet(f"""
            SkillCheckDisplay {{
                background-color: {colors['bg_medium']};
                border: 2px solid {colors['border_dark']};
                border-radius: 8px;
            }}
        """)
        
        self.title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {colors['text_primary']};
        """)
        
        stat_style = f"""
            font-size: 14px;
            font-weight: bold;
            color: {colors['text_secondary']};
        """
        self.stat_label.setStyleSheet(stat_style)
        self.difficulty_label.setStyleSheet(stat_style)
        
        self.mod_label.setStyleSheet(f"""
            font-size: 14px;
            color: {colors['text_secondary']};
        """)
        
        self.total_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {colors['text_bright']};
        """)
        
        self.context_label.setStyleSheet(f"""
            font-size: 14px;
            font-style: italic;
            color: {colors['text_secondary']};
        """)
        
        self.xp_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {colors.get('text_highlight', '#FFD700')};
        """)
        
        # Re-apply success/fail color based on current text
        text = self.success_label.text()
        if "CRITICAL SUCCESS" in text:
            color = colors.get('text_primary', '#c9a875')
        elif "SUCCESS" in text:
            color = colors.get('accent_positive', '#5a9068')
        else: # Failure
            color = colors.get('accent_negative', '#D94A38')
            
        self.success_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {color};
        """)
    
    def show_check_result(self, result: SkillCheckResult, context: str = "", duration_ms: int = 3000) -> None:
        """
        Display a skill check result with animation.
        
        Args:
            result: The SkillCheckResult object containing the check details
            context: Optional context description for the check
            duration_ms: How long to display the result (in milliseconds)
        """
        colors = self.palette['colors']
        
        # Update the labels with the check information
        self.title_label.setText(f"Skill Check: {result.stat_type}")
        self.stat_label.setText(f"Stat: {result.stat_type} ({int(result.stat_value)})")
        self.difficulty_label.setText(f"Difficulty: {result.difficulty}")
        self.mod_label.setText(f"Modifier: {'+' if result.modifier >= 0 else ''}{result.modifier}")
        self.total_label.setText(f"Total: {result.roll + result.modifier}")
        
        # Update XP Label
        if hasattr(result, 'xp_gained') and result.xp_gained > 0:
            xp_text = f"+{result.xp_gained:.1f} XP"
            if hasattr(result, 'leveled_up') and result.leveled_up:
                xp_text += " [LEVEL UP!]"
                self.xp_label.setStyleSheet(f"""
                    font-size: 14px;
                    font-weight: bold;
                    color: {colors.get('accent_positive', '#5a9068')};
                    background-color: rgba(255, 215, 0, 0.1);
                    border-radius: 4px;
                """)
            else:
                self.xp_label.setStyleSheet(f"""
                    font-size: 12px;
                    font-weight: bold;
                    color: {colors.get('text_highlight', '#FFD700')};
                """)
            self.xp_label.setText(xp_text)
            self.xp_label.setVisible(True)
        else:
            self.xp_label.setVisible(False)
        
        # Set success/failure display
        if result.success:
            if result.roll == 20:
                self.success_label.setText("CRITICAL SUCCESS!")
                self.success_label.setStyleSheet(f"""
                    font-size: 16px;
                    font-weight: bold;
                    color: {colors.get('text_primary', '#c9a875')};
                """)
            else:
                self.success_label.setText("SUCCESS")
                self.success_label.setStyleSheet(f"""
                    font-size: 16px;
                    font-weight: bold;
                    color: {colors.get('accent_positive', '#5a9068')};
                """)
        else:
            if result.roll == 1:
                self.success_label.setText("CRITICAL FAILURE!")
            else:
                self.success_label.setText("FAILURE")
            self.success_label.setStyleSheet(f"""
                font-size: 16px;
                font-weight: bold;
                color: {colors.get('accent_negative', '#D94A38')};
            """)
        
        # Set the context text
        self.context_label.setText(context)
        
        # Make the widget visible
        self.setVisible(True)
        
        # Create fade-in animation
        self.fade_in_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.fade_in_effect)
        self.fade_in_effect.setOpacity(0)
        
        self.fade_in = QPropertyAnimation(self.fade_in_effect, b"opacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.start()
        
        # Start the dice roll animation
        self.dice_widget.roll_animation(result.roll, 800)
        
        # Create a timer to hide the widget after duration_ms
        QTimer.singleShot(duration_ms, self._fade_out)

# For testing purposes
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from core.stats.stats_base import StatType
    
    # Create a test application
    app = QApplication(sys.argv)
    
    # Create a mock skill check result
    test_result = SkillCheckResult(
        stat_type=StatType.STRENGTH,
        stat_value=15,
        difficulty=12,
        roll=18,
        modifier=3,
        success=True,
        advantage=False,
        disadvantage=False
    )
    
    # Create and show the widget
    widget = SkillCheckDisplay()
    widget.show_check_result(test_result, "Attempting to lift the heavy boulder")
    widget.show()
    
    # Run the application
    sys.exit(app.exec())
