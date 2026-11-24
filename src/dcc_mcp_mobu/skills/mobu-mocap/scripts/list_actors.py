"""List visible MotionBuilder Mocap actors."""

from _common import as_list, class_name, json_value, marker_set_details, name_of
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main() -> dict:
    """Return actors and their associated marker-set state."""
    import pyfbsdk

    scene = pyfbsdk.FBSystem().Scene
    if not hasattr(scene, "Actors"):
        return skill_error(
            "MotionBuilder does not expose the scene actor collection",
            "unsupported",
            capability="scene_actors",
        )

    actors = []
    for actor in as_list(scene.Actors):
        marker_set = getattr(actor, "MarkerSet", None)
        output_marker_set = getattr(actor, "OutputMarkerSet", None)
        actors.append(
            {
                "name": name_of(actor),
                "class_name": class_name(actor),
                "marker_set": marker_set_details(marker_set, kind="actor") if marker_set else None,
                "output_marker_set": (
                    marker_set_details(output_marker_set, kind="output")
                    if output_marker_set
                    else None
                ),
                "marker_set_size": json_value(getattr(actor, "MarkerSetSize", None)),
            }
        )
    return skill_success(
        "MotionBuilder Mocap actors listed.",
        actors=actors,
        actor_count=len(actors),
    )
