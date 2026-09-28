# 08 — Источники и лог поисковых запросов

Дата ресерча: **2026-09-20**.  
Формат: тематические блоки запросов (выполнены через WebSearch / WebFetch) + ключевые URL.

Объём: **~85 отдельных запросов** (+ точечные fetch страниц).

---

## A. GTK Window / lifecycle / Ubuntu 26 (~15)

1. `Ubuntu 26.04 GTK version Wayland X11 window management 2026`
2. `GTK3 gtk_window_close delete-event destroy-event lifecycle GtkApplication`
3. `Gtk.Window.close gtk3 documentation`
4. `Gtk.Widget::delete-event return TRUE hide`
5. `How do I intercept a gtk window close button click?`
6. `Gio.Application.quit g_application_hold windows`
7. `Ubuntu Resolute Raccoon drops Xorg`
8. `Wayland Display Server Guide on Ubuntu 26.04`
9. `GNOME Mutter 50 Alpha X11 backend removed`
10. `UbuntuUpdates gtk4 resolute 26.04`
11. `GTK4 Flutter Linux embedder why not`
12. `Use gtk4 for linux desktop flutter issue 94804`
13. `Switch to GTK4 flutter engine PR 50960`
14. `Build a GTK4 version of libflutter_gtk`
15. `Multiple GtkGLArea widget share OpenGL context GNOME`

### Ключевые URL
- https://docs.gtk.org/gtk3/method.Window.close.html
- https://docs.gtk.org/gtk3/signal.Widget.delete-event.html
- https://docs.gtk.org/gtk3/class.Window.html
- https://docs.gtk.org/gtk3/class.GLArea.html
- https://www.theregister.com/software/2026/04/24/ubuntu-resolute-raccoon-drops-xorg-keeps-x11-apps-alive/
- https://linuxconfig.org/wayland-display-server-guide-on-ubuntu-26-04
- https://www.phoronix.com/news/GNOME-Mutter-Shell-50-Alpha
- https://github.com/flutter/flutter/issues/94804
- https://discourse.gnome.org/t/multiple-gtkglarea-widget/27877

---

## B. Flutter Engine / multi-view API (~18)

16. `Flutter engine AddView RemoveView Linux GTK desktop embedding`
17. `Flutter multi-window Linux official API ViewCollection`
18. `FlutterEngineAddView FlutterEngineRemoveView embedder API multi-view design doc`
19. `Add new multi-view embedder APIs issue 144806`
20. `Add fl_engine_add/remove_view PR 54018`
21. `fl_view_new_for_engine fl_engine_add_view`
22. `fl_view_dispose fl_engine_remove_view order destroy FlView Linux`
23. `FlutterEngineRemoveView may execute the callback too early 164564`
24. `ViewCollection class Flutter API`
25. `View class Flutter widgets multi-view`
26. `The Linux embedder should support multiple views or windows 138178`
27. `Support multiple windows for desktop shells 30701`
28. `Flutter enable-windowing RegularWindowController Linux API documentation`
29. `Introducing the Desktop Windowing API for Flutter`
30. `How to enable multi-window support in a Flutter desktop app`
31. `flutter examples multiple_windows Linux crash github`
32. `Multi-Window Pre-launch Checklist 177586`
33. `What’s new in Flutter 3.44 windowing`
34. `What’s new in Flutter 3.47 popup windows Linux`

### Ключевые URL
- https://flutter.dev/go/multi-view-embedder-apis
- https://flutter.dev/blog/desktop-windowing-apis
- https://api.flutter.dev/flutter/widgets/ViewCollection-class.html
- https://api.flutter.dev/linux-embedder/fl__view_8cc_source.html
- https://api.flutter.dev/linux-embedder/fl__engine_8cc.html
- https://api.flutter.dev/linux-embedder/fl__engine__private_8h.html
- https://github.com/flutter/flutter/issues/138178
- https://github.com/flutter/flutter/issues/144806
- https://github.com/flutter/flutter/issues/30701
- https://github.com/flutter/flutter/issues/164564
- https://github.com/flutter/flutter/tree/master/examples/multiple_windows
- https://github.com/flutter/engine/pull/54018

---

## C. Engine ↔ GTK / GL / EGL (~16)

35. `Flutter Linux multi-view EGL X11 fallback robert-ancell PR 170045`
36. `Perform OpenGL compositing in the Flutter thread and write to a framebuffer 172090`
37. `Use EGLImage to pass Flutter frames between GTK OpenGL contexts 165539`
38. `Render Flutter in its own EGL context 172330`
39. `Add a platform OpenGL context 183715`
40. `GTK3 GtkGLArea cannot share OpenGL context Flutter multi window`
41. `Fix multi-view GL rendering not working since software rendering was added 171409`
42. `Fix crash if FlView is destroyed during a draw 186848`
43. `[Linux] Don't clear the OpenGL context when a frame has been drawn 192137`
44. `Revert Linux reuse sibling 183871`
45. `XInitThreads Flutter Linux required multi thread OpenGL`
46. `Linux desktop window is blank XInitThreads 170937`
47. `Multithreaded X11 application and OpenGL`
48. `Flutter Linux g_application_hold quit on window close multi window`
49. `Fix the application not disposing circular references on quit engine 47684`
50. `fl_platform_handler quit_application gtk_window_set_application NULL`

### Ключевые URL
- https://github.com/flutter/flutter/pull/172090
- https://github.com/flutter/flutter/pull/172330
- https://github.com/flutter/flutter/pull/165539
- https://github.com/flutter/flutter/pull/183715
- https://github.com/flutter/flutter/pull/186848
- https://github.com/flutter/flutter/pull/192137
- https://github.com/flutter/flutter/pull/183871
- https://github.com/flutter/flutter/pull/171409
- https://github.com/flutter/engine/pull/47684
- https://api.flutter.dev/linux-embedder/fl__platform__handler_8cc_source.html
- https://www.x.org/releases/X11R7.6/doc/man/man3/XInitThreads.3.xhtml

---

## D. Краши secondary close / Linux bugs (~18)

51. `Flutter Linux multi-view GtkWindow close crash secondary window`
52. `FlutterEngineRemoveView "implicit view cannot be removed" Linux`
53. `Flutter Linux GLX BadAccess glXSwapBuffers window close crash X11`
54. `[windowing][linux] RegularWindowController crashes on X11 with GLX BadAccess 186577`
55. `[linux] app freezes/crashes on startup running on X11 169470`
56. `[Linux/X11/NVIDIA] Failed to create OpenGL context 184259`
57. `linux ubuntu2020 多窗口情况下 子窗口关闭会奔溃 window_manager 581`
58. `Crash on exit application with window_manager on Fedora 44 585`
59. `Linux Wayland SIGSEGV gdk_gl_texture_from_surface WebView window closed`
60. `erro flet FlutterEngineRemoveView kInvalidArguments`
61. `[Linux] High VRAM usage when resizing desktop app on Wayland 182192`
62. `BadAccess GLX AnimatedSwitcher Flutter X11 fvp`
63. `Flutter Linux Wayland secondary window close crash EGL`
64. `FLUTTER_LINUX_RENDERER=software multi window crash workaround`
65. `mixed view ownership Flutter multi-window Linux hide instead destroy`
66. `site:reddit.com Flutter multi window Linux crash OR close`
67. `Flutter desktop multi-window wait or use existing packages reddit`
68. `Does Flutter officially support multi-window desktop apps reddit`

### Ключевые URL
- https://github.com/flutter/flutter/issues/186577
- https://github.com/flutter/flutter/issues/169470
- https://github.com/flutter/flutter/issues/184259
- https://github.com/flutter/flutter/issues/182192
- https://github.com/leanflutter/window_manager/issues/581
- https://github.com/leanflutter/window_manager/issues/585
- https://github.com/kodjodevf/mangayomi/issues/752
- https://github.com/flet-dev/flet/issues/4947
- https://github.com/wang-bin/fvp/issues/271
- https://www.reddit.com/r/FlutterDev/comments/1u9qabh/does_flutter_officially_support_multiwindow/
- https://www.reddit.com/r/FlutterDev/comments/1uj9nv1/flutter_desktop_multiwindow_wait_or_use_existing/

---

## E. Сторонние решения / пакеты (~12)

69. `desktop_multi_window Linux FlView destroy close secondary window github`
70. `desktop_multi_window Flutter package`
71. `[desktop_multi_window] Can it work with window_manager?`
72. `vvlad-islavs/multi-window-manager`
73. `multi_window_manager Dart API docs`
74. `multi_window_manager Flutter package reuse Linux`
75. `window_manager_plus Linux unsupported`
76. `bitsdojo_window Linux multi window OR window_manager_plus Linux crash`
77. `multiview_desktop Flutter package`
78. `ubuntu.com blog multiple window flutter desktop Canonical`
79. `Expose LinuxWindowRegistrar out of tree LinuxWindowingOwners`
80. `Share the common Linux window controller code in mixins PR 191930`

### Ключевые URL
- https://pub.dev/packages/desktop_multi_window
- https://pub.dev/packages/multi_window_manager
- https://pub.dev/packages/window_manager_plus
- https://pub.dev/packages/multiview_desktop
- https://github.com/vvlad-islavs/multi-window-manager
- https://github.com/MixinNetwork/flutter-plugins/issues/137
- https://github.com/bitsdojo/bitsdojo_window
- https://startdebugging.net/2026/08/how-to-enable-multi-window-support-in-a-flutter-desktop-app/

---

## F. Доп. уточняющие / fetch (~5+)

81. Fetch: `https://flutter.dev/blog/desktop-windowing-apis`
82. Fetch: `https://github.com/flutter/flutter/issues/138178`
83. Fetch: multiple agent-tools dumps of embedder docs / issue threads
84. `Expose platform specific handles for multi-window API GtkWindow`
85. Local code review: `linux/mvd_linux_window.cc`, `mvd_linux_runner.cc`, `multiview_desktop_plugin.cc`

---

## G. Локальные артефакты проекта (проанализированы)

| Файл | Что извлечено |
|------|----------------|
| `linux/mvd_linux_runner.cc` | X11 GLX error handler rationale; shared engine; secondary create |
| `linux/multiview_desktop_plugin.cc` | on_delete soft-close + deferred destroy 100ms |
| `linux/mvd_linux_window.cc` | Close/Destroy deferred path; registry |
| `linux/mvd_linux_window.h` | Window state machine fields |

---

## Как воспроизводить ресерч

Повторить блоки A–E в поисковике / GitHub; для свежих багов добавить:

```
Flutter Linux multi-view close crash after:2026-01-01
is:issue label:platform-linux "RemoveView"
is:issue "GLX" "BadAccess" "windowing"
```

---

## Карта «запрос → вывод»

| Тема | Главный вывод из блока |
|------|------------------------|
| Ubuntu 26 | Wayland-only GNOME; X11 apps via XWayland; Flutter всё ещё GTK3 |
| Engine | AddView/RemoveView есть; RemoveView timing unsafe (#164564) |
| Bridge | FlView in GtkWindow; shared FlEngine — правильная модель |
| Multi-view | Official API experimental; plugins либо shared-engine либо multi-engine+reuse |
| Bugs | Close crash class: GLX race, implicit RemoveView, compositor dispose |
| Solutions | Hide/reuse > event-driven RemoveView > delay > X handler only |
