# gui/inventory/utils.py
from PySide6.QtGui import QPixmap
import os

def load_image_with_fallback(file_path, default_text="?", size=(50, 50)):
    """Load an image with fallback to a colored placeholder"""
    try:
        if file_path and os.path.exists(file_path):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                return pixmap
        return None
    except Exception as e:
        print(f"Error loading image {file_path}: {e}")
        return None