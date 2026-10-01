"""Open and close many native dialogs that keep painting translucent circles.

Each cycle opens ``count`` modeless dialogs (default 30) on the primary window,
closes them newest-first, then waits while the process stays alive. Default is
three cycles in one process.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402

DEFAULT_COUNT = 30
DEFAULT_CYCLES = 3
# Serialized Linux destroy is about 1s per dialog (800ms drain + 200ms gap).
DRAIN_PER_DIALOG_S = 1.2


def _cycle(client: MvdE2eClient, count: int, cycle: int) -> None:
    parent = client.primary_window_id()
    ids: list[int] = []
    for i in range(count):
        width, height = (1000, 640) if i % 2 == 0 else (820, 640)
        dialog_id = client.open_os_dialog(
            parent,
            modal=False,
            title=f"circles-{cycle}-{i + 1}",
            content="circles",
            width=width,
            height=height,
            settle_ms=80,
        )
        ids.append(dialog_id)

    snap = client.snapshot()
    missing = [dialog_id for dialog_id in ids if dialog_id not in snap["dialogs"]]
    assert not missing, f"dialogs missing after open: {missing}"

    for dialog_id in reversed(ids):
        assert client.close_dialog(dialog_id, "ok", settle_ms=40), dialog_id

    deadline = time.monotonic() + count * DRAIN_PER_DIALOG_S
    while time.monotonic() < deadline:
        client.assert_alive()
        time.sleep(1)

    leftover = client.snapshot()["dialogs"]
    assert not leftover, f"leftover dialogs: {leftover}"
    client.assert_alive()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()

    begin_report("circles_dialogs", launch=not args.no_launch)

    def scenario(client: MvdE2eClient) -> None:
        client.timeout = max(client.timeout, 120.0)
        for cycle in range(1, args.cycles + 1):
            _cycle(client, args.count, cycle)

    ok = run_scenario(
        f"circles_dialogs(count={args.count}, cycles={args.cycles})",
        scenario,
        launch=not args.no_launch,
    )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
