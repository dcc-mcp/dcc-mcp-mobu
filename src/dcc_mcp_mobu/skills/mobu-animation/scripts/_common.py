"""JSON-safe read-only projections of MotionBuilder animation objects."""

from __future__ import annotations

from typing import Any, Iterable


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    try:
        return list(value)
    except TypeError:
        return []


def name_of(value: Any) -> Any:
    return getattr(value, "Name", None) if value is not None else None


def time_value(value: Any) -> Any:
    """Convert an FBTime-like value into JSON-safe details."""
    if value is None:
        return None
    details: dict[str, Any] = {}
    for method_name, key in (
        ("GetFrame", "frame"),
        ("GetSecondDouble", "seconds"),
        ("GetTimeString", "formatted"),
    ):
        method = getattr(value, method_name, None)
        if not callable(method):
            continue
        try:
            details[key] = method()
        except Exception:
            continue
    return details or str(value)


def time_span(value: Any) -> Any:
    if value is None:
        return None
    return {
        "start": time_value(getattr(value, "Start", None)),
        "stop": time_value(getattr(value, "Stop", None)),
    }


def take_details(take: Any, *, is_current: bool = False) -> dict[str, Any]:
    return {
        "name": name_of(take),
        "comments": getattr(take, "Comments", None),
        "is_current": is_current,
        "local_time_span": time_span(getattr(take, "LocalTimeSpan", None)),
        "reference_time_span": time_span(getattr(take, "ReferenceTimeSpan", None)),
    }


def clip_details(clip: Any) -> dict[str, Any]:
    connected_take = getattr(clip, "ConnectedToTake", None)
    return {
        "name": name_of(clip),
        "start": time_value(getattr(clip, "Start", None)),
        "stop": time_value(getattr(clip, "Stop", None)),
        "source_mark_in": time_value(getattr(clip, "SourceMarkIn", None)),
        "source_mark_out": time_value(getattr(clip, "SourceMarkOut", None)),
        "loaded": getattr(clip, "Loaded", None),
        "loop": getattr(clip, "Loop", None),
        "speed": getattr(clip, "Speed", None),
        "connected_to_take": name_of(connected_take),
    }


def track_details(track: Any, folder_path: list[str]) -> dict[str, Any]:
    track_name = name_of(track)
    child_path = folder_path + ([track_name] if track_name else [])
    return {
        "name": track_name,
        "label": getattr(track, "Label", None),
        "type": str(getattr(track, "Type", "unknown")),
        "folder_path": folder_path,
        "mute": getattr(track, "Mute", None),
        "solo": getattr(track, "Solo", None),
        "clips": [clip_details(clip) for clip in as_list(getattr(track, "Clips", None))],
        "sub_tracks": [
            track_details(sub_track, child_path)
            for sub_track in as_list(getattr(track, "SubTracks", None))
        ],
    }


def iter_tracks(
    folder: Any, folder_path: list[str] | None = None
) -> Iterable[tuple[Any, list[str]]]:
    current_path = list(folder_path or [])
    folder_name = name_of(folder)
    if folder_name and not current_path:
        current_path.append(folder_name)
    for track in as_list(getattr(folder, "Tracks", None)):
        yield track, current_path
    for component in as_list(getattr(folder, "Components", None)):
        if hasattr(component, "Tracks"):
            child_path = current_path + ([name_of(component)] if name_of(component) else [])
            yield from iter_tracks(component, child_path)
