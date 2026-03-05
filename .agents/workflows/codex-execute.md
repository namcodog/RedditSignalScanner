---
description: Opus 设计架构 → Codex 执行代码 → Opus 自动验收的全自动流水线
---

# Opus 总指挥 — 多引擎联动工作流

## 角色分工

| 角色 | 引擎 | 职责 |
|------|------|------|
| 🧠 总架构师 | Opus (Antigravity) | 需求拆解、架构设计、任务分配、验收质检 |
| 🔧 后端工程师 | Codex CLI | 后端代码实现、API开发、数据库、脚本、测试 |
| 🎨 前端工程师 | Gemini CLI | 前端UI实现、组件开发、样式、交互 |

## 核心原则
- **Opus 推理强** → 负责想清楚"怎么做"和"做得对不对"
- **Codex 工程强** → 负责后端代码落地
- **Gemini 前端强** → 负责前端代码落地
- **每次只做一件事**，做完验收再做下一件

---

## 流程

### Step 1: Opus 拆解需求 & 设计架构
根据用户需求，Opus 输出结构化方案：

**后端任务** → 保存到 `/tmp/codex_task.md`
**前端任务** → 保存到 `/tmp/gemini_task.md`

每份任务文档包含：
- 任务目标（一句话）
- 需要修改/创建的文件清单
- 每个文件的具体实现说明（函数签名、逻辑、参数）
- 验收标准（怎样算"做完了"）
- 约束条件（不能改什么、风格要求等）

### Step 2a: 后端 — 调用 Codex 执行
// turbo
```bash
codex exec --full-auto \
  -C /Users/hujia/Desktop/RedditSignalScanner \
  -o /tmp/codex_result.md \
  "$(cat /tmp/codex_task.md)"
```

### Step 2b: 前端 — 调用 Gemini 执行
// turbo
```bash
cd /Users/hujia/Desktop/RedditSignalScanner && \
gemini -p "$(cat /tmp/gemini_task.md)" -y 2>&1 | tee /tmp/gemini_result.md
```

注意：
- 前后端任务如果没有依赖关系，可以**并行执行**
- 有依赖关系时（比如前端依赖后端API），先跑后端，验收通过后再跑前端

### Step 3: 监控执行
通过 `command_status` 工具持续监控两个引擎的执行状态。

### Step 4: Opus 自动验收
执行完毕后，Opus 依次检查：

**代码级：**
1. `git diff` — 查看所有改动
2. 逐文件审查 — 是否符合架构设计
3. 代码风格 — 是否符合项目规范

**功能级：**
4. 后端测试 — `pytest` 相关测试用例
5. 前端构建 — `npm run build` 是否通过
6. 集成检查 — 前后端是否能联调

### Step 5: 迭代修复（如果验收不通过）
- **小问题**: Opus 直接修复
- **后端大问题**: 生成新的 codex_task.md，让 Codex 重做
- **前端大问题**: 生成新的 gemini_task.md，让 Gemini 重做

### Step 6: 完成汇报
验收通过后，向用户汇报：
- 做了什么改动（前端 + 后端）
- 改了哪些文件
- 测试是否通过
- 有没有遗留风险

---

## 快捷用法

用户只需要说需求，Opus 自动判断前后端分工：
- 纯后端任务 → 只调 Codex
- 纯前端任务 → 只调 Gemini
- 全栈任务 → 先 Codex 后端，再 Gemini 前端

## 紧急参数参考

**Codex:**
- 换模型: `-m "o3"`
- 全权限: `-s danger-full-access`
- JSON输出: `--json`

**Gemini:**
- 换模型: `-m "gemini-2.5-pro"`
- 沙箱模式: `-s`
- 自动批准编辑: `--approval-mode auto_edit`
