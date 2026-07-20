from _example import ffi, lib

p = lib.getpwuid(0)
five = lib.addTwo(2, 3)

envDat = ffi.new("D_AttRel *")

envDat.AttCf = .5
envDat.RelCf = .1

lib.AttRelProc(envDat, 1)
lib.AttRelProc(envDat, 1)
lib.AttRelProc(envDat, 1)
