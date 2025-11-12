import sys
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property

class LoadingProgressBar(QWidget):
    """A custom widget that displays a looping progress bar animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__offset = 0.0
        self.setMinimumHeight(20)
        self.animation = QPropertyAnimation(self, b"_offset", self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(1500)
        self.animation.setLoopCount(-1)  # Loop indefinitely
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

    def _get_offset(self):
        return self.__offset

    def _set_offset(self, value):
        self.__offset = value
        self.update()

    _offset = Property(float, _get_offset, _set_offset)

    def start_animation(self):
        self.animation.start()

    def stop_animation(self):
        self.animation.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        width = self.width()
        height = self.height()
        
        # Background
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.drawRect(self.rect())

        num_rects = 5
        rect_width = width / (num_rects * 1.5)
        spacing = rect_width * 0.5

        total_width = (num_rects * (rect_width + spacing))

        for i in range(num_rects):
            # Calculate the base position
            x = (i * (rect_width + spacing))
            
            # Apply the animated offset, wrapping around the total width
            animated_x = (x + self.__offset * total_width * 2) % (width + total_width) - total_width

            painter.setBrush(QColor(200, 200, 220, 180))
            painter.drawRect(int(animated_x), 0, int(rect_width), height)

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication, QMainWindow
    app = QApplication(sys.argv)
    main_win = QMainWindow()
    central_widget = QWidget()
    main_win.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    loading_bar = LoadingProgressBar()
    layout.addWidget(loading_bar)
    loading_bar.start_animation()
    
    main_win.show()
    sys.exit(app.exec())
