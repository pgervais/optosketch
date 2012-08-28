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
        self.setCursor(Qt.Qt.SizeHorCursor)
        self.__moving = False

    def mousePressEvent(self, event):
        logging.debug('FocalPointItem: mouse press %d' % self.x())
        self.__moving = True
        # Use scene coordinates because element is moved by the backend while
        # dragging the mouse.
        self.__startPosX = self.scenePos().x() - self.x()
        
    def mouseReleaseEvent(self, event):
        logging.debug('FocalPointItem: mouse release')
        self.__moving = False
        
    def mouseMoveEvent(self, event):
        # logging.debug('FocalPointItem: mouse move %d' % self.x())
        focal = event.scenePos().x() - self.__startPosX
        if self.__moving and self.principal:
            self.parentItem().set_focal_length(focal)
        elif self.__moving and not self.principal:
            self.parentItem().set_focal_length(-focal)


class ArrowHeadItem(QtGui.QGraphicsPathItem):
    """Shape of an arrow-head."""
    def __init__(self, span=10., height=6., pen=None, angle=0, **kwargs):
        """height and span are longitudinal and transverse dimensions, resp.
        Head is center on (0,0), oriented towards the right (zero angle)"""

        super(ArrowHeadItem, self).__init__(**kwargs)
        self._span = span
        self._height = height
        self.setRotation(angle)
        head = QtGui.QPolygonF([QPointF(-height, span/2.),
                                QPointF(0., 0.),
                                QPointF(-height, -span/2.)
                                ])

        self.path = QtGui.QPainterPath()
        if pen is not None: self.setPen(pen)
        self.path.addPolygon(head)
        self.setPath(self.path)
        self.setCursor(Qt.Qt.SizeVerCursor)


    def mousePressEvent(self, event):
        logging.debug('ArrowHeadItem: mouse press %d' % self.x())
        self.__moving = True
        # Use scene coordinates because element is moved by the backend while
        # dragging the mouse.
        self.__startPosY = self.scenePos().y() - self.y()
        
    def mouseReleaseEvent(self, event):
        logging.debug('ArrowHeadItem: mouse release')
        self.__moving = False
        
    def mouseMoveEvent(self, event):
        # logging.debug('ArrowHeadItem: mouse move %d' % self.y())
        span = abs(event.scenePos().y() - self.__startPosY)
        if self.__moving:
            self.parentItem().set_span(span)


class LensItem(QtGui.QGraphicsPathItem):
    def __init__(self, xlocation=0., ylocation=0., span=50.,
                 pen = QtGui.QPen(QtGui.QColor('black')), kind=None,
                 focal = 50., backend=None, *args):

        super(LensItem, self).__init__(*args)
        self.setPos(QPointF(xlocation, ylocation))

        self.xlocation = xlocation
        self.ylocation = ylocation
        self.backend = backend
        self._focal = focal
        self._span = span
        self.__moving = False

        self.setPen(pen)
        
        # Draw arrow heads
        self.heads = (ArrowHeadItem(parent=self, angle=90., pen=pen),
                      ArrowHeadItem(parent=self, angle=-90., pen=pen))
        self.setup_heads()
        
        # Draw focal points as sub-objects
        self.foci = FocalPointItem(label="F'", parent=self, principal=True), \
                    FocalPointItem(label="F", parent = self, principal=False)
        
        self.setFlag(self.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.Qt.SizeHorCursor)
        self.update(self.xlocation, self.ylocation, self._focal, self._span)


    def setup_heads(self):
        """Update heads after a change of focal length."""
        if self._focal > 0:
            self.heads[0].setPos(QPointF(0., self._span))
            self.heads[1].setPos(QPointF(0., -self._span))
        else:
            self.heads[0].setPos(QPointF(0., -self._span))
            self.heads[1].setPos(QPointF(0., self._span))
        

    def set_focal_length(self, focal):
        """Change focal length. To be called by FocalPointItem."""
        self.backend.set_lens_focal(self, focal)

    def set_span(self, span):
        """Change lens span. To be called by ArrowHeadItem"""
        self.backend.set_lens_span(self, span)

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

    def update(self, xpos, ypos, focal, span=None):
        ## logging.debug('updating lens: %d, %d, %d' % (xpos, ypos, focal))
        self.xlocation = xpos
        self.ylocation = ypos
        self._focal = focal

        self.setPos(xpos, ypos)
        self.foci[0].setPos(QPointF( self._focal, 0.))
        self.foci[1].setPos(QPointF(-self._focal, 0.))
        self.setup_heads()

        # Item shape
        if span is not None:
            self._span = span
            self.path = QtGui.QPainterPath()        
            self.path.moveTo(QPointF(0., -span))
            self.path.lineTo(QPointF(0., +span))
            self.setPath(self.path)
