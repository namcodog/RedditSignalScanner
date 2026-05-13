# phase951

1. 这轮达到的目的
   运营日志日清单已补上 `主社区` 列，回看每天发卡时能直接看到每张卡主要来自哪个社区。
2. 当前状态变化
   `export_ops_log.py` 已支持优先读取顶层 `top_community`，缺失时回退到 `source_module.top_community` 和 `primary_communities`；最近 5 个发布日的日志已全部重刷。
3. 还没完成什么
   `ops-log/INDEX.md` 仍保持轻量汇总，没有把主社区塞进总索引。
4. 下一步做什么
   后续继续按现在的导出逻辑重刷；如果运营还想看社区聚类分布，再单独加社区汇总页。
