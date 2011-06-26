# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
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


  def add_point(self, x,y, kind=None):
    sl = PointItem(QtCore.QPointF(x,y), 
                   color=QtGui.QColor('red'), radius = 5)
    self.scene.addItem(sl)
    return sl


  def add_line(self, line, kind=None):
    """Add a polyline"""

    if kind == "simplified":
      color = QtGui.QColor('red')
    else:
      color = QtGui.QColor('black')
      
    sl = StrokeItem(color=color)
    sl.fromnumpy(line)
    self.scene.addItem(sl)
    return sl


  def add_baseline(self, ylocation,span):
    """Add a baseline"""

    bl = BaselineItem(ylocation, span)
    self.scene.addItem(bl)
    return bl


  def add_lens(self, xlocation, baseline, span, kind=None):
      """Add a lens to a baseline.
      xlocation: horizontal coordinate along baseline. 
      baseline: frontend object returned by add_baseline().
      span: half-size of lens (distance between center and one extreme
              point)
      kind: "diverging" or "converging" (or "negative"/"positive") or None if the kind
            is still undefined
      """
      lens = LensItem(xlocation, baseline.ylocation, span, kind)
      self.scene.addItem(lens)
      return lens


  def add_ray(self, polyline):
    """Add a ray to the canvas."""
    ray = RayItem(polyline)
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
    print key
    QtGui.QGraphicsScene.keyPressEvent(self, event)
    print event.key()
    # Display last stroke coordinates as a numpy array.
    if event.key() == 80: # p 
      print (self.strokeitem[-1].tonumpy())
    
    if event.key() == 69: # e
      print "Existing objects: "+self.engine.content()


  def mousePressEvent(self, event):
    print "Mouse press."
    self.currentitem = StrokeItem(event.scenePos())
    self.strokeitem.append(self.currentitem)
    self.addItem(self.currentitem)


  def mouseMoveEvent(self, event):
     if self.currentitem: 
        self.currentitem.lineTo(event.scenePos())
 

  def mouseReleaseEvent(self, event):
    print "Mouse release."
    if self.currentitem:
      self.removeItem(self.currentitem)
      self.engine.push_stroke(self.currentitem.tonumpy())
      self.currentitem = None


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
                            color=QtGui.QColor('red'),
                            radius = 5)
                  );
 #   text = scene.addText("foo bar")
 #   text.setPos(0,0)


