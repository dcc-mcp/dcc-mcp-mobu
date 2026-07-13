from pathlib import Path

from dcc_mcp_mobu import __version__


def test_package_version_matches_project_metadata() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert f'version = "{__version__}"' in project.read_text(encoding="utf-8")


def test_startup_script_is_packaged_with_source() -> None:
    startup = (
        Path(__file__).parents[1]
        / "src"
        / "dcc_mcp_mobu"
        / "mobu_plugin"
        / "startup"
        / "dcc_mcp_mobu.py"
    )
    assert startup.is_file()
