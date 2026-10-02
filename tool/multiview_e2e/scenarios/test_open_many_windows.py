"""Open many independent secondary windows, then close LIFO."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402


def scenario(client: MvdE2eClient, count: int = 10) -> None:
    before = client.snapshot()
    primary_windows = set(before["windows"])

    ids = client.create_windows(count)
    assert len(ids) == count, ids
    snap = client.snapshot()
    assert len(snap["windows"]) >= len(primary_windows) + count

    # Close newest → oldest (close_window already waits close animation settle)
    for view_id in reversed(ids):
        ok = client.close_window(view_id)
        assert ok, f"failed to close {view_id}"

    after = client.snapshot()
    remaining_extra = set(after["windows"]) - primary_windows
    assert not remaining_extra, f"leftover windows: {remaining_extra}"
    client.assert_alive()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--no-launch", action="store_true", help="App already running with harness")
    args = parser.parse_args()
    begin_report("open_many_windows", launch=not args.no_launch)
    ok = run_scenario(
        f"open_many_windows(count={args.count})",
        lambda c: scenario(c, args.count),
        launch=not args.no_launch,
    )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
