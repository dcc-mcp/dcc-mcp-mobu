---
name: mobu-mocap
description: >-
  Host skill - inspect MotionBuilder motion-capture devices, optical devices,
  actors, and marker sets through read-only typed queries. Not for live device
  control, recording, calibration commands, or raw Python execution.
license: MIT
compatibility: "MotionBuilder Python API; dcc-mcp-core 0.19+"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: mobu
    version: "0.1.0"
    layer: domain
    stage: mocap
    search-hint: "motionbuilder mobu mocap device optical actor marker set online live recording calibration"
    tags: "motionbuilder, mobu, mocap, device, optical, actor, marker-set"
    tools: tools.yaml
---

# MotionBuilder Mocap Diagnostics

Use these tools to inspect visible MotionBuilder motion-capture state without
starting, stopping, recording, calibrating, or changing a device. The tools
read scene device, actor, marker-set, and optical marker collections and return
stable JSON-safe state projections.

Calibration setup methods and real-time recording controls are intentionally
outside this read-only skill. A future extension may add them only with an
explicit operation contract and host-side verification.
