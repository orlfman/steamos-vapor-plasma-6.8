/* Test-only instrumentation for the installed GTK 4 Widget Factory.
 * Built in /tmp and loaded only into the private child by the Python runner.
 * It drives GTK APIs, never desktop input, files, audio, printing or app actions.
 */
#define _GNU_SOURCE
#include <gtk/gtk.h>
#include <dlfcn.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static GtkWindow *main_window;
static GtkStack *pages;
static const char *page_name, *state_name;
static gboolean dark;
static int attempts;

static void fail(const char *message) {
  g_printerr("FACTORY TEST FAILED: %s\n", message);
  _exit(2);
}

static GtkWidget *find_id(GtkWidget *root, const char *id) {
  const char *name = gtk_buildable_get_buildable_id(GTK_BUILDABLE(root));
  if (name && strcmp(name, id) == 0) return root;
  for (GtkWidget *child = gtk_widget_get_first_child(root); child;
       child = gtk_widget_get_next_sibling(child)) {
    GtkWidget *found = find_id(child, id);
    if (found) return found;
  }
  return NULL;
}

static void set_state(GtkWidget *root) {
  if (strcmp(state_name, "backdrop") == 0)
    gtk_widget_set_state_flags(root, GTK_STATE_FLAG_BACKDROP, FALSE);
  else
    gtk_widget_unset_state_flags(root, GTK_STATE_FLAG_BACKDROP);
  if (strcmp(state_name, "rtl") == 0)
    gtk_widget_set_direction(root, GTK_TEXT_DIR_RTL);
  for (GtkWidget *child = gtk_widget_get_first_child(root); child;
       child = gtk_widget_get_next_sibling(child)) set_state(child);
}

static int count_mapped(GtkWidget *root) {
  int count = gtk_widget_get_mapped(root) ? 1 : 0;
  for (GtkWidget *child = gtk_widget_get_first_child(root); child;
       child = gtk_widget_get_next_sibling(child)) count += count_mapped(child);
  return count;
}

static gboolean capture(gpointer unused) {
  (void)unused;
  GtkWidget *page = gtk_stack_get_visible_child(pages);
  if (!page || strcmp(gtk_stack_get_visible_child_name(pages), page_name) != 0)
    fail("wrong visible page");
  /* Mapping can change focus flags. Apply the synthetic state immediately
   * before allocation/snapshot, and verify the effective state below. */
  set_state(GTK_WIDGET(main_window));
  gboolean backdrop = (gtk_widget_get_state_flags(page) & GTK_STATE_FLAG_BACKDROP) != 0;
  if (backdrop != (strcmp(state_name, "backdrop") == 0)) fail("wrong backdrop state");
  if (strcmp(state_name, "rtl") == 0 && gtk_widget_get_direction(page) != GTK_TEXT_DIR_RTL)
    fail("wrong text direction");
  GtkInterfaceColorScheme scheme;
  g_object_get(gtk_settings_get_default(), "gtk-interface-color-scheme", &scheme, NULL);
  if (scheme != (dark ? GTK_INTERFACE_COLOR_SCHEME_DARK : GTK_INTERFACE_COLOR_SCHEME_LIGHT))
    fail("wrong requested color scheme");
  G_GNUC_BEGIN_IGNORE_DEPRECATIONS
  GtkStyleContext *context = gtk_widget_get_style_context(page);
  GdkRGBA marker, background, foreground;
  if (!gtk_style_context_lookup_color(context, "vapor_factory_test_marker", &marker) ||
      fabs(marker.red - 17.0/255.0) > .001 || fabs(marker.green - 23.0/255.0) > .001 ||
      fabs(marker.blue - 29.0/255.0) > .001)
    fail("staged theme was not loaded");
  GdkRGBA expected_background, expected_foreground;
  const char *theme_name = g_getenv("VAPOR_FACTORY_THEME");
  const char *bg = g_getenv("VAPOR_FACTORY_SELECTION_BG");
  const char *fg = g_getenv("VAPOR_FACTORY_SELECTION_FG");
  if (!theme_name || !bg || !fg || !gdk_rgba_parse(&expected_background, bg) ||
      !gdk_rgba_parse(&expected_foreground, fg)) fail("missing expected family palette");
  char *actual_theme = NULL;
  g_object_get(gtk_settings_get_default(), "gtk-theme-name", &actual_theme, NULL);
  if (g_strcmp0(actual_theme, theme_name)) fail("wrong named theme");
  g_free(actual_theme);
  if (!gtk_style_context_lookup_color(context, "theme_selected_bg_color", &background) ||
      fabs(background.red - expected_background.red) > .001 || fabs(background.green - expected_background.green) > .001 ||
      fabs(background.blue - expected_background.blue) > .001)
    fail("wrong selection background");
  if (!gtk_style_context_lookup_color(context, "theme_selected_fg_color", &foreground) ||
      fabs(foreground.red - expected_foreground.red) > .001 || fabs(foreground.green - expected_foreground.green) > .001 ||
      fabs(foreground.blue - expected_foreground.blue) > .001)
    fail("wrong selection foreground");
  G_GNUC_END_IGNORE_DEPRECATIONS
  int width = gtk_widget_get_width(page), height = gtk_widget_get_height(page);
  if (width < 200 || height < 200) fail("page has no useful allocation");
  /* Consume pending layout on this private test display before snapshotting. */
  gtk_widget_allocate(page, width, height, -1, NULL);
  GtkSnapshot *snapshot = gtk_snapshot_new();
  G_GNUC_BEGIN_IGNORE_DEPRECATIONS
  gtk_snapshot_render_background(snapshot, gtk_widget_get_style_context(GTK_WIDGET(main_window)),
                                 0, 0, width, height);
  G_GNUC_END_IGNORE_DEPRECATIONS
  gtk_widget_snapshot_child(gtk_widget_get_parent(page), page, snapshot);
  GskRenderNode *node = gtk_snapshot_free_to_node(snapshot);
  if (!node) {
    if (++attempts < 10) return G_SOURCE_CONTINUE;
    fail("page snapshot stayed empty");
  }
  GskRenderer *renderer = gsk_cairo_renderer_new();
  GError *error = NULL;
  if (!gsk_renderer_realize(renderer, NULL, &error)) fail(error->message);
  graphene_rect_t viewport = GRAPHENE_RECT_INIT(0, 0, width, height);
  GdkTexture *texture = gsk_renderer_render_texture(renderer, node, &viewport);
  const char *directory = g_getenv("VAPOR_FACTORY_OUTPUT");
  if (!directory) fail("missing output directory");
  char *filename = g_strdup_printf("%s-%s-%s.png", page_name, state_name, dark ? "dark" : "normal");
  char *path = g_build_filename(directory, filename, NULL);
  if (!gdk_texture_save_to_png(texture, path)) fail("could not save screenshot");
  int mapped = count_mapped(page);
  if (mapped < 20) fail("page did not map its controls");
  g_print("VAPOR_FACTORY_RESULT {\"page\":\"%s\",\"state\":\"%s\",\"dark\":%s,"
          "\"width\":%d,\"height\":%d,\"mapped_widgets\":%d,\"file\":\"%s\","
          "\"gtk\":\"%d.%d.%d\",\"theme\":\"%s\",\"theme_marker\":true}\n",
          page_name, state_name, dark ? "true" : "false", width, height, mapped, filename,
          gtk_get_major_version(), gtk_get_minor_version(), gtk_get_micro_version(), theme_name);
  g_free(path); g_free(filename); g_object_unref(texture);
  gsk_renderer_unrealize(renderer); g_object_unref(renderer); gsk_render_node_unref(node);
  g_application_quit(G_APPLICATION(gtk_window_get_application(main_window)));
  return G_SOURCE_REMOVE;
}

void gtk_window_present(GtkWindow *window) {
  static void (*original)(GtkWindow *);
  if (!original) original = dlsym(RTLD_NEXT, "gtk_window_present");
  if (!original) fail("could not find original GTK function");
  GtkApplication *application = gtk_window_get_application(window);
  const char *id = application ? g_application_get_application_id(G_APPLICATION(application)) : NULL;
  if (!main_window && id && strcmp(id, "org.gtk.WidgetFactory4") == 0) {
    GtkWidget *stack = find_id(GTK_WIDGET(window), "toplevel_stack");
    if (!stack || !GTK_IS_STACK(stack)) fail("factory layout changed: main stack not found");
    main_window = window; pages = GTK_STACK(stack);
    page_name = g_getenv("VAPOR_FACTORY_PAGE"); state_name = g_getenv("VAPOR_FACTORY_STATE");
    if (!page_name || (!g_str_equal(page_name,"page1") && !g_str_equal(page_name,"page2") && !g_str_equal(page_name,"page3")))
      fail("invalid test page");
    if (!state_name || (!g_str_equal(state_name,"normal") && !g_str_equal(state_name,"backdrop") && !g_str_equal(state_name,"rtl")))
      fail("invalid test state");
    dark = g_strcmp0(g_getenv("VAPOR_FACTORY_DARK"), "1") == 0;
    g_object_set(gtk_settings_get_default(), "gtk-enable-animations", FALSE,
                 "gtk-cursor-blink", FALSE, "gtk-interface-color-scheme",
                 dark ? GTK_INTERFACE_COLOR_SCHEME_DARK : GTK_INTERFACE_COLOR_SCHEME_LIGHT, NULL);
    gtk_stack_set_transition_type(pages, GTK_STACK_TRANSITION_TYPE_NONE);
    gtk_stack_set_visible_child_name(pages, page_name);
    gtk_window_set_default_size(window, 1100, 900);
    set_state(GTK_WIDGET(window));
    g_timeout_add(450, capture, NULL);
  }
  original(window);
}
