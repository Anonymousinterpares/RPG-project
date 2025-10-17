#!/usr/bin/env python3
import os
from core.base.engine import GameEngine

def test_engine_set_get_context_updates_world_and_canonicalizes():
    # Ensure no desktop audio backend init
    os.environ['RPG_WEB_MODE'] = '1'
    eng = GameEngine()
    # Create a new game to ensure world/player exist
    eng.start_new_game(player_name="Tester")
    # Provide a context with synonyms
    eng.set_game_context({
        'location': { 'name': 'Ashen Camp', 'major': 'town', 'venue': 'pub' },
        'weather': { 'type': 'rainy' },
        'time_of_day': 'dusk',
        'biome': 'woods',
        'interior': False,
        'underground': False,
        'crowd_level': 'crowded',
        'danger_level': 'safe'
    })
    ctx = eng.get_game_context()
    assert ctx['location']['name'] == 'Ashen Camp'
    assert ctx['location']['major'] in ('city','camp','forest','village','castle','dungeon','seaside','desert','mountain','swamp','ruins','port','temple')
    # Synonyms resolved
    assert ctx['location']['venue'] == 'tavern'
    assert ctx['weather']['type'] == 'rain'
    assert ctx['time_of_day'] == 'sunset'
    assert ctx['biome'] == 'forest'
    assert ctx['crowd_level'] == 'busy'
    assert ctx['danger_level'] == 'calm'
    # World current_location synced
    st = eng.state_manager.current_state
    assert st is not None
    assert st.world.current_location == 'Ashen Camp'