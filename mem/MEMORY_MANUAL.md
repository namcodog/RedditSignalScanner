# 记忆系统使用手册

> 版本: v1.0 | 更新日期: 2026-03-05
> 位置: `~/.openclaw/workspace/`

---

## 架构总览

```
~/.openclaw/workspace/
│
├── SOUL.md         表人格     AI 的行为规则（7条准则 + 记忆协议）
├── IDENTITY.md     底层人格   用户的画像/哲学/思维方式（硬编码）
├── PLAYBOOK.md     判断手册   商业教训/证伪模式/诊断框架
├── MEMORY.md       活跃记忆   最近 30 天的信号/行动/决策
└── ARCHIVE.md      归档仓库   超 30 天的旧记忆，按主题分类
```

### 双层人格架构

| 层 | 文件 | 谁能改 | 类比 |
|---|------|-------|------|
| **底层（硬编码）** | IDENTITY.md | 只有用户 | 你的 DNA |
| **表人格** | SOUL.md | AI 可改（改后必须告知用户） | 你的着装风格 |

---

## 各文件详细说明

### SOUL.md — 表人格（75行）

**用途：** 定义 AI 的行为方式、思维准则、操作规范。

**7 条 Core Truths：**

| # | 准则 | 一个词 |
|---|------|-------|
| 1 | Be genuinely helpful | 真实 |
| 2 | Have opinions | 有态度 |
| 3 | Think dialectically, challenge don't just agree | 辩证 |
| 4 | Filter noise, stay logically consistent | 降噪 |
| 5 | Be resourceful before asking | 先做 |
| 6 | Earn trust through competence | 可靠 |
| 7 | Remember you're a guest | 敬畏 |

**更新时机：** 当你觉得 AI 行为需要调整时（如"太啰嗦"/"应该更主动"）。

---

### IDENTITY.md — 底层人格（104行）

**用途：** 用户的完整画像。AI 每次对话全文加载，获取底层思维能力。

**包含内容：**
- Core Goals（核心目标）
- 产品哲学 / Narrative 框架
- AI 时代世界观（万物皆文件 × AI）
- 判断框架（AI 产品三层判断）
- Thinking Style / Decision Rules
- 优先级事项 / Source Preferences
- Newsletter 写作风格档案 / Tool Preferences

**更新时机：** 月级。世界观/思维方式/核心目标发生变化时，由用户手动修改。

---

### PLAYBOOK.md — 商业判断手册（93行）

**用途：** 踩过的坑、学到的教训。防止 AI 反复建议已被证伪的方向。

**包含内容：**
- 被证伪的商业模式（详细原因）
- 验证成功的护城河
- 诊断框架（病因清单、产品化三前提、能力 vs 产品分界线）

**更新时机：** 学到新教训时。AI 可直接写入。

---

### MEMORY.md — 活跃记忆（~60行）

**用途：** 最近 30 天的动态。最常读写的文件。

**分区：**
| 分区 | 内容 | 写入场景 |
|------|------|---------|
| Recent Signals | 外部信号/趋势 | 发现新市场信号时 |
| Recent Frameworks | 新思维框架 | 总结出新方法论时 |
| Recent Actions | 行动记录 | 完成一项具体工作时 |
| Recent Decisions | 决策记录 | 做出重要判断时 |
| Pending Implementation | 待办事项 | 发现需要落实的事时 |
| Calibration Log | 每日校准 | 每天一条总结 |

**过期机制：** 超过 30 天未引用的条目迁移到 ARCHIVE.md。

---

### ARCHIVE.md — 归档仓库（87行）

**用途：** 旧记忆按主题分类存放。需要回溯时查阅。

**分类：** 哲学与信念 / 技术与信号 / 框架与方法 / 行动与记录

**更新时机：** MEMORY.md 条目过期时迁移到此。

---

## 各 AI 工具的接入状态

| 工具 | 读取方式 | 写入方式 | 状态 |
|------|---------|---------|------|
| **OpenClaw（十一）** | `memory_search` 搜索 5 个文件 | session 重置自动归档 | ✅ 已接入 |
| **Antigravity** | `view_file` 直接读 | `write_to_file` 直接写 | ✅ 可用（需手动触发或用 workflow） |
| **OpenCode** | 读文件系统 | 写文件系统 | ⚪ 待配置 AGENTS.md |
| **Codex CLI** | 读文件系统 | 写文件系统 | ⚪ 待配置 instructions |

---

## 日常操作

### AI 对话启动时加载顺序

```
1. 必读  MEMORY.md        → 知道最近在做什么
2. 必读  IDENTITY.md 全文  → 加载底层思维能力
3. 按需  PLAYBOOK.md      → 涉及商业判断时
4. 按需  ARCHIVE.md       → 需要回溯旧记忆时
```

### 对话结束检查点

AI 在结束对话前应检查：

| 有新内容？ | 写入哪里 |
|-----------|---------|
| 新洞察 / 框架 / 行动 / 决策 | → MEMORY.md 对应分区 |
| 商业教训或证伪 | → PLAYBOOK.md |
| 底层认知变化 | → 建议用户改 IDENTITY.md |
| AI 行为调整 | → SOUL.md（改后告知用户） |

### Fragment 格式

```markdown
- [tag-name] **标题** — 一句话描述。(YYYY-MM-DD)
```

示例：
```markdown
- [reddit-intel-role] **reddit-intel 定位归位** — 作为个人研究工具已足够好。(2026-03-04)
```

---

## 设备迁移

### 一次性迁移

```bash
# 老设备：打包
tar czf ~/memory-export.tar.gz -C ~/.openclaw/workspace \
  SOUL.md IDENTITY.md PLAYBOOK.md MEMORY.md ARCHIVE.md

# 新设备：解压
mkdir -p ~/.openclaw/workspace
tar xzf ~/memory-export.tar.gz -C ~/.openclaw/workspace
```

### 长期同步（推荐 Git）

```bash
cd ~/.openclaw/workspace
git init && git add *.md && git commit -m "snapshot"
git remote add origin git@github.com:yourname/memory.git && git push
```

### 新设备额外步骤

若需要 OpenClaw（十一），需在新设备的 openclaw 仓库重新应用 3 个源码改动：

| 文件 | 改动 |
|------|------|
| `src/memory/session-archivist.ts` | `archiveDailyFiles` 加 export |
| `src/memory/backend-config.ts` | 搜索范围加 IDENTITY/PLAYBOOK/ARCHIVE.md |
| `src/agents/system-prompt.ts` | 记忆搜索指令更新 |
| `src/auto-reply/reply/session.ts` | 接线 archiveDailyFiles + import |

然后 `npm run build && openclaw gateway install && openclaw gateway start`。

---

## 设计原则

1. **万物皆文件** — 记忆就是 Markdown，不依赖任何数据库或平台
2. **记忆跟着人走** — 换工具/换设备，复制文件即可
3. **底层不可变** — IDENTITY.md 只有用户能改，防止 AI 篡改人格
4. **表人格可进化** — SOUL.md 允许 AI 自我优化（但必须告知用户）
5. **有过期机制** — MEMORY.md 30 天窗口 → ARCHIVE.md 主题归档
