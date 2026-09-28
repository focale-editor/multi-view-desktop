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

    cmd = [
        "flutter",
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
        if proc.poll() is not None:
            raise E2eError(f"Flutter process exited early with code {proc.returncode}")
    finally:
        _terminate(proc)


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
) -> bool:
    """Run one case, append to the active report, return True on success."""
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
            fn(client)
            if capture_snapshots:
                try:
                    snap_after = client.snapshot()
                except Exception:  # noqa: BLE001
                    snap_after = None
        else:
            with launched_example() as (client, proc):
                if capture_snapshots:
                    try:
                        snap_before = client.snapshot()
                    except Exception:  # noqa: BLE001
                        snap_before = None
                fn(client)
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
