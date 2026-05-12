// libstubs.c — minimal stubs required when linking -lm without full newlib.
//
// newlib's math error handling layer calls __errno() to get a pointer to the
// thread-local errno variable. In a bare-metal single-threaded build there are
// no threads, so a plain global suffices.

static int _errno_val;

int *__errno(void) {
  return &_errno_val;
}
