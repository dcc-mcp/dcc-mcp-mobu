"""Import a MotionBuilder FBX motion file."""

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
def main(
    path: str,
    file_type: str,
    match_models: bool = False,
    create_unmatched_models: bool = True,
) -> dict:
    """Import an existing absolute FBX motion file into the current take."""
    if file_type != "fbx":
        return skill_error(
            "Only the FBX motion file type is supported",
            "unsupported_file_type",
            file_type=file_type,
        )
    try:
        source = require_path(path, "path", must_exist=True, suffixes=(".fbx",))
    except InterchangePathError as exc:
        return path_error(exc)

    import pyfbsdk

    try:
        succeeded = pyfbsdk.FBApplication().FileImport(
            str(source), bool(match_models), bool(create_unmatched_models)
        )
    except Exception as exc:
        return host_operation_error("import", file_type, source, exc)
    if not succeeded:
        return skill_error(
            "MotionBuilder could not import the motion file",
            "host_operation_failed",
            operation="import",
            file_type=file_type,
            path=str(source),
        )
    try:
        state = readback_state()
    except Exception as exc:
        return readback_error("import", source, exc)
    return skill_success(
        "MotionBuilder motion file imported.",
        operation="import",
        file_type=file_type,
        path=str(source),
        match_models=bool(match_models),
        create_unmatched_models=bool(create_unmatched_models),
        state=state,
        verified=True,
        postcondition={"method": "inspect_state", "actual": state},
    )
