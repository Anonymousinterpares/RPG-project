from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from core.context.game_context import GameContext, canonicalize_context, enrich_context_from_location
from core.utils.logging_config import get_logger

logger = get_logger("CONTEXT_CTRL")

class GameContextController(QObject):
    """
    Manages the GameContext state, canonicalization, and updates.
    """
    # Emitted when GameContext changes (payload is dict)
    context_updated = Signal(object)

    def __init__(self, engine):
        super().__init__()
        self._engine = engine # Weakref not strictly necessary if ownership is clear, but be careful of cycles
        self._game_context: GameContext = GameContext()

    def get_game_context(self) -> Dict[str, Any]:
        try:
            return self._game_context.to_dict()
        except Exception:
            return {}

    def set_game_context(self, ctx: Optional[Dict[str, Any]] = None, source: Optional[str] = None, **kwargs) -> None:
        """Set or update the engine's GameContext with canonicalization and notify listeners."""
        try:
            incoming: Dict[str, Any] = {}
            if isinstance(ctx, dict):
                incoming.update(ctx)
            if kwargs:
                incoming.update(kwargs)
            
            logger.info("LOCATION_MGMT: set_game_context incoming=%s", str(incoming))

            # Canonicalize only the provided fields
            new_gc, warn = canonicalize_context(incoming)

            # Start from previous context and only update fields that were explicitly provided
            prev_gc = self._game_context
            merged_gc: GameContext = GameContext(
                location_name=prev_gc.location_name,
                location_major=prev_gc.location_major,
                location_venue=prev_gc.location_venue,
                weather_type=prev_gc.weather_type,
                time_of_day=prev_gc.time_of_day,
                biome=prev_gc.biome,
                region=prev_gc.region,
                interior=prev_gc.interior,
                underground=prev_gc.underground,
                crowd_level=prev_gc.crowd_level,
                danger_level=prev_gc.danger_level,
            )

            loc_in = (incoming.get('location') or {}) if isinstance(incoming.get('location'), dict) else {}
            
            # Location name/major/venue
            if ('location_name' in incoming) or ('name' in loc_in):
                merged_gc.location_name = new_gc.location_name
            if ('location_major' in incoming) or ('major' in loc_in):
                merged_gc.location_major = new_gc.location_major
            if ('location_venue' in incoming) or ('venue' in loc_in):
                merged_gc.location_venue = new_gc.location_venue

            # Weather.type
            weather_in = incoming.get('weather') if isinstance(incoming.get('weather'), dict) else None
            if ('weather_type' in incoming) or (isinstance(weather_in, dict) and ('type' in weather_in)):
                merged_gc.weather_type = new_gc.weather_type

            # Simple top-level fields
            for key in ('time_of_day','biome','region','interior','underground','crowd_level','danger_level'):
                if key in incoming:
                    setattr(merged_gc, key if key not in ('time_of_day',) else 'time_of_day', getattr(new_gc, key))

            # Enrichment guard for explicit clears
            explicit_venue_provided = (('location_venue' in incoming) or ('venue' in loc_in))
            venue_provided_as_none = False
            try:
                v_raw = loc_in.get('venue') if isinstance(loc_in, dict) else None
                if (v_raw is None) or (isinstance(v_raw, str) and v_raw.strip().lower() in ('', 'none', 'null', 'n/a')):
                    venue_provided_as_none = ('venue' in loc_in)
                if incoming.get('location_venue', '___MISSING___') is None:
                    venue_provided_as_none = True
            except Exception:
                pass

            # Enrich from mapping by location name/id
            try:
                loc_id = None
                try:
                    loc_id = incoming.get('location_id') or (loc_in or {}).get('id')
                except Exception:
                    loc_id = None
                loc_name = merged_gc.to_dict().get('location', {}).get('name')
                merged_gc = enrich_context_from_location(merged_gc, location_name=loc_name, location_id=loc_id)
                if explicit_venue_provided and venue_provided_as_none:
                    merged_gc.location_venue = None
            except Exception:
                pass

            self._game_context = merged_gc
            logger.info("LOCATION_MGMT: canonicalized=%s", str(merged_gc.to_dict()))
            
            # Sync world current_location in state manager
            try:
                if self._engine._state_manager and self._engine._state_manager.current_state:
                    name = merged_gc.to_dict().get("location", {}).get("name") or ""
                    self._engine._state_manager.current_state.world.current_location = name
                    self._engine._state_manager.current_state.player.current_location = name
            except Exception:
                pass
            
            # Forward to MusicDirector
            try:
                md = getattr(self._engine, 'get_music_director', lambda: None)()
                if md and hasattr(md, 'set_context'):
                    d = merged_gc.to_dict()
                    loc = d.get("location", {}) or {}
                    md.set_context(
                        location_major=loc.get("major"), 
                        location_venue=loc.get("venue"), 
                        weather_type=d.get("weather", {}).get("type"), 
                        time_of_day=d.get("time_of_day"), 
                        biome=d.get("biome"), 
                        region=d.get("region"), 
                        interior=d.get("interior"), 
                        underground=d.get("underground"), 
                        crowd_level=d.get("crowd_level"), 
                        danger_level=d.get("danger_level")
                    )
            except Exception:
                pass
                
            # Trigger SFX context update
            try:
                if hasattr(self._engine, '_sfx_manager') and self._engine._sfx_manager:
                    # Just pass all keys as changed for simplicity or diff if needed
                    self._engine._sfx_manager.apply_context(merged_gc.to_dict(), list(incoming.keys()))
            except Exception:
                pass
                
            # Emit signal
            payload = merged_gc.to_dict()
            import time as _t
            payload["ts"] = int(_t.time())
            payload["source"] = source or "unknown"
            self.context_updated.emit(payload)
            
        except Exception as e:
            logger.warning(f"set_game_context failed: {e}")

    def get_location_major(self) -> Optional[str]:
        """Derive a coarse location_major from current state (best-effort)."""
        try:
            st = self._engine._state_manager.current_state
            loc = (getattr(getattr(st, 'world', None), 'current_location', None) or getattr(getattr(st, 'player', None), 'current_location', None))
            if not loc:
                return None
            s = str(loc).strip().lower()
            checks = [
                ("city", "city"), ("camp", "camp"), ("forest", "forest"),
                ("harbor", "port"), ("harbour", "port"), ("docks", "port"), ("port", "port"),
                ("seaside", "seaside"), ("coast", "seaside"), ("beach", "seaside"), ("shore", "seaside"),
                ("desert", "desert"), ("mountain", "mountain"), ("peak", "mountain"), ("ridge", "mountain"),
                ("swamp", "swamp"), ("marsh", "swamp"), ("castle", "castle"), ("keep", "castle"),
                ("dungeon", "dungeon"), ("cavern", "dungeon"), ("cave", "dungeon"), ("village", "village"), ("hamlet", "village"),
            ]
            for token, tag in checks:
                if token in s:
                    return tag
            return None
        except Exception:
            return None