"""Inspect MotionBuilder metadata that can map to production tracking."""

from _common import (
    absolute_scene_file,
    config_diagnostics,
    iter_story_tracks,
    json_time,
    resolve_adapter,
)
from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def main() -> dict:
    """Return non-mutating Asset, Shot, Take, and scene mapping candidates."""
    import pyfbsdk

    application = pyfbsdk.FBApplication()
    system = pyfbsdk.FBSystem()
    scene = system.Scene
    current_take = getattr(system, "CurrentTake", None)
    components = list(getattr(scene, "Components", ()) or ())
    model_type = getattr(pyfbsdk, "FBModel", None)

    asset_candidates = [
        str(component.Name)
        for component in components
        if model_type is not None and isinstance(component, model_type) and component.Name
    ]
    take_candidates = [
        str(take.Name) for take in list(getattr(scene, "Takes", ()) or ()) if take.Name
    ]
    shot_candidates = []
    try:
        story = pyfbsdk.FBStory()
        for track, folder_path in iter_story_tracks(story.RootFolder):
            track_type = str(getattr(track, "Type", "unknown"))
            if "shot" not in track_type.lower():
                continue
            for clip in list(getattr(track, "Clips", ()) or ()):
                camera = getattr(clip, "ShotCamera", None)
                shot_candidates.append(
                    {
                        "name": getattr(clip, "Name", None),
                        "track_name": getattr(track, "Name", None),
                        "track_type": track_type,
                        "folder_path": folder_path,
                        "start": json_time(getattr(clip, "Start", None)),
                        "stop": json_time(getattr(clip, "Stop", None)),
                        "camera": getattr(camera, "Name", None) if camera else None,
                    }
                )
    except AttributeError:
        shot_candidates = []

    adapter, adapter_reason = resolve_adapter()
    return skill_success(
        "MotionBuilder production-tracking mapping context inspected.",
        scene={
            "current_file": absolute_scene_file(getattr(application, "FBXFileName", None)),
            "author": _call_string(application, "GetSceneAuthor"),
            "comment": _call_string(application, "GetSceneComment"),
            "keywords": _call_string(application, "GetSceneKeywords"),
            "component_count": len(components),
        },
        asset_candidates=asset_candidates,
        current_take=getattr(current_take, "Name", None) if current_take else None,
        take_candidates=take_candidates,
        shot_candidates=shot_candidates,
        production_tracking={
            "contract": "dcc-mcp-fpt",
            "adapter_status": "available" if adapter else "unavailable",
            "adapter_reason": adapter_reason,
            "configuration": config_diagnostics(),
            "writes_enabled": False,
        },
    )


def _call_string(value: object, method_name: str):
    method = getattr(value, method_name, None)
    if not callable(method):
        return None
    try:
        return str(method())
    except Exception:
        return None
