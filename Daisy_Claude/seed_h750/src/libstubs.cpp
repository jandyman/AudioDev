// libstubs.cpp — minimal stubs required when linking -lm without full newlib.
//
// newlib's math error handling layer calls __errno() to get a pointer to the
// thread-local errno variable. In a bare-metal single-threaded build there are
// no threads, so a plain global suffices.
//
// extern "C" so the symbol newlib looks for (`__errno`) is unmangled. Without
// it, libm's error reporting paths would fail to link.

static int _errno_val;

extern "C" int *__errno(void) {
  return &_errno_val;
}
