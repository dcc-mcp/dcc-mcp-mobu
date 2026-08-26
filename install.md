# Install dcc-mcp-mobu

This runbook installs, verifies, upgrades, and removes the DCC-MCP adapter for
Autodesk MotionBuilder. The adapter implements the host-specific vertical slice
of [DCC-MCP Adapter Install SOP v1](https://dcc-mcp.github.io/dcc-mcp-core/guide/adapter-install-sop).

## Requirements

- **MotionBuilder:** 2023 or newer. MotionBuilder 2023 is the first supported
  generation because it embeds Python 3.9.7.
- **Python:** MotionBuilder's matching `mobupy`, Python 3.9 or newer. Do not use
  an unrelated system Python.
- **dcc-mcp-core:** `>=0.19.45,<1.0.0`, installed in that same interpreter.
- **Platforms:** Autodesk MotionBuilder is supported by this adapter on Windows
  and Linux. Autodesk does not publish MotionBuilder for macOS; macOS CI checks
  the wheel and lifecycle contract only. A studio-provided compatible wrapper
  must supply all three exact paths described below.
- **Permissions:** write access to one user-owned Python Startup directory.
  The installer never modifies MotionBuilder's factory Startup directory.

Install the wheel with the exact interpreter selected for this MotionBuilder:

```text
<absolute-mobupy> -m pip install "dcc-mcp-mobu==0.4.0"
```

The installer verifies that this interpreter imports the exact adapter version
and a compatible Core before writing a Startup hook.

## Supported versions

| Adapter | dcc-mcp-core | MotionBuilder | Embedded Python | Platforms |
| --- | --- | --- | --- | --- |
| 0.4.x | >=0.19.45,<1.0.0 | 2023+ | 3.9+ | Windows, Linux |

Official default installation layouts are:

| Platform | Host | Embedded interpreter |
| --- | --- | --- |
| Windows | `C:\Program Files\Autodesk\MotionBuilder <year>\bin\x64\motionbuilder.exe` | `<host-root>\bin\x64\mobupy.exe` |
| Linux | `/usr/autodesk/MotionBuilder<year>/bin/motionbuilder` | `<host-root>/bin/mobupy` |
| macOS | No official Autodesk build | Studio-supplied path required |

The lifecycle CLI accepts an exact executable or an installation root through
`--dcc-path`. It accepts `--python` first, then
`DCC_MCP_INSTALL_PYTHON`, then one unique `mobupy` found under the selected
host root. If discovery finds zero or multiple candidates it fails with exit
10; it never chooses the newest installation.

MotionBuilder's documented Windows user Startup directory is:

```text
C:\Users\<user>\Documents\MB\<year>-x64\config\PythonStartup
```

Set `MOTIONBUILDER_PYTHON_STARTUP` to one exact, user-owned directory before
running the lifecycle CLI. This also handles redirected Windows Documents
folders and Linux studio profiles without guessing. MotionBuilder's factory
`<host-root>/bin/config/PythonStartup` is intentionally not an install target.

## Agent quick path

Inspect the universal Core plan first:

```text
dcc-mcp-cli install --dcc-type mobu
dcc-mcp-cli install --dcc-type mobu --execute --json
```

Core catalog execution remains tracked by `dcc-mcp-core#2252/#2320`. The
adapter-owned lifecycle is available now:

```text
dcc-mcp-mobu install --dcc-path <absolute-host> --python <absolute-mobupy> --json --dry-run
dcc-mcp-mobu install --dcc-path <absolute-host> --python <absolute-mobupy> --json --yes
```

The default and `--dry-run` are plans and never create Startup directories,
files, staging state, or receipts. Mutating verbs require `--yes`; `--json`
never prompts.

Stable exits are:

| Exit | Meaning |
| ---: | --- |
| 0 | Plan/status/uninstall completed, or typed verification is usable |
| 10 | Host, interpreter, version, profile, receipt, or partial-state preflight failed |
| 20 | Reserved for pinned acquisition/integrity failure; this wheel-owned adapter downloads no payload |
| 30 | Staging, commit, rollback, receipt, or uninstall transaction failed |
| 40 | Files/import passed but the live host or typed ping is not usable |
| 50 | Core reported real loaded/locked-file evidence requiring host restart |

Every result uses schema version 1 and includes `steps`, `next_steps`,
`receipt_path`, host/interpreter selection evidence, current state, and:

```json
{
  "verify": {
    "directly_usable": false,
    "failure_stage": "readiness",
    "failure_reason": "motionbuilder_runtime_not_ready"
  }
}
```

`next_steps` are argv arrays or precise file edits, never shell-joined strings.

## Manual path

1. Identify the exact MotionBuilder executable and its matching `mobupy`.
2. Select one user-owned Startup directory through
   `MOTIONBUILDER_PYTHON_STARTUP`.
3. Install the exact wheel into that `mobupy`; do not run pip through a system
   Python.
4. Run `install --json --dry-run` and verify host version, interpreter version,
   Startup path, `current_state`, ordered steps, and receipt path.
5. Run the same command with `--yes`.
6. Start or restart the selected MotionBuilder so it loads
   `dcc_mcp_mobu.py` from the Startup directory.
7. Run the verify command below.

The installer stages the complete hook on the destination filesystem, backs up
receipted prior state, uses atomic replacement where the platform permits, and
commits a versioned receipt only after the hook is in place. A commit failure
restores the previous hook and receipt. Repeating an identical install does not
rewrite either file.

The Startup hook wraps the full adapter import/start block with
`capture_bootstrap_errors`. It preserves the native traceback but catches the
failure after capture so MotionBuilder can continue running later Startup
scripts. It uses the existing in-process `DccServerBase`,
`HostExecutionBridge`, and `FBSystem.OnUIIdle` dispatcher; the installer adds no
thread, pump, job registry, or UI automation fallback.

## Verify

```text
dcc-mcp-mobu status --dcc-path <absolute-host> --python <absolute-mobupy> --json
dcc-mcp-mobu verify --dcc-path <absolute-host> --python <absolute-mobupy> --json
```

Verification proceeds through:

1. receipt schema, ownership path, installed file, and SHA-256 consistency;
2. exact adapter and Core import in the selected interpreter;
3. captured-bootstrap/startup state represented by the live runtime;
4. one unambiguous live `mobu` registry instance; and
5. `mobu_diagnostics__ping`, a typed, read-only, main-affinity host call.

Only a successful typed ping returns `directly_usable: true`. A copied hook,
running gateway, or registry row alone is insufficient. When multiple live
MotionBuilder instances exist, verification returns an ambiguity result rather
than selecting one arbitrarily.

CI validates the contract, transaction, receipt, rollback, entry point, and
bootstrap shim without a licensed MotionBuilder. A real Windows/Linux
MotionBuilder typed-ping smoke remains a manual/live-host gate.

## Upgrade

Install the exact newer wheel into the same target interpreter, then plan and
execute the adapter-owned upgrade:

```text
<absolute-mobupy> -m pip install --upgrade "dcc-mcp-mobu==<version>"
dcc-mcp-mobu upgrade --dcc-path <absolute-host> --python <absolute-mobupy> --json --dry-run
dcc-mcp-mobu upgrade --dcc-path <absolute-host> --python <absolute-mobupy> --json --yes
```

If MotionBuilder holds a receipted file lock, the command returns exit 50 with
the exact Core lock evidence. Save work, close only that MotionBuilder process,
then repeat the same command. The installer never terminates the host.

An upgrade transaction failure restores the prior working hook and receipt;
it never rolls back to an empty installation.

## Uninstall

Plan removal first, then execute it before uninstalling the wheel:

```text
dcc-mcp-mobu uninstall --dcc-path <absolute-host> --python <absolute-mobupy> --json --dry-run
dcc-mcp-mobu uninstall --dcc-path <absolute-host> --python <absolute-mobupy> --json --yes
<absolute-mobupy> -m pip uninstall dcc-mcp-mobu
```

Uninstall consumes the receipt and removes only its exact owned Startup hook
and receipt. It preserves every other Startup script, scene, preference, and
user file. A missing receipt plus a colliding hook is reported as partial and
is never deleted. Repeating uninstall after success is safe.

## Troubleshooting

| Result | Diagnosis | Action |
| --- | --- | --- |
| Exit 10, `dcc_path_not_found` or ambiguity | Host path is absent or not unique | Pass the exact executable with `--dcc-path`. |
| Exit 10, `host_version_below_floor` | MotionBuilder predates 2023/Python 3.9 | Select MotionBuilder 2023 or newer. |
| Exit 10, Python preflight | `mobupy` is missing, too old, or cannot import this adapter | Use the matching `--python`, then install the wheel with that interpreter. |
| Exit 10, `startup_path_unresolved` | No safe user Startup directory was proven | Set one exact `MOTIONBUILDER_PYTHON_STARTUP`. |
| Exit 10, partial/receipt | Hook ownership is unknown or the receipt is invalid | Inspect reported paths; do not delete or overwrite user files. |
| Exit 30 | Transaction or rollback failed | Preserve the JSON result and prior receipt; follow its exact retry step. |
| Exit 40, readiness | MotionBuilder has not loaded the hook | Start/restart the selected host, then rerun verify. |
| Exit 40, typed ping | Runtime exists but the main-thread host API probe failed | Run the returned exact `dcc-mcp-cli call mobu_diagnostics__ping` command. |
| Exit 50 | Core found a real loaded/locked file | Save work, close only the reported host, and retry. |

Early startup failures are written through Core's bounded
`dcc-mcp-mobu.<pid>.host-errors.log` capture and remain visible in the native
MotionBuilder console. For shared runtime diagnosis run:

```text
dcc-mcp-cli doctor
dcc-mcp-cli list
```

This adapter downloads no external binary, scrapes no latest URL, owns no
persistent payload cache, and never stores credentials in results or receipts.

Catalog `instructions_url` target (owned by the Core catalog follow-up):

```text
https://raw.githubusercontent.com/dcc-mcp/dcc-mcp-mobu/main/install.md
```
