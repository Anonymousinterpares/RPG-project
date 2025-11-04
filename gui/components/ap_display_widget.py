import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QSize, QPointF, QRectF
from PySide6.QtGui import (QPainter, QPolygonF, QColor, QPen, QBrush, 
                           QLinearGradient, QRadialGradient, QPainterPath)

logger = logging.getLogger(__name__)

# --- STYLING COLORS ---
COLORS = {
    'background_dark': '#1a1410',
    'background_light': '#3a302a',
    'border_dark': '#4a3a30',
    'text_primary': '#c9a875',
    'ap_pip_active_light': '#4a7c59',
    'ap_pip_active_dark': '#2d5a3a',
    'ap_pip_border_active': '#5a9068',
    'ap_pip_glow_active': 'rgba(90, 144, 104, 30)',
    'overflow_text': '#5a9068',
}
# --- END STYLING COLORS ---


class APDisplayWidget(QWidget):
    """
    A widget to visually display Action Points (AP) using a hybrid pip system
    with overflow text for values greater than 5.
    Enhanced with gradients and visual effects to match fantasy game aesthetic.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_ap = 0
        self.max_ap = 0
        self.pip_count = 5  # Max individual pips to show
        self.pip_size = 20  # Increased size for better visual impact
        self.pip_spacing = 6  # Spacing between pips
        self.overflow_threshold = self.pip_count + 1  # When to switch to overflow text
        
        self.setMinimumHeight(self.pip_size + 10)  # A bit of padding
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(self.pip_spacing)
        self.main_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.ap_label = QLabel("Action Points")
        self.ap_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-weight: 600;
            font-size: 13px;
        """)
        self.main_layout.addWidget(self.ap_label)

        # This widget will handle drawing the pips and overflow text
        self.pip_drawing_widget = _APDrawingWidget(
            self.pip_count, 
            self.pip_size, 
            self.pip_spacing, 
            self.overflow_threshold, 
            self
        )
        self.main_layout.addWidget(self.pip_drawing_widget)

        self.overflow_label = QLabel("")
        self.overflow_label.setStyleSheet(f"""
            color: {COLORS['overflow_text']};
            font-weight: bold;
            font-size: 14px;
        """)
        self.main_layout.addWidget(self.overflow_label)

        self.main_layout.addStretch(1)  # Push everything to the left

    def update_ap(self, current_ap: float, max_ap: float):
        """
        Update the displayed AP values.
        """
        logger.info(f"[APDisplay] update_ap called with current_ap: {current_ap}, max_ap: {max_ap}")
        self.current_ap = current_ap
        self.max_ap = max_ap
        self.pip_drawing_widget.update_ap(current_ap, max_ap)
        self._update_overflow_text()

    def _update_overflow_text(self):
        if self.current_ap > self.pip_count:
            overflow_val = int(self.current_ap - self.pip_count)
            self.overflow_label.setText(f"+{overflow_val}/{int(self.max_ap - self.pip_count)}")
            self.overflow_label.show()
        else:
            self.overflow_label.hide()
class _APDrawingWidget(QWidget):
    """Internal widget to draw the hexagonal AP pips with enhanced visual effects."""
    
    def __init__(self, pip_count: int, pip_size: int, pip_spacing: int, 
                 overflow_threshold: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.pip_count = pip_count
        self.pip_size = pip_size  # This is the width of the hexagon
        self.pip_spacing = pip_spacing
        self.overflow_threshold = overflow_threshold
        self.current_ap = 0
        self.max_ap = 0

        # Calculate required size
        hex_height = int(self.pip_size * 0.866)  # height of flat-top hexagon
        total_width = self.pip_count * (self.pip_size + self.pip_spacing) - self.pip_spacing
        self.setFixedSize(QSize(total_width, hex_height + 4))  # Extra padding for shadow

    def update_ap(self, current_ap: float, max_ap: float):
        self.current_ap = current_ap
        self.max_ap = max_ap
        self.update()  # Trigger repaint

    def _create_hexagon_path(self, x_center: float, y_center: float, radius: float) -> QPainterPath:
        """Create a hexagon path for the pip."""
        path = QPainterPath()
        points = [
            QPointF(x_center + radius, y_center),
            QPointF(x_center + radius / 2, y_center - radius * 0.866),
            QPointF(x_center - radius / 2, y_center - radius * 0.866),
            QPointF(x_center - radius, y_center),
            QPointF(x_center - radius / 2, y_center + radius * 0.866),
            QPointF(x_center + radius / 2, y_center + radius * 0.866),
        ]
        path.moveTo(points[0])
        for point in points[1:]:
            path.lineTo(point)
        path.closeSubpath()
        return path

    def _create_gradient(self, x_center: float, y_center: float, radius: float, 
                        is_active: bool) -> QLinearGradient:
        """Create gradient for pip fill."""
        gradient = QLinearGradient(
            x_center - radius * 0.7, 
            y_center - radius * 0.7,
            x_center + radius * 0.7, 
            y_center + radius * 0.7
        )
        
        if is_active:
            # Active gradient: green tones matching game's stamina bar
            gradient.setColorAt(0, QColor(COLORS['ap_pip_active_light']))
            gradient.setColorAt(1, QColor(COLORS['ap_pip_active_dark']))
        else:
            # Inactive gradient: dark brown/gray
            gradient.setColorAt(0, QColor(COLORS['background_light']))
            gradient.setColorAt(1, QColor(COLORS['background_dark']))
        
        return gradient

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        radius = self.pip_size / 2
        y_center = self.height() / 2

        for i in range(self.pip_count):
            # Determine if this pip should be filled
            if self.current_ap > self.pip_count:
                is_active = True  # All pips active when overflow
            elif i < self.current_ap:
                is_active = True
            else:
                is_active = False

            x_center = i * (self.pip_size + self.pip_spacing) + radius

            # Create hexagon path
            hex_path = self._create_hexagon_path(x_center, y_center, radius)

            # Draw shadow/depth effect (slightly offset darker hexagon)
            shadow_path = self._create_hexagon_path(x_center + 0.5, y_center + 1, radius)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 60))  # Semi-transparent black
            painter.drawPath(shadow_path)

            # Draw main pip with gradient
            gradient = self._create_gradient(x_center, y_center, radius, is_active)
            painter.setBrush(QBrush(gradient))
            
            # Border color
            if is_active:
                border_color = QColor(COLORS['ap_pip_border_active'])
                border_width = 2
            else:
                border_color = QColor(COLORS['border_dark'])
                border_width = 1
            
            painter.setPen(QPen(border_color, border_width))
            painter.drawPath(hex_path)

            # Add inner highlight for active pips (for depth/gloss effect)
            if is_active:
                highlight_path = self._create_hexagon_path(
                    x_center, 
                    y_center - 1, 
                    radius * 0.6
                )
                highlight_gradient = QLinearGradient(
                    x_center, y_center - radius,
                    x_center, y_center
                )
                highlight_gradient.setColorAt(0, QColor(255, 255, 255, 40))
                highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(highlight_gradient))
                painter.drawPath(highlight_path)

            # Optional: Add subtle glow for active pips
            if is_active:
                glow_radius = radius + 1
                glow_path = self._create_hexagon_path(x_center, y_center, glow_radius)
                painter.setPen(QPen(QColor(COLORS['ap_pip_glow_active']), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(glow_path)

        painter.end()