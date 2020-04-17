import sys
import random
import matplotlib
matplotlib.use('Qt5Agg')

from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas, 
                                                NavigationToolbar2QT as NavigationToolbar)

from matplotlib.figure import Figure
from flat_response_sequence import test_level, get_response

import sounddevice as sd
sd.default.device = 1

class MplCanvas(FigureCanvas):

  def __init__(self, parent=None, width=5, height=4, dpi=100):
    self.figure = fig = Figure(figsize=(width, height), dpi=dpi)
    self.axes = fig.add_subplot(111)
    super(MplCanvas, self).__init__(fig)


class MainWindow(QtWidgets.QMainWindow):

  def __init__(self, *args, **kwargs):
    super(MainWindow, self).__init__(*args, **kwargs)

    # Create a placeholder widget to hold our toolbar and canvas.
    self.mainWidget = QtWidgets.QWidget()
    self.setWindowTitle('Pickup Analyzer')

    sc = self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
    toolbar = NavigationToolbar(sc, self)
    button = QtWidgets.QPushButton('Press Me', self.mainWidget)
    button.clicked.connect(self.update_plot)
    layout = QtWidgets.QVBoxLayout()
    layout.addWidget(toolbar)
    layout.addWidget(sc)
    layout.addWidget(button)
    
    self.mainWidget.setLayout(layout)
    self.setCentralWidget(self.mainWidget)

    #self.update_plot()
    self.canvas.draw()
    self.canvas.repaint()
    self.show()

  def update_plot(self):
    #data = [random.random() for i in range(self.update_count)]
    response = get_response(16384, plot=False)
    sc = self.canvas
    sc.axes.cla()
    sc.axes.semilogx(response)
    sc.axes.grid(True, which='major')
    sc.axes.grid(True, which='minor', linestyle="--")
    
    # Trigger the canvas to update and redraw.
    self.canvas.draw()
    self.canvas.repaint()

if __name__ == "__main__":
  def run_app():
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    app.exec_()
    app.setApplicationName("Pickup Analyzer")
  run_app()