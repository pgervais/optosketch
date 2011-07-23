# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import QPointF

import logging
import numpy as np

default_color = QtGui.QColor('orange')
default_ray_pen = QtGui.QPen(QtGui.QColor('black'))
default_handle_pen = QtGui.QPen(QtGui.QColor('red'))
default_handle_pen.setWidth(3)
default_handle_brush = QtGui.QBrush(QtGui.QColor('red'))

class RayHandleItem(QtGui.QGraphicsPathItem):
    """Widget to show a ray's basepoint and unit vector."""
    def __init__(self, basepoint, unit,
                 pen=default_handle_pen,
                 brush = default_handle_brush,
                 radius=4,
                 *args, **kwargs):
        """basepoint, unit: numpy arrays (1x2)"""
        super(RayHandleItem, self).__init__(*args, **kwargs)

        self.pen = pen
        self.brush = brush
        self.basepoint = basepoint
        self.radius = radius

        self.setPen(self.pen)
        self.setBrush(self.brush)

        self.path = QtGui.QPainterPath()
        self._draw(basepoint, unit)
        self.setPath(self.path)

        self.setCursor(Qt.Qt.SizeAllCursor)
        self.__moving = False
        self.__rotating = False
        print (self.parentItem())


    def _draw(self, basepoint, unit):
        center = QtCore.QPointF(basepoint[0], basepoint[1])
        self.path.addEllipse(center, self.radius, self.radius)
        head = basepoint+30*unit
        self.path.moveTo(center)
        self.path.lineTo(QtCore.QPointF(head[0], head[1]))


    def update(self, basepoint, unit):
        """Update handle position and orientation."""
        self.path = QtGui.QPainterPath()
#        self.setPen(self.pen)
        self.basepoint = basepoint
        self._draw(basepoint, unit)
        self.setPath(self.path)
        
        
    def mousePressEvent(self, event):
        logging.debug('RayHandleItem: mouse press')
        pos = event.scenePos()
        dist = (self.basepoint[0] - pos.x()) ** 2 + \
               (self.basepoint[1] - pos.y()) ** 2
        if (dist > (self.radius ** 2)):
            self.__rotating = True
        else:
            self.__moving = True


    def mouseReleaseEvent(self, event):
        self.__moving = False
        self.__rotating = False


    def mouseMoveEvent(self, event):
        current = event.scenePos()
        parent = self.parentItem()
        if self.__moving:
            parent.backend.set_ray_point(parent, current.x(), current.y())
        if self.__rotating:
            bpt = self.basepoint
            dir_vec = np.asarray((current.x() - bpt[0], current.y() - bpt[1]))
            parent.backend.set_ray_direction(parent, dir_vec)


class RayItem(QtGui.QGraphicsPathItem):
    def __init__(self, polyline, basepoint, unit,
                 color=default_color, backend=None, *args):
        """polyline : numpy array, defining ray as a polyline.
        basepoint, unit: point through which the ray passes, and unit vector
        along the ray at that point."""
        super(RayItem, self).__init__(*args)

        self.path = QtGui.QPainterPath()
        self._draw_polyline(polyline, color=color)
        self.setPath(self.path)
        self.handle = RayHandleItem(basepoint, unit, parent=self)
        self.backend = backend

    def _draw_polyline(self, polyline, color=default_color):
        """Draw polyline in current path"""
        pen = QtGui.QPen(color)
        pen.setWidth(3)
        self.setPen(pen)

        self.path.moveTo(QPointF(polyline[0,0], polyline[0,1]))
        for k in polyline[1:,]:
#            print("point: "+str(k))
            self.path.lineTo(QPointF(k[0], k[1]))


    def update(self, polyline, basepoint, unit, color=default_color):
        """Change the shape of the ray. """
        self.path = QtGui.QPainterPath()
        self._draw_polyline(polyline, color=color)
        self.setPath(self.path)
        self.handle.update(basepoint, unit)

