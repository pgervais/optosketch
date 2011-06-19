# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
import numpy as np


class BaselineItem(QtGui.QGraphicsPathItem):
    def __init__(self, ylocation=0., span=300.,
                 color=QtGui.QColor('gray'), *args):

        super(BaselineItem, self).__init__(*args)

        self.ylocation = ylocation
        self.path = QtGui.QPainterPath()
        self.path.moveTo(QtCore.QPointF(-span,ylocation))
        pen = QtGui.QPen(color)
        pen.setDashPattern([5,5])
        self.setPen(pen)
        self.path.lineTo(QtCore.QPointF(+span,ylocation))
        self.setPath(self.path)

        
