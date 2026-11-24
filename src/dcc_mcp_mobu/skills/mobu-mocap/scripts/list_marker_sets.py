"""List visible MotionBuilder marker sets."""

from _common import as_list, marker_set_details
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main() -> dict:
    """Return scene and character marker sets without changing them."""
    import pyfbsdk

    scene = pyfbsdk.FBSystem().Scene
    if not hasattr(scene, "MarkerSets"):
        return skill_error(
            "MotionBuilder does not expose the scene marker-set collection",
            "unsupported",
            capability="scene_marker_sets",
        )

    marker_sets = [
        marker_set_details(marker_set, kind="scene") for marker_set in as_list(scene.MarkerSets)
    ]
    character_marker_sets = [
        marker_set_details(marker_set, kind="character")
        for marker_set in as_list(getattr(scene, "CharacterMarkerSets", None))
    ]
    return skill_success(
        "MotionBuilder marker sets listed.",
        marker_sets=marker_sets,
        character_marker_sets=character_marker_sets,
        marker_set_count=len(marker_sets),
        character_marker_set_count=len(character_marker_sets),
    )
