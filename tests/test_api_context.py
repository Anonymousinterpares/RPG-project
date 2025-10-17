#!/usr/bin/env python3
from fastapi.testclient import TestClient
from web.server.server import app

client = TestClient(app)

def test_context_endpoints_roundtrip():
    # Create session
    r = client.post('/api/session')
    assert r.status_code == 200
    session_id = r.json()['session_id']

    # Get initial context
    r = client.get(f'/api/context/{session_id}')
    assert r.status_code == 200
    assert 'context' in r.json()

    # Apply new context
    payload = {
        'location': { 'name': 'Test Village', 'major': 'village', 'venue': 'inn' },
        'weather': { 'type': 'clear' },
        'time_of_day': 'morning'
    }
    r = client.post(f'/api/context/{session_id}', json=payload)
    assert r.status_code == 200

    # Read back
    r = client.get(f'/api/context/{session_id}')
    assert r.status_code == 200
    ctx = r.json()['context']
    assert ctx['location']['name'] == 'Test Village'
    assert ctx['location']['major'] == 'village'
    assert ctx['location']['venue'] == 'inn'
    assert ctx['weather']['type'] == 'clear'
    assert ctx['time_of_day'] == 'morning'


def test_dev_flag_endpoint():
    r = client.get('/api/config/dev')
    assert r.status_code == 200
    assert 'dev_mode' in r.json()