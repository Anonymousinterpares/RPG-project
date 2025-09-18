import sys
import json
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal, Slot

# Note: This listener depends only on Engine/Orchestrator Qt signals. It does not import GUI.

class HeadlessUIListener(QObject):
    """
    Headless listener that captures Engine and Orchestrator outputs and
    acknowledges visual completion to advance the orchestrator queue.

    - Connect to engine.output_generated(str, str) to capture text outputs
    - Connect to engine.orchestrated_event_to_ui(object) to capture DisplayEvents
    - For DisplayEvents that normally wait for UI, we immediately call back
      to orchestrator._handle_visual_display_complete() to keep processing.
    """

    # Optional signal for external consumers (e.g., CLI) to observe new lines
    line_captured = Signal(str)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.events: List[Dict[str, Any]] = []   # structured capture of DisplayEvents
        self.lines: List[str] = []               # captured simple text lines (role: content)

        # Wire up signals
        # Text output
        try:
            self.engine.output_generated.connect(self._on_text_output)
        except Exception:
            pass
        # Orchestrated events
        try:
            self.engine.orchestrated_event_to_ui.connect(self._on_display_event)
        except Exception:
            pass

    @Slot(str, str)
    def _on_text_output(self, role: str, content: str) -> None:
        try:
            line = f"[{role}] {content}"
            self.lines.append(line)
            self.line_captured.emit(line)
        except Exception:
            pass

    @Slot(object)
    def _on_display_event(self, display_event_obj: object) -> None:
        """
        Receives DisplayEvent objects from engine/orchestrator and logs them.
        Immediately schedules a visual completion acknowledgement to unblock orchestrator.
        Using QTimer.singleShot(0, ...) avoids re-entrancy in orchestrator processing.
        """
        try:
            # Store a JSON-serializable summary
            try:
                from core.orchestration.events import DisplayEvent
                if isinstance(display_event_obj, DisplayEvent):
                    ser = {
                        "id": display_event_obj.event_id,
                        "type": getattr(display_event_obj.type, "name", str(display_event_obj.type)),
                        "target": getattr(display_event_obj.target_display, "name", str(display_event_obj.target_display)),
                        "tts": bool(getattr(display_event_obj, "tts_eligible", False)),
                        "gradual": bool(getattr(display_event_obj, "gradual_visual_display", False)),
                        "role": getattr(display_event_obj, "role", None),
                        "content": display_event_obj.content,
                        "metadata": display_event_obj.metadata,
                    }
                else:
                    ser = {"id": None, "type": str(type(display_event_obj)), "raw": str(display_event_obj)}
            except Exception:
                ser = {"id": None, "type": str(type(display_event_obj)), "raw": str(display_event_obj)}
            self.events.append(ser)

            # Schedule acknowledgement to avoid re-entrancy
            try:
                orch = getattr(self.engine, "_combat_orchestrator", None)
                if orch is not None and hasattr(orch, "_handle_visual_display_complete"):
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(0, orch._handle_visual_display_complete)
            except Exception:
                pass
        except Exception:
            pass

    def dump_transcript(self) -> str:
        """Return a human-friendly transcript of captured lines and events."""
        parts: List[str] = []
        # Basic text lines
        for line in self.lines:
            parts.append(line)
        # Orchestrated events
        for ev in self.events:
            t = ev.get("type", "?")
            tgt = ev.get("target", "?")
            c = ev.get("content")
            parts.append(f"<{t} -> {tgt}> {c}")
        return "\n".join(parts)

    def to_json(self) -> str:
        """Return a JSON dump of both events and lines for programmatic use."""
        payload = {"lines": self.lines, "events": self.events}
        try:
            return json.dumps(payload, ensure_ascii=False, indent=2)
        except Exception:
            return json.dumps({"error": "serialization_failed"})

