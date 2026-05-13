# phase59 - 27社区验毒启动与C组停用

日期: 2025-12-22

## 背景
- 27 个手动新增社区需走验毒流程
- C 组先停用，不直接黑掉

## 执行
- 写入 discovered_communities (pending) 27 条
- C 组在 community_pool 设为 is_active=false (6 条)
- 启动 probe/bulk worker
- 触发 tasks.discovery.run_community_evaluation

## 验证
- discovered_communities: pending=27
- metrics.vetting 已写入 (status=queued)
- 队列: probe_queue=0, backfill_queue=135

## 备注
- bulk worker 同时接到 seed crawl 任务 (来自 beat)
- community_blacklist.yaml 不存在警告 (运行时提示)
- Chrome DevTools MCP 无法连接到既有实例，因此用 DB 查询完成验证

## 下一步
- 等 backfill_queue 消化完成 -> vetting completed
- 再触发 run_community_evaluation 完成评估
- A 组做 12 个月回填; B 组先小样本; C 组保持停用
