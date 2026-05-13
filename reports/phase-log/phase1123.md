# phase1123 - Brand Intelligence R15.0.5 来源目录归一

- 这轮目的：把分散的品牌资源统一进只读 source catalog，避免语义库、初始品牌表、历史 archive 和噪音词表各走一套。
- 当前状态变化：catalog 已生成 `1845` 个条目，digest 已从 `849` 张已发布卡识别 `169` 个品牌/候选、`1543` 条证据，全部 `db_writes=false`。
- 还没完成：archive 候选混入普通词噪音，不能直接入库。
- 下一步：R15.1 做品牌质量合同、噪音降权和审核状态；通过后 R15.2 再写 Dev DB。
