# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
import numpy as np
import time
from frontend import GenericLine

class StrokeItem(QtGui.QGraphicsPathItem, GenericLine):
    def __init__(self, pos=QtCore.QPointF(0.,0.), 
                 color=QtGui.QColor('black'), width = 1, *args, **kwargs):
        """pos is initial position. """
        super(StrokeItem, self).__init__(*args, **kwargs)
        self.path = QtGui.QPainterPath()
        self.path.moveTo(pos)
        self.setPath(self.path)
        pen = QtGui.QPen(color)
        pen.setWidth(width)
        self.setPen(pen)
        self._time = time.time()


    def lineTo(self, *pos):
        """Add a new point to the line.""" 
        self.path.lineTo(*pos)
        _time = time.time()
        if _time - self._time > 0.1: # Avoid updating every time
            self.setPath(self.path)
            self._time = _time


    def clear(self):
        """Remove every points from the path."""
        self.path = QtGui.QPainterPath()


    def tonumpy(self):
        """Get current path as a numpy array."""
        coords = []
        for n in xrange(self.path.elementCount()):
            elem = self.path.elementAt(n) 
            coords.append([elem.x, elem.y])
        return np.asarray(coords)


    def fromnumpy(self,coords):
        """Set current path with a numpy array.
        This method does an append. Use clear()
        to remove every point before appending."""
        self.path.moveTo(coords[0,0], coords[0,1])
        for l in coords[1:]:
            self.path.lineTo(l[0], l[1])

        self.setPath(self.path)


    def save(self, filename):
        """Save the stroke in a file (for debugging)."""
        np.savetxt(filename, self.tonumpy())

