import json
import platform
import re
import runpy
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

import pytest

from dcc_mcp_mobu import __version__


def test_package_version_matches_project_metadata() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert f'version = "{__version__}"' in project.read_text(encoding="utf-8")


def test_install_guide_tracks_release_version() -> None:
    root = Path(__file__).parents[1]
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version = "(\d+\.\d+\.\d+)"$', project, re.MULTILINE)
    assert version_match is not None
    release_version = version_match.group(1)
    guide = root / "install.md"
    content = guide.read_text(encoding="utf-8")

    assert set(re.findall(r"dcc-mcp-mobu==(\d+\.\d+\.\d+)", content)) == {release_version}
    assert f"| {release_version} |" in content


def test_release_please_updates_both_install_guide_version_surfaces() -> None:
    root = Path(__file__).parents[1]
    config = json.loads((root / "release-please-config.json").read_text(encoding="utf-8"))
    extra_files = config["packages"]["."]["extra-files"]
    assert {"type": "generic", "path": "install.md"} in extra_files

    content = (root / "install.md").read_text(encoding="utf-8")
    next_version = "12.34.56"
    updated_lines = []
    updated_count = 0
    for line in content.splitlines():
        if "x-release-please-version" in line:
            line, count = re.subn(r"\d+\.\d+\.\d+", next_version, line, count=1)
            updated_count += count
        updated_lines.append(line)
    rendered = re.sub(
        r"[ \t]*<!-- x-release-please-version -->[ \t]*", "", "\n".join(updated_lines)
    )

    assert updated_count == 2
    assert f"dcc-mcp-mobu=={next_version}" in rendered
    assert f"| {next_version} |" in rendered


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

    pyfbsdk.FBSystem = FakeSystem
    monkeypatch.setitem(sys.modules, "pyfbsdk", pyfbsdk)

    namespace = runpy.run_path(str(script), run_name="__mobu_diagnostics_ping_test__")
    result = namespace["main"]()

    assert result["success"] is True
    assert result["context"] == {
        "ready": True,
        "application_version": "2026.1",
        "python_version": platform.python_version(),
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
    dispatcher = SimpleNamespace(install=lambda: None, uninstall=lambda: None)
    monkeypatch.setattr(server_module, "MobuDispatcher", lambda: dispatcher)
    monkeypatch.setattr(
        server_module,
        "_dispatcher",
        dispatcher,
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


@pytest.mark.parametrize("stop_raises", [False, True])
def test_stop_replaces_dispatcher_before_restart(monkeypatch, stop_raises) -> None:
    from types import SimpleNamespace

    from dcc_mcp_mobu import server as server_module

    events = []
    bindings = []

    def dispatcher(name):
        return SimpleNamespace(
            install=lambda: events.append((name, "install")),
            uninstall=lambda: events.append((name, "uninstall")),
        )

    original = dispatcher("original")
    replacement = dispatcher("replacement")
    next_dispatcher = dispatcher("next")
    replacements = iter([replacement, next_dispatcher])

    def construct(port):
        binding = server_module._dispatcher
        bindings.append(binding)

        def stop():
            events.append(("server", "stop"))
            if stop_raises and binding is original:
                raise RuntimeError("shutdown failure")

        return SimpleNamespace(
            register_builtin_actions=lambda: None,
            start=lambda: None,
            stop=stop,
        )

    monkeypatch.setattr(server_module, "_server", None)
    monkeypatch.setattr(server_module, "_dispatcher", original)
    monkeypatch.setattr(server_module, "MobuDispatcher", lambda: next(replacements))
    monkeypatch.setattr(server_module, "MobuMcpServer", construct)

    server_module.start_server()
    if stop_raises:
        with pytest.raises(RuntimeError, match="shutdown failure"):
            server_module.stop_server()
    else:
        server_module.stop_server()

    assert server_module._server is None
    assert server_module._dispatcher is replacement
    assert events == [("original", "install"), ("server", "stop"), ("original", "uninstall")]

    server_module.start_server()
    server_module.stop_server()

    assert bindings == [original, replacement]
    assert server_module._server is None
    assert server_module._dispatcher is next_dispatcher
    assert events[-3:] == [
        ("replacement", "install"),
        ("server", "stop"),
        ("replacement", "uninstall"),
    ]


@pytest.mark.parametrize("failure_stage", ["construct", "register", "start"])
def test_failed_start_does_not_cache_server_or_reuse_shutdown_dispatcher(
    monkeypatch, failure_stage
):
    from types import SimpleNamespace

    from dcc_mcp_mobu import server as server_module

    events = []
    old = SimpleNamespace(
        install=lambda: events.append("install"),
        uninstall=lambda: events.append("uninstall"),
    )
    fresh = object()

    def stage(name):
        events.append(name)
        if failure_stage == name:
            raise RuntimeError("startup failure")

    def construct(port):
        stage("construct")
        return SimpleNamespace(
            register_builtin_actions=lambda: stage("register"),
            start=lambda: stage("start"),
            stop=lambda: stage("stop"),
        )

    monkeypatch.setattr(server_module, "_server", None)
    monkeypatch.setattr(server_module, "_dispatcher", old)
    monkeypatch.setattr(server_module, "MobuMcpServer", construct)
    monkeypatch.setattr(server_module, "MobuDispatcher", lambda: fresh)
    with pytest.raises(RuntimeError, match="startup failure"):
        server_module.start_server()
    assert server_module._server is None
    assert server_module._dispatcher is fresh
    assert events[-1] == "uninstall"
    assert ("stop" in events) == (failure_stage != "construct")
