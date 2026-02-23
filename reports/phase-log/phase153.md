# Phase 153 - 用户端 UI E2E 验收（Playwright）

日期：2026-01-23

## 目标
- 修复 Playwright 阻塞并完成用户端 UI E2E（user-journey.spec.ts）。

## 执行
1) 修复 E2E 口径问题  
   - 注册表单补填必填字段（name）  
   - 登录/注册错误校验改为更稳健的断言（token 是否写入）  
   - 适配“快速完成直达报告页/查看报告按钮”的跳转逻辑  
   - 报告页降级时（C_scouting）允许无 Tab  
   - 导出按钮断言对齐真实 UI（“导出报告”）

2) 运行 E2E  
   - `npx playwright test e2e/user-journey.spec.ts`

## 结果
- ✅ 10 passed / 1 skipped（Tab 切换测试仍按原逻辑 skip）
- ✅ 用户端 UI E2E 通过

## 备注
- 仍建议后续补齐：Tab 切换真实任务的可复现数据入口。
