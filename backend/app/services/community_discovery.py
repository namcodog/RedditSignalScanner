"""Compatibility shim for legacy imports.

The canonical implementation now lives in ``app.services.community.community_discovery``.
This module keeps existing ``app.services.community_discovery`` imports working.
"""

from app.services.community.community_discovery import *  # noqa: F401,F403
