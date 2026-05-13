# card-autoresearch-lab v3 growth-pack keep

## 发现了什么

- 本轮只在 `business-growth-ops` 范围内做更窄的 polish 实验，不碰 `why_now` 主体逻辑。
- baseline：
  - `clean_summary_polish_v1 = 3/10 pass`
- v3 变体：
  - `clean_summary_growth_pack_polish_v3 = 4/10 pass`
- 结论：
  - `clean_summary_growth_pack_polish_v3 = keep`

## 是否需要修复

- 需要 promote，但只能窄 promote。
- 不把这轮结果扩成全局 polish。
- 不影响：
  - `paid-economics`
  - `organic-discovery`

## 精确修复方法

- 新增：
  - `backend/app/services/hotpost/business_growth_signal_overrides.py`
- 生产接线：
  - `backend/app/services/hotpost/card_content_generator.py`
- 作用范围：
  - `source_scope_id == business-growth-ops`
  - 且 `topic_pack_id not in {"paid-economics", "organic-discovery"}`

## 验证结果

- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_signal_polish_experiment.py backend/tests/services/hotpost/test_card_autoresearch_lab.py backend/tests/services/hotpost/test_card_content_generator.py -q`
  - `22 passed`
- `python -m py_compile backend/app/services/hotpost/business_growth_signal_overrides.py backend/app/services/hotpost/card_content_generator.py backend/app/services/hotpost/signal_polish_variant_policy.py backend/app/services/hotpost/signal_polish_experiment.py backend/scripts/evals/run_card_autoresearch_lab_v3.py`
  - 通过

## 当前结论

- `autoresearch-lab v3` 已经证明：
  - 更窄的 growth-pack polish 比继续赌全局 prompt 更值。
- 当前生产稳定资产新增：
  - `business-growth` 窄范围去过度报告腔/过度定性 polish
