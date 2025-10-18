#!/usr/bin/env python3
import random

from core.music.director import MusicDirector

class DummyBackend:
    def __init__(self):
        self.states = []
    def apply_state(self, mood, intensity, track_path, transition):
        self.states.append((mood, track_path))
    def set_volumes(self, master, music, effects, muted):
        pass


def _build_director_with_tracks():
    d = MusicDirector(project_root=None)
    # Override rotation with synthetic tracks
    d._rotation = {
        'ambient': [
            'C:/tmp/sound/music/ambient/city_theme.ogg',
            'C:/tmp/sound/music/ambient/forest_theme.ogg',
            'C:/tmp/sound/music/ambient/storm_night.ogg',
            'C:/tmp/sound/music/ambient/tavern_interior.ogg',
        ]
    }
    d._played = {'ambient': set()}
    d.set_backend(DummyBackend())
    return d


def test_bias_location_major_city():
    d = _build_director_with_tracks()
    d.set_context(location_major='city')
    random.seed(123)
    counts = {p:0 for p in d._rotation['ambient']}
    # Sample selection distribution directly
    for _ in range(200):
        track = d._select_next_track_locked('ambient')
        counts[track] += 1
    # city track should be preferred over unrelated ones
    city = [k for k in counts if 'city' in k][0]
    forest = [k for k in counts if 'forest' in k][0]
    assert counts[city] > counts[forest]
    assert counts[city] >= max(v for k,v in counts.items() if k != city)  # top pick


def test_bias_weather_and_time():
    d = _build_director_with_tracks()
    d.set_context(weather_type='storm', time_of_day='night')
    random.seed(456)
    counts = {p:0 for p in d._rotation['ambient']}
    for _ in range(200):
        track = d._select_next_track_locked('ambient')
        counts[track] += 1
    storm_night = [k for k in counts if 'storm_night' in k][0]
    # Should dominate because it matches two tokens
    assert counts[storm_night] == max(counts.values())
