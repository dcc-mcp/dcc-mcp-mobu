"""Import-light MotionBuilder adapter install lifecycle CLI.

The schema and exit constants mirror Core PR #2320 until that public surface is
available in a released ``dcc-mcp-core`` wheel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Optional

from .__version__ import __version__

SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_PREFLIGHT = 10
EXIT_ACQUIRE = 20
EXIT_INSTALL = 30
EXIT_VERIFY = 40
EXIT_REQUIRES_RESTART = 50
MIN_CORE_VERSION = "0.19.45"
MIN_HOST_VERSION = 2023
MIN_PYTHON_VERSION = "3.9"

_HOST_RELATIVE_CANDIDATES = (
    Path("bin/x64/motionbuilder.exe"),
    Path("bin/motionbuilder.exe"),
    Path("bin/x64/motionbuilder"),
    Path("bin/motionbuilder"),
    Path("MotionBuilder.app/Contents/MacOS/MotionBuilder"),
)
_PYTHON_RELATIVE_CANDIDATES = (
    Path("bin/x64/mobupy.exe"),
    Path("bin/mobupy.exe"),
    Path("bin/x64/mobupy"),
    Path("bin/mobupy"),
)


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _version_at_least(value: object, minimum: str) -> bool:
    def parts(item: object) -> tuple[int, ...]:
        match = re.search(r"\d+(?:\.\d+)+", str(item or ""))
        return tuple(int(part) for part in match.group(0).split(".")) if match else ()

    current = parts(value)
    floor = parts(minimum)
    width = max(len(current), len(floor))
    return bool(current) and current + (0,) * (width - len(current)) >= floor + (0,) * (
        width - len(floor)
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_receipt(path: Optional[Path]) -> tuple[Optional[dict[str, Any]], bool]:
    if path is None or not path.is_file():
        return None, False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, True
    return (payload, False) if isinstance(payload, dict) else (None, True)


def _installation_state(
    shim: Optional[Path],
    receipt_path: Optional[Path],
    desired_digest: str,
) -> tuple[str, Optional[dict[str, Any]]]:
    receipt, malformed = _read_receipt(receipt_path)
    shim_exists = bool(shim and shim.is_file())
    if malformed or (shim_exists and receipt is None):
        return "partial", receipt
    if receipt is None:
        return "fresh", None
    if receipt.get("schema_version") != 1 or receipt.get("dcc", {}).get("type") != "mobu":
        return "partial", receipt
    if not shim_exists:
        return "repair", receipt
    owned = receipt.get("owned_files") or []
    recorded_path = owned[0].get("path") if len(owned) == 1 and isinstance(owned[0], dict) else None
    if recorded_path != str(shim):
        return "partial", receipt
    recorded = owned[0].get("sha256") if len(owned) == 1 and isinstance(owned[0], dict) else None
    actual = _sha256(shim) if shim else None
    if recorded != actual or actual != desired_digest:
        return "repair", receipt
    if receipt.get("adapter_version") != __version__:
        return "upgrade", receipt
    return "current", receipt


def _probe_target_python(
    python_path: Path,
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    script = (
        "import json,sys; from importlib.metadata import version; "
        "import dcc_mcp_mobu; "
        "print(json.dumps({'python_version': '.'.join(map(str,sys.version_info[:3])), "
        "'adapter_version': dcc_mcp_mobu.__version__, "
        "'core_version': version('dcc-mcp-core')}))"
    )
    try:
        completed = subprocess.run(
            [str(python_path), "-c", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "target_python_unusable"
    if completed.returncode != 0:
        return None, "adapter_import_failed"
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        return None, "target_python_invalid_output"
    if payload.get("adapter_version") != __version__:
        return payload, "adapter_version_mismatch"
    version_match = re.match(r"(\d+)\.(\d+)", str(payload.get("python_version") or ""))
    if not version_match or tuple(map(int, version_match.groups())) < (3, 9):
        return payload, "python_version_below_floor"
    return payload, None


def _inspect_lock(path: Path) -> dict[str, Any]:
    try:
        from dcc_mcp_core.deployment import inspect_install_root
    except ImportError:
        try:
            from dcc_mcp_core.install_lifecycle import inspect_install_root
        except ImportError:
            return {"requires_restart": False}
    try:
        return inspect_install_root(path)
    except Exception:
        return {"requires_restart": False}


def _receipt_payload(
    *,
    host: Path,
    host_version: str,
    startup: Path,
    python_path: Path,
    python_probe: dict[str, Any],
    shim: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "adapter_version": __version__,
        "core_version": str(python_probe["core_version"]),
        "dcc": {
            "type": "mobu",
            "version": host_version,
            "path": str(host),
            "startup_path": str(startup),
        },
        "python": {
            "path": str(python_path),
            "version": str(python_probe["python_version"]),
        },
        "owned_files": [{"path": str(shim), "sha256": _sha256(shim)}],
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }


def _commit_install(
    *,
    startup: Path,
    shim: Path,
    receipt_path: Path,
    host: Path,
    host_version: str,
    python_path: Path,
    python_probe: dict[str, Any],
) -> tuple[bool, Optional[dict[str, Any]]]:
    payload_source = Path(__file__).resolve().parent / "mobu_plugin" / "startup" / "dcc_mcp_mobu.py"
    startup.parent.mkdir(parents=True, exist_ok=True)
    transaction = Path(tempfile.mkdtemp(prefix=".dcc-mcp-mobu-stage-", dir=str(startup.parent)))
    staged_shim = transaction / shim.name
    staged_receipt = transaction / receipt_path.name
    backup_shim = transaction / "previous-shim.py"
    backup_receipt = transaction / "previous-receipt.json"
    moved_shim = False
    moved_receipt = False
    try:
        shutil.copy2(payload_source, staged_shim)
        startup.mkdir(parents=True, exist_ok=True)
        if shim.exists():
            os.replace(shim, backup_shim)
            moved_shim = True
        if receipt_path.exists():
            os.replace(receipt_path, backup_receipt)
            moved_receipt = True
        os.replace(staged_shim, shim)
        payload = _receipt_payload(
            host=host,
            host_version=host_version,
            startup=startup,
            python_path=python_path,
            python_probe=python_probe,
            shim=shim,
        )
        staged_receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(staged_receipt, receipt_path)
        return True, None
    except PermissionError as error:
        if shim.exists():
            shim.unlink(missing_ok=True)
        if receipt_path.exists():
            receipt_path.unlink(missing_ok=True)
        if moved_shim and backup_shim.exists():
            os.replace(backup_shim, shim)
        if moved_receipt and backup_receipt.exists():
            os.replace(backup_receipt, receipt_path)
        return False, {
            "reason": "windows_file_lock" if os.name == "nt" else "permission_denied",
            "path": str(getattr(error, "filename", None) or shim),
        }
    except Exception as error:
        if shim.exists():
            shim.unlink(missing_ok=True)
        if receipt_path.exists():
            receipt_path.unlink(missing_ok=True)
        if moved_shim and backup_shim.exists():
            os.replace(backup_shim, shim)
        if moved_receipt and backup_receipt.exists():
            os.replace(backup_receipt, receipt_path)
        return False, {"reason": "transaction_failed", "error_type": type(error).__name__}
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def _live_runtime_entries() -> list[dict[str, Any]]:
    try:
        from dcc_mcp_core.deployment import query_runtime_state
    except ImportError:
        try:
            from dcc_mcp_core.install_lifecycle import query_runtime_state
        except ImportError:
            return []
    try:
        state = query_runtime_state(dcc_type="mobu", include_dead=False)
    except Exception:
        return []
    entries = state.get("entries") or []
    return [
        entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("runtime_alive") and entry.get("mcp_url")
    ]


def _run_typed_ping(entry: dict[str, Any]) -> bool:
    cli = shutil.which("dcc-mcp-cli")
    instance_id = str(entry.get("instance_id") or "")
    if not cli or not instance_id:
        return False
    try:
        completed = subprocess.run(
            [
                cli,
                "call",
                "mobu_diagnostics__ping",
                "--dcc-type",
                "mobu",
                "--instance-id",
                instance_id,
                "--json",
                "{}",
                "--output",
                "json",
                "--non-interactive",
                "--timeout-secs",
                "10",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if completed.returncode != 0:
        return False
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        return False
    return payload.get("success") is not False


def _runtime_readiness() -> tuple[bool, Optional[str], Optional[dict[str, Any]]]:
    entries = _live_runtime_entries()
    if not entries:
        return False, "motionbuilder_runtime_not_ready", None
    if len(entries) != 1:
        return False, "motionbuilder_runtime_ambiguous", {"instance_count": len(entries)}
    entry = entries[0]
    evidence = {
        "instance_id": str(entry.get("instance_id")),
        "probe_tool": "mobu_diagnostics__ping",
        "typed_ping": "ready" if _run_typed_ping(entry) else "failed",
    }
    if evidence["typed_ping"] != "ready":
        return False, "mobu_diagnostics_ping_failed", evidence
    return True, None, evidence


def _commit_uninstall(shim: Path, receipt_path: Path) -> tuple[bool, Optional[dict[str, Any]]]:
    transaction = Path(
        tempfile.mkdtemp(prefix=".dcc-mcp-mobu-remove-", dir=str(receipt_path.parent.parent))
    )
    backup_shim = transaction / shim.name
    backup_receipt = transaction / receipt_path.name
    moved_shim = False
    moved_receipt = False
    try:
        if shim.exists():
            os.replace(shim, backup_shim)
            moved_shim = True
        if receipt_path.exists():
            os.replace(receipt_path, backup_receipt)
            moved_receipt = True
        return True, None
    except PermissionError as error:
        if moved_shim and backup_shim.exists():
            os.replace(backup_shim, shim)
        if moved_receipt and backup_receipt.exists():
            os.replace(backup_receipt, receipt_path)
        return False, {
            "reason": "windows_file_lock" if os.name == "nt" else "permission_denied",
            "path": str(getattr(error, "filename", None) or shim),
        }
    except Exception as error:
        if moved_shim and backup_shim.exists():
            os.replace(backup_shim, shim)
        if moved_receipt and backup_receipt.exists():
            os.replace(backup_receipt, receipt_path)
        return False, {"reason": "transaction_failed", "error_type": type(error).__name__}
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dcc-mcp-mobu")
    parser.add_argument("verb", choices=("install", "status", "verify", "uninstall", "upgrade"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dcc-path")
    parser.add_argument("--python", dest="python_path")
    return parser


def _resolve_explicit_host(
    value: Optional[str],
) -> tuple[Optional[Path], Optional[Path]]:
    if not value:
        return None, None
    selected = Path(value).expanduser().resolve()
    if selected.is_file():
        if selected.parent.name.lower() == "x64" and selected.parent.parent.name.lower() == "bin":
            root = selected.parents[2]
        elif selected.parent.name.lower() == "bin":
            root = selected.parents[1]
        else:
            root = selected.parent
        return selected, root
    if selected.is_dir():
        candidates = [selected / relative for relative in _HOST_RELATIVE_CANDIDATES]
        matches = [candidate.resolve() for candidate in candidates if candidate.is_file()]
        if len(matches) == 1:
            return matches[0], selected
    return None, selected


def _explicit_host_failure(value: Optional[str]) -> str:
    if not value:
        return "dcc_path_not_found"
    selected = Path(value).expanduser().resolve()
    if selected.is_dir():
        matches = [selected / relative for relative in _HOST_RELATIVE_CANDIDATES]
        if sum(candidate.is_file() for candidate in matches) > 1:
            return "dcc_path_ambiguous"
    return "dcc_path_not_found"


def _system_host_roots() -> list[Path]:
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles")
        if not program_files:
            return []
        autodesk = Path(program_files) / "Autodesk"
        return sorted(path for path in autodesk.glob("MotionBuilder*") if path.is_dir())
    if sys.platform.startswith("linux"):
        return sorted(
            path for path in Path("/usr/autodesk").glob("MotionBuilder*") if path.is_dir()
        )
    if sys.platform == "darwin":
        return sorted(
            path for path in Path("/Applications/Autodesk").glob("MotionBuilder*") if path.is_dir()
        )
    return []


def _discover_system_host() -> tuple[Optional[Path], Optional[Path], str]:
    matches: list[tuple[Path, Path]] = []
    for root in _system_host_roots():
        candidates = [root / relative for relative in _HOST_RELATIVE_CANDIDATES]
        matches.extend(
            (candidate.resolve(), root.resolve()) for candidate in candidates if candidate.is_file()
        )
    if len(matches) == 1:
        return matches[0][0], matches[0][1], "system_discovery"
    return None, None, "system_discovery_ambiguous" if matches else "system_discovery_missing"


def _resolve_python(
    explicit: Optional[str],
    host_root: Optional[Path],
) -> tuple[Optional[Path], str]:
    if explicit:
        return Path(explicit).expanduser().resolve(), "python_flag"
    configured = os.environ.get("DCC_MCP_INSTALL_PYTHON")
    if configured:
        return Path(configured).expanduser().resolve(), "environment"
    if host_root is not None:
        matches = [
            (host_root / relative).resolve()
            for relative in _PYTHON_RELATIVE_CANDIDATES
            if (host_root / relative).is_file()
        ]
        if len(matches) == 1:
            return matches[0], "host_embedded"
    return None, "unresolved"


def _plan(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.dcc_path:
        host, host_root = _resolve_explicit_host(args.dcc_path)
        host_source = "dcc_path"
        host_resolution_failure = _explicit_host_failure(args.dcc_path) if host is None else None
    else:
        host, host_root, host_source = _discover_system_host()
        host_resolution_failure = host_source if host is None else None
    python_path, python_source = _resolve_python(args.python_path, host_root)
    version_match = re.search(
        r"(?<!\d)(20\d{2})(?!\d)",
        "%s %s" % (host or "", host_root or ""),
    )
    host_version = version_match.group(1) if version_match else None
    startup_value = os.environ.get("MOTIONBUILDER_PYTHON_STARTUP")
    startup = Path(startup_value).expanduser().resolve() if startup_value else None
    receipt = startup / ".dcc-mcp-mobu.receipt.json" if startup else None
    shim = startup / "dcc_mcp_mobu.py" if startup else None
    payload_source = Path(__file__).resolve().parent / "mobu_plugin" / "startup" / "dcc_mcp_mobu.py"
    desired_digest = _sha256(payload_source)
    current_state, _ = _installation_state(shim, receipt, desired_digest)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "planned",
        "dcc_type": "mobu",
        "adapter_version": __version__,
        "core_version": _package_version("dcc-mcp-core"),
        "requirements": {
            "min_core_version": MIN_CORE_VERSION,
            "min_host_version": str(MIN_HOST_VERSION),
            "min_python_version": MIN_PYTHON_VERSION,
        },
        "exit_codes": {
            "ok": EXIT_OK,
            "preflight": EXIT_PREFLIGHT,
            "acquire": EXIT_ACQUIRE,
            "install": EXIT_INSTALL,
            "verify": EXIT_VERIFY,
            "requires_restart": EXIT_REQUIRES_RESTART,
        },
        "steps": [
            {"id": "preflight", "status": "ok"},
            {"id": "install", "status": "planned"},
            {"id": "verify", "status": "planned"},
        ],
        "next_steps": [
            {
                "id": "execute",
                "description": "Execute the validated MotionBuilder install plan.",
                "command": [
                    "dcc-mcp-mobu",
                    args.verb,
                    "--dcc-path",
                    str(host) if host else "<required-host-path>",
                    "--python",
                    str(python_path) if python_path else "<required-target-python>",
                    "--json",
                    "--yes",
                ],
                "why": "Planning and dry-run modes do not modify the host profile.",
            }
        ],
        "receipt_path": str(receipt) if receipt else None,
        "verify": {
            "directly_usable": False,
            "failure_stage": None,
            "failure_reason": None,
        },
        "plan": {
            "host": {
                "path": str(host) if host else None,
                "root": str(host_root) if host_root else None,
                "version": host_version,
                "selection_source": host_source,
            },
            "python": {
                "path": str(python_path) if python_path else None,
                "selection_source": python_source,
            },
            "startup_path": str(startup) if startup else None,
            "current_state": current_state,
        },
    }
    if host is None:
        host_failure = host_resolution_failure or "system_discovery_missing"
        report.update(
            {
                "status": "failed",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {"stage": "host_preflight", "reason": host_failure},
                "next_steps": [
                    {
                        "id": "select_motionbuilder",
                        "description": "Select an existing MotionBuilder 2023 or newer executable.",
                        "command": [
                            "dcc-mcp-mobu",
                            args.verb,
                            "--dcc-path",
                            "<absolute-path>",
                            "--json",
                        ],
                        "why": (
                            "The discovered roots contain multiple host executables."
                            if "ambiguous" in host_failure
                            else "The explicit MotionBuilder path does not exist."
                        ),
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT
    if host_version is not None and int(host_version) < MIN_HOST_VERSION:
        report.update(
            {
                "status": "failed",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {
                    "stage": "host_preflight",
                    "reason": "host_version_below_floor",
                },
                "next_steps": [
                    {
                        "id": "select_supported_motionbuilder",
                        "description": "Select MotionBuilder 2023 or newer.",
                        "command": [
                            "dcc-mcp-mobu",
                            args.verb,
                            "--dcc-path",
                            "<motionbuilder-2023-or-newer>",
                            "--json",
                        ],
                        "why": "MotionBuilder 2022 embeds Python 3.7, below this package's floor.",
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT
    if args.python_path and (python_path is None or not python_path.is_file()):
        report.update(
            {
                "status": "failed",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {"stage": "python_preflight", "reason": "python_path_not_found"},
                "next_steps": [
                    {
                        "id": "select_target_python",
                        "description": "Select MotionBuilder's existing mobupy interpreter.",
                        "command": [
                            "dcc-mcp-mobu",
                            args.verb,
                            "--dcc-path",
                            str(host),
                            "--python",
                            "<absolute-path>",
                            "--json",
                        ],
                        "why": (
                            "The explicit target interpreter does not exist; PATH Python is not "
                            "a safe fallback."
                        ),
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT
    if python_path is None or not python_path.is_file():
        report.update(
            {
                "status": "failed",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {"stage": "python_preflight", "reason": "python_unresolved"},
                "next_steps": [
                    {
                        "id": "select_target_python",
                        "description": "Select MotionBuilder's exact mobupy interpreter.",
                        "command": [
                            "dcc-mcp-mobu",
                            args.verb,
                            "--dcc-path",
                            str(host),
                            "--python",
                            "<absolute-mobupy-path>",
                            "--json",
                        ],
                        "why": "No unique embedded interpreter was found for the selected host.",
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT
    if host_version is None:
        report.update(
            {
                "status": "failed",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {"stage": "host_preflight", "reason": "host_version_unknown"},
                "next_steps": [
                    {
                        "id": "select_versioned_motionbuilder",
                        "description": "Select an exact versioned MotionBuilder executable.",
                        "command": [
                            "dcc-mcp-mobu",
                            args.verb,
                            "--dcc-path",
                            "<versioned-motionbuilder-path>",
                            "--python",
                            str(python_path),
                            "--json",
                        ],
                        "why": "The host version could not be proven from the selected path.",
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT
    if startup is None:
        report.update(
            {
                "status": "failed",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {"stage": "profile_preflight", "reason": "startup_path_unresolved"},
                "next_steps": [
                    {
                        "id": "configure_python_startup",
                        "description": (
                            "Configure one exact MotionBuilder Python Startup directory."
                        ),
                        "command": [
                            "env",
                            "MOTIONBUILDER_PYTHON_STARTUP=<absolute-startup-directory>",
                            "dcc-mcp-mobu",
                            args.verb,
                            "--dcc-path",
                            str(host),
                            "--python",
                            str(python_path),
                            "--json",
                        ],
                        "why": (
                            "The installer will not guess a host profile or modify a factory "
                            "directory."
                        ),
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT

    python_probe, python_failure = _probe_target_python(python_path)
    if python_failure:
        report.update(
            {
                "status": "failed",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {"stage": "python_preflight", "reason": python_failure},
                "next_steps": [
                    {
                        "id": "install_into_target_python",
                        "description": (
                            "Install this exact adapter into the selected target interpreter."
                        ),
                        "command": [
                            str(python_path),
                            "-m",
                            "pip",
                            "install",
                            "dcc-mcp-mobu==%s" % __version__,
                        ],
                        "why": (
                            "MotionBuilder can import only packages installed in its target "
                            "interpreter."
                        ),
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT
    if not _version_at_least(python_probe.get("core_version"), MIN_CORE_VERSION):
        report.update(
            {
                "status": "failed",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {"stage": "core_preflight", "reason": "core_version_below_floor"},
                "next_steps": [
                    {
                        "id": "upgrade_target_core",
                        "description": "Upgrade Core in the selected MotionBuilder interpreter.",
                        "command": [
                            str(python_path),
                            "-m",
                            "pip",
                            "install",
                            "--upgrade",
                            "dcc-mcp-core>=%s,<1.0.0" % MIN_CORE_VERSION,
                        ],
                        "why": "The target interpreter must satisfy the adapter's Core floor.",
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT
    report["plan"]["python"].update(
        {
            "version": python_probe["python_version"],
            "adapter_version": python_probe["adapter_version"],
            "core_version": python_probe["core_version"],
        }
    )
    report["core_version"] = python_probe["core_version"]

    if args.verb == "status":
        status_next_steps = []
        if current_state == "partial":
            status_next_steps = [
                {
                    "id": "inspect_partial_install",
                    "description": "Inspect the startup hook and receipt ownership evidence.",
                    "command": [
                        "dcc-mcp-mobu",
                        "install",
                        "--dcc-path",
                        str(host),
                        "--python",
                        str(python_path),
                        "--json",
                        "--dry-run",
                    ],
                    "why": "Status found an unreceipted or invalid ownership state.",
                }
            ]
        report.update(
            {
                "status": "ok" if current_state != "partial" else "partial",
                "steps": [
                    {"id": "preflight", "status": "ok"},
                    {"id": "status", "status": current_state},
                ],
                "next_steps": status_next_steps,
            }
        )
        return report, EXIT_OK if current_state != "partial" else EXIT_PREFLIGHT

    if current_state == "partial":
        report.update(
            {
                "status": "partial",
                "steps": [{"id": "preflight", "status": "failed"}],
                "failure": {"stage": "install_state", "reason": "unreceipted_or_invalid_state"},
                "next_steps": [
                    {
                        "id": "inspect_partial_install",
                        "description": "Inspect the unreceipted startup file before changing it.",
                        "file_edit": {"path": str(shim), "action": "update"},
                        "why": "The installer never overwrites an unknown user-owned startup file.",
                    }
                ],
            }
        )
        return report, EXIT_PREFLIGHT

    if args.verb == "uninstall":
        if args.dry_run or not args.yes:
            report["steps"] = [
                {"id": "preflight", "status": "ok"},
                {"id": "uninstall", "status": "planned"},
            ]
            return report, EXIT_OK
        if current_state == "fresh":
            report.update(
                {
                    "status": "ok",
                    "steps": [
                        {"id": "preflight", "status": "ok"},
                        {"id": "uninstall", "status": "already_absent"},
                    ],
                    "next_steps": [],
                }
            )
            return report, EXIT_OK
        receipt_payload, malformed = _read_receipt(receipt)
        owned_files = receipt_payload.get("owned_files") if receipt_payload else None
        owned_path = (
            owned_files[0].get("path")
            if isinstance(owned_files, list)
            and len(owned_files) == 1
            and isinstance(owned_files[0], dict)
            else None
        )
        if malformed or owned_path != str(shim):
            report.update(
                {
                    "status": "partial",
                    "steps": [{"id": "uninstall", "status": "failed"}],
                    "failure": {"stage": "receipt", "reason": "receipt_ownership_invalid"},
                    "next_steps": [
                        {
                            "id": "inspect_receipt",
                            "description": "Inspect the invalid receipt before removing any file.",
                            "command": [
                                "dcc-mcp-mobu",
                                "status",
                                "--dcc-path",
                                str(host),
                                "--python",
                                str(python_path),
                                "--json",
                            ],
                            "why": "Uninstall may remove only paths proven by a valid receipt.",
                        }
                    ],
                }
            )
            return report, EXIT_PREFLIGHT
        lock = _inspect_lock(startup)
        if lock.get("requires_restart"):
            report.update(
                {
                    "status": "requires_restart",
                    "steps": [{"id": "uninstall", "status": "requires_restart"}],
                    "failure": {"stage": "lock_preflight", "reason": "windows_file_lock"},
                    "next_steps": [
                        {
                            "id": "retry_after_restart",
                            "description": (
                                "Close the locking MotionBuilder process and retry uninstall."
                            ),
                            "command": [
                                "dcc-mcp-mobu",
                                "uninstall",
                                "--dcc-path",
                                str(host),
                                "--python",
                                str(python_path),
                                "--json",
                                "--yes",
                            ],
                            "why": "Core reported real loaded-file evidence requiring restart.",
                        }
                    ],
                    "lock": lock,
                }
            )
            return report, EXIT_REQUIRES_RESTART
        removed, error = _commit_uninstall(shim, receipt)
        if not removed:
            requires_restart = bool(error and error.get("reason") == "windows_file_lock")
            report.update(
                {
                    "status": "requires_restart" if requires_restart else "failed",
                    "steps": [{"id": "uninstall", "status": "failed"}],
                    "failure": {
                        "stage": "uninstall",
                        "reason": error.get("reason") if error else "transaction_failed",
                    },
                    "next_steps": [
                        {
                            "id": "retry_uninstall",
                            "description": (
                                "Retry the receipt-driven uninstall after resolving the error."
                            ),
                            "command": [
                                "dcc-mcp-mobu",
                                "uninstall",
                                "--dcc-path",
                                str(host),
                                "--python",
                                str(python_path),
                                "--json",
                                "--yes",
                            ],
                            "why": (
                                "The previous installation was restored after the failed "
                                "transaction."
                            ),
                        }
                    ],
                }
            )
            return report, EXIT_REQUIRES_RESTART if requires_restart else EXIT_INSTALL
        report.update(
            {
                "status": "ok",
                "steps": [
                    {"id": "preflight", "status": "ok"},
                    {"id": "uninstall", "status": "ok"},
                ],
                "next_steps": [],
            }
        )
        return report, EXIT_OK

    if args.verb == "verify":
        if current_state not in {"current", "upgrade"}:
            report.update(
                {
                    "status": "failed",
                    "steps": [{"id": "verify", "status": "failed"}],
                    "verify": {
                        "directly_usable": False,
                        "failure_stage": "receipt",
                        "failure_reason": "installed_receipt_not_current",
                    },
                    "next_steps": [
                        {
                            "id": "repair_install",
                            "description": "Repair the receipted MotionBuilder startup hook.",
                            "command": [
                                "dcc-mcp-mobu",
                                "install",
                                "--dcc-path",
                                str(host),
                                "--python",
                                str(python_path),
                                "--json",
                                "--yes",
                            ],
                            "why": (
                                "Verification requires a current receipt and matching owned file."
                            ),
                        }
                    ],
                }
            )
            return report, EXIT_VERIFY
        ready, readiness_failure, readiness_evidence = _runtime_readiness()
        if not ready:
            failure_stage = (
                "typed_ping" if readiness_failure == "mobu_diagnostics_ping_failed" else "readiness"
            )
            if readiness_failure == "mobu_diagnostics_ping_failed" and readiness_evidence:
                readiness_next_step = {
                    "id": "run_typed_ping",
                    "description": "Run the typed MotionBuilder readiness probe directly.",
                    "command": [
                        "dcc-mcp-cli",
                        "call",
                        "mobu_diagnostics__ping",
                        "--dcc-type",
                        "mobu",
                        "--instance-id",
                        str(readiness_evidence["instance_id"]),
                        "--json",
                        "{}",
                        "--output",
                        "json",
                        "--non-interactive",
                    ],
                    "why": "The live runtime was discovered but its typed host API probe failed.",
                }
            elif readiness_failure == "motionbuilder_runtime_ambiguous":
                readiness_next_step = {
                    "id": "list_motionbuilder_instances",
                    "description": "List live instances before selecting an exact runtime.",
                    "command": ["dcc-mcp-cli", "list", "--output", "json"],
                    "why": "Verification will not choose among multiple MotionBuilder processes.",
                }
            else:
                readiness_next_step = {
                    "id": "start_motionbuilder",
                    "description": "Start the selected MotionBuilder and rerun typed verification.",
                    "command": [str(host)],
                    "why": "The startup hook becomes callable only after the host loads it.",
                }
            report.update(
                {
                    "status": "failed",
                    "steps": [{"id": "verify", "status": "failed"}],
                    "verify": {
                        "directly_usable": False,
                        "failure_stage": failure_stage,
                        "failure_reason": readiness_failure,
                    },
                    "next_steps": [readiness_next_step],
                    "readiness": readiness_evidence,
                }
            )
            return report, EXIT_VERIFY
        report.update(
            {
                "status": "ok",
                "steps": [{"id": "verify", "status": "ok"}],
                "verify": {
                    "directly_usable": True,
                    "failure_stage": None,
                    "failure_reason": None,
                },
                "next_steps": [],
                "readiness": readiness_evidence,
            }
        )
        return report, EXIT_OK

    if args.verb in {"install", "upgrade"} and (args.dry_run or not args.yes):
        return report, EXIT_OK

    if args.verb in {"install", "upgrade"}:
        if current_state != "current":
            lock = _inspect_lock(startup)
            if lock.get("requires_restart"):
                report.update(
                    {
                        "status": "requires_restart",
                        "steps": [{"id": "preflight", "status": "requires_restart"}],
                        "failure": {"stage": "lock_preflight", "reason": "windows_file_lock"},
                        "next_steps": [
                            {
                                "id": "restart_motionbuilder",
                                "description": (
                                    "Close the exact MotionBuilder process holding the reported "
                                    "file."
                                ),
                                "command": [
                                    "dcc-mcp-mobu",
                                    args.verb,
                                    "--dcc-path",
                                    str(host),
                                    "--python",
                                    str(python_path),
                                    "--json",
                                    "--yes",
                                ],
                                "why": (
                                    "A loaded file cannot be safely replaced until that host exits."
                                ),
                            }
                        ],
                        "lock": lock,
                    }
                )
                return report, EXIT_REQUIRES_RESTART
            committed, error = _commit_install(
                startup=startup,
                shim=shim,
                receipt_path=receipt,
                host=host,
                host_version=host_version,
                python_path=python_path,
                python_probe=python_probe,
            )
            if not committed:
                requires_restart = bool(error and error.get("reason") == "windows_file_lock")
                report.update(
                    {
                        "status": "requires_restart" if requires_restart else "failed",
                        "steps": [{"id": "install", "status": "failed"}],
                        "failure": {
                            "stage": "install",
                            "reason": error.get("reason") if error else "transaction_failed",
                        },
                        "next_steps": [
                            {
                                "id": "retry_transaction",
                                "description": (
                                    "Retry after resolving the reported transaction error."
                                ),
                                "command": [
                                    "dcc-mcp-mobu",
                                    args.verb,
                                    "--dcc-path",
                                    str(host),
                                    "--python",
                                    str(python_path),
                                    "--json",
                                    "--yes",
                                ],
                                "why": "Rollback restored the previous receipted installation.",
                            }
                        ],
                    }
                )
                return report, EXIT_REQUIRES_RESTART if requires_restart else EXIT_INSTALL
        report["steps"] = [
            {"id": "preflight", "status": "ok"},
            {"id": "install", "status": "ok"},
            {"id": "verify", "status": "failed"},
        ]
        ready, readiness_failure, readiness_evidence = _runtime_readiness()
        if not ready:
            report.update(
                {
                    "status": "partial",
                    "verify": {
                        "directly_usable": False,
                        "failure_stage": "readiness",
                        "failure_reason": readiness_failure,
                    },
                    "next_steps": [
                        {
                            "id": "start_motionbuilder",
                            "description": (
                                "Start the selected MotionBuilder and rerun typed verification."
                            ),
                            "command": [str(host)],
                            "why": (
                                "The installed startup hook has not been loaded by a live host yet."
                            ),
                        }
                    ],
                    "readiness": readiness_evidence,
                }
            )
            return report, EXIT_VERIFY
        report.update(
            {
                "status": "ok",
                "steps": [
                    {"id": "preflight", "status": "ok"},
                    {"id": "install", "status": "ok"},
                    {"id": "verify", "status": "ok"},
                ],
                "verify": {
                    "directly_usable": True,
                    "failure_stage": None,
                    "failure_reason": None,
                },
                "next_steps": [],
                "readiness": readiness_evidence,
            }
        )
        return report, EXIT_OK
    return report, EXIT_OK


def main(argv: Optional[list[str]] = None) -> int:
    """Run the standard adapter-owned lifecycle command."""
    args = _parser().parse_args(argv)
    report, exit_code = _plan(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
