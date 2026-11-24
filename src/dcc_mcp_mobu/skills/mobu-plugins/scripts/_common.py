"""Read-only normalization helpers for MotionBuilder plug-in queries."""

from __future__ import annotations

from typing import Any


def as_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    try:
        return [str(item) for item in value]
    except TypeError:
        return [str(value)]


def call_strings(system: Any, method_name: str, *args: Any) -> list[str]:
    method = getattr(system, method_name, None)
    if not callable(method):
        return []
    try:
        return as_strings(method(*args))
    except Exception:
        return []
