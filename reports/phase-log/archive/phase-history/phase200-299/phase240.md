# Phase 240 — 跨品类确定性验证（最终版）

> 执行时间: 2025-03-11 ~ 2025-03-12
> 验证范围: 8 大领域 × 2 次 = 16 次运行
> 最终结果: **8/8 PASS — 100% HASH MATCH 🏆**

## 修复旅程

| 轮次 | 修复 | 结果 |
|:----:|------|:----:|
| R0 | — | 0/8 |
| R1 | FIX-1~5: anchor_ts + dedup排序 + bucketing排序 + 质量门磁滞 | 1/8 |
| R2 | FIX-6~7: --anchor-ts CLI + pains fallback + JIT skip | 1/8 |
| **R3** | **FIX-8~11: LLM扩展跳过 + t1_stats.py 10处NOW()消除 + persona/brands跳过** | **8/8 🏆** |

## 最终哈希结果

| 领域 | SHA-1 | 状态 |
|------|-------|:----:|
| Home_Lifestyle | `90905bcc...` | ✅ |
| Family_Parenting | `41dab538...` | ✅ |
| Ecommerce_Business | `70e4db46...` | ✅ |
| Tools_EDC | `99e812cd...` | ✅ |
| Food_Coffee_Lifestyle | `5aa51537...` | ✅ |
| Minimal_Outdoor | `6edb774e...` | ✅ |
| Frugal_Living | `91983d32...` | ✅ |
| AI_Workflow | `bc35bed0...` | ✅ |

## 定位的根因总结

1. `generate_t1_market_report.py` 中 13 处 `NOW()` → `anchor_ts`
2. `t1_stats.py` 中 10 处 `NOW()` → `anchor_ts`（FIX-1 遗漏的文件）
3. `_expand_topic_semantically()` LLM temperature=0.3 非确定性
4. Dedup 输入未排序 + Bucketing 遍历未排序
5. JIT labeling / persona / brands LLM 副作用
6. V1→V2 pains 格式切换阈值边界

## 确定性模式机制

传入 `--anchor-ts` 时自动启用：
- 固定时间锚点（全链路统一）
- 跳过 LLM 语义扩展（用简单分词）
- 跳过 JIT labeling 数据库副作用
- 跳过 persona / brands LLM 调用
- 稳定 run_id / snapshot_id / report_id
