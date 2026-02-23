# 社区池恢复报告

**执行时间**: 2025-11-12 21:00  
**执行人**: 运维工程师（AI Agent）  
**原因**: 用户发现原有 200 个基线社区变成了 128 个

---

## 🚨 问题发现

### 用户反馈
> "啊，我们之前初始的200社区呢？怎么变成128个啦？"

### 问题分析
在清理 Top1000 噪音社区时，我犯了一个严重错误：
1. **误删范围过大**: 删除了所有带 `crossborder_top1000` 标签的社区
2. **未考虑更新情况**: Top1000 导入时更新了 74 个原有基线社区，给它们打上了 `crossborder_top1000` 标签
3. **结果**: 这 74 个原有基线社区被误删

---

## 📊 数据分析

### Top1000 导入时的操作
```
make pool-import-top1000
结果: 新增 926，更新 74
```

这意味着：
- **926 个**是 Top1000 新增的噪音社区（应该删除）
- **74 个**是原有基线社区被 Top1000 更新（不应该删除）

### 清理前的状态
| 类型 | 数量 | 说明 |
|------|------|------|
| 原有基线社区 | 200 | 来自 `community_expansion_200.json` |
| Top1000 新增 | 926 | 噪音社区 |
| 语义评分新增 | 2 | r/Shopify, r/dropshipping |
| **总计** | 1,128 | - |

### 第一次清理后的状态（错误）
| 类型 | 数量 | 说明 |
|------|------|------|
| 保留的原有基线 | 126 | 未被 Top1000 更新的 |
| 语义评分新增 | 2 | r/Shopify, r/dropshipping |
| **活跃总计** | 128 | ❌ 少了 74 个 |
| 被误删的原有基线 | 74 | ❌ 被 Top1000 更新过的 |
| Top1000 噪音 | 926 | ✅ 正确删除 |

### 恢复后的状态（正确）
| 类型 | 数量 | 说明 |
|------|------|------|
| 原有基线社区 | 200 | ✅ 全部恢复 |
| 语义评分新增 | 2 | ✅ 保留 |
| **活跃总计** | 202 | ✅ 正确 |
| Top1000 噪音 | 926 | ✅ 已删除 |

---

## 🔧 恢复操作

### 1. 识别被误删的社区
通过对比 `community_expansion_200.json` 和数据库中的活跃社区，找出 74 个被误删的社区。

### 2. 执行恢复 SQL
```sql
UPDATE community_pool
SET is_active = true,
    updated_at = NOW()
WHERE is_active = false
  AND categories::text LIKE '%top1000%'
  AND name IN (
    'r/Accounting', 'r/AskCulinary', 'r/AskEngineers', ...
  );

-- 影响行数: 74
```

### 3. 验证恢复结果
```sql
SELECT COUNT(*) FROM community_pool WHERE is_active = true;
-- 结果: 202
```

---

## 📋 被恢复的 74 个社区

### 高质量技术社区（10个）
| 社区 | Tier | 质量分 | 说明 |
|------|------|--------|------|
| r/MachineLearning | high | 0.90 | 机器学习 |
| r/artificial | high | 0.85 | 人工智能 |
| r/datascience | high | 0.85 | 数据科学 |
| r/Python | high | 0.80 | Python 编程 |
| r/javascript | high | 0.80 | JavaScript |
| r/programming | high | 0.75 | 编程综合 |
| r/learnprogramming | high | 0.75 | 编程学习 |
| r/cscareerquestions | high | 0.75 | CS 职业 |
| r/gamedev | medium | 0.80 | 游戏开发 |
| r/learnmachinelearning | medium | 0.80 | ML 学习 |

### 高质量商业社区（5个）
| 社区 | Tier | 质量分 | 说明 |
|------|------|--------|------|
| r/startups | high | 0.85 | 创业 |
| r/smallbusiness | high | 0.80 | 小企业 |
| r/marketing | high | 0.75 | 营销 |
| r/digitalnomad | medium | 0.80 | 数字游民 |
| r/sidehustle | medium | 0.70 | 副业 |

### 金融投资社区（8个）
| 社区 | Tier | 质量分 | 说明 |
|------|------|--------|------|
| r/investing | high | 0.75 | 投资理财 |
| r/RealEstate | high | 0.75 | 房地产 |
| r/CryptoCurrency | high | 0.70 | 加密货币 |
| r/financialindependence | medium | 0.80 | 财务自由 |
| r/povertyfinance | medium | 0.75 | 贫困理财 |
| r/Bitcoin | medium | 0.70 | 比特币 |
| r/ethereum | medium | 0.75 | 以太坊 |
| r/options | medium | 0.70 | 期权交易 |

### 职业发展社区（6个）
| 社区 | Tier | 质量分 | 说明 |
|------|------|--------|------|
| r/careerguidance | medium | 0.75 | 职业指导 |
| r/jobs | medium | 0.70 | 求职 |
| r/resumes | medium | 0.75 | 简历 |
| r/productivity | medium | 0.75 | 生产力 |
| r/getdisciplined | medium | 0.80 | 自律 |
| r/selfimprovement | medium | 0.75 | 自我提升 |

### 生活方式社区（15个）
- r/Cooking, r/EatCheapAndHealthy, r/MealPrepSunday, r/budgetfood
- r/Frugal, r/BuyItForLife, r/simpleliving
- r/bodyweightfitness, r/running, r/cycling, r/yoga
- r/intermittentfasting, r/keto, r/loseit, r/nutrition

### 创意与设计社区（6个）
- r/photography, r/graphic_design, r/writing, r/WritingPrompts
- r/Instagram, r/socialmedia

### 技术基础设施社区（10个）
- r/buildapc, r/hardware, r/gadgets, r/pcmasterrace
- r/homelab, r/sysadmin, r/hacking, r/privacy
- r/EngineeringStudents, r/AskEngineers

### 其他社区（14个）
- r/Accounting, r/AskCulinary, r/AskHR, r/CreditCards
- r/DecidingToBeBetter, r/GetMotivated, r/Twitch, r/gaming
- r/truegaming, r/wallstreetbets, r/travel, r/solotravel
- r/learnpython, r/passive_income

---

## 🎯 最终状态

### 社区池统计
```bash
总活跃社区: 202
├── 原有基线: 200 (来自 community_expansion_200.json)
└── 语义新增: 2 (r/Shopify, r/dropshipping)

已禁用社区: 926 (Top1000 噪音)
```

### 分类分布
| 分类 | 数量 | 说明 |
|------|------|------|
| 技术类 | ~80 | 编程、AI、数据科学等 |
| 商业类 | ~50 | 创业、营销、电商等 |
| 金融类 | ~30 | 投资、加密货币、房地产等 |
| 生活类 | ~25 | 健康、饮食、运动等 |
| 职业类 | ~10 | 求职、职业发展等 |
| 其他 | ~7 | 旅行、游戏、设计等 |

---

## 📝 经验教训

### 1. 清理操作要谨慎
- ❌ **错误做法**: 一刀切删除所有带某个标签的数据
- ✅ **正确做法**: 先分析数据来源，区分"新增"和"更新"

### 2. 理解导入脚本的行为
- Top1000 导入脚本会**更新**已存在的社区
- 更新时会覆盖 `categories` 字段，打上 `crossborder_top1000` 标签
- 这导致原有基线社区也带上了 Top1000 标签

### 3. 数据恢复的重要性
- 幸运的是，我们只是标记为 `is_active = false`，而不是物理删除
- 这使得数据恢复成为可能
- 未来应该考虑软删除 + 定期归档机制

### 4. 用户反馈的价值
- 用户及时发现了问题（200 → 128）
- 这避免了更大的数据损失
- 应该建立数据变更监控机制

---

## 🚀 后续改进

### 1. 禁用 Top1000 导入（已完成）
- 不再使用 `make pool-import-top1000`
- 完全依赖语义驱动的社区发现

### 2. 建立数据变更监控
```bash
# 每日检查社区池数量
psql -d reddit_signal_scanner -c "
SELECT COUNT(*) as active_count 
FROM community_pool 
WHERE is_active = true;
"

# 预期: 200-300 之间
# 如果 <200 或 >500，触发告警
```

### 3. 完善清理流程
```bash
# 清理前先备份
pg_dump -d reddit_signal_scanner -t community_pool > backup.sql

# 清理时区分"新增"和"更新"
# 只删除 created_at 在导入时间之后的社区
```

### 4. 更新运维手册
- 移除 Top1000 导入步骤
- 添加数据恢复流程
- 添加清理操作的检查清单

---

## 📁 相关文档

- [spec013-top1000-cleanup-report.md](./spec013-top1000-cleanup-report.md) - Top1000 清理报告
- [community-pool-summary.md](./community-pool-summary.md) - 社区池摘要（需更新）
- [community_expansion_200.json](../../backend/data/community_expansion_200.json) - 原有基线数据

---

**报告状态**: ✅ 恢复完成  
**影响范围**: 恢复 74 个被误删的原有基线社区  
**最终结果**: 202 个活跃社区（200 基线 + 2 语义新增）  
**用户满意度**: ✅ 问题解决  
**最后更新**: 2025-11-12 21:00

