# Phase 206 - LLM 标签回流修复与语义候选同步

## 目标
- 修复 LLM 语义候选回流失败（批量插入参数上限）
- 回流最新 LLM 标签结果并统计覆盖率/质量

## 变更
- backend/app/repositories/semantic_candidate_repository.py
  - bulk_upsert 改为分批写入（batch_size=500），避免 32767 参数上限
- backend/app/tasks/semantic_task.py
  - sync_llm_candidates 不再因 auto_approve 关闭而跳过回流

## 执行
- make semantic-llm-sync
- 覆盖率统计（90 天窗口）
- 标签质量统计（空标签占比）

## 结果
- 语义回流：candidates=7074，auto_approved=679，pending=6395
- 覆盖率（lookback=90 天）：
  - posts_total=216052，posts_labeled=214636（99.34%）
  - comments_total=280521，comments_labeled=280454（99.98%）
- 质量（空标签占比）：
  - posts_empty=16555（4.21%）
  - comments_empty=1499（0.33%）
- 数据库：reddit_signal_scanner_dev（默认）

## 风险/待办
- 语义候选数量较大时仍需观察批量写入耗时
- 若需更细 QC（offtopic 占比、分布）可追加统计
