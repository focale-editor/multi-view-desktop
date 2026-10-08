#include "mvd_view_render_lifetime.h"

#include <flutter_linux/flutter_linux.h>

#include <atomic>

/// Identifies the references owned by the view, rather than its GTK container.
static constexpr char kRenderChildren[] = "mvd-render-children";

/// Marks an engine whose finalization is observed by this file.
static constexpr char kEngineObserved[] = "mvd-render-engine-observed";

/// Set once a view's engine is finalized. Its EGL display goes with it, so
/// GL-backed render children can no longer be finalized safely.
static std::atomic<bool> g_engine_finalized{false};

/// Engine finalization may happen on the raster thread.
static void engine_finalized_cb(gpointer, GObject*) {
  g_engine_finalized = true;
}

/// Releases GTK objects on the main thread after the engine drops the view.
static gboolean release_children_cb(gpointer data) {
  GPtrArray* children = static_cast<GPtrArray*>(data);
  if (g_engine_finalized) {
    // Finalizing them now calls eglDestroyImageKHR without a provider and
    // libepoxy aborts. This only happens while the application exits, so the
    // operating system reclaims them instead.
    g_ptr_array_set_free_func(children, nullptr);
  }
  g_ptr_array_unref(children);
  return G_SOURCE_REMOVE;
}

/// Finalization may happen on the raster thread; do not finalize GTK there.
static void view_finalized_cb(gpointer data) {
  g_idle_add_full(G_PRIORITY_DEFAULT, release_children_cb, data, nullptr);
}

/// Retains all descendants without depending on private Flutter widget types.
static void collect_children_cb(GtkWidget* child, gpointer data) {
  GPtrArray* children = static_cast<GPtrArray*>(data);
  g_ptr_array_add(children, g_object_ref(child));
  if (GTK_IS_CONTAINER(child)) {
    gtk_container_forall(GTK_CONTAINER(child), collect_children_cb, children);
  }
}

/// Prevents a pending first-frame callback from calling an already closed view.
static void view_destroyed_cb(GtkWidget* view, gpointer data) {
  GPtrArray* children = static_cast<GPtrArray*>(data);
  for (guint index = 0; index < children->len; ++index) {
    g_signal_handlers_disconnect_matched(
        g_ptr_array_index(children, index), G_SIGNAL_MATCH_DATA, 0, 0, nullptr,
        nullptr, view);
  }
}

static void retain_view_render_children(GtkWidget* view) {
  if (g_object_get_data(G_OBJECT(view), kRenderChildren) != nullptr) {
    return;
  }
  FlEngine* engine = fl_view_get_engine(FL_VIEW(view));
  if (engine != nullptr &&
      g_object_get_data(G_OBJECT(engine), kEngineObserved) == nullptr) {
    g_object_set_data(G_OBJECT(engine), kEngineObserved, GINT_TO_POINTER(1));
    g_object_weak_ref(G_OBJECT(engine), engine_finalized_cb, nullptr);
  }
  GPtrArray* children = g_ptr_array_new_with_free_func(g_object_unref);
  gtk_container_forall(GTK_CONTAINER(view), collect_children_cb, children);
  // A strong FlView reference held by the raster thread does not retain its
  // GTK children: gtk_widget_destroy disposes the entire container subtree.
  // FlViewRenderer releases its compositor at finalization, so an explicit
  // owner reference bridges that gap. Object data is released at finalization,
  // unlike weak notifications, which GTK can deliver during forced dispose.
  g_object_set_data_full(G_OBJECT(view), kRenderChildren, children,
                         view_finalized_cb);
  g_signal_connect(view, "destroy", G_CALLBACK(view_destroyed_cb), children);
}

/// Installs ownership as soon as a fully constructed FlView enters a window.
static void window_child_added_cb(GtkContainer*, GtkWidget* child, gpointer) {
  if (FL_IS_VIEW(child)) {
    retain_view_render_children(child);
  }
}

/// Covers primary, dialog and floating-document windows alike.
static void window_added_cb(GtkApplication*, GtkWindow* window, gpointer) {
  g_signal_connect_after(window, "add", G_CALLBACK(window_child_added_cb),
                         nullptr);
  GtkWidget* child = gtk_bin_get_child(GTK_BIN(window));
  if (child != nullptr && FL_IS_VIEW(child)) {
    retain_view_render_children(child);
  }
}

void mvd_install_view_render_lifetime(GtkApplication* application) {
  if (!application) {
    return;
  }
  g_signal_connect(application, "window-added", G_CALLBACK(window_added_cb),
                   nullptr);
  // Windows created before the hook (should not happen if install is first).
  GList* windows = gtk_application_get_windows(application);
  for (GList* link = windows; link != nullptr; link = link->next) {
    window_added_cb(application, GTK_WINDOW(link->data), nullptr);
  }
}
