# 06 — Варианты решений и workarounds

## A. Upstream / engine-level (долгосрочно)

| Решение | Статус | Эффект на close-crash |
|---------|--------|----------------------|
| Own EGL context + FB compositing | Partially landed | Меньше связки с GtkWindow GL |
| Platform GL context (#183715) | Landed | Фикс create-time shader fails |
| FlView retain until redraw (#186848) | Landed May 2026 | Rapid open/close |
| Don't clear GL after draw (#192137) | Landed | GTK draw без context |
| Правильный RemoveView callback timing (#164564) | **Open / design debt** | Ключ к безопасному destroy surface |
| Official windowing API | Experimental main | Не устраняет Linux GLX bugs сам по себе |
| GTK4 | Not ready | Не ждать |

**Действие:** пинить/тестировать Flutter versions, где есть #186848+#183715+#172330; открывать/следить #164564 и #186577.

## B. Application / plugin teardown protocol (средний срок)

### B1. Deferred destroy (уже в multiview_desktop)

```
delete-event → TRUE
hide window
emit close to Dart
g_timeout_add(N ms) → gtk_widget_destroy
X11 error handler safety net
```

Улучшения:

1. **N не фиксировать слепо** — ждать ack от Dart («view unmounted»).
2. После unmount — вызвать `fl_engine_remove_view` **с callback**, destroy GTK только в callback (+ idle).
3. Увеличить N на медленных машинах / debug (250–500 ms).
4. При `GDK_SYNCHRONIZE=1` тестировать, что race исчез.

### B2. Hide / reuse (самый надёжный)

Паттерн `multi_window_manager`:

- Close secondary → `gtk_widget_hide` only.
- FlView / engine остаются.
- Next create → show + reset content args.
- На Linux reuse **forced**.

Для single-engine multi-view аналог:

- `CloseMode.hide` / `reusePool`.
- Dart: убрать UI content, оставить или не оставить native view (два подрежима).
- Periodic / explicit purge при low memory.

### B3. Never destroy primary first

Исторический совет embedder team: primary GL context / sibling — «держи primary живым (хотя бы hidden)».  
Если app позволяет — primary = скрытый sentinel window.

### B4. Detach quit-on-close + hold application

Обязательно:

- снять Flutter delete handler, который делает quit;
- не вызывать `g_application_quit` пока есть secondary/primary policy;
- при полном выходе — detach windows from GtkApplication перед quit (Flutter уже делает в platform handler).

## C. Multi-engine plugins (альтернативная архитектура)

| Package | Linux advice |
|---------|--------------|
| `desktop_multi_window` | Работает, но close крашит; plugins per window |
| `window_manager_plus` | Linux ❌ |
| `multi_window_manager` | Linux OK **только** с reuse/hide |
| `window_manager` alone | Не создаёт windows; combo с DMW проблемна |

Переход на multi-engine **не** решает Linux close сам по себе — без reuse хуже или так же.

## D. Session / environment workarounds

```bash
# 1) Предпочитать native Wayland на Ubuntu 26
unset GDK_BACKEND
# или
export GDK_BACKEND=wayland

# 2) НЕ форсить X11 на Ubuntu 26 + NVIDIA
# export GDK_BACKEND=x11   # часто триггерит #186577

# 3) Software renderer (диагностика / слабый GPU)
export FLUTTER_LINUX_RENDERER=software

# 4) Debug X races
export GDK_SYNCHRONIZE=1
# gdb: break _XError / gdk_x_error

# 5) XInitThreads в main.cc (если ещё нет в template)
XInitThreads(); // before gtk/g_application
```

## E. Official Flutter windowing API

Когда использовать:

- прототипы на `main` channel;
- alignment с будущим Material `showDialog`/`Tooltip` native windows.

Когда **не** использовать как «fix краша»:

- stable channel ещё без публичного API (на Aug 2026);
- Ubuntu 26 XWayland + NVIDIA: official sample сам крашится (#186577).

Гибрид: держать `multiview_desktop` API, внутри позже делегировать в WindowController, если стабилизируют Linux.

## F. Сравнительная таблица стратегий против close-crash

| Стратегия | Надёжность на Linux | Стоимость | Совместимость с multiview_desktop |
|-----------|---------------------|-----------|-----------------------------------|
| Hide/reuse | ★★★★★ | UX/memory | Высокая (новый CloseMode) |
| Event-driven RemoveView+destroy | ★★★★☆ | Сложность native | Высокая |
| Fixed delay 100–500ms | ★★★☆☆ | Просто | Уже есть |
| X11 error suppress only | ★★☆☆☆ | Просто | Уже есть |
| Software renderer | ★★☆☆☆ | Perf | Env only |
| Switch to multi-engine | ★☆☆☆☆ без reuse | Архитектура | Низкая |
| Wait GTK4 | ★☆☆☆☆ | Годы | N/A |
| Pin new Flutter engine | ★★★☆☆ | CI matrix | Высокая |

## G. Рекомендуемый «стек защиты» (defense in depth)

1. Soft-close protocol (уже есть).
2. Hide immediately (уже есть).
3. Dart unmount View + ack.
4. `fl_engine_remove_view` with callback (улучшить).
5. Deferred widget destroy (уже есть; привязать к 4).
6. X11 GLX error handler (уже есть).
7. Optional Linux reuse mode for apps that can hide.
8. Document env matrix for Ubuntu 26 Wayland vs XWayland.
