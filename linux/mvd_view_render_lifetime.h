#ifndef MVD_VIEW_RENDER_LIFETIME_H_
#define MVD_VIEW_RENDER_LIFETIME_H_

#include <gtk/gtk.h>

/// Keep FlView render descendants alive until the view itself is finalized.
/// gtk_widget_destroy drops the container subtree while the raster thread may
/// still hold the FlView; those children are released on the GTK main thread.
void mvd_install_view_render_lifetime(GtkApplication* application);

#endif  // MVD_VIEW_RENDER_LIFETIME_H_
