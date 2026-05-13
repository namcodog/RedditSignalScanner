from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = (
    ROOT / "scripts" / "brand_intelligence" / "preview_brand_registry.py",
    ROOT / "scripts" / "brand_intelligence" / "generate_brand_ops_sidecar.py",
    ROOT / "scripts" / "brand_intelligence" / "generate_brand_system_evidence.py",
    ROOT / "scripts" / "brand_intelligence" / "write_brand_registry_dev.py",
)


def test_brand_db_scripts_load_env_before_session_factory() -> None:
    for path in SCRIPTS:
        source = path.read_text(encoding="utf-8")

        assert source.index("load_backend_env()") < source.index(
            "from app.db.session import SessionFactory"
        )
