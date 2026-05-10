from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.card_payload_store import migrate_cards_payload_layout


def main() -> None:
    load_backend_env()
    result = migrate_cards_payload_layout()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
