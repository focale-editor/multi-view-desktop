"""Open/close many windows across animation durations (100ms … 5s).

Sweeps animationMs from 100 to 5000 with step 500. Each step opens ``count``
windows (default 12), closes LIFO, and asserts the process stays alive.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402

# 100, 600, …, 4600, and include 5000 (end of range).
ANIM_MS_STEPS = list(range(100, 5000, 500)) + [5000]
SETTLE_PAD_MS = 120
DEFAULT_COUNT = 12


def settle_ms_for(animation_ms: int) -> int:
    return animation_ms + SETTLE_PAD_MS


def _bump_timeout(client: MvdE2eClient, *, count: int, settle_ms: int) -> None:
    # Sequential create/close: count * settle each way, plus headroom.
    need = count * (settle_ms / 1000.0) + 120.0
    client.timeout = max(client.timeout, need)


def open_close_cycle(
    client: MvdE2eClient,
    *,
    animation_ms: int,
    count: int,
) -> None:
    settle = settle_ms_for(animation_ms)
    _bump_timeout(client, count=count, settle_ms=settle)

    before = client.snapshot()
    primary = set(before["windows"])

    ids = client.create_windows(
        count,
        titlePrefix=f"anim{animation_ms}",
        width=420,
        height=300,
        content="plain",
        animation_ms=animation_ms,
        settle_ms=settle,
    )
    assert len(ids) == count, ids

    for view_id in reversed(ids):
        ok = client.close_window(
            view_id,
            animation_ms=animation_ms,
            settle_ms=settle,
        )
        assert ok, f"failed to close {view_id} at anim={animation_ms}ms"

    after = client.snapshot()
    leftover = set(after["windows"]) - primary
    assert not leftover, f"leftover windows at anim={animation_ms}ms: {leftover}"
    client.assert_alive()


def matrix_all_speeds(client: MvdE2eClient, *, count: int = DEFAULT_COUNT) -> None:
    for anim_ms in ANIM_MS_STEPS:
        print(f"  animationMs={anim_ms}, windows={count}", flush=True)
        open_close_cycle(client, animation_ms=anim_ms, count=count)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open/close N windows for each animation duration in the matrix",
    )
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument(
        "--anim-ms",
        type=int,
        choices=ANIM_MS_STEPS,
        default=None,
        help="Run a single animationMs step instead of the full matrix",
    )
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()

    begin_report("anim_speed_matrix", launch=not args.no_launch)

    if args.anim_ms is not None:
        ok = run_scenario(
            f"anim_speed_matrix:anim={args.anim_ms}ms(count={args.count})",
            lambda c: open_close_cycle(c, animation_ms=args.anim_ms, count=args.count),
            launch=not args.no_launch,
        )
    else:
        ok = run_scenario(
            f"anim_speed_matrix:all(count={args.count})",
            lambda c: matrix_all_speeds(c, count=args.count),
            launch=not args.no_launch,
        )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
