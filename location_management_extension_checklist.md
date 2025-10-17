# Location Management Extension Checklist (LLM‑aware, Engine‑Authoritative)

This document defines an end‑to‑end plan to extend location management into a structured, canonical GameContext owned by the engine and surfaced to both UIs. It lays the groundwork for context‑aware Music & SFX selection and future gameplay systems.

---

## 0) Principles (accepted)
- Engine is the source of truth for context; LLM may propose, engine canonicalizes and applies policy.
- Context is data‑driven (enums + synonyms), forward‑compatible, and safe to persist.
- UI shows context read‑only by default; dev builds may expose edit/simulation controls.
- Music Director and SFX systems consume context as soft bias, never hard blockers.

---

## 1) GameContext Model (Data design)
[x] Introduce a canonical GameContext with core and optional fields:
- Core (Phase A):
  - location.name (UI string, e.g., "Ashen Camp")
  - location.major (enum: city|forest|camp|village|port|castle|dungeon|seaside|desert|mountain|swamp|ruins|temple|…)
  - location.venue (enum: tavern|market|blacksmith|inn|chapel|library|manor|arena|fireplace|bridge|tower|cave|farm|…)
  - weather.type (enum: clear|overcast|rain|storm|snow|blizzard|fog|windy|sandstorm)
  - time_of_day (enum: deep_night|pre_dawn|dawn|morning|noon|afternoon|evening|sunset|night)
- Nice‑to‑have (Phase B):
  - biome (forest|desert|swamp|mountain|seaside|plains|ruins|…)
  - region (string; optional canonical list later)
  - interior (bool), underground (bool)
  - crowd_level (empty|sparse|busy or 0..1)
  - danger_level (calm|tense|deadly or 0..1)

[x] Add a dataclass/struct in the engine to hold and serialize GameContext.
[x] Provide to_dict/from_dict helpers for persistence and WS payloads.

Example (Python dataclass sketch):
```python
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class GameContext:
    location_name: str = ""
    location_major: Optional[str] = None
    location_venue: Optional[str] = None
    weather_type: Optional[str] = None
    time_of_day: Optional[str] = None
    biome: Optional[str] = None
    region: Optional[str] = None
    interior: Optional[bool] = None
    underground: Optional[bool] = None
    crowd_level: Optional[str] = None
    danger_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GameContext":
        return cls(**d)
```

---

## 2) Context Canonicalization (data‑driven)
[x] Create config/audio/context_enums.json with canonical allowed values for each field.
[x] Create config/audio/context_synonyms.json mapping free‑text → canonical enums.
[x] Implement canonicalize_context(input_dict) that:
- trims strings, lowers case, maps via synonyms, validates against enums
- returns (canonical_context, warnings)
- unknown values: either map to None or safe default; log once

Example enums (excerpt):
```json
{
  "location": {
    "major": ["city","forest","camp","village","castle","dungeon","seaside","desert","mountain","swamp","ruins","port","temple"],
    "venue": ["tavern","market","blacksmith","inn","chapel","library","manor","arena","fireplace","bridge","tower","cave","farm"]
  },
  "weather": { "type": ["clear","overcast","rain","storm","snow","blizzard","fog","windy","sandstorm"] },
  "time_of_day": ["dawn","day","dusk","night"],
  "biome": ["forest","desert","swamp","mountain","seaside","plains","ruins"],
  "crowd_level": ["empty","sparse","busy"],
  "danger_level": ["calm","tense","deadly"],
  "booleans": ["interior","underground"]
}
```

Example synonyms (excerpt):
```json
{
  "location": {
    "major": { "town":"city", "hamlet":"village", "port town":"port" },
    "venue": { "pub":"tavern", "smith":"blacksmith", "church":"chapel" }
  },
  "weather": { "type": { "rainy":"rain", "snowing":"snow" } },
  "time_of_day": { "morning":"day", "evening":"dusk", "nighttime":"night" },
  "biome": { "shore":"seaside", "coast":"seaside", "woods":"forest" },
  "crowd_level": { "crowded":"busy", "packed":"busy" },
  "danger_level": { "safe":"calm", "high":"deadly" }
}
```

---

## 3) Engine Integration (authoritative owner)
[x] Add a ContextManager (or integrate into Engine) to store GameContext.
[x] Public API:
- set_context(partial_ctx: dict | GameContext) → canonicalize and update
- get_context() → GameContext
- on_context_changed(callback) → subscribe

[x] Persist context in saves and restore on load.
[x] Backward compatibility: if only location.name exists, infer safe defaults (e.g., major=camp for "Ashen Camp").

---

## 4) Music Director Integration (bias, not hard filter)
[x] Add Director.set_context(ctx: GameContext) and store it.
[ ] Use context tags to bias track selection (soft weights):
- Overlap of track tags with {location_major, location_venue, weather_type, time_of_day, biome} increases weight (e.g., +20% per match, tunable, capped).
- If no tracks match, proceed with neutral weighting; never block music.

Example bias sketch:
```python
def compute_weight(base_weight: float, tags: set[str], ctx: GameContext) -> float:
    bias = 1.0
    wanted = {ctx.location_major, ctx.location_venue, ctx.weather_type, ctx.time_of_day, ctx.biome}
    wanted = {w for w in wanted if w}
    overlap = len(tags & wanted)
    if overlap:
        bias *= min(2.0, 1.0 + 0.2 * overlap)  # cap at 2x by default
    return base_weight * bias
```

[ ] Director.current_state(): include context snapshot for debug/UI.

---

## 5) Server API (FastAPI)
[x] GET /api/context → current GameContext (JSON)
[x] POST /api/context → partial update; server canonicalizes and applies policy
- Validate payload; whitelist fields; ignore unknowns; booleans only true/false
- Clamp any numeric 0..1 fields if introduced
- Emit WS broadcast (game_context) on change

[x] CORS remains consistent; small payloads; avoid PII.

Example POST payload:
```json
{
  "location": { "name": "Ashen Camp", "major": "camp", "venue": "tavern" },
  "weather": { "type": "rain" },
  "time_of_day": "dusk",
  "biome": "forest",
  "region": "Ashen Fields",
  "interior": false,
  "underground": false,
  "crowd_level": "sparse",
  "danger_level": "tense"
}
```

---

## 6) WebSocket Events
[x] New WS message type: "game_context"
- data: GameContext as JSON + ts
- Emitted on initial connect (snapshot) and on changes

Example payload:
```json
{
  "type": "game_context",
  "data": {
    "location": { "name": "Ashen Camp", "major": "camp", "venue": "tavern" },
    "weather": { "type": "rain" },
    "time_of_day": "dusk",
    "biome": "forest",
    "region": "Ashen Fields",
    "interior": false,
    "underground": false,
    "crowd_level": "sparse",
    "danger_level": "tense",
    "ts": 1739532000
  }
}
```

---

## 7) Persistence
[x] Include GameContext in save files; version the schema.
[x] On load, canonicalize and broadcast context.
[x] Migrations: unknown fields ignored; missing fields default to None.

---

## 8) Web UI Integration (dev‑first, non‑intrusive)
[x] Add a small dev context panel (visible only in dev mode):
- Subscribe to WS "game_context"; render a one‑line summary and an expandable detail view.
- Optional dev controls to POST partial context for simulation.

[x] Keep production UI read‑only (no controls) unless explicitly enabled.

JS sketch:
```js
socket.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.type === "game_context") {
    ui.updateContextPanel(msg.data);
  }
};
```

---

## 9) Python GUI Integration (dev‑first)
[ ] Optional status bar line that shows: "Ashen Camp · camp/tavern · dusk · rain · forest · crowd:sparse · danger:tense"
[x] Optional dev dialog to simulate context (behind a flag) that POSTs to /api/context.

---

## 10) LLM Tools (optional, controlled)
[ ] Define a SET_CONTEXT tool schema (preferred):
- { location_major?, venue?, weather?, time_of_day?, biome?, interior?, underground?, crowd_level?, danger_level?, evidence? }
- Server canonicalizes; applies thresholds/policy; logs decision.

[ ] Alternatively, allow MUSIC tool to include optional context fields; SET_CONTEXT is cleaner separation.
[ ] Server‑side validation: whitelist, clamp, reject malformed.

---

## 11) Testing Strategy
Unit (Python):
[x] Canonicalization:
- synonyms map correctly; casing/whitespace normalized; unknowns safe
[ ] Director bias:
- tracks with overlapping tags gain selection probability vs non‑matching
- no tracks matching → selection still functions (no crash)
[x] Persistence:
- context round‑trips save/load
[x] API/WS:
- GET/POST /api/context contracts; WS emits on change; initial snapshot on connect

Integration:
[ ] End‑to‑end: context change biases music (observable in logs/WS), UIs display context.

Manual/QA:
[x] Dev panels reflect updates; production UI unaffected.

---

## 12) Telemetry & Logging
[ ] Structured logs:
- context_changed {fields_changed, source, canonicalized, warnings}
- suggestion_received (if LLM path used)
- decision {accepted, reason}

[ ] Optional counters: context_change_count by source (engine/LLM/UI).

---

## 13) Security & Robustness
[ ] Whitelist enums; canonicalize free‑text via synonyms; ignore/flag unknowns.
[ ] POST /api/context validates shapes and types; booleans strictly parsed.
[ ] Rate‑limit context updates if exposed to untrusted sources.
[ ] Never allow path traversal or file reads via context payloads (N/A by design, verify anyway).

---

## 14) Implementation Artifacts (Files/Modules)
Python:
- world_configurator/models/context_location_map.py (manager for config/audio/context_location_map.json)
- world_configurator/ui/editors/location_editor.py (Context Mapping section UI + enums)
- world_configurator/ui/dialogs/export_dialog.py (context_map export option)
- world_configurator/models/world_config.py (integrates context map manager; sync/export)
[ ] config/audio/context_enums.json
[ ] config/audio/context_synonyms.json
[ ] core/context/game_context.py (GameContext dataclass, canonicalization helpers)
[ ] core/base/engine.py (context owner; save/load wiring)
[ ] core/music/director.py (set_context, bias hook, current_state includes context)
[ ] core/web/api/context_endpoints.py (GET/POST /api/context)
[ ] core/web/ws/messages.py ("game_context" broadcasting)
[ ] tests/context/test_canonicalization.py
[ ] tests/context/test_director_bias.py
[ ] tests/context/test_api_ws.py

Web:
[ ] web/client/js/context-panel.js (dev widget)
[ ] web/client/js/main.js (WS handling for game_context)

Desktop UI:
[ ] gui/status/context_status.py (optional status bar integration)
[ ] gui/dialogs/dev_context_dialog.py (optional dev panel)

---

## 15) Milestones
Milestone A (Core context plumbing):
[x] GameContext model + canonicalization (enums & synonyms)
[x] Engine ownership + save/load
[x] Director.set_context + soft bias
[x] GET/POST /api/context + WS "game_context"
[x] Web & Python dev displays (read‑only or dev panels)

Milestone B (Extended fields & polish):
[x] Add biome, booleans, crowd_level, danger_level usage (engine enrichment + mapping; non-overwriting; UI shows values; API/WS emit)
[x] World Configurator: editable Context Location Map (by_id/by_name), enums-backed dropdowns for major/venue/weather/biome/crowd/danger + tri‑state interior/underground; import from game and export to game
[ ] Dev tools to simulate context changes
[ ] Tune bias weights; add caps and logs

Milestone C (LLM & SFX integration):
[ ] SET_CONTEXT tool integration & policy
[ ] SFX context mapping consumption (continuous ambience, instant SFX presets)

---

## 16) Acceptance Criteria
[x] Engine tracks and persists GameContext fields (Core set at minimum).
[ ] Director consumes context to bias music selection (soft bias; never blocks playback).
[x] Web and Python UIs display current context (dev panels acceptable for v1).
[x] GET/POST /api/context implemented; WS "game_context" broadcasts on change and on connect.
[x] Unknown/unsupported values handled safely (no crash); logs explain canonicalization.
[x] Unit/integration tests pass; manual QA verified.

---

## 17) Edge Cases
[ ] Only location.name provided → infer or set None for others; system behaves safely.
[ ] Rapid context flapping → optional debounce/hysteresis before bias affecting music.
[ ] Conflicting inputs (LLM vs engine) → engine policy wins; log decision.
[ ] Missing enums/synonyms files → use built‑in defaults; warn once.

---

## 18) Rollout & Backward Compatibility
[ ] Non‑breaking: if clients lack the context panel, they ignore the WS message.
[ ] Save schema versioning; migrate old saves by defaulting missing fields.
[ ] Feature flags: dev panels and LLM SET_CONTEXT gated behind config.

---

## 19) Notes for Music & SFX Systems
- Track manifests can reuse tags from enums to naturally align with context (no extra folders).
- Bias is soft: selection favors matching tags but never excludes non‑matching tracks.
- SFX mapping can reference context (e.g., crowd_level → continuous/crowd ambience; venue=tavern → clinks UI SFX bias).
