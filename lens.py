# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QPointF
from point import PointItem
import numpy as np


class LensItem(QtGui.QGraphicsPathItem):
    def __init__(self, xlocation=0., ylocation=0., span=50.,
                 color=QtGui.QColor('gray'), kind=None, *args):

        super(LensItem, self).__init__(*args)

        self.xlocation = xlocation
        self.ylocation = ylocation
        
        self.path = QtGui.QPainterPath()
        self.path.moveTo(QPointF(xlocation, -span + ylocation))
        pen = QtGui.QPen(color)
##         pen.setDashPattern([5,5])
        self.setPen(pen)
        self.path.lineTo(QPointF(xlocation, +span +ylocation))

        # Draw arrows
        # TODO: compute "head" in a helper function
        dx = 5
        dy = 6
        head = QtGui.QPolygonF([QPointF(xlocation-dx, -dy+span +ylocation),
                        QPointF(xlocation, +span +ylocation),
                        QPointF(xlocation+dx, -dy+span +ylocation)])
        self.path.addPolygon(head)

        head = QtGui.QPolygonF([QPointF(xlocation-dx, dy -span +ylocation),
                        QPointF(xlocation, -span +ylocation),
                        QPointF(xlocation+dx, dy-span +ylocation)])
        self.path.addPolygon(head)

        # Draw focal points as sub-objects
        f=50 # FIXME: pass this as a parameter to __init__
        focii = PointItem(QPointF(xlocation-f, ylocation), label='f', parent=self), \
                PointItem(QPointF(xlocation+f, ylocation), label="f'", parent = self)
        
        self.setPath(self.path)


