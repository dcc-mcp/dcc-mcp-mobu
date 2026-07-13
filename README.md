# dcc-mcp-mobu

An MCP adapter for Autodesk MotionBuilder, built on [dcc-mcp-core](https://github.com/dcc-mcp/dcc-mcp-core).

It exposes a small, typed scene-management surface and runs MotionBuilder API calls on the application's UI thread.

## Install

```bash
pip install dcc-mcp-mobu
```

Copy the installed `dcc_mcp_mobu/mobu_plugin/startup/dcc_mcp_mobu.py` into a MotionBuilder Python Startup directory, or add that directory to the application's Python Startup paths. Restart MotionBuilder to start the adapter.

By default the MCP server listens on port `8765`. Set `DCC_MCP_MOBU_PORT` to override it.

## Tools

- `mobu-scene.inspect_scene`
- `mobu-scene.list_models`
- `mobu-scene.save_scene`

`save_scene` is destructive and requires an explicit absolute `.fbx` path.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check src tests tools
ruff format --check src tests tools
python tools/lint_skills.py
python -m build
```

## License

MIT
