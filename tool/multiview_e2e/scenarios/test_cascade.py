"""Cascade close modes from different starting points."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402

# Cases that tear down the whole app — exit is the success signal.
EXPECT_EXIT = frozenset(
    {
        "soft_cascade_app",
        "destroy",
        "primary_with_secondaries",
    }
)


def soft_cascade_close_app(client: MvdE2eClient) -> None:
    client.set_close_mode("softCascade")
    ids = client.create_windows(3)
    assert len(ids) == 3
    ok = client.close_app(mode="softCascade")
    assert isinstance(ok, bool)


def force_secondary(client: MvdE2eClient) -> None:
    """forceSecondary force-closes children; preventClose primary soft-close → Cancel keeps app."""
    primary = client.primary_window_id()
    client.set_close_mode("forceSecondary")
    client.set_prevent_close(primary, True)

    children = [
        client.create_window(
            title=f"force-sec-{i}",
            parentId=primary,
            width=420,
            height=320,
            content="plain",
        )
        for i in range(3)
    ]
    assert len(children) == 3
    for child_id in children:
        assert child_id in client.snapshot()["windows"]

    # Force-close descendants, then soft-close primary → ConfirmDialog Cancel.
    # Timeout must cover force-closing every child before the primary dialog appears.
    closed_all = client.close_app(
        mode="forceSecondary",
        confirm_close=False,
        confirm_timeout_ms=30000,
    )
    assert closed_all is False

    snap = client.snapshot()
    for child_id in children:
        assert child_id not in snap["windows"], snap
    assert primary in snap["windows"], snap
    client.assert_alive()


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
    """Closing primary under softCascade tears down secondaries and the app."""
    client.set_close_mode("softCascade")
    ids = client.create_windows(3)
    assert len(ids) == 3
    primary = int(client.snapshot()["windows"][0])
    # Soft-close of primary may reset the socket mid-RPC as the process exits.
    client.close_window(primary)


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
        expect_exit = name in EXPECT_EXIT
        ok = (
            run_scenario(
                f"cascade:{name}",
                SCENARIOS[name],
                # Exit cases need a fresh process; --no-launch cannot revive a dead app.
                launch=True if expect_exit else not args.no_launch,
                capture_snapshots=not expect_exit,
                expect_exit=expect_exit,
            )
            and ok
        )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
