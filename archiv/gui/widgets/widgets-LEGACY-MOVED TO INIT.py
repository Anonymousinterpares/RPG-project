#gui/widgets.py
from queue import Queue
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QMetaObject
# --- Helper Classes ---

class CustomButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        # Default style (if no images provided)
        self.default_style = """
            CustomButton {
                background-color: rgba(200,200,200,0.8);
                border: none;
                padding: 5px;
            }
            CustomButton:hover {
                background-color: rgba(150,150,150,0.8);
            }
            CustomButton:pressed {
                background-color: rgba(100,100,100,0.8);
            }
        """
        self.setStyleSheet(self.default_style)
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(100)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.original_geometry = None

    def enterEvent(self, event):
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
        rect = self.geometry()
        new_rect = QRect(rect.x()-2, rect.y()-2, rect.width()+4, rect.height()+4)
        self.anim.stop()
        self.anim.setStartValue(rect)
        self.anim.setEndValue(new_rect)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.original_geometry is not None:
            rect = self.geometry()
            self.anim.stop()
            self.anim.setStartValue(rect)
            self.anim.setEndValue(self.original_geometry)
            self.anim.start()
        super().leaveEvent(event)

    def update_theme(self, theme_dict):
        """
        Update the button's style according to theme_dict.
        If custom image keys are provided (btn_bg_image, btn_hover_image, btn_pressed_image),
        load the normal image, apply its mask, and set a stylesheet using these images.
        Otherwise, fallback to using color values with a rounded border.
        """
        from PySide6.QtGui import QPixmap
        if all(key in theme_dict for key in ("btn_bg_image", "btn_hover_image", "btn_pressed_image")):
            normal_pixmap = QPixmap(theme_dict["btn_bg_image"])
            if not normal_pixmap.isNull():
                # Apply a mask so that the clickable area follows the irregular shape.
                self.setMask(normal_pixmap.mask())
            style = f"""
                CustomButton {{
                    background-image: url("{theme_dict['btn_bg_image']}");
                    background-repeat: no-repeat;
                    background-position: center;
                    border: none;
                    padding: 5px;
                }}
                CustomButton:hover {{
                    background-image: url("{theme_dict['btn_hover_image']}");
                }}
                CustomButton:pressed {{
                    background-image: url("{theme_dict['btn_pressed_image']}");
                }}
            """
        else:
            style = f"""
                CustomButton {{
                    background-color: {theme_dict.get('btn_bg', 'rgba(200,200,200,0.8)')};
                    border: none;
                    border-radius: 10px;
                    padding: 5px;
                }}
                CustomButton:hover {{
                    background-color: {theme_dict.get('btn_hover', 'rgba(150,150,150,0.8)')};
                }}
                CustomButton:pressed {{
                    background-color: {theme_dict.get('btn_pressed', 'rgba(100,100,100,0.8)')};
                }}
            """
            self.clearMask()
        self.setStyleSheet(style)


# A helper class that redirects writes to an output queue.
class QueueStream:
    def __init__(self, output_queue: Queue, gui):
        self.output_queue = output_queue
        self.gui = gui  # reference to the GameGUI instance

    def write(self, text: str):
        if text.strip():
            self.output_queue.put(text)
            QMetaObject.invokeMethod(self.gui, "update_output_from_queue", Qt.QueuedConnection)

    def flush(self):
        pass