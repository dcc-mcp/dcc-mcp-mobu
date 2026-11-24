---
name: mobu-production-tracking
description: >-
  Host skill - expose MotionBuilder scene, asset, take, and Story shot mapping
  metadata and diagnose an optional dcc-mcp-fpt connection contract. It never
  writes credentials to MotionBuilder and never publishes or changes external
  production-tracking data.
license: MIT
compatibility: "MotionBuilder Python API; optional dcc-mcp-fpt runtime contract"
allowed-tools: Python
metadata:
  dcc-mcp:
    dcc: mobu
    version: "0.1.0"
    layer: domain
    stage: production-tracking
    search-hint: "motionbuilder mobu ShotGrid Flow Production Tracking FPT asset shot take mapping connection"
    tags: "motionbuilder, mobu, production-tracking, shotgrid, flow-production-tracking, fpt"
    tools: tools.yaml
---

# MotionBuilder Production Tracking Context

`inspect_mapping_context` reads current MotionBuilder metadata that can be
mapped to Asset, Shot, and Take records. It returns candidate names and Story
clip timing without querying or modifying an external service.

`check_connection` uses the existing `dcc-mcp-fpt` environment names and, when
that adapter is already registered in the same Python process, its existing
`runtime_context.get_request_connection_info` protocol. This skill does not
copy authentication, accept credentials as tool parameters, write credentials
into MotionBuilder, or perform publish, upload, write-back, or status changes.

When the optional adapter is unavailable, the result is an explicit
`unavailable` diagnostic. This repository does not claim that ShotGrid or
Autodesk Flow Production Tracking is connected by default.
