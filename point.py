# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
import numpy as np
from frontend import GenericPoint

class PointItem(QtGui.QGraphicsPathItem, GenericPoint):
    """Object that represents a geometrical point.
    It is shown as a small circle on the canvas."""
    def __init__(self, pos=QtCore.QPointF(0.,0.), 
                 color=QtGui.QColor('black'), 
                 radius = 3, label=None,
                 *args, **kwargs):
        """pos is point position. radius is circle radius."""
        super(PointItem, self).__init__(*args, **kwargs)
        self.path = QtGui.QPainterPath()
        self.path.addEllipse(pos, radius, radius)
        self.setPen(QtGui.QPen(color))
        self.setPath(self.path)
        self.radius = radius
        self.__x = pos.x()
        self.__y = pos.y()
        ## FIXME: devise a better placement algorithm.
        if not label is None:
            QtGui.QGraphicsSimpleTextItem(label, parent=self
                                          ).moveBy(self.__x,self.__y+self.radius)
