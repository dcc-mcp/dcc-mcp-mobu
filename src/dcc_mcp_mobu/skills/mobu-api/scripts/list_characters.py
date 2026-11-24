"""List official MotionBuilder FBCharacter state."""

from _common import (
    as_bool,
    as_list,
    as_string,
    call_value,
    component_details,
    name_of,
    safe_attribute,
)
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


def character_details(character: object) -> dict[str, object]:
    details = component_details(character)
    characterize_error = call_value(character, "GetCharacterizeError")
    details.update(
        {
            "characterized": as_bool(call_value(character, "GetCharacterize")),
            "characterize_error": as_string(characterize_error),
            "active_input": as_bool(safe_attribute(character, "ActiveInput")),
            "input_type": as_string(safe_attribute(character, "InputType")),
            "input_actor": name_of(safe_attribute(character, "InputActor")),
            "input_character": name_of(safe_attribute(character, "InputCharacter")),
            "sync_mode": as_string(safe_attribute(character, "SyncMode")),
            "character_extension_count": len(
                as_list(safe_attribute(character, "CharacterExtensions"))
            ),
        }
    )
    return details


@skill_entry
def main(selected_only: bool = False, limit: int = 200) -> dict:
    """Return bounded character state from the current FBScene."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        return skill_error("limit must be an integer between 1 and 1000", "invalid_limit")

    from pyfbsdk import FBSystem

    scene = safe_attribute(FBSystem(), "Scene")
    characters = as_list(safe_attribute(scene, "Characters"))
    matching = [
        character_details(character)
        for character in characters
        if not selected_only or safe_attribute(character, "Selected") is True
    ]
    return skill_success(
        "MotionBuilder characters listed.",
        characters=matching[:limit],
        character_count=len(matching[:limit]),
        total_character_count=len(characters),
        matching_character_count=len(matching),
        truncated=len(matching) > limit,
    )
