"""UI-thread execution bridge for MotionBuilder."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Event, Lock, current_thread, main_thread
from typing import Any, Callable, Deque, Optional


@dataclass
class _PendingCall:
    callback: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    completed: Event
    result: dict[str, Any]


class MobuDispatcher:
    """Dispatch bridge that drains queued calls from ``FBSystem.OnUIIdle``."""

    def __init__(self) -> None:
        self._calls: Deque[_PendingCall] = deque()
        self._lock = Lock()
        self._system: Optional[Any] = None
        self._installed = False

    def install(self) -> None:
        """Register the UI-idle callback once MotionBuilder is available."""
        if self._installed:
            return

        from pyfbsdk import FBSystem

        self._system = FBSystem()
        self._system.OnUIIdle.Add(self._drain)
        self._installed = True

    def uninstall(self) -> None:
        """Remove the UI-idle callback during adapter shutdown."""
        if not self._installed or self._system is None:
            return

        self._system.OnUIIdle.Remove(self._drain)
        self._system = None
        self._installed = False

    def dispatch_callable(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run a callable on the MotionBuilder UI thread and return its result."""
        for key in (
            "context",
            "action_name",
            "skill_name",
            "execution",
            "timeout_hint_secs",
            "affinity",
            "thread_affinity",
        ):
            kwargs.pop(key, None)

        if current_thread() is main_thread():
            return callback(*args, **kwargs)
        if not self._installed:
            raise RuntimeError("MotionBuilder UI dispatcher is not installed")

        completed = Event()
        result: dict[str, Any] = {}
        pending = _PendingCall(callback, args, kwargs, completed, result)
        with self._lock:
            self._calls.append(pending)

        if not completed.wait(timeout=30):
            raise RuntimeError("Timed out waiting for MotionBuilder UI thread execution")
        if "error" in result:
            raise result["error"]
        return result["value"]

    def _drain(self, *_: Any) -> None:
        """Execute queued work while MotionBuilder is idle."""
        while True:
            with self._lock:
                if not self._calls:
                    return
                pending = self._calls.popleft()

            try:
                pending.result["value"] = pending.callback(*pending.args, **pending.kwargs)
            except Exception as error:
                pending.result["error"] = error
            finally:
                pending.completed.set()
