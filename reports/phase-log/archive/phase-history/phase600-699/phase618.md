# Phase 618 - Hotpost Rant 样本真值三层拆分落地

## 时间
- 2026-03-30

## 目标
- 把第二刀从“文案诚实”推进到“链路真值”
- 让系统正式区分：
  - 总帖子少
  - 高相关少
  - 原话少

## 发现了什么？

### 1. 只改 note 还不够
- 如果链路里没有正式的样本真值分层
- 系统还是只能靠猜
- 所以第二刀必须把真值指标正式拆出来

### 2. 当前最该拆的是 3 层
1. `raw_posts`
2. `relevant_posts`
3. `voice_hits`

## 是否需要修复？
- 需要。
- 这轮直接落到链路与 debug_info，不再只停在页面文案。

## 精确修复方法

### 一、evidence 层新增 `relevant_posts`
- `backend/app/services/hotpost/evidence_collection_workflow.py`
  - 记录限流前的高相关总量

### 二、结果层新增 `voice_hits`
- `backend/app/services/hotpost/mode_contract.py`
  - 直接用强原话数参与 reliability note 判断
- `backend/app/services/hotpost/response_bundle.py`
  - 将 `relevant_posts / voice_hits` 写入 `debug_info`

### 三、搜索层完成透传
- `backend/app/services/hotpost/search_workflow.py`
  - 透传 `relevant_posts`
  - 保持对旧测试 stub 的兼容

### 四、前后端类型同步
- `backend/app/schemas/hotpost.py`
- `frontend/src/types/hotpost.ts`
- `hotpost-mini/hotpost-mini-app/src/services/hotpost.ts`

## 下一步系统性计划

1. 第三刀直接转：
   - `voices-first`
2. 第一屏先做：
   - 代表原话
   - 骂点
   - 对比/迁移
3. 不再让前端替后端补二次推导

## 这次执行的价值是什么？
- 第二刀现在已经真正落地了。
- 后面再看到“结果弱”，系统终于能明确回答：
  - 是帖子没抓到
  - 还是抓到了但不够相关
  - 还是相关有了但原话不够强
