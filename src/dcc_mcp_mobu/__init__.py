"""Autodesk MotionBuilder MCP adapter."""

from .__version__ import __version__

__all__ = ["MobuMcpServer", "__version__"]


def __getattr__(name: str):
    """Load the host server only when the adapter entry point requests it."""
    if name == "MobuMcpServer":
        from .server import MobuMcpServer

        return MobuMcpServer
    raise AttributeError(name)
