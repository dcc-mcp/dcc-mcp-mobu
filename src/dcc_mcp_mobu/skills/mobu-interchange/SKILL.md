---
name: mobu-interchange
description: >-
  Host skill - open, merge, append, import, export, and inspect the active
  MotionBuilder file and scene through typed operations. All file paths must be
  absolute. Not for raw Python execution or advanced motion-capture options.
license: MIT
compatibility: "MotionBuilder Python API; dcc-mcp-core 0.19+"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: mobu
    version: "0.1.0"
    layer: domain
    stage: interchange
    search-hint: "motionbuilder mobu open merge append import export file scene state fbx"
    tags: "motionbuilder, mobu, interchange, file, scene, fbx"
    tools: tools.yaml
---

# MotionBuilder Interchange

Use these tools for typed file and scene interchange in a running
MotionBuilder host. `open` replaces the active scene. `merge` and `append`
add scene data to the active scene. `import` and `export` use MotionBuilder's
Motion File API and currently expose the direct SDK FBX path only.

Every operation requires an absolute path. Input files must already exist, and
export refuses to replace an existing file unless `overwrite` is explicitly
true. Successful mutations include a readback of the current file and scene
state in `postcondition` and `context.state`.

The `mobu-mocap` skill remains a later boundary for format-specific capture
options such as BVH, C3D, HTR, TRC, and Acclaim files. `mobu-plugins` and
`dcc-mcp-fpt` / Autodesk Flow Production Tracking connections are also outside
this skill.
