"""Typed MotionBuilder readiness probe."""

from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def main() -> dict:
    """Return host and embedded-Python version evidence."""
    from pyfbsdk import FBSystem

    system = FBSystem()
    return skill_success(
        "MotionBuilder host API is ready.",
        ready=True,
        application_version=str(system.Version),
        python_version=str(system.PythonVersionString),
    )


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
