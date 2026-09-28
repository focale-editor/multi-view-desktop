# 01 — GTK Window и Ubuntu 26.04

## Ubuntu 26.04 (Resolute Raccoon) — что важно для Flutter

| Компонент | Состояние (2026) |
|-----------|------------------|
| Кодовое имя | Resolute Raccoon (LTS, ~апрель 2026) |
| Desktop | GNOME 50 |
| Display session | **Wayland-only** для стандартного Ubuntu Desktop; опция «Ubuntu on Xorg» убрана |
| X11 apps | Через **XWayland** |
| Mutter | X11 backend удалён в Mutter 50; остаётся только Wayland session + XWayland |
| GTK4 в дистрибутиве | ~4.22.x |
| Flutter Linux embedder | По-прежнему **GTK3** (не GTK4) |

Источники: The Register (Ubuntu drops Xorg), Phoronix (Mutter 50), linuxconfig Wayland guide, Ubuntu packages gtk4.

### Последствия для multi-window Flutter

1. Пользователь на «чистой» Ubuntu 26 почти всегда в Wayland-сессии.
2. Flutter GTK3 app может идти native Wayland **или** через XWayland (если форсят `GDK_BACKEND=x11` / отсутствие Wayland backend).
3. Краши на «Ubuntu 26» часто = **XWayland + NVIDIA + GLX**, а не «баг Ubuntu как таковой».
4. Позиционирование окон (`gtk_window_move`) на native Wayland ограничено compositor’ом — это отдельная боль, не путать с close-crash.

## Принцип работы GtkWindow (GTK3)

Flutter Linux использует **GTK3**, не GTK4. Ниже — lifecycle, релевантный закрытию.

### Создание

```
GtkApplication
  └── GtkApplicationWindow (GtkWindow)
        └── child widgets (у Flutter: FlView)
```

- `gtk_application_window_new(app)` — окно привязано к `GtkApplication`.
- Пока есть окна, `g_application_hold` косвенно удерживает process alive.
- `gtk_window_set_application(window, NULL)` используется Flutter при quit, чтобы разорвать циклы ссылок (GTK issue #6190).

### Закрытие: правильный путь

1. Пользователь жмёт close / вызывается `gtk_window_close(window)`.
2. Генерируется `GDK_DELETE` → сигнал **`delete-event`**.
3. Handlers:
   - return **TRUE** → остановить дальнейшую обработку → **окно НЕ уничтожается** (можно hide).
   - return **FALSE** → default handler → **`gtk_widget_destroy`**.
4. При destroy:
   - unrealize → уничтожение `GdkWindow` / native surface (XID на X11, wl_surface на Wayland);
   - сигнал `destroy` на GObject;
   - для `GtkApplicationWindow` — удаление из списка окон приложения.

Документация GTK3 явно рекомендует `gtk_widget_hide_on_delete()` / custom `delete-event` → TRUE, если нужно **скрыть, а не уничтожить**.

### Почему sync destroy опасен для Flutter

На X11 цепочка:

```
delete-event FALSE
  → gtk_widget_destroy
    → GdkWindow destroyed
      → XDestroyWindow / XID freed
        → Flutter raster thread: glXSwapBuffers(dead_drawable)
          → X error BadAccess / GLXBadDrawable
            → GDK default handler: _exit(1)
```

На Wayland симптомы другие (eglMakeCurrent failed, SIGSEGV в texture upload), но идея та же: **surface lifetime короче, чем GL work**.

## CSD / SSD / HeaderBar

На GNOME (Ubuntu) Flutter templates часто ставят `GtkHeaderBar` (CSD).  
На non-GNOME WM — decorated title через `gtk_window_set_title`.

Для multi-view это влияет на:

- геометрию (shadow + header в GDK hints);
- close button → тот же `delete-event`;
- frameless windows (`gtk_window_set_decorated(FALSE)`).

Не является root cause краша, но влияет на timing realize/unrealize.

## GtkApplication и multi-window

| Поведение | Значение для Flutter |
|-----------|----------------------|
| Последнее окно закрыто | Часто quit application |
| Secondary closed, primary remains | App должен жить |
| Flutter default | `FlView` / platform handler может quit на delete любого окна |

Поэтому multi-window плагины **обязаны**:

1. Отцепить Flutter’s quit-on-delete handler.
2. Сами решать, когда `g_application_quit`.
3. Иногда делать `g_application_hold` / не отпускать hold при secondary close.

`multiview_desktop` это делает (`detach_flutter_quit`, `g_terminate_after_last_window_closed`).

## Wayland vs X11: window management

| Операция | X11 | Wayland |
|----------|-----|---------|
| `gtk_window_move` | Обычно работает | Часто игнорируется |
| Always-on-top | Работает | Ограничено |
| Opaque region / opacity | Предсказуемее | Зависит от compositor |
| GL path в Flutter | GLX (+ CPU copy) | EGL / EGLImage предпочтительнее |
| Close race | BadAccess / BadDrawable | eglMakeCurrent / texture crash |

## GTK4 статус для Flutter

Issue [#94804](https://github.com/flutter/flutter/issues/94804): переход на GTK4 **не завершён**.  
Canonical (robert-ancell): multi-view делается на GTK3; GTK4 — отдельная долгая миграция (a11y, clipboard, plugins).

**Вывод:** ждать GTK4 как fix close-crash — бессмысленно. Чинить нужно в GTK3 + engine GL lifecycle.

## Практические env vars

```bash
echo $XDG_SESSION_TYPE          # wayland | x11
GDK_BACKEND=wayland             # native Wayland
GDK_BACKEND=x11                 # форс X11/XWayland — часто хуже на Ubuntu 26 + NVIDIA
GDK_SYNCHRONIZE=1               # sync X errors для gdb
FLUTTER_LINUX_RENDERER=software # обход части GL багов
```
