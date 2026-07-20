from cffi import FFI
ffi = FFI()

ffi.cdef("""
// some declarations from the man page
typedef struct {
  float AttCf;
  float RelCf;
  float PrevOut;
} D_AttRel;

void AttRelProc(D_AttRel* s, float newSamp);

""")

#lib = ffi.dlopen('/Users/Andy/Library/Developer/Xcode/DerivedData/DspFuncs-fklguxxfrrturbgtdpuuvflenbts/Build/Products/Debug/libDspFuncs.dylib')
lib = ffi.dlopen('libDspFuncs.dylib')

envDat = ffi.new("D_AttRel *")

envDat.AttCf = .5
envDat.RelCf = .1

lib.AttRelProc(envDat, 1)
lib.AttRelProc(envDat, 1)
lib.AttRelProc(envDat, 1)
