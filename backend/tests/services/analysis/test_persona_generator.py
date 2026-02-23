from __future__ import annotations

import pytest
from sqlalchemy import text


# 目标模块：app.services.analysis.persona_generator
# 注意：此测试先于实现创建，用于约束接口与基本行为。


@pytest.mark.asyncio
async def test_persona_generator_rules_basic(db_session) -> None:
    """
    规则模式：无 LLM，仅依赖社区样本文本（comments）与 TF-IDF 提取。
    期望：
      - 至少生成 1 个 PersonaResult
      - label 非空（长度适中），traits 2-6 项，method == 'rules'
    """
    # 准备最小样本：在 r/test_sub 中插入 5 条包含订阅与价格抱怨的评论
    await db_session.execute(text("DELETE FROM comments"))
    texts = [
        ("t1_1", "r/test_sub", "I hate the subscription fee, too expensive"),
        ("t1_2", "r/test_sub", "Price is getting worse with monthly fee"),
        ("t1_3", "r/test_sub", "Looking for one-time purchase, no subscription"),
        ("t1_4", "r/test_sub", "Subscription model sucks for students"),
        ("t1_5", "r/test_sub", "Prefer open-source over SaaS subscription"),
    ]
    for idx, (cid, sub, body) in enumerate(texts, start=1):
        await db_session.execute(
            text(
                """
                INSERT INTO comments (id, reddit_comment_id, source, source_post_id, subreddit, depth, body, created_utc)
                VALUES (:id, :rid, 'reddit', :pid, :sub, 0, :body, NOW())
                """
            ),
            {"id": 9000 + idx, "rid": cid, "pid": f"p_{idx}", "sub": sub, "body": body},
        )
    await db_session.commit()

    # 延迟导入：避免实现尚未完成导致 import 失败使整个测试收集中断
    import importlib
    pg = importlib.import_module("app.services.analysis.persona_generator")

    # 无 LLM 客户端（仅规则模式）
    gen = pg.PersonaGenerator(llm_client=None)
    results = await gen.generate_batch(db_session, communities=["r/test_sub"], pain_points=[])

    assert isinstance(results, list)
    assert len(results) == 1
    r0 = results[0]

    # 基本字段约束
    assert getattr(r0, "community", None) == "r/test_sub"
    assert isinstance(getattr(r0, "persona_label", None), str)
    assert len(getattr(r0, "persona_label")) >= 2
    traits = getattr(r0, "traits", [])
    assert isinstance(traits, list) and 1 <= len(traits) <= 6
    assert isinstance(getattr(r0, "strategy", None), str)
    assert 0.0 <= float(getattr(r0, "confidence", 0.0)) <= 1.0
    assert getattr(r0, "method", None) == "rules"


@pytest.mark.asyncio
async def test_persona_generator_llm_parsing_with_fallback(db_session, monkeypatch) -> None:
    """
    LLM 模式：为确保可测性，使用伪造的 LLM 客户端并验证解析；
    若 LLM 出错，应优雅降级到 rules。
    """
    await db_session.execute(text("DELETE FROM comments"))
    await db_session.execute(
        text(
            """
            INSERT INTO comments (id, reddit_comment_id, source, source_post_id, subreddit, depth, body, created_utc)
            VALUES (9101, 't1_llm', 'reddit', 'p_llm', 'r/llm_sub', 0, 'community likes diy and hates subscription', NOW())
            """
        )
    )
    await db_session.commit()

    import importlib
    pg = importlib.import_module("app.services.analysis.persona_generator")

    class FakeLLM:
        def __init__(self, ok: bool = True) -> None:
            self.ok = ok

        def _chat_completion(self, messages, *, max_tokens: int, temperature: float) -> str:  # noqa: ANN001
            if self.ok:
                # 约束输出格式：label|trait1,trait2|strategy|confidence
                return "DIY建设|注重性价比,讨厌订阅|从反订阅角度切入|0.88"
            return ""  # 触发降级

    # Case 1: 正常解析
    gen_ok = pg.PersonaGenerator(llm_client=FakeLLM(ok=True))
    res_ok = await gen_ok.generate_batch(db_session, ["r/llm_sub"], pain_points=[])
    assert res_ok and getattr(res_ok[0], "method") == "llm"
    assert 0.5 <= float(getattr(res_ok[0], "confidence", 0.0)) <= 1.0

    # Case 2: LLM失败 → 降级到规则
    gen_fail = pg.PersonaGenerator(llm_client=FakeLLM(ok=False))
    res_fallback = await gen_fail.generate_batch(db_session, ["r/llm_sub"], pain_points=[])
    assert res_fallback and getattr(res_fallback[0], "method") == "rules"

