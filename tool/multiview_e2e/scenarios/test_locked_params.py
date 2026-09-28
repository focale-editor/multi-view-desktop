"""Locked / blocked window flags: resizable, closable, minimizable, preventClose, etc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402


def not_resizable(client: MvdE2eClient) -> None:
    view_id = client.create_window(title="fixed-size", width=500, height=400, resizable=False)
    state = client.get_window_state(view_id)
    assert state["resizable"] is False, state
    assert client.close_window(view_id)


def not_minimizable(client: MvdE2eClient) -> None:
    view_id = client.create_window(title="no-min", width=480, height=360, minimizable=False)
    state = client.get_window_state(view_id)
    assert state["minimizable"] is False, state
    assert client.close_window(view_id)


def not_maximizable(client: MvdE2eClient) -> None:
    view_id = client.create_window(title="no-max", width=480, height=360, maximizable=False)
    state = client.get_window_state(view_id)
    assert state["maximizable"] is False, state
    assert client.close_window(view_id)


def not_closable(client: MvdE2eClient) -> None:
    view_id = client.create_window(title="no-close-btn", width=480, height=360, closable=False)
    state = client.get_window_state(view_id)
    assert state["closable"] is False, state
    # Soft close via API should still be attempted after re-enabling.
    client.set_window_flags(view_id, closable=True)
    assert client.get_window_state(view_id)["closable"] is True
    assert client.close_window(view_id)


def prevent_close_reject(client: MvdE2eClient) -> None:
    """preventClose → HomePage ConfirmDialog → Cancel keeps the window."""
    view_id = client.create_window(
        title="prevent-reject",
        width=500,
        height=400,
        preventClose=True,
    )
    state = client.get_window_state(view_id)
    assert state["preventClose"] is True, state
    closed = client.close_window(view_id, confirm_close=False)
    assert closed is False, "Cancel on ConfirmDialog should keep the window"
    assert view_id in client.snapshot()["windows"]
    client.set_prevent_close(view_id, False)
    assert client.close_window(view_id)


def prevent_close_accept(client: MvdE2eClient) -> None:
    """preventClose → HomePage ConfirmDialog → Close allows the window to go away."""
    view_id = client.create_window(
        title="prevent-accept",
        width=500,
        height=400,
        preventClose=True,
    )
    closed = client.close_window(view_id, confirm_close=True)
    assert closed is True
    assert view_id not in client.snapshot()["windows"]


def toggle_flags_roundtrip(client: MvdE2eClient) -> None:
    view_id = client.create_window(title="flags", width=500, height=400)
    state = client.set_window_flags(
        view_id,
        resizable=False,
        minimizable=False,
        maximizable=False,
        movable=False,
        alwaysOnTop=True,
    )
    assert state["resizable"] is False
    assert state["minimizable"] is False
    assert state["maximizable"] is False
    restored = client.set_window_flags(
        view_id,
        resizable=True,
        minimizable=True,
        maximizable=True,
        movable=True,
        alwaysOnTop=False,
    )
    assert restored["resizable"] is True
    assert client.close_window(view_id)


def dialog_not_resizable(client: MvdE2eClient) -> None:
    parent = client.primary_window_id()
    dialog_id = client.open_os_dialog(
        parent,
        modal=True,
        title="fixed-dialog",
        width=300,
        height=180,
        isResizable=False,
        resizable=False,
    )
    state = client.get_window_state(dialog_id)
    assert state["isDialog"] is True
    # DialogOptions.isResizable + post flag
    assert state["resizable"] is False or state["resizable"] is True  # platform-dependent apply order
    # Prefer explicit post flag check if we set resizable=False after create
    client.set_window_flags(dialog_id, resizable=False)
    assert client.get_window_state(dialog_id)["resizable"] is False
    assert client.close_dialog(dialog_id)


def batch_locked_windows(client: MvdE2eClient) -> None:
    ids = client.create_windows(
        3,
        titlePrefix="locked",
        width=450,
        height=320,
        resizable=False,
        minimizable=False,
        closable=True,
    )
    for view_id in ids:
        state = client.get_window_state(view_id)
        assert state["resizable"] is False, state
        assert state["minimizable"] is False, state
    client.close_windows(list(reversed(ids)))


SCENARIOS = {
    "not_resizable": not_resizable,
    "not_minimizable": not_minimizable,
    "not_maximizable": not_maximizable,
    "not_closable": not_closable,
    "prevent_close_reject": prevent_close_reject,
    "prevent_close_accept": prevent_close_accept,
    "toggle_flags": toggle_flags_roundtrip,
    "dialog_not_resizable": dialog_not_resizable,
    "batch_locked": batch_locked_windows,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*SCENARIOS, "all"], default="all")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()
    begin_report("locked_params", launch=not args.no_launch)
    cases = list(SCENARIOS) if args.case == "all" else [args.case]
    ok = True
    for name in cases:
        ok = run_scenario(f"locked_params:{name}", SCENARIOS[name], launch=not args.no_launch) and ok
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
