"""JSON-safe projections for the public MotionBuilder object model."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    try:
        return list(value)
    except TypeError:
        return []


def safe_attribute(value: Any, name: str, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return getattr(value, name)
    except Exception:
        return default


def call_value(value: Any, method_name: str, *args: Any) -> Any:
    method = safe_attribute(value, method_name)
    if not callable(method):
        return None
    try:
        return method(*args)
    except Exception:
        return None


def as_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def name_of(value: Any) -> str | None:
    return as_string(safe_attribute(value, "Name"))


def class_name(value: Any) -> str:
    result = call_value(value, "ClassName")
    return as_string(result) or type(value).__name__


def time_details(value: Any) -> Optional[Union[Dict[str, Any], str]]:
    if value is None:
        return None
    details: dict[str, Any] = {}
    for method_name, key in (
        ("GetFrame", "frame"),
        ("GetSecondDouble", "seconds"),
        ("GetTimeString", "formatted"),
    ):
        result = call_value(value, method_name)
        if result is not None:
            details[key] = result
    return details or str(value)


def component_details(component: Any) -> dict[str, Any]:
    name = name_of(component)
    return {
        "name": name,
        "long_name": as_string(safe_attribute(component, "LongName", name)),
        "class_name": class_name(component),
        "class_group_name": as_string(safe_attribute(component, "ClassGroupName")),
        "type_info": safe_attribute(component, "TypeInfo"),
        "selected": as_bool(safe_attribute(component, "Selected")),
    }
