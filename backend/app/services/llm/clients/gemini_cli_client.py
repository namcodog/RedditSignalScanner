from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional, Any, Sequence

from app.services.llm.interfaces import LLMClientError


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_response_text(stdout: str) -> str:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMClientError("gemini_cli", "output missing JSON envelope")
    payload = json.loads(stdout[start : end + 1])
    if not isinstance(payload, dict):
        raise LLMClientError("gemini_cli", "output must be a JSON object")
    response = payload.get("response")
    if not isinstance(response, str) or not response.strip():
        raise LLMClientError("gemini_cli", "JSON envelope missing response text")
    return _strip_markdown_fence(response)


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


def _with_json_object_guard(prompt_text: str) -> str:
    return (
        prompt_text.rstrip()
        + "\n\nJSON output contract: return exactly one JSON object. "
        "Do not return a JSON array, markdown, code fences, or extra text."
    )


class GeminiCLIChatClient:
    def __init__(
        self,
        *,
        model: str = "gemini-3.1-pro-preview",
        timeout_seconds: float = 90.0,
        command: str = "gemini",
        cwd:Optional[ Path] = None,
    ) -> None:
        self.model = model
        self.timeout_seconds = max(2.0, float(timeout_seconds))
        self.command = command
        self.cwd = cwd

    async def generate(
        self,
        prompt: str | list[dict[str, str]],
        *,
        response_format:Optional[ dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        del temperature, max_tokens
        prompt_text = prompt if isinstance(prompt, str) else _format_messages(prompt)
        if response_format and response_format.get("type") == "json_object":
            prompt_text = _with_json_object_guard(prompt_text)
        proc = await asyncio.create_subprocess_exec(
            self.command,
            "-p",
            prompt_text,
            "--output-format",
            "json",
            "--model",
            self.model,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.cwd) if self.cwd else None,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_seconds)
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise LLMClientError("gemini_cli", f"timed out after {self.timeout_seconds}s") from exc
        if proc.returncode != 0:
            err_text = (stderr or b"").decode("utf-8", errors="ignore").strip()
            raise LLMClientError("gemini_cli", err_text or f"exited with code {proc.returncode}")
        stdout_text = (stdout or b"").decode("utf-8", errors="ignore").strip()
        if not stdout_text:
            raise LLMClientError("gemini_cli", "returned empty output")
        return _extract_response_text(stdout_text)


__all__ = ["GeminiCLIChatClient"]
