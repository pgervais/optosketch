# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import QPointF
from point import PointItem
import numpy as np
import logging

class LensItem(QtGui.QGraphicsPathItem):
    def __init__(self, xlocation=0., ylocation=0., span=50.,
                 color=QtGui.QColor('gray'), kind=None,
                 focal = 50., backend=None, *args):

        super(LensItem, self).__init__(*args)

        self.xlocation = xlocation
        self.ylocation = ylocation
        self.backend = backend
        self.__moving = False
        super(LensItem, self).setPos(QPointF(xlocation, ylocation))

        # Item shape
        self.path = QtGui.QPainterPath()
        
        self.path.moveTo(QPointF(0., -span))
        pen = QtGui.QPen(color)
        pen.setWidth(2)
        self.setPen(pen)
        self.path.lineTo(QPointF(0., +span))

        # Draw arrows
        # TODO: compute "head" in a helper function
        dx = 5
        if focal > 0:
            dy = 6
        else:
            dy = -6
            
        head = QtGui.QPolygonF([QPointF(-dx, -dy+span),
                        QPointF(0., +span ),
                        QPointF(dx, -dy+span)])
        self.path.addPolygon(head)

        head = QtGui.QPolygonF([QPointF(-dx, dy -span),
                        QPointF(0., -span),
                        QPointF(dx, dy-span)])
        self.path.addPolygon(head)

        # Draw focal points as sub-objects
        focii = PointItem(QPointF(-focal, 0.), label='f', parent=self), \
                PointItem(QPointF( focal, 0.), label="f'", parent = self)
        
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.Qt.SizeHorCursor)

        self.setPath(self.path)


    def mousePressEvent(self, event):
        self.__startPos = event.pos()
        logging.debug("LensItem: mouse press: %d %d" % (self.__startPos.x(), self.__startPos.y()))
        self.__moving = True


    def mouseReleaseEvent(self, event):
        logging.debug("LensItem: mouse release.")
        self.__moving=False
        self.__startPos = None


    def mouseMoveEvent(self, event):
        if self.__moving :
            current = event.scenePos() - self.__startPos
            self.setPos(current.x(), self.ylocation)


    def setPos(self, x, y):
        newx, newy = x, y
        newx, newy=self.backend.set_lens_pos(self, x, y)
        super(LensItem, self).setPos(QPointF(newx,newy))
