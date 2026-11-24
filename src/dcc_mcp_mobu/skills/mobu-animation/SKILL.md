---
name: mobu-animation
description: >-
  Host skill - inspect MotionBuilder takes and Story tracks and clips through
  read-only typed queries. Not for raw Python execution or complex animation
  authoring.
license: MIT
compatibility: "MotionBuilder Python API; dcc-mcp-core 0.19+"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: mobu
    version: "0.1.0"
    layer: domain
    stage: animation
    search-hint: "motionbuilder mobu animation takes current take story track clip"
    tags: "motionbuilder, mobu, animation, take, story, clip"
    tools: tools.yaml
---

# MotionBuilder Animation Inspection

Use these read-only tools to inspect scene takes, the current take, and Story
tracks with their clips and sub-tracks. Time values include seconds, frames,
and the host's formatted value when MotionBuilder exposes them.

Character setup, Control Rig creation or connection, plotting, key editing,
retiming, and other complex animation writes remain later capabilities. The
future `mobu-mocap` skill covers format-specific capture workflows. External
plugin loading belongs to `mobu-plugins`, and Autodesk Flow Production
Tracking integration belongs to `dcc-mcp-fpt`.
