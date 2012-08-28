# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import QPointF
from point import PointItem
import numpy as np
import logging

class FocalPointItem(PointItem):
    """Sub-object of LensItem"""
    def __init__(self, *args, **kwargs):
        self.principal = kwargs["principal"]
        del kwargs['principal']
        super(FocalPointItem, self).__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.Qt.SizeHorCursor)
        self.__moving = False

    def mousePressEvent(self, event):
        logging.debug('FocalPointItem: mouse press %d' % self.x())
        self.__moving = True
        self.__startPosX = self.scenePos().x() - self.x()
        print (self.__startPosX)
        
    def mouseReleaseEvent(self, event):
        logging.debug('FocalPointItem: mouse release')
        self.__moving = False
        
    def mouseMoveEvent(self, event):
        logging.debug('FocalPointItem: mouse move %d' % self.x())
        focal = event.scenePos().x() - self.__startPosX
        if self.__moving and self.principal:
            self.parentItem().set_focal_length(focal)
        elif self.__moving and not self.principal:
            self.parentItem().set_focal_length(-focal)


class LensItem(QtGui.QGraphicsPathItem):
    def __init__(self, xlocation=0., ylocation=0., span=50.,
                 color=QtGui.QColor('gray'), kind=None,
                 focal = 50., backend=None, *args):

        super(LensItem, self).__init__(*args)

        self.xlocation = xlocation
        self.ylocation = ylocation
        self.backend = backend
        self._focal = focal
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
        if self._focal > 0:
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
        self.focii = FocalPointItem(label='f', parent=self, principal=True), \
                     FocalPointItem(label="f'", parent = self, principal=False)
        
        self.setFlag(self.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.Qt.SizeHorCursor)

        self.setPath(self.path)
        self.update(self.xlocation, self.ylocation, self._focal)


    def set_focal_length(self, focal):
        """Change focal length. To be called by FocalPointItem."""
        self.backend.set_lens_focal(self, focal)


    def keyPressEvent(self, event):
        key = event.key()
        
        if key == Qt.Qt.Key_Plus:
            self.backend.set_lens_focal(self, self._focal+1)
        elif key == Qt.Qt.Key_Minus:
            self.backend.set_lens_focal(self, self._focal-1)
        elif key == Qt.Qt.Key_PageUp:
            self.backend.set_lens_focal(self, self._focal+10)
        elif key == Qt.Qt.Key_PageDown:
            self.backend.set_lens_focal(self, self._focal-10)
        elif key == Qt.Qt.Key_Enter:
            print (self.x(), self.y())
            self.update(self.x(), self.y(), 0)

            
    def hoverEnterEvent(self, event):
        logging.debug('entering lens')
        self.setFocus() # in order to get key events
        
    def hoverLeaveEvent(self, event):
        logging.debug('leaving lens')
        self.clearFocus()
        

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
            self.backend.set_lens_pos(self, current.x(), self.ylocation)
#            print("mouse move (lens): ", current.x(), current.y())

    def update(self, xpos, ypos, focal):
        logging.debug('updating lens: %d, %d, %d' % (xpos, ypos, focal))
        self.xlocation = xpos
        self.ylocation = ypos
        self._focal = focal

        self.setPos(xpos, ypos)
        self.focii[0].setPos(QPointF( self._focal, 0.))
        self.focii[1].setPos(QPointF(-self._focal, 0.))
