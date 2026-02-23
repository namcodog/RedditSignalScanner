from __future__ import annotations

import re
from typing import Iterable, Mapping, Tuple

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


RouteKey = Tuple[str, str]


def _route_index() -> Mapping[RouteKey, APIRoute]:
    index: dict[RouteKey, APIRoute] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = route.methods or set()
        for method in methods:
            index[(method.upper(), route.path)] = route
    return index


def _missing_routes(expected: Iterable[RouteKey]) -> list[str]:
    routes = _route_index()
    missing = []
    for method, path in expected:
        if (method.upper(), path) not in routes:
            missing.append(f"{method.upper()} {path}")
    return sorted(missing)


def _routes_for(method: str, path: str) -> list[APIRoute]:
    matches: list[APIRoute] = []
    method_upper = method.upper()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path != path:
            continue
        methods = route.methods or set()
        if method_upper in {m.upper() for m in methods}:
            matches.append(route)
    return matches


def _describe_route(method: str, path: str, route: APIRoute) -> str:
    endpoint = getattr(route, "endpoint", None)
    module = getattr(endpoint, "__module__", "<unknown>")
    qualname = getattr(endpoint, "__qualname__", getattr(endpoint, "__name__", "<unknown>"))
    return f"{method.upper()} {path} -> {module}.{qualname}"


async def test_golden_path_routes_exist() -> None:
    expected = {
        ("POST", "/api/analyze"),
        ("GET", "/api/status/{task_id}"),
        ("GET", "/api/analyze/stream/{task_id}"),
        ("GET", "/api/report/{task_id}"),
        ("POST", "/api/export/csv"),
    }
    missing = _missing_routes(expected)
    assert not missing, f"Missing golden-path routes: {missing}"


async def test_no_duplicate_routes_for_frozen_contract_paths() -> None:
    frozen_paths: set[RouteKey] = {
        ("GET", "/api/healthz"),
        ("GET", "/api/diag/runtime"),
        ("POST", "/api/analyze"),
        ("GET", "/api/status/{task_id}"),
        ("GET", "/api/analyze/stream/{task_id}"),
        ("GET", "/api/report/{task_id}"),
        ("POST", "/api/export/csv"),
    }

    duplicates: list[str] = []
    for method, path in sorted(frozen_paths):
        routes = _routes_for(method, path)
        if len(routes) == 1:
            continue
        if not routes:
            duplicates.append(f"{method.upper()} {path} -> <missing>")
            continue
        rendered = "; ".join(_describe_route(method, path, route) for route in routes)
        duplicates.append(f"{method.upper()} {path} -> {rendered}")

    assert not duplicates, f"Duplicate or missing frozen routes: {duplicates}"


async def test_healthz_does_not_point_to_nonexistent_path() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/healthz")

    assert response.status_code == 200
    payload = response.json()
    deprecated = payload.get("deprecated")
    if deprecated is None:
        return
    assert isinstance(deprecated, str)

    match = re.match(r"^\s*use\s+(?P<path>/\S+)\s*$", deprecated)
    assert match is not None, "deprecated must follow format: 'use /path'"
    target = match.group("path")

    missing = _missing_routes({("GET", target)})
    assert not missing, f"Healthz deprecated points to missing route: {deprecated}"


async def test_root_endpoints_list_only_includes_existing_routes() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")

    assert response.status_code == 200
    payload = response.json()
    endpoints = payload.get("endpoints")
    if endpoints is None:
        return
    assert isinstance(endpoints, list)

    invalid: list[str] = []
    for entry in endpoints:
        if not isinstance(entry, str):
            invalid.append("<non-string>")
            continue
        match = re.match(
            r"^\s*(?P<method>GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(?P<path>/\S+)",
            entry,
        )
        if match is None:
            invalid.append(entry)
            continue
        method = match.group("method")
        path = match.group("path")
        if _missing_routes({(method, path)}):
            invalid.append(entry)

    assert not invalid, f"Root endpoints list contains nonexistent routes: {invalid}"
