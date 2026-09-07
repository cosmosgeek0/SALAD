#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef void (*Initialize)(const char *, const char *, const char *, const char *, const char *);
typedef void (*Start)(const char *, void (*)(char *));

static void report(char *data) {
    printf("PAWNS_SDK %s\n", data);
    fflush(stdout);
}

int main(void) {
    HMODULE library = LoadLibraryA("Z:\\app\\libpawns.dll");
    if (!library) {
        fprintf(stderr, "SDK load failed: Windows error %lu\n", GetLastError());
        return 1;
    }
    Initialize initialize = (Initialize)GetProcAddress(library, "Initialize");
    Start start = (Start)GetProcAddress(library, "StartMainRoutine");
    if (!initialize || !start || !getenv("PAWNS_ACCESS_TOKEN") || !getenv("PAWNS_DEVICE_ID")) return 1;
    initialize("pawnsapp-gui", "2.0.0", getenv("PAWNS_DEVICE_ID"), "windows", "https://bootstrap.pawns.app");
    start(getenv("PAWNS_ACCESS_TOKEN"), report);
    Sleep(INFINITE);
}
