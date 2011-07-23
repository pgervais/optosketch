# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
import time
import logging

from stroke import StrokeItem
from point import PointItem
from baseline import BaselineItem
from lens import LensItem
from ray import RayItem
from frontend import FrontEnd


class FrontEndCanvas(FrontEnd):
  """Used for communication with backend. Must implement
  methods defined in frontend.FrontEnd."""

  def __init__(self, scene):
    self.scene = scene


  def remove_object(self, frontend_object):
    self.scene.removeItem(frontend_object)
    

  def add_point(self, x,y, kind=None):

    if kind == "intersection":
      color = QtGui.QColor('blue')
      radius = 3
    else:
      color = QtGui.QColor('red')
      radius = 5
      
    sl = PointItem(QtCore.QPointF(x,y), 
                   color=color, radius = radius)
    self.scene.addItem(sl)
    return sl


  def add_line(self, line, kind=None):
    """Add a polyline"""

    if kind == "simplified":
      color = QtGui.QColor('red')
      width = 1
    elif kind == "loop":
      color = QtGui.QColor("lightgreen")
      width = 2
    else:
      color = QtGui.QColor('black')
      width = 1

    sl = StrokeItem(color=color, width=width)
    sl.fromnumpy(line)
    self.scene.addItem(sl)
    return sl


  def add_baseline(self, ylocation,span):
    """Add a baseline"""

    bl = BaselineItem(ylocation, span)
    self.scene.addItem(bl)
    return bl


  def add_lens(self, xlocation, baseline, span, focal=50., kind=None):
      """Add a lens to a baseline.
      xlocation: horizontal coordinate along baseline. 
      baseline: frontend object returned by add_baseline().
      span: half-size of lens (distance between center and one extreme
              point)
      kind: "diverging" or "converging" (or "negative"/"positive") or None if the kind
            is still undefined
      """
      lens = LensItem(xlocation, baseline.ylocation,
                      backend = self.scene.engine,
                      focal=focal, span=span, kind=kind)
      self.scene.addItem(lens)
      return lens


  def add_ray(self, polyline, basepoint, unit):
    """Add a ray to the canvas.
    poyline: numpy array
    basepoint: numpy array. Point through which the ray passes.
    unit: numpy array. Unit vector along the ray at the basepoint."""
    ray = RayItem(polyline, basepoint, unit, backend = self.scene.engine)
    self.scene.addItem(ray)
    return ray
  

class CanvasScene(QtGui.QGraphicsScene):
  """Qt scene for stroke board. Handles lines drawing. """
  def __init__(self, *args):
    super(CanvasScene, self).__init__(*args)
    self.pressed = False
    self.currentitem = None # stroke being drawn
    self.strokeitem = [] # list of all strokes

    # Recognition engine.
    self.frontend = FrontEndCanvas(self)
    self.engine = QtCore.QCoreApplication.instance().engine
    self.engine.set_frontend(self.frontend)
    

  def keyPressEvent(self, event):
    key = event.key()
    logging.debug("event.key(): "+str(key))

    # Display last stroke coordinates as a numpy array.
    if key == 80: # p (print)
      print ("last stroke:")
      print (self.strokeitem[-1].tonumpy())
      
    elif key == 83: # s (save) for debugging.
      dt = time.strftime("%Y%m%d%H%M%S")
      print("Saving every strokes. Time: %s" % dt)
      for n, stroke in enumerate(self.strokeitem):
        filename = "strokes/stroke_%s_%.2d.dat" % (dt, n)
        stroke.save(filename)
      
    elif key == 69: # e
      print "Existing objects: "+self.engine.content()
    else:
      super(CanvasScene, self).keyPressEvent(event)      


  def mousePressEvent(self, event):
    ret = super(CanvasScene, self).mousePressEvent(event)
    logging.debug("Mouse press (scene)."+str(ret))
    grabber = self.mouseGrabberItem()
    if not grabber is None:
      pass
    else:
      self.currentitem = StrokeItem(event.scenePos())
      self.strokeitem.append(self.currentitem)
      self.addItem(self.currentitem)


  def mouseMoveEvent(self, event):
    grabber = self.mouseGrabberItem()
    if not grabber is None:
      super(CanvasScene, self).mouseMoveEvent(event)
    elif self.currentitem: 
      self.currentitem.lineTo(event.scenePos())
    else:
      super(CanvasScene, self).mouseMoveEvent(event)


  def mouseReleaseEvent(self, event):
    logging.debug("Mouse release (scene).")
    if self.currentitem:
      self.removeItem(self.currentitem)
      self.engine.push_stroke(self.currentitem.tonumpy())
      self.currentitem = None
    else:
      super(CanvasScene, self).mouseReleaseEvent(event)


class CanvasView(QtGui.QGraphicsView):
  def __init__(self, *args):
    super(CanvasView, self).__init__(*args)
    scene = CanvasScene(self)
    scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
    scene.setSceneRect(-200, -200, 400, 400)
    self.setScene(scene)

    self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
    self.setViewportUpdateMode(QtGui.QGraphicsView.BoundingRectViewportUpdate)
    self.setRenderHint(QtGui.QPainter.Antialiasing)
    self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
    self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)

    scene.addItem(PointItem(QtCore.QPointF(0.,0.), 
                            color=QtGui.QColor('blue'),
                            radius = 3)
                  );
 #   text = scene.addText("foo bar")
 #   text.setPos(0,0)


