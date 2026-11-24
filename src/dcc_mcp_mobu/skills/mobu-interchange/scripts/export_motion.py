"""Export the current MotionBuilder take to an FBX motion file."""

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
def main(path: str, file_type: str, overwrite: bool = False) -> dict:
    """Export the current take to an explicit absolute FBX path."""
    if file_type != "fbx":
        return skill_error(
            "Only the FBX motion file type is supported",
            "unsupported_file_type",
            file_type=file_type,
        )
    try:
        target = require_path(path, "path", must_exist=False, suffixes=(".fbx",))
    except InterchangePathError as exc:
        return path_error(exc)
    if target.exists() and not overwrite:
        return skill_error(
            "The export target already exists and overwrite is false",
            "output_exists",
            operation="export",
            file_type=file_type,
            path=str(target),
        )

    import pyfbsdk

    try:
        succeeded = pyfbsdk.FBApplication().FileExport(str(target))
    except Exception as exc:
        return host_operation_error("export", file_type, target, exc)
    if not succeeded:
        return skill_error(
            "MotionBuilder could not export the motion file",
            "host_operation_failed",
            operation="export",
            file_type=file_type,
            path=str(target),
        )
    if not target.is_file():
        return skill_error(
            "MotionBuilder reported export success but the output file was not found",
            "output_verification_failed",
            operation="export",
            file_type=file_type,
            path=str(target),
        )
    try:
        state = readback_state()
    except Exception as exc:
        return readback_error("export", target, exc)
    return skill_success(
        "MotionBuilder motion file exported.",
        operation="export",
        file_type=file_type,
        path=str(target),
        overwrite=bool(overwrite),
        state=state,
        verified=True,
        postcondition={
            "method": "output_file_and_inspect_state",
            "actual": {"path": str(target), "state": state},
        },
    )
