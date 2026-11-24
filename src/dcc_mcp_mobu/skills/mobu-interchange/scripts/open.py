"""Open a MotionBuilder scene file."""

from pathlib import Path

from _common import (
    InterchangePathError,
    host_operation_error,
    path_error,
    readback_error,
    readback_state,
    require_path,
)
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main(path: str, file_type: str) -> dict:
    """Replace the active scene with an existing absolute scene file."""
    if file_type != "scene":
        return skill_error(
            "Only the scene file type is supported", "unsupported_file_type", file_type=file_type
        )
    try:
        source = require_path(
            path, "path", must_exist=True, suffixes=(".fbx", ".3ds", ".dae", ".dxf", ".obj")
        )
    except InterchangePathError as exc:
        return path_error(exc)

    import pyfbsdk

    try:
        succeeded = pyfbsdk.FBApplication().FileOpen(str(source), False)
    except Exception as exc:
        return host_operation_error("open", file_type, source, exc)
    if not succeeded:
        return skill_error(
            "MotionBuilder could not open the scene file",
            "host_operation_failed",
            operation="open",
            file_type=file_type,
            path=str(source),
        )
    try:
        state = readback_state()
    except Exception as exc:
        return readback_error("open", source, exc)
    verified = state["current_file"] == str(Path(source).absolute())
    if not verified:
        return skill_error(
            "MotionBuilder opened the file but the current file readback did not match",
            "readback_mismatch",
            operation="open",
            path=str(source),
            expected_current_file=str(source),
            actual_current_file=state["current_file"],
            state=state,
        )
    return skill_success(
        "MotionBuilder scene opened.",
        operation="open",
        file_type=file_type,
        path=str(source),
        state=state,
        verified=verified,
        postcondition={
            "method": "inspect_state",
            "expected": {"current_file": str(source)},
            "actual": state,
        },
    )
