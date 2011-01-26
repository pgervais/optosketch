# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
import numpy as np

class PointItem(QtGui.QGraphicsPathItem):
    """Object that represents a geometrical point.
    It is shown as a small circle on the canvas."""
    def __init__(self, pos=QtCore.QPointF(0.,0.), 
                 color=QtGui.QColor('black'), 
                 radius = 3,
                 *args):
        """pos is point position. radius is circle radius."""
        super(PointItem, self).__init__(*args)
        self.path = QtGui.QPainterPath()
        self.path.addEllipse(pos, radius, radius)
        self.setPath(self.path)
        self.setPen(QtGui.QPen(color))

