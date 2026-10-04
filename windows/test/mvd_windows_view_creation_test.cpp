#include "mvd_windows_view_creation.h"

#include <UIAutomation.h>
#include <cstdio>

namespace {

/// Tracks whether accessibility requests reach an initializing window.
struct WindowState {
  int queries = 0;
};

/// Simulates requests from an accessibility client during WM_CREATE.
LRESULT CALLBACK TestWindowProc(HWND window, UINT message, WPARAM wparam,
                                LPARAM lparam) {
  if (message == WM_NCCREATE) {
    const auto* creation = reinterpret_cast<CREATESTRUCTW*>(lparam);
    SetWindowLongPtrW(window, GWLP_USERDATA,
                     reinterpret_cast<LONG_PTR>(creation->lpCreateParams));
  }
  auto* state = reinterpret_cast<WindowState*>(
      GetWindowLongPtrW(window, GWLP_USERDATA));
  if (message == WM_CREATE) {
    SendMessageW(window, WM_GETOBJECT, 0, OBJID_CLIENT);
    SendMessageW(window, WM_GETOBJECT, 0, UiaRootObjectId);
  }
  if (message == WM_GETOBJECT && state != nullptr) {
    ++state->queries;
    return 123;
  }
  if (message == WM_APP) {
    return 456;
  }
  return DefWindowProcW(window, message, wparam, lparam);
}

/// Registers a window class using the test accessibility provider.
bool RegisterTestClass(const wchar_t* name) {
  WNDCLASSW window_class = {};
  window_class.lpszClassName = name;
  window_class.hInstance = GetModuleHandleW(nullptr);
  window_class.lpfnWndProc = TestWindowProc;
  return RegisterClassW(&window_class) != 0;
}

/// Creates a message-only child as Flutter does before parenting a view.
HWND CreateTestWindow(const wchar_t* name, WindowState* state) {
  return CreateWindowExW(0, name, name, WS_CHILD | WS_VISIBLE,
                         0, 0, 100, 100, HWND_MESSAGE, nullptr,
                         GetModuleHandleW(nullptr), state);
}

/// Fails with a useful diagnostic instead of relying on disabled assertions.
bool Check(bool condition, const char* message) {
  if (!condition) {
    std::fprintf(stderr, "FAIL: %s (Win32 error %lu)\n", message, GetLastError());
  }
  return condition;
}

}  // namespace

/// Checks initialization filtering, normal accessibility and nested cleanup.
int main() {
  if (!Check(RegisterTestClass(L"FLUTTERVIEW"), "register Flutter class") ||
      !Check(RegisterTestClass(L"MVD_TEST_HOST"), "register host class")) {
    return 1;
  }
  WindowState outer_state;
  WindowState inner_state;
  WindowState host_state;
  HWND outer = nullptr;
  HWND inner = nullptr;
  HWND host = nullptr;
  {
    multi_view_desktop::ScopedViewCreation guard;
    if (!Check(guard.is_active(), "install creation hook")) return 1;
    outer = CreateTestWindow(L"FLUTTERVIEW", &outer_state);
    host = CreateTestWindow(L"MVD_TEST_HOST", &host_state);
    if (!Check(outer != nullptr && host != nullptr, "create test windows") ||
        !Check(outer_state.queries == 0, "defer both early accessibility requests") ||
        !Check(host_state.queries == 2, "leave non-Flutter windows unchanged") ||
        !Check(SendMessageW(outer, WM_APP, 0, 0) == 456, "forward other messages")) {
      return 1;
    }
    {
      multi_view_desktop::ScopedViewCreation nested;
      inner = CreateTestWindow(L"FLUTTERVIEW", &inner_state);
      if (!Check(inner != nullptr && inner_state.queries == 0,
                 "guard reentrant view creation")) return 1;
      // A failed native creation may destroy its HWND before the scope ends.
      WindowState destroyed_state;
      HWND destroyed = CreateTestWindow(L"FLUTTERVIEW", &destroyed_state);
      if (!Check(destroyed != nullptr && DestroyWindow(destroyed),
                 "destroy a partially initialized view")) return 1;
    }
    if (!Check(SendMessageW(inner, WM_GETOBJECT, 0, OBJID_CLIENT) == 123,
               "restore nested view accessibility") ||
        !Check(SendMessageW(outer, WM_GETOBJECT, 0, OBJID_CLIENT) == 0,
               "retain outer initialization guard")) return 1;
  }
  if (!Check(SendMessageW(outer, WM_GETOBJECT, 0, OBJID_CLIENT) == 123,
             "restore MSAA after creation") ||
      !Check(SendMessageW(outer, WM_GETOBJECT, 0, UiaRootObjectId) == 123,
             "restore UIA after creation") ||
      !Check(outer_state.queries == 2, "deliver restored accessibility queries")) {
    return 1;
  }
  WindowState unguarded_state;
  HWND unguarded = CreateTestWindow(L"FLUTTERVIEW", &unguarded_state);
  if (!Check(unguarded != nullptr && unguarded_state.queries == 2,
             "remove the thread hook after creation")) return 1;
  DestroyWindow(unguarded);
  DestroyWindow(inner);
  DestroyWindow(host);
  DestroyWindow(outer);
  std::puts("PASS: early MSAA/UIA queries deferred; accessibility restored; "
            "other windows and messages preserved; nested and failed creation cleaned up.");
  return 0;
}
