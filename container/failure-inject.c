#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int configured_errno(void) {
  const char *name = getenv("ASD_FAIL_ERRNO");
  if (!name) return 0;
  if (strcmp(name, "EACCES") == 0) return EACCES;
  if (strcmp(name, "EEXIST") == 0) return EEXIST;
  if (strcmp(name, "EIO") == 0) return EIO;
  if (strcmp(name, "ENOSPC") == 0) return ENOSPC;
  if (strcmp(name, "EROFS") == 0) return EROFS;
  return 0;
}

static int is_write_flags(int flags) {
  return (flags & O_WRONLY) || (flags & O_RDWR) || (flags & O_CREAT) ||
         (flags & O_TRUNC) || (flags & O_APPEND);
}

static int matches_target(const char *pathname) {
  const char *target = getenv("ASD_FAIL_PATH");
  if (!target || !pathname) return 0;
  if (pathname[0] == '/') return strcmp(pathname, target) == 0;
  char cwd[PATH_MAX];
  char resolved[PATH_MAX];
  if (!getcwd(cwd, sizeof(cwd))) return 0;
  if (snprintf(resolved, sizeof(resolved), "%s/%s", cwd, pathname) >= (int)sizeof(resolved)) return 0;
  return strcmp(resolved, target) == 0;
}

static int reject(const char *pathname, int flags) {
  int err = configured_errno();
  if (err && is_write_flags(flags) && matches_target(pathname)) {
    errno = err;
    return 1;
  }
  return 0;
}

int open(const char *pathname, int flags, ...) {
  static int (*real_open)(const char *, int, ...) = NULL;
  if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
  mode_t mode = 0;
  if (flags & O_CREAT) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
  if (reject(pathname, flags)) return -1;
  return (flags & O_CREAT) ? real_open(pathname, flags, mode) : real_open(pathname, flags);
}

int open64(const char *pathname, int flags, ...) {
  static int (*real_open64)(const char *, int, ...) = NULL;
  if (!real_open64) real_open64 = dlsym(RTLD_NEXT, "open64");
  mode_t mode = 0;
  if (flags & O_CREAT) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
  if (reject(pathname, flags)) return -1;
  return (flags & O_CREAT) ? real_open64(pathname, flags, mode) : real_open64(pathname, flags);
}

int openat(int dirfd, const char *pathname, int flags, ...) {
  static int (*real_openat)(int, const char *, int, ...) = NULL;
  if (!real_openat) real_openat = dlsym(RTLD_NEXT, "openat");
  mode_t mode = 0;
  if (flags & O_CREAT) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
  if ((dirfd == AT_FDCWD || pathname[0] == '/') && reject(pathname, flags)) return -1;
  return (flags & O_CREAT) ? real_openat(dirfd, pathname, flags, mode) : real_openat(dirfd, pathname, flags);
}

int openat64(int dirfd, const char *pathname, int flags, ...) {
  static int (*real_openat64)(int, const char *, int, ...) = NULL;
  if (!real_openat64) real_openat64 = dlsym(RTLD_NEXT, "openat64");
  mode_t mode = 0;
  if (flags & O_CREAT) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
  if ((dirfd == AT_FDCWD || pathname[0] == '/') && reject(pathname, flags)) return -1;
  return (flags & O_CREAT) ? real_openat64(dirfd, pathname, flags, mode) : real_openat64(dirfd, pathname, flags);
}

int creat(const char *pathname, mode_t mode) {
  static int (*real_creat)(const char *, mode_t) = NULL;
  if (!real_creat) real_creat = dlsym(RTLD_NEXT, "creat");
  if (reject(pathname, O_WRONLY | O_CREAT | O_TRUNC)) return -1;
  return real_creat(pathname, mode);
}
