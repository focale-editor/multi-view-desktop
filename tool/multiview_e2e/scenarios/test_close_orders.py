"""Different close orders for secondary windows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mvd_e2e import MvdE2eClient, begin_report, finalize_and_exit, run_scenario  # noqa: E402


def _create(client: MvdE2eClient, n: int = 5) -> list[int]:
    return client.create_windows(n)


def close_fifo(client: MvdE2eClient) -> None:
    ids = _create(client)
    for view_id in ids:
        assert client.close_window(view_id)
    client.assert_alive()


def close_lifo(client: MvdE2eClient) -> None:
    ids = _create(client)
    for view_id in reversed(ids):
        assert client.close_window(view_id)
    client.assert_alive()


def close_interleaved(client: MvdE2eClient) -> None:
    ids = _create(client, 6)
    order = [ids[0], ids[-1], ids[2], ids[1], ids[4], ids[3]]
    for view_id in order:
        assert client.close_window(view_id)
    client.assert_alive()


def close_while_siblings_open(client: MvdE2eClient) -> None:
    ids = _create(client, 4)
    assert client.close_window(ids[1])
    assert client.close_window(ids[2])
    snap = client.snapshot()
    assert ids[0] in snap["windows"]
    assert ids[3] in snap["windows"]
    assert client.close_window(ids[0])
    assert client.close_window(ids[3])
    client.assert_alive()


SCENARIOS = {
    "fifo": close_fifo,
    "lifo": close_lifo,
    "interleaved": close_interleaved,
    "middle_first": close_while_siblings_open,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*SCENARIOS, "all"], default="all")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()

    begin_report("close_orders", launch=not args.no_launch)
    cases = list(SCENARIOS) if args.case == "all" else [args.case]
    ok = True
    for name in cases:
        ok = (
            run_scenario(
                f"close_orders:{name}",
                SCENARIOS[name],
                launch=not args.no_launch,
            )
            and ok
        )
    finalize_and_exit(ok)


if __name__ == "__main__":
    main()
