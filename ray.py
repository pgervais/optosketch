# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QPointF
import numpy as np

class RayItem(QtGui.QGraphicsPathItem):
    def __init__(self, polyline, color=QtGui.QColor('orange'), *args):
        """polyline : numpy array, defining ray as a polyline."""
        super(RayItem, self).__init__(*args)

        self._polyline = polyline

        self.path = QtGui.QPainterPath()
        pen = QtGui.QPen(color)
        pen.setWidth(3)
        self.setPen(pen)

        # Draw polyline
        print ("polyline: "+str(polyline))
        self.path.moveTo(QPointF(polyline[0,0], polyline[0,1]))
        for k in polyline[1:,]:
            print("point: "+str(k))
            self.path.lineTo(QPointF(k[0], k[1]))

        self.setPath(self.path)
