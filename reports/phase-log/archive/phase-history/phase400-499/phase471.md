# Phase 471 - 爆贴速递模块 UI/UE 设计说明文档输出

## 背景

当前用户要求暂停主链重构插入一个产品文档交付：

- 目标不是改代码
- 而是把“爆贴速递模块”当前已经落地的真实功能、页面结构、动作链和系统边界整理成一份系统说明
- 供 UI/UE 按真实功能做小程序界面设计

## 本轮产出

### 1. 新增根目录产品说明文档

- 文件：`爆贴速递模块_UIUE产品设计说明.md`

文档覆盖：

- 模块定位与价值
- 与完整报告的关系
- 当前真实功能范围
- 用户主链路与重扫链路
- 搜索页 / 结果页的信息架构
- 3 种 mode 的差异
- 状态机
- 接口动作合同
- 结果数据结构重点
- 数据落地方式
- 小程序版 IA 建议
- 当前边界与不要误设计的点

### 2. 基于真实实现而非想象稿

这次文档不是凭口头总结，而是明确对照了当前仓库里已经落地的真实模块：

- 前端：
  - `HotPostSearchPage.tsx`
  - `HotPostResultPage.tsx`
  - `hotpost.service.ts`
  - `hotpost.ts`
- 后端：
  - `hotpost.py`
  - `service.py`
  - `search_workflow.py`
  - `summary_workflow.py`
  - `report_workflow.py`
  - `response_bundle.py`
  - `persistence_workflow.py`
  - `queue.py`
  - `hotpost_query.py`
  - `hotpost_query_evidence_map.py`

并补充参考：

- `docs/爆帖速递报告增强_实施计划.md`
- `docs/爆帖速递_关键词策略设计SOP.md`
- `reports/phase-log/phase415.md`
- `reports/phase-log/phase421.md`

## 关键结论

当前爆贴速递模块已经具备做“小程序独立模块设计”的完整度：

- 有明确定位：先快扫，再决定要不要深挖
- 有明确页面：搜索页、结果页
- 有明确状态机：排队、处理中、完成、降级、失败
- 有明确主 CTA：继续深挖 / 回搜索页重扫
- 有明确与完整报告的关系：它是前置快反模块，不是完整报告本体

## 输出路径

- [爆贴速递模块_UIUE产品设计说明.md](/Users/hujia/Desktop/RedditSignalScanner/爆贴速递模块_UIUE产品设计说明.md)

## 下一步

- 如果用户继续要求，我可以再基于这份说明直接补：
  - 小程序页面清单
  - 页面字段优先级
  - 交互稿说明
  - 页面状态图
