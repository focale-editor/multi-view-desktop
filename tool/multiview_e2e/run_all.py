#!/usr/bin/env python3
"""Run all multiview E2E scenario modules and write an aggregate report."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS = ROOT / "scenarios"
sys.path.insert(0, str(ROOT))

from mvd_e2e.report import results_dir, write_aggregate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multiview_desktop E2E scenarios")
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Reuse an already running example with MVD_E2E=true",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        choices=[
            "open_many",
            "close_orders",
            "dialogs_popups",
            "window_options",
            "locked_params",
            "animations_settle",
            "anim_speed_matrix",
            "cascade",
            "macos_platform_params",
        ],
        help="Subset of suites",
    )
    args = parser.parse_args()

    suites = {
        "open_many": ["test_open_many_windows.py", ["--count", "8"]],
        "close_orders": ["test_close_orders.py", []],
        "dialogs_popups": ["test_dialogs_popups.py", []],
        "window_options": ["test_window_options.py", []],
        "locked_params": ["test_locked_params.py", []],
        "animations_settle": ["test_animations_settle.py", []],
        # Full matrix is long (~11 speeds × 12 windows × open+close).
        "anim_speed_matrix": [
            "test_anim_speed_matrix.py",
            ["--count", "12"],
        ],
        "cascade": ["test_cascade.py", []],
        "macos_platform_params": ["test_macos_platform_params.py", []],
    }
    selected = args.only or list(suites)

    suite_results: list[dict] = []
    failed: list[str] = []
    for key in selected:
        script, extra = suites[key]
        cmd = [sys.executable, str(SCENARIOS / script), *extra]
        if args.no_launch:
            cmd.append("--no-launch")
        print(f"\n######## suite: {key} ########")
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, cwd=str(ROOT))
        duration = time.perf_counter() - t0
        # Child writes its own latest.json; point aggregate at that path if present.
        latest = results_dir() / "latest.json"
        marker = results_dir() / "last_suite_path.txt"
        report_path = None
        if marker.exists():
            report_path = marker.read_text(encoding="utf-8").strip() or None
        elif latest.exists():
            report_path = str(latest)
        suite_results.append(
            {
                "name": key,
                "started_at": started_at,
                "exit_code": proc.returncode,
                "duration_sec": round(duration, 3),
                "report_json": report_path,
            }
        )
        if proc.returncode != 0:
            failed.append(key)

    write_aggregate(suite_results, name="run_all")

    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print("\nAll suites passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
