# Phase 90 - Rolling restart Celery workers

## Action
- Rolled restart all Celery workers and beat to load new DB pool settings.
- Recovered missing patrol/monitoring/labels/probe workers after timeout.
- Cleared duplicate analysis workers left from partial restart.

## Result
- Workers running: analysis1-5, backfill x2, compensation, monitoring, patrol, probe, labels, beat.
- Queues: all 0 at check time.
- DB connections stable (no "too many clients").

## Note
- Force-stopped stale analysis workers that did not exit on TERM to avoid duplicates.
