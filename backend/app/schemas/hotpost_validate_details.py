from __future__ import annotations

from typing import Optional, Any

from app.schemas.base import ORMModel


class SignalValidationDetail(ORMModel):
    pain_point: str
    target_user_and_scene: str
    why_test_now: str
    min_test_action: str = ""
    continue_signal: str
    stop_signal: str


class HotValidationDetail(ORMModel):
    flashpoint: str
    fight_line: str
    why_test_now: str
    continue_signal: str
    stop_signal: str


ValidationDetailLike = SignalValidationDetail | HotValidationDetail

_SIGNAL_DETAIL_FIELDS = (
    "pain_point",
    "target_user_and_scene",
    "why_test_now",
    "min_test_action",
    "continue_signal",
    "stop_signal",
)
_HOT_DETAIL_FIELDS = (
    "flashpoint",
    "fight_line",
    "why_test_now",
    "continue_signal",
    "stop_signal",
)


def empty_validation_detail_payload(lane:Optional[ str]) -> dict[str, str]:
    fields = _HOT_DETAIL_FIELDS if lane == "hot" else _SIGNAL_DETAIL_FIELDS
    return {field_name: "" for field_name in fields}


def normalize_validation_detail_payload(lane:Optional[ str], detail: dict[str, Any]) -> dict[str, str]:
    raw = dict(detail)
    if lane == "hot":
        if "flashpoint" in raw or "fight_line" in raw:
            return {field_name: str(raw.get(field_name) or "").strip() for field_name in _HOT_DETAIL_FIELDS}
        return {
            "flashpoint": str(raw.get("pain_point") or "").strip(),
            "fight_line": str(raw.get("target_user_and_scene") or "").strip(),
            "why_test_now": str(raw.get("why_test_now") or "").strip(),
            "continue_signal": str(raw.get("continue_signal") or "").strip(),
            "stop_signal": str(raw.get("stop_signal") or "").strip(),
        }
    return {
        "pain_point": str(raw.get("pain_point") or "").strip(),
        "target_user_and_scene": str(raw.get("target_user_and_scene") or "").strip(),
        "why_test_now": str(raw.get("why_test_now") or "").strip(),
        "min_test_action": str(raw.get("min_test_action") or "").strip(),
        "continue_signal": str(raw.get("continue_signal") or "").strip(),
        "stop_signal": str(raw.get("stop_signal") or "").strip(),
    }


def normalize_validation_container_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    detail = payload.get("detail")
    if not isinstance(detail, dict):
        return payload
    normalized = dict(payload)
    normalized["detail"] = normalize_validation_detail_payload(str(payload.get("lane") or "signal"), detail)
    return normalized


def build_validation_detail(lane:Optional[ str], detail: dict[str, Any]) -> ValidationDetailLike:
    normalized = normalize_validation_detail_payload(lane, detail)
    if lane == "hot":
        return HotValidationDetail.model_validate(normalized)
    return SignalValidationDetail.model_validate(normalized)


def validation_detail_field_names_for_payload(detail: dict[str, Any], *, lane:Optional[ str] = None) -> tuple[str, ...]:
    if lane == "hot" or "flashpoint" in detail or "fight_line" in detail:
        return _HOT_DETAIL_FIELDS
    return _SIGNAL_DETAIL_FIELDS


def validate_validation_detail_lane(lane:Optional[ str], detail: ValidationDetailLike) -> None:
    if lane == "hot" and not isinstance(detail, HotValidationDetail):
        raise ValueError("hot lane requires hot validation detail")
    if lane != "hot" and not isinstance(detail, SignalValidationDetail):
        raise ValueError("signal lane requires signal validation detail")


__all__ = [
    "HotValidationDetail",
    "SignalValidationDetail",
    "ValidationDetailLike",
    "build_validation_detail",
    "empty_validation_detail_payload",
    "normalize_validation_container_payload",
    "normalize_validation_detail_payload",
    "validate_validation_detail_lane",
    "validation_detail_field_names_for_payload",
]
