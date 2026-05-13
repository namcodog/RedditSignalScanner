from __future__ import annotations

import fcntl
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from app.services.hotpost.card_storage_layout import load_payload, migrate_legacy_payload, storage_root_for, write_split_payload


_CARDS_PATH = Path(__file__).resolve().parents[3] / "data" / "hotpost_clues.json"
ResultT = TypeVar("ResultT")


def _lock_path() -> Path:
    root = storage_root_for(_CARDS_PATH)
    return root / ".storage.lock"


def _read_payload_unlocked() -> dict:
    return load_payload(_CARDS_PATH)


def load_cards_payload() -> dict:
    return _read_payload_unlocked()


def load_categories() -> list[dict]:
    return list(load_cards_payload().get("categories", []))


def load_candidates() -> list[dict]:
    return list(load_cards_payload().get("candidates", []))


def load_drafts() -> list[dict]:
    return list(load_cards_payload().get("drafts", []))


def load_published_cards() -> list[dict]:
    return list(load_cards_payload().get("published", []))


def write_cards_payload(payload: dict) -> None:
    mutate_cards_payload(lambda current: current.update(payload))


def mutate_candidates(mutator: Callable[[list[dict]], ResultT]) -> ResultT:
    def _mutate(payload: dict) -> ResultT:
        candidates = list(payload.get("candidates", []))
        result = mutator(candidates)
        payload["candidates"] = candidates
        return result

    return mutate_cards_payload(_mutate)


def mutate_drafts(mutator: Callable[[list[dict]], ResultT]) -> ResultT:
    def _mutate(payload: dict) -> ResultT:
        drafts = list(payload.get("drafts", []))
        result = mutator(drafts)
        payload["drafts"] = drafts
        return result

    return mutate_cards_payload(_mutate)


def mutate_published_cards(mutator: Callable[[list[dict]], ResultT]) -> ResultT:
    def _mutate(payload: dict) -> ResultT:
        published = list(payload.get("published", []))
        result = mutator(published)
        payload["published"] = published
        return result

    return mutate_cards_payload(_mutate)


def mutate_drafts_and_published(mutator: Callable[[list[dict], list[dict]], ResultT]) -> ResultT:
    def _mutate(payload: dict) -> ResultT:
        drafts = list(payload.get("drafts", []))
        published = list(payload.get("published", []))
        result = mutator(drafts, published)
        payload["drafts"] = drafts
        payload["published"] = published
        return result

    return mutate_cards_payload(_mutate)


def replace_published_cards(cards: list[dict]) -> int:
    def _mutate(published: list[dict]) -> int:
        published[:] = list(cards)
        return len(published)

    return mutate_published_cards(_mutate)


def merge_published_cards(updated_cards: list[dict]) -> int:
    replacements = {
        item["card_id"]: item
        for item in updated_cards
        if item.get("card_id")
    }

    def _mutate(payload: dict) -> int:
        current = list(payload.get("published", []))
        touched = 0
        merged: list[dict] = []
        for item in current:
            replacement = replacements.get(item.get("card_id"))
            if replacement is None:
                merged.append(item)
                continue
            merged.append(replacement)
            touched += 1
        payload["published"] = merged
        return touched

    return mutate_cards_payload(_mutate)


def mutate_cards_payload(mutator: Callable[[dict], ResultT]) -> ResultT:
    _lock_path().parent.mkdir(parents=True, exist_ok=True)
    with _lock_path().open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        payload = _read_payload_unlocked()
        result = mutator(payload)
        write_split_payload(_CARDS_PATH, payload)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        return result


def migrate_cards_payload_layout() -> dict[str, int | str]:
    return migrate_legacy_payload(_CARDS_PATH)
