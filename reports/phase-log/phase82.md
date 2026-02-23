# Phase 82 - B group 12m comments backfill + label worker

## What changed
- Started B group 12-month comments backfill using smart_shallow + blast boost.
- Added a dedicated label worker for analysis_queue to unblock A/B labeling.

## B group comments backfill
- Run ID: 9d4afb5d-f6ef-4d69-b320-cb7708f223c1
- Targets enqueued: 157 posts (12 months, is_current=true, dedup by source_post_id).
- Smart mode:
  - Default: limit=50, depth=2 (top 30 + new 20 + reply-top 15).
  - Blast: if num_comments >= 300 or score >= 500 -> limit=150, depth=3.
- Enqueue pacing: countdown 2s step, capped at 180s.
- Snapshot: completed 47 / running 1 / queued 109 / partial 1.

## Labeling
- Found analysis_queue backlog dominated by monitoring tasks (no queue option set), causing label tasks to starve.
- Started label-only worker:
  - celery -A app.core.celery_app:celery_app worker -n labels@%h --pool=solo --concurrency=1 --queues=analysis_queue
- analysis_queue now draining (monitor tasks still ahead of label tasks).

## Note
- To permanently avoid label starvation, consider routing monitoring tasks to monitoring_queue.
