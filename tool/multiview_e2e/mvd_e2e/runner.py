"""Scenario helpers: process launch + assertions + report writing."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from .client import E2eError, MvdE2eClient
from .report import CaseResult, begin_report, finish_report, format_exc, record_case

# tool/multiview_e2e/mvd_e2e/runner.py → repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_DIR = REPO_ROOT / "example"


def default_base_url() -> str:
    port = os.environ.get("MVD_E2E_PORT", "9876")
    host = os.environ.get("MVD_E2E_HOST", "127.0.0.1")
    return f"http://{host}:{port}"


def default_device() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


@contextmanager
def launched_example(
    *,
    device: str | None = None,
    port: int = 9876,
    extra_defines: list[str] | None = None,
    ready_timeout: float = 120.0,
    allow_exit: bool = False,
) -> Iterator[tuple[MvdE2eClient, subprocess.Popen[str]]]:
    """Start `flutter run` for example with MVD_E2E harness, yield client, then kill."""
    device = device or default_device()
    env = os.environ.copy()
    env["MVD_E2E_PORT"] = str(port)

    defines = [
        "--dart-define=MVD_E2E=true",
        f"--dart-define=MVD_E2E_PORT={port}",
    ]
    if extra_defines:
        defines.extend(extra_defines)

    # On Windows, `flutter` is a .bat — CreateProcess needs cmd.exe.
    flutter = ["cmd", "/c", "flutter"] if sys.platform.startswith("win") else ["flutter"]
    cmd = [
        *flutter,
        "run",
        "-d",
        device,
        *defines,
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(EXAMPLE_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    client = MvdE2eClient(base_url=f"http://127.0.0.1:{port}")
    try:
        client.wait_ready(timeout=ready_timeout)
        yield client, proc
        if not allow_exit and proc.poll() is not None:
            raise E2eError(f"Flutter process exited early with code {proc.returncode}")
    finally:
        _terminate(proc)


def _harness_reachable(client: MvdE2eClient) -> bool:
    try:
        client.ping()
        return True
    except Exception:  # noqa: BLE001
        return False


def _wait_for_exit(
    client: MvdE2eClient,
    proc: subprocess.Popen[str] | None,
    *,
    timeout: float = 15.0,
) -> None:
    """Succeed when the OS process exits and/or the harness stops responding."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        proc_dead = proc is not None and proc.poll() is not None
        if proc_dead or not _harness_reachable(client):
            return
        time.sleep(0.2)
    proc_dead = proc is not None and proc.poll() is not None
    if proc_dead or not _harness_reachable(client):
        return
    raise E2eError("Expected app/harness exit, but process is still alive")


def _terminate(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        if sys.platform.startswith("win"):
            proc.terminate()
        else:
            proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception:  # noqa: BLE001
        pass


def run_scenario(
    name: str,
    fn: Callable[[MvdE2eClient], None],
    *,
    launch: bool = True,
    capture_snapshots: bool = True,
    expect_exit: bool = False,
) -> bool:
    """Run one case, append to the active report, return True on success.

    When ``expect_exit`` is True, the scenario is allowed to tear down the app
    (``close_app`` / primary cascade). Connection drops during the case are OK;
    success means the process/harness is gone afterwards.
    """
    print(f"==> {name}")
    started = time.perf_counter()
    snap_before = None
    snap_after = None
    try:
        if not launch:
            client = MvdE2eClient(default_base_url())
            client.wait_ready(timeout=30)
            if capture_snapshots:
                try:
                    snap_before = client.snapshot()
                except Exception:  # noqa: BLE001
                    snap_before = None
            try:
                fn(client)
            except AssertionError:
                raise
            except Exception:
                if not expect_exit:
                    raise
                # Mid-RPC teardown (e.g. closing primary) often resets the socket.
            if expect_exit:
                _wait_for_exit(client, None)
            elif capture_snapshots:
                try:
                    snap_after = client.snapshot()
                except Exception:  # noqa: BLE001
                    snap_after = None
        else:
            with launched_example(allow_exit=expect_exit) as (client, proc):
                if capture_snapshots:
                    try:
                        snap_before = client.snapshot()
                    except Exception:  # noqa: BLE001
                        snap_before = None
                try:
                    fn(client)
                except AssertionError:
                    raise
                except Exception:
                    if not expect_exit:
                        raise
                if expect_exit:
                    _wait_for_exit(client, proc)
                else:
                    time.sleep(0.3)
                    if proc.poll() is not None:
                        raise E2eError(
                            f"Process died during scenario (code={proc.returncode})"
                        )
                    client.assert_alive()
                    if capture_snapshots:
                        try:
                            snap_after = client.snapshot()
                        except Exception:  # noqa: BLE001
                            snap_after = None

        duration = time.perf_counter() - started
        record_case(
            CaseResult(
                name=name,
                status="passed",
                duration_sec=duration,
                snapshot_before=snap_before,
                snapshot_after=snap_after,
            )
        )
        print(f"OK  {name} ({duration:.2f}s)")
        return True
    except Exception as exc:  # noqa: BLE001 — record then fail case
        duration = time.perf_counter() - started
        err, tb = format_exc(exc)
        record_case(
            CaseResult(
                name=name,
                status="failed",
                duration_sec=duration,
                error=err,
                traceback=tb,
                snapshot_before=snap_before,
                snapshot_after=snap_after,
            )
        )
        print(f"FAIL {name} ({duration:.2f}s): {err}")
        return False


def finalize_and_exit(ok: bool) -> None:
    finish_report(write=True)
    raise SystemExit(0 if ok else 1)
