"""Test second-batch read-only MotionBuilder skills with mocked SDK objects."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from dcc_mcp_core._server.inprocess_executor import run_skill_script

ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "src" / "dcc_mcp_mobu" / "skills"


def run_script(skill: str, script: str, **params: object) -> dict:
    return run_skill_script(str(SKILLS / skill / "scripts" / script), params)


def test_second_batch_skill_declarations_are_read_only_and_main_thread() -> None:
    import yaml

    for skill, expected_tools in {
        "mobu-mocap": {"list_devices", "list_actors", "list_marker_sets"},
        "mobu-plugins": {"list_loaded_plugins", "inspect_runtime"},
        "mobu-production-tracking": {"inspect_mapping_context", "check_connection"},
    }.items():
        data = yaml.safe_load((SKILLS / skill / "tools.yaml").read_text(encoding="utf-8"))
        tools = {tool["name"]: tool for tool in data["tools"]}
        assert set(tools) == expected_tools
        assert all(tool["read_only"] for tool in tools.values())
        assert all(tool["destructive"] is False for tool in tools.values())
        assert all(tool["idempotent"] is True for tool in tools.values())
        assert all(tool["affinity"] == "main" for tool in tools.values())
        assert all(tool["input_schema"]["additionalProperties"] is False for tool in tools.values())


def test_second_batch_scripts_have_no_raw_entrypoints() -> None:
    scripts = [
        path
        for skill in ("mobu-mocap", "mobu-plugins", "mobu-production-tracking")
        for path in (SKILLS / skill / "scripts").glob("*.py")
    ]
    assert scripts
    assert all("__main__" not in path.read_text(encoding="utf-8") for path in scripts)


def test_mocap_lists_devices_actors_and_marker_sets(monkeypatch) -> None:
    marker_set = _marker_set("ActorMarkers")
    actor = SimpleNamespace(
        Name="Actor",
        MarkerSet=marker_set,
        OutputMarkerSet=None,
        MarkerSetSize=2.0,
    )

    class OpticalDevice:
        Name = "Optical Device"
        Online = True
        Status = "Ready"
        Live = True
        RecordMode = False
        RecordingStartTime = _time(1)
        RecordingStopTime = _time(24)
        SamplingMode = "Free Run"
        SamplingPeriod = _time(0)
        Markers = [SimpleNamespace(Name="Marker")]
        SupportOcclusion = True
        OpticalSamplingRate = 120.0
        UseMarkerTimeStamp = False
        ForceOpticalSamplingRate = False

    optical = OpticalDevice()
    scene = SimpleNamespace(
        Devices=[optical],
        Actors=[actor],
        MarkerSets=[marker_set],
        CharacterMarkerSets=[],
    )
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: SimpleNamespace(Scene=scene)
    sdk.FBDeviceOptical = OpticalDevice
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    devices = run_script("mobu-mocap", "list_devices.py")
    actors = run_script("mobu-mocap", "list_actors.py")
    marker_sets = run_script("mobu-mocap", "list_marker_sets.py")

    assert devices["success"] is True
    assert devices["context"]["devices"][0]["online"] is True
    assert devices["context"]["devices"][0]["calibration_status"]["status"] == "unsupported"
    assert actors["context"]["actors"][0]["marker_set"]["link_to_model_ok"] is True
    assert marker_sets["context"]["marker_set_count"] == 1


def test_mocap_reports_unsupported_collection(monkeypatch) -> None:
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: SimpleNamespace(Scene=SimpleNamespace())
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    result = run_script("mobu-mocap", "list_devices.py")

    assert result["success"] is False
    assert result["error"] == "unsupported"


def test_plugins_reads_loaded_items_and_paths_without_mutating(monkeypatch) -> None:
    calls: list[str] = []

    class System:
        def GetLoadedPluginItemsName(self):
            calls.append("names")
            return ["OpticalPlugin"]

        def GetLoadedPluginItemGroups(self, name):
            calls.append(f"groups:{name}")
            return ["Devices"]

        def GetLoadedPluginItemInfo(self, name):
            calls.append(f"info:{name}")
            return ["Vendor", "Version"]

        def GetPluginPath(self):
            calls.append("plugin_paths")
            return "C:/MotionBuilder/plugins"

        def GetPythonStartupPath(self):
            calls.append("startup_paths")
            return "C:/MotionBuilder/PythonStartup"

    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = System
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    plugins = run_script("mobu-plugins", "list_loaded_plugins.py")
    runtime = run_script("mobu-plugins", "inspect_runtime.py")

    assert plugins["context"]["plugins"][0]["name"] == "OpticalPlugin"
    assert runtime["context"]["plugin_paths"] == ["C:/MotionBuilder/plugins"]
    assert runtime["context"]["python_startup_paths"] == ["C:/MotionBuilder/PythonStartup"]
    assert runtime["context"]["capabilities"]["library_load"] == "unsupported_read_only_surface"
    assert "library_load" not in calls
    assert "library_free" not in calls


def test_plugins_reports_unsupported_discovery(monkeypatch) -> None:
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: SimpleNamespace()
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    result = run_script("mobu-plugins", "list_loaded_plugins.py")

    assert result["success"] is False
    assert result["error"] == "unsupported"


def test_production_tracking_mapping_is_host_only_and_connection_is_explicitly_unavailable(
    monkeypatch,
) -> None:
    system = SimpleNamespace(
        CurrentTake=SimpleNamespace(Name="Take 001"),
        Scene=SimpleNamespace(
            Components=[SimpleNamespace(Name="AssetRoot")],
            Takes=[SimpleNamespace(Name="Take 001")],
        ),
    )

    class Model:
        pass

    component = Model()
    component.Name = "AssetRoot"
    system.Scene.Components = [component]
    application = SimpleNamespace(
        FBXFileName="C:/show/asset.fbx",
        GetSceneAuthor=lambda: "Artist",
        GetSceneComment=lambda: "Shot context",
        GetSceneKeywords=lambda: "shot010,asset010",
    )
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: system
    sdk.FBApplication = lambda: application
    sdk.FBModel = Model
    sdk.FBStory = lambda: SimpleNamespace(RootFolder=SimpleNamespace(Tracks=[], Components=[]))
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)
    monkeypatch.delenv("SHOTGRID_URL", raising=False)
    monkeypatch.delenv("SHOTGRID_SCRIPT_NAME", raising=False)
    monkeypatch.delenv("SHOTGRID_SCRIPT_KEY", raising=False)

    mapping = run_script("mobu-production-tracking", "inspect_mapping_context.py")
    connection = run_script("mobu-production-tracking", "check_connection.py")

    assert mapping["success"] is True
    assert mapping["context"]["asset_candidates"] == ["AssetRoot"]
    assert mapping["context"]["production_tracking"]["adapter_status"] == "unavailable"
    assert connection["success"] is True
    assert connection["context"]["status"] == "unavailable"
    assert connection["context"]["secrets_exposed"] is False


def test_production_tracking_reuses_optional_fpt_runtime_protocol(monkeypatch) -> None:
    class RuntimeContext:
        @staticmethod
        def get_current_server():
            return object()

        @staticmethod
        def get_request_connection_info(server, params):
            return {
                "authenticated": True,
                "server_version": "8.0.0",
                "script_key": "must-not-be-returned",
            }

    fpt = ModuleType("dcc_mcp_fpt")
    runtime = ModuleType("dcc_mcp_fpt.runtime_context")
    runtime.get_current_server = RuntimeContext.get_current_server
    runtime.get_request_connection_info = RuntimeContext.get_request_connection_info
    monkeypatch.setitem(sys.modules, "dcc_mcp_fpt", fpt)
    monkeypatch.setitem(sys.modules, "dcc_mcp_fpt.runtime_context", runtime)

    result = run_script("mobu-production-tracking", "check_connection.py")

    assert result["success"] is True
    assert result["context"]["status"] == "connected"
    assert result["context"]["connection"]["server_version"] == "8.0.0"
    assert "script_key" not in result["context"]["connection"]


def _marker_set(name: str) -> object:
    return SimpleNamespace(
        Name=name,
        GetLinkToModelOk=lambda: True,
        GetUsedMarkerCount=lambda: 3,
        GetMarkerCount=lambda: 4,
        GetReferenceModel=lambda: SimpleNamespace(Name="Hips"),
    )


def _time(frame: int) -> object:
    return SimpleNamespace(
        GetFrame=lambda: frame,
        GetSecondDouble=lambda: frame / 24.0,
        GetTimeString=lambda: f"00:00:{frame:02d}",
    )
