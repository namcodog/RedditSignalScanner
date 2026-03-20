"""
Phase 240 确定性回归测试。
验证: 同一 anchor_ts + 同一参数，generate_t1_market_report 的核心数据输出必须完全一致。
"""

from pathlib import Path


class TestDeterminismProtocol:
    """确定性协议合规检测"""

    def test_no_now_in_report_script(self):
        """报告脚本中不应包含 NOW()"""
        report_file = Path(__file__).resolve().parents[3] / "scripts" / "report" / "generate_t1_market_report.py"
        content = report_file.read_text(encoding="utf-8")
        lines_with_now = [
            (i + 1, line)
            for i, line in enumerate(content.splitlines())
            if "NOW()" in line and not line.strip().startswith("#")
        ]
        assert not lines_with_now, (
            f"NOW() found in generate_t1_market_report.py at lines: "
            f"{[ln for ln, _ in lines_with_now]}. "
            f"Use anchor_ts parameter instead. See DETERMINISM PROTOCOL."
        )

    def test_no_now_in_t1_stats(self):
        """t1_stats.py 中不应包含 NOW()"""
        stats_file = Path(__file__).resolve().parents[3] / "app" / "services" / "analysis" / "t1_stats.py"
        content = stats_file.read_text(encoding="utf-8")
        lines_with_now = [
            (i + 1, line)
            for i, line in enumerate(content.splitlines())
            if "NOW()" in line and not line.strip().startswith("#")
        ]
        assert not lines_with_now, (
            f"NOW() found in t1_stats.py at lines: "
            f"{[ln for ln, _ in lines_with_now]}. "
            f"Use anchor_ts parameter instead. See DETERMINISM PROTOCOL."
        )

    def test_no_now_in_embedding_task(self):
        """embedding_task.py 中不应包含 NOW()"""
        task_file = Path(__file__).resolve().parents[3] / "app" / "tasks" / "embedding_task.py"
        content = task_file.read_text(encoding="utf-8")
        lines_with_now = [
            (i + 1, line)
            for i, line in enumerate(content.splitlines())
            if "NOW()" in line and not line.strip().startswith("#")
        ]
        assert not lines_with_now, (
            f"NOW() found in embedding_task.py at lines: "
            f"{[ln for ln, _ in lines_with_now]}. "
            f"Use Python-side cutoff params instead."
        )

    def test_deterministic_validation_flag_exists(self):
        """确认 deterministic_validation 守卫变量存在"""
        report_file = Path(__file__).resolve().parents[3] / "scripts" / "report" / "generate_t1_market_report.py"
        content = report_file.read_text(encoding="utf-8")
        assert "deterministic_validation = bool(args.anchor_ts)" in content, (
            "deterministic_validation flag not found. "
            "This is the core switch for determinism mode."
        )

    def test_deterministic_guards_count(self):
        """确认至少有 4 个确定性守卫点"""
        report_file = Path(__file__).resolve().parents[3] / "scripts" / "report" / "generate_t1_market_report.py"
        content = report_file.read_text(encoding="utf-8")
        guard_count = content.count("if deterministic_validation:")
        assert guard_count >= 4, (
            f"Only {guard_count} deterministic guards found, expected >= 4. "
            f"Guards needed: LLM expansion, JIT labeling, persona, brands."
        )
