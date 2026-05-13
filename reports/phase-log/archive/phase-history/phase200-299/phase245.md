# Phase 245 - facts_quality_audit ORM + 品牌噪音配置化 + 可观测性日志

执行时间: 2026-03-12

## 1. 发现了什么

- `facts_quality_audit` 仍然用裸 SQL 写入，字段一旦扩展，脚本 SQL 和 migration 很容易不同步。
- 品牌噪音词虽然已经支持 profile 级 stopwords，但通用噪音和 operations 扩展还写死在脚本里，改一次就得发一次版。
- 品牌过滤前后没有日志，线上排查时只能看到最终结果，看不到噪音词到底生效了多少、过滤掉了多少。
- 用户给的 `brand_noise.yaml` 验证命令路径写成了 `../config/brand_noise.yaml`。仓库实际配置路径在 `backend/config/brand_noise.yaml`，验证时按真实路径执行。

## 2. 是否需要修复

- 需要，已经一起落地。
- `facts_quality_audit` 已切到 ORM model 写入。
- 品牌噪音词已迁到 YAML 配置，并保留 profile 级 stopwords 叠加能力。
- 品牌过滤日志已补齐，实跑能看到加载词数、过滤前后数量、保留品牌样本。

## 3. 精确修复方法

### 3.1 审计写入改 ORM

- 新增 `backend/app/models/facts_quality_audit.py`
- 在 `backend/app/models/__init__.py` 注册 `FactsQualityAudit`
- `generate_t1_market_report.py::_write_quality_audit()` 改成构造 `FactsQualityAudit` 后 `await session.merge(record)` + `commit`

### 3.2 品牌噪音配置化

- 新增 `backend/config/brand_noise.yaml`
- 新增 `_load_brand_noise(config_root, mode)`，按 `general` + `operations` 两层加载
- 品牌过滤继续叠加 `profile_for_v2.brand_discovery.stopwords`

### 3.3 品牌发现可观测性日志

- 过滤前记录候选数
- 过滤后输出:
  - 当前生效噪音词加载数量
  - 过滤前后数量变化
  - 保留品牌 Top 样本

## 4. 验证结果

### 静态检查

- `python -c "import ast; ast.parse(open('backend/scripts/report/generate_t1_market_report.py').read()); print('✅ AST OK')"` -> 通过
- `cd backend && python -c "from app.models.facts_quality_audit import FactsQualityAudit; print(f'✅ ORM model loaded: {FactsQualityAudit.__tablename__}')"` -> 通过
- `python -c "from pathlib import Path; import yaml; data = yaml.safe_load(Path('backend/config/brand_noise.yaml').read_text(encoding='utf-8')); print(f'✅ general: {len(data[\"general\"])} words, operations: {len(data[\"operations\"])} words')"` -> `general=113`, `operations=24`

### 回归测试

- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report/test_report_logic.py -q` -> `14 passed`
- `SKIP_DB_RESET=1 make test-quality-gate` -> `24 passed`
- `make check-determinism` -> 通过

### 实跑日志

命令:

```bash
PYTHONPATH=backend python -u backend/scripts/report/generate_t1_market_report.py \
  --topic "robot vacuum cleaner" \
  --mode market_insight \
  --skip-llm \
  --days 365 \
  --anchor-ts "2026-03-12T03:00:00+00:00"
```

命中日志:

```text
📋 Brand noise loaded: 113 words (mode=market_insight)
🏷️ Brand filter: 12 candidates → 9 kept, 3 noise filtered
   Top brands kept: ['Habitat', 'Buying', 'Dawn', 'Bona', 'Tire', 'Concentrate Cleaning', 'Vinegar', 'Cleaning', 'UnFuck']
```

## 5. 这次执行的价值

- `facts_quality_audit` 的字段扩展风险明显下降，后面再加字段不用继续拼长 SQL。
- 品牌噪音词从“改代码发版”变成“改 YAML 生效”，日常维护轻了很多。
- 品牌发现现在有了最基本的可观测性，运维排查不再是黑盒。
