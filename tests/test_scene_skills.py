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

    components = [Model(name) for name in model_names] + [SimpleNamespace(Name="Material")]
    scene = SimpleNamespace(Components=components)
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
        assert context["models"] == [{"name": name} for name in model_names]
    else:
        assert context["component_count"] == len(components)
        assert context["current_take"] is None
