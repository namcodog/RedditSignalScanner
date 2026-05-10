from __future__ import annotations

import asyncio
import os
import signal
import tempfile
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


class CodexCLIChatClient:
    def __init__(
        self,
        *,
        model: str = "gpt-5.4-mini",
        timeout_seconds: float = 120.0,
        command: str = "codex",
        cwd:Optional[ Path] = None,
        sandbox: str = "read-only",
        reasoning_effort: str = "low",
    ) -> None:
        self.model = model
        self.timeout_seconds = max(2.0, float(timeout_seconds))
        self.command = command
        self.cwd = cwd
        self.sandbox = sandbox
        self.reasoning_effort = reasoning_effort

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

        with tempfile.NamedTemporaryFile(delete=False) as handle:
            output_path = Path(handle.name)

        proc = await asyncio.create_subprocess_exec(
            self.command,
            "exec",
            "-m",
            self.model,
            "-c",
            f'model_reasoning_effort="{self.reasoning_effort}"',
            "--skip-git-repo-check",
            "-C",
            str(self.cwd) if self.cwd else ".",
            "-o",
            str(output_path),
            "--color",
            "never",
            "-s",
            self.sandbox,
            "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.cwd) if self.cwd else None,
            start_new_session=True,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(prompt_text.encode("utf-8")),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception:
                proc.kill()
            try:
                await proc.communicate()
            except Exception:
                pass
            raise LLMClientError("codex_cli", f"timed out after {self.timeout_seconds}s") from exc

        try:
            if proc.returncode != 0:
                err_text = (stderr or b"").decode("utf-8", errors="ignore").strip()
                out_text = (stdout or b"").decode("utf-8", errors="ignore").strip()
                raise LLMClientError(
                    "codex_cli",
                    err_text or out_text or f"exited with code {proc.returncode}",
                )
            if not output_path.exists():
                raise LLMClientError("codex_cli", "output file missing")
            result = output_path.read_text(encoding="utf-8").strip()
            if not result:
                raise LLMClientError("codex_cli", "returned empty output")
            return _strip_markdown_fence(result)
        finally:
            output_path.unlink(missing_ok=True)


__all__ = ["CodexCLIChatClient"]
