# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore 
from mainwindow import Ui_MainWindow
from backend import RecognitionEngine


class Board(QtGui.QMainWindow):
  def __init__(self, parent=None):
    QtGui.QMainWindow.__init__(self, parent)
    self.ui = Ui_MainWindow()
    self.ui.setupUi(self)


class Application(QtGui.QApplication):
  def __init__(self, argv):
    QtGui.QApplication.__init__(self, argv)
    self.engine = RecognitionEngine()
    self.window = Board()
    self.window.show()


if __name__ == "__main__":
  import sys
  a = Application(sys.argv)  
  sys.exit(a.exec_())

