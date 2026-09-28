# 05 — Проблемы и баги (каталог)

## Симптомы → вероятная причина

| Симптом | Вероятная причина | Типичная среда |
|---------|-------------------|----------------|
| `BadAccess` GLX minor 26 | SwapBuffers/MakeCurrent на мёртвом drawable | X11 / XWayland |
| `GLXBadDrawable` | То же, следующий request в цепочке | X11 |
| GDK `_exit(1)` после X error | Default GDK handler | X11 |
| `FlutterEngineRemoveView` / implicit view | Попытка RemoveView id=0 или wrong view | Любая |
| `g_object_weak_unref: couldn't find weak ref` | Двойной dispose / broken GObject lifetime | GTK teardown |
| `Failed to cleanup compositor shaders` | Нет current GL context при dispose | X11/Wayland |
| `epoxy_get_proc_address` assert | GL calls без context | X11 |
| SIGSEGV `gdk_gl_texture_from_surface` | Draw после invalidation surface | Wayland |
| `g_mutex_clear` on uninitialised mutex | FlView destroyed mid-draw | Rapid close |
| `Failed to setup compositor shaders` | Engine context held on wrong thread | Multi-window create |
| Blank / black window + compositor asserts | NVIDIA PRIME / context create fail | NVIDIA hybrid |

## Upstream issues (ядро)

### Close / RemoveView / teardown

| ID | Суть |
|----|------|
| [flutter#164564](https://github.com/flutter/flutter/issues/164564) | RemoveView callback слишком рано — surface ещё в raster queue |
| [leanflutter/window_manager#581](https://github.com/leanflutter/window_manager/issues/581) | Ubuntu secondary close → RemoveView implicit + Lost connection |
| [leanflutter/window_manager#585](https://github.com/leanflutter/window_manager/issues/585) | Fedora 44 exit: RemoveView + epoxy assert |
| [kodjodevf/mangayomi#752](https://github.com/kodjodevf/mangayomi/issues/752) | Wayland WebView window close → RemoveView + SIGSEGV |
| [flet-dev/flet#4947](https://github.com/flet-dev/flet/issues/4947) | RemoveView implicit на Linux Mint |
| [flutter#182192](https://github.com/flutter/flutter/issues/182192) | Wayland VRAM/leak + RemoveView noise на exit |

### GLX / X11 / NVIDIA

| ID | Суть |
|----|------|
| [flutter#186577](https://github.com/flutter/flutter/issues/186577) | RegularWindowController / multiple_windows crash GLX BadAccess на Ubuntu 26.04 + NVIDIA XWayland |
| [flutter#169470](https://github.com/flutter/flutter/issues/169470) | Startup freeze/crash X11; XInitThreads; NVIDIA drivers |
| [flutter#184259](https://github.com/flutter/flutter/issues/184259) | NVIDIA PRIME offload: OpenGL context fail |
| [flutter#170937](https://github.com/flutter/flutter/issues/170937) | Blank window / XInitThreads missing |
| [wang-bin/fvp#271](https://github.com/wang-bin/fvp/issues/271) | BadAccess при GL cleanup на X11 (не multi-window, но тот же класс) |

### Multi-view tracking / architecture

| ID | Суть |
|----|------|
| [flutter#138178](https://github.com/flutter/flutter/issues/138178) | Linux embedder multi-view tracking |
| [flutter#30701](https://github.com/flutter/flutter/issues/30701) | Desktop multi-window umbrella |
| [flutter#144806](https://github.com/flutter/flutter/issues/144806) | Multi-view embedder APIs |
| [flutter#94804](https://github.com/flutter/flutter/issues/94804) | GTK4 migration (не fix) |

### Fixes already landed (частично)

| PR | Что чинит |
|----|-----------|
| [#54018](https://github.com/flutter/engine/pull/54018) | fl_engine_add/remove_view |
| [#172090](https://github.com/flutter/flutter/pull/172090) | FB compositing; развязка Flutter/GTK GL |
| [#172330](https://github.com/flutter/flutter/pull/172330) | Own EGL context |
| [#183715](https://github.com/flutter/flutter/pull/183715) | Platform OpenGL context |
| [#171409](https://github.com/flutter/flutter/pull/171409) | Multi-view GL после software renderer |
| [#186848](https://github.com/flutter/flutter/pull/186848) | FlView alive until redraw idle |
| [#192137](https://github.com/flutter/flutter/pull/192137) | Don't clear GL context after draw |
| [#183871](https://github.com/flutter/flutter/pull/183871) | Revert sibling reuse — регрессия main window после close |

## Паттерн «implicit view cannot be removed»

Это **не** сообщение «secondary view broken». Это:

- кто-то вызвал RemoveView для view_id==0 (implicit), **или**
- dispose primary FlView / wrong pointer, **или**
- engine state уже inconsistent после предыдущего teardown.

Часто появляется **вместе** с close secondary, потому что teardown secondary триггерит cascade (weak refs, compositor cleanup primary, quit handler). Нужно смотреть stack: какой view_id уходит в RemoveView.

## Паттерн GLX BadAccess на close

Классическая последовательность (как в комментариях `mvd_linux_runner.cc`):

```
serial N:   X_GLXMakeContextCurrent  → BadAccess
serial N+1: X_GLXGetDrawableAttributes → GLXBadDrawable
```

Подавление X errors спасает от `_exit(1)`, но **не** от:

- Flutter `FML_CHECK` на false return из GLX;
- epoxy asserts;
- последующего use-after-free в compositor.

Поэтому нужен **и** handler, **и** правильный порядок destroy.

## Регрессии sibling / primary context

PR [#183653](https://github.com/flutter/flutter/pull/183653) (reuse sibling) → reverted [#183871](https://github.com/flutter/flutter/pull/183871): после close secondary main window переставал обновляться (GL framebuffer errors).

Урок: shared framebuffer/sibling state между views — хрупкий; close secondary может ломать primary.

## Плагины: известные Linux close crashes

| Пакет | Модель | Linux close |
|-------|--------|-------------|
| `desktop_multi_window` | multi-engine | Краши reported (#581) |
| `window_manager` + DMW | combo | Краши |
| `window_manager_plus` | multi | **Linux не поддерживается** официально |
| `multi_window_manager` | multi-engine + **forced reuse** | Hide вместо destroy |
| `desktop_webview_window` | extra FlView | Wayland SIGSEGV on close |
| `bitsdojo_window` | chrome only | Не multi-window |
| Official windowing | shared | #186577 на Ubuntu 26 XWayland |

## Вывод раздела

Краш secondary close на Linux — **воспроизводимый класс багов экосистемы**, подтверждённый official sample, Canonical PRs и третьими плагинами. `multiview_desktop` уже mitigates часть; полный fix требует либо более жёсткой синхронизации teardown, либо hide/reuse, либо свежего engine с EGL + draw-lifetime fixes — и всё равно тестировать XWayland/NVIDIA отдельно.
