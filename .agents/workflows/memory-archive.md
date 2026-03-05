---
description: 归档过期记忆 — 将 MEMORY.md 中超过 30 天的条目迁移到 ARCHIVE.md
---

# /memory-archive — 归档过期记忆

月度维护任务。扫描 MEMORY.md 中的过期条目，按主题分类迁移到 ARCHIVE.md。

## 步骤

1. **读 `mem/MEMORY.md`** 全文

2. **扫描所有带日期的条目**（格式 `(YYYY-MM-DD)`），找出**超过 30 天**的条目

3. **如果没有过期条目**，告知用户"没有需要归档的条目"并结束

4. **读 `mem/ARCHIVE.md`**（如不存在则创建）

5. **按主题分类迁移**过期条目到 ARCHIVE.md：
   - 哲学与信念 → 来自 Recent Signals/Frameworks 中的认知类
   - 技术与信号 → 来自 Recent Signals 中的技术/市场类
   - 框架与方法 → 来自 Recent Frameworks
   - 行动与记录 → 来自 Recent Actions / Recent Decisions

6. **从 MEMORY.md 中移除已迁移条目**

7. **不要移动以下内容**：
   - `Current State` 段（永远保留）
   - `Pending Implementation` 段（待办无过期，手动清理）
   - `Calibration Log` 最近 5 条

8. **更新两个文件的 `Last updated` 时间戳**

9. **输出归档摘要**：迁移了多少条目，各归入哪个分类
