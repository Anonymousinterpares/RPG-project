"""
Client base and OpenAI-like implementation using requests.
Note: This is a minimal synchronous client; UI should run it in a worker thread.
"""
from __future__ import annotations

import json
from typing import List, Dict, Any, Optional

import requests

from .settings import LLMSettings


class LLMClient:
    def send(self, messages: List[Dict[str, str]], settings: LLMSettings) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError


class OpenAILikeClient(LLMClient):
    def _endpoint(self, base: Optional[str]) -> str:
        base = base or "https://api.openai.com/v1"
        if base.endswith("/"):
            base = base[:-1]
        return f"{base}/chat/completions"

    def _headers(self, settings: LLMSettings) -> Dict[str, str]:
        # Some OpenRouter routes require a different auth header
        prov = (settings.provider or '').lower()
        if 'openrouter' in prov:
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.api_key}",
                "X-Title": "World Configurator Assistant",
            }
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.api_key}",
        }

    def send(self, messages: List[Dict[str, str]], settings: LLMSettings) -> Dict[str, Any]:
        payload = {
            "model": settings.model,
            "messages": messages,
            "temperature": 0.3,
        }
        url = self._endpoint(settings.api_base)
        headers = self._headers(settings)
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            resp.raise_for_status()
        except requests.HTTPError as e:
            body = None
            try:
                body = e.response.text
            except Exception:
                pass
            raise Exception(f"Upstream error {e.response.status_code} from {url}: {body}")
        data = resp.json()
        # Expect OpenAI-like structure
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            return json.loads(content)
        except Exception:
            return {"raw": content or data}

