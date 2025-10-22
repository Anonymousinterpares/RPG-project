#!/usr/bin/env python3
"""
MusicDirector: authoritative orchestrator for music state.
- Maintains mood/intensity/mute/volume state
- Selects tracks per mood (folder-based) with rotation fairness
- Applies transitions via the desktop backend (if present)
- Notifies listeners (e.g., web server) of state changes

This v1 focuses on core flow for Milestone 1. Advanced features (stingers, layers,
loudness normalization manifests) are stubbed and safe to ignore if absent.
"""
from __future__ import annotations
import os
import random
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.utils.logging_config import get_logger
logger = get_logger("MUSIC_DIRECTOR")

ALLOWED_EXTS = {".mp3", ".ogg", ".wav", ".flac"}

class MusicDirector:
    def __init__(self, project_root: Optional[str] = None):
        self._lock = threading.RLock()
        self._listeners: List[Callable[[Dict], None]] = []
        self._backend = None  # type: ignore
        self._project_root = Path(project_root or os.getcwd())
        # State
        self._mood: str = "ambient"
        self._intensity: float = 0.3
        self._muted: bool = False
        self._master: int = 100
        self._music: int = 100
        self._effects: int = 100
        self._current_track: Optional[str] = None  # absolute path (desktop)
        self._rotation: Dict[str, List[str]] = {}
        self._played: Dict[str, set] = {}
        # Manifest metadata per mood: { mood: { abs_path: {weight: float, tags: set[str], loudness_offset_db: float} } }
        self._track_meta: Dict[str, Dict[str, Dict]] = {}
        # Suggestion policy
        self._suggest_threshold: float = 0.7
        self._mood_cooldown_s: float = 5.0
        self._last_mood_change_ts: float = 0.0
        self._intensity_alpha: float = 0.35  # EMA smoothing
        self._intensity_ema: float = self._intensity
        self._jumpscare_thread: Optional[threading.Thread] = None
        self._jumpscare_active: bool = False
        # Lightweight context (Phase B): accept multiple tags for selection bias
        self._context: Dict[str, Optional[str]] = {
            "location_major": None,
            "location_venue": None,
            "weather_type": None,
            "time_of_day": None,
            "biome": None,
            "region": None,
            "interior": None,       # bool → represented as 'interior' token if True
            "underground": None,    # bool → represented as 'underground' token if True
            "crowd_level": None,
            "danger_level": None,
        }
        self._context_bias_enabled: bool = True
        # Debounce very rapid context changes to avoid jitter (ms window)
        self._last_context_change_ts: float = 0.0
        self._min_context_change_interval_s: float = 0.2
        # Scan once on init
        try:
            self._scan_tracks()
        except Exception as e:
            logger.warning(f"Music scan failed: {e}")

    # --- Public API ---
    def set_backend(self, backend) -> None:
        with self._lock:
            self._backend = backend
            # ensure current volumes/mute are applied
            if self._backend:
                self._backend.set_volumes(self._master, self._music, self._effects, self._muted)

    # --- Phase A/B: context API (accepts multiple fields) ---
    def set_context(self, location_major: Optional[str] = None, **kwargs) -> None:
        """Update lightweight context used for selection bias.
        Accepts: location_major, location_venue, weather_type, time_of_day, biome, region, interior, underground, crowd_level, danger_level.
        """
        with self._lock:
            updated = False
            if location_major is not None:
                val = str(location_major).strip().lower() or None
                if self._context.get("location_major") != val:
                    self._context["location_major"] = val
                    updated = True
            # Merge any other provided keys as-is (lowercased for strings)
            for k, v in (kwargs or {}).items():
                key = str(k)
                new_val = v
                try:
                    if isinstance(v, str):
                        new_val = v.strip().lower() or None
                except Exception:
                    pass
                if self._context.get(key) != new_val:
                    self._context[key] = new_val
                    updated = True
            # Debounce jitter
            now = time.time()
            if updated and (now - self._last_context_change_ts) < self._min_context_change_interval_s:
                return
            if updated:
                self._last_context_change_ts = now
                try:
                    get_logger("GAME").info("LOCATION_MGMT: director.set_context updated keys=%s", list({k for k in (['location_major'] if location_major is not None else [])} | set(kwargs.keys())))
                except Exception:
                    pass
                self._emit_state_locked(reason="context_changed")

    def set_volumes(self, master: int, music: int, effects: int) -> None:
        with self._lock:
            self._master = max(0, min(100, int(master)))
            self._music = max(0, min(100, int(music)))
            self._effects = max(0, min(100, int(effects)))
            if self._backend:
                self._backend.set_volumes(self._master, self._music, self._effects, self._muted)
            self._emit_state_locked(reason="volumes_changed")

    def set_muted(self, muted: bool) -> None:
        with self._lock:
            self._muted = bool(muted)
            if self._backend:
                self._backend.set_volumes(self._master, self._music, self._effects, self._muted)
            self._emit_state_locked(reason="muted_changed")

    def hard_set(self, mood: str, intensity: Optional[float] = None, reason: str = "") -> None:
        with self._lock:
            self._mood = (mood or "ambient").lower()
            if intensity is not None:
                self._intensity = float(max(0.0, min(1.0, intensity)))
            track = self._select_next_track_locked(self._mood)
            self._apply_locked(track, reason or "hard_set")

    def suggest(self, mood: str, intensity: float, source: str, confidence: float, evidence: str = "") -> None:
        """Apply an LLM or system suggestion with policy (threshold/cooldown) and intensity smoothing."""
        with self._lock:
            prev_i = self._intensity
            # Validate intensity and update EMA
            if intensity is not None:
                try:
                    val = float(intensity)
                    self._intensity_ema = self._intensity_alpha * max(0.0, min(1.0, val)) + (1.0 - self._intensity_alpha) * self._intensity_ema
                    self._intensity = self._intensity_ema
                except Exception:
                    pass
            # Check acceptance policy for mood
            now = time.time()
            accepted_reason = None
            if mood:
                try:
                    mood_l = str(mood).lower()
                except Exception:
                    mood_l = self._mood
                # Accept only if confidence and cooldown satisfied
                if (confidence is None) or (float(confidence) < self._suggest_threshold):
                    accepted_reason = None
                else:
                    if (now - self._last_mood_change_ts) >= self._mood_cooldown_s and mood_l and mood_l != self._mood:
                        self._mood = mood_l
                        self._last_mood_change_ts = now
                        accepted_reason = f"suggest:{source}:{confidence:.2f}"
            # Choose next track if mood changed or if no current track
            track = None
            if accepted_reason is not None or self._current_track is None:
                track = self._select_next_track_locked(self._mood, force_unplayed=True)
            # Apply if mood changed; otherwise only emit updated state (intensity smoothing)
            if track:
                self._apply_locked(track, accepted_reason or f"suggest:{source}:{confidence:.2f}")
            else:
                # If only intensity changed, reflect it in backend immediately with a short ramp
                if self._backend and abs(self._intensity - prev_i) > 1e-3:
                    try:
                        self._backend.set_intensity(self._intensity, ramp_ms=250)
                    except Exception:
                        pass
                self._emit_state_locked(reason=accepted_reason or f"intensity_update:{source}")

    def next_track(self, reason: str = "user_skip") -> None:
        with self._lock:
            track = self._select_next_track_locked(self._mood, force_unplayed=True)
            self._apply_locked(track, reason)

    def add_state_listener(self, callback: Callable[[Dict], None]) -> None:
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def list_moods(self) -> List[str]:
        """Return available mood names discovered from folders (sorted)."""
        try:
            return sorted(list(self._rotation.keys()))
        except Exception:
            return []

    def _load_manifest_for_mood(self, mood_dir: Path) -> Optional[Dict[str, Dict]]:
        """Load optional manifest (YAML or JSON) for a mood directory.
        Returns mapping { abs_path: {weight, tags, loudness_offset_db} } or None.
        """
        manifest = None
        try:
            yml = mood_dir / "manifest.yaml"
            js = mood_dir / "manifest.json"
            data = None
            if yml.exists():
                try:
                    import yaml  # type: ignore
                    with yml.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                except Exception:
                    data = None
            if data is None and js.exists():
                try:
                    import json as _json
                    with js.open("r", encoding="utf-8") as f:
                        data = _json.load(f)
                except Exception:
                    data = None
            if not isinstance(data, dict):
                return None
            tracks = data.get("tracks") or []
            out: Dict[str, Dict] = {}
            for t in tracks:
                try:
                    rel = t.get("file")
                    if not isinstance(rel, str):
                        continue
                    abs_p = str((mood_dir / rel).resolve())
                    meta = {
                        "weight": float(t.get("weight", 1.0)),
                        "tags": list(t.get("tags", []) or []),
                        "loudness_offset_db": float(t.get("loudness_offset_db", 0.0)),
                    }
                    out[abs_p] = meta
                except Exception:
                    continue
            return out
        except Exception:
            return None

    def current_state(self) -> Dict:
        """Return a snapshot of current music state (for debug/API)."""
        with self._lock:
            return {
                "mood": self._mood,
                "intensity": self._intensity,
                "track": os.path.basename(self._current_track) if self._current_track else None,
                "url": self._to_web_url(self._current_track),
                "muted": self._muted,
                "master": self._master,
                "music": self._music,
                "effects": self._effects,
                "context": dict(self._context),
            }

    # --- Internals ---
    def _scan_tracks(self) -> None:
        base = (self._project_root / "sound" / "music")
        if not base.exists():
            logger.info(f"No sound/music directory at {base}")
            return
        for mood_dir in base.iterdir():
            if not mood_dir.is_dir():
                continue
            mood = mood_dir.name.lower()
            files: List[str] = []
            for p in mood_dir.iterdir():
                if p.is_file() and p.suffix.lower() in ALLOWED_EXTS:
                    files.append(str(p.resolve()))
            files.sort()
            self._rotation[mood] = files
            self._played[mood] = set()
            # Try to load manifest metadata for weighting/tags
            self._track_meta[mood] = self._load_manifest_for_mood(mood_dir) or {}
        logger.info(f"MusicDirector scanned moods: {list(self._rotation.keys())}")

    def _select_next_track_locked(self, mood: str, force_unplayed: bool = False) -> Optional[str]:
        pool = self._rotation.get(mood) or []
        if not pool:
            # no tracks for this mood; keep current
            return self._current_track
        # compute unplayed set
        unplayed = [p for p in pool if p not in self._played.get(mood, set())]
        if not unplayed:
            # reset rotation
            self._played[mood] = set()
            unplayed = pool[:]
        # If forcing unplayed to change track, remove current from candidates if possible
        candidates = unplayed if force_unplayed else pool
        if self._current_track in candidates and len(candidates) > 1:
            candidates = [c for c in candidates if c != self._current_track]
        # Context bias: combine manifest weights + tag matches + filename tokens into weighted choice
        ctx = {k: v for k, v in self._context.items() if v}
        def _context_tokens() -> List[str]:
            toks: List[str] = []
            for key in ("location_major","location_venue","weather_type","time_of_day","biome","crowd_level","danger_level","region"):
                val = ctx.get(key)
                if isinstance(val, str) and val:
                    toks.append(val.lower())
            if ctx.get("interior") is True:
                toks.append("interior")
            if ctx.get("underground") is True:
                toks.append("underground")
            return toks
        tokens = _context_tokens()
        meta = self._track_meta.get(mood, {})
        def _weight_for(path: str) -> float:
            base = os.path.basename(path).lower()
            m = meta.get(path) or {}
            w = float(m.get("weight", 1.0))
            # Manifest tags
            try:
                tags = set([str(t).lower() for t in (m.get("tags") or [])])
            except Exception:
                tags = set()
            tag_matches = len(tags.intersection(tokens)) if tags else 0
            # Filename token bias
            filename_matches = sum(1 for t in tokens if t in base)
            return max(0.01, w) * (1.0 + 0.75 * tag_matches) * (1.0 + 0.25 * filename_matches)
        try:
            weights = [_weight_for(p) for p in candidates]
            total = sum(weights)
            if total <= 0:
                choice = random.choice(candidates)
            else:
                r = random.random() * total
                acc = 0.0
                choice = candidates[-1]
                for p, w in zip(candidates, weights):
                    acc += w
                    if r <= acc:
                        choice = p
                        break
        except Exception:
            choice = random.choice(candidates)
        if choice:
            self._played[mood].add(choice)
        return choice

    def _apply_locked(self, track: Optional[str], reason: str) -> None:
        # Apply to backend (desktop)
        # Crossfade duration may vary slightly by intensity (higher intensity → faster)
        try:
            # Map intensity 0..1 to fade 3000..800 ms
            i = max(0.0, min(1.0, float(self._intensity)))
            cf_ms = int(3000 - (2200 * i))
            cf_ms = max(400, min(4000, cf_ms))
        except Exception:
            cf_ms = 3000
        # Attach loudness offset if manifest provides one
        lou_db = 0.0
        try:
            lou_db = float((self._track_meta.get(self._mood, {}) or {}).get(track or "", {}).get("loudness_offset_db", 0.0))
        except Exception:
            lou_db = 0.0
        transition = {"crossfade_ms": cf_ms, "loudness_offset_db": lou_db}
        if self._backend:
            try:
                self._backend.apply_state(self._mood, self._intensity, track, transition)
            except Exception as e:
                logger.warning(f"Backend apply_state failed: {e}")
        # Update current and notify
        self._current_track = track or self._current_track
        self._emit_state_locked(reason=reason)

    def _emit_state_locked(self, reason: str) -> None:
        payload = {
            "mood": self._mood,
            "intensity": self._intensity,
            "track": os.path.basename(self._current_track) if self._current_track else None,
            "track_path": self._current_track,
            # web URL (if file is under sound/): replace project_root with /sound
            "url": self._to_web_url(self._current_track),
            "muted": self._muted,
            "master": self._master,
            "music": self._music,
            "effects": self._effects,
            "reason": reason,
        }
        for cb in list(self._listeners):
            try:
                cb(payload)
            except Exception as e:
                logger.debug(f"MusicDirector listener error: {e}")

    # --- Public UX helpers ---
    def jumpscare(self, peak: float = 1.0, attack_ms: int = 60, hold_ms: int = 150, release_ms: int = 800) -> None:
        """Trigger a quick intensity spike (attack/hold/release). Emits state with reasons so web can ramp appropriately.
        Non-blocking: runs release in a small thread. Backend ramps are handled via set_intensity.
        """
        def _worker(prev_i: float, p: float, a_ms: int, h_ms: int, r_ms: int):
            try:
                with self._lock:
                    # Attack: set to peak quickly
                    self._intensity = max(0.0, min(1.0, float(p)))
                    self._intensity_ema = self._intensity
                    if self._backend:
                        try:
                            self._backend.set_intensity(self._intensity, ramp_ms=max(0, int(a_ms)))
                        except Exception:
                            pass
                    self._emit_state_locked(reason="jumpscare_attack")
                # Hold
                time.sleep(max(0, int(h_ms)) / 1000.0)
                # Release: back to previous intensity with release ramp
                with self._lock:
                    self._intensity = max(0.0, min(1.0, float(prev_i)))
                    self._intensity_ema = self._intensity
                    if self._backend:
                        try:
                            self._backend.set_intensity(self._intensity, ramp_ms=max(0, int(r_ms)))
                        except Exception:
                            pass
                    self._emit_state_locked(reason="jumpscare_release")
            finally:
                with self._lock:
                    self._jumpscare_active = False

        with self._lock:
            if self._jumpscare_active:
                # Ignore if a jumpscare is currently active to avoid stacking
                return
            self._jumpscare_active = True
            prev = self._intensity
            t = threading.Thread(target=_worker, args=(prev, peak, attack_ms, hold_ms, release_ms), daemon=True)
            self._jumpscare_thread = t
            t.start()

    def _to_web_url(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        try:
            p = Path(path).resolve()
            base = (self._project_root / "sound").resolve()
            if str(p).startswith(str(base)):
                relative = p.relative_to(base)
                # web served under /sound
                return f"/sound/{relative.as_posix()}"
        except Exception:
            pass
        return None

# Convenience accessor for construction elsewhere if desired
_director_singleton: Optional[MusicDirector] = None

def get_music_director(project_root: Optional[str] = None) -> MusicDirector:
    global _director_singleton
    if _director_singleton is None:
        _director_singleton = MusicDirector(project_root=project_root)
    return _director_singleton

    # --- Reactive Helpers ---

    
