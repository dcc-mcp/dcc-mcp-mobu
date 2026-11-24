"""Diagnose the optional dcc-mcp-fpt runtime connection."""

from _common import config_diagnostics, resolve_adapter, safe_connection_diagnostics
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success


@skill_entry
def main() -> dict:
    """Return non-secret FPT connection diagnostics or an unavailable result."""
    adapter, reason = resolve_adapter()
    configuration = config_diagnostics()
    if adapter is None:
        return skill_success(
            "Flow Production Tracking adapter is unavailable in this MotionBuilder process.",
            status="unavailable",
            error="adapter_unavailable",
            adapter="dcc-mcp-fpt",
            reason=reason,
            configuration=configuration,
            secrets_exposed=False,
        )
    try:
        diagnostics = safe_connection_diagnostics(adapter.connection_diagnostics({}))
    except Exception as exc:
        return skill_error(
            "Flow Production Tracking connection diagnostics failed",
            "external_connection_error",
            adapter="dcc-mcp-fpt",
            error_type=type(exc).__name__,
            configuration=configuration,
            secrets_exposed=False,
        )
    authenticated = diagnostics.get("authenticated") is True
    return skill_success(
        "Flow Production Tracking connection diagnostics completed.",
        status="connected" if authenticated else "unavailable",
        adapter="dcc-mcp-fpt",
        connection=diagnostics,
        configuration=configuration,
        secrets_exposed=False,
    )
