# phase906

1. 这轮达到的目的
   把“补上线卡”从日运营主链里拆出来，做成可配置的补卡入口。

2. 当前状态变化
   `collect_named_topics.py` 已支持 `--watch-profile / --watch-profile-config / --topic-cluster`；新增补卡配置文件 `backend/config/hotpost_card_supplement_profiles.yaml`，当前已内置 `selection-30d-core` 和可选的 `selection-30d-home-decisions`。以后补卡主要改 YAML，不再改 Python 主链。

3. 还没完成什么
   profile 现在只是第一版；`selection-30d-home-decisions` 仍保留为可选项，因为 `homeowners` 噪音明显偏高，不适合默认混进核心补卡流。

4. 下一步做什么
   后续补卡直接走 profile；默认先跑 `selection-30d-core`，只有你明确要扩大到家居/购房决策时，才加 `selection-30d-home-decisions`。
