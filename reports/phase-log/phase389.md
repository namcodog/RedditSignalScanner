# Phase 389 - 官方技能安装：ui-ux-pro-max / superpowers / planning-with-files / web-design-guidelines / frontend-design

## 1. 发现了什么？

这一步不是修系统主链，而是把你指定的 5 个 skill 真正装进 Codex。

先用 Tavily 查了一轮，结论很清楚：

1. `ui-ux-pro-max`
   - 官方来源指向：
     - `nextlevelbuilder/ui-ux-pro-max-skill`
   - 仓库里给 Codex/Claude 共用的技能内容在：
     - `.claude/skills/ui-ux-pro-max`

2. `planning-with-files`
   - 官方来源指向：
     - `OthmanAdi/planning-with-files`
   - 仓库里实际 skill 目录在：
     - `skills/planning-with-files`

3. `web-design-guidelines`
   - 官方来源指向：
     - `vercel-labs/agent-skills`
   - skill 目录在：
     - `skills/web-design-guidelines`

4. `frontend-design`
   - 官方来源指向：
     - `anthropics/skills`
   - skill 目录在：
     - `skills/frontend-design`

5. `superpowers`
   - 官方来源指向：
     - `obra/superpowers`
   - 这个仓库里没有叫 `superpowers` 的单独 skill 目录
   - 真正的官方 skill 名是：
     - `skills/using-superpowers`

所以这一步最关键的发现是：

- **`superpowers` 不是 skill 目录名**
- **在 Codex 里真正应该装的是它官方 skill：`using-superpowers`**
- 为了符合你这次指定的命名，我把它安装成了本地目录名：
  - `~/.codex/skills/superpowers`

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库，没有改业务代码，没有新 migration。  
改的是本机 Codex 技能环境。

## 3. 精确修复方法？

### 3.1 Tavily 查官方来源

本轮明确按你的要求先用了 Tavily，确认了来源：

- `ui-ux-pro-max` -> `nextlevelbuilder/ui-ux-pro-max-skill`
- `planning-with-files` -> `OthmanAdi/planning-with-files`
- `web-design-guidelines` -> `vercel-labs/agent-skills`
- `frontend-design` -> `anthropics/skills`
- `superpowers` -> `obra/superpowers`（实际 skill 为 `using-superpowers`）

### 3.2 安装到 Codex 目录

统一安装到了：

- `~/.codex/skills`

安装结果：

1. `ui-ux-pro-max`
   - `/Users/hujia/.codex/skills/ui-ux-pro-max`

2. `superpowers`
   - `/Users/hujia/.codex/skills/superpowers`
   - 实际来源路径：
     - `obra/superpowers -> skills/using-superpowers`

3. `planning-with-files`
   - `/Users/hujia/.codex/skills/planning-with-files`
   - 这个仓库的安装脚本对临时目录有冲突，最后改成手工从官方 repo 的真实目录复制进 Codex

4. `web-design-guidelines`
   - `/Users/hujia/.codex/skills/web-design-guidelines`

5. `frontend-design`
   - `/Users/hujia/.codex/skills/frontend-design`

### 3.3 当前 Codex 技能目录核对

安装后本机目录已经变成：

- `atlas`
- `frontend-design`
- `llm-label`
- `planning-with-files`
- `playwright`
- `sora`
- `superpowers`
- `ui-ux-pro-max`
- `web-design-guidelines`

## 4. 验证结果

### 4.1 技能目录核对

逐个检查了：

- `~/.codex/skills/ui-ux-pro-max/SKILL.md`
- `~/.codex/skills/superpowers/SKILL.md`
- `~/.codex/skills/planning-with-files/SKILL.md`
- `~/.codex/skills/web-design-guidelines/SKILL.md`
- `~/.codex/skills/frontend-design/SKILL.md`

结果：

- 全部存在

### 4.2 当前已安装技能列表

结果：

- 5 个目标 skill 都已经在 `~/.codex/skills` 下可见

## 5. 下一步系统性的计划是什么？

这里下一步不是继续安装，而是两件事：

1. **重启 Codex**
   - 新安装的 skill 需要重启后，当前会话之外的 Codex 才能稳定识别

2. **后续按需调用**
   - 做前端产品抛光时：
     - `ui-ux-pro-max`
     - `web-design-guidelines`
     - `frontend-design`
   - 做复杂分阶段推进时：
     - `planning-with-files`
   - 需要 superpowers 工作流时：
     - `superpowers`

## 6. 这次执行的价值是什么？达到了什么目的？

这一步的价值很直接：

- 你指定的 5 个技能，已经真正装进 Codex 本机技能目录了
- 后面做产品抛光、页面改版、复杂计划推进，不需要再临时找外部仓库
- 特别是这次把 `superpowers` 的真实官方映射也理顺了，不会再把“仓库名”和“skill 名”混着用

一句大白话收口：

- **现在这 5 个 skill 已经装好，下一步只差重启 Codex，让它们在后续会话里正式生效。**
