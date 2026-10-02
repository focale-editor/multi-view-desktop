"""macOS dock / last-window platform params (example defaults vs quit mode).

Cascade exit cases override these via dart-define + env; this suite covers the
params themselves. Skipped on non-macOS.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402

# Match example/lib/main.dart defaults (stay in dock).
STAY_ALIVE_DEFINES = [
    "--dart-define=MVD_E2E_CLOSE_APP_AFTER_LAST=false",
    "--dart-define=MVD_E2E_SAVE_LAST_WINDOW=true",
]
STAY_ALIVE_ENV = {
    "MVD_E2E_CLOSE_APP_AFTER_LAST": "false",
    "MVD_E2E_SAVE_LAST_WINDOW": "true",
}

# Opposite: last window close terminates the process.
QUIT_DEFINES = [
    "--dart-define=MVD_E2E_CLOSE_APP_AFTER_LAST=true",
    "--dart-define=MVD_E2E_SAVE_LAST_WINDOW=false",
]
QUIT_ENV = {
    "MVD_E2E_CLOSE_APP_AFTER_LAST": "true",
    "MVD_E2E_SAVE_LAST_WINDOW": "false",
}


def _assert_macos_params(
    client: MvdE2eClient,
    *,
    close_after_last: bool,
    save_last: bool,
) -> None:
    snap = client.snapshot()
    params = snap.get("macosParams") or {}
    assert params.get("closeAppAfterLastWindowClosed") is close_after_last, snap
    assert params.get("saveLastWindowToReopen") is save_last, snap


def stay_alive_after_close_app(client: MvdE2eClient) -> None:
    """Example defaults: soft closeApp leaves the process alive (dock)."""
    _assert_macos_params(client, close_after_last=False, save_last=True)
    client.set_close_mode("softCascade")
    client.create_windows(2)
    ok = client.close_app(mode="softCascade")
    assert isinstance(ok, bool)
    # Native may still be tearing down; give hide/reopen path a beat.
    time.sleep(0.8)
    client.assert_alive()
    snap = client.snapshot()
    windows = snap.get("windows") or []
    # Last root may remain hidden in the stack for dock reopen.
    if windows:
        state = client.get_window_state(int(windows[0]))
        assert state.get("visible") is False, state


def stay_alive_close_primary(client: MvdE2eClient) -> None:
    """Closing the primary under softCascade with saveLast keeps the process."""
    _assert_macos_params(client, close_after_last=False, save_last=True)
    client.set_close_mode("softCascade")
    client.create_windows(2)
    primary = int(client.snapshot()["windows"][0])
    try:
        client.close_window(primary)
    except Exception:  # noqa: BLE001 — hide path may drop mid-RPC
        pass
    time.sleep(0.8)
    client.assert_alive()


def quit_after_close_app(client: MvdE2eClient) -> None:
    """With quit-friendly params, soft closeApp should terminate."""
    _assert_macos_params(client, close_after_last=True, save_last=False)
    client.set_close_mode("softCascade")
    client.create_windows(2)
    ok = client.close_app(mode="softCascade")
    assert isinstance(ok, bool)


SCENARIOS = {
    "stay_alive_close_app": stay_alive_after_close_app,
    "stay_alive_close_primary": stay_alive_close_primary,
    "quit_close_app": quit_after_close_app,
}

OVERRIDES = {
    "stay_alive_close_app": (STAY_ALIVE_DEFINES, STAY_ALIVE_ENV),
    "stay_alive_close_primary": (STAY_ALIVE_DEFINES, STAY_ALIVE_ENV),
    "quit_close_app": (QUIT_DEFINES, QUIT_ENV),
}

EXPECT_EXIT = frozenset({"quit_close_app"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*SCENARIOS, "all"], default="all")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()

    if sys.platform != "darwin":
        begin_report("macos_platform_params", launch=False)
        print("SKIP macos_platform_params (not darwin)")
        finalize_and_exit(True)
        return

    begin_report("macos_platform_params", launch=not args.no_launch)
    cases = list(SCENARIOS) if args.case == "all" else [args.case]
    ok = True
    for name in cases:
        expect_exit = name in EXPECT_EXIT
        defines, env = OVERRIDES[name]
        # Always launch — defines/env must match the case; --no-launch cannot switch them.
        ok = (
            run_scenario(
                f"macos_platform_params:{name}",
                SCENARIOS[name],
                launch=True,
                capture_snapshots=not expect_exit,
                expect_exit=expect_exit,
                extra_defines=list(defines),
                extra_env=dict(env),
            )
            and ok
        )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
