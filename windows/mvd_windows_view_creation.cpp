#include "mvd_windows_view_creation.h"

#include <UIAutomation.h>
#include <cwchar>

namespace multi_view_desktop {

thread_local ScopedViewCreation* ScopedViewCreation::current_ = nullptr;

ScopedViewCreation::ScopedViewCreation() : previous_(current_) {
  if (previous_ == nullptr) {
    hook_ = SetWindowsHookExW(WH_CBT, OnWindowCreating, nullptr,
                             GetCurrentThreadId());
  }
  current_ = this;
}

ScopedViewCreation::~ScopedViewCreation() {
  current_ = previous_;
  if (hook_ != nullptr) {
    UnhookWindowsHookEx(hook_);
  }
  for (const HWND window : windows_) {
    RemoveWindowSubclass(window, OnWindowMessage,
                         reinterpret_cast<UINT_PTR>(this));
  }
}

bool ScopedViewCreation::is_active() const {
  return hook_ != nullptr ||
         (previous_ != nullptr && previous_->is_active());
}

LRESULT CALLBACK ScopedViewCreation::OnWindowCreating(int code, WPARAM wparam,
                                                       LPARAM lparam) {
  if (code == HCBT_CREATEWND && current_ != nullptr) {
    const HWND window = reinterpret_cast<HWND>(wparam);
    wchar_t class_name[32] = {};
    GetClassNameW(window, class_name, 32);
    if (std::wcscmp(class_name, L"FLUTTERVIEW") == 0) {
      if (!SetWindowSubclass(window, OnWindowMessage,
                             reinterpret_cast<UINT_PTR>(current_), 0)) {
        OutputDebugStringW(L"[MVD] Cannot guard Flutter view initialization\n");
        return 1;
      }
      current_->windows_.push_back(window);
    }
  }
  return CallNextHookEx(nullptr, code, wparam, lparam);
}

LRESULT CALLBACK ScopedViewCreation::OnWindowMessage(
    HWND window, UINT message, WPARAM wparam, LPARAM lparam,
    UINT_PTR subclass_id, DWORD_PTR reference_data) {
  if (message == WM_GETOBJECT) {
    const DWORD object_id = static_cast<DWORD>(lparam);
    if (object_id == static_cast<DWORD>(OBJID_CLIENT) ||
        object_id == static_cast<DWORD>(UiaRootObjectId)) {
      return 0;
    }
  }
  if (message == WM_NCDESTROY) {
    RemoveWindowSubclass(window, OnWindowMessage, subclass_id);
  }
  return DefSubclassProc(window, message, wparam, lparam);
}

}  // namespace multi_view_desktop
