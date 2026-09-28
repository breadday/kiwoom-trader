"""Python-level regression guards for trusted, checked-in demo code only.

This helper is not an OS security sandbox: native extensions may bypass the
patched Python APIs. Never run untrusted demo code through this module.
"""

import asyncio
import builtins
import contextlib
import http.client
import io
import multiprocessing.process
import os
import runpy
import socket
import subprocess
import sys
import urllib.request
from contextlib import ExitStack
from unittest.mock import patch

try:
    import pty
except ImportError:
    pty = None

import requests
import urllib3.connectionpool

# Import trusted numerical dependencies before process guards are installed.
# pandas initializes platform metadata during import and may consult a native
# platform command; that dependency bootstrap is not demo-code execution.
import numpy
import pandas


NETWORK_ENTRYPOINTS = (
    "socket.getaddrinfo",
    "socket.gethostbyname",
    "socket.create_connection",
    "socket.socket.connect",
    "socket.socket.connect_ex",
    "socket.socket.sendto",
    "socket.socket.send",
    "socket.socket.sendall",
    "http.client.HTTPConnection.connect",
    "http.client.HTTPSConnection.connect",
    "urllib.request.urlopen",
    "requests.sessions.Session.request",
    "urllib3.connectionpool.HTTPConnectionPool.urlopen",
    "urllib3.connectionpool.HTTPSConnectionPool.urlopen",
)
BLOCKED_MODULES = {"api.kiwoom_auth", "api.kiwoom_api"}
_ORIGINAL_IMPORT = builtins.__import__


def _guarded_import(name, *args, **kwargs):
    fromlist = kwargs.get("fromlist", args[2] if len(args) > 2 else ()) or ()
    blocked_fromlist = name == "api" and any("api." + item in BLOCKED_MODULES for item in fromlist)
    if name in BLOCKED_MODULES or blocked_fromlist:
        raise AssertionError("broker client import is forbidden: " + name)
    return _ORIGINAL_IMPORT(name, *args, **kwargs)


def _fail_network(*_args, **_kwargs):
    raise AssertionError("selected Python network API is forbidden during the trusted-source regression check")


def _process_entrypoints():
    entrypoints = [
        (subprocess, name)
        for name in ("Popen", "run", "call", "check_call", "check_output")
    ]
    entrypoints.extend(
        (asyncio, name)
        for name in ("create_subprocess_exec", "create_subprocess_shell")
        if hasattr(asyncio, name)
    )
    entrypoints.append((multiprocessing.process.BaseProcess, "start"))
    entrypoints.extend(
        (os, name)
        for name in dir(os)
        if name in {"system", "popen", "startfile", "fork", "forkpty"}
        or name.startswith(("spawn", "exec", "posix_spawn"))
    )
    if pty is not None and hasattr(pty, "spawn"):
        entrypoints.append((pty, "spawn"))
    return entrypoints


def _fail_process(*_args, **_kwargs):
    raise AssertionError("selected Python process API is forbidden during the trusted-source regression check")


def run_demo_offline(script_path):
    """Run trusted demo code with selected Python-level regression guards.

    This function does not provide OS-level isolation; native code can bypass
    its monkeypatches.
    """
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), patch("builtins.__import__", side_effect=_guarded_import):
        with ExitStack() as stack:
            for entrypoint in NETWORK_ENTRYPOINTS:
                stack.enter_context(patch(entrypoint, side_effect=_fail_network))
            for target, name in _process_entrypoints():
                stack.enter_context(patch.object(target, name, side_effect=_fail_process))
            namespace = runpy.run_path(str(script_path), run_name="__main__")
    return namespace, captured.getvalue()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m tests.offline_demo_runner <demo-script>")
    _, output = run_demo_offline(sys.argv[1])
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
