# 第二阶段执行记录：R-F-E 战略校准与自动化 (Phase 2 Execution Log)

**日期**: 2025-12-04
**执行人**: Eleven (Architect) & Product Manager
**状态**: ✅ 已完成 (Completed)

---

## 1. 阶段目标
利用 **System B** 回填的 12 个月全量数据，废弃基于主观判断的 Tier 分级，转向基于 **R-F-E (Recency, Frequency, Engagement)** 模型的动态调度策略，并实现该策略的自动化闭环。

## 2. 核心里程碑 (Milestones)

### ✅ 2.1 混合价值模型 (Hybrid Model)
*   **算法升级**: 从单纯的 90 天平均，升级为 **"三七开混合模型"**。
    *   $$F_{final} = 0.3 \times F_{year} + 0.7 \times F_{month}$$
    *   **价值**: 既保留了老牌社区的历史权重，又敏锐捕捉了 Q4 旺季（如 `r/baking`）的爆发趋势。
*   **僵尸检测**: 引入 `Zombie` (F<0.1, E<5) 判定逻辑。经检测，目前社区池健康度 100%，无僵尸。

### ✅ 2.2 动态调度落地 (Dynamic Scheduling)
*   **动作**: 执行回写脚本，更新 `community_cache`。
*   **策略映射**:
    | Archetype | 特征 | 抓取频率 | 数量 (2025-12-04) |
    | :--- | :--- | :--- | :--- |
    | **🔥 High Traffic** | F > 5 | **2小时** | 138 |
    | **💎 Hidden Gem** | E > 50, F < 2 | **4小时** | 10 |
    | **⭐ Solid Gold** | E > 20 | **6小时** | 25 |
    | **🌱 Growing** | 其他 | **12小时** | 27 |

### ✅ 2.3 自动化闭环 (Automation)
*   **服务化**: 将分析逻辑封装为 `app.services.scheduler_service.recalibrate_crawl_frequencies`。
*   **任务化**: 注册 Celery 任务 `tasks.recalibrate_community_schedules`。
*   **调度化**: 配置 Celery Beat，**每周一凌晨 04:00** 自动执行“体检”与“调频”。

---

## 3. 工具链与脚本 (Toolchain)

| 脚本/文件 | 用途 | 运行方式 |
| :--- | :--- | :--- |
| `backend/scripts/analyze_community_value.py` | **手动分析工具**。打印排行榜，支持 `--apply` 立即生效。 | `python -m ...` |
| `backend/app/services/scheduler_service.py` | **核心服务**。封装了 SQL 查询与写库逻辑。 | 被 Task 调用 |
| `backend/app/tasks/scheduler_task.py` | **任务包装器**。Celery 异步任务入口。 | 自动调度 |

---

## 4. 应急与维护 (Maintenance)

*   **手动触发**: 如果发现市场风向突变，无需等待周一，可直接运行：
    ```bash
    python -m backend.scripts.analyze_community_value --apply
    ```
*   **调整阈值**: 若需修改 "High Traffic" 的定义（如从 5 改为 10），请修改 `analyze_community_value.py` 和 `scheduler_service.py` 中的 `_classify` 函数。

---

**文档维护**: Reddit Signal Scanner Team
