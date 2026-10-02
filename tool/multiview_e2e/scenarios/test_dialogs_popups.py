"""OS dialogs, overlay dialogs, popups and their effect on parent windows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402


def _primary(client: MvdE2eClient) -> int:
    snap = client.snapshot()
    windows = snap["windows"]
    assert windows, "expected at least the primary window"
    return int(windows[0])


def os_modal_dialog(client: MvdE2eClient) -> None:
    parent = _primary(client)
    dialog_id = client.open_os_dialog(parent, modal=True, title="modal-e2e")
    snap = client.snapshot()
    assert dialog_id in snap["dialogs"]
    assert parent in snap["windows"]
    assert client.close_dialog(dialog_id, "ok")
    client.wait_ms(150)
    snap2 = client.snapshot()
    assert dialog_id not in snap2["dialogs"]
    assert parent in snap2["windows"]
    client.assert_alive()


def os_modeless_dialog(client: MvdE2eClient) -> None:
    parent = _primary(client)
    child = client.create_window(title="host-for-dialog")
    dialog_id = client.open_os_dialog(child, modal=False, title="modeless-e2e")
    assert client.close_dialog(dialog_id)
    assert client.close_window(child)
    client.assert_alive()
    _ = parent


def nested_dialogs(client: MvdE2eClient) -> None:
    """Two modal dialogs on different windows (one modal per window limit)."""
    parent = _primary(client)
    child = client.create_window(title="nested-host")
    d1 = client.open_os_dialog(parent, modal=True, title="d1")
    d2 = client.open_os_dialog(child, modal=True, title="d2")
    assert client.close_dialog(d2)
    assert client.close_dialog(d1)
    assert client.close_window(child)
    client.assert_alive()


def overlay_dialog(client: MvdE2eClient) -> None:
    parent = _primary(client)
    client.open_overlay_dialog(parent)
    client.wait_ms(200)
    client.assert_alive()
    assert parent in client.snapshot()["windows"]


def popup_roundtrip(client: MvdE2eClient) -> None:
    parent = _primary(client)
    client.open_popup(parent)
    snap = client.snapshot()
    assert parent in snap["openPopups"]
    assert client.close_popup(parent)
    snap2 = client.snapshot()
    assert parent not in snap2["openPopups"]
    client.assert_alive()


def dialog_then_close_parent(client: MvdE2eClient) -> None:
    child = client.create_window(title="parent-with-dialog")
    dialog_id = client.open_os_dialog(child, modal=True)
    assert client.close_dialog(dialog_id)
    client.wait_ms(100)
    assert client.close_window(child)
    client.assert_alive()


SCENARIOS = {
    "os_modal": os_modal_dialog,
    "os_modeless": os_modeless_dialog,
    "nested": nested_dialogs,
    "overlay": overlay_dialog,
    "popup": popup_roundtrip,
    "dialog_then_parent": dialog_then_close_parent,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*SCENARIOS, "all"], default="all")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()
    begin_report("dialogs_popups", launch=not args.no_launch)
    cases = list(SCENARIOS) if args.case == "all" else [args.case]
    ok = True
    for name in cases:
        ok = (
            run_scenario(
                f"dialogs_popups:{name}",
                SCENARIOS[name],
                launch=not args.no_launch,
            )
            and ok
        )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
