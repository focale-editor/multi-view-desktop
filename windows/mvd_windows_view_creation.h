#ifndef MVD_WINDOWS_VIEW_CREATION_H_
#define MVD_WINDOWS_VIEW_CREATION_H_

#include <windows.h>
#include <commctrl.h>

#include <vector>

namespace multi_view_desktop {

/// Defers accessibility queries until a new Flutter view has its delegate.
///
/// Flutter creates FLUTTERVIEW before binding its view delegate. Windows can
/// synchronously request MSAA/UIA objects during that interval. The thread-local
/// hook only subclasses newly created Flutter windows, and the scope removes
/// those subclasses once FlutterDesktopEngineCreateViewController returns.
class ScopedViewCreation {
 public:
  /// Installs a creation hook on the current platform thread.
  ScopedViewCreation();
  /// Restores normal accessibility and removes the thread hook.
  ~ScopedViewCreation();
  ScopedViewCreation(const ScopedViewCreation&) = delete;
  ScopedViewCreation& operator=(const ScopedViewCreation&) = delete;

  /// Whether the current thread's initialization hook was installed.
  bool is_active() const;

 private:
  /// Subclasses Flutter windows before their first initialization message.
  static LRESULT CALLBACK OnWindowCreating(int code, WPARAM wparam,
                                           LPARAM lparam);

  /// Rejects early accessibility queries and forwards other window messages.
  static LRESULT CALLBACK OnWindowMessage(HWND window, UINT message,
                                          WPARAM wparam, LPARAM lparam,
                                          UINT_PTR subclass_id,
                                          DWORD_PTR reference_data);

  /// The previous scope, when Flutter creates a view reentrantly.
  ScopedViewCreation* previous_;
  /// Hook owned by the outermost scope on this thread.
  HHOOK hook_ = nullptr;
  /// Windows whose temporary subclasses must be removed on scope exit.
  std::vector<HWND> windows_;
  /// Innermost active creation scope on the platform thread.
  static thread_local ScopedViewCreation* current_;
};

}  // namespace multi_view_desktop

#endif  // MVD_WINDOWS_VIEW_CREATION_H_
