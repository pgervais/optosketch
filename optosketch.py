# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore 
from mainwindow import Ui_MainWindow
from backend import RecognitionEngine
import logging

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

  logging.addLevelName(5, "DEBUG2")
  logging.getLogger().setLevel(logging.DEBUG)
#  logging.getLogger().setLevel(5)
  ch = logging.StreamHandler()
#  ch.setLevel(logging.DEBUG)
  formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
  ch.setFormatter(formatter)
  logging.getLogger().addHandler(ch)
  logging.debug('Debug logging activated')

  a = Application(sys.argv)
  sys.exit(a.exec_())

