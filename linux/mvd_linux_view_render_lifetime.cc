#include "mvd_linux_view_render_lifetime.h"

#include <flutter_linux/flutter_linux.h>

namespace {
/// Key marking views whose descendants already have additional ownership.
constexpr const char* kRenderChildren = "focale-render-children";

/// Retains descendants before GTK can dispose their parent container.
void collect_children(GtkWidget* widget, gpointer data) {
  auto* children = static_cast<GPtrArray*>(data);
  g_ptr_array_add(children, g_object_ref(widget));
  if (GTK_IS_CONTAINER(widget)) {
    gtk_container_forall(GTK_CONTAINER(widget), collect_children, children);
  }
}

/// Releases retained resources on GTK's thread after final raster ownership.
gboolean release_children(gpointer data) {
  g_ptr_array_unref(static_cast<GPtrArray*>(data));
  return G_SOURCE_REMOVE;
}

/// Final view references may be released by the raster thread.
void schedule_release(gpointer data) {
  g_idle_add_full(G_PRIORITY_DEFAULT_IDLE, release_children, data, nullptr);
}

/// Prevents late renderer notifications from calling a destroyed FlView.
void disconnect_children(GtkWidget* view, gpointer data) {
  auto* children = static_cast<GPtrArray*>(data);
  for (guint index = 0; index < children->len; index++) {
    g_signal_handlers_disconnect_matched(g_ptr_array_index(children, index),
        G_SIGNAL_MATCH_DATA, 0, 0, nullptr, nullptr, view);
  }
}

/// A Flutter view is attached after GtkApplication's window-added signal.
void child_added(GtkContainer*, GtkWidget* child, gpointer) {
  if (FL_IS_VIEW(child)) {
    mvd_linux_retain_view_render_children(child);
  }
}

/// Covers every native window created by the shared-engine backend.
void window_added(GtkApplication*, GtkWindow* window, gpointer) {
  g_signal_connect(window, "add", G_CALLBACK(child_added), nullptr);
}
}  // namespace

void mvd_linux_retain_view_render_children(GtkWidget* view) {
  if (g_object_get_data(G_OBJECT(view), kRenderChildren) != nullptr) {
    return;
  }
  GPtrArray* children = g_ptr_array_new_with_free_func(g_object_unref);
  gtk_container_forall(GTK_CONTAINER(view), collect_children, children);
  g_signal_connect(view, "destroy", G_CALLBACK(disconnect_children), children);
  g_object_set_data_full(G_OBJECT(view), kRenderChildren, children,
                        schedule_release);
}

void mvd_linux_install_view_render_lifetime(GtkApplication* application) {
  static constexpr const char* kInstalled = "mvd-view-render-lifetime";
  if (g_object_get_data(G_OBJECT(application), kInstalled) != nullptr) {
    return;
  }
  g_object_set_data(G_OBJECT(application), kInstalled, GINT_TO_POINTER(1));
  g_signal_connect(application, "window-added", G_CALLBACK(window_added), nullptr);
}
