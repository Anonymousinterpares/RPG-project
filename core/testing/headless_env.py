import os
import sys
import json
import time
import random
from typing import Optional, List, Dict, Any

from PySide6.QtCore import QCoreApplication, QTimer, QObject, Slot

from core.base.engine import get_game_engine

# We intentionally import these lazily in some methods to avoid early side effects

class HeadlessBootstrapError(Exception):
    pass


def bootstrap_headless(
    seed: Optional[int] = 42,
    llm_enabled: bool = False,
    tts_enabled: bool = False,
    combat_delay_ms: Optional[int] = 0,
    set_env_test: bool = True,
) -> Dict[str, Any]:
    """
    Initialize a headless Qt environment and a configured GameEngine instance.

    - Creates a QCoreApplication if not already present
    - Seeds RNG for determinism
    - Disables LLM (by default)
    - Disables TTS (by default) and sets orchestrator inter-step delay

    Returns a dict with {"app", "engine"}.
    """
    app = QCoreApplication.instance() or QCoreApplication([])

    if set_env_test:
        os.environ.setdefault("APP_ENV", "test")

    if isinstance(seed, int):
        random.seed(seed)

    engine = get_game_engine()

    # Register test-layer quest commands (no core modifications)
    try:
        from core.testing.quest_commands import register_quest_commands
        register_quest_commands()
    except Exception:
        pass

    # Configure engine features without touching logic
    try:
        engine.set_llm_enabled(bool(llm_enabled))
    except Exception:
        pass

    try:
        if hasattr(engine, "_tts_manager") and engine._tts_manager is not None:
            engine._tts_manager.is_enabled = bool(tts_enabled)
    except Exception:
        pass

    try:
        if hasattr(engine, "_combat_orchestrator") and engine._combat_orchestrator is not None:
            if combat_delay_ms is not None:
                engine._combat_orchestrator.config_delay_ms = int(combat_delay_ms)
    except Exception:
        pass

    return {"app": app, "engine": engine}


def run_in_qt_thread(func, delay_ms: int = 0, *args, **kwargs) -> None:
    """
    Schedule a callable to run on the Qt event loop after delay_ms.
    Useful for kicking off actions after the app is started.
    """
    def _wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            # In headless mode print to stderr to make failures visible
            sys.stderr.write(f"[HEADLESS] Exception in scheduled function: {e}\n")
            import traceback
            traceback.print_exc()
    QTimer.singleShot(max(0, int(delay_ms)), _wrapper)

