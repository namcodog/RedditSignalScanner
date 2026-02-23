# Phase 185 - Hotpost 中文关键词解析（LLM）落地

日期：2026-01-29

## 本阶段目标
- 支持中文输入→英文检索的关键词解析流程，保证爆帖速递可用性。

## 主要改动
- 新增中文关键词解析器（LLM + 缓存 + 回退）：
  - `backend/app/services/hotpost/query_resolver.py`
- Hotpost 搜索接入解析结果：
  - `backend/app/services/hotpost/service.py`
- 新增测试：
  - `backend/tests/services/hotpost/test_hotpost_query_resolver.py`
- 文档补充中文解析口径与配置项：
  - `docs/Reddit爆帖速递_产品模块文档.md`

## 新增配置
```bash
ENABLE_HOTPOST_QUERY_TRANSLATION=true
HOTPOST_QUERY_TRANSLATE_TTL_SECONDS=86400
HOTPOST_QUERY_TRANSLATE_MAX_TOKENS=200
```

## 测试
```bash
PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_query_resolver.py -q
```

结果：3 passed（含少量 pytest 警告）

## 备注
- 中文输入仅在检测到中文字符时触发 LLM；无 LLM 时自动回退原查询。
- 解析结果缓存 24h，避免重复 token 消耗。
