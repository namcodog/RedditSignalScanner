# Phase 176 - 主系统词库口径统一（Signal/Classifier）

## 目标
- 主系统信号提取/痛点桶/引言打分词库统一入口，避免硬编码分散。
- 文本分类器词库从配置读取，去除代码内硬编码。
- 语义迁移脚本支持 signal_keywords 入库（DB 优先、YAML 兜底）。

## 变更摘要
- 统一信号词库入口：新增 `backend/app/services/analysis/signal_lexicon.py`
  - DB 优先（semantic_rules），无数据时回退 YAML。
  - 输出统一的负面词/机会词/解决方案词/紧迫词/竞品线索/痛点正则/痛点桶。
- 信号提取器改为读统一词库：`backend/app/services/analysis/signal_extraction.py`
- 痛点桶规则改为读统一词库：`backend/app/services/analysis_engine.py`
- 引言打分负面词来源改为统一词库：`backend/app/services/analysis/quote_extractor.py`
- 文本分类器词库去硬编码：`backend/app/services/text_classifier.py`
  - 新增配置：`backend/config/text_classifier_keywords.yml`
- 新增信号词库配置：`backend/config/signal_keywords.yaml`
- 迁移脚本支持信号词库：`backend/scripts/migrate_semantics.py`
  - 新增 `signal_keywords` 概念 + rule_type 写入
- 新增测试：`backend/tests/services/test_signal_lexicon.py`

## 影响范围
- Signal 提取（pain/opportunity/solution/competitor）
- Facts v2 痛点桶聚合
- 引言抽取情感强度
- TextClassifier 分类

## 测试
- 未跑（新增用例：`backend/tests/services/test_signal_lexicon.py`）

## 备注
- 需执行 `python -m backend.scripts.migrate_semantics` 才会把 signal_keywords 写入 DB。
- YAML 仍作为冷启动兜底；DB 有数据时覆盖。

## 执行结果（dev）
- 修复迁移脚本 f-string 语法错误：`backend/scripts/migrate_semantics.py`
- dev 数据库已执行：`python -m backend.scripts.migrate_semantics`
  - 输出：pain_keywords=136, blacklist=15, filter_keywords=4, signal_keywords=183

## 测试结果（dev）
- 执行：`pytest backend/tests/services/test_signal_lexicon.py -q`
- 结果：被安全保护拦截（DATABASE_URL=reddit_signal_scanner_dev 非 _test 库），测试未运行。
- 测试库执行失败：账号权限不足（permission denied for table users），无法创建/迁移表。需要具备 DDL 权限的 test 库账号或使用具备权限的连接。
- 测试通过（test 库）：
  - 命令：`DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test PYTHONPATH=backend pytest backend/tests/services/test_signal_lexicon.py -q`
  - 结果：2 passed
  - 备注：pytest asyncio 配置警告（asyncio_default_fixture_loop_scope）
- 补充 test 环境配置：`backend/.env.test`（DATABASE_URL 指向 reddit_signal_scanner_test）
