# 04 — FlutterEngine с несколькими View / GtkWindow

## Целевая архитектура (single-engine multi-view)

```
                    FlEngine (1)
                   /    |     \
            FlView0  FlView1  FlView2
               |        |        |
           GtkWin0  GtkWin1  GtkWin2
               |        |        |
            Dart ViewCollection
               View0  View1  View2
```

Создание secondary:

1. Native: new `GtkWindow` + `fl_view_new_for_engine`.
2. Engine: `AddView` → новый `FlutterViewId`.
3. Dart: увидеть view в `platformDispatcher.views` (metrics change).
4. Dart: добавить `View(view: ..., child: ...)` в `ViewCollection`.
5. Show window после first-frame (избежать blank flash).

Уничтожение secondary (идеал):

1. User close / API close.
2. Soft-close hooks (prevent/confirm).
3. Dart убирает `View` из дерева.
4. Raster перестаёт рисовать view.
5. `RemoveView` + await safe callback.
6. Destroy `GtkWindow` / `FlView`.
7. Registry cleanup; app живёт, пока есть окна.

## Official windowing vs ViewCollection plugins

| | Official windowing API | `multiview_desktop` | `desktop_multi_window` |
|--|------------------------|---------------------|------------------------|
| Engine | 1 shared | 1 shared | N engines |
| Isolate | 1 | 1 | N |
| Channel | main + flag | pub package | pub package |
| Native API | RegularWindowController… | custom runner hooks | per-window FlView |
| Linux close | всё ещё баги | deferred destroy + X handler | краши / reuse forks |

## GL compositing strategies (Linux)

### Historical (GTK3 GtkGLArea era)

- Primary window owns «main» GL context.
- Secondary views: copy pixels from primary render.
- Destroy primary first → catastrophic.
- Comment from robert-ancell: *«what happens when first window destroyed? keep it around (hide)»*.

### Current direction (EGL)

- Flutter own EGL context (independent of GTK windows).
- Wayland: EGLImage share to GTK contexts.
- X11: CPU copy (no mix EGL/GLX easily).
- Platform thread has separate GL context for shader setup (#183715).

Даже с EGL close race **не исчез** полностью: texture/draw idle vs dispose (#186848), clear_current vs GTK (#192137), XWayland NVIDIA (#186577).

## Поведение при закрытии: матрица

| Сценарий | Ожидание | Частый факт на Linux |
|----------|----------|----------------------|
| Close secondary, primary remains | OK | Race / BadAccess / RemoveView noise |
| Close primary, secondaries remain | Hard | Shared context / app quit |
| Rapid open/close | OK | mutex/draw UAF (#186848 fixed partially) |
| Hide secondary | OK | Самый безопасный путь |
| Destroy all then quit | OK | Implicit view RemoveView warnings |

## Сравнение с Windows / macOS

| | Windows | macOS | Linux |
|--|---------|-------|-------|
| Surface destroy sync | HWND + D3D/OpenGL carefully latched | NSWindow/FlutterViewController mature | GTK destroy sync + async raster |
| RemoveView | Blocking latch in embedder | Relatively robust | Fire-and-forget in FlView dispose |
| Multi-view age | Active | Active | Later + GTK GL constraints |
| Session split | N/A | N/A | Wayland vs X11 vs XWayland |

Поэтому «на Mac/Win работает, на Linux нет» — ожидаемо, не обязательно баг приложения.

## ViewCollection нюансы

- Два `View` с одним `FlutterView` одновременно — запрещено (`GlobalObjectKey`).
- После RemoveView native view_id мёртв — Dart должен убрать виджет **до** или согласованно с destroy.
- Если native destroy раньше Dart unmount → frames в никуда / use-after-free.
- Если Dart unmount раньше, но native surface ещё жив 100ms hidden — обычно OK.

`multiview_desktop` комментарии в `on_delete` описывают именно этот контракт (100 ms ≈ 6 frames).
