"""UI-thread execution bridge for MotionBuilder."""

from __future__ import annotations

from functools import partial
from threading import current_thread, main_thread
from typing import Any, Callable, Optional
from uuid import uuid4

from dcc_mcp_core import HostUiDispatcherBase


class MobuDispatcher(HostUiDispatcherBase):
    """Pump shared Python and native HTTP queues from ``FBSystem.OnUIIdle``."""

    def __init__(self) -> None:
        super().__init__(label="MotionBuilder UI")
        self._system: Optional[Any] = None
        self._installed = False

    def install(self) -> None:
        """Register the UI-idle callback once MotionBuilder is available."""
        if self._installed:
            return
        if current_thread() is not main_thread():
            raise RuntimeError("Install the MotionBuilder UI dispatcher on the host main thread")

        from pyfbsdk import FBSystem

        self._system = FBSystem()
        self._system.OnUIIdle.Add(self._drain)
        self._installed = True
        # Establish host identity without executing work during startup.
        self.drain_queue(budget_ms=0)

    def uninstall(self) -> None:
        """Remove the UI-idle callback during adapter shutdown."""
        if not self._installed or self._system is None:
            return

        self._system.OnUIIdle.Remove(self._drain)
        self._system = None
        self._installed = False
        self.shutdown()

    def poke_host_pump(self) -> None:
        """Let the registered idle event drain work without cross-thread SDK calls."""

    def dispatch_callable(
        self,
        callback: Callable[..., Any],
        *args: Any,
        affinity: str = "main",
        context: Any = None,
        action_name: str = "",
        skill_name: Optional[str] = None,
        execution: Optional[str] = None,
        timeout_hint_secs: Optional[int] = None,
        thread_affinity: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Run a callable on the MotionBuilder UI thread and return its result."""
        if not self._installed:
            raise RuntimeError("MotionBuilder UI dispatcher is not installed")
        if self.is_host_thread():
            return callback(*args, **kwargs)
        outcome = self.submit_callable(
            str(uuid4()),
            partial(callback, *args, **kwargs),
            affinity=thread_affinity or affinity,
            timeout_ms=int(timeout_hint_secs * 1000) if timeout_hint_secs else None,
        )
        if not outcome["success"]:
            raise RuntimeError(outcome["error"])
        return outcome["output"]

    def _drain(self, *_: Any) -> None:
        """Drain both queues within the shared soft per-idle budget."""
        self.drain_queue(budget_ms=8)
