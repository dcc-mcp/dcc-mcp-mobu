"""MotionBuilder mapping projections and optional dcc-mcp-fpt protocol."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol


class ProductionTrackingAdapter(Protocol):
    """Read-only boundary implemented by an optional dcc-mcp-fpt runtime."""

    def connection_diagnostics(self, params: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return non-secret connection diagnostics for one request."""


class DccMcpFptRuntimeAdapter:
    """Adapt the existing dcc-mcp-fpt runtime context without copying auth."""

    def __init__(self, server: Any) -> None:
        self._server = server

    def connection_diagnostics(self, params: Mapping[str, Any]) -> Mapping[str, Any]:
        from dcc_mcp_fpt.runtime_context import get_request_connection_info

        return get_request_connection_info(self._server, dict(params))


def resolve_adapter() -> tuple[Optional[ProductionTrackingAdapter], str]:
    """Return the optional in-process FPT adapter and a diagnostic reason."""
    try:
        from dcc_mcp_fpt.runtime_context import get_current_server
    except ImportError:
        return None, "dcc_mcp_fpt_not_installed"
    try:
        server = get_current_server()
    except Exception as exc:
        return None, f"runtime_context_error:{type(exc).__name__}"
    if server is None:
        return None, "dcc_mcp_fpt_server_not_registered"
    return DccMcpFptRuntimeAdapter(server), "available"


def config_diagnostics() -> dict[str, Any]:
    """Report FPT configuration presence without returning secret values."""
    url_present = bool(os.environ.get("SHOTGRID_URL"))
    script_name_present = bool(os.environ.get("SHOTGRID_SCRIPT_NAME"))
    script_key_present = bool(os.environ.get("SHOTGRID_SCRIPT_KEY"))
    profile_present = any(
        bool(os.environ.get(name))
        for name in (
            "DCC_MCP_FPT_CREDENTIAL_PROFILES",
            "SHOTGRID_CREDENTIAL_PROFILES",
            "DCC_MCP_FPT_CREDENTIAL_PROFILES_FILE",
            "SHOTGRID_CREDENTIAL_PROFILES_FILE",
        )
    )
    return {
        "contract": "dcc-mcp-fpt",
        "url_present": url_present,
        "script_name_present": script_name_present,
        "script_key_present": script_key_present,
        "credential_profile_configured": profile_present,
        "configured": profile_present
        or (url_present and script_name_present and script_key_present),
        "secrets_exposed": False,
    }


def safe_connection_diagnostics(value: Any) -> dict[str, Any]:
    """Keep only the non-secret fields defined by the FPT connection contract."""
    if not isinstance(value, Mapping):
        return {}
    safe_fields = ("url", "script_name", "authenticated", "server_version")
    return {key: value[key] for key in safe_fields if key in value}


def absolute_scene_file(raw_path: Any) -> Optional[str]:
    if raw_path in (None, ""):
        return None
    return str(Path(str(raw_path)).expanduser().absolute())


def json_time(value: Any) -> Any:
    if value is None:
        return None
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
    return details or str(value)


def iter_story_tracks(folder: Any, folder_path: Optional[list[str]] = None):
    current_path = list(folder_path or [])
    folder_name = getattr(folder, "Name", None)
    if folder_name and not current_path:
        current_path.append(str(folder_name))
    for track in _as_list(getattr(folder, "Tracks", None)):
        yield track, current_path
    for component in _as_list(getattr(folder, "Components", None)):
        if hasattr(component, "Tracks"):
            name = getattr(component, "Name", None)
            child_path = current_path + ([str(name)] if name else [])
            yield from iter_story_tracks(component, child_path)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    try:
        return list(value)
    except TypeError:
        return []
