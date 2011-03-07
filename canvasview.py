# This file is part of Optosketch. It is released under the GPL v2 licence.

from PyQt4 import QtGui, QtCore
from stroke import StrokeItem
from simplify import simplify_dp
from point import PointItem
from descriptors import StrokeDescriptors

def display_properties(scene, item):
  """Test function. Display some line properties and do some actions for a 
  finished line.
  item: StrokeItem().
  """

  c=item.tonumpy()
  print "--- Base line ---"
  print "number of points: ",len(c)
 # print "coordinates: ", c

  print "--- Descriptors ---"
  descriptors = StrokeDescriptors(c)
  print (descriptors)
  print "Angles:\n", descriptors._angles

  resamp = descriptors.resample()
  corners1 = descriptors.corners1()
  print "corners:",corners1
  print 'resampled point number: %d' % len(resamp)
#  print "Inflection points\n", descriptors.inflection_points()

  if True:
    rl = StrokeItem(color=QtGui.QColor('red'))
    rl.fromnumpy(corners1)
    #scene.removeItem(item)
    scene.addItem(rl)
    return

  point = descriptors.point_detector()
  line = descriptors.straight_line_detector()
  print point
  print line

  if point[0]:
    sl = PointItem(QtCore.QPointF(point[1], point[2]), 
                   color=QtGui.QColor('red'), radius = 5)
    scene.addItem(sl)
    scene.removeItem(item) # FIXME: remove it from CanvasScene.StrokeItem as well 
    return 

  if line[0]:
    s = c[(0,-1),:]
    sl = StrokeItem(color=QtGui.QColor('red'))
    sl.fromnumpy(s)
    scene.removeItem(item)
    scene.addItem(sl)
    return

  print "--- Simplification ---"
  threshold = 1
  d = simplify_dp(c[:,0], c[:,1])
  s = c[d>1.]
  print "threshold: ", threshold
  print "number of points: ", len(s) 
  
  # Display simplified line
  sl = StrokeItem(color=QtGui.QColor('green'))
  sl.fromnumpy(s)
  scene.removeItem(item)
  scene.addItem(sl)


class CanvasScene(QtGui.QGraphicsScene):
  """Qt scene for stroke board. Handles lines drawing. """
  def __init__(self, *args):
    super(CanvasScene, self).__init__(*args)
    self.pressed = False
    self.currentitem = None # stroke being drawn
    self.strokeitem = [] # list of all strokes


  def keyPressEvent(self, event):
    key = event.key()
    print key
    QtGui.QGraphicsScene.keyPressEvent(self, event)
    print event.key()
    # Display last stroke coordinates as a numpy array.
    if event.key() == 80: # p ?
      print self.strokeitem[-1].tonumpy()


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
      display_properties(self, self.currentitem)
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


