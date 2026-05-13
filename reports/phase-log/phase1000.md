# Phase 1000 - V13 标题与小程序体验优化验收

## 这轮达到的目的
- 把用户反馈的标题模板化、标题字体、收藏延迟、现有卡片 JSON 标题问题落成代码和数据修复。

## 当前状态变化
- V13 标题规则已收紧：默认不写 `r/xxxx`，压 18-32 字，拦“这帖火了 / 评论区在吵 / 有用户开始”等模板句式。
- 当前 `release-33033bf53e07` 的 mini snapshot / cloud_db / miniRelease / miniFavorites 标题已批量打磨，`card_count=618`。
- 首页、详情、收藏页已改成标题 sans 字体和收藏乐观更新；取消收藏立即从收藏页消失。

## 还没完成什么
- 线上还需要重新导入优化后的 `mini_release_cards`，并上传新版小程序包后才能看到前端体验变化。

## 下一步做什么
- 云数据库重导 `backend/data/hotpost/mini_snapshots/cloud_db/mini_release_cards.wechat-import.json`，再用 `dist-dev` 或生产包上传小程序。
