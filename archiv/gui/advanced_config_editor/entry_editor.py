# gui/advanced_config_editor/entry_editor.py
"""
Dialog for editing individual configuration entries.
"""
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QLabel, 
)
from .custom_widgets import AutoResizingPlainTextEdit

class EntryEditorDialog(QDialog):
    """
    Dialog for editing individual configuration entries.
    """
    def __init__(self, entry_type, entry_data=None, parent=None):
        super().__init__(parent)
        self.entry_type = entry_type
        self.entry_data = entry_data if entry_data is not None else {}
        self.setWindowTitle(f"Edit {self.entry_type}")
        self.resize(800, 300)
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)
        self.widgets = {}

        if self.entry_type == "Race":
            fields = [
                ("name", "Race Name", "line"),
                ("description", "Description", "plain")
            ]
        elif self.entry_type == "Path":
            fields = [
                ("name", "Path Name", "line"),
                ("description", "Description", "plain"),
                ("backgrounds_file", "Backgrounds File (e.g. academic.json)", "line"),
                ("starting_advantages", "Starting Advantages (comma separated)", "plain"),
                ("common_challenges", "Common Challenges (comma separated)", "plain")
            ]
        elif self.entry_type == "Background":
            fields = [
                ("name", "Background Name", "line"),
                ("description", "Description", "plain"),
                ("origin", "Origin", "line"),
                ("skills", "Skills (JSON format)", "plain"),
                ("starting_resources", "Starting Resources (JSON format)", "plain"),
                ("starting_locations", "Starting Locations (JSON format)", "plain"),
                ("motivation", "Motivation", "plain"),
                ("challenge", "Challenge", "plain"),
                ("narrative_elements", "Narrative Elements (JSON format)", "plain")
            ]
        else:
            fields = []

        for key, label, wtype in fields:
            if wtype == "line":
                widget = QLineEdit()
                widget.setPlaceholderText(f"Enter {label}")
                if key in self.entry_data:
                    widget.setText(str(self.entry_data.get(key)))
            else:
                widget = AutoResizingPlainTextEdit(min_lines=2, max_lines=10)
                widget.setPlaceholderText(f"Enter {label}")
                if key in self.entry_data:
                    try:
                        widget.setPlainText(json.dumps(self.entry_data.get(key), indent=2))
                    except Exception:
                        widget.setPlainText(str(self.entry_data.get(key)))
            self.widgets[key] = widget
            self.form_layout.addRow(label + ":", widget)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        self.layout.addLayout(btn_layout)

        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def get_entry_data(self):
            """
            Get the data from the dialog widgets.
            
            Returns:
                dict: The entry data
            """
            data = {}
            for key, widget in self.widgets.items():
                if isinstance(widget, QLineEdit):
                    text = widget.text().strip()
                elif isinstance(widget, AutoResizingPlainTextEdit):
                    text = widget.toPlainText().strip()
                else:
                    text = ""
                # For JSON fields, if parsing fails, store as string wrapped in quotes.
                if self.entry_type == "Background" and key in ["skills", "starting_resources", "starting_locations", "narrative_elements"]:
                    try:
                        data[key] = json.loads(text)
                    except Exception:
                        # Auto-convert: if not valid JSON, store as string.
                        data[key] = text
                else:
                    data[key] = text
            data["version"] = self.entry_data.get("version", 1)
            data["last_modified"] = datetime.now().isoformat()
            return data