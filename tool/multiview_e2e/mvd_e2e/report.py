"""Write E2E scenario results to JSON + Markdown under results/."""

from __future__ import annotations

import json
import os
import platform
import sys
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = PACKAGE_ROOT / "results"


def results_dir() -> Path:
    raw = os.environ.get("MVD_E2E_REPORT_DIR")
    path = Path(raw) if raw else DEFAULT_RESULTS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class CaseResult:
    name: str
    status: str  # passed | failed | error
    duration_sec: float
    error: str | None = None
    traceback: str | None = None
    snapshot_before: dict[str, Any] | None = None
    snapshot_after: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class SuiteReport:
    suite: str
    started_at: str
    finished_at: str | None = None
    os_platform: str = field(default_factory=lambda: sys.platform)
    python: str = field(default_factory=lambda: sys.version.split()[0])
    host: str = field(default_factory=platform.node)
    launch: bool | None = None
    cases: list[CaseResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for c in self.cases if c.status != "passed")

    @property
    def ok(self) -> bool:
        return self.failed == 0 and len(self.cases) > 0


_active: SuiteReport | None = None
_active_paths: tuple[Path, Path] | None = None


def begin_report(suite: str, *, launch: bool | None = None) -> SuiteReport:
    global _active, _active_paths
    _active = SuiteReport(
        suite=suite,
        started_at=_now_iso(),
        launch=launch,
    )
    _active_paths = None
    return _active


def active_report() -> SuiteReport | None:
    return _active


def record_case(case: CaseResult) -> None:
    if _active is None:
        begin_report("ad-hoc")
    assert _active is not None
    _active.cases.append(case)


def finish_report(*, write: bool = True) -> Path | None:
    """Finalize active report; write JSON + MD. Returns JSON path."""
    global _active, _active_paths
    if _active is None:
        return None
    _active.finished_at = _now_iso()
    if not write:
        _active = None
        return None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_suite = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in _active.suite)
    base = results_dir() / f"{stamp}_{safe_suite}"
    json_path = Path(str(base) + ".json")
    md_path = Path(str(base) + ".md")

    payload = {
        "suite": _active.suite,
        "started_at": _active.started_at,
        "finished_at": _active.finished_at,
        "platform": _active.os_platform,
        "python": _active.python,
        "host": _active.host,
        "launch": _active.launch,
        "summary": {
            "total": len(_active.cases),
            "passed": _active.passed,
            "failed": _active.failed,
            "ok": _active.ok,
        },
        "cases": [asdict(c) for c in _active.cases],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")

    # Always refresh "latest" pointers for quick open.
    latest_json = results_dir() / "latest.json"
    latest_md = results_dir() / "latest.md"
    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    (results_dir() / "last_suite_path.txt").write_text(str(json_path) + "\n", encoding="utf-8")

    _active_paths = (json_path, md_path)
    print(f"Report: {json_path}")
    print(f"Report: {md_path}")
    _active = None
    return json_path


def write_aggregate(suite_results: list[dict[str, Any]], *, name: str = "run_all") -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = results_dir() / f"{stamp}_{name}"
    json_path = Path(str(base) + ".json")
    md_path = Path(str(base) + ".md")
    total_failed = sum(1 for s in suite_results if s.get("exit_code", 1) != 0)
    payload = {
        "suite": name,
        "started_at": suite_results[0]["started_at"] if suite_results else _now_iso(),
        "finished_at": _now_iso(),
        "platform": sys.platform,
        "host": platform.node(),
        "summary": {
            "suites": len(suite_results),
            "failed_suites": total_failed,
            "ok": total_failed == 0,
        },
        "suites": suite_results,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        f"# E2E aggregate: {name}",
        "",
        f"- finished: `{payload['finished_at']}`",
        f"- suites: **{payload['summary']['suites']}**",
        f"- failed suites: **{payload['summary']['failed_suites']}**",
        f"- ok: **{payload['summary']['ok']}**",
        "",
        "| Suite | Exit | Duration (s) | Report |",
        "|---|---:|---:|---|",
    ]
    for s in suite_results:
        report = s.get("report_json") or "—"
        lines.append(
            f"| `{s.get('name')}` | {s.get('exit_code')} | {s.get('duration_sec', 0):.2f} | `{report}` |"
        )
    lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (results_dir() / "latest_run_all.json").write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    (results_dir() / "latest_run_all.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Aggregate report: {json_path}")
    print(f"Aggregate report: {md_path}")
    return json_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# E2E report: {payload['suite']}",
        "",
        f"- started: `{payload['started_at']}`",
        f"- finished: `{payload['finished_at']}`",
        f"- platform: `{payload['platform']}` / host `{payload['host']}`",
        f"- launch app: `{payload.get('launch')}`",
        f"- total: **{summary['total']}**  passed: **{summary['passed']}**  failed: **{summary['failed']}**",
        f"- ok: **{summary['ok']}**",
        "",
        "| Case | Status | Duration (s) | Error |",
        "|---|---|---:|---|",
    ]
    for case in payload["cases"]:
        err = (case.get("error") or "").replace("|", "\\|").replace("\n", " ")
        if len(err) > 120:
            err = err[:117] + "..."
        lines.append(
            f"| `{case['name']}` | **{case['status']}** | {case['duration_sec']:.3f} | {err or '—'} |"
        )
    lines.append("")
    failed = [c for c in payload["cases"] if c["status"] != "passed"]
    if failed:
        lines.append("## Failures")
        lines.append("")
        for case in failed:
            lines.append(f"### `{case['name']}`")
            lines.append("")
            lines.append("```")
            lines.append(case.get("traceback") or case.get("error") or "")
            lines.append("```")
            lines.append("")
    return "\n".join(lines) + "\n"


def format_exc(exc: BaseException) -> tuple[str, str]:
    return str(exc), "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
