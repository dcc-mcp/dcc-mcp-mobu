# AGENTS.md — dcc-mcp-mobu

> Navigation map, not a reference manual. Follow the links; don't read
> everything upfront.

dcc-mcp-mobu is the Autodesk MotionBuilder adapter for the DCC Model Context
Protocol (MCP) ecosystem. It exposes MotionBuilder scene, character and
animation operations as typed MCP tools on top of `dcc-mcp-core`.

---

## Repository Contract

**This repository has no justfile. Use `uv` with the `dev` extra, matching CI.**

| Task | Command |
|------|---------|
| Install with dev extras | `uv sync --extra dev` |
| Test | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Install CLI entrypoint check | `uv run python -m pytest tests/test_install_cli.py tests/test_package.py -q` |

**Repository layout**

| Path | Role |
|------|------|
| `src/dcc_mcp_mobu/` | Adapter package — server, dispatcher, skills |
| `docs/` | Documentation |
| `tests/` | pytest suite |
| `tools/` | Dev helper scripts |
| `pyproject.toml` | Package metadata; `dev` extra holds build/pytest/ruff/twine |

**Release flow** — `release-please` on `main` drives `CHANGELOG.md` and the version in
`pyproject.toml` from Conventional Commit subjects. Tagging and
publishing run in CI. Never edit `CHANGELOG.md` or a version string by hand.

**Prohibitions**

- Do not edit `CHANGELOG.md` or version strings manually.
- Do not add a second agent contract file at the repository root; `AGENTS.md` is the single source.
- Do not add a runtime dependency for something only tests need — put it in the `dev` extra.
- Prefer typed skill tools over raw in-MotionBuilder scripting.

---

## Agent Contract Files

`AGENTS.md` is the **only** agent contract file at the repository root. It is the
native instruction file for Codex, OpenCode, Cursor, GitHub Copilot, Windsurf,
Cline, Roo Code, Kiro, Trae, and Augment, and Claude Code falls back to it when
no `CLAUDE.md` exists — so do not add `CLAUDE.md`, `GEMINI.md`, `CURSOR.md`, or
any other vendor-specific variant.

**Gemini CLI exception:** Gemini CLI defaults its context file to `GEMINI.md`. To
make it read `AGENTS.md`, set `context.fileName` once in `~/.gemini/settings.json`:

```json
{
  "context": {
    "fileName": ["AGENTS.md", "GEMINI.md"]
  }
}
```
