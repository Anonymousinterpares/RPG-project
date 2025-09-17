"""
Google Gemini client adapter.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

import requests

from .settings import LLMSettings


class GeminiClient:
    """Minimal Gemini API client using generateContent endpoint.

    Expects OpenAI-like chat messages (list of {role, content}) and converts to Gemini format.
    """

    def _endpoint(self, model: str) -> str:
        # v1beta remains widely compatible; adjust to v1 if your key is v1-only.
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def _convert_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        system_instruction = None
        contents: List[Dict[str, Any]] = []
        for m in messages:
            role = m.get("role", "user")
            text = m.get("content", "")
            if role == "system":
                # Use system_instruction where possible
                system_instruction = {
                    "role": "system",
                    "parts": [{"text": text}]
                }
            else:
                contents.append({
                    "role": "user" if role == "user" else "model",
                    "parts": [{"text": text}]
                })
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                # Encourage JSON output in the supported field location
                "response_mime_type": "application/json",
            },
        }
        if system_instruction is not None:
            payload["systemInstruction"] = system_instruction
        return payload

    def send(self, messages: List[Dict[str, str]], settings: LLMSettings) -> Dict[str, Any]:
        url = self._endpoint(settings.model)
        params = {"key": settings.api_key}
        headers = {"Content-Type": "application/json"}
        payload = self._convert_messages(messages)
        try:
            resp = requests.post(url, params=params, headers=headers, data=json.dumps(payload), timeout=60)
            resp.raise_for_status()
        except requests.HTTPError as e:
            body = None
            try:
                body = e.response.text
            except Exception:
                pass
            raise Exception(f"Upstream error {e.response.status_code} from {url}: {body}")
        data = resp.json()
        # Parse first candidate's text
        try:
            candidates = data.get("candidates") or []
            if not candidates:
                return {"raw": data}
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            return json.loads(text) if text else {"raw": data}
        except Exception:
            return {"raw": data}

