#ifndef MVD_LINUX_VIEW_RENDER_LIFETIME_H_
#define MVD_LINUX_VIEW_RENDER_LIFETIME_H_

#include <gtk/gtk.h>

/// Keeps GTK render children alive while a raster callback owns their view.
void mvd_linux_retain_view_render_children(GtkWidget* view);

/// Attaches rendering ownership to primary and secondary Flutter views.
///
/// Idempotent; covers every window later added to [application].
void mvd_linux_install_view_render_lifetime(GtkApplication* application);

#endif  // MVD_LINUX_VIEW_RENDER_LIFETIME_H_
