"""Compatibility shim for legacy routes."""
from app.api.legacy import metrics as _legacy

globals().update({k: getattr(_legacy, k) for k in dir(_legacy) if not k.startswith('__')})
__all__ = getattr(_legacy, '__all__', [])
