"""Exercise MotionBuilder's pump with Core's real native HTTP dispatcher."""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from dcc_mcp_core import HostExecutionBridge, McpHttpConfig, McpHttpServer, ToolRegistry

from dcc_mcp_mobu.dispatcher import MobuDispatcher


@pytest.fixture
def dispatcher(monkeypatch):
    callbacks = []
    idle = SimpleNamespace(Add=callbacks.append, Remove=callbacks.remove)
    monkeypatch.setitem(
        sys.modules, "pyfbsdk", SimpleNamespace(FBSystem=lambda: SimpleNamespace(OnUIIdle=idle))
    )
    instance = MobuDispatcher()
    instance.install()
    instance.install()
    assert len(callbacks) == 1
    yield instance, callbacks
    instance.uninstall()
    assert not callbacks


def pump_until_done(future, callbacks):
    deadline = time.monotonic() + 5
    while not future.done() and time.monotonic() < deadline:
        for callback in list(callbacks):
            callback(None, None)
        time.sleep(0.001)
    return future.result(timeout=1)


def test_python_and_native_queues_use_the_host_thread(dispatcher):
    instance, callbacks = dispatcher
    host_thread = threading.get_ident()
    bridge = HostExecutionBridge(dispatcher=instance)
    native = bridge.resolve_host_dispatcher()
    assert native is bridge.resolve_host_dispatcher()
    with ThreadPoolExecutor(max_workers=2) as pool:
        python_call = pool.submit(
            bridge.dispatch_callable,
            threading.get_ident,
            action_name="inspect_scene",
            thread_affinity="main",
        )
        native_call = native.post(threading.get_ident)
        assert pump_until_done(python_call, callbacks) == host_thread
        for callback in callbacks:
            callback()
        assert native_call.wait(timeout=1) == host_thread


def test_any_affinity_does_not_wait_for_ui_idle(dispatcher):
    instance, _ = dispatcher
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(
            instance.dispatch_callable, threading.get_ident, affinity="any"
        ).result(timeout=1)
    assert result != threading.get_ident()


def test_uninstall_releases_queued_waiter_without_running_host_code(dispatcher):
    instance, _ = dispatcher
    called = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(instance.dispatch_callable, lambda: called.append(True))
        deadline = time.monotonic() + 2
        while instance.pending_count() == 0 and time.monotonic() < deadline:
            time.sleep(0.001)
        assert instance.pending_count() > 0
        instance.uninstall()
        with pytest.raises(RuntimeError, match="Interrupted"):
            future.result(timeout=1)
    assert not called


def test_http_main_affinity_call_runs_on_mobu_idle_thread(dispatcher, tmp_path, monkeypatch):
    instance, callbacks = dispatcher
    monkeypatch.setenv("DCC_MCP_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "0")
    monkeypatch.setenv("DCC_MCP_DISABLE_DEFAULT_SKILL_PATHS", "1")
    registry = ToolRegistry()
    registry.register(
        "inspect_scene",
        description="Verify MotionBuilder main-thread HTTP routing",
        dcc="mobu",
        version="1.0.0",
        execution="sync",
        thread_affinity="main",
        enforce_thread_affinity=True,
    )
    server = McpHttpServer(registry, McpHttpConfig(port=0, server_name="mobu-http-regression"))
    bridge = HostExecutionBridge(dispatcher=instance)
    server.attach_dispatcher(bridge.resolve_host_dispatcher())
    observed = []

    def inspect_scene(params):
        observed.append(threading.get_ident())
        return {"success": True, "host_thread": observed[-1]}

    server.register_handler("inspect_scene", inspect_scene)
    handle = server.start()
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    def post(method, params):
        request = urllib.request.Request(
            handle.mcp_url(),
            data=json.dumps(
                {"jsonrpc": "2.0", "id": method, "method": method, "params": params}
            ).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            session = response.headers.get("Mcp-Session-Id")
            if session:
                headers["Mcp-Session-Id"] = session
            return json.loads(response.read())

    try:
        post(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "mobu-dispatch-regression", "version": "1.0"},
            },
        )
        listing = post("tools/list", {})
        assert any(tool["name"] == "inspect_scene" for tool in listing["result"]["tools"])
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(post, "tools/call", {"name": "inspect_scene", "arguments": {}})
            response = pump_until_done(future, callbacks)
        assert "error" not in response, response
        assert response["result"]["isError"] is False, response
        assert observed == [threading.get_ident()]
    finally:
        handle.shutdown()
