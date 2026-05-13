from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import TypeAlias


JsonObject: TypeAlias = dict[str, object]
JsonList: TypeAlias = list[JsonObject]


def storage_root_for(legacy_cards_path: Path) -> Path:
    return legacy_cards_path.parent / "hotpost"


def split_layout_exists(legacy_cards_path: Path) -> bool:
    root = storage_root_for(legacy_cards_path)
    return (
        (root / "categories.json").exists()
        and (root / "releases" / "latest.json").exists()
    )


def load_payload(legacy_cards_path: Path) -> JsonObject:
    if split_layout_exists(legacy_cards_path):
        return _load_split_payload(storage_root_for(legacy_cards_path))
    return _read_json_object(legacy_cards_path)


def write_split_payload(legacy_cards_path: Path, payload: JsonObject) -> None:
    root = storage_root_for(legacy_cards_path)
    root.mkdir(parents=True, exist_ok=True)

    _atomic_write_json(root / "categories.json", _payload_list(payload, "categories"))
    _write_candidates(root / "candidates", _payload_object_list(payload, "candidates"))
    _write_drafts(root / "drafts", _payload_object_list(payload, "drafts"))
    _write_release(root / "releases", _payload_object_list(payload, "published"))


def migrate_legacy_payload(legacy_cards_path: Path) -> dict[str, int | str]:
    payload = _read_json_object(legacy_cards_path)
    write_split_payload(legacy_cards_path, payload)
    latest = _read_json_object(storage_root_for(legacy_cards_path) / "releases" / "latest.json")
    return {
        "categories": len(_payload_list(payload, "categories")),
        "candidates": len(_payload_object_list(payload, "candidates")),
        "drafts": len(_payload_object_list(payload, "drafts")),
        "published": len(_payload_object_list(payload, "published")),
        "release_id": str(latest["release_id"]),
    }


def _load_split_payload(root: Path) -> JsonObject:
    categories = _read_json_if_exists(root / "categories.json", [])
    candidates = _load_candidates(root / "candidates")
    drafts = _load_drafts(root / "drafts")
    published = _load_release_cards(root / "releases")
    return {
        "categories": categories,
        "candidates": candidates,
        "drafts": drafts,
        "published": published,
    }


def _load_candidates(candidates_dir: Path) -> list[dict]:
    if not candidates_dir.exists():
        return []
    items: JsonList = []
    for path in sorted(candidates_dir.glob("*.json")):
        items.extend(_read_json_list(path))
    return items


def _load_drafts(drafts_dir: Path) -> JsonList:
    if not drafts_dir.exists():
        return []
    return [_read_json_object(path) for path in sorted(drafts_dir.glob("*.json"))]


def _load_release_cards(releases_dir: Path) -> JsonList:
    latest_path = releases_dir / "latest.json"
    if not latest_path.exists():
        return []
    release_id = str(_read_json_object(latest_path)["release_id"])
    release_root = releases_dir / release_id
    index = _read_json_object(release_root / "index.json")
    card_ids = index.get("card_ids", [])
    if not isinstance(card_ids, list):
        raise ValueError(f"release index card_ids must be a list: {release_root / 'index.json'}")
    cards_dir = release_root / "cards"
    return [_read_json_object(cards_dir / f"{card_id}.json") for card_id in card_ids]


def _write_candidates(candidates_dir: Path, candidates: JsonList) -> None:
    candidates_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, JsonList] = defaultdict(list)
    for item in candidates:
        grouped[str(item["source_scope_id"])].append(item)

    expected_paths: set[Path] = set()
    for scope_id, items in grouped.items():
        path = candidates_dir / f"{scope_id}.json"
        _atomic_write_json(path, items)
        expected_paths.add(path)

    _remove_stale_files(candidates_dir, expected_paths)


def _write_drafts(drafts_dir: Path, drafts: JsonList) -> None:
    drafts_dir.mkdir(parents=True, exist_ok=True)

    expected_paths: set[Path] = set()
    for item in drafts:
        path = drafts_dir / f"{str(item['draft_id'])}.json"
        _atomic_write_json(path, item)
        expected_paths.add(path)

    _remove_stale_files(drafts_dir, expected_paths)


def _write_release(releases_dir: Path, published: JsonList) -> None:
    releases_dir.mkdir(parents=True, exist_ok=True)
    release_id = _release_id_for(published)
    release_root = releases_dir / release_id
    cards_dir = release_root / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    ordered = sorted(published, key=lambda item: str(item["published_at"]), reverse=True)
    card_ids: list[str] = []
    expected_paths: set[Path] = set()
    for item in ordered:
        card_id = str(item["card_id"])
        card_ids.append(card_id)
        path = cards_dir / f"{card_id}.json"
        _atomic_write_json(path, item)
        expected_paths.add(path)

    _remove_stale_files(cards_dir, expected_paths)
    _atomic_write_json(
        release_root / "index.json",
        {
            "release_id": release_id,
            "card_ids": card_ids,
            "card_count": len(card_ids),
        },
    )
    _atomic_write_json(releases_dir / "latest.json", {"release_id": release_id})


def _release_id_for(published: JsonList) -> str:
    if not published:
        return "empty"
    digest = hashlib.sha1(
        json.dumps(
            sorted(published, key=lambda item: str(item["card_id"])),
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"release-{digest[:12]}"


def _remove_stale_files(directory: Path, expected_paths: set[Path]) -> None:
    if not directory.exists():
        return
    for path in directory.glob("*.json"):
        if path not in expected_paths:
            path.unlink()


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_object(path: Path) -> JsonObject:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _read_json_list(path: Path) -> JsonList:
    payload = _read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list: {path}")
    items: JsonList = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"Expected JSON object items: {path}")
        items.append(item)
    return items


def _payload_list(payload: JsonObject, key: str) -> list[object]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"Expected payload[{key!r}] to be a list")
    return value


def _payload_object_list(payload: JsonObject, key: str) -> JsonList:
    value = _payload_list(payload, key)
    items: JsonList = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"Expected payload[{key!r}] items to be objects")
        items.append(item)
    return items


def _read_json_if_exists(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return _read_json(path)


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as temp_file:
        json.dump(payload, temp_file, ensure_ascii=False, indent=2)
        temp_file.write("\n")
        temp_name = temp_file.name
    os.replace(temp_name, path)
