# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
import numpy as np


class StrokeItem(QtGui.QGraphicsPathItem):
    def __init__(self, pos=QtCore.QPointF(0.,0.), 
                 color=QtGui.QColor('black'), *args):
        """pos is initial position. """
        super(StrokeItem, self).__init__(*args)
        self.path = QtGui.QPainterPath()
        self.path.moveTo(pos)
        self.setPath(self.path)
        self.setPen(QtGui.QPen(color))

    def lineTo(self, *pos):
        """Add a new point to the line.""" 
        self.path.lineTo(*pos)
        self.setPath(self.path)


    def clear(self):
        """Remove every points from the path."""
        # tbd


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
        to remove every points before appending."""
        self.path.moveTo(coords[0,0], coords[0,1])
        for l in coords[1:]:
            self.lineTo(l[0], l[1])
