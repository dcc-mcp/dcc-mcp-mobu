"""Public Install SOP CLI tests for the MotionBuilder adapter."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_install_dry_run_reports_a_non_mutating_schema_v1_plan(tmp_path: Path) -> None:
    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    env = os.environ.copy()
    env["MOTIONBUILDER_PYTHON_STARTUP"] = str(startup)
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dcc_mcp_mobu.install_cli",
            "install",
            "--dcc-path",
            str(host),
            "--python",
            sys.executable,
            "--json",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "planned"
    assert report["dcc_type"] == "mobu"
    assert report["plan"]["host"]["path"] == str(host.resolve())
    assert report["plan"]["python"]["path"] == str(Path(sys.executable).resolve())
    assert report["plan"]["startup_path"] == str(startup.resolve())
    assert report["steps"][0] == {"id": "preflight", "status": "ok"}
    assert report["next_steps"][0]["command"][-2:] == ["--json", "--yes"]
    assert report["verify"] == {
        "directly_usable": False,
        "failure_stage": None,
        "failure_reason": None,
    }
    assert not startup.exists()


def test_explicit_missing_host_and_python_fail_closed_with_machine_next_steps(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )
    env.pop("MOTIONBUILDER_PYTHON_STARTUP", None)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dcc_mcp_mobu.install_cli",
            "status",
            "--dcc-path",
            str(tmp_path / "missing-motionbuilder"),
            "--python",
            str(tmp_path / "missing-mobupy"),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 10
    report = json.loads(completed.stdout)
    assert report["status"] == "failed"
    assert report["steps"][0] == {"id": "preflight", "status": "failed"}
    assert report["failure"] == {
        "stage": "host_preflight",
        "reason": "dcc_path_not_found",
    }
    assert report["next_steps"] == [
        {
            "id": "select_motionbuilder",
            "description": "Select an existing MotionBuilder 2023 or newer executable.",
            "command": ["dcc-mcp-mobu", "status", "--dcc-path", "<absolute-path>", "--json"],
            "why": "The explicit MotionBuilder path does not exist.",
        }
    ]


def test_missing_target_interpreter_never_falls_back_to_path_python(tmp_path: Path) -> None:
    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )
    env["MOTIONBUILDER_PYTHON_STARTUP"] = str(tmp_path / "PythonStartup")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dcc_mcp_mobu.install_cli",
            "verify",
            "--dcc-path",
            str(host),
            "--python",
            str(tmp_path / "missing-mobupy"),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 10
    report = json.loads(completed.stdout)
    assert report["failure"] == {
        "stage": "python_preflight",
        "reason": "python_path_not_found",
    }
    assert report["next_steps"] == [
        {
            "id": "select_target_python",
            "description": "Select MotionBuilder's existing mobupy interpreter.",
            "command": [
                "dcc-mcp-mobu",
                "verify",
                "--dcc-path",
                str(host.resolve()),
                "--python",
                "<absolute-path>",
                "--json",
            ],
            "why": (
                "The explicit target interpreter does not exist; PATH Python is not a safe "
                "fallback."
            ),
        }
    ]


def test_host_root_resolves_its_matching_executable_and_embedded_python(tmp_path: Path) -> None:
    host_root = tmp_path / "MotionBuilder2026"
    binary_dir = host_root / "bin" / "x64"
    binary_dir.mkdir(parents=True)
    host = binary_dir / "motionbuilder.exe"
    host.write_text("synthetic host marker", encoding="utf-8")
    mobupy = binary_dir / "mobupy.exe"
    shutil.copy2(sys.executable, mobupy)
    startup = tmp_path / "PythonStartup"
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )
    env["MOTIONBUILDER_PYTHON_STARTUP"] = str(startup)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dcc_mcp_mobu.install_cli",
            "status",
            "--dcc-path",
            str(host_root),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["plan"]["host"] == {
        "path": str(host.resolve()),
        "root": str(host_root.resolve()),
        "version": "2026",
        "selection_source": "dcc_path",
    }
    assert report["plan"]["python"]["path"] == str(mobupy.resolve())
    assert report["plan"]["python"]["selection_source"] == "host_embedded"


def test_ambiguous_host_root_requires_an_exact_executable_override(tmp_path: Path) -> None:
    host_root = tmp_path / "MotionBuilder2026"
    first = host_root / "bin" / "x64" / "motionbuilder.exe"
    second = host_root / "bin" / "motionbuilder.exe"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True, exist_ok=True)
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dcc_mcp_mobu.install_cli",
            "status",
            "--dcc-path",
            str(host_root),
            "--python",
            sys.executable,
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 10
    report = json.loads(completed.stdout)
    assert report["failure"] == {
        "stage": "host_preflight",
        "reason": "dcc_path_ambiguous",
    }
    assert report["next_steps"][0]["command"] == [
        "dcc-mcp-mobu",
        "status",
        "--dcc-path",
        "<absolute-path>",
        "--json",
    ]


def test_system_discovery_accepts_only_one_verified_host_and_matching_mobupy(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from dcc_mcp_mobu import install_cli

    host_root = tmp_path / "MotionBuilder2026"
    binary_dir = host_root / "bin" / "x64"
    binary_dir.mkdir(parents=True)
    host = binary_dir / "motionbuilder.exe"
    host.write_text("synthetic host marker", encoding="utf-8")
    mobupy = binary_dir / "mobupy.exe"
    shutil.copy2(sys.executable, mobupy)
    monkeypatch.setattr(install_cli, "_system_host_roots", lambda: [host_root])
    monkeypatch.setenv("MOTIONBUILDER_PYTHON_STARTUP", str(tmp_path / "PythonStartup"))

    exit_code = install_cli.main(["status", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["plan"]["host"] == {
        "path": str(host.resolve()),
        "root": str(host_root.resolve()),
        "version": "2026",
        "selection_source": "system_discovery",
    }
    assert report["plan"]["python"]["path"] == str(mobupy.resolve())
    assert report["plan"]["python"]["selection_source"] == "host_embedded"


def test_motionbuilder_before_python_39_generation_fails_version_preflight(tmp_path: Path) -> None:
    host = tmp_path / "MotionBuilder2022"
    host.write_text("synthetic host marker", encoding="utf-8")
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )
    env["MOTIONBUILDER_PYTHON_STARTUP"] = str(tmp_path / "PythonStartup")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "dcc_mcp_mobu.install_cli",
            "install",
            "--dcc-path",
            str(host),
            "--python",
            sys.executable,
            "--json",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 10
    report = json.loads(completed.stdout)
    assert report["failure"] == {
        "stage": "host_preflight",
        "reason": "host_version_below_floor",
    }
    assert report["requirements"]["min_host_version"] == "2023"
    assert report["requirements"]["min_python_version"] == "3.9"


def test_target_core_below_floor_fails_before_writing_startup(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from dcc_mcp_mobu import install_cli

    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    monkeypatch.setenv("MOTIONBUILDER_PYTHON_STARTUP", str(startup))
    monkeypatch.setattr(
        install_cli,
        "_probe_target_python",
        lambda _path: (
            {
                "python_version": "3.11.9",
                "adapter_version": install_cli.__version__,
                "core_version": "0.19.1",
            },
            None,
        ),
    )

    exit_code = install_cli.main(
        [
            "install",
            "--dcc-path",
            str(host),
            "--python",
            sys.executable,
            "--json",
            "--yes",
        ]
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 10
    assert report["failure"] == {
        "stage": "core_preflight",
        "reason": "core_version_below_floor",
    }
    assert not startup.exists()


def test_install_commits_a_receipt_and_status_reports_the_receipted_state(tmp_path: Path) -> None:
    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    registry = tmp_path / "registry"
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )
    env["MOTIONBUILDER_PYTHON_STARTUP"] = str(startup)
    env["DCC_MCP_REGISTRY_DIR"] = str(registry)
    common = [
        "--dcc-path",
        str(host),
        "--python",
        sys.executable,
        "--json",
    ]

    installed = subprocess.run(
        [sys.executable, "-m", "dcc_mcp_mobu.install_cli", "install", *common, "--yes"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert installed.returncode == 40, installed.stderr
    install_report = json.loads(installed.stdout)
    assert install_report["status"] == "partial"
    assert install_report["plan"]["current_state"] == "fresh"
    assert install_report["verify"] == {
        "directly_usable": False,
        "failure_stage": "readiness",
        "failure_reason": "motionbuilder_runtime_not_ready",
    }
    receipt_path = Path(install_report["receipt_path"])
    shim = startup / "dcc_mcp_mobu.py"
    assert receipt_path.is_file()
    assert shim.is_file()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema_version"] == 1
    assert receipt["adapter_version"] == install_report["adapter_version"]
    assert receipt["dcc"] == {
        "type": "mobu",
        "version": "2026",
        "path": str(host.resolve()),
        "startup_path": str(startup.resolve()),
    }
    assert receipt["python"]["path"] == str(Path(sys.executable).resolve())
    assert receipt["owned_files"] == [
        {
            "path": str(shim.resolve()),
            "sha256": hashlib.sha256(shim.read_bytes()).hexdigest(),
        }
    ]

    status = subprocess.run(
        [sys.executable, "-m", "dcc_mcp_mobu.install_cli", "status", *common],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert status.returncode == 0, status.stderr
    status_report = json.loads(status.stdout)
    assert status_report["status"] == "ok"
    assert status_report["plan"]["current_state"] == "current"
    assert status_report["receipt_path"] == str(receipt_path)


def test_second_identical_install_converges_without_rewriting_receipted_files(
    tmp_path: Path,
) -> None:
    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )
    env["MOTIONBUILDER_PYTHON_STARTUP"] = str(startup)
    env["DCC_MCP_REGISTRY_DIR"] = str(tmp_path / "registry")
    command = [
        sys.executable,
        "-m",
        "dcc_mcp_mobu.install_cli",
        "install",
        "--dcc-path",
        str(host),
        "--python",
        sys.executable,
        "--json",
        "--yes",
    ]
    first = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert first.returncode == 40
    receipt = Path(json.loads(first.stdout)["receipt_path"])
    shim = startup / "dcc_mcp_mobu.py"
    before = (shim.read_bytes(), receipt.read_bytes())

    second = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert second.returncode == 40
    assert json.loads(second.stdout)["plan"]["current_state"] == "current"
    assert (shim.read_bytes(), receipt.read_bytes()) == before


def test_uninstall_is_receipt_driven_preserves_user_files_and_is_idempotent(tmp_path: Path) -> None:
    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )
    env["MOTIONBUILDER_PYTHON_STARTUP"] = str(startup)
    env["DCC_MCP_REGISTRY_DIR"] = str(tmp_path / "registry")
    common = ["--dcc-path", str(host), "--python", sys.executable, "--json"]
    install = subprocess.run(
        [sys.executable, "-m", "dcc_mcp_mobu.install_cli", "install", *common, "--yes"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert install.returncode == 40
    receipt = Path(json.loads(install.stdout)["receipt_path"])
    shim = startup / "dcc_mcp_mobu.py"
    user_file = startup / "studio_startup.py"
    user_file.write_text("# user owned\n", encoding="utf-8")

    dry_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "dcc_mcp_mobu.install_cli",
            "uninstall",
            *common,
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert dry_run.returncode == 0
    assert shim.is_file() and receipt.is_file()

    removed = subprocess.run(
        [sys.executable, "-m", "dcc_mcp_mobu.install_cli", "uninstall", *common, "--yes"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert removed.returncode == 0, removed.stderr
    removed_report = json.loads(removed.stdout)
    assert removed_report["status"] == "ok"
    assert removed_report["steps"][-1] == {"id": "uninstall", "status": "ok"}
    assert not shim.exists()
    assert not receipt.exists()
    assert user_file.read_text(encoding="utf-8") == "# user owned\n"

    repeated = subprocess.run(
        [sys.executable, "-m", "dcc_mcp_mobu.install_cli", "uninstall", *common, "--yes"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert repeated.returncode == 0
    assert json.loads(repeated.stdout)["plan"]["current_state"] == "fresh"


def test_unreceipted_file_is_refused_but_receipted_missing_file_is_repaired(tmp_path: Path) -> None:
    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    startup.mkdir()
    shim = startup / "dcc_mcp_mobu.py"
    shim.write_text("# user-owned collision\n", encoding="utf-8")
    env = os.environ.copy()
    source_root = Path(__file__).parents[1] / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(source_root), env.get("PYTHONPATH")) if value
    )
    env["MOTIONBUILDER_PYTHON_STARTUP"] = str(startup)
    env["DCC_MCP_REGISTRY_DIR"] = str(tmp_path / "registry")
    command = [
        sys.executable,
        "-m",
        "dcc_mcp_mobu.install_cli",
        "install",
        "--dcc-path",
        str(host),
        "--python",
        sys.executable,
        "--json",
        "--yes",
    ]

    refused = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert refused.returncode == 10
    assert json.loads(refused.stdout)["plan"]["current_state"] == "partial"
    assert shim.read_text(encoding="utf-8") == "# user-owned collision\n"

    shim.unlink()
    installed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert installed.returncode == 40
    receipt = Path(json.loads(installed.stdout)["receipt_path"])
    assert receipt.is_file()
    shim.unlink()

    repaired = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert repaired.returncode == 40
    repaired_report = json.loads(repaired.stdout)
    assert repaired_report["plan"]["current_state"] == "repair"
    assert shim.is_file() and receipt.is_file()


def test_verify_requires_a_live_instance_and_successful_typed_ping(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from dcc_mcp_mobu import install_cli

    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    monkeypatch.setenv("MOTIONBUILDER_PYTHON_STARTUP", str(startup))
    monkeypatch.setenv("DCC_MCP_REGISTRY_DIR", str(tmp_path / "registry"))
    common = ["--dcc-path", str(host), "--python", sys.executable, "--json"]
    assert install_cli.main(["install", *common, "--yes"]) == 40
    capsys.readouterr()

    live_entry = {
        "instance_id": "00000000-0000-4000-8000-000000000006",
        "runtime_alive": True,
        "mcp_url": "http://127.0.0.1:46006/mcp",
    }
    monkeypatch.setattr(install_cli, "_live_runtime_entries", lambda: [live_entry])
    monkeypatch.setattr(install_cli, "_run_typed_ping", lambda _entry: False)

    failed = install_cli.main(["verify", *common])
    failed_report = json.loads(capsys.readouterr().out)
    assert failed == 40
    assert failed_report["verify"] == {
        "directly_usable": False,
        "failure_stage": "typed_ping",
        "failure_reason": "mobu_diagnostics_ping_failed",
    }

    monkeypatch.setattr(install_cli, "_run_typed_ping", lambda _entry: True)
    ready = install_cli.main(["verify", *common])
    ready_report = json.loads(capsys.readouterr().out)
    assert ready == 0
    assert ready_report["verify"]["directly_usable"] is True
    assert ready_report["readiness"] == {
        "instance_id": live_entry["instance_id"],
        "probe_tool": "mobu_diagnostics__ping",
        "typed_ping": "ready",
    }


def test_upgrade_receipt_commit_failure_restores_the_previous_install(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from dcc_mcp_mobu import install_cli

    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    monkeypatch.setenv("MOTIONBUILDER_PYTHON_STARTUP", str(startup))
    monkeypatch.setenv("DCC_MCP_REGISTRY_DIR", str(tmp_path / "registry"))
    common = ["--dcc-path", str(host), "--python", sys.executable, "--json"]
    assert install_cli.main(["install", *common, "--yes"]) == 40
    install_report = json.loads(capsys.readouterr().out)
    receipt = Path(install_report["receipt_path"])
    shim = startup / "dcc_mcp_mobu.py"
    prior = json.loads(receipt.read_text(encoding="utf-8"))
    prior["adapter_version"] = "0.2.0"
    receipt.write_text(json.dumps(prior, indent=2) + "\n", encoding="utf-8")
    previous_shim = shim.read_bytes()
    previous_receipt = receipt.read_bytes()
    original_write_text = Path.write_text

    def fail_staged_receipt(path, *args, **kwargs):
        if path.name == receipt.name and path.parent.name.startswith(".dcc-mcp-mobu-stage-"):
            raise OSError("synthetic receipt commit failure")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_staged_receipt)

    exit_code = install_cli.main(["upgrade", *common, "--yes"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 30
    assert report["failure"] == {"stage": "install", "reason": "transaction_failed"}
    assert shim.read_bytes() == previous_shim
    assert receipt.read_bytes() == previous_receipt


def test_real_lock_evidence_defers_upgrade_with_exit_50(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from dcc_mcp_mobu import install_cli

    host = tmp_path / "MotionBuilder2026"
    host.write_text("synthetic host marker", encoding="utf-8")
    startup = tmp_path / "PythonStartup"
    monkeypatch.setenv("MOTIONBUILDER_PYTHON_STARTUP", str(startup))
    monkeypatch.setenv("DCC_MCP_REGISTRY_DIR", str(tmp_path / "registry"))
    common = ["--dcc-path", str(host), "--python", sys.executable, "--json"]
    assert install_cli.main(["install", *common, "--yes"]) == 40
    install_report = json.loads(capsys.readouterr().out)
    receipt = Path(install_report["receipt_path"])
    shim = startup / "dcc_mcp_mobu.py"
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    receipt_payload["adapter_version"] = "0.2.0"
    receipt.write_text(json.dumps(receipt_payload, indent=2) + "\n", encoding="utf-8")
    before = (shim.read_bytes(), receipt.read_bytes())
    lock = {
        "status": "requires_restart",
        "requires_restart": True,
        "reason": "windows_file_lock",
        "locked_path": str(shim),
    }
    monkeypatch.setattr(install_cli, "_inspect_lock", lambda _path: lock)

    exit_code = install_cli.main(["upgrade", *common, "--yes"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 50
    assert report["status"] == "requires_restart"
    assert report["failure"] == {"stage": "lock_preflight", "reason": "windows_file_lock"}
    assert report["lock"] == lock
    assert (shim.read_bytes(), receipt.read_bytes()) == before
