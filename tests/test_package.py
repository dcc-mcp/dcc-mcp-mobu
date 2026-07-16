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


def test_start_server_defers_port_resolution_to_core(monkeypatch) -> None:
    from types import SimpleNamespace

    from dcc_mcp_mobu import server as server_module

    ports = []
    stub = SimpleNamespace(
        is_running=False,
        register_builtin_actions=lambda: None,
        start=lambda: None,
        stop=lambda: None,
    )

    monkeypatch.setattr(server_module, "_server", None)
    monkeypatch.setattr(
        server_module,
        "_dispatcher",
        SimpleNamespace(install=lambda: None, uninstall=lambda: None),
    )
    monkeypatch.setattr(
        server_module, "MobuMcpServer", lambda port=None: ports.append(port) or stub
    )
    monkeypatch.setenv("DCC_MCP_MOBU_PORT", "8765")

    server_module.start_server(0)
    server_module.stop_server()
    server_module.start_server()
    server_module.stop_server()

    assert ports == [0, None]
