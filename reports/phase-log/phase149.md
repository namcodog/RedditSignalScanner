# Phase 149 - Admin 侧栏补齐社区导入入口

日期：2026-01-22

## 目标
- 在 Admin 侧栏补齐“社区导入”入口，保证页面可达。

## 变更
- `frontend/src/components/AdminLayout.tsx`：
  - 侧栏新增“社区导入”导航入口，指向 `/admin/communities/import`。
- `frontend/src/components/__tests__/AdminLayout.test.tsx`：
  - 新增测试，验证侧栏存在社区导入入口。

## 测试
- 未运行（仅新增导航与测试用例）。

## 结果
- Admin 侧栏入口补齐，可直接进入导入页。
