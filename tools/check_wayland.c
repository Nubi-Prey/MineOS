#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>
#include <string.h>
#include <dlfcn.h>

typedef void (*GLFWerrorfun)(int, const char*);

void error_cb(int error, const char* desc) {
    printf("[GLFW ERROR 0x%x]: %s\n", error, desc);
}

int main(int argc, char **argv) {
    printf("=========================================\n");
    printf("[DIAG] Starting Wayland / GLFW Diagnostic\n");
    printf("=========================================\n");
    printf("PID: %d, UID: %d, EUID: %d, GID: %d, EGID: %d\n", getpid(), getuid(), geteuid(), getgid(), getegid());
    
    const char *rtd = getenv("XDG_RUNTIME_DIR");
    const char *wld = getenv("WAYLAND_DISPLAY");
    const char *sst = getenv("XDG_SESSION_TYPE");
    printf("ENV XDG_RUNTIME_DIR: %s\n", rtd ? rtd : "<NULL>");
    printf("ENV WAYLAND_DISPLAY: %s\n", wld ? wld : "<NULL>");
    printf("ENV XDG_SESSION_TYPE: %s\n", sst ? sst : "<NULL>");

    if (rtd && wld) {
        char sockpath[256];
        snprintf(sockpath, sizeof(sockpath), "%s/%s", rtd, wld);
        struct stat st;
        if (stat(sockpath, &st) == 0) {
            printf("[OK] Socket %s exists! Mode: %o, UID: %d, GID: %d\n", sockpath, st.st_mode, st.st_uid, st.st_gid);
            if (access(sockpath, R_OK | W_OK) == 0) {
                printf("[OK] Socket %s is readable and writable!\n", sockpath);
            } else {
                printf("[FAIL] Socket %s access failed: %s (errno=%d)\n", sockpath, strerror(errno), errno);
            }
        } else {
            printf("[FAIL] Socket %s does NOT exist: %s (errno=%d)\n", sockpath, strerror(errno), errno);
        }
    }

    // Test libwayland-client
    void *wlc = dlopen("libwayland-client.so.0", RTLD_NOW | RTLD_GLOBAL);
    if (!wlc) {
        printf("[FAIL] dlopen(libwayland-client.so.0): %s\n", dlerror());
    } else {
        printf("[OK] dlopen(libwayland-client.so.0) succeeded\n");
        void *(*wl_conn)(const char*) = dlsym(wlc, "wl_display_connect");
        if (!wl_conn) {
            printf("[FAIL] dlsym(wl_display_connect): %s\n", dlerror());
        } else {
            errno = 0;
            void *disp = wl_conn(NULL);
            if (!disp) {
                printf("[FAIL] wl_display_connect(NULL) failed: %s (errno=%d)\n", strerror(errno), errno);
            } else {
                printf("[SUCCESS] wl_display_connect(NULL) returned %p!\n", disp);
            }
        }
    }

    // Test GLFW
    // Try to find libglfw.so in /tmp or native-libs
    const char *glfw_paths[] = {
        "/tmp/libglfw.so",
        "/usr/lib/libglfw.so",
        "/opt/mineos/native-libs/libglfw.so",
        NULL
    };
    void *glfw = NULL;
    for (int i = 0; glfw_paths[i]; i++) {
        glfw = dlopen(glfw_paths[i], RTLD_NOW | RTLD_GLOBAL);
        if (glfw) {
            printf("[OK] dlopen(%s) succeeded\n", glfw_paths[i]);
            break;
        }
    }
    if (!glfw) {
        glfw = dlopen("libglfw.so", RTLD_NOW | RTLD_GLOBAL);
    }
    if (!glfw) {
        printf("[WARN] dlopen(libglfw.so) failed: %s\n", dlerror());
    } else {
        void (*set_err)(GLFWerrorfun) = dlsym(glfw, "glfwSetErrorCallback");
        int (*init_hint)(int, int) = dlsym(glfw, "glfwInitHint");
        int (*init)(void) = dlsym(glfw, "glfwInit");
        int (*plat_supp)(int) = dlsym(glfw, "glfwPlatformSupported");
        
        if (set_err) set_err(error_cb);
        if (plat_supp) {
            printf("GLFW Platform Supported WAYLAND (0x60003): %d\n", plat_supp(0x60003));
            printf("GLFW Platform Supported X11 (0x60004): %d\n", plat_supp(0x60004));
        }
        
        if (init) {
            printf("--- Test 1: glfwInit() with DEFAULT hints (GLFW_ANY_PLATFORM) ---\n");
            int res1 = init();
            printf("glfwInit() default result: %d\n", res1);
            
            void (*term)(void) = dlsym(glfw, "glfwTerminate");
            if (term && res1) term();
            
            printf("--- Test 2: glfwInit() with GLFW_PLATFORM_WAYLAND hint ---\n");
            if (init_hint) {
                init_hint(0x50003, 0x60003);
            }
            int res2 = init();
            printf("glfwInit() Wayland hint result: %d\n", res2);
            if (term && res2) term();
        }
    }

    printf("=========================================\n");
    return 0;
}
