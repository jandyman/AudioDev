
CPPFLAGS += -I. -std=gnu++14 
VPATH = ..

coefgen.dylib: CoefGen.o
	$(CC) -shared -fpic -o coefgen.dylib CoefGen.o
	
CoefGen.o: CoefGen.hpp

%.o: %.cpp 
	$(CC) -c -o $@ $< $(CPPFLAGS)

