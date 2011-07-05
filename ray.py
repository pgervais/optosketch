# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QPointF
import numpy as np

default_color = QtGui.QColor('orange')

class RayItem(QtGui.QGraphicsPathItem):
    def __init__(self, polyline, color=default_color, *args):
        """polyline : numpy array, defining ray as a polyline."""
        super(RayItem, self).__init__(*args)

        self.path = QtGui.QPainterPath()
        self._draw_polyline(polyline, color=color)
        self.setPath(self.path)


    def _draw_polyline(self, polyline, color=default_color):
        """Draw polyline in current path"""
        pen = QtGui.QPen(color)
        pen.setWidth(3)
        self.setPen(pen)

        self.path.moveTo(QPointF(polyline[0,0], polyline[0,1]))
        for k in polyline[1:,]:
            print("point: "+str(k))
            self.path.lineTo(QPointF(k[0], k[1]))


    def update(self, polyline, color=default_color):
        """Change the shape of the ray. """
        self.path = QtGui.QPainterPath()
        self._draw_polyline(polyline, color=color)
        self.setPath(self.path)
