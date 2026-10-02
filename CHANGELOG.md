## Unreleased

- `MainAppShellCapture` no longer walks the whole main view after every frame. It keeps the element of the entry widget it found and walks again only once that element is unmounted.
- Linux. Window close paths destroy and unmap GTK windows from a main-loop idle callback instead of a 100 ms timer, and no longer quit the application themselves (Focale ADRs 0251 and 0252).
- Linux. `multiview_desktop_linux_runner_install` keeps each Flutter view's GTK render children alive until the engine releases the view (Focale ADR 0251). `tool/linux_view_render_lifetime.cc` checks this ownership.
- Linux. Activating a window blocked by a modal dialog hands keyboard focus back to that dialog, so typing never reaches the blocked window.

## 1.2.2

- [Check README] Windows. Fixed other plugins registration and using. Minor native setting update

## 1.2.1

- MacOS. Returned `closeAppAfterLastWindowClosed` param for more custom ways
- MacOS. Add taskbar icon tap handler.
- MacOS. Specific functions moved to `macos` part

## 1.2.0

- [Check README] Linux. x11 support (setAlignment, alwaysOnTop, setPosition, center). Use
  GDK_BACKEND=x11 env arg to enable
- [Check README] Taskbar custom menu items on all platforms
- [Check README] MacOS. OnTerminate handler (CMD+Q/terminate the app from taskbar)
- MacOS. Removed `closeAppAfterLastWindowClosed` param. App automatically defines when need to stay
  in memory
- MacOS. saveLastWindowToReopen now ignored by one of causes: use `closeApp`/ onTerminate/ close
  mode is `destroy`

## 1.1.2

- Up view create timeout to 10 sec
- Fix: Orphan was sending data to observers

## 1.1.1

- Hot restart windowOptions fix

## 1.1.0

- View builder got context & id.
- [Check README] Added observers to runMultiApp->config
- [Check README] Added native openDialog
- [Check README] Updated EntryApp requirements, now needs only in home builder.

## 1.0.2

- Linux min/max size fix. Repository link fix.

## 1.0.1

- Linux setup doc update

## 1.0.0

- Windows, macOS and linux (without X11) support