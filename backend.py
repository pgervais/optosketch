# This file is part of Optosketch. It is released under the GPL v2 licence.
"""Recognition engine main file. The API provided by this file must be independant
of frontend. Frontend communication must be implemented in a separate file.
"""

from descriptors import StrokeDescriptors
from simplify import simplify_dp
import numpy as np
    
class Baseline(object):
    def __init__(self, frontend, ylocation, span=300):
        self.ylocation = ylocation
        self._frontend_object = frontend.add_baseline(ylocation, span)

class Lens(object):
    def __init__(self, frontend, xlocation, baseline, focal=50.,
                 span=70, kind="thin"):
        # kind can be "undefined" or "thin"
        self.xlocation = xlocation
        self.focal = focal
        self._frontend_object = frontend.add_lens(xlocation, baseline,
                                                  span, kind)
        

class Ray(object):
    def __init__(self, frontend, polyline):
        self.polyline = polyline
        self._frontend_object = frontend.add_ray(polyline)
        

class RecognitionEngine(object):
    """Main communication object between frontend and backend."""

    def __init__(self):
        """Initialize various caches."""

        self._baseline = None
        self._lenses = []
        self._rays = []


    def set_frontend(self, frontend):
        """Must be called by frontend object after __init__()"""
        self.frontend = frontend

    def content(self):
        """Print known objects as a human-readable string"""
        s=""
        if self._baseline:
            s+="Baseline: ylocation = "+str(self._baseline.ylocation)+"\n"

        if self._lenses:
            for l in self._lenses:
                s+="Lens: xlocation = "+str(l.xlocation)+"\n"

        return s
    
                
    def push_stroke(self, stroke):
        """Provides the engine with a new stroke. Interpretation is performed."""
        
        print "--- Raw line ---"
        print "number of points: ",len(stroke)
        # print "coordinates: ", stroke

        print ("--- Descriptors ---")
        descriptors = StrokeDescriptors(stroke)
        print (descriptors)
        # print "Angles:\n", descriptors._angles

        # Call detectors here
        print("--- Detectors ---")
        point = descriptors.point_detector()
        print "Point: "+str(point) 
        line  = descriptors.straight_line_detector()        
        print "Line: "+str(line)

        baseline = self.baseline_detector(descriptors)
        print "Baseline: "+str(baseline)

        lens = self.lens_detector(descriptors)
        print "Lens: "+str(lens)

        ray = self.ray_detector(descriptors)
        print "Ray: "+str(ray)

        print("--- Corners detection ---")
        resamp = descriptors.resample()
        corners1 = descriptors.corners1()
        print "corners:",corners1
        print 'resampled point number: %d' % len(resamp)

        # Make recognition decision and call frontend here.
##         self.frontend.add_line(corners1) # Display line with detected corners.
        if point[0]:
            print ("Adding point")
            self.frontend.add_point(point[1], point[2])
            return 

        if baseline:
            if self._baseline is None:
                print ("Adding baseline")
                ylocation = (stroke[0,1] + stroke[-1, 1])/2.
                self._baseline = Baseline(self.frontend, ylocation)
                return
            else:
                print ("Already a baseline")

        if lens:
            print ("Adding a lens")
            xlocation = (stroke[0,0] + stroke[-1, 0])/2.
            self._lenses.append(Lens(self.frontend, xlocation,
                                     self._baseline._frontend_object))
            return

        if ray[0]:
            print("Adding a ray")
            polyline = self.ray_polyline(descriptors, *ray[1:])
            self._rays.append(Ray(self.frontend, polyline))
            return
            
        if line[0]:
            print("Adding generic line")
            self.frontend.add_line(stroke[(0,-1),:], kind="generic")
            return

        print "--- Simplification ---"
        threshold = 1
        d = simplify_dp(stroke[:,0], stroke[:,1])
        s = stroke[d>1.]
        print "threshold: ", threshold
        print "number of points: ", len(s) 

        # Display simplified line
        self.frontend.add_line(s, kind="simplified")


## Detectors
        
    def scale_to(self, vector, length=1.):
        """Scale a vector to a given length."""
        factor = np.sqrt(length**2/(vector[0]**2 + vector[1]**2))
        return (vector * factor)

        
    def ray_detector(self, descriptors):
        """Detect if a stroke can be a ray.
        Criteria :
        - straight line
        - end or start point near a lens
        (if there is no lens, there can be no rays)
        """
        if len(self._lenses) == 0:
            return (False,)

        result = False
        line = descriptors.straight_line_detector()
        if line[0]:
            closest_lens = None
            min_distance = 2000000
            ending = None # "start" or "end"
            for lens in self._lenses:
                if abs(descriptors._a[0,0] - lens.xlocation) < min_distance:
                    closest_lens = lens
                    min_distance = abs(descriptors._a[0,0] - lens.xlocation)
                    ending = "start"

                if abs(descriptors._a[-1,0] - lens.xlocation) < min_distance:
                    closest_lens = lens
                    min_distance = abs(descriptors._a[-1,0] - lens.xlocation)
                    ending = "end"

            if min_distance < 50:
                # Is ray mainly drawn on the left or on the right of the lens ?
                if ending == "start":
                    closest_point = descriptors._a[-1,:] 
                else:
                    closest_point = descriptors._a[0,:]

                if closest_lens.xlocation-closest_point[0] < 0:
                    side = "right"
                else:
                    side = "left"
                    
                # unit vector
                unit = self.scale_to(np.asarray(
                    (descriptors._a[-1,0]-descriptors._a[0,0],
                     descriptors._a[-1,1]-descriptors._a[0,1])))

                # Compute ray-lens intersection
                if ending=="start":
                    ylocation = closest_point[1] + (
                        closest_lens.xlocation-closest_point[0]
                        )*unit[1]/unit[0]
                else:
                    ylocation = closest_point[1] + (
                        closest_lens.xlocation-closest_point[0]
                        )*unit[1]/unit[0]
                
                result = True
                if side == 'left':
                    point = np.asarray((closest_lens.xlocation-1,ylocation))
                else:
                    point = np.asarray((closest_lens.xlocation+1,ylocation))

        if result:
            # unit is a unitary vector telling drawing direction.
            return (result, point, unit)
        else:
            return(False,)
        
    
    def ray_polyline(self, descriptors, basepoint, unit):
        print ("unit: ", unit)
        print ("basepoint: ", basepoint)

        # Get sorted lens locations
        lenses_x = np.array([(l.xlocation, l.focal,
                              l._frontend_object.ylocation)
                             for l in self._lenses])
        I = lenses_x[:,0].argsort()
        lenses_x = lenses_x[I, :]
        
        index = lenses_x[:,0].searchsorted(basepoint[0])

        # Propagate on the right
        rpoints=[]
        point = basepoint
        if unit[0] > 0: vector = unit
        else: vector = -unit
            
        for l in lenses_x[index:,:]:
            point, vector = self.lens_transmission(point, vector,
                                                   l[0], l[2], l[1],
                                                   direction="right")
            rpoints.append((point,vector))
        rpoints.append((point + 200*vector, vector))
        
        # Propagate on the left
        lpoints=[]
        point = basepoint
        if unit[0] > 0: vector = unit
        else: vector = -unit

        if index == 0:
            llenses = []
        else:
            llenses = lenses_x[index-1::-1,:]
            
        for l in llenses:
            point, vector = self.lens_transmission(point, vector,
                                                   l[0], l[2], l[1],
                                                   direction="left")
            lpoints.append((point,vector))
        lpoints.append((point - 200*vector, vector))
        lpoints.reverse()
        
        polyline = [p[0] for p in lpoints+rpoints]        
        return np.asarray(polyline)


    def lens_transmission(self, point, vector, xlocation, ylocation, focal, 
                          direction="right"):
        """Compute ray transmission through a lens.
        direction can be "left" or "right" : light propagation direction.
        xlocation, ylocation: coordinates of center of lens.
        """

        # Ray-lens intersection point
        # h is the oriented distance between the base line and the point
        # where the ray hits the lens.
        h = point[1] + (xlocation-point[0])*vector[1]/vector[0]
        point = np.asarray((xlocation,h))

        # Ray vector after the lens.
        if direction == "right":
            vector = self.scale_to(
                np.asarray((1., - (h - ylocation)/ focal
                            + vector[1]/vector[0])))
        else:
            vector = self.scale_to(
                np.asarray((1., + (h - ylocation) / focal
                            + vector[1]/vector[0])))

        return (point, vector)

        
    def baseline_detector(self, descriptors, span=270):
        """Detect if a stroke can be a base line.
        Criteria :
        - horizontal line
        - horizontal coordinate of leftmost point is less than -span
        - horizontal coordinate of rightmost point is greater than span.
        """
        line  = descriptors.straight_line_detector()        
        print (descriptors._a[0,0])
        print (descriptors._a[-1,0])

        if line[0] \
           and line[1] == 'horizontal' \
           and descriptors._a[0,0] < -span \
           and descriptors._a[-1,0] > span:
            return True
        else:
            return False


    def lens_detector(self, descriptors):
        """Detect if a stroke can be a lens
        Criteria :
        - a base line must exist
        - vertical line
        - start and end points on each side of the baseline
        - start and end points farther from the baseline than a threshold
        """
        if self._baseline is None: return False
        
        line  = descriptors.straight_line_detector()        
        threshold = 40
        ylocation = self._baseline.ylocation
        ds = descriptors._a[0,1] - ylocation
        de = descriptors._a[-1,1] - ylocation

        if line[0] \
           and line[1] == 'vertical' \
           and ds*de < 0. \
           and abs(ds) > threshold \
           and abs(de) > threshold :
            return True

        else:
            return False

        
