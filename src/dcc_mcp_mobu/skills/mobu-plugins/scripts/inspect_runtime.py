"""Inspect MotionBuilder plug-in paths and safe operation boundaries."""

from _common import call_strings
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main() -> dict:
    """Return plug-in search paths and explicit read-only capability boundaries."""
    import pyfbsdk

    system = pyfbsdk.FBSystem()
    if not callable(getattr(system, "GetPluginPath", None)):
        return skill_error(
            "MotionBuilder does not expose plug-in runtime discovery",
            "unsupported",
            capability="plugin_runtime",
        )

    return skill_success(
        "MotionBuilder plug-in runtime inspected.",
        plugin_paths=call_strings(system, "GetPluginPath"),
        python_startup_paths=call_strings(system, "GetPythonStartupPath"),
        capabilities={
            "loaded_plugin_item_discovery": "supported",
            "library_load": "unsupported_read_only_surface",
            "library_free": "unsupported_read_only_surface",
            "create_object": "unsupported_read_only_surface",
        },
    )
