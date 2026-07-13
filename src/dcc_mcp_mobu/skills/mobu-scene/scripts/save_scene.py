"""Save the current MotionBuilder scene to a typed path."""

from pathlib import Path

from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main(path: str) -> dict:
    """Save the scene as an FBX file at an explicit absolute path."""
    from pyfbsdk import FBApplication

    target = Path(path).expanduser()
    if not target.is_absolute():
        return skill_error("path must be absolute")
    if target.suffix.lower() != ".fbx":
        return skill_error("path must end with .fbx")

    target.parent.mkdir(parents=True, exist_ok=True)
    if not FBApplication().FileSave(str(target)):
        return skill_error("MotionBuilder could not save the scene", path=str(target))
    return skill_success("MotionBuilder scene saved.", path=str(target))


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
