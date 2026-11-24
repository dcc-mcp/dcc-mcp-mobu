"""Inspect the current MotionBuilder file and scene state."""

from _common import readback_state
from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def main() -> dict:
    """Return current file, take, and scene counts."""
    return skill_success("MotionBuilder file and scene state inspected.", **readback_state())
