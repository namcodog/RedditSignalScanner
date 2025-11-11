# 语义库开发快速启动指南

> **配套文档**: `.specify/specs/011-semantic-lexicon-development-plan.md`  
> **目标**: 5 分钟内启动 P0 任务

---

## 🚀 立即开始（复制粘贴即可）

### Step 1: 环境准备（1 分钟）

```bash
# 进入项目目录
cd /Users/hujia/Desktop/RedditSignalScanner

# 激活虚拟环境（如果有）
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖（如果缺失）
pip install pyyaml
```

---

### Step 2: 创建工作目录（30 秒）

```bash
# 创建必要的目录
mkdir -p backend/reports/local-acceptance
mkdir -p backend/config/semantic_sets/versions
mkdir -p backend/tests/services/analysis

# 备份当前词库
cp backend/config/semantic_sets/crossborder.yml \
   backend/config/semantic_sets/versions/crossborder_v1.0_backup_$(date +%Y%m%d).yml

echo "✅ 工作目录创建完成"
```

---

### Step 3: 创建 CHANGELOG（1 分钟）

```bash
cat > backend/config/semantic_sets/CHANGELOG.md << 'EOF'
# Semantic Lexicon Changelog

## [v1.1] - 2025-01-04 (In Progress)

### Added
- 待补充：pain_points 挖掘结果

### Changed
- 待更新：precision_tag 匹配策略

### Fixed
- 待修复：已知问题

---

## [v1.0] - 2024-12-20

### Added
- 初始版本，包含 4 个主题 × 3 类词
- brands=13, features=30, pain_points=12-15
- 基础 aliases 和 exclude 列表

### Notes
- 基于人工策划的种子词
- 简单正则匹配
EOF

echo "✅ CHANGELOG 创建完成"
```

---

### Step 4: 检查数据文件（30 秒）

```bash
# 检查是否有候选数据文件
if [ -f "backend/data/crossborder_candidates.json" ]; then
    echo "✅ 数据文件存在，可以运行 pain_points 挖掘"
    echo "   文件大小: $(du -h backend/data/crossborder_candidates.json | cut -f1)"
else
    echo "⚠️  数据文件不存在: backend/data/crossborder_candidates.json"
    echo "   请先运行数据采集任务，或使用测试数据"
    echo ""
    echo "   临时方案：创建空文件（跳过挖掘）"
    echo "   mkdir -p backend/data"
    echo "   echo '[]' > backend/data/crossborder_candidates.json"
fi
```

---

### Step 5: 运行 pain_points 挖掘（2 分钟）

```bash
# 如果数据文件存在，运行挖掘
python backend/scripts/mine_pain_points.py \
  --data backend/data/crossborder_candidates.json \
  --lexicon backend/config/semantic_sets/crossborder.yml \
  --output backend/reports/local-acceptance/pain_points_candidates.csv \
  --min-freq 5

# 查看结果
if [ -f "backend/reports/local-acceptance/pain_points_candidates.csv" ]; then
    echo ""
    echo "✅ 挖掘完成！TOP 10 候选词："
    head -n 11 backend/reports/local-acceptance/pain_points_candidates.csv | column -t -s,
    echo ""
    echo "📝 下一步：打开 CSV 文件，人工审核并挑选 TOP 30"
    echo "   open backend/reports/local-acceptance/pain_points_candidates.csv"
else
    echo "⚠️  挖掘失败，请检查错误信息"
fi
```

---

## 📋 P0 任务清单（本周完成）

### ✅ 任务 1: 补充 pain_points 词库（4h）

**当前进度**: 
- [x] 创建挖掘脚本 `mine_pain_points.py`
- [ ] 运行挖掘（上面 Step 5）
- [ ] 人工审核 TOP 30
- [ ] 更新 `crossborder.yml`
- [ ] 更新版本号为 v1.1

**人工审核步骤**:
```bash
# 1. 打开 CSV
open backend/reports/local-acceptance/pain_points_candidates.csv

# 2. 在 Excel/Numbers 中：
#    - 按 frequency 降序排序
#    - 挑选 TOP 30 高质量词
#    - 标记为 "approved"

# 3. 手动编辑 crossborder.yml
#    将审核通过的词加入各主题的 pain_points 列表

# 4. 更新版本号
#    在 crossborder.yml 顶部：version: 1 → version: 1.1

# 5. 更新 CHANGELOG
#    记录新增的 pain_points
```

---

### ✅ 任务 2: 实现 precision_tag 真实匹配（6h）

**当前进度**:
- [x] 创建 `hybrid_matcher.py`
- [ ] 编写测试
- [ ] 运行测试
- [ ] 集成到 `score_with_semantic.py`

**执行步骤**:
```bash
# 1. 创建测试文件
cat > backend/tests/services/analysis/test_hybrid_matcher.py << 'EOF'
import pytest
from backend.app.services.analysis.hybrid_matcher import HybridMatcher, Term

def test_exact_matching():
    """测试 exact 匹配（词边界）"""
    terms = [
        Term(
            canonical="Amazon",
            aliases=["AMZ"],
            precision_tag="exact",
            category="brands",
        )
    ]
    matcher = HybridMatcher(terms)
    
    # 应该匹配
    results = matcher.match_text("I sell on Amazon")
    assert len(results) == 1
    assert results[0].canonical == "Amazon"
    assert results[0].match_type == "exact"
    
    # 应该匹配别名
    results = matcher.match_text("AMZ fees are high")
    assert len(results) == 1
    
    # 不应该匹配（不是词边界）
    results = matcher.match_text("Amazonian rainforest")
    assert len(results) == 0

def test_phrase_matching():
    """测试 phrase 匹配（短语）"""
    terms = [
        Term(
            canonical="dropshipping",
            aliases=["drop shipping"],
            precision_tag="phrase",
            category="features",
        )
    ]
    matcher = HybridMatcher(terms)
    
    # 应该匹配
    results = matcher.match_text("I do dropshipping")
    assert len(results) == 1
    
    # 应该匹配别名
    results = matcher.match_text("drop-shipping is hard")
    assert len(results) >= 1

def test_aggregation():
    """测试聚合功能"""
    terms = [
        Term(canonical="Amazon", aliases=[], precision_tag="exact", category="brands"),
        Term(canonical="Shopify", aliases=[], precision_tag="exact", category="brands"),
        Term(canonical="FBA", aliases=[], precision_tag="phrase", category="features"),
    ]
    matcher = HybridMatcher(terms)
    
    text = "I sell on Amazon using FBA and also on Shopify"
    results = matcher.match_text(text)
    
    # 按类别聚合
    by_category = matcher.aggregate_by_category(results)
    assert by_category["brands"] == 2
    assert by_category["features"] == 1
    
    # 按规范名聚合
    by_canonical = matcher.aggregate_by_canonical(results)
    assert by_canonical["Amazon"] == 1
    assert by_canonical["Shopify"] == 1
    assert by_canonical["FBA"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
EOF

# 2. 运行测试
pytest backend/tests/services/analysis/test_hybrid_matcher.py -v

# 3. 如果测试通过，集成到 score_with_semantic.py
#    （需要修改 score_theme 函数）
```

---

### ✅ 任务 3: 建立词库版本管理（2h）

**当前进度**:
- [x] 创建 CHANGELOG.md（上面 Step 3）
- [x] 创建 versions/ 目录（上面 Step 2）
- [ ] 制定版本管理规范

**版本管理规范**:
```bash
# 版本号规则：v{major}.{minor}
# - major: 大版本（架构变更、不兼容更新）
# - minor: 小版本（新增词、优化）

# 每次更新词库时：
# 1. 备份当前版本
cp backend/config/semantic_sets/crossborder.yml \
   backend/config/semantic_sets/versions/crossborder_v{old_version}.yml

# 2. 更新版本号
# 在 crossborder.yml 顶部修改 version 字段

# 3. 更新 CHANGELOG
# 记录 Added/Changed/Fixed

# 4. 提交 Git
git add backend/config/semantic_sets/
git commit -m "feat(lexicon): update to v{new_version} - {summary}"
```

---

## 🎯 验收标准（自检清单）

### P0 完成标准

- [ ] `pain_points_candidates.csv` 存在且包含 ≥ 50 条
- [ ] 人工审核通过 ≥ 30 条，加入词库
- [ ] 词库版本号更新为 `v1.1`
- [ ] `CHANGELOG.md` 记录了变更
- [ ] `HybridMatcher` 测试通过率 100%
- [ ] `versions/` 目录包含 v1.0 备份

### 质量门禁

```bash
# 运行质量检查
cd backend

# 1. 代码格式
black app/services/analysis/hybrid_matcher.py
isort app/services/analysis/hybrid_matcher.py

# 2. 类型检查
mypy --strict app/services/analysis/hybrid_matcher.py

# 3. 测试
pytest tests/services/analysis/test_hybrid_matcher.py -v

# 如果全部通过，说明 P0 完成 ✅
```

---

## 🔍 常见问题

### Q1: 数据文件不存在怎么办？

**A**: 有两个选择：
1. **推荐**: 先运行数据采集任务，生成真实数据
2. **临时**: 创建空文件跳过挖掘，直接人工补充 pain_points

```bash
# 临时方案
mkdir -p backend/data
echo '[]' > backend/data/crossborder_candidates.json
```

---

### Q2: 挖掘出的候选词质量太低？

**A**: 调整参数：
```bash
# 提高频次阈值（默认 5 → 10）
python backend/scripts/mine_pain_points.py \
  --min-freq 10 \
  ...

# 或者直接人工补充高质量词
```

---

### Q3: 测试失败怎么办？

**A**: 检查依赖：
```bash
# 确保安装了 pytest
pip install pytest

# 检查导入路径
python -c "from backend.app.services.analysis.hybrid_matcher import HybridMatcher"

# 如果报错，检查 __init__.py 文件是否存在
```

---

## 📞 需要帮助？

- 查看完整计划: `.specify/specs/011-semantic-lexicon-development-plan.md`
- 查看原始思路: `词义库思路.md`
- 查看项目规范: `AGENTS.md`

---

**下一步**: 完成 P0 后，继续 P1 任务（候选词挖掘、质量指标看板）

