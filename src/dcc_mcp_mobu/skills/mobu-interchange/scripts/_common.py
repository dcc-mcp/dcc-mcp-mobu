"""Shared validation and readback helpers for MotionBuilder interchange."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

from dcc_mcp_core.skill import skill_error


class InterchangePathError(ValueError):
    """A user-correctable interchange path error."""

    def __init__(self, message: str, code: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = context


def require_path(
    raw_path: str,
    field_name: str,
    *,
    must_exist: bool,
    suffixes: Sequence[str] = (),
) -> Path:
    """Validate and normalize one absolute input or output path."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise InterchangePathError(
            f"{field_name} must be a non-empty absolute path",
            "invalid_path",
            field=field_name,
        )

    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise InterchangePathError(
            f"{field_name} must be absolute",
            "invalid_path",
            field=field_name,
        )
    path = path.absolute()

    normalized_suffixes = tuple(suffix.lower() for suffix in suffixes)
    if normalized_suffixes and path.suffix.lower() not in normalized_suffixes:
        supported = ", ".join(normalized_suffixes)
        raise InterchangePathError(
            f"{field_name} must use one of these file types: {supported}",
            "unsupported_file_type",
            field=field_name,
            supported_file_types=list(normalized_suffixes),
        )

    if must_exist and not path.exists():
        raise InterchangePathError(
            f"{field_name} does not exist",
            "input_not_found",
            field=field_name,
            path=str(path),
        )
    if must_exist and not path.is_file():
        raise InterchangePathError(
            f"{field_name} must be a file",
            "input_not_file",
            field=field_name,
            path=str(path),
        )
    if not must_exist and path.exists() and not path.is_file():
        raise InterchangePathError(
            f"{field_name} must name a file",
            "output_not_file",
            field=field_name,
            path=str(path),
        )
    if not must_exist and not path.parent.is_dir():
        raise InterchangePathError(
            f"{field_name} parent directory does not exist",
            "output_parent_not_found",
            field=field_name,
            path=str(path),
        )
    return path


def path_error(exc: InterchangePathError) -> dict[str, Any]:
    """Convert a validation exception into the standard skill envelope."""
    return skill_error(exc.message, exc.code, **exc.context)


def readback_state() -> dict[str, Any]:
    """Return JSON-safe current file and scene metadata from the host."""
    import pyfbsdk

    application = pyfbsdk.FBApplication()
    system = pyfbsdk.FBSystem()
    scene = getattr(system, "Scene", None)
    components = list(getattr(scene, "Components", ()) or ())
    model_type = getattr(pyfbsdk, "FBModel", None)
    current_take = getattr(system, "CurrentTake", None)
    takes = list(getattr(scene, "Takes", ()) or ())
    raw_file = getattr(application, "FBXFileName", None)

    return {
        "current_file": _absolute_host_path(raw_file),
        "application_version": str(getattr(system, "Version", "unknown")),
        "current_take": getattr(current_take, "Name", None) if current_take else None,
        "scene": {
            "component_count": len(components),
            "model_count": (
                sum(isinstance(component, model_type) for component in components)
                if model_type is not None
                else None
            ),
            "take_count": len(takes),
        },
    }


def _absolute_host_path(raw_path: Any) -> Optional[str]:
    if raw_path in (None, ""):
        return None
    return str(Path(str(raw_path)).expanduser().absolute())


def readback_error(operation: str, path: Path, exc: Exception) -> dict[str, Any]:
    """Return an explicit failure when a host mutation cannot be verified."""
    return skill_error(
        f"MotionBuilder {operation} completed but its state readback failed",
        "readback_failed",
        operation=operation,
        path=str(path),
        error_type=type(exc).__name__,
        error_message=str(exc),
    )


def host_operation_error(
    operation: str, file_type: str, path: Path, exc: Exception
) -> dict[str, Any]:
    """Return an explicit error when the SDK call raises."""
    return skill_error(
        f"MotionBuilder could not complete the {operation} operation",
        "host_operation_error",
        operation=operation,
        file_type=file_type,
        path=str(path),
        error_type=type(exc).__name__,
        error_message=str(exc),
    )
