import sys
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QCoreApplication

from core.testing.headless_env import bootstrap_headless, run_in_qt_thread
from core.testing.headless_ui_listener import HeadlessUIListener
from core.base.engine import get_game_engine


def _start_game(engine, params: Dict[str, Any]) -> None:
    # Initialize a new game with minimal params; GUI normally collects these
    engine.start_new_game(
        player_name=params.get("player_name", "Player"),
        race=params.get("race", "Human"),
        path=params.get("path", "Wanderer"),
        background=params.get("background", "Commoner"),
        sex=params.get("sex", "Male"),
        character_image=None,
        stats=None,
        origin_id=params.get("origin_id")
    )


def _send_commands(engine, listener: HeadlessUIListener, commands: List[str], spacing_ms: int = 5):
    # Send commands with small spacing; orchestrator delay is already set to 0 by bootstrap
    from PySide6.QtCore import QTimer

    def schedule_command(i: int):
        if i >= len(commands):
            return
        cmd = (commands[i] or "").strip()
        if cmd:
            engine.process_input(cmd)
        # Schedule next
        QTimer.singleShot(spacing_ms, lambda: schedule_command(i + 1))

    schedule_command(0)


def run_scenario(params: Dict[str, Any], commands: List[str]) -> Dict[str, Any]:
    """
    Run a scenario headlessly and return a dict with transcript and structured events.
    params keys: player_name, race, path, background, sex, origin_id
    """
    ctx = bootstrap_headless(seed=params.get("seed", 42), llm_enabled=params.get("llm", False), tts_enabled=False, combat_delay_ms=0)
    app: QCoreApplication = ctx["app"]
    engine = ctx["engine"]

    listener = HeadlessUIListener(engine)

    # Start game after event loop starts
    run_in_qt_thread(_start_game, 0, engine, params)
    # Send commands shortly after
    run_in_qt_thread(_send_commands, 10, engine, listener, commands)

    # Quit when engine seems idle enough: we’ll set a conservative timeout
    # and rely on orchestrator’s zero-delay processing.
    from PySide6.QtCore import QTimer

    def stop_app():
        app.quit()

    timeout_ms = params.get("timeout_ms", 5000)
    QTimer.singleShot(timeout_ms, stop_app)

    # Run
    app.exec()

    return {"transcript": listener.dump_transcript(), "events": listener.events, "lines": listener.lines}

