# file "example_build.py"

from cffi import FFI
ffi = FFI()

ffi.set_source("_example",
               """ // passed to the real C compiler
                   #include <sys/types.h>
                   #include <pwd.h>
                   #include "Envelopes.h"
                   double addTwo(double, double);
               """,
               libraries=[],
               sources = ['extrafunc.c', 'Envelopes.c'])   # or a list of libraries to link with
# (more arguments like setup.py's Extension class:
# include_dirs=[..], extra_objects=[..], and so on)

ffi.cdef("""     // some declarations from the man page
    struct passwd {
        char *pw_name;
        ...;     // literally dot-dot-dot
    };
    struct passwd *getpwuid(int uid);
""")

ffi.cdef("double addTwo(double a, double b);")

ffi.cdef("""typedef struct {
  float AttCf;
  float RelCf;
  float PrevOut;
} D_AttRel;
""")

ffi.cdef("void AttRelProc(D_AttRel* s, float newSamp);")

if __name__ == "__main__":
  ffi.compile()