# Phase 617 - Hotpost Rant “样本不足”诚实口径第一轮收口

## 时间
- 2026-03-30

## 目标
- 先把 `rant` 里第一处最伤用户的“假样本不足”口径收掉
- 让结果页开始区分：
  - 真样本少
  - 命中偏了

## 发现了什么？

### 1. 当前用户最烦的不是 preview，而是假话
- 如果系统明明抓到了不少帖子
- 但高相关证据只剩很少
- 继续统一说“样本不足”
- 用户会直接觉得系统在胡说

### 2. 这次最先该收口的是 `reliability_note`
- 小程序和 Web 结果页都会直接展示这句话
- 所以它必须先说真话

## 是否需要修复？
- 需要。
- 但这轮只收口用户可见口径，不顺手扩修 retrieval 主算法。

## 精确修复方法

### 一、让 mode contract 看懂“命中偏了”
- `backend/app/services/hotpost/mode_contract.py`
  - 增加对：
    - `raw_posts`
    - `relevance_filtered`
    - `mode_state_reasons`
    的判断
  - 如果帖子抓到不少、但高相关掉得厉害，就直接说：
    - 更像命中偏了

### 二、把真值传到结果层
- `backend/app/services/hotpost/response_bundle.py`
  - 将 `raw_posts / relevance_filtered` 传给 mode contract

### 三、补测试把口径钉住
- `backend/tests/services/hotpost/test_hotpost_mode_contract.py`
- `backend/tests/services/hotpost/test_hotpost_response_bundle.py`

## 下一步系统性计划

1. 继续第二刀
2. 把：
   - `raw_hits`
   - `relevant_hits`
   - `voice_hits`
   真正拆进链路
3. 让系统以后能明确区分：
   - 样本真少
   - 命中偏了
   - 原话抽取弱

## 这次执行的价值是什么？
- 这轮先把“系统别睁眼说瞎话”这件事做到了第一步。
- 用户现在至少不会再看到那种：
  - 明明抓到很多帖子
  - 却还只会说“样本不足”
  的糟糕体验。
