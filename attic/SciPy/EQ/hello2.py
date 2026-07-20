
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.use("MacOSX")
plt.ion()
fig = plt.figure()
x = [0, 1, 1,   2,    2,    10, 10, 20]
y = [0, 0, 100, 100, -12.5, -12.5, 0, 0]
plot = plt.plot(x, y)       # Plot the sine of each x point
plt.grid(True)
axes = fig.axes[0]
axes.set_xlabel('uSec')
axes.set_ylabel('uA')
#x = np.linspace(0, 20, 100)  # Create a list of evenly-spaced numbers over the range
#plt.plot(x, np.sin(x))       # Plot the sine of each x point
plt.show() 
# put a breakpoint on this next line 
y = 5

