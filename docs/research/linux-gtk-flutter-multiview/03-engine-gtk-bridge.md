# 03 — Связь FlutterEngine и GtkWindow

## Слои

```
┌─────────────────────────────────────────────────────────┐
│ Dart: ViewCollection / View / WindowController          │
└──────────────────────────┬──────────────────────────────┘
                           │ PlatformDispatcher / embedder
┌──────────────────────────▼──────────────────────────────┐
│ FlEngine  ←→  FlutterEngine (C API)                     │
│   views: map<FlutterViewId, FlRenderable>               │
└──────────────────────────┬──────────────────────────────┘
                           │ fl_view_new_for_engine
┌──────────────────────────▼──────────────────────────────┐
│ FlView (GtkWidget, FlRenderable)                        │
│   view_id, engine ref, renderer/compositor              │
└──────────────────────────┬──────────────────────────────┘
                           │ gtk_container_add
┌──────────────────────────▼──────────────────────────────┐
│ GtkWindow / GtkApplicationWindow                        │
│   GdkWindow → X11 XID  |  Wayland wl_surface            │
└─────────────────────────────────────────────────────────┘
```

**Важно:** `GtkWindow` ≠ `FlutterView`.  
`GtkWindow` — native chrome/surface host.  
`FlView` — мост: metrics, input, GL present.  
`FlEngine` — один на процесс в multi-view модели.

## Два паттерна создания окон

### A. Shared engine (правильный multi-view) — `multiview_desktop`

```
Primary:
  FlView* primary = fl_view_new(project);   // creates engine, implicit view
  FlEngine* engine = fl_view_get_engine(primary);
  gtk_container_add(primary_window, primary);

Secondary:
  GtkWindow* w2 = gtk_application_window_new(app);
  FlView* v2 = fl_view_new_for_engine(engine);  // AddView
  gtk_container_add(w2, v2);
```

Плюсы: один isolate, shared memory, дешёвые окна.  
Минусы: тесная связь GL/compositor между views; destroy одного view влияет на shared state.

### B. Per-window engine (legacy plugins)

```
Secondary:
  FlView* v2 = fl_view_new(project2);  // NEW engine + NEW isolate
```

Так работают `desktop_multi_window` / многие forks.  
Плюсы: изоляция.  
Минусы: IPC, память; на Linux destroy/recreate `FlView`/`FlEngine` всё равно крашит → forced reuse.

## Ownership и refcount

| Объект | Кто владеет |
|--------|-------------|
| `GtkApplication` | process / runner |
| `GtkWindow` | application (пока attached) + GObject refs |
| `FlView` | parent container (window) + refs от signals/idle |
| `FlEngine` | ref от каждого FlView + runner global |

При destroy window:

1. Container убирает FlView → dispose FlView.
2. FlView вызывает `fl_engine_remove_view`.
3. Engine unref; если refs > 0 (другие views) — engine жив.
4. GdkWindow / GL context для этого view уничтожаются.

Race возникает между шагами 2–4 и raster thread.

## Input / focus / metrics

- Pointer/keyboard events с GtkWidget → Fl*Manager → engine с `view_id`.
- Resize → `FlutterWindowMetricsEvent` для конкретного view.
- Focus: `gtk_window_present` / `grab_focus` на FlView.

Ошибки в view_id routing исторически были частью [#138178](https://github.com/flutter/flutter/issues/138178).

## Quit handlers

Flutter Linux по умолчанию может привязать `delete-event` → request app exit / quit.

Для multi-window нужно:

```c
// концептуально — как multi_window_manager / multiview_desktop
detach_flutter_quit_on_window_close(window, view);
```

Иначе закрытие secondary = exit всего приложения (или странный teardown primary).

## Как `multiview_desktop` связывает слои

Из кода репозитория:

1. `multiview_desktop_linux_runner_register_primary(window, view)`  
   → сохраняет `g_shared_engine`, регистрирует primary в registry.
2. `create_secondary_window`  
   → `gtk_application_window_new` + `fl_view_new_for_engine(g_shared_engine)`.
3. `mvd_linux_complete_secondary_window`  
   → registry `view_id → MvdLinuxWindow{window, view}`, signals (`delete-event`, focus, configure).
4. Close path  
   → soft-close protocol (preconfirm/confirm) → hide → deferred destroy.

Это **правильная** архитектура связи Engine↔GTK; краши — в timing/GL, не в «не той модели».
