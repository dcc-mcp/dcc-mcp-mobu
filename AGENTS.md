# AGENTS.md — dcc-mcp-mobu

> MCP adapter for Autodesk MotionBuilder, built on `dcc-mcp-core`. Exposes a
> small typed scene-management surface and runs MotionBuilder API calls on the
> application's UI thread.
> Navigation map for AI agents, not a reference manual. Follow the links; do not
> read everything up front.

## Build & test

There is no `justfile` or `vx.toml` in this repo — use the commands CI runs:

```bash
python -m pip install -e ".[dev]"   # editable install with dev extras
pytest                              # run the test suite
ruff check src tests tools          # lint
ruff format --check src tests tools # format check
python tools/lint_skills.py         # validate SKILL.md / tools.yaml
python -m build                     # build wheel + sdist
```

## Agent control path

AI agents drive MotionBuilder through the shared gateway using the `dcc-mcp`
skill and `dcc-mcp-cli` REST commands:

```bash
dcc-mcp-cli list                                     # live sessions
dcc-mcp-cli dcc-types                                # release-catalog support
dcc-mcp-cli search --query "<task>" --dcc-type mobu
dcc-mcp-cli describe <tool-slug>
dcc-mcp-cli call <tool-slug> --json '{"key":"value"}'
```

If a tool belongs to an inactive progressive skill, load it first:
`dcc-mcp-cli load-skill <skill-name> --dcc-type mobu`.

If `dcc-mcp-cli` is missing, obtain user consent before running the official
install commands in the README Agent workflow. Keep an official build current
with `dcc-mcp-cli update check` / `dcc-mcp-cli update apply` — `update apply`
stages the CLI for the next launch and does not update a running
`dcc-mcp-server`.

Each adapter instance takes an OS-assigned port and registers it for CLI
discovery. Connect through the stable gateway at `http://127.0.0.1:9765/mcp`;
set `DCC_MCP_MOBU_PORT` only when a fixed direct endpoint is required.

## Skills and tools

| Skill | Tools |
|---|---|
| `mobu-scene` | `inspect_scene`, `list_models`, `save_scene` |
| `mobu-diagnostics` | `ping` (typed host ping used by install verification) |

Prefer typed skills and tools over raw scripts. `save_scene` is destructive and
requires an explicit absolute `.fbx` path.

## Install is not a pip install

Follow `install.md`. It installs into MotionBuilder's exact `mobupy`, stages a
receipted Startup hook, and verifies a typed host ping. **A system-pip install
is not a MotionBuilder installation.**

## Repo layout

| Path | Role |
|---|---|
| `src/dcc_mcp_mobu/` | Python package — `MobuMcpServer`, dispatcher, plugin, install CLI |
| `src/dcc_mcp_mobu/skills/` | `mobu-scene`, `mobu-diagnostics` (`SKILL.md` + `tools.yaml` + `scripts/`) |
| `src/dcc_mcp_mobu/mobu_plugin/startup/` | The Startup hook staged into MotionBuilder |
| `tests/` | `test_install_cli.py`, `test_package.py` |
| `tools/` | `lint_skills.py` |
| `install.md` | Agent-first install / status / verify / uninstall / upgrade guide |
| `docs/assets/` | Images |

## Release

- release-please drives versioning from Conventional Commits on `main`.
- `feat:` → minor, `fix:` → patch. Every other prefix still lands on **patch**:
  `DefaultVersioningStrategy.determineReleaseType()` falls back to
  `PatchVersionUpdate` when the batch has no `feat:` and no breaking change, so
  `chore:`/`docs:`/`ci:` are **not** “no release”.
- What those prefixes change is the changelog: `chore:`/`ci:`/`style`/`refactor`/
  `test`/`build` are `hidden: true` sections, while `docs:` is a **visible**
  `Documentation` section (`release-type: python`).
- The version is mirrored into `pyproject.toml`,
  `src/dcc_mcp_mobu/__version__.py`, and `install.md`; do not edit those by
  hand.
- Use `chore:` for config and doc work: it still bumps the version, but keeps
  the changelog free of valueless entries.

## Do / Don't

- **Do** single-source agent instructions here — this is the only agent contract
  file at the repo root. Rebase onto `main` before merging (no merge commits);
  CI must pass before review.
- **Do** keep the wheel payload complete: CI asserts
  `dcc_mcp_mobu/install_cli.py`, `dcc_mcp_mobu/mobu_plugin/startup/dcc_mcp_mobu.py`,
  and `dcc_mcp_mobu/skills/mobu-diagnostics/scripts/ping.py` ship in the wheel,
  and that `install.md` ships in the sdist.
- **Don't** add `CLAUDE.md` / `GEMINI.md` / `CURSOR.md` / `ANTHROPIC.md` /
  `OPENAI.md` / `COPILOT.md` / `CODEBUDDY.md` / `.cursorrules` / `.clinerules` /
  `.windsurfrules` at the root. This repo has no `docs/integrations/`; keep any
  vendor-specific notes here.
- **Don't** hardcode an exact version in tests (`assert __version__ == "X.Y.Z"`)
  — release-please bumps will break it. Use `>=` or read package metadata.
- **Don't** commit build artifacts to the repo root (`dist/`, `build/`,
  `coverage.json`, `*.egg-info`).
- **Don't** add AI-attribution footers to PR bodies or commit messages.
