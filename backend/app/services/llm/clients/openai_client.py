from __future__ import annotations

"""
OpenAI Chat client with graceful fallbacks.

Reads credentials from environment variables:
  - OPENAI_API_KEY (required)
  - OPENAI_BASE (optional; defaults to https://api.openai.com/v1)
  - OPENAI_ORG_ID (optional)

Model is provided by caller (e.g., settings.llm_model_name).
"""

import os
from typing import List, Sequence

try:  # Prefer the official SDK if available (>=1.0)
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

import json
import time
import urllib.request

from app.services.llm.interfaces import LLMClient


class OpenAIChatClient(LLMClient):
    def __init__(self, model: str, *, timeout: float = 8.0) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._api_key = api_key
        self._base = os.getenv("OPENAI_BASE", "https://api.openai.com/v1").rstrip("/")
        self._org = os.getenv("OPENAI_ORG_ID", "").strip() or None
        self._model = model
        self._timeout = max(2.0, float(timeout))
        self._sdk = None
        if OpenAI is not None:  # prefer SDK
            try:
                client_kwargs = {"api_key": self._api_key}
                if self._base and self._base != "https://api.openai.com/v1":
                    client_kwargs["base_url"] = self._base
                if self._org:
                    client_kwargs["organization"] = self._org
                self._sdk = OpenAI(**client_kwargs)
            except Exception:
                self._sdk = None

    # --------------- Public API ---------------

    def summarize(self, texts: Sequence[str], *, max_chars: int = 48) -> list[str]:
        outputs: List[str] = []
        for text in texts:
            prompt = self._build_summarize_prompt(text, max_chars=max_chars)
            content = self._chat_completion(prompt, max_tokens=max(64, max_chars * 3), temperature=0.2)
            outputs.append(self._post_summarize(content, max_chars))
        return outputs

    def normalize(self, name: str, *, candidates: Sequence[str]) -> str | None:
        prompt = self._build_normalize_prompt(name, candidates)
        content = self._chat_completion(prompt, max_tokens=24, temperature=0.1)
        return self._post_normalize(content, candidates)

    # --------------- Prompt craft ---------------

    @staticmethod
    def _build_summarize_prompt(text: str, *, max_chars: int) -> list[dict[str, str]]:
        system = (
            "你是严谨的编辑。只能从提供的文本抽取信息，不得编造。"
            f"用中文输出，单句不超过{max_chars}个字，避免形容词和夸张语气，只保留事实。"
        )
        user = f"请为下面的文本写一条要点句（<= {max_chars} 字）：\n\n{text.strip()}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    @staticmethod
    def _build_normalize_prompt(name: str, candidates: Sequence[str]) -> list[dict[str, str]]:
        cand_text = "\n".join(f"- {c}" for c in candidates)
        system = (
            "你是实体规范化助手。只能在候选列表中选择一个最佳匹配；若无匹配，输出 NONE。"
            "只输出候选名称或 NONE，不要额外说明。"
        )
        user = f"候选列表:\n{cand_text}\n\n实体名称: {name}\n\n输出:" 
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    @staticmethod
    def _post_summarize(text: str, max_chars: int) -> str:
        text = (text or "").strip().splitlines()[0].strip()
        if len(text) > max_chars:
            text = text[: max_chars - 1] + "…"
        return text

    @staticmethod
    def _post_normalize(text: str, candidates: Sequence[str]) -> str | None:
        value = (text or "").strip().splitlines()[0].strip()
        if value.upper() == "NONE":
            return None
        for c in candidates:
            if value.lower() == c.lower():
                return c
        return None

    # --------------- Transport ---------------

    def _chat_completion(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
        if self._sdk is not None:
            try:
                resp = self._sdk.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception:
                pass
        # Fallback to raw HTTP (minimal dependency)
        url = f"{self._base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._org:
            headers["OpenAI-Organization"] = self._org
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        except Exception:
            # On any failure, return empty string to trigger caller fallback
            time.sleep(0.05)
            return ""


__all__ = ["OpenAIChatClient"]

