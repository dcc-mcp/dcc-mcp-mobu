"""MotionBuilder Python Startup entry points."""

from .server import start_server, stop_server


def initialize() -> None:
    """Start the MCP adapter after MotionBuilder finishes startup."""
    start_server()


def shutdown() -> None:
    """Stop the MCP adapter before MotionBuilder exits."""
    stop_server()
