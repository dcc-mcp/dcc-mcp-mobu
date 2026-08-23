import runpy
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

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


def test_startup_script_captures_bootstrap_errors_without_stopping_later_scripts(
    monkeypatch,
) -> None:
    startup = (
        Path(__file__).parents[1]
        / "src"
        / "dcc_mcp_mobu"
        / "mobu_plugin"
        / "startup"
        / "dcc_mcp_mobu.py"
    )
    captured = []
    core = ModuleType("dcc_mcp_core")

    @contextmanager
    def capture_bootstrap_errors(dcc_type, **metadata):
        captured.append((dcc_type, metadata))
        yield

    core.capture_bootstrap_errors = capture_bootstrap_errors
    plugin = ModuleType("dcc_mcp_mobu.plugin")

    def fail_initialize():
        raise RuntimeError("synthetic startup failure")

    plugin.initialize = fail_initialize
    monkeypatch.setitem(sys.modules, "dcc_mcp_core", core)
    monkeypatch.setitem(sys.modules, "dcc_mcp_mobu.plugin", plugin)

    runpy.run_path(str(startup), run_name="__dcc_mcp_mobu_startup_test__")

    assert captured == [
        (
            "mobu",
            {
                "adapter_version": __version__,
                "min_core_version": "0.19.45",
            },
        )
    ]


def test_distribution_declares_standard_cli_and_adapter_entry_points() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    metadata = project.read_text(encoding="utf-8")

    assert '[project.scripts]\ndcc-mcp-mobu = "dcc_mcp_mobu.install_cli:main"' in metadata
    assert (
        '[project.entry-points."dcc_mcp.adapters"]\nmobu = "dcc_mcp_mobu:MobuMcpServer"'
    ) in metadata

    from dcc_mcp_mobu import MobuMcpServer

    assert MobuMcpServer.__name__ == "MobuMcpServer"


def test_diagnostics_ping_reports_motionbuilder_and_embedded_python_lazily(monkeypatch) -> None:
    script = (
        Path(__file__).parents[1]
        / "src"
        / "dcc_mcp_mobu"
        / "skills"
        / "mobu-diagnostics"
        / "scripts"
        / "ping.py"
    )
    pyfbsdk = ModuleType("pyfbsdk")

    class FakeSystem:
        Version = "2026.1"
        PythonVersionString = "3.11.9"

    pyfbsdk.FBSystem = FakeSystem
    monkeypatch.setitem(sys.modules, "pyfbsdk", pyfbsdk)

    namespace = runpy.run_path(str(script), run_name="__mobu_diagnostics_ping_test__")
    result = namespace["main"]()

    assert result["success"] is True
    assert result["context"] == {
        "ready": True,
        "application_version": "2026.1",
        "python_version": "3.11.9",
    }


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
