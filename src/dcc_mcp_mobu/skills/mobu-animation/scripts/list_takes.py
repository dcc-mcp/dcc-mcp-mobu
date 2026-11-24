"""List MotionBuilder takes."""

from _common import as_list, take_details
from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def main() -> dict:
    """Return all scene takes and identify the current take."""
    from pyfbsdk import FBSystem

    system = FBSystem()
    current_take = getattr(system, "CurrentTake", None)
    takes = as_list(getattr(getattr(system, "Scene", None), "Takes", None))
    return skill_success(
        "MotionBuilder takes listed.",
        current_take=getattr(current_take, "Name", None) if current_take else None,
        takes=[
            take_details(
                take,
                is_current=take is current_take
                or (
                    current_take is not None
                    and getattr(take, "Name", None) == getattr(current_take, "Name", None)
                ),
            )
            for take in takes
        ],
        take_count=len(takes),
    )
