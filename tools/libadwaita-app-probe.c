/* Test-only probe for a selected native libadwaita app on a private display.
 * Public GTK/Adw APIs only. No desktop input or application actions.
 */
#define _GNU_SOURCE
#include <adwaita.h>
#include <dlfcn.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static GtkWindow *window;
static int attempts;
static struct timespec idle_cpu_start;
static gint64 idle_wall_start;
static void fail(const char *message) { g_printerr("ADW APP FAILED: %s\n",message);_exit(2); }

static gboolean finish_idle(gpointer unused) {
  (void)unused;
  struct timespec end;clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&end);
  double cpu_ms=(end.tv_sec-idle_cpu_start.tv_sec)*1000.0+(end.tv_nsec-idle_cpu_start.tv_nsec)/1000000.0;
  g_print("VAPOR_ADW_IDLE {\"cpu_ms\":%.3f,\"wall_ms\":%.3f}\n",cpu_ms,(g_get_monotonic_time()-idle_wall_start)/1000.0);
  g_application_quit(G_APPLICATION(gtk_window_get_application(window)));return G_SOURCE_REMOVE;
}

static gboolean begin_idle(gpointer unused) {
  (void)unused;
  clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&idle_cpu_start);idle_wall_start=g_get_monotonic_time();
  guint seconds=(guint)g_ascii_strtoull(g_getenv("VAPOR_APP_IDLE_SECONDS"),NULL,10);
  g_timeout_add(seconds*1000,finish_idle,NULL);return G_SOURCE_REMOVE;
}

static int mapped(GtkWidget *widget) {
  int n=gtk_widget_get_mapped(widget)?1:0;
  for (GtkWidget *c=gtk_widget_get_first_child(widget);c;c=gtk_widget_get_next_sibling(c)) n+=mapped(c);
  return n;
}

static GdkRGBA variable(const char *name) {
  GtkCssProvider *provider=gtk_css_provider_new();
  char *css=g_strdup_printf(".vapor-app-query { color: var(--%s); }",name);
  gtk_css_provider_load_from_string(provider,css);g_free(css);
  G_GNUC_BEGIN_IGNORE_DEPRECATIONS
  gtk_style_context_add_provider_for_display(gtk_widget_get_display(GTK_WIDGET(window)),GTK_STYLE_PROVIDER(provider),GTK_STYLE_PROVIDER_PRIORITY_USER);
  G_GNUC_END_IGNORE_DEPRECATIONS
  gtk_widget_add_css_class(GTK_WIDGET(window),"vapor-app-query");
  GdkRGBA rgba;gtk_widget_get_color(GTK_WIDGET(window),&rgba);
  gtk_widget_remove_css_class(GTK_WIDGET(window),"vapor-app-query");
  G_GNUC_BEGIN_IGNORE_DEPRECATIONS
  gtk_style_context_remove_provider_for_display(gtk_widget_get_display(GTK_WIDGET(window)),GTK_STYLE_PROVIDER(provider));
  G_GNUC_END_IGNORE_DEPRECATIONS
  g_object_unref(provider);return rgba;
}

static gboolean capture(gpointer unused) {
  (void)unused;
  GdkRGBA accent=variable("accent-bg-color"),text=variable("accent-fg-color"),bg=variable("window-bg-color");
  gboolean baseline=g_strcmp0(g_getenv("VAPOR_APP_BASELINE"),"1")==0;
  int red=baseline?53:86,green=baseline?132:159,blue=baseline?228:204;
  if (fabs(accent.red*255-red)>.1 || fabs(accent.green*255-green)>.1 || fabs(accent.blue*255-blue)>.1)
    fail("wrong computed accent");
  if (!baseline && (fabs(text.red*255-31)>.1 || fabs(text.green*255-31)>.1 || fabs(text.blue*255-38)>.1))
    fail("wrong accent foreground");
  if (!baseline && (fabs(bg.red*255-36)>.1 || fabs(bg.green*255-39)>.1 || fabs(bg.blue*255-44)>.1))
    fail("wrong window surface");
  GtkWidget *child=gtk_window_get_child(window);
  int width=gtk_widget_get_width(child),height=gtk_widget_get_height(child);
  if (width<200 || height<200 || mapped(child)<15) fail("application did not map useful content");
  GtkSnapshot *snap=gtk_snapshot_new();
  G_GNUC_BEGIN_IGNORE_DEPRECATIONS
  gtk_snapshot_render_background(snap,gtk_widget_get_style_context(GTK_WIDGET(window)),0,0,width,height);
  G_GNUC_END_IGNORE_DEPRECATIONS
  gtk_widget_allocate(child,width,height,-1,NULL);
  gtk_widget_snapshot_child(GTK_WIDGET(window),child,snap);
  GskRenderNode *node=gtk_snapshot_free_to_node(snap);
  if (!node) {if (++attempts<8)return G_SOURCE_CONTINUE;fail("empty app snapshot");}
  GskRenderer *renderer=gsk_cairo_renderer_new();GError *error=NULL;
  if (!gsk_renderer_realize(renderer,NULL,&error))fail(error->message);
  graphene_rect_t rect=GRAPHENE_RECT_INIT(0,0,width,height);
  GdkTexture *texture=gsk_renderer_render_texture(renderer,node,&rect);
  const char *file=g_getenv("VAPOR_APP_IMAGE");
  if (!file || !gdk_texture_save_to_png(texture,file))fail("could not save capture");
  g_print("VAPOR_ADW_APP {\"width\":%d,\"height\":%d,\"mapped_widgets\":%d,\"accent\":[%d,%d,%d],\"baseline\":%s}\n",
          width,height,mapped(child),red,green,blue,baseline?"true":"false");
  g_object_unref(texture);gsk_renderer_unrealize(renderer);g_object_unref(renderer);gsk_render_node_unref(node);
  const char *idle=g_getenv("VAPOR_APP_IDLE_SECONDS");
  if (idle && g_ascii_strtoull(idle,NULL,10)>0)g_timeout_add(300,begin_idle,NULL);
  else g_application_quit(G_APPLICATION(gtk_window_get_application(window)));
  return G_SOURCE_REMOVE;
}

void gtk_window_present(GtkWindow *candidate) {
  static void (*original)(GtkWindow*);
  if (!original)original=dlsym(RTLD_NEXT,"gtk_window_present");
  if (!original)fail("could not find original GTK entry point");
  GtkApplication *app=gtk_window_get_application(candidate);
  const char *id=app?g_application_get_application_id(G_APPLICATION(app)):NULL;
  const char *expected=g_getenv("VAPOR_APP_ID");
  if (!window && id && expected && strcmp(id,expected)==0) {
    window=candidate;
    adw_style_manager_set_color_scheme(adw_style_manager_get_default(),ADW_COLOR_SCHEME_FORCE_DARK);
    g_object_set(gtk_settings_get_default(),"gtk-enable-animations",FALSE,"gtk-cursor-blink",FALSE,NULL);
    g_timeout_add(1200,capture,NULL);
  }
  original(candidate);
}
