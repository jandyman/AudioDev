import matplotlib.pyplot as plt
import scipy
import scipy.signal
import scipy.signal.windows
import numpy
import numpy.random

# set up the input bit pattern
x = numpy.zeros(29*2)
x = numpy.append(x, numpy.ones(29))
x = numpy.append(x, numpy.zeros(29))
x = numpy.append(x, numpy.ones(29*2))
x = numpy.append(x, numpy.zeros(29*2))
r = numpy.random.rand(x.size)
r = r / 1.5
x = x + r
# simple window filter
ir = numpy.ones(29)
ir = ir / scipy.sum(ir)
y1 = scipy.signal.lfilter(ir, 1, x)
# hamming 29 long
ir = scipy.signal.windows.hamming(29)
ir = ir / scipy.sum(ir)
y2 = scipy.signal.lfilter(ir, 1, x)
# hamming 10 long
ir = scipy.signal.windows.hamming(10)
ir = ir / scipy.sum(ir)
y3 = scipy.signal.lfilter(ir, 1, x)

plt.ion()
plt.plot(x)
plt.plot(y1)
plt.plot(y2)
plt.plot(y3)
plt.draw()

