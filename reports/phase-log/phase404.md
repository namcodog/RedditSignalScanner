# Phase 404 - 截图级验收与完整正式 E2E 复核

## 背景

`Phase 403` 已经把：

- `InputPage`
- `ProgressPage`
- `AdminLayout`
- `AdminRoute`

一起收进了新的视觉系统，产品体感已经来到约 `96-97`。

这轮不再继续铺新设计，而是做两件更关键的事：

1. 用真实浏览器把桌面端和移动端再验一遍
2. 跑完整正式 E2E，确认“像成品”不是只停留在截图层

---

## 本轮发现

### 1. 桌面端和移动端的主链页面，完成感已经基本站住

这轮实际过掉了这些真实页面：

- 输入页
- 等待页
- 报告页
- hotpost 结果页
- admin 控制面

并且都留下了真实截图：

- `output/playwright/phase404-browser/input-desktop.png`
- `output/playwright/phase404-browser/progress-desktop.png`
- `output/playwright/phase404-browser/report-desktop.png`
- `output/playwright/phase404-browser/hotpost-desktop.png`
- `output/playwright/phase404-browser/admin-desktop.png`
- `output/playwright/phase404-browser/input-mobile.png`
- `output/playwright/phase404-browser/progress-mobile.png`
- `output/playwright/phase404-browser/report-mobile.png`
- `output/playwright/phase404-browser/hotpost-mobile.png`
- `output/playwright/phase404-browser/admin-mobile.png`

结论：

- 这套产品已经不只是“结果页像成品”
- 输入、等待、结果、控制面四段体验已经基本处在同一档完成感

### 2. 验收过程中暴露出一个真实链路细节：浏览器上下文脏了会误判成权限问题

本轮在移动端 `progress` 验收时，先遇到一次 `403`。

最后确认根因不是产品权限坏了，而是：

- 浏览器里残留着旧登录态
- 我手动切 token 时又写错了 localStorage key
- 结果新任务 owner 和当前 token 不一致，才被状态页拦住

处理方式不是改产品代码，而是：

- 清理浏览器上下文
- 用项目固定测试账号 `test@test.com`
- 现场重新创建一条真实任务

重新跑之后：

- `progress` 页面正常
- `status` 接口正常
- SSE 正常

这说明产品主链没坏，问题在验收上下文，不在业务逻辑。

### 3. `free` 会员访问报告被拦，是当前产品规则，不是回归

本轮用 `test@test.com` 跑完新任务后，等待页正常跳转到报告页，但报告接口返回：

- `403`
- `Your subscription tier does not include report access`

这不是新 bug，而是当前会员权限规则本来就这样。

所以这轮验收里要区分两件事：

- 等待链路：已经正常
- free 用户直进报告：按当前产品规则会被挡住

这点需要作为真实产品事实记录下来，避免以后把权限设计误判成回归。

---

## 本轮执行

### A. 完成截图级浏览器验收

实际操作：

- 确认本地 backend / frontend 服务可用
- 使用 Playwright 真浏览器复验桌面端和移动端
- 补齐 `progress-mobile.png`

验收范围：

- 桌面端：输入、等待、报告、hotpost、admin
- 移动端：输入、等待、报告、hotpost、admin

### B. 清理验收上下文误差，不把脏浏览器状态当产品问题

本轮中途做了两次纠偏：

- 确认前端真正读取的是 `auth_token`，不是旧 key
- 确认 `phase404-acceptance@example.com` 并不是库里真实用户，不能再拿手工造 token 冒充正式验收用户

最终统一改用项目固定测试账号：

- `test@test.com`

### C. 跑完整正式 E2E 复核

执行命令：

- `make test-e2e`

结果：

- `21 passed`

说明：

- 当前正式 E2E 世界观仍然和产品一致
- `Phase 403` 没有把真链路带坏
- 这轮截图级验收和完整正式 E2E 之间没有打架

---

## 验证结果

### 浏览器验收

- 桌面端截图：已完成
- 移动端截图：已完成
- 其中移动端 `progress` 已用真实新任务 `4de6ffc3-7e5b-4d25-9aee-242d6efd6be1` 复验通过

### 正式 E2E

- `make test-e2e`
- 结果：`21 passed`

---

## 当前判断

这轮做完后，我不会把产品直接拉到 `98`。

更稳的判断是：

- 当前大概仍在 `96-97`

原因是：

- 主链体验和正式验收都已经站住
- 截图级验收也没再打出大的断点
- 但最后一层“精品感”还有一点点空间，尤其是个别真实状态话术、留白密度和过渡细节

一句大白话：

- 现在已经很像成熟产品了
- 但还没到“随便截哪一屏都像上线精品”的 `98`

---

## 下一步建议

如果继续冲，就开 `Phase 405`，只做最后一轮小而狠的收口：

1. 只看截图里还略掉档的细节
2. 再收一轮留白、层级、过渡和状态文案
3. 复跑 `make test-e2e`
4. 最后再决定能不能给 `98`

如果不继续冲，这一轮已经足够作为当前阶段验收点。

---

## 本轮价值

这轮最值钱的，不是又多了几个截图。

真正的价值是：

- 我们确认了这套产品现在不只是“局部页面变好看”
- 而是桌面端、移动端、正式 E2E 三条线都能对得上

一句话收口：

- 现在这套产品已经很接近最后的精品线了，剩下的是最后一层微调，不是大改。
