# gui/safe_zone_widget.py

from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPen
from PySide6.QtCore import Qt, QRect, QPoint, QRectF, QSize

class SafeZoneWidget(QFrame):
    def __init__(self, margin=105, parent=None):
        super().__init__(parent)
        self.margin = margin
        self.fade_distance = 40  # Pixels over which the fade occurs
        self.show_guides = False  # Set to True to show guide lines
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(margin, margin, margin, margin)
        self.layout.setSpacing(0)
        
        # Make widget transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # Create gradient masks for fading edges
        self._setup_gradients()

        # Set minimum size
        self.setMinimumSize(margin * 2 + 100, margin * 2 + 100)  # Ensure minimum content area

    def _setup_gradients(self):
        """Initialize gradient masks for fading edges"""
        self.top_gradient = QLinearGradient(0, self.margin - self.fade_distance, 
                                          0, self.margin)
        self.top_gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
        self.top_gradient.setColorAt(1.0, QColor(255, 255, 255, 255))

        self.bottom_gradient = QLinearGradient(0, self.height() - self.margin,
                                             0, self.height() - self.margin + self.fade_distance)
        self.bottom_gradient.setColorAt(0.0, QColor(255, 255, 255, 255))
        self.bottom_gradient.setColorAt(1.0, QColor(255, 255, 255, 0))

        self.left_gradient = QLinearGradient(self.margin - self.fade_distance, 0,
                                           self.margin, 0)
        self.left_gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
        self.left_gradient.setColorAt(1.0, QColor(255, 255, 255, 255))

        self.right_gradient = QLinearGradient(self.width() - self.margin, 0,
                                            self.width() - self.margin + self.fade_distance, 0)
        self.right_gradient.setColorAt(0.0, QColor(255, 255, 255, 255))
        self.right_gradient.setColorAt(1.0, QColor(255, 255, 255, 0))

    def resizeEvent(self, event):
        """Handle widget resizing"""
        super().resizeEvent(event)
        self._setup_gradients()

    def paintEvent(self, event):
        """Custom paint event to handle fading edges and guide lines"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get safe zone rectangle
        safe_rect = self.rect().adjusted(self.margin, self.margin, 
                                       -self.margin, -self.margin)

        # Draw guide lines if enabled (for development)
        if self.show_guides:
            painter.setPen(QPen(Qt.red, 1, Qt.DashLine))
            painter.drawRect(safe_rect)

        # Apply fade effects using gradients
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        # Top fade
        painter.fillRect(QRect(safe_rect.left(), safe_rect.top() - self.fade_distance,
                             safe_rect.width(), self.fade_distance),
                        self.top_gradient)
        
        # Bottom fade
        painter.fillRect(QRect(safe_rect.left(), safe_rect.bottom(),
                             safe_rect.width(), self.fade_distance),
                        self.bottom_gradient)
        
        # Left fade
        painter.fillRect(QRect(safe_rect.left() - self.fade_distance, safe_rect.top(),
                             self.fade_distance, safe_rect.height()),
                        self.left_gradient)
        
        # Right fade
        painter.fillRect(QRect(safe_rect.right(), safe_rect.top(),
                             self.fade_distance, safe_rect.height()),
                        self.right_gradient)

    def set_content_widget(self, widget):
        """Set the widget to be displayed in the safe zone"""
        if widget:
            self.layout.addWidget(widget)

    def sizeHint(self):
        """Provide a reasonable default size"""
        return QSize(800, 600)  # Adjust these values based on your needs