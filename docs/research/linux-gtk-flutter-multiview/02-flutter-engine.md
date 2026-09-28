# 02 — Flutter Engine: принцип работы и multi-view

## Общая модель Engine

Flutter Engine — native runtime:

- **UI isolate** (Dart)
- **Raster / GPU thread**
- **IO / platform threads**
- Embedder API (`embedder.h`) — контракт с платформой

На desktop Linux embedder = `libflutter_linux_gtk.so`:

- `FlEngine` — обёртка над `FlutterEngine`
- `FlView` — GtkWidget + `FlRenderable` (поверхность для кадров)
- `FlCompositor*` — OpenGL / software present в GTK

## Implicit view vs explicit views

Исторически у engine был **один implicit view** (id = 0).

Multi-view embedder API ([design doc](https://flutter.dev/go/multi-view-embedder-apis), issue [#144806](https://github.com/flutter/flutter/issues/144806)):

| API | Назначение |
|-----|------------|
| `FlutterEngineAddView` | Зарегистрировать новый view + metrics |
| `FlutterEngineRemoveView` | Снять view (async callback) |
| Multi-view present callbacks | Present layers **per view_id** |

Ограничения (ещё open checklist items):

- нельзя смешивать со старыми single-view semantics callbacks;
- **implicit view нельзя RemoveView** → `kInvalidArguments`;
- опция «disable implicit view» ещё в TODO.

## Linux wrappers

```c
// Secondary / additional view
FlView* fl_view_new_for_engine(FlEngine* engine);
// → внутри: fl_engine_add_view(...); setup_engine(...)

// Primary (legacy)
FlView* fl_view_new(FlDartProject* project);
// → создаёт engine + fl_engine_set_implicit_view
```

`fl_view_get_id(view)` → `FlutterViewId` для Dart `FlutterView` / `View` widget.

### Dispose path (критично)

Из `fl_view_dispose` (документация Flutter Linux embedder):

```c
fl_engine_remove_view(self->engine, self->view_id, nullptr, nullptr, nullptr);
g_clear_object(&self->engine);
// ... затем parent dispose → GL/GTK teardown
```

Проблемы:

1. Callback = **NULL** (fire-and-forget).
2. Surface/widget может уничтожаться **до** завершения raster work.
3. Issue [#164564](https://github.com/flutter/flutter/issues/164564): даже при callback он может сработать раньше, чем «безопасно destroy surface».

Windows embedder для сравнения **блокирует** platform thread latch’ем до AddView/RemoveView completion — Linux historically async/loose.

## Dart / Framework сторона

| API | Роль |
|-----|------|
| `WidgetsBinding.instance.platformDispatcher.views` | Список `FlutterView` |
| `View(view: flutterView, child: ...)` | Bootstrap render tree в конкретный view |
| `ViewCollection(views: [...])` | Несколько sibling `View` в non-rendering zone |
| `runWidget(...)` | Нужен когда нет/нельзя полагаться на implicit view |
| `runApp(...)` | Ожидает implicit view — для pure multi-view часто неправильно |

`ViewCollection` — **framework** API (не создаёт native windows).  
Native windows создаёт embedder / plugin / windowing API.

## Official Desktop Windowing API (2025–2026)

Canonical + Google:

- Blog: [Desktop Windowing APIs](https://flutter.dev/blog/desktop-windowing-apis) (Aug 2026)
- Flag: `flutter config --enable-windowing` (channel **main**)
- Типы окон: Regular, Dialog, Tooltip, Popup, Satellite
- Linux handle: pointer to `GtkWindow`
- Example: `examples/multiple_windows`

Статус на сентябрь 2026:

- Experimental, не для production на stable ([Flutter 3.44 notes](https://flutter.dev/blog/whats-new-in-flutter-3-44)).
- Tracking: [#30701](https://github.com/flutter/flutter/issues/30701), checklist [#177586](https://github.com/flutter/flutter/issues/177586).
- Linux GLX startup crash всё ещё воспроизводится ([#186577](https://github.com/flutter/flutter/issues/186577) на Ubuntu 26.04).

## Эволюция Linux GL для multi-view

Хронология (по комментариям robert-ancell и PRs):

1. **Prototype:** render в implicit view context → CPU copy в secondary GtkGLArea contexts (GTK3 не даёт нормально шарить один context между GLArea).
2. **EGLImage** ([#165539](https://github.com/flutter/flutter/pull/165539), closed): zero-copy между contexts; на X11/GLX не работает → fallback CPU.
3. **Own EGL context** ([#170045](https://github.com/flutter/flutter/pull/170045), [#172330](https://github.com/flutter/flutter/pull/172330)): Flutter может рендерить без GTK window; нужно для multi-window.
4. **Framebuffer compositing** ([#172090](https://github.com/flutter/flutter/pull/172090)): Flutter пишет в свой FB; GTK копирует на draw; на X11 — CPU copy.
5. **Platform OpenGL context** ([#183715](https://github.com/flutter/flutter/pull/183715)): отдельный context для platform thread (fix shaders при создании окон из Dart).
6. **FlView destroy during draw** ([#186848](https://github.com/flutter/flutter/pull/186848), May 2026): retain object until redraw idle completes — rapid open/close tooltips.
7. **Don't clear GL context after draw** ([#192137](https://github.com/flutter/flutter/pull/192137)): GTK продолжал GL без current context → crash.

Вывод: Linux multi-view **активно чинится**, но close/destroy path всё ещё зона высокого риска, особенно X11/XWayland/NVIDIA.

## Threads

```
Platform / GTK main loop
  ├── input, delete-event, timers, widget destroy
  └── иногда GL для compositor shaders

Flutter UI thread
  └── Dart build/layout, ViewCollection updates

Flutter Raster thread
  └── Skia/Impeller → present to view surface / EGL / GLX
```

Любой destroy GtkWindow с FlView без синхронизации с raster = race.

## Ключевые инварианты безопасного RemoveView

Из design intent + [#164564](https://github.com/flutter/flutter/issues/164564):

1. Не destroy native surface, пока RemoveView callback не сказал `removed=true`.
2. Идеально: callback только после того, как raster queue больше не содержит work для этого view_id.
3. Linux `fl_view_dispose` сейчас **не** полностью соблюдает (2).
4. Приложения/плагины должны компенсировать: hide + delay + Dart-side unmount + error handlers.
