# phase1036

## 这轮达到的目的

V13 title 主体规则进入全量 shadow 分批执行，按“正常吐进度就继续等”的规则跑完 batch005 到 batch007。

## 当前状态变化

batch005 主批 `18/20`，2 张因 banned pattern 被拦；失败 2 张单独重跑 `2/2` 通过。batch006 `20/20`，batch007 `20/20`。三批补跑后 title issues `0`，density issues `0`。

## 还没完成什么

这仍是 shadow 重跑，没有写回线上卡。OpenRouter 上游 deepseek 仍偶发 `429`，但本轮均能恢复或通过失败卡重跑补齐。

## 下一步做什么

人工审核 batch005/006/007 报告；继续从 `offset=140` 跑 batch008，保持 `limit=20, workers=2`。
