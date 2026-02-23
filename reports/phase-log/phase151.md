# Phase 151 - Admin P0 手工验收（候选/池子/导入/账本）

日期：2026-01-22

## 目标
- 完成 Admin P0 手工验收：候选审核、社区池、导入、任务账本。

## 执行
1) 候选审核  
   - 通过 API 校验 `/api/admin/communities/discovered`  
   - 手动插入测试候选（与社区池同名，满足 FK）  
   - `/api/admin/communities/approve` 成功

2) 社区池  
   - `/api/admin/communities/pool` 可读  
   - `/api/admin/communities/batch` 成功更新 priority  
   - `/api/admin/communities/{name}/tier-audit-logs` 可读  
   - `/api/admin/communities/rollback` 成功回滚

3) 导入（Dry Run）  
   - 构造最小模板 Excel（含必填列）  
   - `/api/admin/communities/import?dry_run=true` 返回 `validated`

4) 任务账本  
   - `/api/admin/tasks/recent` 取 task_id  
   - `/api/admin/tasks/{task_id}/ledger` 返回成功

## 数据准备
- 使用测试库 `reddit_signal_scanner_test`。  
- 导入 1 条社区池记录（真实导入），用于社区池与候选审批流程。

## 结果
- ✅ Admin P0 手工验收全流程通过
