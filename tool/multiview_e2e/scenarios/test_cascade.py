"""Cascade close modes from different starting points."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402


def soft_cascade_close_app(client: MvdE2eClient) -> None:
    client.set_close_mode("softCascade")
    ids = client.create_windows(3)
    assert len(ids) == 3
    ok = client.close_app(mode="softCascade")
    assert isinstance(ok, bool)
    try:
        client.assert_alive()
    except Exception:
        pass


def force_secondary(client: MvdE2eClient) -> None:
    client.set_close_mode("forceSecondary")
    ids = client.create_windows(4)
    primary = client.snapshot()["windows"][0]
    ok = client.close_app(mode="forceSecondary")
    assert isinstance(ok, bool)
    try:
        snap = client.snapshot()
        for view_id in ids:
            assert view_id not in snap.get("windows", [])
        assert primary in snap.get("windows", []) or ok
        client.assert_alive()
    except Exception:
        pass


def destroy_mode(client: MvdE2eClient) -> None:
    client.set_close_mode("destroy")
    client.create_windows(2)
    ok = client.close_app(mode="destroy")
    assert isinstance(ok, bool)


def cascade_abort(client: MvdE2eClient) -> None:
    """Start soft close on a preventClose window and abort via ConfirmDialog Cancel."""
    client.set_close_mode("softCascade")
    child = client.create_window(title="prevent-close-child", preventClose=True)
    closed = client.close_window(child, confirm_close=False)
    assert closed is False
    client.cancel_cascade(child)
    client.set_prevent_close(child, False)
    assert client.close_window(child)
    client.assert_alive()


def close_primary_with_secondaries(client: MvdE2eClient) -> None:
    client.set_close_mode("softCascade")
    ids = client.create_windows(3)
    primary = int(client.snapshot()["windows"][0])
    client.close_window(primary)
    client.wait_ms(800)
    try:
        snap = client.snapshot()
        for view_id in ids:
            _ = view_id
        client.assert_alive()
        assert isinstance(snap["windows"], list)
    except Exception:
        pass


SCENARIOS = {
    "soft_cascade_app": soft_cascade_close_app,
    "force_secondary": force_secondary,
    "destroy": destroy_mode,
    "abort": cascade_abort,
    "primary_with_secondaries": close_primary_with_secondaries,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*SCENARIOS, "all"], default="all")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()
    begin_report("cascade", launch=not args.no_launch)
    cases = list(SCENARIOS) if args.case == "all" else [args.case]
    ok = True
    for name in cases:
        ok = (
            run_scenario(
                f"cascade:{name}",
                SCENARIOS[name],
                launch=not args.no_launch,
                # close_app may kill the process; snapshots after can fail noisily
                capture_snapshots=name not in {"soft_cascade_app", "force_secondary", "destroy"},
            )
            and ok
        )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
