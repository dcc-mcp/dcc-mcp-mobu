"""Guard the release workflow against publishing the triggering branch."""

from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "release.yml"


def test_release_publishes_distributions_built_from_created_tag() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "publish_tag:" in workflow
    assert "tag_name: ${{ steps.release.outputs.tag_name }}" in workflow
    assert "ref: ${{ inputs.publish_tag || needs.release-please.outputs.tag_name }}" in workflow
    assert "contents: write" in workflow
    assert (
        'gh release upload "${{ inputs.publish_tag || needs.release-please.outputs.tag_name }}" '
        "dist/*.whl dist/*.tar.gz --clobber"
    ) in workflow
