# Phase 662 - Signal Input Quality Gate Wired Into Production Path

## 结果

`signal input quality gate` 已经不再停留在离线审计层，而是正式接进了 `signal` 生成主链。

接入位置：

- `backend/app/services/hotpost/card_content_generator.py`
- 只对 `ValidationCardDraft` 生效
- 在进入 LLM 之前先做输入质量判断
- 命中闸门则直接报错，不再继续生成

新增与修改：

- `backend/app/services/hotpost/signal_input_quality.py`
- `backend/tests/services/hotpost/test_signal_input_quality.py`
- `backend/tests/services/hotpost/test_card_content_generator.py`
- `backend/tests/api/test_hotpost_card_candidates.py`

## 当前行为

现在对于这类样本，系统会直接拦住：

- 单帖弱证据
- 单社区弱证据
- 主要 quote 来自：
  - bot / automod
  - 公版提醒
  - 寒暄废话

而不会再把它们送进 LLM 生成一张看起来顺、实际上没价值的 signal 卡。

## 验证结果

定向测试：

- `backend/tests/services/hotpost/test_card_content_generator.py`
- `backend/tests/api/test_hotpost_card_candidates.py`
- `backend/tests/services/hotpost/test_signal_input_quality.py`

结果：

- `19 passed`

离线审计复核：

- `sample_count = 36`
- `blocked_fail_count = 9`
- `blocked_pass_count = 0`

说明：

- 当前闸门仍然能稳定提前挡掉 `9` 条 judge 已判死的垃圾样本
- 接入生产路径后没有新增误伤证据

## 当前判断

这一步把主矛盾再次往前推了一层：

- 之前是“prompt 怎么写更好”
- 现在先解决了“哪些输入根本不该写”

只有把这道闸先接进去，后面的 prompt 优化才不会一直在垃圾样本上浪费时间。

## 下一步

下一步应直接做：

1. 重跑 `signal eval set`
2. 重跑 `signal judge`
3. 对比接闸前后的：
   - pass/fail 分布
   - 高失败标签分布
4. 再判断第二轮 prompt 优化是否还值得继续推进
