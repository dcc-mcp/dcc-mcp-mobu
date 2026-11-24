"""Append a MotionBuilder scene file."""

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
    """Append an existing absolute scene file to the active scene."""
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
        succeeded = pyfbsdk.FBApplication().FileAppend(str(source), False)
    except Exception as exc:
        return host_operation_error("append", file_type, source, exc)
    if not succeeded:
        return skill_error(
            "MotionBuilder could not append the scene file",
            "host_operation_failed",
            operation="append",
            file_type=file_type,
            path=str(source),
        )
    try:
        state = readback_state()
    except Exception as exc:
        return readback_error("append", source, exc)
    return skill_success(
        "MotionBuilder scene appended.",
        operation="append",
        file_type=file_type,
        path=str(source),
        state=state,
        verified=True,
        postcondition={"method": "inspect_state", "actual": state},
    )
