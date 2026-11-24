"""Inspect the current MotionBuilder scene."""

from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def main() -> dict:
    """Return concise scene metadata."""
    from pyfbsdk import FBModel, FBSystem

    system = FBSystem()
    scene = system.Scene
    current_take = system.CurrentTake
    characters = [
        getattr(character, "LongName", getattr(character, "Name", ""))
        for character in getattr(scene, "Characters", ())
    ]
    takes = [getattr(take, "Name", "") for take in getattr(scene, "Takes", ())]
    return skill_success(
        "MotionBuilder scene inspected.",
        application_version=str(system.Version),
        current_take=current_take.Name if current_take else None,
        component_count=len(scene.Components),
        model_count=sum(isinstance(component, FBModel) for component in scene.Components),
        character_count=len(characters),
        characters=characters,
        take_count=len(takes),
        takes=takes,
    )


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
