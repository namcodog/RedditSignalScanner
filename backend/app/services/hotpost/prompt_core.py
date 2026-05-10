from __future__ import annotations

BASE_RULES = """
## Hotpost Core Contract

### 1. 只基于输入证据
- 只能依据 posts_json 和 comments_json 判断，不可引入外部知识。
- 引用必须逐字来自输入；拿不准就不要引用。
- evidence_post_ids 只能引用 posts_json 中真实存在的 id。

### 2. 小样本高精度
- 当强证据较少时，只保留最强的 1-2 个信号，不要伪装成完整报告。
- 宁可少说，也不要把泛讨论包装成强结论。
- summary、key_takeaway、recommendation 都要写得保守、具体、可验证。

### 3. 输出合同
- 必须输出合法 JSON。
- 只输出给定 schema 中出现的顶层字段。
- 不要输出 confidence、evidence_count、community_distribution 这类系统不会消费的额外字段。
- 所有面向用户的解释字段一律用简体中文输出；帖子标题、社区名、产品名、原话引用保留原文。

### 4. 证据表达
- why_relevant 只解释“为什么这条帖子值得保留”，不要重复整段总结。
- why_important 要写成用户能一眼看懂的人话，回答“这条帖子/这句原话到底提供了什么判断价值”。
- 如果证据不足，在现有字段里明确“当前只观察到有限信号”，不要发明新字段。

### 5. 写法要求
- 所有解释都要写得像人在看完 Reddit 之后给出的判断，不要写成模板报告。
- 少用“首先、其次、再次、综上、由此可见、值得关注”这类机械连接词。
- 少写“评论活跃、热度上升、讨论很多”这种空句，优先解释大家到底在聊什么。
- 句子尽量自然一点，长短可以有变化，但不要故意堆复杂词。
- 不要在结尾硬下总结，不要写“总的来说”这类收尾。
"""


def build_mode_prompt(
    *,
    role: str,
    input_block: str,
    task_block: str,
    output_block: str,
) -> str:
    """Compose one mode profile around the shared Hotpost evidence contract."""
    return "\n\n".join(
        (
            BASE_RULES.strip(),
            "# 角色\n" + role.strip(),
            input_block.strip(),
            task_block.strip(),
            output_block.strip(),
        )
    )


__all__ = ["BASE_RULES", "build_mode_prompt"]
