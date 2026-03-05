from __future__ import annotations

import json
import os
import time

from app.tasks.scoring_task import score_new_comments_v1


def main() -> None:
    limit = int(os.getenv("SCORE_COMMENTS_LIMIT", "5000"))
    max_batches = int(os.getenv("SCORE_COMMENT_BATCHES", "500"))
    sleep_s = float(os.getenv("SCORE_COMMENT_SLEEP", "0.5"))

    total = 0
    for idx in range(max_batches):
        result = score_new_comments_v1(limit=limit) or {}
        processed = int(result.get("processed") or 0)
        total += processed
        print(
            json.dumps(
                {"batch": idx + 1, "processed": processed, "total": total},
                ensure_ascii=True,
            ),
            flush=True,
        )
        if processed <= 0:
            break
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
