# 00 — Executive Summary

## Проблема

На Linux закрытие вторичного окна в multi-view приложении (один `FlEngine`, несколько `GtkWindow` + `FlView`) часто приводит к:

- `Gdk-ERROR` / `BadAccess` (GLX minor 26 = SwapBuffers / MakeCurrent)
- `GLXBadDrawable`
- `FlutterEngineRemoveView` → `kInvalidArguments` («implicit view cannot be removed»)
- `Failed to cleanup compositor shaders, unable to make OpenGL context current`
- `epoxy_get_proc_address` assertion (нет текущего GL context)
- SIGSEGV в `gdk_gl_texture_from_surface` (Wayland)
- `_exit(1)` из GDK X11 error handler

macOS и Windows в той же модели (shared engine + multi-view) стабильнее, потому что их native window teardown и GL surface lifetime лучше согласованы с engine.

## Корневые причины (ранжировано)

1. **Race: GTK destroy vs Flutter raster thread**  
   `gtk_widget_destroy` освобождает XID/drawable, пока raster thread ещё вызывает `glXSwapBuffers` / `glXMakeContextCurrent`. GDK по умолчанию делает `_exit(1)` на X error.

2. **`FlutterEngineRemoveView` callback слишком ранний**  
   Issue [#164564](https://github.com/flutter/flutter/issues/164564): callback может вернуться до того, как raster thread гарантированно перестанет трогать surface. Документация говорит «не destroy surface до callback», но на практике и этого недостаточно без drain raster queue.

3. **Implicit view (view_id == 0) нельзя RemoveView**  
   Плагины, создающие «второй engine» / неправильно уничтожающие primary `FlView`, получают `kInvalidArguments`. Симптом часто путают с «крашем secondary close», хотя root cause — teardown primary или перепутанный view_id.

4. **Архитектура GL на Linux**  
   Исторически: один GL context (часто от primary window) + copy кадров в secondary. Уничтожение primary / sibling framebuffer ломает remaining views. Canonical переводит на own EGL context + EGLImage (Wayland) / CPU copy (X11), но X11/XWayland и NVIDIA остаются хрупкими.

5. **Ubuntu 26.04 специфика**  
   GNOME session — Wayland-only; X11 apps через XWayland. `GDK_BACKEND=x11` на Ubuntu 26 + NVIDIA воспроизводит GLX BadAccess даже в official `examples/multiple_windows` ([#186577](https://github.com/flutter/flutter/issues/186577)).

## Что уже сделано в `multiview_desktop` (хорошо)

Исходники `linux/` уже содержат правильные направления:

| Мера | Где | Зачем |
|------|-----|-------|
| Deferred `gtk_widget_destroy` (~100 ms) | `on_delete`, `Destroy()` | Дать Dart/raster drain |
| Return TRUE из `delete-event` | `multiview_desktop_plugin.cc` | Блокировать sync destroy |
| X11 GLX error handler | `mvd_linux_runner.cc` | Не дать GDK `_exit(1)` |
| Shared engine + `fl_view_new_for_engine` | runner | Правильная multi-view модель |
| Detach Flutter quit-on-close | plugin | Secondary close ≠ app quit |

Этого **может быть недостаточно**, если: delay мал; Dart не успевает снять view из `ViewCollection`; RemoveView fire-and-forget; residual GLX frames всё ещё fatal внутри Flutter (`FML_CHECK`), а не только X error.

## Приоритетные варианты решения краша

### A. Усилить teardown (рекомендуется для текущего API)

1. Hide → уведомить Dart (`close` / `destroyWindow`) → **ждать**, пока framework уберёт `View` из дерева и/или придёт подтверждение.
2. Вызвать / дождаться `fl_engine_remove_view` **с async callback** (не fire-and-forget как в `fl_view_dispose`).
3. Только после callback (+ optional idle/timeout safety) — `gtk_widget_destroy`.
4. Оставить X11 error handler как safety net.
5. Рассмотреть увеличение delay 100→250–500 ms или заменить фиксированный timeout на event-driven barrier.

### B. Hide / reuse вместо destroy (самый надёжный workaround)

Как `multi_window_manager` на Linux: **forced reuse** — close = `gtk_widget_hide`, FlView/engine не уничтожаются. Новый «open» reclaim’ит скрытое окно. Это единственная стратегия, которую сторонние multi-engine либы официально называют «safe on Linux».

Для single-engine multi-view: hide window + оставить FlView в engine **или** hide + отложить RemoveView до process exit / explicit purge.

### C. Сессионные workarounds для пользователей

| Workaround | Эффект |
|------------|--------|
| Native Wayland (`GDK_BACKEND=wayland`, не форсить x11) | Часто стабильнее GLX-path |
| Избегать `GDK_BACKEND=x11` на Ubuntu 26 + NVIDIA | Обход #186577 |
| `FLUTTER_LINUX_RENDERER=software` | Обходит часть GL teardown (не всегда close-crash) |
| Актуальный Flutter `main` / свежий engine | Фиксы #186848, platform GL context #183715, EGL path |
| Не закрывать primary первым | Primary GL context historically shared |

### D. Долгосрочно

- Следить за official windowing API (`flutter config --enable-windowing`, Canonical + Google).
- Трекать PRs robert-ancell: own EGL context, FlView draw-lifetime, compositor fixes.
- Не ждать GTK4: Flutter Linux всё ещё на GTK3; multi-view делается на GTK3.

## Сравнение подходов

| Подход | Плюсы | Минусы |
|--------|-------|--------|
| Single engine + ViewCollection (`multiview_desktop`) | Общий isolate/state, дешево | Linux GL teardown хрупок |
| Multi engine (`desktop_multi_window`) | Изоляция окон | IPC, память, на Linux destroy тоже крашит |
| Hide/reuse | Практически устраняет close-crash | Утечка окон/VRAM, сложный lifecycle |
| Official windowing API | Будущий стандарт | Experimental, только main channel; Linux GLX bugs остаются |

## Рекомендация для команды

1. **Короткий срок:** event-driven destroy (не только 100 ms) + опциональный Linux reuse/hide mode в API.
2. **Средний срок:** дождаться/подтянуть Flutter engine с EGL compositor + FlView draw retain (#186848).
3. **Тесты матрицы:** Ubuntu 26 Wayland, Ubuntu 26 XWayland (`GDK_BACKEND=x11`), Fedora X11, NVIDIA / Mesa / Intel; close secondary ×N; close primary last; rapid open/close.
