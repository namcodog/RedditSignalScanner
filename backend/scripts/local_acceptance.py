"""Local acceptance automation script.

This utility drives a lightweight end-to-end smoke test against a running
local stack.  It mirrors the manual checklist described in the documentation
and produces a Markdown report under ``reports/local-acceptance`` so the
result can be attached to phase logs or shared with the team.

The module also exposes small helpers (``StepResult``, ``AcceptanceSummary``,
``summarize_results`` and ``render_markdown_report``) that are unit-tested and
can be reused by other tooling.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

import httpx

try:  # pragma: no cover - optional dependency at runtime
    import redis
except Exception:  # pragma: no cover - redis is optional for local smoke
    redis = None  # type: ignore

try:  # pragma: no cover - optional dependency for frontend health check
    import requests
except Exception:  # pragma: no cover - requests is optional
    requests = None  # type: ignore


AcceptStep = Callable[[], str]


@dataclass(slots=True)
class StepResult:
    """Result for a single acceptance step."""

    name: str
    success: bool
    detail: str
    duration: float
    skipped: bool = False
    error: Optional[str] = None

    @property
    def icon(self) -> str:
        if self.skipped:
            return "⚪️"
        return "✅" if self.success else "❌"


@dataclass(slots=True)
class AcceptanceSummary:
    """Aggregated summary for the entire run."""

    total_steps: int
    success_steps: int
    failed_steps: int
    skipped_steps: int
    duration_seconds: float
    success: bool
    started_at: datetime
    finished_at: datetime


def summarize_results(
    steps: Iterable[StepResult],
    *,
    started_at: datetime,
    finished_at: datetime,
) -> AcceptanceSummary:
    """Compute an ``AcceptanceSummary`` from step results."""

    step_list = list(steps)
    success_steps = sum(1 for step in step_list if step.success and not step.skipped)
    failed_steps = sum(1 for step in step_list if not step.success and not step.skipped)
    skipped_steps = sum(1 for step in step_list if step.skipped)
    duration_seconds = max(0.0, (finished_at - started_at).total_seconds())

    return AcceptanceSummary(
        total_steps=len(step_list),
        success_steps=success_steps,
        failed_steps=failed_steps,
        skipped_steps=skipped_steps,
        duration_seconds=duration_seconds,
        success=failed_steps == 0,
        started_at=started_at,
        finished_at=finished_at,
    )


def render_markdown_report(
    summary: AcceptanceSummary,
    steps: Iterable[StepResult],
    *,
    environment: str,
) -> str:
    """Render a Markdown report containing summary and step details."""

    lines: list[str] = []
    lines.append(f"# 本地验收报告 ({environment})")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **开始时间**: {summary.started_at.isoformat()}")
    lines.append(f"- **结束时间**: {summary.finished_at.isoformat()}")
    lines.append(f"- **总步骤**: {summary.total_steps}")
    lines.append(f"- **成功步骤**: {summary.success_steps}")
    lines.append(f"- **失败步骤**: {summary.failed_steps}")
    lines.append(f"- **跳过步骤**: {summary.skipped_steps}")
    lines.append(f"- **总耗时**: {summary.duration_seconds:.2f} 秒")
    lines.append(f"- **验收结果**: {'✅ 通过' if summary.success else '❌ 失败'}")
    lines.append("")

    lines.append("## 步骤详情")
    lines.append("")
    lines.append("| 状态 | 步骤 | 描述 | 耗时 (秒) |")
    lines.append("| --- | --- | --- | --- |")

    for step in steps:
        detail = step.detail.replace("\n", " ").strip() or "--"
        lines.append(
            f"| {step.icon} | `{step.name}` | {detail} | {step.duration:.2f} |"
        )
        if step.error:
            lines.append(f"|  | ⚠️ 错误 | `{step.error.strip()}` |  |")

    lines.append("")
    lines.append("> 说明: ✅=成功, ❌=失败, ⚪️=跳过 (前置条件缺失或显式跳过)。")

    return "\n".join(lines)


class StepSkipped(RuntimeError):
    """Internal helper exception to mark a step as skipped."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class LocalAcceptanceRunner:
    """Drive local acceptance steps and collect structured results."""

    def __init__(
        self,
        *,
        backend_base: str = "http://localhost:8006",
        frontend_base: str = "http://localhost:3006",
        redis_url: str = "redis://localhost:6379/0",
        environment: str = "local",
        email: Optional[str] = None,
        password: Optional[str] = None,
        product_description: Optional[str] = None,
        timeout: float = 10.0,
        poll_interval: float = 2.0,
        poll_attempts: int = 60,
    ) -> None:
        self.backend_base = backend_base.rstrip("/")
        self.frontend_base = frontend_base.rstrip("/")
        self.redis_url = redis_url
        self.environment = environment
        self.email = email or self._generate_email()
        self.password = password or "LocalAcceptance!123"
        self.product_description = (
            product_description
            or "Local acceptance smoke test for Reddit Signal Scanner"
        )
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.poll_attempts = poll_attempts

        self._api_client = httpx.Client(
            base_url=f"{self.backend_base}/api",
            timeout=self.timeout,
            headers={"Accept": "application/json"},
        )
        self._http_client = httpx.Client(timeout=self.timeout)

        self.access_token: Optional[str] = None
        self.task_id: Optional[str] = None
        self._steps: list[StepResult] = []

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def run(self) -> tuple[AcceptanceSummary, list[StepResult]]:
        started_at = datetime.now(timezone.utc)
        try:
            self._run()
        finally:
            self._api_client.close()
            self._http_client.close()

        finished_at = datetime.now(timezone.utc)
        summary = summarize_results(
            self._steps, started_at=started_at, finished_at=finished_at
        )
        return summary, list(self._steps)

    def write_report(self, summary: AcceptanceSummary, steps: list[StepResult]) -> Path:
        report_dir = Path("reports") / "local-acceptance"
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        report_path = report_dir / f"local-acceptance-{timestamp}.md"
        markdown = render_markdown_report(summary, steps, environment=self.environment)
        report_path.write_text(markdown, encoding="utf-8")
        return report_path

    # ------------------------------------------------------------------
    # Internal orchestration
    # ------------------------------------------------------------------
    def _run(self) -> None:
        self._steps.append(self._run_step("backend-health", self._check_backend_health))
        self._steps.append(self._run_step("redis", self._check_redis))
        self._steps.append(
            self._run_step("frontend-health", self._check_frontend_health)
        )
        self._steps.append(self._run_step("register-user", self._register_user))
        self._steps.append(self._run_step("login-user", self._login_user))

        if not self.access_token:
            self._steps.append(self._skip_step("create-task", "缺少访问令牌"))
            self._steps.append(self._skip_step("wait-for-task", "缺少访问令牌"))
            self._steps.append(self._skip_step("fetch-report", "缺少访问令牌"))
            self._steps.append(self._skip_step("download-report", "缺少访问令牌"))
            return

        self._steps.append(self._run_step("create-task", self._create_analysis_task))
        if self.task_id is None:
            self._steps.append(self._skip_step("wait-for-task", "创建任务失败"))
            self._steps.append(self._skip_step("fetch-report", "创建任务失败"))
            self._steps.append(self._skip_step("download-report", "创建任务失败"))
            return

        self._steps.append(self._run_step("wait-for-task", self._wait_for_completion))

        self._steps.append(self._run_step("fetch-report", self._fetch_report_payload))
        self._steps.append(
            self._run_step("download-report", self._download_report_json)
        )

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------
    def _check_backend_health(self) -> str:
        response = self._api_client.get("/healthz")
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status", "unknown")
        return f"backend ok (status={status})"

    def _check_frontend_health(self) -> str:
        # Use requests library for frontend health check due to httpx/Vite compatibility issue
        # httpx has issues with Vite dev server's HTTP/1.1 keep-alive connections
        if requests is None:  # pragma: no cover
            raise StepSkipped("requests 库不可用，跳过前端健康检查")

        try:
            response = requests.get(self.frontend_base, timeout=self.timeout)
            response.raise_for_status()
            return f"frontend ok (status={response.status_code})"
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"前端健康检查失败: {e}") from e

    def _check_redis(self) -> str:
        if redis is None:  # pragma: no cover - best effort when dependency missing
            raise StepSkipped("redis 客户端不可用，跳过检查")

        client = redis.from_url(self.redis_url)  # type: ignore[attr-defined]
        try:
            pong = client.ping()
        finally:
            client.close()
        if bool(pong):
            return "redis ok"
        raise RuntimeError("redis ping 未返回预期结果")

    def _register_user(self) -> str:
        payload = {
            "email": self.email,
            "password": self.password,
            "membership_level": "pro",
        }
        response = self._api_client.post("/auth/register", json=payload)
        if response.status_code == 201:
            data = response.json()
            self.access_token = data.get("access_token")
            return "user registered"
        if response.status_code == 409:
            # 用户已存在，后续登录步骤会获取 token
            return "user already exists"
        response.raise_for_status()
        return "user registered"

    def _login_user(self) -> str:
        payload = {
            "email": self.email,
            "password": self.password,
        }
        response = self._api_client.post("/auth/login", json=payload)
        response.raise_for_status()
        data = response.json()
        self.access_token = data.get("access_token")
        expires = data.get("expires_at")
        return f"token issued (expires={expires})"

    def _create_analysis_task(self) -> str:
        headers = self._auth_header()
        payload = {"product_description": self.product_description}
        response = self._api_client.post("/analyze", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        task_id = data.get("task_id")
        if not task_id:
            raise RuntimeError("task_id missing in response")
        self.task_id = str(task_id)
        status = data.get("status")
        return f"task created (id={self.task_id}, status={status})"

    def _wait_for_completion(self) -> str:
        assert self.task_id is not None
        headers = self._auth_header()
        history: list[str] = []
        for attempt in range(1, self.poll_attempts + 1):
            response = self._api_client.get(
                f"/status/{self.task_id}",
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
            status = str(payload.get("status", "unknown")).lower()
            history.append(status)
            if status == "completed":
                return f"task completed after {attempt} polls"
            if status == "failed":
                raise RuntimeError("analysis pipeline reported failure")
            time.sleep(self.poll_interval)
        raise RuntimeError(
            f"task did not complete within {self.poll_attempts * self.poll_interval:.0f} seconds"
        )

    def _fetch_report_payload(self) -> str:
        assert self.task_id is not None
        response = self._api_client.get(
            f"/report/{self.task_id}",
            headers=self._auth_header(),
        )
        response.raise_for_status()
        payload = response.json()
        if "report" not in payload:
            raise RuntimeError("report payload missing 'report' section")
        action_items = len(payload.get("report", {}).get("action_items", []))
        return f"report fetched (action_items={action_items})"

    def _download_report_json(self) -> str:
        assert self.task_id is not None
        response = self._api_client.get(
            f"/report/{self.task_id}/download",
            headers=self._auth_header(),
            params={"format": "json"},
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        size = len(response.content)
        return f"report download ok (content_type={content_type}, bytes={size})"

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _run_step(self, name: str, func: AcceptStep) -> StepResult:
        started = time.monotonic()
        try:
            detail = func()
            duration = time.monotonic() - started
            return StepResult(name=name, success=True, detail=detail, duration=duration)
        except StepSkipped as skipped:  # pragma: no cover - used in optional steps
            duration = time.monotonic() - started
            return StepResult(
                name=name,
                success=False,
                detail=skipped.reason,
                duration=duration,
                skipped=True,
            )
        except Exception as exc:  # pragma: no cover - errors are expected in failures
            duration = time.monotonic() - started
            return StepResult(
                name=name,
                success=False,
                detail=str(exc),
                duration=duration,
                error=repr(exc),
            )

    def _skip_step(self, name: str, reason: str) -> StepResult:
        return StepResult(
            name=name, success=False, detail=reason, duration=0.0, skipped=True
        )

    def _auth_header(self) -> dict[str, str]:
        if not self.access_token:
            raise RuntimeError("missing access token")
        return {"Authorization": f"Bearer {self.access_token}"}

    @staticmethod
    def _generate_email() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"local-acceptance+{timestamp}@example.com"


def build_runner_from_env() -> LocalAcceptanceRunner:
    """Factory helper that reads configuration from environment variables."""

    return LocalAcceptanceRunner(
        backend_base=os.getenv("LOCAL_ACCEPTANCE_BACKEND", "http://localhost:8006"),
        frontend_base=os.getenv("LOCAL_ACCEPTANCE_FRONTEND", "http://localhost:3006"),
        redis_url=os.getenv("LOCAL_ACCEPTANCE_REDIS", "redis://localhost:6379/0"),
        environment=os.getenv("LOCAL_ACCEPTANCE_ENV", "local"),
        email=os.getenv("LOCAL_ACCEPTANCE_EMAIL"),
        password=os.getenv("LOCAL_ACCEPTANCE_PASSWORD"),
        product_description=os.getenv(
            "LOCAL_ACCEPTANCE_PRODUCT",
            "Local acceptance smoke test for Reddit Signal Scanner",
        ),
        timeout=float(os.getenv("LOCAL_ACCEPTANCE_TIMEOUT", "10")),
        poll_interval=float(os.getenv("LOCAL_ACCEPTANCE_POLL_INTERVAL", "2")),
        poll_attempts=int(os.getenv("LOCAL_ACCEPTANCE_POLL_ATTEMPTS", "60")),
    )


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local acceptance smoke test")
    parser.add_argument(
        "--backend",
        "--backend-url",
        dest="backend",
        help="Backend base URL",
        default=os.getenv("LOCAL_ACCEPTANCE_BACKEND"),
    )
    parser.add_argument(
        "--frontend",
        "--frontend-url",
        dest="frontend",
        help="Frontend base URL",
        default=os.getenv("LOCAL_ACCEPTANCE_FRONTEND"),
    )
    parser.add_argument(
        "--redis",
        "--redis-url",
        dest="redis",
        help="Redis URL",
        default=os.getenv("LOCAL_ACCEPTANCE_REDIS"),
    )
    parser.add_argument(
        "--env",
        "--environment",
        dest="environment",
        help="Environment label",
        default=os.getenv("LOCAL_ACCEPTANCE_ENV"),
    )
    parser.add_argument(
        "--email",
        dest="email",
        help="Reusable acceptance account email",
        default=os.getenv("LOCAL_ACCEPTANCE_EMAIL"),
    )
    parser.add_argument(
        "--password",
        dest="password",
        help="Reusable acceptance account password",
        default=os.getenv("LOCAL_ACCEPTANCE_PASSWORD"),
    )
    parser.add_argument(
        "--product",
        dest="product",
        help="Product description used for analysis",
        default=os.getenv("LOCAL_ACCEPTANCE_PRODUCT"),
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=float,
        default=float(os.getenv("LOCAL_ACCEPTANCE_TIMEOUT", "10")),
    )
    parser.add_argument(
        "--poll-interval",
        dest="poll_interval",
        type=float,
        default=float(os.getenv("LOCAL_ACCEPTANCE_POLL_INTERVAL", "2")),
    )
    parser.add_argument(
        "--poll-attempts",
        dest="poll_attempts",
        type=int,
        default=int(os.getenv("LOCAL_ACCEPTANCE_POLL_ATTEMPTS", "60")),
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    runner = LocalAcceptanceRunner(
        backend_base=args.backend or "http://localhost:8006",
        frontend_base=args.frontend or "http://localhost:3006",
        redis_url=args.redis or "redis://localhost:6379/0",
        environment=args.environment or os.getenv("LOCAL_ACCEPTANCE_ENV", "local"),
        email=args.email,
        password=args.password,
        product_description=args.product,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        poll_attempts=args.poll_attempts,
    )

    summary, steps = runner.run()
    report_path = runner.write_report(summary, steps)

    markdown = render_markdown_report(summary, steps, environment=runner.environment)
    print(markdown)
    print()
    print(f"📄 报告已生成: {report_path}")

    return 0 if summary.success else 1


__all__ = [
    "AcceptanceSummary",
    "LocalAcceptanceRunner",
    "StepResult",
    "build_runner_from_env",
    "main",
    "render_markdown_report",
    "summarize_results",
]


if __name__ == "__main__":  # pragma: no cover - manual execution entry point
    sys.exit(main())
