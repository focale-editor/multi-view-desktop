# Research: GTK Window + Flutter Engine Multi-View on Linux

**Дата:** 2026-09-20  
**Контекст:** библиотека `multiview_desktop` (single-engine multi-view). macOS/Windows стабильны; Linux крашится при закрытии вторичных окон (Ubuntu 26.04 / другие дистрибутивы).

## Как читать отчёт

Читать по порядку или по интересующей теме:

| # | Файл | Тема |
|---|------|------|
| 0 | [00-executive-summary.md](./00-executive-summary.md) | Краткие выводы и приоритетные fixes |
| 1 | [01-gtk-window-ubuntu-26.md](./01-gtk-window-ubuntu-26.md) | GTK Window, Ubuntu 26.04, Wayland/X11 |
| 2 | [02-flutter-engine.md](./02-flutter-engine.md) | Flutter Engine, multi-view embedder API |
| 3 | [03-engine-gtk-bridge.md](./03-engine-gtk-bridge.md) | Связь FlEngine ↔ GtkWindow / FlView |
| 4 | [04-multiview-architecture.md](./04-multiview-architecture.md) | Multi-view: один engine — много GtkWindow |
| 5 | [05-bugs-and-crashes.md](./05-bugs-and-crashes.md) | Известные баги и паттерны крашей |
| 6 | [06-solutions-and-workarounds.md](./06-solutions-and-workarounds.md) | Решения: upstream, плагины, workarounds |
| 7 | [07-recommendations-for-multiview_desktop.md](./07-recommendations-for-multiview_desktop.md) | Конкретные рекомендации для этой библиотеки |
| 8 | [08-sources-and-query-log.md](./08-sources-and-query-log.md) | Источники + лог ~80 поисковых запросов |

Диаграммы:

- [diagrams/close-lifecycle.md](./diagrams/close-lifecycle.md) — порядок закрытия secondary window
- [diagrams/architecture.md](./diagrams/architecture.md) — engine / views / GTK

## Ключевой вердикт (1 абзац)

Краш при закрытии вторичных окон на Linux — **системная проблема Flutter Linux embedder + GLX/EGL lifecycle**, а не «ошибка одного плагина». Корневые причины: (1) гонка raster-thread vs уничтожение X11 drawable / GL context; (2) `FlutterEngineRemoveView` / dispose `FlView` без ожидания завершения raster-задач; (3) на Ubuntu 26.04 GNOME — Wayland-only session + XWayland, что усиливает нестабильность GLX-пути. Рабочие стратегии: **отложенный destroy**, **hide/reuse вместо destroy**, **X11 error handler**, **синхронизация RemoveView → callback → destroy surface**, плюс трекинг upstream-фиксов Canonical (`robert-ancell`, windowing API).

## Объём ресерча

- ~80 отдельных web-запросов (см. `08-sources-and-query-log.md`)
- Анализ исходников `linux/` в `multiview_desktop`
- Официальные docs GTK3, Flutter Linux embedder API, Flutter blog (windowing)
- GitHub issues/PRs: flutter/flutter, leanflutter/window_manager, MixinNetwork/desktop_multi_window
- Сравнение сторонних решений: `desktop_multi_window`, `multi_window_manager`, `window_manager_plus`, official `examples/multiple_windows`
