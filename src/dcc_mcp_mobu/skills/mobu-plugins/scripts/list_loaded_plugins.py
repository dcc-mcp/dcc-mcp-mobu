"""List loaded MotionBuilder plug-in items."""

from _common import call_strings
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main() -> dict:
    """Return loaded plug-in item names, groups, and information."""
    import pyfbsdk

    system = pyfbsdk.FBSystem()
    if not callable(getattr(system, "GetLoadedPluginItemsName", None)):
        return skill_error(
            "MotionBuilder does not expose loaded plug-in item discovery",
            "unsupported",
            capability="loaded_plugin_items",
        )

    names = call_strings(system, "GetLoadedPluginItemsName")
    plugins = [
        {
            "name": name,
            "groups": call_strings(system, "GetLoadedPluginItemGroups", name),
            "info": call_strings(system, "GetLoadedPluginItemInfo", name),
        }
        for name in names
    ]
    return skill_success(
        "MotionBuilder loaded plug-ins listed.",
        plugins=plugins,
        plugin_count=len(plugins),
    )
