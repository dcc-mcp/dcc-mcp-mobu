"""Keep scene tools compatible with the documented MotionBuilder SDK surface."""

import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

SCRIPTS = Path(__file__).parents[1] / "src" / "dcc_mcp_mobu" / "skills" / "mobu-scene" / "scripts"


@pytest.mark.parametrize("model_names", [[], ["Camera", "Parent", "Child"]])
@pytest.mark.parametrize("tool", ["inspect_scene", "list_models"])
def test_scene_tools_use_components_without_a_models_attribute(monkeypatch, model_names, tool):
    class Model:
        def __init__(self, name):
            self.Name = name
            self.LongName = f"Character:{name}"

        def ClassName(self):
            return "FBModel"

    components = [Model(name) for name in model_names] + [SimpleNamespace(Name="Material")]
    characters = [SimpleNamespace(LongName="Character:Hero")]
    takes = [SimpleNamespace(Name="Take 001"), SimpleNamespace(Name="Take 002")]
    scene = SimpleNamespace(Components=components, Characters=characters, Takes=takes)
    system = SimpleNamespace(Scene=scene, Version=24000.0, CurrentTake=None)
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: system
    sdk.FBModel = Model
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    namespace = runpy.run_path(str(SCRIPTS / (tool + ".py")))
    result = namespace["main"]()

    assert result["success"] is True, result
    context = result["context"]
    assert context["model_count"] == len(model_names)
    if tool == "list_models":
        assert context["models"] == [
            {"name": name, "long_name": f"Character:{name}", "type": "FBModel"}
            for name in model_names
        ]
    else:
        assert context["component_count"] == len(components)
        assert context["current_take"] is None
        assert context["character_count"] == 1
        assert context["characters"] == ["Character:Hero"]
        assert context["take_count"] == 2
        assert context["takes"] == ["Take 001", "Take 002"]


def test_scene_tools_fall_back_when_legacy_test_doubles_lack_extended_fields(monkeypatch):
    class LegacyModel:
        Name = "Cube"

    scene = SimpleNamespace(Components=[LegacyModel()])
    system = SimpleNamespace(Scene=scene, Version=24000.0, CurrentTake=None)
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: system
    sdk.FBModel = LegacyModel
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    namespace = runpy.run_path(str(SCRIPTS / "list_models.py"))
    result = namespace["main"]()

    assert result["success"] is True
    assert result["context"]["models"] == [
        {"name": "Cube", "long_name": "Cube", "type": "LegacyModel"}
    ]
