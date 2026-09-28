# 07 — Рекомендации для `multiview_desktop`

Контекст: в `linux/` уже реализованы deferred destroy, soft-close, shared engine, X11 GLX handler, detach quit. Ниже — что усилить, опираясь на ресерч.

## 1. Диагностика: классифицировать краш

Перед сменой кода собрать на Ubuntu 26:

```bash
echo $XDG_SESSION_TYPE
# run under:
#   default Wayland
#   GDK_BACKEND=x11
#   FLUTTER_LINUX_RENDERER=software
```

Логи уже подробные (`MVD_LOG_*`). Искать:

| Лог / crash | Следующий шаг |
|-------------|----------------|
| BadAccess / GLX после `deferred_destroy_cb` | Усилить sync (раздел 2–3) |
| BadAccess **до** destroy (ещё visible) | Другой баг (context contention) |
| `implicit view cannot be removed` | Не тот view_id / primary dispose |
| epoxy / compositor shaders | Engine version / context clear |
| Только на `GDK_BACKEND=x11` | Документировать Wayland preferred |

## 2. Event-driven barrier вместо «магических 100 ms»

Сейчас: `g_timeout_add(100, destroy)`.

Предлагаемый контракт:

```
Native on_delete (final):
  hide
  emit('close') / method channel destroyWindow ack request
  state = WAITING_DART

Dart:
  remove View from ViewCollection
  reply ack

Native on ack:
  fl_engine_remove_view(..., callback)

callback (removed==true):
  g_idle_add → gtk_widget_destroy
  (+ safety timeout 500ms если ack потерян)
```

100 ms оставить как **fallback**, не как единственный sync.

## 3. Не полагаться на fire-and-forget RemoveView

`fl_view_dispose` вызывает RemoveView с NULL callback.  
Если destroy идёт через `gtk_widget_destroy` → FlView dispose — вы получаете этот путь.

Варианты:

- **Явно** вызвать `fl_engine_remove_view` сами, дождаться finish, потом destroy widget (сложнее с GObject).
- Или: после hide убрать FlView из container (`gtk_container_remove`) управляемо, контролировать порядок.
- Следить upstream #164564 — когда callback станет «после raster drain», упростить свой код.

## 4. Linux CloseMode: hide/reuse

Добавить в публичный API (если ещё нет симметрии с Mac/Win):

- `CloseBehavior.destroy` (текущий deferred path)
- `CloseBehavior.hide` (только hide; view остаётся в engine)
- `CloseBehavior.reuse` (hide + pool для createWindow)

Для Linux default можно сделать `hide` или `reuse` в debug/docs recommendation, сохранив destroy для тех, кому нужно освобождать ресурсы.

Это то, к чему пришли multi-engine либы после тех же крашей.

## 5. Primary window policy

Документировать / enforce:

- Не уничтожать primary, пока есть secondaries (или auto-hide primary как GL anchor — если engine version ещё зависит от sibling).
- На новых EGL engines зависимость слабее — проверить на целевом Flutter version.

## 6. XInitThreads

Проверить `example/linux/runner/main.cc`:

```cpp
#ifdef GDK_WINDOWING_X11
#include <X11/Xlib.h>
#endif

int main(...) {
#ifdef GDK_WINDOWING_X11
  XInitThreads();
#endif
  ...
}
```

И link `X11` в CMake. Это не fix close-crash, но убирает отдельный класс XCB aborts при multi-thread GL.

## 7. Версии Flutter

В CI / README matrix:

| Channel | Зачем |
|---------|-------|
| stable (пользователи) | Базовая совместимость |
| main (windowing + EGL fixes) | Ранние engine fixes #186848 и др. |

Зафиксировать known-bad / known-good engine hashes, если найдёте.

## 8. Тест-план (минимум)

1. Open 1 secondary → close via button → app alive, primary paints.
2. Open 5 secondary → close all in random order.
3. Rapid open/close 20× (tooltip-like).
4. Close primary last vs first.
5. Modal dialog secondary close.
6. Wayland vs `GDK_BACKEND=x11`.
7. Mesa Intel vs NVIDIA.
8. Stress: close during resize/drag (у вас есть drag watchers — cancel on destroy уже есть).

## 9. Чего не делать

- Не «чинить» переходом на GTK4.
- Не считать multi-engine (`desktop_multi_window`) панацеей без reuse.
- Не полагаться только на suppress X errors.
- Не форсить `GDK_BACKEND=x11` в docs для Ubuntu 26.

## 10. Связь с official API

Долгосрочно: следить `LinuxWindowRegistrar` / out-of-tree windowing owners ([commit 5616240](https://github.com/flutter/flutter/commit/5616240925f6a9a1363d328bf125127862d7241d)) — возможно, `multiview_desktop` станет `LinuxWindowingOwner` без дублирования GtkWindow management.

Краткосрочно: текущая shared-engine + ViewCollection модель правильная; фокус на teardown sync.
