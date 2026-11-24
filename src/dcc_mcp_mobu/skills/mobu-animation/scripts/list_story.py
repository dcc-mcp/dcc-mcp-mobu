"""List MotionBuilder Story tracks and clips."""

from _common import iter_tracks, track_details
from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def main() -> dict:
    """Return read-only Story track, sub-track, and clip details."""
    from pyfbsdk import FBStory

    story = FBStory()
    tracks = [
        track_details(track, folder_path) for track, folder_path in iter_tracks(story.RootFolder)
    ]
    return skill_success(
        "MotionBuilder Story tracks listed.", tracks=tracks, track_count=len(tracks)
    )
