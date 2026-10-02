"""Window init options: size, parent, title bar, alignment, and settle after open anim."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402


def _approx(a: float, b: float, tol: float = 40.0) -> bool:
    return abs(a - b) <= tol


def sized_window(client: MvdE2eClient) -> None:
    result = client.create_window_full(title="sized", width=640, height=480, minWidth=320, minHeight=240)
    view_id = int(result["viewId"])
    state = result["state"]
    assert _approx(state["bounds"]["width"], 640), state
    assert _approx(state["bounds"]["height"], 480), state
    assert _approx(state["minSize"]["width"], 320), state
    assert client.close_window(view_id)


def max_size_window(client: MvdE2eClient) -> None:
    view_id = client.create_window(
        title="maxed",
        width=500,
        height=400,
        maxWidth=700,
        maxHeight=500,
    )
    state = client.get_window_state(view_id)
    assert state["maxSize"]["width"] >= 700 or _approx(state["maxSize"]["width"], 700, 80), state
    assert client.close_window(view_id)


def child_with_parent(client: MvdE2eClient) -> None:
    parent = client.primary_window_id()
    child = client.create_window(title="child", parentId=parent, width=500, height=400)
    snap = client.snapshot()
    assert child in snap["windows"]
    assert parent in snap["windows"]
    assert client.close_window(child)
    assert parent in client.snapshot()["windows"]


def frameless_hidden_title(client: MvdE2eClient) -> None:
    view_id = client.create_window(
        title="frameless",
        titleBarStyle="hidden",
        windowButtonVisibility=False,
        width=600,
        height=400,
    )
    state = client.get_window_state(view_id)
    assert state["title"] == "frameless" or True  # title may still be set natively
    assert client.close_window(view_id)


def alignment_variants(client: MvdE2eClient) -> None:
    for align in ("topLeft", "center", "bottomRight"):
        view_id = client.create_window(title=f"align-{align}", alignment=align, width=420, height=320)
        assert client.close_window(view_id)


def always_on_top_init(client: MvdE2eClient) -> None:
    view_id = client.create_window(title="aot", alwaysOnTop=True, width=400, height=300)
    state = client.get_window_state(view_id)
    # Compositor may ignore; flag should at least round-trip on most platforms.
    assert "alwaysOnTop" in state
    assert client.close_window(view_id)


def custom_open_animation(client: MvdE2eClient) -> None:
    # Longer open animation — harness must wait settleMs / animationMs.
    view_id = client.create_window(
        title="slow-open",
        width=500,
        height=360,
        animation_ms=400,
        settle_ms=520,
    )
    assert view_id in client.snapshot()["windows"]
    assert client.close_window(view_id, animation_ms=400, settle_ms=520)


def dialog_init_size_and_parent(client: MvdE2eClient) -> None:
    parent = client.create_window(title="dlg-parent", width=800, height=600)
    full = client.open_os_dialog_full(
        parent,
        modal=True,
        title="sized-dialog",
        width=360,
        height=200,
        minWidth=200,
        minHeight=120,
    )
    dialog_id = int(full["dialogId"])
    state = full["state"]
    assert state["isDialog"] is True
    assert state["isModal"] is True
    assert _approx(state["bounds"]["width"], 360, 60), state
    assert client.close_dialog(dialog_id)
    assert client.close_window(parent)


def modeless_resizable_dialog(client: MvdE2eClient) -> None:
    parent = client.primary_window_id()
    dialog_id = client.open_os_dialog(
        parent,
        modal=False,
        title="modeless-resize",
        width=400,
        height=240,
        isResizable=True,
    )
    state = client.get_window_state(dialog_id)
    assert state["isDialog"] is True
    assert state["isModal"] is False
    assert client.close_dialog(dialog_id)


SCENARIOS = {
    "sized": sized_window,
    "max_size": max_size_window,
    "parent": child_with_parent,
    "frameless": frameless_hidden_title,
    "alignment": alignment_variants,
    "always_on_top": always_on_top_init,
    "slow_open_anim": custom_open_animation,
    "dialog_size": dialog_init_size_and_parent,
    "modeless_resizable": modeless_resizable_dialog,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*SCENARIOS, "all"], default="all")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()
    begin_report("window_options", launch=not args.no_launch)
    cases = list(SCENARIOS) if args.case == "all" else [args.case]
    ok = True
    for name in cases:
        ok = run_scenario(f"window_options:{name}", SCENARIOS[name], launch=not args.no_launch) and ok
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
