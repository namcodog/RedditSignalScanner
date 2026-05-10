# Phase 651 - 拆解说明补齐 + Suggestion 收紧

## 结果

这轮把上一次审计里两个明确缺口补上了：

- 前端真正补上了 `🔍 拆解` 的解释文案
- `breakdown suggestion` 从“全 pack 粗放建议”收紧成 V1 白名单

现在的真实状态是：

- 用户在首页切到 `🔍 拆解` 时，会看到这不是单帖总结
- 用户打开拆解详情时，会看到这张卡为什么叫“拆解”
- 后端 suggestion 接口只保留更像真拆解的两类：
  - `ecommerce-sellers / selection-signals`
  - `ai-automation / agent-builder`

## 修复内容

### 前端

- 首页新增拆解说明提示
- 详情页 hero 新增拆解解释文案

落点：

- `hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
- `hotpost-mini/hotpost-mini-app/src/constants/card-type-copy.ts`

### 后端

- `breakdown_candidate_clusterer` 增加 V1 白名单 pack
- hypothesis 去掉 `listing:top:day` 这类内部规格词
- suggestion 改成更像人工 review 候选，而不是技术占位句

落点：

- `backend/app/services/hotpost/breakdown_candidate_clusterer.py`
- `backend/tests/services/hotpost/test_breakdown_candidate_clusterer.py`

## 验证

后端定向测试：

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_breakdown_candidate_clusterer.py \
  backend/tests/api/test_hotpost_card_review.py \
  backend/tests/api/test_hotpost_card_candidates.py -q
```

结果：`11 passed`

前端构建：

```bash
cd hotpost-mini/hotpost-mini-app && npm run build:weapp
```

结果：编译通过

运行态烟雾验证：

```bash
GET /api/hotpost/card-review/suggestions?limit=20
```

结果只剩 2 条 suggestion：

- `selection-signals`
- `agent-builder`

且 hypothesis 已不再包含 `listing:*` 这类内部抓取规格词。

## 当前判断

这轮之后，`breakdown suggestion` 的定位更清楚了：

- 不是自动生成拆解卡
- 而是给运营一个更干净的拆解候选池

前端说明缺失这个问题已经不是认知误差，而是实现遗漏；现在已补齐。
