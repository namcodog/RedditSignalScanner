from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from typing import Sequence


class GeminiChatClient:
    def __init__(
        self,
        model: str,
        *,
        timeout: float = 8.0,
        api_key: str | None = None,
    ) -> None:
        self._api_key = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
        self._model = model
        self._timeout = max(2.0, float(timeout))
        self._api_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )

    async def generate(
        self,
        prompt: str | list[dict[str, str]],
        *,
        response_format: dict[str, str] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        if isinstance(prompt, str):
            prompt_text = prompt
        else:
            prompt_text = self._format_messages(prompt)

        return await asyncio.to_thread(
            self._generate,
            prompt_text=prompt_text,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def _format_messages(messages: Sequence[dict[str, str]]) -> str:
        parts: list[str] = []
        for msg in messages:
            role = (msg.get("role") or "user").strip().lower()
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            if role == "system":
                parts.append(f"System:\n{content}")
            elif role == "user":
                parts.append(f"User:\n{content}")
            else:
                parts.append(f"{role.title()}:\n{content}")
        return "\n\n".join(parts).strip()

    def _generate(
        self,
        *,
        prompt_text: str,
        response_format: dict[str, str] | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not self._api_key:
            return ""

        payload: dict[str, object] = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": float(temperature),
                "maxOutputTokens": int(max_tokens),
            },
        }
        if response_format and response_format.get("type") == "json_object":
            payload["generationConfig"]["response_mime_type"] = "application/json"

        headers = {"Content-Type": "application/json"}
        try:
            req = urllib.request.Request(
                self._api_url, data=json.dumps(payload).encode("utf-8"), headers=headers
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates") or []
            if not candidates:
                return ""
            content = (candidates[0].get("content") or {}).get("parts") or []
            if not content:
                return ""
            return str(content[0].get("text") or "")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            print(f"❌ Gemini API HTTP Error {exc.code}: {err_body}")
            return ""
        except Exception as exc:
            print(f"❌ Gemini API Connection Error: {exc}")
            time.sleep(0.05)
            return ""


__all__ = ["GeminiChatClient"]
