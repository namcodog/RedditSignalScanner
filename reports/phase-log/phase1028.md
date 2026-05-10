# phase1028：Hotpost V13 全量重跑进入 pilot gate

## 这轮达到的目的
已新增已发布卡 V13 shadow refresh 跑道：默认只读生成审核包，不改历史 release；应用计划必须带 `--approved-by-human`。

## 当前状态变化
10 张 pilot 生成后，标题独立性明显改善；Shopify 长标题已收敛。失败 4 张重跑后 3 张转成功，剩 1 张 breakdown 仍因 `why_now` 撞 `已经从` 被校验拦下。

## 还没完成什么
未进入 437 张全量 shadow。阻塞点不是 key 或 shell，而是 breakdown 中文输出仍有低密度连接词回潮。

## 下一步做什么
先处理 `card-group-ai-automation-4bd5d9c843` 的 breakdown 生成稳定性，再跑 20-30 张混合批；混合批失败率可接受后再分批全量。
