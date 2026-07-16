"""MotionBuilder MCP server lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from dcc_mcp_core import DccServerOptions, HostExecutionBridge
from dcc_mcp_core.server_base import DccServerBase

from .__version__ import __version__
from .dispatcher import MobuDispatcher

DEFAULT_PORT = 0
SERVER_NAME = "dcc-mcp-mobu"
_dispatcher = MobuDispatcher()
_server: Optional["MobuMcpServer"] = None


class MobuMcpServer(DccServerBase):
    """DCC MCP server configured for a running MotionBuilder process."""

    def __init__(self, port: Optional[int] = None) -> None:
        options = DccServerOptions.from_env(
            "mobu",
            Path(__file__).resolve().parent / "skills",
            port=port,
            server_name=SERVER_NAME,
            server_version=__version__,
            execution_bridge=HostExecutionBridge(dispatcher=_dispatcher),
            enable_file_logging=True,
            enable_telemetry=True,
        )
        super().__init__(options=options)

    def _version_string(self) -> str:
        try:
            from pyfbsdk import FBSystem

            return str(FBSystem().Version)
        except Exception:
            return "unknown"


def start_server(port: Optional[int] = None) -> MobuMcpServer:
    """Start the singleton MCP server from MotionBuilder startup code."""
    global _server
    if _server is not None:
        return _server

    _dispatcher.install()
    _server = MobuMcpServer(port)
    _server.register_builtin_actions()
    _server.start()
    return _server


def stop_server() -> None:
    """Stop the adapter and unregister its UI-idle callback."""
    global _server
    if _server is not None:
        _server.stop()
        _server = None
    _dispatcher.uninstall()
