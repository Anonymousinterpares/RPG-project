# world_configurator/ui/editors/specific_item_editor.py
"""
Editor for a specific category of items (e.g., origin_items.json).
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any, Union

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QDialogButtonBox,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QComboBox,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame, QCheckBox,
    QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog
)
# Safe import of core stats enums even when world_configurator runs standalone
try:
    from core.stats.stats_base import StatType, DerivedStatType
except ModuleNotFoundError:
    import sys
    try:
        # Use helper to get project root if available
        from utils.file_manager import get_project_root as _wcfg_get_root
        _pr = _wcfg_get_root()
    except Exception:
        _pr = None
    if not _pr:
        import os as _os
        # Compute project root relative to this file: .../latest version
        _pr = _os.path.normpath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..'))
    if _pr and _pr not in sys.path:
        sys.path.insert(0, _pr)
    from core.stats.stats_base import StatType, DerivedStatType

from ui.dialogs.base_dialog import BaseDialog
from utils.file_manager import load_json, save_json, get_project_root

logger = logging.getLogger("world_configurator.ui.specific_item_editor")

# --- Stat Entry Dialog (for item stats) ---
class ItemStatDialog(BaseDialog):
    """Dialog for adding/editing an item stat with validated choices."""
    def __init__(self, parent=None, stat_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Item Stat")
        self.stat_data = stat_data if stat_data else {}

        layout = QFormLayout(self)

        # Build validated stat choices from core enums
        self._stat_choices: List[Dict[str, str]] = []  # {'id': 'strength', 'display': 'Strength (STR)', 'category': 'Primary'}
        # Primary stats
        for s in StatType:
            stat_id = s.name.lower()  # e.g., 'strength'
            friendly = s.name.title()  # 'Strength'
            shown = f"[Primary] {friendly} ({str(s)})"  # 'STR' as value
            self._stat_choices.append({'id': stat_id, 'display': shown, 'category': 'Primary'})
        # Derived stats
        for d in DerivedStatType:
            stat_id = d.name.lower()  # e.g., 'melee_attack'
            shown = f"[Derived] {str(d)}"  # str(d) is human-friendly like 'Melee Attack'
            self._stat_choices.append({'id': stat_id, 'display': shown, 'category': 'Derived'})

        # Stat selector
        self.stat_combo = QComboBox()
        for opt in self._stat_choices:
            self.stat_combo.addItem(opt['display'], userData=opt['id'])

        # Preselect if editing existing
        existing_name = str(self.stat_data.get("name", "")).strip()
        selected_index = -1
        if existing_name:
            # Normalize existing to canonical id using enums
            canonical = None
            try:
                st = StatType.from_string(existing_name)
                canonical = st.name.lower()
            except Exception:
                try:
                    dt = DerivedStatType.from_string(existing_name)
                    canonical = dt.name.lower()
                except Exception:
                    # Fallback: attempt lower/underscore
                    canonical = existing_name.lower().replace(' ', '_')
            for i in range(self.stat_combo.count()):
                if self.stat_combo.itemData(i) == canonical:
                    selected_index = i
                    break
        if selected_index >= 0:
            self.stat_combo.setCurrentIndex(selected_index)
        else:
            self.stat_combo.setCurrentIndex(0)

        self.value_edit = QLineEdit(str(self.stat_data.get("value", "0")))  # keep text edit for flexible input
        self.value_edit.setPlaceholderText("Value (numeric or boolean)")

        # Default display name suggestion based on selected stat
        suggested_display = self._suggest_display_name(self.stat_combo.currentData())
        self.display_name_edit = QLineEdit(self.stat_data.get("display_name", suggested_display))
        self.display_name_edit.setPlaceholderText("Auto display name for selected stat")
        # Lock display name to canonical stat name to avoid typos
        try:
            self.display_name_edit.setReadOnly(True)
        except Exception:
            pass
        self.is_percentage_check = QCheckBox("Is Percentage?")
        self.is_percentage_check.setChecked(self.stat_data.get("is_percentage", False))

        # Always update display name to match current selection
        def _on_stat_changed():
            self.display_name_edit.setText(self._suggest_display_name(self.stat_combo.currentData()))
        self.stat_combo.currentIndexChanged.connect(_on_stat_changed)
        # Ensure initial sync
        _on_stat_changed()

        layout.addRow("Stat:", self.stat_combo)
        layout.addRow("Value:", self.value_edit)
        layout.addRow("Display Name:", self.display_name_edit)
        layout.addRow(self.is_percentage_check)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def _suggest_display_name(self, stat_id: Optional[str]) -> str:
        if not stat_id:
            return ""
        # For primary stats, use Title case of enum name; for derived, use enum value (human-friendly)
        try:
            st = StatType[stat_id.upper()]
            return st.name.title()
        except Exception:
            try:
                dt = DerivedStatType[stat_id.upper()]
                return str(dt)
            except Exception:
                # Fallback: prettify
                return stat_id.replace('_', ' ').title()

    def get_stat_data(self) -> Optional[Dict[str, Any]]:
        name = self.stat_combo.currentData()
        value_str = self.value_edit.text().strip()
        display_name = self.display_name_edit.text().strip()
        is_percentage = self.is_percentage_check.isChecked()

        if not name or not value_str:
            QMessageBox.warning(self, "Input Error", "Stat and Value are required.")
            return None

        # Attempt to parse value as float, int, or bool
        parsed_value: Any
        try:
            if '.' in value_str:
                parsed_value = float(value_str)
            else:
                parsed_value = int(value_str)
        except ValueError:
            if value_str.lower() == 'true':
                parsed_value = True
            elif value_str.lower() == 'false':
                parsed_value = False
            else:
                parsed_value = value_str

        data = {"name": name, "value": parsed_value}
        if display_name:
            data["display_name"] = display_name
        if is_percentage:
            data["is_percentage"] = True
        return data

    def get_stat_data(self) -> Optional[Dict[str, Any]]:
        name = self.name_edit.text().strip()
        value_str = self.value_edit.text().strip()
        display_name = self.display_name_edit.text().strip()
        is_percentage = self.is_percentage_check.isChecked()

        if not name or not value_str:
            QMessageBox.warning(self, "Input Error", "Stat ID and Value are required.")
            return None

        # Attempt to parse value as float, int, or bool
        parsed_value: Any
        try:
            if '.' in value_str:
                parsed_value = float(value_str)
            else:
                parsed_value = int(value_str)
        except ValueError:
            if value_str.lower() == 'true':
                parsed_value = True
            elif value_str.lower() == 'false':
                parsed_value = False
            else: # Treat as string if not parsable as number/bool
                parsed_value = value_str


        data = {"name": name, "value": parsed_value}
        if display_name:
            data["display_name"] = display_name
        if is_percentage:
            data["is_percentage"] = True
        return data

# --- Dice Roll Effect Dialog ---
class DiceRollEffectDialog(BaseDialog):
    """Dialog for adding/editing a dice roll effect."""
    def __init__(self, parent=None, effect_data: Optional[Dict[str, str]] = None, effect_types: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Dice Roll Effect")
        self.effect_data = effect_data if effect_data else {}
        self._effect_types = effect_types or [
            "slashing","piercing","bludgeoning","fire","cold","lightning","poison","acid","arcane"
        ]

        layout = QFormLayout(self)
        # Effect type dropdown
        self.effect_type_combo = QComboBox()
        for et in self._effect_types:
            self.effect_type_combo.addItem(et)
        # Preselect existing if provided
        existing_et = str(self.effect_data.get("effect_type", "")).strip().lower()
        if existing_et:
            idx = self.effect_type_combo.findText(existing_et)
            if idx >= 0:
                self.effect_type_combo.setCurrentIndex(idx)
        self.dice_notation_edit = QLineEdit(self.effect_data.get("dice_notation", ""))
        self.dice_notation_edit.setPlaceholderText("e.g., 1d8+2")
        self.description_edit = QLineEdit(self.effect_data.get("description", ""))
        self.description_edit.setPlaceholderText("Optional description of the effect")

        layout.addRow("Effect Type:", self.effect_type_combo)
        layout.addRow("Dice Notation:", self.dice_notation_edit)
        layout.addRow("Description:", self.description_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def get_effect_data(self) -> Optional[Dict[str, str]]:
        effect_type = self.effect_type_combo.currentText().strip()
        dice_notation = self.dice_notation_edit.text().strip()
        description = self.description_edit.text().strip()

        if not effect_type or not dice_notation:
            QMessageBox.warning(self, "Input Error", "Effect Type and Dice Notation are required.")
            return None
        return {"effect_type": effect_type, "dice_notation": dice_notation, "description": description}


class SpecificItemEditor(QWidget):
    """
    Editor for a list of items from a specific JSON file.
    """
    data_modified = Signal()

    def __init__(self, item_file_key: str, item_file_path_relative: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.item_file_key = item_file_key # e.g., "Starting Items"
        self.item_file_path_relative = item_file_path_relative
        self.items_data: List[Dict[str, Any]] = [] # List of item dictionaries
        self.current_item_index: Optional[int] = None

        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.full_item_file_path = os.path.join(self.project_root, self.item_file_path_relative)

        self._setup_ui()
        
        # Load effect types from combat config for dropdowns and LLM grounding
        try:
            combat_cfg_path = os.path.join(self.project_root, "config", "combat", "combat_config.json")
            combat_cfg = load_json(combat_cfg_path) or {}
            dmg = combat_cfg.get("damage", {}) if isinstance(combat_cfg, dict) else {}
            ets = dmg.get("types", []) if isinstance(dmg, dict) else []
            if isinstance(ets, list) and ets:
                self._effect_types: List[str] = [str(x).strip().lower() for x in ets if isinstance(x, str)]
            else:
                self._effect_types = ["slashing","piercing","bludgeoning","fire","cold","lightning","poison","acid","arcane"]
        except Exception:
            self._effect_types = ["slashing","piercing","bludgeoning","fire","cold","lightning","poison","acid","arcane"]
        
        self.load_data()

    # ===== Assistant integration (provider methods) =====
    def get_assistant_context(self):
        """Provide selection context for the assistant."""
        try:
            from assistant.context import AssistantContext
        except Exception:
            # Lazy import path fallback if packaging differs
            from ..assistant.context import AssistantContext  # type: ignore
        item = self._current_item_dict()
        allowed = [
            "/name",
            "/description",
            "/item_type",
            "/rarity",
            "/weight",
            "/value",
            "/is_equippable",
            "/is_consumable",
            "/is_stackable",
            "/is_quest_item",
            "/equip_slots",
            "/stack_limit",
            "/durability",
            "/current_durability",
            "/stats",
            "/dice_roll_effects",
            "/tags",
            "/custom_properties",
        ]
        selection_id = (item.get("id") if isinstance(item, dict) else None)
        return AssistantContext(
            domain=f"items:{self.item_file_key}",
            selection_id=selection_id,
            content=item if isinstance(item, dict) else None,
            schema=None,
            allowed_paths=allowed,
        )

    def get_reference_catalogs(self) -> Dict[str, Any]:
        """Return minimal catalogs and constraints to ground LLM responses."""
        try:
            item_types = ["armor","weapon","shield","accessory","consumable","tool","container","document","key","material","treasure","miscellaneous"]
            rarities = ["common","uncommon","rare","epic","legendary","quest"]
            equip_slots = [
                "main_hand","off_hand","both_hands","head","chest","legs","hands","feet",
                "neck","ring","belt","cloak","quiver","pouch"
            ]
            primary_stats = [s.name.lower() for s in StatType]
            derived_stats = [d.name.lower() for d in DerivedStatType]
            names = sorted({i.get("name","") for i in self.items_data if isinstance(i, dict) and i.get("name")})
            ids = sorted({i.get("id","") for i in self.items_data if isinstance(i, dict) and i.get("id")})
            return {
                "constraints": {
                    "item_types": item_types,
                    "rarities": rarities,
                    "equip_slots": equip_slots,
                    "stat_ids_primary": primary_stats,
                    "stat_ids_derived": derived_stats,
                },
                "effect_types": getattr(self, "_effect_types", []),
                "existing_names": names,
                "existing_ids": ids,
            }
        except Exception:
            return {}

    def apply_assistant_patch(self, patch_ops):
        """Apply RFC6902 patch ops to the current selection, with validation and sanitization."""
        try:
            from assistant.patching import apply_patch_with_validation
        except Exception:
            from ..assistant.patching import apply_patch_with_validation  # type: ignore
        ctx = self.get_assistant_context()
        if not ctx.content or self.current_item_index is None:
            return False, "No item selected."
        ok, msg, new_content = apply_patch_with_validation(ctx, ctx.content, patch_ops)
        if not ok:
            return False, msg
        try:
            sanitized = self._sanitize_item_payload(new_content)
            self._replace_current_item(sanitized)
            self.save_data()
            # Refresh details UI with sanitized values
            self._populate_details_from_item_data(sanitized)
            return True, "OK"
        except Exception as e:
            logger.error("Failed to apply assistant patch: %s", e, exc_info=True)
            return False, f"Failed to apply: {e}"

    def create_entry_from_llm(self, entry: dict):
        """Create a new item from LLM proposal, ensuring uniqueness and sanitization."""
        try:
            payload = self._sanitize_item_payload(entry, for_create=True)
            proposed_id = payload.get("id") or self._generate_id_from_name(payload.get("name", "New Item"))
            new_id = self._ensure_unique_id(proposed_id)
            new_name = self._ensure_unique_name(payload.get("name") or "New Item")
            payload["id"] = new_id
            payload["name"] = new_name
            self.items_data.append(payload)
            if not self.save_data():
                return False, "Failed to save", None
            self._refresh_item_list_widget()
            self._select_item_by_id(new_id)
            return True, "Created", new_id
        except Exception as e:
            logger.error("Failed to create entry from LLM: %s", e, exc_info=True)
            return False, f"Failed to create: {e}", None

    # ===== Search helpers for targeted visibility =====
    def search_for_entries(self, term: str, limit: int = 10) -> List[tuple]:
        """Fuzzy-match items by id/name/tags and return list of (id, name, score)."""
        import difflib, unicodedata
        def _norm(s: str) -> str:
            try:
                s2 = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
            except Exception:
                s2 = s or ""
            return s2.lower()
        q = _norm(term)
        results: List[tuple] = []
        for it in self.items_data:
            if not isinstance(it, dict):
                continue
            iid = str(it.get("id", ""))
            nm = str(it.get("name", ""))
            tags = ",".join(it.get("tags", [])) if isinstance(it.get("tags"), list) else ""
            hay = " | ".join([iid, nm, tags])
            score = difflib.SequenceMatcher(None, q, _norm(hay)).ratio()
            if score >= 0.4:
                results.append((iid, nm or iid, float(score)))
        results.sort(key=lambda t: (-t[2], t[1], t[0]))
        return results[:limit]

    def focus_entry(self, item_id: str) -> bool:
        """Focus/select the item with given id in the UI and internal state."""
        try:
            # update current index to item id's index in items_data
            idx = None
            for i, it in enumerate(self.items_data):
                if isinstance(it, dict) and it.get("id") == item_id:
                    idx = i
                    break
            if idx is None:
                return False
            self.current_item_index = idx
            # refresh list to ensure rows/indices align, then select by id
            self._refresh_item_list_widget()
            self._select_item_by_id(item_id)
            return True
        except Exception:
            return False

    # ===== Internal helpers =====
    def _current_item_dict(self) -> Optional[Dict[str, Any]]:
        if self.current_item_index is None:
            return None
        if 0 <= self.current_item_index < len(self.items_data):
            it = self.items_data[self.current_item_index]
            return it if isinstance(it, dict) else None
        return None

    def _replace_current_item(self, new_dict: Dict[str, Any]) -> None:
        if self.current_item_index is None:
            return
        if 0 <= self.current_item_index < len(self.items_data):
            self.items_data[self.current_item_index] = new_dict

    def _select_item_by_id(self, item_id: str) -> None:
        # Find new index and select in list widget
        target_index = None
        for i, it in enumerate(self.items_data):
            if isinstance(it, dict) and it.get("id") == item_id:
                target_index = i
                break
        if target_index is None:
            return
        # Find the row in the QListWidget whose UserRole matches target_index
        for row in range(self.item_list_widget.count()):
            it = self.item_list_widget.item(row)
            if it and it.data(Qt.UserRole) == target_index:
                self.item_list_widget.setCurrentRow(row)
                break

    def _ensure_unique_id(self, proposed_id: str) -> str:
        existing = {str(it.get("id")) for it in self.items_data if isinstance(it, dict) and it.get("id")}
        pid = (proposed_id or "item").strip()
        if pid not in existing:
            return pid
        base = pid
        suffix = 2
        nid = f"{base}_{suffix}"
        while nid in existing:
            suffix += 1
            nid = f"{base}_{suffix}"
        return nid

    def _ensure_unique_name(self, proposed_name: str) -> str:
        existing = {str(it.get("name")) for it in self.items_data if isinstance(it, dict) and it.get("name")}
        name = (proposed_name or "New Item").strip()
        if name not in existing:
            return name
        base = name
        suffix = 2
        nn = f"{base} ({suffix})"
        while nn in existing:
            suffix += 1
            nn = f"{base} ({suffix})"
        return nn

    def _generate_id_from_name(self, name: str) -> str:
        import re
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", (name or "item").strip().lower()).strip("_")
        if not slug:
            slug = "item"
        return slug

    def _sanitize_item_payload(self, payload: Dict[str, Any], for_create: bool = False) -> Dict[str, Any]:
        """Normalize and validate item payload before persisting."""
        out: Dict[str, Any] = dict(payload or {})
        def as_float(x, default=0.0):
            try:
                return float(x)
            except Exception:
                return default
        def as_int(x, default=0):
            try:
                return int(x)
            except Exception:
                return default
        def as_bool(x):
            if isinstance(x, bool):
                return x
            s = str(x).strip().lower()
            return s in ("1","true","yes","y","on")
        def as_list_str(v):
            vals: List[str] = []
            if isinstance(v, list):
                for el in v:
                    if isinstance(el, str) and el.strip():
                        vals.append(el.strip())
                    elif isinstance(el, dict):
                        vid = el.get("id")
                        if isinstance(vid, str) and vid.strip():
                            vals.append(vid.strip())
            # dedupe preserve order
            seen = set(); res: List[str] = []
            for s in vals:
                if s not in seen:
                    seen.add(s)
                    res.append(s)
            return res

        if for_create:
            out["name"] = (out.get("name") or "New Item").strip()
            out["item_type"] = str(out.get("item_type") or "miscellaneous").lower()
            out["rarity"] = str(out.get("rarity") or "common").lower()

        # Scalars
        if "name" in out: out["name"] = str(out["name"]).strip()
        if "description" in out: out["description"] = str(out["description"]).strip()
        if "item_type" in out: out["item_type"] = str(out["item_type"]).lower()
        if "rarity" in out: out["rarity"] = str(out["rarity"]).lower()
        if "weight" in out: out["weight"] = max(0.0, as_float(out["weight"]))
        if "value" in out: out["value"] = max(0, as_int(out["value"]))
        for k in ("is_equippable","is_consumable","is_stackable","is_quest_item"):
            if k in out: out[k] = as_bool(out[k])

        # Equip slots and tags
        if "equip_slots" in out: out["equip_slots"] = as_list_str(out["equip_slots"]) or out.pop("equip_slots", None) or []
        if "tags" in out: out["tags"] = as_list_str(out["tags"]) or out.pop("tags", None) or []

        # Stack/durability
        if out.get("is_stackable"):
            out["stack_limit"] = max(1, as_int(out.get("stack_limit", 1), 1))
        else:
            out.pop("stack_limit", None)
        if "durability" in out:
            out["durability"] = max(0, as_int(out["durability"]))
            if out["durability"] <= 0:
                out.pop("current_durability", None)
            else:
                out["current_durability"] = max(0, min(out["durability"], as_int(out.get("current_durability", out["durability"]))))

        # Stats normalization
        stats = out.get("stats")
        if isinstance(stats, list):
            norm_stats: List[Dict[str, Any]] = []
            valid_names = {s.name.lower() for s in StatType} | {d.name.lower() for d in DerivedStatType}
            for st in stats:
                if not isinstance(st, dict):
                    continue
                name = str(st.get("name", "")).lower().replace(" ", "_")
                if name not in valid_names:
                    continue
                val = st.get("value")
                # parse numeric/bool if string
                if isinstance(val, str):
                    vstr = val.strip()
                    try:
                        val = float(vstr) if "." in vstr else int(vstr)
                    except Exception:
                        if vstr.lower() in ("true","false"):
                            val = (vstr.lower() == "true")
                entry = {"name": name, "value": val}
                if st.get("display_name"): entry["display_name"] = str(st["display_name"]).strip()
                if st.get("is_percentage"): entry["is_percentage"] = bool(st["is_percentage"])
                norm_stats.append(entry)
            out["stats"] = norm_stats

        # Dice roll effects
        dre = out.get("dice_roll_effects")
        if isinstance(dre, list):
            norm_dre: List[Dict[str, Any]] = []
            for e in dre:
                if not isinstance(e, dict):
                    continue
                et = str(e.get("effect_type", "")).strip()
                dn = str(e.get("dice_notation", "")).strip()
                if not et or not dn:
                    continue
                entry = {"effect_type": et, "dice_notation": dn}
                if e.get("description"): entry["description"] = str(e["description"]).strip()
                norm_dre.append(entry)
            out["dice_roll_effects"] = norm_dre

        # Custom properties must be a dict if present
        if "custom_properties" in out and not isinstance(out["custom_properties"], dict):
            out.pop("custom_properties", None)

        # Clamp enums
        if out.get("item_type") not in {"armor","weapon","shield","accessory","consumable","tool","container","document","key","material","treasure","miscellaneous"}:
            out["item_type"] = "miscellaneous"
        if out.get("rarity") not in {"common","uncommon","rare","epic","legendary","quest"}:
            out["rarity"] = "common"

        return out

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # Left Panel: Item List
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel(f"{self.item_file_key} List"))
        self.item_list_widget = QListWidget()
        self.item_list_widget.currentItemChanged.connect(self._on_item_selected)
        left_layout.addWidget(self.item_list_widget)
        list_buttons_layout = QHBoxLayout()
        self.add_item_button = QPushButton("Add Item")
        self.add_item_button.clicked.connect(self._add_item)
        list_buttons_layout.addWidget(self.add_item_button)
        self.remove_item_button = QPushButton("Remove Item")
        self.remove_item_button.clicked.connect(self._remove_item)
        self.remove_item_button.setEnabled(False)
        list_buttons_layout.addWidget(self.remove_item_button)
        left_layout.addLayout(list_buttons_layout)
        splitter.addWidget(left_panel)

        # Right Panel: Item Details Editor
        right_panel_scroll = QScrollArea()
        right_panel_scroll.setWidgetResizable(True)
        details_widget_container = QWidget() # Container for the form layout
        right_panel_scroll.setWidget(details_widget_container)

        self.details_form_layout = QFormLayout()
        self.details_form_layout.setContentsMargins(10,10,10,10)
        details_widget_container.setLayout(self.details_form_layout) # Set layout on container


        # Common Fields (ID, Name, Description, Item Type, Rarity, Weight, Value)
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("Unique item ID")
        self.details_form_layout.addRow("ID*:", self.id_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Display name of the item")
        self.details_form_layout.addRow("Name*:", self.name_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Detailed description")
        self.description_edit.setFixedHeight(80)
        self.details_form_layout.addRow("Description:", self.description_edit)

        self.item_type_combo = QComboBox()
        item_types = ["armor", "weapon", "shield", "accessory", "consumable", "tool", "container", "document", "key", "material", "treasure", "miscellaneous"]
        self.item_type_combo.addItems(sorted(item_types))
        self.details_form_layout.addRow("Item Type:", self.item_type_combo)

        self.rarity_combo = QComboBox()
        rarities = ["common", "uncommon", "rare", "epic", "legendary", "quest"]
        self.rarity_combo.addItems(sorted(rarities))
        self.details_form_layout.addRow("Rarity:", self.rarity_combo)

        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 1000.0); self.weight_spin.setDecimals(2); self.weight_spin.setSingleStep(0.1)
        self.details_form_layout.addRow("Weight:", self.weight_spin)

        self.value_spin = QSpinBox()
        self.value_spin.setRange(0, 1000000); self.value_spin.setSingleStep(10)
        self.details_form_layout.addRow("Value (base copper):", self.value_spin)

        # Boolean Flags
        flags_layout = QHBoxLayout()
        self.is_equippable_check = QCheckBox("Equippable")
        self.is_consumable_check = QCheckBox("Consumable")
        self.is_stackable_check = QCheckBox("Stackable")
        self.is_quest_item_check = QCheckBox("Quest Item")
        flags_layout.addWidget(self.is_equippable_check)
        flags_layout.addWidget(self.is_consumable_check)
        flags_layout.addWidget(self.is_stackable_check)
        flags_layout.addWidget(self.is_quest_item_check)
        self.details_form_layout.addRow("Flags:", flags_layout)

        # Conditional Fields
        self.equip_slots_edit = QLineEdit()
        self.equip_slots_edit.setPlaceholderText("Comma-separated (e.g., main_hand,chest)")
        self.details_form_layout.addRow("Equip Slots:", self.equip_slots_edit)

        self.stack_limit_spin = QSpinBox()
        self.stack_limit_spin.setRange(1, 9999)
        self.details_form_layout.addRow("Stack Limit:", self.stack_limit_spin)

        self.durability_spin = QSpinBox()
        self.durability_spin.setRange(0, 1000)
        self.details_form_layout.addRow("Durability (Max):", self.durability_spin)

        self.current_durability_spin = QSpinBox()
        self.current_durability_spin.setRange(0,1000)
        self.details_form_layout.addRow("Current Durability:", self.current_durability_spin)


        # Stats Table
        self.details_form_layout.addRow(QLabel("<b>Item Stats:</b>"))
        self.stats_table = QTableWidget(0, 3)
        self.stats_table.setHorizontalHeaderLabels(["Stat ID", "Value", "Display Name"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setFixedHeight(100)
        self.details_form_layout.addRow(self.stats_table)
        stats_buttons_layout = QHBoxLayout()
        self.add_stat_button = QPushButton("Add Stat")
        self.add_stat_button.clicked.connect(self._add_item_stat)
        stats_buttons_layout.addWidget(self.add_stat_button)
        self.remove_stat_button = QPushButton("Remove Stat")
        self.remove_stat_button.clicked.connect(self._remove_item_stat)
        stats_buttons_layout.addWidget(self.remove_stat_button)
        self.details_form_layout.addRow(stats_buttons_layout)

        # Dice Roll Effects Table (for weapons primarily)
        self.details_form_layout.addRow(QLabel("<b>Dice Roll Effects:</b>"))
        self.dice_effects_table = QTableWidget(0, 3)
        self.dice_effects_table.setHorizontalHeaderLabels(["Effect Type", "Dice Notation", "Description"])
        self.dice_effects_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dice_effects_table.setFixedHeight(100)
        self.details_form_layout.addRow(self.dice_effects_table)
        dice_buttons_layout = QHBoxLayout()
        self.add_dice_effect_button = QPushButton("Add Dice Effect")
        self.add_dice_effect_button.clicked.connect(self._add_dice_effect)
        dice_buttons_layout.addWidget(self.add_dice_effect_button)
        self.remove_dice_effect_button = QPushButton("Remove Dice Effect")
        self.remove_dice_effect_button.clicked.connect(self._remove_dice_effect)
        dice_buttons_layout.addWidget(self.remove_dice_effect_button)
        self.details_form_layout.addRow(dice_buttons_layout)


        # Tags
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Comma-separated tags (e.g., magic, fire, potion)")
        self.details_form_layout.addRow("Tags:", self.tags_edit)

        # Custom Properties (simple JSON string for now)
        self.custom_props_edit = QTextEdit()
        self.custom_props_edit.setPlaceholderText("JSON string for custom properties, e.g., {\"charge_cost\": 5}")
        self.custom_props_edit.setFixedHeight(60)
        self.details_form_layout.addRow("Custom Properties (JSON):", self.custom_props_edit)


        self.save_item_button = QPushButton("Save Item Changes")
        self.save_item_button.clicked.connect(self._save_current_item_details)
        self.details_form_layout.addRow(self.save_item_button)

        splitter.addWidget(right_panel_scroll)
        splitter.setSizes([250, 550])
        main_layout.addWidget(splitter)

        self._set_details_enabled(False)

    # --- Data Loading and Saving ---
    def load_data(self):
        """Loads item data from the JSON file."""
        if os.path.exists(self.full_item_file_path):
            loaded_data = load_json(self.full_item_file_path)
            if isinstance(loaded_data, list):
                self.items_data = loaded_data
            else:
                logger.error(f"Data in {self.item_file_key} file is not a list. Initializing as empty.")
                self.items_data = []
        else:
            logger.warning(f"{self.item_file_key} file not found at {self.full_item_file_path}. Starting with empty list.")
            self.items_data = []
        self._refresh_item_list_widget()

    def save_data(self) -> bool:
        """Saves all items data to the JSON file."""
        # Ensure current item details are applied to self.items_data if an item is selected
        if self.current_item_index is not None and self.current_item_index < len(self.items_data):
            self._apply_details_to_current_item_data()

        if save_json(self.items_data, self.full_item_file_path):
            logger.info(f"Saved {self.item_file_key} data to {self.full_item_file_path}")
            self.data_modified.emit()
            return True
        else:
            QMessageBox.critical(self, "Save Error", f"Failed to save {self.item_file_key} data.")
            return False

    def _refresh_item_list_widget(self):
        self.item_list_widget.clear()
        self.items_data.sort(key=lambda x: x.get("name", x.get("id", ""))) # Sort by name, then ID
        for index, item_dict in enumerate(self.items_data):
            display_name = f"{item_dict.get('name', 'Unnamed Item')} ({item_dict.get('id', 'No ID')})"
            list_item = QListWidgetItem(display_name)
            list_item.setData(Qt.UserRole, index) # Store index in the list
            self.item_list_widget.addItem(list_item)
        self._set_details_enabled(False)
        self.remove_item_button.setEnabled(False)

    # --- UI Callbacks ---
    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_item_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if current:
            # Save previous item's details before loading new one if it was modified
            if previous and self.current_item_index is not None:
                 # This check is tricky without a dedicated "modified" flag for the form.
                 # Forcing apply could overwrite unintended changes if user just clicked around.
                 # A simpler approach is to rely on the explicit "Save Item Changes" button.
                 pass


            self.current_item_index = current.data(Qt.UserRole)
            if self.current_item_index is not None and self.current_item_index < len(self.items_data):
                self._populate_details_from_item_data(self.items_data[self.current_item_index])
                self._set_details_enabled(True)
                self.remove_item_button.setEnabled(True)
            else:
                self._clear_details()
                self._set_details_enabled(False)
                self.remove_item_button.setEnabled(False)
        else:
            self.current_item_index = None
            self._clear_details()
            self._set_details_enabled(False)
            self.remove_item_button.setEnabled(False)

    @Slot()
    def _add_item(self):
        new_item_id_prefix = self.item_file_key.lower().replace(" ", "_").replace("_templates","")
        # Generate a unique enough ID
        new_id_base = f"new_{new_item_id_prefix}_item"
        new_id_suffix = 1
        new_id = f"{new_id_base}_{new_id_suffix}"
        existing_ids = {item.get("id") for item in self.items_data}
        while new_id in existing_ids:
            new_id_suffix += 1
            new_id = f"{new_id_base}_{new_id_suffix}"

        new_item = {"id": new_id, "name": "New Item", "item_type": "miscellaneous"}
        self.items_data.append(new_item)
        self._refresh_item_list_widget()
        # Select the new item
        for i in range(self.item_list_widget.count()):
            if self.item_list_widget.item(i).data(Qt.UserRole) == len(self.items_data) - 1:
                self.item_list_widget.setCurrentRow(i)
                break
        self.id_edit.setFocus() # Focus on ID for editing
        self.data_modified.emit()


    @Slot()
    def _remove_item(self):
        if self.current_item_index is None or not (0 <= self.current_item_index < len(self.items_data)):
            return

        item_to_remove = self.items_data[self.current_item_index]
        reply = QMessageBox.question(self, "Remove Item",
                                     f"Are you sure you want to remove '{item_to_remove.get('name', item_to_remove.get('id'))}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.items_data[self.current_item_index]
            self.current_item_index = None
            self._refresh_item_list_widget()
            self._clear_details()
            self._set_details_enabled(False)
            self.data_modified.emit()
            self.save_data() # Auto-save after removal

    @Slot()
    def _save_current_item_details(self):
        if self.current_item_index is None or not (0 <= self.current_item_index < len(self.items_data)):
            QMessageBox.warning(self, "No Item Selected", "Please select an item to save.")
            return
        
        item_id = self.id_edit.text().strip()
        item_name = self.name_edit.text().strip()

        if not item_id:
            QMessageBox.warning(self, "Validation Error", "Item ID cannot be empty.")
            self.id_edit.setFocus()
            return
        if not item_name:
            QMessageBox.warning(self, "Validation Error", "Item Name cannot be empty.")
            self.name_edit.setFocus()
            return

        # Check for ID uniqueness if ID was changed
        original_id = self.items_data[self.current_item_index].get("id")
        if item_id != original_id:
            for idx, item_data_iter in enumerate(self.items_data):
                if idx != self.current_item_index and item_data_iter.get("id") == item_id:
                    QMessageBox.warning(self, "Validation Error", f"Item ID '{item_id}' already exists. Please choose a unique ID.")
                    self.id_edit.setFocus()
                    return

        self._apply_details_to_current_item_data()
        self.save_data() # This will save the whole list to file
        # Refresh the list item text in case name/ID changed
        self._refresh_item_list_widget()
        # Reselect the item
        for i in range(self.item_list_widget.count()):
            if self.item_list_widget.item(i).data(Qt.UserRole) == self.current_item_index: # index might shift if sorted by name
                # find by new ID instead if ID changed
                if item_id != original_id:
                    found_by_new_id = False
                    for new_idx, item_in_list_data in enumerate(self.items_data):
                        if item_in_list_data.get("id") == item_id:
                            self.current_item_index = new_idx # update current_item_index
                            self.item_list_widget.setCurrentRow(new_idx)
                            found_by_new_id = True
                            break
                    if not found_by_new_id:
                        self.current_item_index = None # Should not happen if ID is unique
                else: # ID didn't change, reselect by old index (if still valid after sort)
                    # Re-find by ID to be safe after sort
                    found_by_id_after_sort = False
                    for new_idx_after_sort, item_in_list_data_after_sort in enumerate(self.items_data):
                        if item_in_list_data_after_sort.get("id") == original_id:
                            self.current_item_index = new_idx_after_sort
                            self.item_list_widget.setCurrentRow(new_idx_after_sort)
                            found_by_id_after_sort = True
                            break
                    if not found_by_id_after_sort:
                        self.current_item_index = None


    # --- Helper Methods for Detail Management ---
    def _populate_details_from_item_data(self, item_data: Dict[str, Any]):
        self.id_edit.setText(item_data.get("id", ""))
        self.name_edit.setText(item_data.get("name", ""))
        self.description_edit.setPlainText(item_data.get("description", ""))
        self.item_type_combo.setCurrentText(item_data.get("item_type", "miscellaneous"))
        self.rarity_combo.setCurrentText(item_data.get("rarity", "common"))
        self.weight_spin.setValue(float(item_data.get("weight", 0.0)))
        self.value_spin.setValue(int(item_data.get("value", 0)))

        self.is_equippable_check.setChecked(bool(item_data.get("is_equippable", False)))
        self.is_consumable_check.setChecked(bool(item_data.get("is_consumable", False)))
        self.is_stackable_check.setChecked(bool(item_data.get("is_stackable", False)))
        self.is_quest_item_check.setChecked(bool(item_data.get("is_quest_item", False)))

        self.equip_slots_edit.setText(", ".join(item_data.get("equip_slots", [])))
        self.stack_limit_spin.setValue(int(item_data.get("stack_limit", 1)))
        self.durability_spin.setValue(int(item_data.get("durability", 0)))
        self.current_durability_spin.setValue(int(item_data.get("current_durability", item_data.get("durability", 0))))


        # Populate stats table
        self.stats_table.setRowCount(0)
        stats_list = item_data.get("stats", [])
        if isinstance(stats_list, list):
            for stat_entry in stats_list:
                if isinstance(stat_entry, dict):
                    row_pos = self.stats_table.rowCount()
                    self.stats_table.insertRow(row_pos)
                    self.stats_table.setItem(row_pos, 0, QTableWidgetItem(stat_entry.get("name", "")))
                    self.stats_table.setItem(row_pos, 1, QTableWidgetItem(str(stat_entry.get("value", ""))))
                    self.stats_table.setItem(row_pos, 2, QTableWidgetItem(stat_entry.get("display_name", "")))
                    # Store full stat dict in first item for editing
                    self.stats_table.item(row_pos, 0).setData(Qt.UserRole, stat_entry)


        # Populate dice effects table
        self.dice_effects_table.setRowCount(0)
        dice_effects_list = item_data.get("dice_roll_effects", [])
        if isinstance(dice_effects_list, list):
            for effect_entry in dice_effects_list:
                if isinstance(effect_entry, dict):
                    row_pos = self.dice_effects_table.rowCount()
                    self.dice_effects_table.insertRow(row_pos)
                    self.dice_effects_table.setItem(row_pos, 0, QTableWidgetItem(effect_entry.get("effect_type", "")))
                    self.dice_effects_table.setItem(row_pos, 1, QTableWidgetItem(effect_entry.get("dice_notation", "")))
                    self.dice_effects_table.setItem(row_pos, 2, QTableWidgetItem(effect_entry.get("description", "")))
                    # Store full effect dict in first item for editing
                    self.dice_effects_table.item(row_pos, 0).setData(Qt.UserRole, effect_entry)


        self.tags_edit.setText(", ".join(item_data.get("tags", [])))

        custom_props = item_data.get("custom_properties", {})
        try:
            self.custom_props_edit.setPlainText(json.dumps(custom_props, indent=2) if custom_props else "")
        except TypeError:
            self.custom_props_edit.setPlainText("") # Clear if not serializable

        self._update_conditional_field_visibility()


    def _apply_details_to_current_item_data(self):
        if self.current_item_index is None or not (0 <= self.current_item_index < len(self.items_data)):
            return

        item_data = self.items_data[self.current_item_index]

        item_data["id"] = self.id_edit.text().strip()
        item_data["name"] = self.name_edit.text().strip()
        item_data["description"] = self.description_edit.toPlainText().strip()
        item_data["item_type"] = self.item_type_combo.currentText()
        item_data["rarity"] = self.rarity_combo.currentText()
        item_data["weight"] = self.weight_spin.value()
        item_data["value"] = self.value_spin.value()

        item_data["is_equippable"] = self.is_equippable_check.isChecked()
        item_data["is_consumable"] = self.is_consumable_check.isChecked()
        item_data["is_stackable"] = self.is_stackable_check.isChecked()
        item_data["is_quest_item"] = self.is_quest_item_check.isChecked()

        if item_data["is_equippable"]:
            item_data["equip_slots"] = [s.strip() for s in self.equip_slots_edit.text().split(',') if s.strip()]
        else:
            item_data.pop("equip_slots", None)

        if item_data["is_stackable"]:
            item_data["stack_limit"] = self.stack_limit_spin.value()
        else:
            item_data.pop("stack_limit", None)

        item_data["durability"] = self.durability_spin.value()
        if item_data["durability"] > 0 : # Only save current_durability if max durability is set
            item_data["current_durability"] = self.current_durability_spin.value()
        else:
            item_data.pop("current_durability", None)


        # Stats
        new_stats = []
        for r in range(self.stats_table.rowCount()):
            name = self.stats_table.item(r, 0).text()
            value_str = self.stats_table.item(r,1).text()
            display_name = self.stats_table.item(r,2).text()
            
            parsed_value: Any
            try: # Try to parse as number or bool
                if '.' in value_str: parsed_value = float(value_str)
                else: parsed_value = int(value_str)
            except ValueError:
                if value_str.lower() == 'true': parsed_value = True
                elif value_str.lower() == 'false': parsed_value = False
                else: parsed_value = value_str # Keep as string if not number/bool

            stat_entry = {"name": name, "value": parsed_value}
            if display_name: stat_entry["display_name"] = display_name
            # Check for is_percentage from original data if editing, or default to false
            original_stat_data = self.stats_table.item(r,0).data(Qt.UserRole)
            if isinstance(original_stat_data, dict) and original_stat_data.get("is_percentage"):
                stat_entry["is_percentage"] = True
            new_stats.append(stat_entry)
        item_data["stats"] = new_stats


        # Dice Roll Effects
        new_dice_effects = []
        for r in range(self.dice_effects_table.rowCount()):
            effect_type = self.dice_effects_table.item(r,0).text()
            dice_notation = self.dice_effects_table.item(r,1).text()
            description = self.dice_effects_table.item(r,2).text()
            effect_entry = {"effect_type": effect_type, "dice_notation": dice_notation}
            if description: effect_entry["description"] = description
            new_dice_effects.append(effect_entry)
        item_data["dice_roll_effects"] = new_dice_effects


        item_data["tags"] = [t.strip() for t in self.tags_edit.text().split(',') if t.strip()]

        try:
            custom_props_str = self.custom_props_edit.toPlainText().strip()
            if custom_props_str:
                item_data["custom_properties"] = json.loads(custom_props_str)
            elif "custom_properties" in item_data: # If empty string, remove the key
                del item_data["custom_properties"]
        except json.JSONDecodeError:
            QMessageBox.warning(self, "JSON Error", "Invalid JSON in Custom Properties. Changes not saved for this field.")
            # Optionally, don't save the custom_properties part or revert to original
            # For now, it will keep the old value if new is invalid and save_json doesn't crash

    def _clear_details(self):
        self.id_edit.clear()
        self.name_edit.clear()
        self.description_edit.clear()
        self.item_type_combo.setCurrentIndex(0)
        self.rarity_combo.setCurrentIndex(0)
        self.weight_spin.setValue(0.0)
        self.value_spin.setValue(0)
        self.is_equippable_check.setChecked(False)
        self.is_consumable_check.setChecked(False)
        self.is_stackable_check.setChecked(False)
        self.is_quest_item_check.setChecked(False)
        self.equip_slots_edit.clear()
        self.stack_limit_spin.setValue(1)
        self.durability_spin.setValue(0)
        self.current_durability_spin.setValue(0)
        self.stats_table.setRowCount(0)
        self.dice_effects_table.setRowCount(0)
        self.tags_edit.clear()
        self.custom_props_edit.clear()
        self._update_conditional_field_visibility()


    def _set_details_enabled(self, enabled: bool):
        for i in range(self.details_form_layout.rowCount()):
            widget_item = self.details_form_layout.itemAt(i, QFormLayout.FieldRole)
            if widget_item and widget_item.widget():
                widget_item.widget().setEnabled(enabled)
            # Also enable labels if needed, though usually they are just for display
            # label_item = self.details_form_layout.itemAt(i, QFormLayout.LabelRole)
            # if label_item and label_item.widget():
            #     label_item.widget().setEnabled(enabled)
        self.id_edit.setEnabled(enabled) # Ensure ID can be edited when an item is selected
        if not enabled:
            self.id_edit.setReadOnly(True) # Read-only if no item selected
        else:
            self.id_edit.setReadOnly(False) # Editable if item selected

        self.save_item_button.setEnabled(enabled)
        if enabled:
            self._update_conditional_field_visibility()
        else: # Hide conditional fields if no item is selected
            self.details_form_layout.labelForField(self.equip_slots_edit).setVisible(False)
            self.equip_slots_edit.setVisible(False)
            self.details_form_layout.labelForField(self.stack_limit_spin).setVisible(False)
            self.stack_limit_spin.setVisible(False)


    def _update_conditional_field_visibility(self):
        """Show/hide fields based on checkbox states."""
        is_equippable = self.is_equippable_check.isChecked()
        self.details_form_layout.labelForField(self.equip_slots_edit).setVisible(is_equippable)
        self.equip_slots_edit.setVisible(is_equippable)

        is_stackable = self.is_stackable_check.isChecked()
        self.details_form_layout.labelForField(self.stack_limit_spin).setVisible(is_stackable)
        self.stack_limit_spin.setVisible(is_stackable)

    @Slot()
    def _add_item_stat(self):
        dialog = ItemStatDialog(self)
        if dialog.exec() == QDialog.Accepted:
            stat_data = dialog.get_stat_data()
            if stat_data:
                row_pos = self.stats_table.rowCount()
                self.stats_table.insertRow(row_pos)
                self.stats_table.setItem(row_pos, 0, QTableWidgetItem(stat_data["name"]))
                self.stats_table.setItem(row_pos, 1, QTableWidgetItem(str(stat_data["value"])))
                self.stats_table.setItem(row_pos, 2, QTableWidgetItem(stat_data.get("display_name", "")))
                self.stats_table.item(row_pos,0).setData(Qt.UserRole, stat_data) # Store for editing
                self.data_modified.emit()


    @Slot()
    def _remove_item_stat(self):
        current_row = self.stats_table.currentRow()
        if current_row >= 0:
            self.stats_table.removeRow(current_row)
            self.data_modified.emit()

    @Slot()
    def _add_dice_effect(self):
        dialog = DiceRollEffectDialog(self, effect_types=getattr(self, "_effect_types", None))
        if dialog.exec() == QDialog.Accepted:
            effect_data = dialog.get_effect_data()
            if effect_data:
                row_pos = self.dice_effects_table.rowCount()
                self.dice_effects_table.insertRow(row_pos)
                self.dice_effects_table.setItem(row_pos, 0, QTableWidgetItem(effect_data["effect_type"]))
                self.dice_effects_table.setItem(row_pos, 1, QTableWidgetItem(effect_data["dice_notation"]))
                self.dice_effects_table.setItem(row_pos, 2, QTableWidgetItem(effect_data.get("description", "")))
                self.dice_effects_table.item(row_pos,0).setData(Qt.UserRole, effect_data)
                self.data_modified.emit()

    @Slot()
    def _remove_dice_effect(self):
        current_row = self.dice_effects_table.currentRow()
        if current_row >= 0:
            self.dice_effects_table.removeRow(current_row)
            self.data_modified.emit()

    def refresh_data(self):
        """Public method to reload data from file."""
        self.load_data()
        # If an item was selected, try to reselect it or select first.
        if self.current_item_index is not None and self.current_item_index < self.item_list_widget.count():
            self.item_list_widget.setCurrentRow(self.current_item_index)
        elif self.item_list_widget.count() > 0:
            self.item_list_widget.setCurrentRow(0)
        else:
            self._clear_details()
            self._set_details_enabled(False)