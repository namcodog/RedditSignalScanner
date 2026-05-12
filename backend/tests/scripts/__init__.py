from pathlib import Path

_BACKEND_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_BACKEND_SCRIPTS) not in __path__:
    __path__.insert(0, str(_BACKEND_SCRIPTS))
