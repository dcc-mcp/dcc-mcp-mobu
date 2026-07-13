"""List models in the current MotionBuilder scene."""

from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def main() -> dict:
    """Return model names without exposing a raw scripting surface."""
    from pyfbsdk import FBSystem

    models = [{"name": model.Name} for model in FBSystem().Scene.Models]
    return skill_success("MotionBuilder models listed.", models=models, model_count=len(models))


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
