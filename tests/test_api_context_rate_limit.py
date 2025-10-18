#!/usr/bin/env python3
import time
from fastapi.testclient import TestClient

from web.server.server import app


def test_set_context_rate_limit():
    client = TestClient(app)
    # Create a session
    resp = client.post('/api/session')
    assert resp.status_code == 200
    session_id = resp.json()['session_id']
    url = f'/api/context/{session_id}'
    payload = {"location": {"name": "Harmonia", "major": "city"}}
    # Burst beyond bucket size
    successes = 0
    throttled = 0
    for _ in range(15):
        r = client.post(url, json=payload)
        if r.status_code == 200:
            successes += 1
        elif r.status_code == 429:
            throttled += 1
        else:
            assert False, f"unexpected status {r.status_code}"
    assert successes <= 10 and throttled >= 1
    # After short wait, should allow more
    time.sleep(1.0)
    r2 = client.post(url, json=payload)
    assert r2.status_code == 200
