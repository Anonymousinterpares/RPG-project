#!/usr/bin/env python3
import os
from core.context.game_context import canonicalize_context

def test_time_of_day_synonyms_map_to_canonical():
    ctx, warn = canonicalize_context({ 'time_of_day': 'midday' })
    assert ctx.time_of_day == 'noon'
    ctx, warn = canonicalize_context({ 'time_of_day': 'dusk' })
    assert ctx.time_of_day == 'sunset'
    ctx, warn = canonicalize_context({ 'time_of_day': 'the hours before dawn' })
    assert ctx.time_of_day == 'pre_dawn'


def test_location_synonyms():
    ctx, warn = canonicalize_context({ 'location': { 'name': 'Ashen Camp' }, 'location_major': 'town', 'location_venue': 'pub' })
    assert ctx.location_major == 'city'
    assert ctx.location_venue == 'tavern'


def test_weather_synonyms():
    ctx, warn = canonicalize_context({ 'weather': { 'type': 'rainy' } })
    assert ctx.weather_type == 'rain'