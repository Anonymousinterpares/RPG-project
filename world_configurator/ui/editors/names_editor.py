"""
Names editor for config/npc/names.json.
"""
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QDoubleSpinBox,
    QComboBox, QMessageBox, QSpinBox
)
import os
import json
import random
import re
from utils.file_manager import get_config_dir

class NamesEditor(QWidget):
    names_modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {"cultures": {}}
        self._current_culture = None
        self._manager = None
        self._setup_ui()
        # Do not auto-load; main window will call refresh after managers sync

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.culture_combo = QComboBox()
        self.culture_combo.currentIndexChanged.connect(self._on_culture_changed)
        self.add_culture_edit = QLineEdit(); self.add_culture_edit.setPlaceholderText("new culture id")
        self.add_culture_btn = QPushButton("Add Culture")
        self.add_culture_btn.clicked.connect(self._add_culture)
        top.addWidget(QLabel("Culture:")); top.addWidget(self.culture_combo); top.addWidget(self.add_culture_edit); top.addWidget(self.add_culture_btn)
        layout.addLayout(top)

        form = QFormLayout()
        self.patterns_edit = QTextEdit(); self.patterns_edit.setPlaceholderText("One per line. Tokens: FN, FN2, MI, LN, LN2. Examples: 'FN MI LN', 'FN LN-LN2', 'FN FN2 LN'")
        form.addRow("Patterns:", self.patterns_edit)
        self.first_syllables_edit = QTextEdit(); self.first_syllables_edit.setPlaceholderText("Comma-separated syllables")
        form.addRow("First syllables:", self.first_syllables_edit)
        self.last_prefixes_edit = QTextEdit(); self.last_prefixes_edit.setPlaceholderText("Comma-separated prefixes")
        form.addRow("Last prefixes:", self.last_prefixes_edit)
        self.last_cores_edit = QTextEdit(); self.last_cores_edit.setPlaceholderText("Comma-separated cores")
        form.addRow("Last cores:", self.last_cores_edit)
        self.last_suffixes_edit = QTextEdit(); self.last_suffixes_edit.setPlaceholderText("Comma-separated suffixes")
        form.addRow("Last suffixes:", self.last_suffixes_edit)
        self.allowed_chars_edit = QLineEdit(); self.allowed_chars_edit.setPlaceholderText("Regex for allowed characters, e.g., ^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$")
        form.addRow("Allowed chars:", self.allowed_chars_edit)
        layout.addLayout(form)

        btns = QHBoxLayout()
        self.load_btn = QPushButton("Load from Game")
        self.load_btn.clicked.connect(self.load_from_game)
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        btns.addWidget(self.load_btn); btns.addWidget(self.save_btn)
        layout.addLayout(btns)

        # Preview controls
        preview_ctrls = QHBoxLayout()
        preview_ctrls.addWidget(QLabel("Preview count:"))
        self.preview_count = QSpinBox()
        self.preview_count.setRange(1, 100)
        self.preview_count.setValue(10)
        preview_ctrls.addWidget(self.preview_count)
        self.preview_btn = QPushButton("Generate Preview")
        self.preview_btn.clicked.connect(self._on_generate_preview)
        preview_ctrls.addWidget(self.preview_btn)
        preview_ctrls.addStretch()
        layout.addLayout(preview_ctrls)

        self.preview_list = QListWidget()
        self.preview_list.setMinimumHeight(140)
        layout.addWidget(self.preview_list)

    def set_manager(self, names_manager) -> None:
        """Attach a NamesManager to this editor."""
        self._manager = names_manager

    def refresh(self):
        """Refresh UI from the manager if available; otherwise load from game file."""
        try:
            if self._manager and getattr(self._manager, 'data', None):
                # Manager stores full JSON structure
                self._data = json.loads(json.dumps(self._manager.data))  # deep copy
                self._refresh_cultures()
            else:
                self.load_from_game(show_message=False)
        except Exception as e:
            QMessageBox.warning(self, "Names", f"Failed to refresh names: {e}")

    def load_from_game(self, show_message: bool = True):
        path = os.path.join(get_config_dir(), "npc", "names.json")
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                # Prepopulate sensible defaults if missing
                self._data = {
                        "cultures": {
                            "generic": {
                                "patterns": ["FN LN", "FN MI LN", "FN LN-LN2", "FN FN2 LN"],
                                "first_syllables": ["al","an","ar","el","ia","ro","li","ma","tha","dor","gal","vin","mi","ál","éla","íra","óth","úri","åke","æla","öri","ça","ñor"],
                                "last_prefixes": ["", "bel", "wood", "stone", "fair", "silver", "gold"],
                                "last_cores": ["river", "brook", "storm", "light", "helm", "wright", "smith", "walker", "binder", "seeker", "björn", "gård", "ström"],
                                "last_suffixes": ["son", "ton", "ford", "field", "ward", "shire", "mont", "sson", "sen", "dóttir"],
                                "allowed_chars": "^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$"
                            }
                        },
                        "metadata": {
                            "version": "1.0.0",
                            "description": "Culture-aware name generation guidance"
                        }
                    }
            self._refresh_cultures()
            if show_message:
                QMessageBox.information(self, "Loaded", f"Loaded names from {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load names.json: {e}")

    def save_changes(self):
        """Save current UI state into manager or directly to game file if no manager."""
        # Update current culture entry from UI first
        self._save_current_culture()
        try:
            if self._manager is not None:
                # Push into manager and save to its path or keep in-memory; export uses export dialog
                self._manager.data = json.loads(json.dumps(self._data))  # deep copy
                # If manager has a state path (project mode), save to that file
                if getattr(self._manager, 'state', None) and getattr(self._manager.state, 'path', None):
                    self._manager.save_to_file(self._manager.state.path)
            else:
                # Fallback: write directly to game
                path = os.path.join(get_config_dir(), "npc", "names.json")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
            self.names_modified.emit()
            QMessageBox.information(self, "Saved", "Names data saved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save names: {e}")

    def _refresh_cultures(self):
        self.culture_combo.blockSignals(True)
        self.culture_combo.clear()
        for cid in sorted(self._data.get("cultures", {}).keys()):
            self.culture_combo.addItem(cid, cid)
        self.culture_combo.blockSignals(False)
        if self.culture_combo.count() > 0:
            self.culture_combo.setCurrentIndex(0)
            self._on_culture_changed(0)

    def _on_culture_changed(self, idx: int):
        # Save previous culture edits
        self._save_current_culture()
        cid = self.culture_combo.currentData()
        self._current_culture = cid
        spec = self._data.get("cultures", {}).get(cid, {}) if cid else {}
        self.patterns_edit.setPlainText("\n".join(spec.get("patterns", [])))
        self.first_syllables_edit.setPlainText(",".join(spec.get("first_syllables", [])))
        self.last_prefixes_edit.setPlainText(",".join(spec.get("last_prefixes", [])))
        self.last_cores_edit.setPlainText(",".join(spec.get("last_cores", [])))
        self.last_suffixes_edit.setPlainText(",".join(spec.get("last_suffixes", [])))
        self.allowed_chars_edit.setText(spec.get("allowed_chars", "^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$"))

    def _add_culture(self):
        cid = self.add_culture_edit.text().strip()
        if not cid:
            return
        self._data.setdefault("cultures", {})
        if cid not in self._data["cultures"]:
            self._data["cultures"][cid] = {"patterns": ["FN LN"], "first_syllables": [], "last_prefixes": [], "last_cores": [], "last_suffixes": [], "allowed_chars": "^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$"}
            self._refresh_cultures()
            # Select the new culture
            idx = self.culture_combo.findData(cid)
            if idx >= 0:
                self.culture_combo.setCurrentIndex(idx)

    def _save_current_culture(self):
        cid = self._current_culture
        if not cid:
            return
        spec = {
            "patterns": [p.strip() for p in self.patterns_edit.toPlainText().splitlines() if p.strip()],
            "first_syllables": [s.strip() for s in self.first_syllables_edit.toPlainText().split(',') if s.strip()],
            "last_prefixes": [s.strip() for s in self.last_prefixes_edit.toPlainText().split(',') if s.strip()],
            "last_cores": [s.strip() for s in self.last_cores_edit.toPlainText().split(',') if s.strip()],
            "last_suffixes": [s.strip() for s in self.last_suffixes_edit.toPlainText().split(',') if s.strip()],
            "allowed_chars": self.allowed_chars_edit.text().strip() or "^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$"
        }
        self._data.setdefault("cultures", {})
        self._data["cultures"][cid] = spec

    def _on_generate_preview(self):
        # Ensure current edits are reflected
        self._save_current_culture()
        cid = self._current_culture
        if not cid:
            QMessageBox.information(self, "Preview", "Please select or add a culture first.")
            return
        spec = self._data.get("cultures", {}).get(cid, {})
        count = int(self.preview_count.value())
        names = [self._generate_name(spec) for _ in range(count)]
        self.preview_list.clear()
        for n in names:
            self.preview_list.addItem(n)

    def _generate_name(self, spec: dict) -> str:
        pattern = random.choice(spec.get("patterns", ["FN LN"])) if spec.get("patterns") else "FN LN"
        # Generate base components
        fn = self._generate_first(spec)
        fn2 = self._generate_first(spec)
        # Try to avoid FN=FN2
        if fn2 == fn:
            for _ in range(2):
                alt = self._generate_first(spec)
                if alt != fn:
                    fn2 = alt
                    break
        ln = self._generate_last(spec)
        ln2 = self._generate_last(spec)
        if ln2 == ln:
            for _ in range(2):
                alt = self._generate_last(spec)
                if alt != ln:
                    ln2 = alt
                    break
        mi = (fn2[0:1].upper() + ".") if fn2 else "X."

        # Token substitution using regex with word boundaries
        token_map = {"FN2": fn2, "FN": fn, "LN2": ln2, "LN": ln, "MI": mi}
        def _repl(m: re.Match) -> str:
            return token_map.get(m.group(0), m.group(0))
        name = re.sub(r"\b(FN2|FN|LN2|LN|MI)\b", _repl, pattern).strip()
        # Normalize spaces
        name = " ".join(part for part in name.split(" ") if part)
        # Validate against allowed_chars if provided
        allowed = spec.get("allowed_chars", "^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$")
        # Anchorize if needed
        if not allowed.startswith("^"):
            allowed = "^" + allowed
        if not allowed.endswith("$"):
            allowed = allowed + "$"
        try:
            if not re.fullmatch(allowed, name):
                # Conservative fallback: strip characters not in our extended Latin + space, hyphen, apostrophe
                name = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ' -]", "", name)
        except re.error:
            # Invalid regex; ignore and return as-is
            pass
        return name

    def _generate_first(self, spec: dict) -> str:
        syllables = spec.get("first_syllables") or ["al","an","ar","el","ia","ro","li","ma","tha"]
        # Prefer 2 syllables, sometimes 3
        k = 2 if random.random() < 0.75 else 3
        parts = [random.choice(syllables) for _ in range(k)]
        s = "".join(parts)
        return s.capitalize()

    def _generate_last(self, spec: dict) -> str:
        prefixes = spec.get("last_prefixes") or ["stone", "silver", "gold", "fair", "wood"]
        cores = spec.get("last_cores") or ["smith", "walker", "binder", "seeker", "wright"]
        suffixes = spec.get("last_suffixes") or ["", "son", "ton", "ford", "field"]
        p = random.choice(prefixes) if prefixes else ""
        c = random.choice(cores) if cores else ""
        s = random.choice(suffixes) if suffixes else ""
        ln = f"{p}{c}{s}" if (p or c or s) else "Name"
        # If last name ended up empty, fallback
        if not ln:
            ln = "River"
        return ln[:1].upper() + ln[1:]

