"""MotionBuilder Python Startup script for dcc-mcp-mobu."""

import traceback

try:
    from dcc_mcp_core import capture_bootstrap_errors

    from dcc_mcp_mobu.__version__ import __version__

    with capture_bootstrap_errors(
        "mobu",
        adapter_version=__version__,
        min_core_version="0.19.45",
    ):
        from dcc_mcp_mobu.plugin import initialize

        initialize()
except Exception:
    # The Core capture retains the bounded diagnostic. Keep the native console
    # evidence too, but never stop MotionBuilder from running later startup files.
    traceback.print_exc()
