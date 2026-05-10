# phase-log 使用规则

`phase-log` 现在只服务 4 件事：

1. 说明项目当前进度
2. 说明未完成事项
3. 说明下一步要做什么
4. 保留可追溯的历史记录

## 根目录只保留什么

- `README.md`
- `CURRENT_STATUS.md`
- `OPEN_ITEMS.md`
- `MILESTONES.md`
- `INDEX.md`
- 本轮整理计划文件
- `PHASE_SUMMARY_*.md`
- 最近阶段的 `phase{N}.md`

## 根目录不再保留什么

- 老 phase 大量堆积
- 验收报告
- checklist
- 临时分析
- 调试导出
- `txt/json/csv/log/xml/out/sh` 产物
- 非规范命名文档

这些都已经下沉到 `archive/`。

## 新 phase 记录规则

以后每个 `phase{N}.md` 只写 4 件事：

1. 这轮达到的目的
2. 当前状态发生了什么变化
3. 还没完成什么
4. 下一步做什么

额外要求：

- 不写流水账
- 不贴命令清单
- 不堆执行细节
- 默认控制在短文档，能一眼读完

## 什么时候必须记录 phase

只有出现下面这些“状态变化”时，才新增 `phase{N}.md`：

1. 项目主线状态变了
   例如：阶段切换、阻塞变化、默认判断变化。

2. 关键交付完成了
   例如：发布、验收、主链修复、合同/规则生效。

3. 关键结论被证实或被推翻
   例如：根因确认、旧判断失效、新口径成立。

4. 下一步工作顺序被重排
   例如：优先级变化、计划切换、停止继续某条线。

## 什么时候禁止记录 phase

下面这些情况不单独记 phase：

- 单次命令执行
- 中间测试通过一次
- 临时排查过程
- 重复的 retry / rerun
- 还没有形成状态变化的小修小补
- 只增加过程细节，但没有新增结论

这些细节应留在：

- 代码提交
- 测试日志
- archive 历史资料
- 阶段摘要文档

## 默认阅读顺序

1. 先读 [CURRENT_STATUS.md](/Users/hujia/Desktop/RedditSignalScanner/reports/phase-log/CURRENT_STATUS.md)
2. 再读 [OPEN_ITEMS.md](/Users/hujia/Desktop/RedditSignalScanner/reports/phase-log/OPEN_ITEMS.md)
3. 再读 [MILESTONES.md](/Users/hujia/Desktop/RedditSignalScanner/reports/phase-log/MILESTONES.md)
4. 再读 [INDEX.md](/Users/hujia/Desktop/RedditSignalScanner/reports/phase-log/INDEX.md)
5. 需要最近上下文时，再看根目录保留的最近 phase
6. 需要旧历史时，先看阶段摘要，再进 `archive/`
