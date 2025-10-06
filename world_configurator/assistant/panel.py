"""
Assistant dock widget.
"""
from __future__ import annotations

import json
import traceback
from typing import List, Optional

import logging
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTextEdit, QPushButton, QTabWidget, QPlainTextEdit, QMessageBox
)

from .context import AssistantContext, PatchOp, AssistantContextProvider
from .prompt_builder import build_messages, build_messages_analyze
from llm.client_base import OpenAILikeClient
from llm.settings import load_llm_settings


logger = logging.getLogger("world_configurator.ui.assistant")

class _Worker(QObject):
    finished = Signal(dict, str)
    failed = Signal(str)

    def __init__(self, mode: str, ctx: AssistantContext, user_text: str, messages: Optional[List[dict]] = None) -> None:
        super().__init__()
        self.mode = mode
        self.ctx = ctx
        self.user_text = user_text
        self._messages = messages

    def run(self) -> None:
        try:
            settings = load_llm_settings()
            if not settings.api_key or not settings.model or not settings.provider:
                self.failed.emit("LLM settings incomplete. Please set provider, model, and API key in Settings.")
                return
            messages = self._messages if self._messages is not None else build_messages(self.mode, self.ctx, self.user_text)
            prov = (settings.provider or '').lower()
            if prov.startswith('google') or prov == 'gemini':
                from llm.gemini import GeminiClient
                client = GeminiClient()
            else:
                client = OpenAILikeClient()
            resp = client.send(messages, settings)
            self.finished.emit(resp, "")
        except Exception as e:
            # Log full details to file, emit concise message to UI
            logger.error("Assistant worker error: %s", e, exc_info=True)
            self.failed.emit("Provider request failed. See logs for details.")


class AssistantDock(QDockWidget):
    def __init__(self, parent=None, get_provider_cb=None) -> None:
        super().__init__("Assistant", parent)
        # Make persistent (no close/maximize/floating controls)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self._get_provider_cb = get_provider_cb  # function returning AssistantContextProvider or None

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)

        # Mode selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Analyze", "Modify", "Create"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # User input
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Ask for analysis, suggest changes, or describe a new entry to create…")
        layout.addWidget(self.input_edit)

        # Action buttons
        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear)
        self.reset_conv_btn = QPushButton("Reset conversation")
        self.reset_conv_btn.clicked.connect(self._on_reset_conversation)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        btn_row.addStretch()
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.reset_conv_btn)
        btn_row.addWidget(self.send_btn)
        layout.addLayout(btn_row)

        # Results tabs
        self.tabs = QTabWidget()
        self.analysis_out = QPlainTextEdit(); self.analysis_out.setReadOnly(True)
        self.patch_out = QPlainTextEdit(); self.patch_out.setReadOnly(True)
        self.entry_out = QPlainTextEdit(); self.entry_out.setReadOnly(True)
        self.tabs.addTab(self.analysis_out, "Analysis")
        self.tabs.addTab(self.patch_out, "Patch")
        self.tabs.addTab(self.entry_out, "New Entry")
        layout.addWidget(self.tabs)

        # Apply buttons
        apply_row = QHBoxLayout()
        self.apply_patch_btn = QPushButton("Apply Patch")
        self.apply_patch_btn.clicked.connect(self._apply_patch)
        self.apply_patch_btn.setEnabled(False)
        self.create_entry_btn = QPushButton("Create Entry")
        self.create_entry_btn.clicked.connect(self._create_entry)
        self.create_entry_btn.setEnabled(False)
        apply_row.addWidget(self.apply_patch_btn)
        apply_row.addWidget(self.create_entry_btn)
        layout.addLayout(apply_row)

        self._last_patch: Optional[List[PatchOp]] = None
        self._last_entry: Optional[dict] = None

        # Analyze conversation threading: per (domain, selection_id)
        self._analyze_threads: dict = {}
        self._last_run_mode: Optional[str] = None
        self._last_run_key: Optional[tuple] = None
        self._last_user_text: Optional[str] = None

    def _active_provider(self) -> Optional[AssistantContextProvider]:
        return self._get_provider_cb() if self._get_provider_cb else None

    def _on_send(self) -> None:
        provider = self._active_provider()
        if provider is None:
            QMessageBox.warning(self, "No Active Editor", "Select an editor tab that supports the assistant.")
            return
        mode = self.mode_combo.currentText().lower()
        ctx = provider.get_assistant_context()
        # Always provide references to improve grounding
        try:
            ctx.references = provider.get_reference_catalogs()
        except Exception:
            ctx.references = ctx.references or None
        user_text = self.input_edit.toPlainText()
        messages: Optional[List[dict]] = None

        # On-demand targeted search: if user types "search: <term>", try to focus or attach results.
        try:
            low = (user_text or "").strip().lower()
            if low.startswith("search:") and hasattr(provider, "search_for_entries"):
                term = user_text.split(":", 1)[1].strip() if ":" in user_text else ""
                matches = provider.search_for_entries(term) if term else []
                if len(matches) == 1 and hasattr(provider, "focus_entry"):
                    # Auto-focus the only match and refresh context/references
                    provider.focus_entry(matches[0][0])
                    ctx = provider.get_assistant_context()
                    try:
                        ctx.references = provider.get_reference_catalogs()
                    except Exception:
                        pass
                elif len(matches) > 1:
                    # Attach compact results to references for LLM grounding and user visibility
                    refs = ctx.references or {}
                    refs = dict(refs)
                    refs["search_results"] = [{"id": mid, "name": mname, "score": score} for (mid, mname, score) in matches[:10]]
                    ctx.references = refs
        except Exception:
            # Best effort; proceed with normal flow
            pass

        # Heuristic: if user asks to "create/add/generate" N, force create mode for this send
        try:
            import re
            lowtxt = (user_text or "").strip().lower()
            m = re.search(r"\b(create|add|generate)\s+(\d+)\b", lowtxt)
            if m and mode != "create":
                mode = "create"
        except Exception:
            pass

        # For create mode, attach exemplar and clear selection context
        if mode == "create":
            examples = provider.get_domain_examples()
            ctx.exemplars = examples[:1] if examples else None
            ctx.selection_id = None
            ctx.content = None
            messages = build_messages(mode, ctx, user_text)
            self._last_run_mode = None
            self._last_run_key = None
            self._last_user_text = None
        elif mode == "modify":
            messages = build_messages(mode, ctx, user_text)
            self._last_run_mode = None
            self._last_run_key = None
            self._last_user_text = None
        else:  # analyze with threading
            key = (ctx.domain, ctx.selection_id)
            history = self._analyze_threads.get(key, [])
            messages = build_messages_analyze(history, ctx, user_text, lean=True)
            self._last_run_mode = "analyze"
            self._last_run_key = key
            self._last_user_text = user_text
            # Update tab label to reflect current history count immediately
            self._update_analysis_tab_label(len(history))
        self._run_worker(mode, ctx, user_text, messages=messages)

    def _run_worker(self, mode: str, ctx: AssistantContext, user_text: str, messages: Optional[List[dict]] = None) -> None:
        self.send_btn.setEnabled(False)
        self.apply_patch_btn.setEnabled(False)
        self.create_entry_btn.setEnabled(False)
        self.analysis_out.clear(); self.patch_out.clear(); self.entry_out.clear()
        self._last_patch = None; self._last_entry = None

        self._thread = QThread(self)
        self._worker = _Worker(mode, ctx, user_text, messages=messages)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.failed.connect(self._on_worker_fail)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.start()

    def _on_worker_done(self, data: dict, _msg: str) -> None:
        self.send_btn.setEnabled(True)
        # Route by intent
        intent = data.get("intent")
        if intent == "analyze":
            self.tabs.setCurrentIndex(0)
            analysis = data.get("analysis")
            recs = data.get("recommendations", [])
            text = self._sanitize_text(analysis if isinstance(analysis, str) else "")
            if not text and isinstance(data.get("raw"), str):
                text = self._sanitize_text(data.get("raw"))
            if not text:
                # fallback: pretty-print whatever came
                text = json.dumps(data, indent=2, ensure_ascii=False)
            if recs:
                text = text + ("\n\nRecommendations:\n- " + "\n- ".join(recs))
            self.analysis_out.setPlainText(text)
            # Append to analyze history if applicable
            if self._last_run_mode == "analyze" and self._last_run_key is not None and self._last_user_text:
                self._append_analyze_history(self._last_run_key, self._last_user_text, text)
            # optional patch
            if isinstance(data.get("suggested_patch"), list):
                self.tabs.setCurrentIndex(1)
                self.patch_out.setPlainText(json.dumps(data["suggested_patch"], indent=2, ensure_ascii=False))
                self._try_parse_patch(data["suggested_patch"])  # enable apply if valid
        elif intent == "modify_selection":
            self.tabs.setCurrentIndex(1)
            self.patch_out.setPlainText(json.dumps(data.get("patch", []), indent=2, ensure_ascii=False))
            self._try_parse_patch(data.get("patch"))
        elif intent == "create_entry":
            self.tabs.setCurrentIndex(2)
            entry_obj = data.get("entry")
            # Support single object or list of objects for bulk creation
            try:
                self.entry_out.setPlainText(json.dumps(entry_obj, indent=2, ensure_ascii=False))
            except Exception:
                self.entry_out.setPlainText(str(entry_obj))
            self._last_entry = entry_obj if isinstance(entry_obj, (dict, list)) else None
            if isinstance(entry_obj, list):
                self.create_entry_btn.setText(f"Create {len(entry_obj)} Entries")
                self.create_entry_btn.setEnabled(len(entry_obj) > 0)
            else:
                self.create_entry_btn.setText("Create Entry")
                self.create_entry_btn.setEnabled(isinstance(entry_obj, dict))
        else:
            # Raw content fallback
            self.tabs.setCurrentIndex(0)
            raw = data.get("raw") if isinstance(data, dict) else None
            self.analysis_out.setPlainText(self._sanitize_text(raw if isinstance(raw, str) else json.dumps(data, indent=2, ensure_ascii=False)))

    def _on_worker_fail(self, err: str) -> None:
        self.send_btn.setEnabled(True)
        # Keep UI message short; details are in logs
        QMessageBox.critical(self, "Assistant Error", err)
        logger.error("Assistant error surfaced to UI: %s", err)

    def _try_parse_patch(self, patch_list_obj) -> None:
        try:
            if isinstance(patch_list_obj, list):
                ops: List[PatchOp] = []
                for item in patch_list_obj:
                    if isinstance(item, dict) and "op" in item and "path" in item:
                        ops.append(PatchOp(op=item["op"], path=item["path"], value=item.get("value")))
                if ops:
                    self._last_patch = ops
                    self.apply_patch_btn.setEnabled(True)
        except Exception:
            self._last_patch = None
            self.apply_patch_btn.setEnabled(False)

    def _apply_patch(self) -> None:
        if not self._last_patch:
            return
        provider = self._active_provider()
        if provider is None:
            return
        ok, msg = provider.apply_assistant_patch(self._last_patch)
        if ok:
            QMessageBox.information(self, "Patch Applied", "Changes applied successfully.")
            self.apply_patch_btn.setEnabled(False)
        else:
            QMessageBox.warning(self, "Patch Failed", msg)

    def _create_entry(self) -> None:
        if not self._last_entry:
            return
        provider = self._active_provider()
        if provider is None:
            return
        # Handle bulk list or single dict
        if isinstance(self._last_entry, list):
            created = 0; failed = 0
            for e in self._last_entry:
                if not isinstance(e, dict):
                    failed += 1
                    continue
                ok, msg, new_id = provider.create_entry_from_llm(e)
                if ok:
                    created += 1
                else:
                    failed += 1
            QMessageBox.information(self, "Bulk Create", f"Created: {created}, Failed: {failed}")
            self.create_entry_btn.setEnabled(False)
        else:
            ok, msg, new_id = provider.create_entry_from_llm(self._last_entry)
            if ok:
                QMessageBox.information(self, "Entry Created", f"Created new entry with id: {new_id}")
                self.create_entry_btn.setEnabled(False)
            else:
                QMessageBox.warning(self, "Creation Failed", msg)

    def _on_clear(self) -> None:
        self.input_edit.clear()
        self.analysis_out.clear()
        self.patch_out.clear()
        self.entry_out.clear()
        self.apply_patch_btn.setEnabled(False)
        self.create_entry_btn.setEnabled(False)
        self._last_patch = None
        self._last_entry = None
        # Do not touch analyze history. Label remains as-is.

    def _sanitize_text(self, s: str) -> str:
        if not s:
            return ""
        # Strip common code fences
        if s.strip().startswith("```"):
            lines = [ln for ln in s.splitlines() if not ln.strip().startswith("```")]
            s = "\n".join(lines).strip()
        # If it's JSON-looking, try to flatten nicely
        st = s.strip()
        if (st.startswith("{") and st.endswith("}")) or (st.startswith("[") and st.endswith("]")):
            try:
                obj = json.loads(st)
                # If it looks like {analysis: ...}
                if isinstance(obj, dict) and "analysis" in obj and isinstance(obj["analysis"], str):
                    return obj["analysis"]
                return json.dumps(obj, indent=2, ensure_ascii=False)
            except Exception:
                pass
        return s

    def _on_reset_conversation(self) -> None:
        try:
            provider = self._active_provider()
            if provider is None:
                return
            ctx = provider.get_assistant_context()
            key = (ctx.domain, ctx.selection_id)
            if key in self._analyze_threads:
                del self._analyze_threads[key]
            self.analysis_out.clear()
            self._update_analysis_tab_label(0)
        except Exception:
            # Best-effort reset; keep UI responsive even if provider fails
            self.analysis_out.clear()
            self._update_analysis_tab_label(0)

    def _append_analyze_history(self, key: tuple, user_text: str, assistant_text: str) -> None:
        hist = list(self._analyze_threads.get(key, []))
        hist.append({"role": "user", "content": user_text})
        hist.append({"role": "assistant", "content": assistant_text})
        self._analyze_threads[key] = hist
        self._update_analysis_tab_label(len(hist))

    def _update_analysis_tab_label(self, message_count: int) -> None:
        idx = self.tabs.indexOf(self.analysis_out)
        if idx >= 0:
            label = "Analysis" if message_count <= 0 else f"Analysis ({message_count} messages)"
            self.tabs.setTabText(idx, label)

    def _on_mode_changed(self, text: str) -> None:
        if text and text.lower() == "analyze":
            try:
                provider = self._active_provider()
                if provider is None:
                    self._update_analysis_tab_label(0)
                    return
                ctx = provider.get_assistant_context()
                key = (ctx.domain, ctx.selection_id)
                hist = self._analyze_threads.get(key, [])
                self._update_analysis_tab_label(len(hist))
            except Exception:
                self._update_analysis_tab_label(0)

