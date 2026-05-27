#include <stddef.h>
#include <stdint.h>

static int _errno_val;
extern "C" int* __errno(void) { return &_errno_val; }

extern "C" void* memset(void* s, int c, size_t n) {
  unsigned char* p = static_cast<unsigned char*>(s);
  while (n--) *p++ = static_cast<unsigned char>(c);
  return s;
}

extern "C" void* memcpy(void* dst, const void* src, size_t n) {
  unsigned char* d = static_cast<unsigned char*>(dst);
  const unsigned char* s = static_cast<const unsigned char*>(src);
  while (n--) *d++ = *s++;
  return dst;
}

extern "C" size_t strlen(const char* s) {
  size_t n = 0;
  while (*s++) ++n;
  return n;
}

extern "C" int strcmp(const char* a, const char* b) {
  while (*a && *a == *b) { ++a; ++b; }
  return (unsigned char)*a - (unsigned char)*b;
}

extern "C" int strncmp(const char* a, const char* b, size_t n) {
  while (n && *a && *a == *b) { ++a; ++b; --n; }
  if (!n) return 0;
  return (unsigned char)*a - (unsigned char)*b;
}

extern "C" const char* strchr(const char* s, int c) {
  while (*s) { if (*s == (char)c) return s; ++s; }
  return (c == '\0') ? s : nullptr;
}

// Bump allocator — Faust DSP objects are allocated once at init, never freed.
static uint8_t s_heap[128 * 1024] __attribute__((aligned(8)));
static size_t  s_heap_used = 0;

void* operator new(size_t n) noexcept {
  n = (n + 7u) & ~7u;
  if (s_heap_used + n > sizeof(s_heap)) return nullptr;
  void* p = s_heap + s_heap_used;
  s_heap_used += n;
  return p;
}
void* operator new[](size_t n) noexcept { return operator new(n); }
void  operator delete(void*) noexcept {}
void  operator delete[](void*) noexcept {}
void  operator delete(void*, size_t) noexcept {}
void  operator delete[](void*, size_t) noexcept {}
