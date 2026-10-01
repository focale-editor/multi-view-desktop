#include <gtk/gtk.h>

#include "../linux/mvd_linux_view_render_lifetime.h"

/// Observations shared between the UI thread and the simulated raster worker.
struct RenderCheck {
  GMutex mutex;
  GCond condition;
  bool rendering;
  bool release;
  bool finalized;
  GThread* ui_thread;
  GtkWidget* view;
};

/// Holds the same strong view reference that Flutter's presentation callback owns.
static gpointer render_cb(gpointer data) {
  RenderCheck* check = static_cast<RenderCheck*>(data);
  g_mutex_lock(&check->mutex);
  check->rendering = true;
  g_cond_signal(&check->condition);
  while (!check->release) {
    g_cond_wait(&check->condition, &check->mutex);
  }
  g_mutex_unlock(&check->mutex);
  g_object_unref(check->view);
  return nullptr;
}

/// Records resource release after the worker relinquished its view reference.
static void child_finalized_cb(gpointer data) {
  RenderCheck* check = static_cast<RenderCheck*>(data);
  g_assert_true(g_thread_self() == check->ui_thread);
  check->finalized = true;
}

/// Reproduces GTK destroying a renderer while its parent remains in use.
///
/// Link this and linux/mvd_linux_view_render_lifetime.cc against GTK and
/// flutter_linux.
/// --without-retention verifies that the baseline releases the child too early.
int main(int argc, char** argv) {
  gtk_init(&argc, &argv);
  const bool retain = argc < 2 || g_strcmp0(argv[1], "--without-retention") != 0;
  for (int cycle = 0; cycle < 100; ++cycle) {
    RenderCheck check = {};
    g_mutex_init(&check.mutex);
    g_cond_init(&check.condition);
    check.ui_thread = g_thread_self();
    GtkWidget* window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    check.view = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    GtkWidget* child = gtk_drawing_area_new();
    g_object_set_data_full(G_OBJECT(child), "finalization-check", &check,
                           child_finalized_cb);
    gtk_container_add(GTK_CONTAINER(check.view), child);
    gtk_container_add(GTK_CONTAINER(window), check.view);
    if (retain) {
      mvd_linux_retain_view_render_children(check.view);
      mvd_linux_retain_view_render_children(check.view);  // Idempotent attachment.
    }
    g_object_ref(check.view);
    GThread* worker = g_thread_new("raster-check", render_cb, &check);
    g_mutex_lock(&check.mutex);
    while (!check.rendering) {
      g_cond_wait(&check.condition, &check.mutex);
    }
    g_mutex_unlock(&check.mutex);
    gtk_widget_destroy(window);
    if (check.finalized) {
      g_printerr("Renderer finalized while a presentation still owns its view\n");
      return 1;
    }
    g_mutex_lock(&check.mutex);
    check.release = true;
    g_cond_signal(&check.condition);
    g_mutex_unlock(&check.mutex);
    g_thread_join(worker);
    while (g_main_context_iteration(nullptr, FALSE)) {}
    g_assert_true(check.finalized);
    g_cond_clear(&check.condition);
    g_mutex_clear(&check.mutex);
  }
  g_print("LINUX_VIEW_LIFETIME_OK: 100 concurrent close cycles, no retained children\n");
  return 0;
}
