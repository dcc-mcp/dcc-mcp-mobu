"""List official MotionBuilder FBComponent identity fields."""

from typing import Optional

from _common import as_list, component_details, safe_attribute
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main(class_name: Optional[str] = None, selected_only: bool = False, limit: int = 500) -> dict:
    """Return bounded component metadata from the current FBScene."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 5000:
        return skill_error("limit must be an integer between 1 and 5000", "invalid_limit")

    from pyfbsdk import FBSystem

    scene = safe_attribute(FBSystem(), "Scene")
    components = as_list(safe_attribute(scene, "Components"))
    expected_class = class_name.casefold() if class_name else None
    matching = []
    for component in components:
        details = component_details(component)
        if expected_class and details["class_name"].casefold() != expected_class:
            continue
        if selected_only and details["selected"] is not True:
            continue
        matching.append(details)

    return skill_success(
        "MotionBuilder components listed.",
        components=matching[:limit],
        component_count=len(matching[:limit]),
        total_component_count=len(components),
        matching_component_count=len(matching),
        truncated=len(matching) > limit,
    )
