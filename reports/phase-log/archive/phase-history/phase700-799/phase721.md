# phase721 - Reddit 带路人角色接线与供给主路径 YAML 化

## 本轮完成

- 把“R站老炮儿”正式拆成两层可执行资产：
  - `backend/config/prompt_assets/reddit_guide_soul_prompt.md`
  - `backend/config/prompt_assets/reddit_guide_thinking_contract.md`
- 新增 prompt 资产加载层：
  - `backend/app/services/hotpost/reddit_guide_prompt_assets.py`
- `signal` / `breakdown` 主 prompt 已接入这两层资产：
  - `backend/app/services/hotpost/card_content_prompts.py`
- 供给主路径已从 Python 硬编码切到 YAML 驱动：
  - `backend/config/hotpost_supply_discovery_v2.yaml`
  - `backend/app/services/hotpost/hotpost_supply_contract.py`
  - `backend/app/services/hotpost/hotpost_supply_projection.py`
- 主链已切到读 YAML：
  - `source_scope_catalog.py`
  - `reddit_search_spec_builder.py`
  - `source_scope_candidate_collector.py`

## 这轮确认的关键边界

- 角色 prompt 只负责“像谁说话、怎么理解 Reddit”，不再偷带社区池和关键词桶。
- 社区池、关键词、source mode、candidate cap、noise markers 继续归 YAML 管，不准回写 Python 业务文件。
- 供给面问题不再靠 polish 掩盖；后续判断“今天没料”前，必须先看 supply contract 有没有覆盖到足够宽的料面。
- 旧 `topic_pack_scope_*.py` 现在已不是主路径真相源，只剩兼容遗留参考价值。

## 验证结果

- `python -m py_compile` 通过：
  - `reddit_guide_prompt_assets.py`
  - `hotpost_supply_contract.py`
  - `hotpost_supply_projection.py`
  - `source_scope_catalog.py`
  - `reddit_search_spec_builder.py`
  - `source_scope_candidate_collector.py`
  - `card_content_prompts.py`
- `pytest backend/tests/services/hotpost/test_reddit_guide_prompt_assets.py backend/tests/services/hotpost/test_source_scope_catalog.py backend/tests/services/hotpost/test_reddit_search_spec_builder.py backend/tests/services/hotpost/test_source_scope_candidate_collector.py -q`
  - `15 passed`

## 下一步

- 继续把剩余遗留供给逻辑从 `topic_pack_scope_*.py` 清出主心智。
- 按新的 YAML contract 重跑运营，检查真实 collect 面是否明显变宽。
- 后续再判断哪些题材簇还缺面，不再先从输出文案下手。
