"""Test read-only projections of the official MotionBuilder object model."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from dcc_mcp_core._server.inprocess_executor import run_skill_script

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "src" / "dcc_mcp_mobu" / "skills" / "mobu-api" / "scripts"


def run_script(script_name: str, **params: object) -> dict:
    return run_skill_script(str(SCRIPTS / script_name), params)


def test_system_projection_reads_official_system_and_scene_fields(monkeypatch) -> None:
    take = SimpleNamespace(Name="Take 001")
    scene = SimpleNamespace(
        Components=[SimpleNamespace(Name="Cube")],
        Characters=[SimpleNamespace(Name="Hero")],
        Takes=[take],
        Cameras=[],
    )
    system = SimpleNamespace(
        Version=2026.0,
        PythonVersionString="3.11.9",
        ComputerName="mobu-host",
        ApplicationPath="C:/Program Files/Autodesk/MotionBuilder 2026",
        UserConfigPath="C:/Users/artist/Documents/MB/2026-x64/config",
        Scene=scene,
        CurrentTake=take,
        SystemTime=SimpleNamespace(GetFrame=lambda: 24),
        CurrentDirectory=lambda: "C:/show",
        GetCommandLineArgs=lambda: ["MotionBuilder.exe", "-verbose"],
        GetLoadedPluginItemsName=lambda: ["OpticalPlugin"],
    )
    application = SimpleNamespace(
        FBXFileName="C:/show/scene.fbx",
        IsSceneModified=lambda: True,
        GetSceneAuthor=lambda: "Artist",
        GetSceneComment=lambda: "Blocking pass",
        GetSceneKeywords=lambda: "hero,blocking",
        GetSceneRevisionNumber=lambda: "12",
        GetSceneSubject=lambda: "Animation",
        GetSceneTitle=lambda: "Hero Blocking",
    )
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: system
    sdk.FBApplication = lambda: application
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    result = run_script("inspect_system.py")

    assert result["success"] is True
    assert result["context"]["application_version"] == "2026.0"
    assert result["context"]["current_take"] == "Take 001"
    assert result["context"]["application"]["scene_modified"] is True
    assert result["context"]["application"]["scene_title"] == "Hero Blocking"
    assert result["context"]["scene"]["collection_counts"] == {
        "Components": 1,
        "Characters": 1,
        "Takes": 1,
        "Cameras": 0,
    }
    assert result["context"]["loaded_plugin_count"] == 1


def test_component_projection_supports_filtering_and_bounded_results(monkeypatch) -> None:
    class Model:
        def __init__(self, name: str, selected: bool) -> None:
            self.Name = name
            self.LongName = f"Char:{name}"
            self.Selected = selected
            self.TypeInfo = 101
            self.ClassGroupName = "Model"

        def ClassName(self) -> str:
            return "FBModel"

    class Material:
        Name = "Mat"
        LongName = "Mat"
        Selected = False

        def ClassName(self) -> str:
            return "FBMaterial"

    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: SimpleNamespace(
        Scene=SimpleNamespace(Components=[Model("Hero", True), Model("Prop", False), Material()])
    )
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    result = run_script("list_components.py", class_name="fbmodel", selected_only=True, limit=1)

    assert result["success"] is True
    assert result["context"]["components"] == [
        {
            "name": "Hero",
            "long_name": "Char:Hero",
            "class_name": "FBModel",
            "class_group_name": "Model",
            "type_info": 101,
            "selected": True,
        }
    ]
    assert result["context"]["total_component_count"] == 3
    assert result["context"]["matching_component_count"] == 1


def test_character_projection_reports_sync_and_input_state(monkeypatch) -> None:
    actor = SimpleNamespace(Name="Actor")
    character = SimpleNamespace(
        Name="Hero",
        LongName="Char:Hero",
        Selected=True,
        ActiveInput=True,
        InputType="kFBCharacterInputActor",
        InputActor=actor,
        InputCharacter=None,
        SyncMode="kFBCharacterSyncEvaluation",
        CharacterExtensions=[SimpleNamespace(Name="Face")],
        GetCharacterize=lambda: True,
        GetCharacterizeError=lambda: "",
        ClassName=lambda: "FBCharacter",
    )
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: SimpleNamespace(Scene=SimpleNamespace(Characters=[character]))
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    result = run_script("list_characters.py", selected_only=True)

    assert result["success"] is True
    item = result["context"]["characters"][0]
    assert item["class_name"] == "FBCharacter"
    assert item["characterized"] is True
    assert item["input_actor"] == "Actor"
    assert item["sync_mode"] == "kFBCharacterSyncEvaluation"
    assert item["character_extension_count"] == 1


def test_api_tools_reject_invalid_limits(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "pyfbsdk", ModuleType("pyfbsdk"))

    result = run_script("list_components.py", limit=0)

    assert result["success"] is False
    assert result["error"] == "invalid_limit"
