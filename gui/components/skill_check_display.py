#!/usr/bin/env python3
"""
Skill check display widget for the RPG game GUI.
This module provides a widget for displaying skill check results in a visual way.
"""

import logging
from typing import Optional, Dict, Any, List, Union
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QProgressBar, QGroupBox, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, Slot, QPropertyAnimation, QTimer, QSize, Property
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush

from core.stats.skill_check import SkillCheckResult


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
        
        # Define the dice colors based on the value
        if self._value == 20:
            # Critical success - gold
            bg_color = QColor(255, 215, 0)
            text_color = QColor(0, 0, 0)
        elif self._value == 1:
            # Critical failure - red
            bg_color = QColor(200, 0, 0)
            text_color = QColor(255, 255, 255)
        else:
            # Normal roll - white
            bg_color = QColor(240, 240, 240)
            text_color = QColor(0, 0, 0)
        
        # Draw the dice (d20 is icosahedron, but we'll draw a simplified pentagon)
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        # Draw the background
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(QColor(20, 20, 20), 2))
        
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
        
        # Set up the UI
        self._setup_ui()
        
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
        self.title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #E0E0E0;
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # Create the stat and difficulty display
        self.stat_layout = QHBoxLayout()
        
        self.stat_label = QLabel("Stat: STR")
        self.stat_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #BBBBBB;
        """)
        
        self.difficulty_label = QLabel("Difficulty: 15")
        self.difficulty_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #BBBBBB;
        """)
        
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
        self.mod_label.setStyleSheet("""
            font-size: 14px;
            color: #BBBBBB;
        """)
        
        self.total_label = QLabel("Total: 10")
        self.total_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #E0E0E0;
        """)
        
        self.success_label = QLabel("SUCCESS")
        self.success_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #66CC33;
        """)
        self.success_label.setAlignment(Qt.AlignCenter)
        
        self.result_layout.addWidget(self.mod_label)
        self.result_layout.addStretch(1)
        self.result_layout.addWidget(self.total_label)
        
        # Create the context display
        self.context_label = QLabel("Attempting to climb the steep cliff")
        self.context_label.setStyleSheet("""
            font-size: 14px;
            font-style: italic;
            color: #CCCCCC;
        """)
        self.context_label.setAlignment(Qt.AlignCenter)
        self.context_label.setWordWrap(True)
        
        # Add all elements to the main layout
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addLayout(self.stat_layout)
        self.main_layout.addLayout(self.dice_layout)
        self.main_layout.addLayout(self.result_layout)
        self.main_layout.addWidget(self.success_label)
        self.main_layout.addWidget(self.context_label)
        
        # Set the widget styling
        self.setStyleSheet("""
            background-color: #333333;
            border: 2px solid #555555;
            border-radius: 8px;
        """)
        
        # Set a fixed size for the widget
        self.setFixedSize(300, 250)
    
    def show_check_result(self, result: SkillCheckResult, context: str = "", duration_ms: int = 3000) -> None:
        """
        Display a skill check result with animation.
        
        Args:
            result: The SkillCheckResult object containing the check details
            context: Optional context description for the check
            duration_ms: How long to display the result (in milliseconds)
        """
        # Update the labels with the check information
        self.title_label.setText(f"Skill Check: {result.stat_type}")
        self.stat_label.setText(f"Stat: {result.stat_type} ({int(result.stat_value)})")
        self.difficulty_label.setText(f"Difficulty: {result.difficulty}")
        self.mod_label.setText(f"Modifier: {'+' if result.modifier >= 0 else ''}{result.modifier}")
        self.total_label.setText(f"Total: {result.roll + result.modifier}")
        
        # Set success/failure display
        if result.success:
            if result.roll == 20:
                self.success_label.setText("CRITICAL SUCCESS!")
                self.success_label.setStyleSheet("""
                    font-size: 16px;
                    font-weight: bold;
                    color: #FFD700;  /* Gold */
                """)
            else:
                self.success_label.setText("SUCCESS")
                self.success_label.setStyleSheet("""
                    font-size: 16px;
                    font-weight: bold;
                    color: #66CC33;  /* Green */
                """)
        else:
            if result.roll == 1:
                self.success_label.setText("CRITICAL FAILURE!")
                self.success_label.setStyleSheet("""
                    font-size: 16px;
                    font-weight: bold;
                    color: #CC3333;  /* Red */
                """)
            else:
                self.success_label.setText("FAILURE")
                self.success_label.setStyleSheet("""
                    font-size: 16px;
                    font-weight: bold;
                    color: #CC3333;  /* Red */
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
    
    def _fade_out(self) -> None:
        """Create and start a fade-out animation."""
        self.fade_out = QPropertyAnimation(self.fade_in_effect, b"opacity")
        self.fade_out.setDuration(500)
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.start()
        
        # Hide the widget after the animation finishes
        self.fade_out.finished.connect(self._hide_widget)
    
    def _hide_widget(self) -> None:
        """Hide the widget and emit the finished signal."""
        self.setVisible(False)
        self.display_finished.emit()


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
