# DAY14 QA 系统测试 Speckit 计划

> 验收结论（2025-10-15）：Phase 0-4 全部通过。指标与证据详见 reports/phase-log/DAY14-QA-测试结果.md（含 Phase 2 SLA JSON、Phase 3/4 JUnit）。测试执行已切换至安全版启动器（backend/scripts/pytest_safe.sh），杜绝 pytest 静默无输出。


> **生成方式**: 基于 `spec-kit` 的 `/speckit.plan` 模板（`tmp/.codex/prompts/speckit.plan.md`）手动对照执行，并引自 `docs/PRD/PRD-08-端到端测试规范.md` 与 `docs/2025-10-10-实施检查清单.md`。

## 技术上下文

- **端到端范围**：注册→登录→分析任务→SSE 进度→报告生成，涵盖缓存、任务队列、外部 Reddit API（`docs/PRD/PRD-08-端到端测试规范.md`）。
- **性能基线**：注册 <30s、登录 <1s、任务提交 <200ms、完成 <5 分钟、报告 <2s、API P95 <500ms、缓存命中率 >90%（同上 PRD）。
- **故障注入目标**：Redis 失效、PostgreSQL 慢查询、Celery Worker 崩溃、Reddit API 429 限流、网络延迟≥5s（PRD-08 §2.2）。
- **多租户隔离**：租户 A/B 互访禁止、JWT 过期可靠驱逐（PRD-08 §2.3）。
- **质量门禁**：测试需满足 `docs/2025-10-10-质量标准与门禁规范.md` 的零容忍原则（无失败、无类型逃逸、无未解指标）。
- **执行节奏**：Day14 日程与交付参考 `reports/phase-log/DAY14-任务分配表.md`。

## 宪章校验

| 准则 | 对应动作 |
| --- | --- |
| “代码永远落后于 PRD” (`AGENTS.md`) | 每个测试映射 PRD-08 场景与 SLA。 |
| “先计划、先测试” (`docs/2025-10-10-实施检查清单.md`) | 发布此计划后再执行或补测。 |
| “问题反馈四问” (`AGENTS.md`) | 各测试脚本/报告需按四问记录。 |
| MCP 强制链路 (`AGENTS.md`) | Serena → SequentialThinking → Exa-code → Chrome DevTools → Speckit (本计划阶段完成 Speckit；执行阶段按链路逐一应用)。 |

**结论**：无违例；所有测试必须输出可追溯 PRD 引用与四问记录。

## 阶段规划

### Phase 0：环境与基础验证（09:00-09:30）

- `make services-up` 启动 PostgreSQL、Redis、Celery、FastAPI。
- 使用 Serena (`serena-cli status`) 确认工程启用，列出未完成测试脚本状态。
- `pytest backend/tests/e2e --maxfail=1 --collect-only` 验证测试收敛。
- 记录环境状态至 `reports/phase-log/DAY14-QA-测试结果.md` 起始段。

### Phase 1：完整流程测试（09:30-12:00）

| 步骤 | 工具/脚本 | SLA & 验证 |
| --- | --- | --- |
| 注册 & 登录 | `backend/tests/e2e/test_complete_user_journey.py::test_complete_user_journey_success` | 记录注册/登录耗时，目标 <0.5s。 |
| 任务提交 | 同上 | 响应 <0.5s，返回 task_id。 |
| 等待分析 | `wait_for_task_completion` | 完成耗时 <30s（测试收紧）。 |
| 报告获取 | 同上 | 响应 <2s，数据完整度（痛点≥5、竞争≥3、机会≥3、缓存命中≥0.9）。 |
| 报告验证 | 解析 payload | 结构/字段匹配 PRD-05/PRD-03。 |

输出：测试日志 + 结果摘要写入 `reports/phase-log/DAY14-QA-测试结果.md`。

### Phase 2：性能压力测试（13:00-15:00）

| 场景 | 脚本 | 指标 |
| --- | --- | --- |
| 并发 10 用户 | `backend/tests/e2e/test_performance_stress.py::test_concurrent_users` | 成功率=100%，P95<500ms。 |
| 高负载 50 任务 | `test_performance_stress.py::test_high_volume_tasks` | 任务耗时统计 + 队列积压监控。 |
| 缓存命中率 | `test_real_cache_hit_rate.py`（如需） | 命中率 ≥90%。 |
| API 响应时间 | pytest 输出 + `scripts/perf_collect.py`（如有） | 收集 P50/P95/P99。 |

操作：运行 pytest，加上 `--maxfail=1 --durations=0`，并使用 Chrome DevTools MCP 对前端 SSE 端点进行抽样性能测量，记录 TTFB。

### Phase 3：故障注入（15:00-17:00）

| 故障 | 操作 | 预期行为 |
| --- | --- | --- |
| Redis 宕机 | `scripts/faults/redis_down.sh` 或 `docker stop redis` | 系统降级提示、任务仍完成（<=10 分钟）。 |
| PostgreSQL 慢查询 | `scripts/faults/pg_slow.sh` | API 自动超时/重试、用户反馈明确。 |
| Celery Worker 崩塌 | `scripts/faults/kill_worker.sh` | 重试 3 次 → 成功或明确失败说明。 |
| Reddit API 429 | `backend/tests/e2e/test_fault_injection.py::test_rate_limit_handling` | 降级使用缓存/提示稍后再试。 |

执行顺序：单故障依次注入→恢复→验证→记录。每轮需收集日志 (`logs/*.log`) 并附四问分析。

### Phase 4：多租户隔离（17:00-17:30）

- 运行 `backend/tests/e2e/test_multi_tenant_isolation.py`。
- 检查：
  - 租户 A 无法访问 B 的任务/报告（404）。
  - JWT 过期后拒绝旧请求（401）。
  - 并发访问不会泄露数据（SSE 频道隔离）。
- 结果写入报告，并截取关键日志。

## 工件与输出

1. pytest 结果（`backend/tests/e2e/*.py`）全部通过并产生新的基准数据。
2. `reports/phase-log/DAY14-QA-测试结果.md` 补充：
   - 测试摘要（含 SLA 指标表）。
 	- 故障注入日志分析（按四问结构）。
   - 后续风险/建议。
3. 如发现缺口，先更新 PRD/Checklist，再提出修复任务。

## 风险与缓解

| 风险 | 缓解措施 |
| --- | --- |
| Redis/PG/Celery 操作破坏长期环境 | 使用 `scripts/faults/*` 自带恢复步骤；测试后执行 `scripts/cleanup_env.sh`。 |
| 性能测试影响他人 | 在独立测试环境执行；如需共享环境，提前通知 Lead。 |
| 指标波动难判断 | 结合 Chrome DevTools MCP + server logs 交叉验证。 |
| SLA 未达标 | 立即使用 Serena 定位瓶颈，调用 SequentialThinking 工具梳理根因，再提修复计划。 |

## 下一步

1. 执行 Phase 0，确认环境与测试脚本状态。
2. 按时间表推进 Phase 1-4，过程中遇阻立即停下排查。
3. 结束后更新 `reports/phase-log/DAY14-QA-测试结果.md` 和相关 PRD 条目。

