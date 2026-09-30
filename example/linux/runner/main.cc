#include "my_application.h"

#ifdef GDK_WINDOWING_X11
#include <X11/Xlib.h>
#endif

int main(int argc, char** argv) {
#ifdef GDK_WINDOWING_X11
  // Must be the first Xlib call in the process. Serializes X11 access across
  // GTK and Flutter's raster thread (avoids a class of XCB/Xlib aborts).
  XInitThreads();
#endif
  g_autoptr(MyApplication) app = my_application_new();
  return g_application_run(G_APPLICATION(app), argc, argv);
}
