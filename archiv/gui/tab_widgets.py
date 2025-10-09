# gui/tab_widgets.py
from PySide6.QtWidgets import (QTabWidget, QFrame, QVBoxLayout, 
                             QWidget, QLabel, QScrollArea)
from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QColor

class OverlayContentFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("overlayContent")
        self.setStyleSheet("""
            #overlayContent {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.setVisible(False)
        
        # Ensure overlay is always on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create scroll area for content
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.layout.addWidget(self.scroll)
        
        # Container for actual content
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.scroll.setWidget(self.content_widget)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()  # Ensure we're on top when shown
        
    def setContent(self, widget):
        # Clear existing content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Add new content
        self.content_layout.addWidget(widget)
        widget.setParent(self.content_widget)

class OverlayTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("overlayTabWidget")
        
        self._active_tab = -1
        self._overlay_frames = {}
        self._content_widgets = {}
        
        self.setTabBarAutoHide(False)
        self.tabBar().setExpanding(False)
        self.setDocumentMode(True)
        
        # Install event filter on tab bar to catch mouse clicks
        self.tabBar().installEventFilter(self)
        
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                padding: 5px 10px;
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid #ccc;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
            }
        """)

    def eventFilter(self, obj, event):
        """Handle tab bar clicks"""
        if obj == self.tabBar() and event.type() == QEvent.MouseButtonPress:
            index = self.tabBar().tabAt(event.pos())
            if index >= 0:
                self._handleTabClick(index)
            return True
        return super().eventFilter(obj, event)

    def _handleTabClick(self, index):
        """Handle tab clicks with overlay toggle"""
        if index == self._active_tab:
            # Clicking active tab - hide it
            if self._active_tab in self._overlay_frames:
                self._overlay_frames[self._active_tab].hide()
            self._active_tab = -1
        else:
            self._handleTabChange(index)

    def addTab(self, widget, label):
        """Override addTab to create overlay frame for content"""
        self._content_widgets[label] = widget
        
        # Create empty placeholder for tab
        placeholder = QWidget()
        placeholder.setStyleSheet("background: transparent;")
        index = super().addTab(placeholder, label)
        
        # Create overlay frame
        overlay = QFrame(self.window())
        overlay.setObjectName("overlayContent")
        overlay.setStyleSheet("""
            #overlayContent {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(widget)
        overlay.hide()
        
        self._overlay_frames[index] = overlay
        return index

    def _handleTabChange(self, index):
            if index == self._active_tab:
                # Clicking active tab - hide it
                if self._active_tab in self._overlay_frames:
                    self._overlay_frames[self._active_tab].hide()
                self._active_tab = -1
                return  # Exit after hiding
                
            # Hide previous tab if any
            if self._active_tab in self._overlay_frames:
                self._overlay_frames[self._active_tab].hide()
            
            # Show new tab
            if index in self._overlay_frames:
                overlay = self._overlay_frames[index]
                
                # Get right panel geometry
                right_panel = self.parent()
                right_panel_pos = right_panel.mapToGlobal(right_panel.rect().topLeft())
                
                # Calculate position - align with right panel edge
                overlay_width = right_panel.width() * 2  # 2x panel width
                x_pos = right_panel_pos.x() - overlay_width + right_panel.width()  # Extend left from right edge
                y_pos = right_panel_pos.y() + self.tabBar().height()  # Below tabs
                
                # Convert to window coordinates
                main_window = self.window()
                local_pos = main_window.mapFromGlobal(QPoint(x_pos, y_pos))
                
                # Update overlay
                overlay.setParent(main_window)  # Parent to main window for proper layering
                overlay.setGeometry(
                    local_pos.x(),
                    local_pos.y(),
                    overlay_width,
                    right_panel.height() - self.tabBar().height() - 10  # Full height minus tabs and margin
                )
                
                # Show and bring to front
                overlay.show()
                overlay.raise_()
            
            self._active_tab = index

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._active_tab in self._overlay_frames:
            overlay = self._overlay_frames[self._active_tab]
            if overlay.isVisible():
                # Recalculate position and size using same logic as _handleTabChange
                tab_rect = self.tabBar().tabRect(self._active_tab)
                tab_pos = self.tabBar().mapToGlobal(tab_rect.topLeft())
                right_panel = self.parent()
                right_panel_pos = right_panel.mapToGlobal(right_panel.rect().topLeft())
                
                y_pos = tab_pos.y() + self.tabBar().height()
                overlay_width = 300
                x_pos = right_panel_pos.x() - overlay_width + right_panel.width()
                
                local_pos = right_panel.mapFromGlobal(QPoint(x_pos, y_pos))
                height = right_panel.height() - local_pos.y() - 10
                
                overlay.setGeometry(
                    local_pos.x(),
                    local_pos.y(),
                    overlay_width,
                    height
                )