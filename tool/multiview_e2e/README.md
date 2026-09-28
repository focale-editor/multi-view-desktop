# Multiview E2E (script tests)

Standard `flutter test` cannot drive real OS multi-window lifecycle. These
scripts talk to an optional HTTP harness in the **example** app.

## Design

| Layer | Role |
|-------|------|
| `example/lib/e2e/e2e_harness.dart` | Thin HTTP server (`GET /health`, `POST /rpc`) |
| `example/lib/e2e/e2e_handlers.dart` | **Injectable** method map (built in `main`) |
| `example/lib/e2e/e2e_host.dart` | Registers `BuildContext` per view for dialogs |
| `tool/multiview_e2e/` | Python client + scenarios |

Handlers are **not** hard-coded inside the server. `main.dart` passes them:

```dart
await maybeStartE2eHarness(
  handlers: buildExampleE2eHandlers(ExampleE2eHandlerDeps(contexts: e2eStore)),
);
```

Swap or merge the map to customize commands without touching the transport.

## Enable harness

```bash
cd example
flutter run -d linux \
  --dart-define=MVD_E2E=true \
  --dart-define=MVD_E2E_PORT=9876
```

macOS / Windows: `-d macos` / `-d windows`.

## Run scenarios

**A. Scripts launch Flutter themselves** (slow, isolated):

```bash
cd tool/multiview_e2e
python3 run_all.py
python3 scenarios/test_open_many_windows.py --count 10
python3 scenarios/test_close_orders.py --case interleaved
python3 scenarios/test_dialogs_popups.py --case popup
python3 scenarios/test_window_options.py
python3 scenarios/test_locked_params.py
python3 scenarios/test_animations_settle.py
python3 scenarios/test_cascade.py --case abort
```

**B. App already running** (fast iteration):

```bash
# terminal 1: flutter run ... --dart-define=MVD_E2E=true
# terminal 2:
python3 run_all.py --no-launch
python3 scenarios/test_open_many_windows.py --no-launch --count 12
```

## RPC methods (default map)

| Method | Purpose |
|--------|---------|
| `ping` / `snapshot` | Liveness + window/dialog/popup ids |
| `create_window` / `create_windows` | Secondary windows |
| `close_window` / `close_windows` | Soft close; optional `confirmClose` for HomePage UI |
| `answer_close_confirm` | Accept/reject prevent-close ConfirmDialog |
| `set_prevent_close` / `cancel_cascade` | Soft-close / cascade control |
| `set_close_mode` / `close_app` | `CloseMode` + app-level cascade |
| `open_os_dialog` / `close_dialog` | Native dialog windows |
| `open_overlay_dialog` | In-window Material dialog |
| `open_popup` / `close_popup` | Native popup via `PopupView` |
| `get_window_state` / `set_window_flags` | Bounds + locked flags |
| `wait_ms` / `wait_open_settle` / `wait_close_settle` | Pace open/close animations |

### Animation settle

Example app uses ~150ms open/close fade. Handlers wait **animation + 120ms pad**
(default ~270ms) after create/close unless you pass:

- `animationMs` — soft animation override forwarded to the API
- `settleMs` — explicit wait after the operation

Python client defaults: `open_settle_ms` / `close_settle_ms` = 270.

### Create / dialog params (RPC)

Windows: `title`, `width`/`height`, `minWidth`/`minHeight`, `maxWidth`/`maxHeight`,
`alignment`, `titleBarStyle` (`normal`|`hidden`), `windowButtonVisibility`,
`alwaysOnTop`, `fullScreen`, `parentId`, `content` (`home` default | `plain`),
plus post-create flags
`resizable`, `movable`, `minimizable`, `maximizable`, `closable`, `preventClose`.

Default window content is the real example `HomePage`. When `preventClose` is set,
soft close shows ConfirmDialog — pass `confirmClose: true|false` on `close_window`.

Dialogs: same sizes + `modal`, `isResizable`, `showOnInit`, `parentId` (required).

Manual call:

```bash
curl -s http://127.0.0.1:9876/health
curl -s -X POST http://127.0.0.1:9876/rpc \
  -H 'Content-Type: application/json' \
  -d '{"method":"snapshot","params":{}}'
```

## Reports

Each scenario suite writes:

| File | Content |
|------|---------|
| `results/<UTC>_<suite>.json` | Full machine-readable report (cases, durations, errors, snapshots) |
| `results/<UTC>_<suite>.md` | Human-readable summary |
| `results/latest.json` / `latest.md` | Copy of the last suite report |
| `results/latest_run_all.json` / `.md` | Aggregate when using `run_all.py` |

Override directory with `MVD_E2E_REPORT_DIR=/path/to/dir`.

## Notes

- Cascade scenarios that call `close_app` may exit the process; suites launch a fresh app per case when not using `--no-launch`.
- On Linux, these scripts are meant to catch the secondary-window close race (process dies / harness stops responding).
- No extra Python dependencies (`requirements.txt` is empty on purpose).
