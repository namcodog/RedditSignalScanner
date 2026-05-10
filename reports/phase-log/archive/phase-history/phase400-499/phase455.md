# Phase 455 - live 数据噪音治理第二轮根治：跨题材 pain 补齐与机会去重

## 发现了什么？

这轮把横向验证里暴露出的两个系统级根因继续往下打，结论比 Phase 454 更清楚：

1. `home-cleaning / saas-collaboration` 的问题，不是“数据没出来”，而是：
   - `analysis.insights.pain_points` 为空或不足时
   - loader 只会在“完全为空”时补 pain
   - 导致一旦只有 1 条真 pain，其余位置仍会漏出 `关键痛点 2/3`

2. `EDC` 的问题，不只是 `/api/report` 500：
   - schema extra field 已在 loader 层清理后恢复 `200`
   - 但 canonical 里仍会出现
     - `关键痛点 2/3`
     - 第二张机会卡继续绑回第一条 pain
   - 说明还要补“partial pain supplement”和“duplicate opportunity retargeting”

## 是否需要修复？

需要，而且这轮已经完成第二轮系统级修复。

## 精确修复方法？

### 1. `analysis_payload_loader.py`

- 新增 `_supplement_pain_points()`
- 规则从：
  - `pain_points` 为空才补
- 改成：
  - `pain_points` 少于 3 条就补满
- 补齐来源：
  - `pain_clusters`
  - `opportunities.source_examples`
  - `sources.product_description`

### 2. `structured_report_fallback.py`

- 新增回归门禁，锁住旧 `report_structured` 里的占位词不能透出
- 机会卡去重规则继续收紧：
  - duplicate title 不再保留
  - duplicate linked pain 也算漂移
  - 一旦重复，就按同索引 fallback pain 重新绑定机会卡

### 3. 真实任务落库修复

对横向验证的 3 条任务，直接按新 contract 重新写回 `analysis.sources.report_structured`：

- `27aa6b63-d217-4e0d-985a-6a1e6fc8bf58` (`home-cleaning`)
- `b9bcfde2-57ae-49d0-938f-381f32be01d2` (`saas-collaboration`)
- `7155280a-79c9-4197-833d-e20774bb595c` (`edc-pocket-organizer`)

## 验证

- `pytest tests/services/report/test_analysis_payload_loader.py -q`
  - `7 passed`
- `pytest tests/services/report/test_structured_report_fallback.py -q`
  - `17 passed`

### 真实任务抽检

- `home-cleaning`
  - pain:
    - `小户型混合地面难一台机器全搞定`
    - `空间受限时，清洁和收纳都容易施展不开`
    - `产品太多，不知道该怎么选才不踩雷`
- `saas-collaboration`
  - pain:
    - `跨时区协作一拉长，沟通就容易断档`
    - `任务拆得不够清，执行时就容易互相卡住`
    - `任务很多，但真正推进情况并不清楚`
- `edc-pocket-organizer`
  - `/api/report` payload validation 已恢复
  - pain:
    - `工具越带越多，但常用组合没有被整理好`
    - `随身小物一多，口袋和包里就容易越带越乱`
    - `口袋里东西一挤，走动时就容易硌腿别扭`
  - opp:
    - `工具越带越多，但常用组合没有被整理好`
    - `围绕「随身小物一多，口袋和包里就容易越带越乱」的产品机会`

## 下一步系统性的计划是什么？

1. 继续把这套“partial pain supplement + duplicate opportunity retargeting”扩到更多正式题材
2. 开始做 8 大领域横向验证矩阵，不再只看首页标准卡
3. 下一轮优先打：
   - `evidence_chain` 为空的问题
   - 机会卡第一张仍偶发直接等于 pain 标题的问题

## 这次执行的价值是什么？

- `live 数据噪音治理` 已经不再只是 PayPal 单点有效
- `home-cleaning / saas / edc` 三类题材都已经从“空壳 pain / 重复机会 / schema 500”里拉出来了
- 当前最大未完成合同是 `evidence_chain`
