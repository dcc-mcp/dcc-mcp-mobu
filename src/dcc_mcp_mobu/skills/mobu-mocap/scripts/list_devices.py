"""List visible MotionBuilder Mocap devices."""

from _common import as_list, device_details
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main() -> dict:
    """Return read-only device and optical-device diagnostics."""
    import pyfbsdk

    scene = pyfbsdk.FBSystem().Scene
    if not hasattr(scene, "Devices"):
        return skill_error(
            "MotionBuilder does not expose the scene device collection",
            "unsupported",
            capability="scene_devices",
        )

    devices = as_list(scene.Devices)
    optical_type = getattr(pyfbsdk, "FBDeviceOptical", None)
    device_items = [
        device_details(
            device,
            optical=optical_type is not None and isinstance(device, optical_type),
        )
        for device in devices
    ]
    return skill_success(
        "MotionBuilder Mocap devices listed.",
        devices=device_items,
        device_count=len(device_items),
        optical_device_count=sum(item["optical"] for item in device_items),
    )
