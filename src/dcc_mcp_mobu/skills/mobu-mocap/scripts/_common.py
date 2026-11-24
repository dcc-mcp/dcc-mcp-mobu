"""Read-only JSON projections for MotionBuilder Mocap objects."""

from __future__ import annotations

from typing import Any, Optional


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    try:
        return list(value)
    except TypeError:
        return []


def name_of(value: Any) -> Optional[str]:
    if value is None:
        return None
    name = getattr(value, "Name", None)
    return None if name is None else str(name)


def class_name(value: Any) -> str:
    method = getattr(value, "ClassName", None)
    if callable(method):
        try:
            return str(method())
        except Exception:
            pass
    return type(value).__name__


def json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    details = {}
    for method_name, key in (
        ("GetFrame", "frame"),
        ("GetSecondDouble", "seconds"),
        ("GetTimeString", "formatted"),
    ):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                details[key] = method()
            except Exception:
                continue
    if details:
        return details
    return str(value)


def attribute(value: Any, property_name: str) -> Any:
    try:
        return json_value(getattr(value, property_name))
    except (AttributeError, TypeError, ValueError):
        return None
    except Exception:
        return None


def list_attribute(value: Any, property_name: str) -> list[Any]:
    try:
        return [json_value(item) for item in as_list(getattr(value, property_name))]
    except Exception:
        return []


def marker_set_details(marker_set: Any, *, kind: str) -> dict[str, Any]:
    return {
        "name": name_of(marker_set),
        "class_name": class_name(marker_set),
        "kind": kind,
        "link_to_model_ok": _call_bool(marker_set, "GetLinkToModelOk"),
        "used_marker_count": _call_int(marker_set, "GetUsedMarkerCount"),
        "marker_count": _call_int(marker_set, "GetMarkerCount"),
        "reference_model": name_of(_call_value(marker_set, "GetReferenceModel")),
    }


def device_details(device: Any, *, optical: bool) -> dict[str, Any]:
    details = {
        "name": name_of(device),
        "class_name": class_name(device),
        "optical": optical,
        "online": attribute(device, "Online"),
        "status": attribute(device, "Status"),
        "live": attribute(device, "Live"),
        "record_mode": attribute(device, "RecordMode"),
        "recording_start_time": attribute(device, "RecordingStartTime"),
        "recording_stop_time": attribute(device, "RecordingStopTime"),
        "sampling_mode": attribute(device, "SamplingMode"),
        "sampling_period": attribute(device, "SamplingPeriod"),
    }
    if optical:
        details.update(
            {
                "marker_count": len(as_list(getattr(device, "Markers", None))),
                "support_occlusion": attribute(device, "SupportOcclusion"),
                "optical_sampling_rate": attribute(device, "OpticalSamplingRate"),
                "use_marker_time_stamp": attribute(device, "UseMarkerTimeStamp"),
                "force_optical_sampling_rate": attribute(device, "ForceOpticalSamplingRate"),
                "calibration_status": {
                    "status": "unsupported",
                    "reason": (
                        "MotionBuilder exposes optical setup methods, but this skill "
                        "does not invoke them"
                    ),
                },
            }
        )
    return details


def _call_value(value: Any, method_name: str) -> Any:
    method = getattr(value, method_name, None)
    if not callable(method):
        return None
    try:
        return method()
    except Exception:
        return None


def _call_bool(value: Any, method_name: str) -> Optional[bool]:
    result = _call_value(value, method_name)
    return None if result is None else bool(result)


def _call_int(value: Any, method_name: str) -> Optional[int]:
    result = _call_value(value, method_name)
    if result is None:
        return None
    try:
        return int(result)
    except (TypeError, ValueError):
        return None
