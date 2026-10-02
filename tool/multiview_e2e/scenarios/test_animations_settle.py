"""Animation settle: open/close windows, dialogs, popups with explicit timings."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402


def window_open_close_default_anim(client: MvdE2eClient) -> None:
    t0 = time.perf_counter()
    view_id = client.create_window(title="anim-default", width=500, height=360)
    open_elapsed = time.perf_counter() - t0
    # Server waits ~270ms settle; wall time should reflect that.
    assert open_elapsed >= 0.2, f"open settled too fast: {open_elapsed:.3f}s"
    assert view_id in client.snapshot()["windows"]
    t1 = time.perf_counter()
    assert client.close_window(view_id)
    close_elapsed = time.perf_counter() - t1
    assert close_elapsed >= 0.2, f"close settled too fast: {close_elapsed:.3f}s"


def window_slow_then_fast(client: MvdE2eClient) -> None:
    slow = client.create_window(title="slow", width=500, height=360, animation_ms=500, settle_ms=620)
    fast = client.create_window(title="fast", width=500, height=360, animation_ms=50, settle_ms=80)
    assert slow in client.snapshot()["windows"]
    assert fast in client.snapshot()["windows"]
    assert client.close_window(fast, animation_ms=50, settle_ms=80)
    assert client.close_window(slow, animation_ms=500, settle_ms=620)


def dialog_modal_vs_modeless_settle(client: MvdE2eClient) -> None:
    parent = client.primary_window_id()
    modal = client.open_os_dialog(parent, modal=True, title="modal-anim", width=320, height=200)
    assert client.close_dialog(modal)
    modeless = client.open_os_dialog(parent, modal=False, title="modeless-anim", width=320, height=200)
    assert client.close_dialog(modeless)


def popup_anim_roundtrip(client: MvdE2eClient) -> None:
    parent = client.primary_window_id()
    client.open_popup(parent, animation_ms=200, settle_ms=320)
    assert parent in client.snapshot()["openPopups"]
    assert client.close_popup(parent, animation_ms=200, settle_ms=320)
    assert parent not in client.snapshot()["openPopups"]


def staggered_batch_with_anim(client: MvdE2eClient) -> None:
    ids = client.create_windows(4, titlePrefix="stag", width=420, height=300, animation_ms=150)
    assert len(ids) == 4
    # Close LIFO with close animation settle baked into RPC.
    assert all(r["closed"] for r in client.close_windows(list(reversed(ids))))


def mixed_types_sequence(client: MvdE2eClient) -> None:
    parent = client.create_window(title="host", width=700, height=500)
    dialog = client.open_os_dialog(parent, modal=True, title="d", width=300, height=180)
    client.open_popup(parent)
    assert parent in client.snapshot()["openPopups"]
    assert client.close_popup(parent)
    assert client.close_dialog(dialog)
    sibling = client.create_window(title="sib", parentId=parent, width=400, height=300)
    assert client.close_window(sibling)
    assert client.close_window(parent)


SCENARIOS = {
    "default_anim": window_open_close_default_anim,
    "slow_fast": window_slow_then_fast,
    "dialog_settle": dialog_modal_vs_modeless_settle,
    "popup_anim": popup_anim_roundtrip,
    "staggered_batch": staggered_batch_with_anim,
    "mixed_types": mixed_types_sequence,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*SCENARIOS, "all"], default="all")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()
    begin_report("animations_settle", launch=not args.no_launch)
    cases = list(SCENARIOS) if args.case == "all" else [args.case]
    ok = True
    for name in cases:
        ok = (
            run_scenario(f"animations_settle:{name}", SCENARIOS[name], launch=not args.no_launch)
            and ok
        )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
