"""Inspect official MotionBuilder FBSystem and FBScene metadata."""

from _common import (
    as_list,
    as_string,
    call_value,
    name_of,
    safe_attribute,
    time_details,
)
from dcc_mcp_core.skill import skill_entry, skill_success

SCENE_COLLECTIONS = (
    "Components",
    "Models",
    "Cameras",
    "Characters",
    "Constraints",
    "Devices",
    "MarkerSets",
    "Sets",
    "Takes",
    "Textures",
    "VideoClips",
)


@skill_entry
def main() -> dict:
    """Return JSON-safe system, scene, take, and loaded-plugin metadata."""
    from pyfbsdk import FBApplication, FBSystem

    application = FBApplication()
    system = FBSystem()
    scene = safe_attribute(system, "Scene")
    current_take = safe_attribute(system, "CurrentTake")
    plugin_names = call_value(system, "GetLoadedPluginItemsName")
    collection_counts = {
        collection_name: len(as_list(safe_attribute(scene, collection_name)))
        for collection_name in SCENE_COLLECTIONS
        if safe_attribute(scene, collection_name) is not None
    }
    return skill_success(
        "MotionBuilder system inspected.",
        application_version=as_string(safe_attribute(system, "Version")),
        python_version=as_string(safe_attribute(system, "PythonVersionString")),
        computer_name=as_string(safe_attribute(system, "ComputerName")),
        application_path=as_string(safe_attribute(system, "ApplicationPath")),
        user_config_path=as_string(safe_attribute(system, "UserConfigPath")),
        current_directory=as_string(call_value(system, "CurrentDirectory")),
        command_line_args=[
            as_string(value) for value in as_list(call_value(system, "GetCommandLineArgs"))
        ],
        system_time=time_details(safe_attribute(system, "SystemTime")),
        current_take=name_of(current_take),
        application={
            "file_name": as_string(safe_attribute(application, "FBXFileName")),
            "scene_modified": call_value(application, "IsSceneModified"),
            "scene_author": as_string(call_value(application, "GetSceneAuthor")),
            "scene_comment": as_string(call_value(application, "GetSceneComment")),
            "scene_keywords": as_string(call_value(application, "GetSceneKeywords")),
            "scene_revision": as_string(call_value(application, "GetSceneRevisionNumber")),
            "scene_subject": as_string(call_value(application, "GetSceneSubject")),
            "scene_title": as_string(call_value(application, "GetSceneTitle")),
        },
        scene={
            "collection_counts": collection_counts,
            "long_name": as_string(safe_attribute(scene, "LongName")),
        },
        loaded_plugin_count=len(as_list(plugin_names)),
    )
