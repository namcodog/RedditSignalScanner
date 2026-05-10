# Phase 515 - Hotpost 低成本 live 校准（第一轮）

## 本轮目标

在第三刀完成后，不扩题、不换关键词，直接用固定 low-cost smoke 题做一次真实校准：

- 看新风控下 Hotpost 能不能正常返回
- 看哪一类 mode 还在慢
- 不为了验收再去冒 Reddit 风险

## 本轮执行

### 1. 先确认运行态

已确认：

- `http://127.0.0.1:8006/api/v1/health` -> `{"status":"ok"}`
- `http://127.0.0.1:8006/api/healthz` -> `{"status":"ok"}`

说明：

- 不是后端没起来
- 当前阻塞如果出现，一定是 Hotpost live 执行链本身

### 2. 先跑固定 `trending` 校准题

命令：

```bash
cd backend && python scripts/acceptance/run_hotpost_quality_smoke.py --base-url http://127.0.0.1:8006 --case 'tiktok shop sellers|trending|month' --limit 1 --request-timeout-seconds 45 --timeout-seconds 75
```

结果：

- `query_id = 9b6cd743-ea05-45c4-9870-90629338b352`
- `status = completed`
- `evidence_count = 30`
- `quality_contract_gaps = 0`
- `degraded_reasons = []`
- `report_source = llm`
- `final_report_layer = fast`
- `report_model_name = x-ai/grok-4.1-fast`

当前判断：

- `trending` 这条在现有缓存/当前运行态下是通的
- 第三刀没有把最轻路径打坏

### 3. `rant / opportunity` 首次 live 仍然偏重

命令（分别单独跑）：

```bash
cd backend && python scripts/acceptance/run_hotpost_quality_smoke.py --base-url http://127.0.0.1:8006 --case 'shopify app bugs|rant|month' --limit 1 --request-timeout-seconds 45 --timeout-seconds 75
cd backend && python scripts/acceptance/run_hotpost_quality_smoke.py --base-url http://127.0.0.1:8006 --case 'reddit scheduling tool|opportunity|month' --limit 1 --request-timeout-seconds 45 --timeout-seconds 75
```

观察结果：

- 两条请求都长时间占住连接，没有像 `trending` 一样快速返回
- 本轮我没有继续硬等到无限长，也没有继续叠更多并发请求
- 为保护本地 runtime 和 Reddit 调用边界，已主动停止额外 hanging 请求

当前判断：

- 第三刀已经把 Reddit 风控接进来了
- 但 runtime latency 仍没有完全收住
- 当前慢点更集中在：
  - `rant`
  - `opportunity`

## 本轮结论

### 发现了什么？

- 第三刀的风控没有把 Hotpost 打坏，`trending` 已可正常返回
- 但 `rant / opportunity` 的首次 live 仍明显偏慢

### 是否需要修复？

- 需要
- 当前下一层主问题已经不只是“有没有风控”，而是“风控边界内的执行时延怎么继续压”

### 精确修复方向

下一步优先看这两类点：

1. `rant / opportunity` 的首轮 evidence collection 是否仍过重
2. 是否存在某一段同步链路把整个请求长时间占住：
   - subreddit 搜索
   - comment fetch
   - report generation

## 当前价值

这轮校准的价值是：

- 已经确认第三刀不是假稳定
- 也已经确认下一层真实问题不是“后端挂了”，而是“部分 mode 的 live 首次响应还太重”

## 下一步

第四刀先不加新能力，先做一轮 runtime latency 定位：

1. 给 `rant / opportunity` 加更细的阶段耗时日志
2. 拆出首轮 collection / comment fetch / report generation 的耗时占比
3. 再决定是继续压首轮 fanout，还是要把某段改异步/降级

## 一句话结论

Hotpost 第三刀后第一轮低成本 live 校准已经拿到结论：**`trending` 能通，`rant / opportunity` 仍慢。**
下一步该收的不是更多规则，而是 runtime latency 的具体断点。
