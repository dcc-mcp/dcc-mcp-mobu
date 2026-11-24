"""Inspect the current MotionBuilder take."""

from _common import take_details
from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def main() -> dict:
    """Return the active take or an explicit null current-take result."""
    from pyfbsdk import FBSystem

    current_take = FBSystem().CurrentTake
    return skill_success(
        "MotionBuilder current take inspected.",
        current_take=take_details(current_take, is_current=True) if current_take else None,
    )
