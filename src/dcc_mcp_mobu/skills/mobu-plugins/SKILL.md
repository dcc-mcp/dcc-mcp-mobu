---
name: mobu-plugins
description: >-
  Host skill - inspect loaded MotionBuilder plug-in items, groups, metadata,
  and search paths through read-only SDK queries. Not for library loading,
  library freeing, object creation, or raw Python execution.
license: MIT
compatibility: "MotionBuilder Python API; dcc-mcp-core 0.19+"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: mobu
    version: "0.1.0"
    layer: domain
    stage: plugins
    search-hint: "motionbuilder mobu plugin loaded plugin item library path object discovery"
    tags: "motionbuilder, mobu, plugin, library, object-discovery"
    tools: tools.yaml
---

# MotionBuilder Plug-in Diagnostics

Use these tools to inspect plug-in items that MotionBuilder already reports as
loaded. The implementation uses `FBSystem.GetLoadedPluginItemsName`,
`GetLoadedPluginItemInfo`, `GetLoadedPluginItemGroups`, `GetPluginPath`, and
`GetPythonStartupPath`.

The SDK exposes `LibraryLoad`, `LibraryFree`, and `FBCreateObject`, but those
operations can change the host process or scene. This skill reports them as
`unsupported` for this read-only surface and never invokes them. A future
write skill must define explicit consent, rollback, and verification contracts.
