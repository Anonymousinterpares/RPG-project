#!/usr/bin/env python3
from core.audio.sfx_manager import SFXManager

class DummyBackend:
    def __init__(self):
        self.calls = []
    def play_sfx(self, file_path, category: str):
        self.calls.append((category, file_path))


def test_sfx_on_context_change(monkeypatch):
    mgr = SFXManager(project_root=None)
    mgr.set_backend(DummyBackend())
    # Force path resolution to succeed
    monkeypatch.setattr(mgr, "_abs_path", lambda rel: "C:/dummy/path.wav")
    # Venue change triggers venue SFX
    ctx = {"location": {"venue": "tavern"}, "weather": {"type": None}}
    mgr.apply_context(ctx, changed_keys=["location.venue"])
    assert mgr._backend.calls and mgr._backend.calls[-1][0] == 'venue'
    # Weather change triggers weather SFX
    ctx2 = {"location": {}, "weather": {"type": "storm"}}
    mgr.apply_context(ctx2, changed_keys=["weather.type"])
    assert any(c[0] == 'weather' for c in mgr._backend.calls)
