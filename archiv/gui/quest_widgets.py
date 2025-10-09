# gui/quest_widgets.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QDialog, QTextEdit, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from datetime import datetime

class QuestListWidget(QWidget):
    questClicked = Signal(str)  # Signal emitted when a quest is clicked, with quest_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setStyleSheet("background-color: #d9caaa;")

        # Active quests section
        self.active_label = QLabel("Active Quests:", self)
        self.active_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.layout.addWidget(self.active_label)

        self.active_list = QWidget(self)
        self.active_layout = QVBoxLayout(self.active_list)
        self.active_layout.setContentsMargins(0, 0, 0, 0)
        
        self.active_layout.setSpacing(2)
        self.layout.addWidget(self.active_list)
        
        # Add a separator
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(separator)
        
        # Completed quests section
        self.completed_label = QLabel("Completed/Closed Quests:", self)
        self.completed_label.setStyleSheet("font-weight: bold; color: #7f8c8d;")
        self.layout.addWidget(self.completed_label)
        
        self.completed_list = QWidget(self)
        self.completed_layout = QVBoxLayout(self.completed_list)
        self.completed_layout.setContentsMargins(0, 0, 0, 0)
        self.completed_layout.setSpacing(2)
        self.layout.addWidget(self.completed_list)
        
        # Always add stretch at the end to push everything to the top
        self.layout.addStretch()
        
    def update_quests(self, active_quests, completed_quests):
        """Update the quest list with the given quests"""
        # Clear current quests
        self._clear_layout(self.active_layout)
        self._clear_layout(self.completed_layout)
        
        # Add active quests
        if not active_quests:
            label = QLabel("No active quests.", self.active_list)
            label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.active_layout.addWidget(label)
        else:
            for quest in active_quests:
                self._add_quest_widget(quest, self.active_layout)
                
        # Add completed quests
        if not completed_quests:
            label = QLabel("No completed quests.", self.completed_list)
            label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.completed_layout.addWidget(label)
        else:
            for quest in completed_quests:
                self._add_quest_widget(quest, self.completed_layout, True)
                
    def _clear_layout(self, layout):
        """Clear all widgets from the layout"""
        if layout is None:
            return
            
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
    def _add_quest_widget(self, quest, layout, completed=False):
        """Add a quest widget to the layout"""
        # Create hover effect widget
        quest_widget = QFrame(self)
        quest_widget.setFrameShape(QFrame.StyledPanel)
        quest_widget.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 120);
                border-radius: 4px;
                padding: 5px;
                margin: 2px;
            }
            QFrame:hover {
                background-color: rgba(230, 240, 250, 180);
                border: 1px solid #3498db;
            }
        """)
        
        # Create layout for the quest item
        quest_layout = QHBoxLayout(quest_widget)
        quest_layout.setContentsMargins(5, 5, 5, 5)
        quest_layout.setSpacing(5)
        
        # Create status indicator
        status_indicator = QLabel(quest_widget)
        status_indicator.setFixedSize(16, 16)
        
        # Set indicator color based on status
        if completed:
            # Use different colors for completed/failed/refused
            if quest.get("status") == "completed":
                status_indicator.setStyleSheet("background-color: #2ecc71; border-radius: 8px;")
            elif quest.get("status") == "failed":
                status_indicator.setStyleSheet("background-color: #e74c3c; border-radius: 8px;")
            else:  # refused
                status_indicator.setStyleSheet("background-color: #7f8c8d; border-radius: 8px;")
        else:
            status_indicator.setStyleSheet("background-color: #3498db; border-radius: 8px;")
            
        quest_layout.addWidget(status_indicator)
        
        # Create quest name label
        quest_name = QLabel(quest.get("name", "Unnamed Quest"), quest_widget)
        if completed:
            # Use strikethrough for completed quests
            quest_name.setStyleSheet("color: #7f8c8d; text-decoration: line-through;")
        else:
            quest_name.setStyleSheet("color: #2c3e50; font-weight: bold;")
        quest_layout.addWidget(quest_name, 1)  # 1 = stretch factor
        
        # Make the whole widget clickable
        quest_widget.mousePressEvent = lambda e, qid=quest.get("id", ""): self.questClicked.emit(qid)
        
        # Add the quest widget to the layout
        layout.addWidget(quest_widget)


class QuestDetailDialog(QDialog):
    def __init__(self, quest, parent=None):
        super().__init__(parent)
        self.quest = quest
        
        self.setWindowTitle(f"Quest Details: {quest.get('name', 'Unnamed Quest')}")
        self.resize(500, 400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Quest name header
        header = QLabel(quest.get("name", "Unnamed Quest"), self)
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)
        
        # Status indicator
        status_text = quest.get("status", "active").capitalize()
        status_label = QLabel(f"Status: {status_text}", self)
        if quest.get("status") == "active":
            status_label.setStyleSheet("color: #3498db; font-weight: bold;")
        elif quest.get("status") == "completed":
            status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        elif quest.get("status") == "failed":
            status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:  # refused
            status_label.setStyleSheet("color: #7f8c8d; font-weight: bold;")
        layout.addWidget(status_label)
        
        # Time information
        try:
            start_time = datetime.fromisoformat(quest.get("start_time", "")) if quest.get("start_time") else None
            if start_time:
                start_label = QLabel(f"Started: {start_time.strftime('%Y-%m-%d %H:%M')}", self)
                layout.addWidget(start_label)
        except ValueError:
            pass
            
        if quest.get("status", "active") != "active":
            try:
                end_time = datetime.fromisoformat(quest.get("end_time", "")) if quest.get("end_time") else None
                if end_time:
                    end_label = QLabel(f"Ended: {end_time.strftime('%Y-%m-%d %H:%M')}", self)
                    layout.addWidget(end_label)
            except ValueError:
                pass
                
        # Separator
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Quest description
        description_label = QLabel("Description:", self)
        description_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(description_label)
        
        description = QTextEdit(self)
        description.setReadOnly(True)
        description.setPlainText(quest.get("description", "No description available."))
        description.setStyleSheet("background-color: rgba(255, 255, 255, 180); border: 1px solid #bdc3c7;")
        description.setMaximumHeight(100)
        layout.addWidget(description)
        
        # Quest steps header
        steps_label = QLabel("Progress:", self)
        steps_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(steps_label)
        
        # Quest steps scroll area
        steps_scroll = QScrollArea(self)
        steps_scroll.setWidgetResizable(True)
        steps_scroll.setStyleSheet("background-color: transparent; border: none;")
        steps_widget = QWidget()
        steps_layout = QVBoxLayout(steps_widget)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        steps_layout.setSpacing(5)
        
        if not quest.get("steps", []):
            no_steps = QLabel("No progress steps recorded.", steps_widget)
            no_steps.setStyleSheet("color: #7f8c8d; font-style: italic;")
            steps_layout.addWidget(no_steps)
        else:
            for step in quest.get("steps", []):
                step_text = step.get("description", "")
                step_widget = QLabel(step_text, steps_widget)
                
                if step.get("completed", False):
                    # Strikethrough for completed steps
                    step_widget.setStyleSheet("text-decoration: line-through; color: #7f8c8d;")
                else:
                    step_widget.setStyleSheet("color: #2c3e50;")
                
                steps_layout.addWidget(step_widget)
                
                # Add timestamp if available
                if step.get("timestamp", ""):
                    try:
                        timestamp = datetime.fromisoformat(step.get("timestamp", ""))
                        time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                        time_widget = QLabel(f"   [{time_str}]", steps_widget)
                        time_widget.setStyleSheet("color: #7f8c8d; font-size: small;")
                        steps_layout.addWidget(time_widget)
                    except ValueError:
                        pass
                        
        steps_layout.addStretch()
        steps_scroll.setWidget(steps_widget)
        layout.addWidget(steps_scroll, 1)  # 1 = stretch factor
        
        # Close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)