# Phase 133 - Admin 后端口径补齐与鉴权收口

日期：2026-01-21

## 目标（说人话）
按 PRD-07 统一 Admin 后端口径：所有 Admin 接口必须鉴权，候选社区可看证据帖。

## 做了什么
- Admin 端点统一加 `require_admin`（dashboard/tasks/users、communities summary/template/import/history、beta feedback）。
- 候选社区列表增加 `evidence_posts`（Top N 证据帖），支持审核展示。
- Excel 导入记录改为使用管理员真实身份写审计字段。
- 测试更新：Admin 鉴权要求、候选证据帖、导入审计。

## 影响范围
- 后端 API 行为调整（Admin 必须鉴权；discovered 返回证据帖）。
- 仅影响 Admin 端与审核流程。

## 验证
- `pytest backend/tests/api/test_admin.py backend/tests/api/test_admin_community_pool.py backend/tests/api/test_admin_community_import.py backend/tests/api/test_beta_feedback.py`
