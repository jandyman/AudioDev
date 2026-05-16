// libstubs.cpp — minimal stubs required when linking -lm / -lgcc without full newlib.

#include <stddef.h>

// newlib libm calls __errno() to get a pointer to the thread-local errno.
// In a bare-metal single-threaded build a plain global suffices.
static int _errno_val;
extern "C" int *__errno(void) {
  return &_errno_val;
}

// SEGGER_RTT.c calls memset() to zero its control block in _DoInit().
// Provide a minimal implementation; -nostdlib means there is no libc to pull
// one from and -lgcc does not include string functions.
extern "C" void *memset(void *s, int c, size_t n) {
  unsigned char *p = static_cast<unsigned char *>(s);
  while (n--) { *p++ = static_cast<unsigned char>(c); }
  return s;
}

// __builtin_memcpy on large buffers (e.g. the 384-byte CMD_AUDIO_BLOCK payload)
// emits a call to memcpy rather than inlining. Same situation as memset above.
extern "C" void *memcpy(void *dst, const void *src, size_t n) {
  unsigned char *d = static_cast<unsigned char *>(dst);
  const unsigned char *s = static_cast<const unsigned char *>(src);
  while (n--) { *d++ = *s++; }
  return dst;
}
