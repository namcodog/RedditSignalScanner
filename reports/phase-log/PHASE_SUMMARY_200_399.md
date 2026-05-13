# PHASE SUMMARY 200-399

## 这个阶段主要做了什么

- 对分析层、`facts_v2`、数据加工层做系统审计
- 开始把“能跑”改成“合同一致”
- 收数据约束、冷存储和 dedup 合同

## 这个阶段留下了什么有效资产

- 对 silent degrade / synthetic fallback 的明确警惕
- 数据层和分析层的若干硬约束
- 更严的测试与数据库合同意识

## 今天仍然有效的判断

- 不能让展示兜底伪装成真实结果
- 质量门必须能区分“样本不足”和“链路失败”

## 细节去哪里看

- 代表 phase：
  - `phase250`
  - `phase350`
- archive：
  - `archive/phase-history/phase200-299/`
  - `archive/phase-history/phase300-399/`
