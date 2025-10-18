#!/usr/bin/env python3
"""Test context-aware music bias using headless CLI mode."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base.engine import GameEngine
from core.music.director import MusicDirector
from core.testing.headless_env import get_headless_game_state
from pathlib import Path

def main():
    print("Testing context-aware music bias...")
    
    # Initialize headless game state
    engine = GameEngine()
    test_state = get_headless_game_state()
    engine._state_manager.set_current_state(test_state)
    
    # Get or create MusicDirector
    director = engine._music_director if hasattr(engine, '_music_director') else None
    if not director:
        from core.music.director import get_music_director
        director = get_music_director(project_root=Path(__file__).resolve().parents[2])
    
    print(f"Initial mood: {director._mood}")
    print(f"Available moods: {list(director._rotation.keys())}")
    
    # Test 1: Set context and observe track selection
    print("\n--- Test 1: City location context ---")
    engine.set_game_context({"location": {"name": "Harmonia", "major": "city"}}, source="test")
    for i in range(3):
        track = director._select_next_track_locked("ambient")
        if track:
            print(f"Selected track {i+1}: {os.path.basename(track)}")
        else:
            print(f"No track selected for ambient mood")
    
    # Test 2: Multi-tag context (forest + storm)
    print("\n--- Test 2: Forest + Storm context ---")
    engine.set_game_context({
        "location": {"major": "forest"},
        "weather": {"type": "storm"},
        "time_of_day": "night"
    }, source="test")
    for i in range(3):
        track = director._select_next_track_locked("ambient")
        if track:
            print(f"Selected track {i+1}: {os.path.basename(track)}")
        else:
            print("No track selected for ambient mood")
    
    # Test 3: Interior tavern with crowd
    print("\n--- Test 3: Tavern interior + crowd ---")
    engine.set_game_context({
        "location": {"venue": "tavern"},
        "interior": True,
        "crowd_level": "busy"
    }, source="test")
    for i in range(3):
        track = director._select_next_track_locked("ambient")
        if track:
            print(f"Selected track {i+1}: {os.path.basename(track)}")
        else:
            print("No track selected for ambient mood")
    
    # Test 4: Observe context in status
    print("\n--- Test 4: Current context state ---")
    current_ctx = engine.get_game_context() if hasattr(engine, 'get_game_context') else {}
    print(f"Current context: {current_ctx}")
    print(f"MusicDirector context: {director._context}")
    
    print("\nTest complete!")

if __name__ == "__main__":
    main()