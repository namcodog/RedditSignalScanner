from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(dotenv_path=ROOT / ".env")

from app.services.hotpost.card_content_polish import polish_published_card
from app.services.hotpost.card_payload_store import load_published_cards, merge_published_cards


def main() -> None:
    published = load_published_cards()
    polished = [polish_published_card(card) for card in published]
    polished_count = merge_published_cards(polished)
    print(json.dumps({"polished": polished_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
