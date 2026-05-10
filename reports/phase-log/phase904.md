# phase904

1. 这轮达到的目的
   从 Reddit 近 `7d` 直接挖 fresh 选品信息，不再依赖历史 snapshot，验证 `selection-signals` 还能不能长出真正可发的新卡。

2. 当前状态变化
   已新增发布 `2` 张 fresh 选品卡：`1sji2uz`（社区 4000+ 配置数据拆解，指向预算分配判断）和 `1so2bpp`（狗车载出行从航空箱转向安全带胸背）；当前 `hotpost release latest = release-d674f902fd79`，小程序同步快照已更新到 `release-c8ab947acd95`。同时已打回噪音候选 `cand-ecommerce-sellers-1soqzy5`。

3. 还没完成什么
   近 `7d` fresh 选品信号仍偏稀：大范围抓取不是直接跑空，就是混进大量 EDC 晒图/身份梗/宠物场景求助；当前 queue 默认还会吞掉有用的 fresh selection 候选，需要 `--live seed` 才能把它们拉进 review。

4. 下一步做什么
   后续继续用窄 query 挖 `selection-signals`，优先抓：
   - 社区真实配置/购买组合统计
   - 平替与单价对撞
   - 车载/出行/收纳等具体场景配件
   同时继续清掉会污染选品面的生活方式噪音。
