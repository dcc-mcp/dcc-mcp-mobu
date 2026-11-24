"""Test typed interchange and animation inspection skills without MotionBuilder."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import yaml
from dcc_mcp_core._server.inprocess_executor import run_skill_script

ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "src" / "dcc_mcp_mobu" / "skills"
INTERCHANGE = SKILLS / "mobu-interchange" / "scripts"
ANIMATION = SKILLS / "mobu-animation" / "scripts"


def run_script(script_path: Path, **params: object) -> dict:
    return run_skill_script(str(script_path), params)


def test_new_skill_declarations_expose_expected_typed_tools() -> None:
    interchange = yaml.safe_load(
        (SKILLS / "mobu-interchange" / "tools.yaml").read_text(encoding="utf-8")
    )
    animation = yaml.safe_load(
        (SKILLS / "mobu-animation" / "tools.yaml").read_text(encoding="utf-8")
    )

    interchange_tools = {tool["name"]: tool for tool in interchange["tools"]}
    animation_tools = {tool["name"]: tool for tool in animation["tools"]}
    assert set(interchange_tools) == {
        "inspect_state",
        "open",
        "merge",
        "append",
        "import",
        "export",
    }
    assert set(animation_tools) == {"list_takes", "inspect_current_take", "list_story"}
    assert all(tool["affinity"] == "main" for tool in interchange_tools.values())
    assert all(tool["affinity"] == "main" for tool in animation_tools.values())
    assert all(tool["read_only"] for tool in animation_tools.values())
    assert all(
        tool.get("readback") == "inspect_state"
        for name, tool in interchange_tools.items()
        if name != "inspect_state"
    )


def test_new_skill_scripts_do_not_expose_raw_script_entrypoints() -> None:
    scripts = [
        *(SKILLS / "mobu-interchange" / "scripts").glob("*.py"),
        *(SKILLS / "mobu-animation" / "scripts").glob("*.py"),
    ]

    assert scripts
    assert all("__main__" not in path.read_text(encoding="utf-8") for path in scripts)


def test_interchange_reports_missing_host_with_stable_error(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "pyfbsdk", raising=False)

    result = run_script(INTERCHANGE / "inspect_state.py")

    assert result["success"] is False
    assert result["error"] == "import_error"
    assert "pyfbsdk" in result["message"]


def test_interchange_validates_absolute_input_paths_before_importing_sdk() -> None:
    result = run_script(
        INTERCHANGE / "open.py",
        path="relative/input.fbx",
        file_type="scene",
    )

    assert result["success"] is False
    assert result["error"] == "invalid_path"


def test_interchange_calls_sdk_and_reads_back_mutated_state(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, object]] = []
    app = _fake_application(calls)
    system = _fake_system()
    sdk = _fake_sdk(app, system)
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)
    source = tmp_path / "incoming.fbx"
    source.write_bytes(b"fbx")

    result = run_script(INTERCHANGE / "open.py", path=str(source), file_type="scene")

    assert result["success"] is True, result
    assert calls == [("FileOpen", (str(source), False))]
    assert result["postcondition"]["verified"] is True
    assert result["context"]["state"]["current_file"] == str(source.absolute())


@pytest.mark.parametrize(
    ("script_name", "method_name"),
    [("merge.py", "FileMerge"), ("append.py", "FileAppend")],
)
def test_interchange_scene_mutations_use_typed_sdk_methods(
    monkeypatch, tmp_path, script_name, method_name
) -> None:
    calls: list[tuple[str, object]] = []
    app = _fake_application(calls)
    monkeypatch.setitem(sys.modules, "pyfbsdk", _fake_sdk(app, _fake_system()))
    source = tmp_path / "incoming.fbx"
    source.write_bytes(b"fbx")

    result = run_script(INTERCHANGE / script_name, path=str(source), file_type="scene")

    assert result["success"] is True, result
    assert calls == [(method_name, (str(source), False))]
    assert result["context"]["state"]["scene"]["component_count"] == 0


def test_interchange_import_and_export_use_explicit_fbx_type(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, object]] = []
    app = _fake_application(calls)
    monkeypatch.setitem(sys.modules, "pyfbsdk", _fake_sdk(app, _fake_system()))
    source = tmp_path / "motion.fbx"
    source.write_bytes(b"fbx")
    target = tmp_path / "exported.fbx"

    imported = run_script(
        INTERCHANGE / "import_motion.py",
        path=str(source),
        file_type="fbx",
        match_models=True,
        create_unmatched_models=False,
    )
    exported = run_script(
        INTERCHANGE / "export_motion.py",
        path=str(target),
        file_type="fbx",
    )

    assert imported["success"] is True, imported
    assert exported["success"] is True, exported
    assert calls == [
        ("FileImport", (str(source), True, False)),
        ("FileExport", (str(target),)),
    ]
    assert target.is_file()


def test_interchange_export_requires_explicit_overwrite(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, object]] = []
    app = _fake_application(calls)
    monkeypatch.setitem(sys.modules, "pyfbsdk", _fake_sdk(app, _fake_system()))
    target = tmp_path / "existing.fbx"
    target.write_bytes(b"old")

    result = run_script(
        INTERCHANGE / "export_motion.py",
        path=str(target),
        file_type="fbx",
    )

    assert result["success"] is False
    assert result["error"] == "output_exists"
    assert calls == []


def test_interchange_reports_sdk_exceptions_with_operation_context(monkeypatch, tmp_path) -> None:
    source = tmp_path / "incoming.fbx"
    source.write_bytes(b"fbx")

    class FailingApplication:
        def FileMerge(self, path: str, show_ui: bool) -> bool:
            raise RuntimeError("merge failed")

    sdk = _fake_sdk(FailingApplication(), _fake_system())
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    result = run_script(INTERCHANGE / "merge.py", path=str(source), file_type="scene")

    assert result["success"] is False
    assert result["error"] == "host_operation_error"
    assert result["context"]["operation"] == "merge"
    assert result["context"]["file_type"] == "scene"


def test_animation_reports_missing_host_with_stable_error(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "pyfbsdk", raising=False)

    result = run_script(ANIMATION / "list_takes.py")

    assert result["success"] is False
    assert result["error"] == "import_error"


def test_animation_lists_takes_current_take_and_story_clips(monkeypatch) -> None:
    current = SimpleNamespace(
        Name="Walk",
        Comments="primary",
        LocalTimeSpan=_time_span(1, 24),
        ReferenceTimeSpan=_time_span(1, 24),
    )
    other = SimpleNamespace(
        Name="Idle",
        Comments="",
        LocalTimeSpan=_time_span(0, 12),
        ReferenceTimeSpan=_time_span(0, 12),
    )
    clip = SimpleNamespace(
        Name="WalkClip",
        Start=_time(1),
        Stop=_time(24),
        SourceMarkIn=_time(0),
        SourceMarkOut=_time(24),
        Loaded=True,
        Loop=False,
        Speed=1.0,
        ConnectedToTake=current,
    )
    track = SimpleNamespace(
        Name="Character Track",
        Label="Character Track",
        Type="Character",
        Mute=False,
        Solo=False,
        Clips=[clip],
        SubTracks=[],
    )
    root = SimpleNamespace(Name="Root", Tracks=[track], Components=[])
    system = SimpleNamespace(
        CurrentTake=current,
        Scene=SimpleNamespace(Takes=[current, other]),
    )
    sdk = ModuleType("pyfbsdk")
    sdk.FBSystem = lambda: system
    sdk.FBStory = lambda: SimpleNamespace(RootFolder=root)
    monkeypatch.setitem(sys.modules, "pyfbsdk", sdk)

    takes = run_script(ANIMATION / "list_takes.py")
    current_take = run_script(ANIMATION / "inspect_current_take.py")
    story = run_script(ANIMATION / "list_story.py")

    assert takes["success"] is True
    assert takes["context"]["current_take"] == "Walk"
    assert [take["name"] for take in takes["context"]["takes"]] == ["Walk", "Idle"]
    assert current_take["context"]["current_take"]["local_time_span"]["start"]["frame"] == 1
    assert story["context"]["track_count"] == 1
    assert story["context"]["tracks"][0]["clips"][0]["name"] == "WalkClip"


def _fake_application(calls: list[tuple[str, object]]) -> object:
    class FakeApplication:
        FBXFileName = ""

        def FileOpen(self, path: str, show_ui: bool) -> bool:
            calls.append(("FileOpen", (path, show_ui)))
            self.FBXFileName = path
            return True

        def FileMerge(self, path: str, show_ui: bool) -> bool:
            calls.append(("FileMerge", (path, show_ui)))
            return True

        def FileAppend(self, path: str, show_ui: bool) -> bool:
            calls.append(("FileAppend", (path, show_ui)))
            return True

        def FileImport(self, path: str, match_models: bool, create_unmatched: bool) -> bool:
            calls.append(("FileImport", (path, match_models, create_unmatched)))
            return True

        def FileExport(self, path: str) -> bool:
            calls.append(("FileExport", (path,)))
            Path(path).write_bytes(b"exported")
            return True

    return FakeApplication()


def _fake_system() -> object:
    class Model:
        pass

    return SimpleNamespace(
        Version="2026.1",
        CurrentTake=None,
        Scene=SimpleNamespace(Components=[], Takes=[]),
        FBModel=Model,
    )


def _fake_sdk(application: object, system: object) -> ModuleType:
    sdk = ModuleType("pyfbsdk")
    sdk.FBApplication = lambda: application
    sdk.FBSystem = lambda: system
    sdk.FBModel = type("FBModel", (), {})
    return sdk


def _time(frame: int) -> object:
    return SimpleNamespace(
        GetFrame=lambda: frame,
        GetSecondDouble=lambda: frame / 24.0,
        GetTimeString=lambda: f"00:00:{frame:02d}",
    )


def _time_span(start: int, stop: int) -> object:
    return SimpleNamespace(Start=_time(start), Stop=_time(stop))
