---
name: mobu-api
description: >-
  Host skill - inspect MotionBuilder FBSystem, FBScene, FBComponent, and
  FBCharacter state through read-only typed queries. Not for raw Python or
  scene mutation.
license: MIT
compatibility: "MotionBuilder Python API; dcc-mcp-core 0.19+"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: mobu
    version: "0.1.0"
    layer: foundation
    stage: api
    search-hint: "motionbuilder mobu FBSystem FBScene FBComponent FBCharacter sync components"
    tags: "motionbuilder, mobu, fb-system, fb-scene, fb-component, character, sync"
    tools: tools.yaml
---

# MotionBuilder API Projections

Use these tools to inspect the official MotionBuilder object model through the
public `pyfbsdk` surface. `inspect_system` reports host and scene collection
metadata. `list_components` exposes stable `FBComponent` identity fields.
`list_characters` reports characterization, input, and synchronization state.

All tools are read-only and execute on the MotionBuilder UI thread.
