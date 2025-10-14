# Music & Sound System Implementation Checklist (LLM‑aware, dual‑GUI)

This checklist specifies a full, end‑to‑end implementation of a robust, LLM‑aware music and sound system for both the Python GUI (desktop) and the Web GUI, based on the agreed architecture:
- Music Director mediates all LLM suggestions and in‑game triggers
- Python backend: python‑vlc behind a clean MusicBackend interface
- Web backend: Web Audio API
- Continuous music playback (no “stop” concept); users can mute/unmute or skip to next track; LLM and Director can change tracks/moods
- Immediate but smooth music transitions (constant‑power fades) and immediate SFX (no fades) unless ducking
- Stingers and layers supported, with explicit fallbacks: if any stinger or next stage element is missing, continue current track uninterrupted
- Silence windows use gain ducking to zero instead of stopping playback

Use this document to drive work across multiple sessions without relying on persistent context.

---

## 0) Shared Principles and Constraints (accepted)
- Music is always “playing” in principle. We never depend on a “stopped” state. Muting/unmuting and track changes are supported. No explicit “stop” control in UI.
- Stingers/layers are supported but optional; if a stinger or layered element is missing, we DO NOT pause or restart. We continue the currently playing track.
- SFX are overlaid on music. Two categories:
  - Continuous (looping ambiences like crowd/market/wind)
  - Instantaneous (one‑shots like door open, sword swing, spell cast, monster growl)
- Transitions for music: immediate but smooth crossfades (constant‑power). SFX: immediate (no fade) unless ducking for TTS or dialogue.
- LLM suggestions are mediated by a Music Director. The Director enforces thresholds, hysteresis, cooldowns, etc. Game state events can hard‑set mood.
- Silence windows should not stop playback. Use gain ramp to zero (or a silent buffer) to maintain “playing” semantics while inaudible.

---

## 1) Directory Structure and Assets
[ ] Create or validate base directories under project root:
- sound/music/<mood>/
- sound/music/<mood>/manifest.yaml (optional but recommended for weights/metadata)
- Optional stingers per mood:
  - sound/music/<mood>/stingers/<event>/  (e.g., combat/stingers/start, combat/stingers/boss)
- Optional layers (advanced, later milestone):
  - sound/music/<mood>/layers/<stem_name>/ (e.g., layers/pad, layers/drums)
- SFX directories:
  - sound/sfx/continuous/<tag>/  (e.g., crowd, rain, wind)
  - sound/sfx/instant/<category>/  (e.g., ui, door, sword, bow, magic, monster)

Notes:
- Accepted audio formats: .mp3, .ogg, .wav
- No separate directories for intensity. Intensity is a scalar (0.0–1.0) used for weighting/selection, not path segregation.

---

## 2) Track Metadata Manifests (optional but recommended)
[ ] For each mood, author an optional manifest file sound/music/<mood>/manifest.yaml to normalize loudness, assign weights and tags, define loop points and other hints.

### Tagging guidance (to support context weighting)
- Recommended tags to include per track: [location_major, venue, weather, time_of_day, mood_flavor]
  - location_major examples: city, camp, forest, seaside, desert, mountain, swamp, dungeon, castle, village, port, temple, ruins
  - venue examples: tavern, market, blacksmith, inn, chapel, library, manor, arena, fireplace, bridge, tower, cave, farm
  - weather examples: clear, overcast, rain, storm, snow, blizzard, fog, windy, sandstorm
  - time_of_day (optional): dawn, day, dusk, night
- These tags are used by the Director to bias selection; do not multiply directories unnecessarily.

Example manifest keys:
- mood: "tension"
- default_intensity: 0.5
- tracks:
  - file: "edge_of_fog.mp3"
    weight: 1.0
    loudness_offset_db: -1.5
    tags: ["night", "outdoors"]
    min_play_seconds: 20
    loop_points: { start_sec: 0.0, end_sec: null }  # optional
  - file: "shadows_in_motion.ogg"
    weight: 0.8
    loudness_offset_db: -0.7
    tags: ["indoors"]

[ ] For stingers (optional): sound/music/<mood>/stingers/<event>/manifest.yaml
- event: "start" | "boss" | "victory" | ...
- tracks: [ { file, loudness_offset_db } ... ]

[ ] For SFX manifests (optional): sound/sfx/<type>/<category>/manifest.yaml for per‑sound volume offsets or concurrency limits

---

## 2A) Context Model (Location, Venue, Weather, Time of Day)
[ ] Define canonical enums and synonyms mapping (data-driven) for:
- location.major (top-level: city, forest, seaside, desert, mountain, dungeon, village, port, temple, ruins, camp, swamp, castle, etc.)
- location.venue (fine-grained: tavern, market, blacksmith, chapel, library, fireplace, arena, cave, inn, manor, farm, bridge, tower, etc.)
- weather.type (clear, overcast, rain, storm, snow, blizzard, fog, windy, sandstorm)
- time_of_day (optional for selection weighting: dawn, day, dusk, night)

[ ] Provide a synonyms map for each domain so LLM/world strings can be canonicalized (e.g., "town" → city, "pub" → tavern)
[ ] Persist current context in saves: location.major, location.venue, weather.type (and time_of_day if used)
[ ] Director uses context to bias track selection via manifest tags (no extra folders required)
[ ] Engine owns context; LLM may propose (optional) but engine canonicalizes and applies policy

Artifacts (proposed):
- config/audio/context_enums.json (canonical values)
- config/audio/context_synonyms.json (string → canonical)
- config/audio/sfx_mapping.json (Phase C; context → SFX tags)

---

## 3) Server (FastAPI) Enhancements for Web
[x] Mount static sound folder (serving audio to browser):
- app.mount("/sound", StaticFiles(directory=os.path.join(project_root, "sound")), name="sound")

[ ] Add GET /api/music/tracks endpoint (optional convenience; v1 can hardcode client tracks):
- Input: none
- Output JSON:
  - moods: { mood_name: ["/sound/music/<mood>/<file>", ...] }
  - stingers: { mood_name: { event: ["/sound/music/<mood>/stingers/<event>/<file>", ...] } }
  - sfx: {
      continuous: { tag: ["/sound/sfx/continuous/<tag>/<file>", ...] },
      instant: { category: ["/sound/sfx/instant/<cat>/<file>", ...] }
    }
- Notes:
  - Prevent path traversal
  - Filter by allowed extensions

[x] WebSocket events (augment existing WS broadcast):
- type: "music_state"
  - data: { mood, intensity, track, ts }
- type: "music_settings" (optional)
  - data: { enabled, master, music, effects, muted }
- type: "music_debug" (optional dev)
  - data: { reason, source, confidence, applied: bool }

[ ] Optional GET /api/music/state (debug): returns current Director state

[ ] Security & perf:
- Ensure CORS consistent (already permissive)
- Limit payload sizes
- Validate files exist before listing

---

## 4) Music Director (Python, authoritative brain)
[x] Create module: core/music/director.py

Context integration (Phase A scope):
[ ] Accept and store context fields (location.major, location.venue, weather.type, time_of_day?)
[ ] Expose set_context(...) or accept context via game state updates; canonicalize via synonyms config
[ ] Weight track selection by matching manifest tags to current context (soft bias, not hard filter)
[ ] Persist context in saves and restore on load

Responsibilities:
- Holds canonical state: { mood, intensity [0..1], current_track, last_change_ts, muted }
- Merges inputs from:
  - Engine events (hard_set): combat start/end, location changes
  - LLM suggestions (with confidence)
  - User overrides (dev/debug)
- Enforces policy:
  - Confidence threshold for LLM suggestions (e.g., 0.7)
  - Hysteresis to avoid oscillation (mood cooldown window, e.g., 4–6 seconds)
  - Intensity smoothing (e.g., EMA) allows frequent small adjustments without jarring track changes
  - Jumpscare helper: attack/hold/release spike to peak intensity with explicit WS reason so clients ramp appropriately
- Owns selection logic:
  - Track rotation per mood with fairness: no repeats until all have played (unless <2 tracks)
  - Weighting by manifest and tags (optional)
  - Loudness normalization: per‑track offset applied downstream
- Transition orchestration:
  - Immediate but smooth crossfades (constant‑power)
  - Stingers if available; if missing, DO NOT pause/restart. Continue current base track
  - Silence windows by ramping music gain to zero (no stop)
- Broadcast updated state to:
  - Python MusicBackend (direct calls)
  - Web via WS: music_state

Public API (suggested):
[ ] def suggest(self, mood: str, intensity: float, source: str, confidence: float, evidence: str = "") -> None
[x] def hard_set(self, mood: str, intensity: float | None = None, reason: str = "") -> None
[x] def set_muted(self, muted: bool) -> None  # reflect UI or settings
[x] def next_track(self, reason: str = "") -> None  # user skip
[x] def set_volumes(self, master: int, music: int, effects: int) -> None
[ ] def current_state(self) -> dict

Implementation details:
[ ] Confidence/hysteresis:
- Only apply LLM mood change if confidence >= threshold and mood cooldown passed
- Always allow engine hard_set
- Allow intensity changes more often than moods (no cooldown or a shorter one)

[ ] Selection policy:
- Maintain per‑mood rotation set and played set
- If manifest weights exist, use weighted random on unplayed; reset when exhausted
- If mood has zero available tracks: fallback to continuing current track; schedule retry later (e.g., at next crossfade)

[ ] Stinger policy:
- On entering new mood, attempt stinger for the event (e.g., "start"). If not found, do nothing special; baseline music continues (no pause/restart)
- If found, play stinger over current music with ducking. After stinger, either fade in a track from the new mood or continue current track if no track exists in the new mood

[ ] Silence windows:
- Represent as either mood="silence" or intensity=0.0; backend applies music gain to zero while keeping clock running

---

Intensity policy (Milestone 1):
- Map intensity 0..1 to music gain using a perceptual gamma curve (~1.8). 0 → silence (music continues), 1.0 → full presence within user slider ceiling.
- Intensity-only updates should not force track changes; they ramp the active gain quickly (~250 ms).
- Crossfade durations can vary by intensity (faster at high intensity).
- Jumpscare API: spike to peak rapidly, hold briefly, release to previous intensity.
  Example command for LLM:
  {"action":"jumpscare","peak":1.0,"attack_ms":60,"hold_ms":150,"release_ms":800}

[ ] Telemetry hooks:
- Log every suggestion and decision with reasons
- Counters: transitions, rejections, track load failures, fallback occurrences

---

## 5) Python MusicBackend (VLC wrapped behind interface)
[x] Create module: core/music/backend_vlc.py (plus an abstract interface core/music/backend.py)

Interface (example):
[ ] class MusicBackend:
- apply_state(mood: str, intensity: float, track_path: Optional[str], transition: dict)
- set_volumes(master: int, music: int, effects: int, muted: bool)
- next_track()
- play_stinger(file_path: str, duck_db: float, restore_ms: int)
- play_sfx(file_path: str, category: str)

VLC implementation specifics:
[ ] Players:
- 2 main VLC media players for crossfading base music (current/next)
- 1 stinger player (short‑lived or pooled)
- SFX players: small pool (e.g., up to 8 concurrent); category aware (continuous vs instant)

[ ] Crossfades:
- Constant‑power gain law for fade‑out/fade‑in over configurable ms
- Schedule crossfade N seconds before track end or on Director change

[ ] Loudness normalization:
- Apply per‑track loudness_offset_db to music player gain
- Master/music/effects volumes computed as final linear gain factors

[ ] Stingers & ducking:
- On stinger start: duck current music by X dB immediately
- On stinger end: ramp music back to prior gain over Y ms
- If stinger missing: do nothing; continue baseline music

[ ] Continuous SFX:
- Separate SFX gain bus (applied via volume on SFX players)
- Loopable sources; allow fade start/stop if desired (optional in v1)

[ ] Instantaneous SFX:
- Fire and forget; limit concurrency per category to avoid cacophony

[ ] Mute semantics (no stop):
- Muted = music gain to 0; tracks continue; rotation still advances

[ ] Error handling:
- If VLC media parse fails or playback fails, skip track, log error, continue

[ ] Threading:
- Use an internal queue for commands; avoid blocking UI threads

[ ] Dependencies:
- Document VLC installation path for Windows; verify codecs

---

## 6) Web MusicBackend (Web Audio API)
[x] Create module/file: web/client/js/music-manager.js

Planned SFX scaffolding (Phase C):
[ ] Continuous SFX bus (looping ambiences) and instant SFX bus (one-shots)
[ ] Respect context→SFX mapping from config/audio/sfx_mapping.json
[ ] Concurrency caps per category; per-category gain presets

Architecture:
[x] AudioContext and user‑gesture gating:
- User gesture unlock via Settings click; no intrusive overlay

[x] Nodes:
- Two music sources (MediaElementAudioSourceNode) with individual GainNodes for crossfade
- Master GainNode upstream
- SFX chains: placeholders for future implementation

[x] Crossfades:
- Use linearRampToValueAtTime with proper old audio element cleanup

[x] Preload strategy:
- Create new audio elements on demand during crossfade
- Handle decode errors; fallback to continue current track

[ ] Loudness normalization:
- Apply track loudness_offset_db by adjusting music chain gain per track

[ ] Stingers:
- If stinger exists for event: duck music, play stinger to completion, then restore music gain
- If no stinger: do nothing

[ ] SFX:
- Continuous: loop true; start/stop via Director or scene cues
- Instantaneous: fire on demand; enforce concurrency caps per category

[x] Mute semantics:
- Mute = music gain to 0; do not pause

[x] WS handling:
- On "music_state": apply server state via WebMusicManager.applyState()

[x] Settings application:
- On save in settings modal, immediately apply new volumes to gain nodes and POST to /api/gameplay_settings

---

## 7) GUI Integration – Python
[ ] MainWindow top‑right music controls:
- Buttons wired to: mute/unmute toggle, next_track
- Remove/disable any stop semantics
- Tooltip updates reflecting state

[ ] Apply QSettings on startup:
- sound/enabled, sound/master_volume, sound/music_volume, sound/effects_volume
- Call Director.set_volumes(...) and Director.set_muted(...)

[ ] New Game flow:
- Hard‑set mood to ambient with default intensity; allow immediate playback (if volumes enabled)

[ ] Optional status area:
- Show current mood, intensity, and track (for dev/testing)

---

## 8) GUI Integration – Web
[x] Banner music controls (now functional):

Context visibility (dev-only, optional):
[ ] Small dev widget to display {mood, intensity, track, location.major, venue, weather}
- Play/pause: browser-only mute toggle
- Next: calls /api/music/next endpoint
- Volume: opens popover with real-time volume control
- No stop control

[x] Settings modal:
- Save/restore sound settings via /api/gameplay_settings
- Apply live to WebAudio gain nodes

[x] Audio context unlock:
- Unlock audio context on Settings click (user gesture)
- No intrusive overlay; follows autoplay best practices

[ ] Dev/debug (optional):
- Show current mood/intensity/track in a small corner widget in dev mode

---

## 9) LLM Integration – Structured Suggestions
[ ] Define function (tool) schema for LLM output (JSON):

Optional context tool (if not driven purely by engine):
[ ] Define SET_CONTEXT tool: { location_major?, venue?, weather?, time_of_day? }
- Engine canonicalizes via synonyms, applies policy, and updates Director.
- Alternatively, allow MUSIC tool to include optional context fields—but SET_CONTEXT keeps concerns cleaner.
{
  "tool": "music",
  "action": "set_mood",            // set_mood | set_intensity | next | mute | unmute
  "mood": "ambient|tension|combat|victory|defeat|stealth|town|dungeon",
  "intensity": 0.0..1.0,
  "confidence": 0.0..1.0,
  "evidence": "string"
}

[ ] Validation (server‑side):
- Reject malformed payloads
- Clamp intensity
- Map mood names case‑insensitively

[ ] Command plumbing:
- Extend core/game_flow/command_handlers.py with MUSIC handler that calls Director.suggest(...) or Director.next_track()/set_muted based on action
- Engine events (combat start/end) call Director.hard_set(...)

[ ] Decision policy in Director:
- Apply if confidence >= threshold and cooldown passed
- Log accept/reject reason

---

## 10) Transition Details and Math
[ ] Constant‑power crossfade:
- Use gain curves that approximate constant power: gain_out = cos(theta), gain_in = sin(theta), where theta goes 0→pi/2 over fade_duration
- Implementation: either approximate via square‑root/linear combos or compute per‑step

[ ] Stingers:
- Default duck: e.g., −8 dB instantly, restore over 300–600 ms post stinger

[ ] Intensity smoothing:
- Exponential moving average on intensity to avoid jitter: I(t) = a*new + (1−a)*prev
- Use intensity primarily for track weighting and for layered stems (later)

---

## 11) SFX System
[ ] Categories and routing:

Planning deliverables (before implementation):
[ ] Ambient library list defined (continuous + one-shot) with canonical tag names
[ ] Context→SFX mapping table authored (data-driven)
- continuous/<tag>: looped ambiences; separate gain bus
- instant/<category>: one‑shots; concurrency caps; optional per‑category output gain

[ ] Triggering:
- Director or gameplay systems trigger continuous SFX on scene change (e.g., market location)
- Instant SFX triggered by events (UI clicks, combat actions); wire hooks in combat code and UI handlers

[ ] Ducking priority:
- TTS or VO duck music; SFX generally not ducked (unless specifically desired)

---

## 12) Settings and Persistence
[ ] QSettings / /api/gameplay_settings already exist; ensure both backends read/apply at startup and on change
[ ] Persist and restore context fields (location.major, location.venue, weather.type, time_of_day?) alongside mood/intensity
[ ] Additional toggles (optional):
- "allow_llm_music_influence": true/false – gates Director.suggest application
- Per‑category SFX volume (e.g., UI vs combat SFX)

---

## 13) Testing Strategy
Unit Tests (Python):
[ ] Context weighting tests:
- Given context C and manifests with tags, selection probability shifts as expected (bias not hard exclusion)
- Unknown context values fall back safely (no crash, default weighting)
[ ] Director decisions:
- LLM suggestions below threshold rejected
- Cooldown/hysteresis enforced
- Hard‑set overrides suggestions
- No tracks available → fallback to continue current track

[ ] Rotation fairness:
- No repeats until pool exhausted
- Weighted selection respects manifest weights

[ ] Transition edges:
- Crossfade math sanity (sum of squares ~1)
- Stinger fallback: missing stinger results in no pause/restart

Integration Tests:
[ ] Python backend VLC:
- Simulate crossfades, stingers, mute/unmute
- SFX concurrency and no crash on decode error

[ ] Web backend:
- Autoplay gating; enabling audio resumes
- Crossfade scheduling and immediate SFX
- WS state application

[ ] End‑to‑end scenario:
- New game → ambient
- LLM suggests tension → if accepted, crossfade
- Combat start event → hard_set combat; optional stinger; fallback if missing
- Combat short (<2 min) but music long: ensure no forced restart; allow natural crossfade to next on schedule

Manual/QA Checklists:
[ ] Volume consistency (loudness normalization observed)
[ ] Muting doesn’t pause; unmute resumes seamlessly
[ ] Missing assets never crash playback
[ ] Browser tab visibility changes don’t break chain

---

## 14) Telemetry & Logging
[ ] Structured logs for Director:
- context_changed {location_major, venue, weather, time_of_day, source}
- suggestion_received {source, mood, intensity, confidence}
- decision {accepted, reason}
- transition {from, to, fade_ms}
- fallback events {missing_tracks, missing_stinger}

[ ] Optional counters/metrics:
- transitions_count, rejections_count, stinger_usage_count

[ ] Dev toggle to surface last 10 decisions in UI (optional)

---

## 15) Deployment & Packaging
[ ] Python VLC dependency:
- Document Windows VLC install & PATH expectations
- Validate codecs for .mp3/.ogg/.wav

[ ] Asset licensing:
- Ensure all audio has proper licenses; keep attributions if required

[ ] Performance:
- Preload track lists on startup (lightweight)
- Avoid decoding more than necessary; predecode next track only

---

## 16) Security Considerations
[ ] Prevent directory traversal in /api/music/tracks
[ ] Sanitize and canonicalize context inputs (LLM/user): whitelist enums; map via synonyms; reject unknown if necessary
[ ] Sanitize mood/tag inputs from LLM; use whitelist
[ ] Consider max concurrency limits for SFX to avoid resource abuse

---

## 17) Rollout Plan (Milestones)
Milestone 1 (Core functionality):
- Completed (see above) + Add in-scope context plumbing:
  [ ] Add Director context fields and weighting by tags (no SFX yet)
  [ ] Persist/restore context in saves
[x] Implement Music Director (state, policy, selection)
[x] Implement Python MusicBackend (VLC) with dual‑player crossfade, stinger ducking, SFX pool
[x] Wire Python GUI controls (mute/unmute, next)
[x] Apply QSettings volumes at startup and changes
[x] Implement Web MusicBackend with AudioContext, crossfades, proper cleanup
[x] WS: broadcast music_state; web follows Director
[x] Web mode detection: disable VLC backend when serving web clients
[x] /api/music/next endpoint for server-authoritative track advancement
[x] Header music controls fully functional with volume popover

Milestone 2 (LLM and events):
[ ] Define and validate LLM music tool schema (MUSIC) and optional SET_CONTEXT tool
[ ] Add MUSIC handler in command_handlers → Director.suggest; add context update path if SET_CONTEXT enabled
[ ] Hard‑set mood from engine events (combat start/end); stinger fallback if missing
[ ] (Optional) /api/music/tracks; web fetches track lists dynamically

Milestone 3 (SFX & ambience):
[ ] Author ambient library list (continuous + one-shot) and context→SFX mapping (data-driven)
[ ] Implement SFX buses (continuous + instant) and initial triggers (location/weather/UI)
[ ] Concurrency limits and per-category gains

Milestone 4 (Polish):
[ ] Loudness normalization via manifest
[ ] Better crossfade curve tuning and configurable durations
[ ] Optional layered stems and intensity‑based stem morphing
[ ] Telemetry panel (dev)
[ ] Comprehensive tests and QA

---

## 18) Edge Case Handling (Explicit)
[ ] No tracks for target mood: maintain current track; schedule retry later
[ ] Unknown/unsupported context: keep last valid context; apply neutral weighting; log once
[ ] Missing stinger: don’t interrupt; continue current track; just mark transition logically
[ ] Autoplay blocked (web): show overlay and retry start on click
[ ] Decode/parse failures: skip offending media; continue gracefully
[ ] Rapid LLM spam: throttle via Director’s cooldown and confidence threshold; log rejections
[ ] Muted state + crossfade: rotations continue; unmuting should reveal correct current track

---

## 19) Implementation Artifacts (File/Module Checklist)
Python:
[ ] config/audio/context_enums.json (canonical enums)
[ ] config/audio/context_synonyms.json (string → canonical mapping)
[ ] config/audio/sfx_mapping.json (context → SFX tags; Phase C)
[ ] core/music/director.py (Director)
[ ] core/music/backend.py (abstract interface)
[ ] core/music/backend_vlc.py (VLC implementation)
[ ] core/music/__init__.py (optional)
[x] Wire in core/base/engine.py to construct Director and backend; expose minimal getters
[ ] core/game_flow/command_handlers.py – MUSIC handler
[ ] gui/main_window.py – wire buttons to Director
[ ] gui/dialogs/settings/settings_dialog.py – volumes apply to Director
[ ] sound/music/<mood>/manifest.yaml (optional)
[ ] sound/sfx/... manifests (optional)

Web:
[x] web/client/js/music-manager.js (WebMusicManager class)
[x] Wire banner buttons in main.js/ui-manager.js
[x] /api/gameplay_settings integrated for volume persistence
[x] WS integration for "music_state" events
[x] Static mount /sound for serving audio assets
[x] /api/music/next endpoint for track advancement

---

## 20) Acceptance Criteria (Definition of Done)
[x] On desktop, starting a new game plays ambient music; mute/unmute and next work; no stop button
[x] On web, after enabling sound, ambient plays; controls work; no stop
[ ] Director uses location/venue/weather to bias selection (Phase A updated)
[ ] LLM can suggest tension/combat; Director accepts or rejects based on confidence and cooldown
[ ] Context persisted/restored across saves; unknown context handled gracefully
[ ] Combat start hard‑sets combat; if stinger exists, it plays with ducking; if not, current track keeps playing with no pause/restart
[ ] If combat ends quickly (<2 min) and music is long, we do not forcibly restart; crossfades occur naturally near track end or when directed
[ ] SFX: Continuous ambiences (e.g., market) can loop over music; instantaneous SFX play immediately and do not break music
[ ] Silence windows reduce music to zero gain without stopping; subsequent unmute or transition resumes cleanly
[ ] No crashes on missing files; logs explain fallbacks
[ ] Unit and integration tests pass; QA checklist items verified
