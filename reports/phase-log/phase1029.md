# phase1029：Hotpost V13 全量跑第一批效率测试

## 这轮达到的目的
已用 OpenRouter 当前 key 跑 `20` 张 V13 published shadow，小并发 `workers=2`，只生成审核包，不写历史卡。

## 当前状态变化
本批 `selected=20 / generated=11 / failed=9`。没有出现 `429 / 402` 限流证据；失败主要是内容校验 `6` 个、连接抖动 `2` 个、空返回 `1` 个。

## 还没完成什么
不能继续放大全量。当前瓶颈不是额度，而是中文规则回潮和 OpenRouter 连接层偶发断开。

## 下一步做什么
先收紧内容禁词回潮，并给 shadow run 增加 transient 网络失败重试；再用同一批失败样本复跑，稳定后再开下一批。
