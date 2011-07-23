# This file is part of Optosketch. It is released under the GPL v2 licence.
"""Recognition engine main file. The API provided by this file must be independant
of frontend. Frontend communication must be implemented in a separate file.
"""

from descriptors import StrokeDescriptors
from intersection import SelfIntersection, LineIntersection
from simplify import simplify_dp
import math
import numpy as np
from numpy.linalg import svd

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
        self.baseline = baseline
        self._frontend_object = frontend.add_lens(xlocation, baseline,
                                                  focal=focal,
                                                  span=span, kind=kind)
        

class Ray(object):
    def __init__(self, frontend, backend, basepoint, unit):
        """basepoint: point through which the ray passes.
        unit: unitary vector along the ray, at basepoint."""
        self.basepoint = basepoint
        self.unit = unit
        self.backend = backend
        
        self.polyline = self.backend.ray_polyline(self.basepoint, self.unit)
        self._frontend_object = frontend.add_ray(self.polyline, basepoint, unit)


    def update(self):
        """Update ray."""
        self.polyline = self.backend.ray_polyline(self.basepoint, self.unit)        
        self._frontend_object.update(self.polyline, self.basepoint, self.unit)


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


        print "--- Simplification ---"
        threshold = 1.
        d = simplify_dp(stroke[:,0], stroke[:,1])
        s = stroke[d>threshold]
        print "threshold: ", threshold
        print "number of points: ", len(s) 

        simplified_descriptors = StrokeDescriptors(s)
        scratch = self.scratch_detector(simplified_descriptors)
        print "Scratch: "+str(scratch)

        print("--- Corners detection ---")
        resamp = descriptors.resample()
        corners1 = descriptors.corners1()
#        print "corners:",corners1
#        print 'resampled point number: %d' % len(resamp)

        # Make recognition decision and call frontend here.
##         self.frontend.add_line(corners1) # Display line with detected corners.
        if scratch[0]:
            print ("Processing scratch")
            # Display intersections with the first ray drawn.
            for n, ray in enumerate(self._rays):
                ray_descriptors = StrokeDescriptors(ray.polyline)
                intersections = LineIntersection(descriptors, ray_descriptors)

                coordinates = np.asarray([l[3] for l in intersections.parts1[:-1]])
                points = descriptors.resample(lengths=coordinates)
#                print (points)
                # Show intersection points (debug)
##                 for p in points:
##                     self.frontend.add_point(*p, kind="intersection")

                if len(coordinates) >= len(scratch[1])-1 \
                       and len(coordinates) > 2:
                    self.frontend.remove_object(ray._frontend_object)
                    del self._rays[n]
                    print "erase ray"

            # Show inflection points and line (debug)
##             for p in scratch[1]:
##                 self.frontend.add_point(p[0], p[1])
##             self.frontend.add_line(stroke, kind="generic")
            return
                
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
            if len(self._lenses) % 2 == 0:
                sign = 1
            else:
                sign = -1
            self._lenses.append(Lens(self.frontend, xlocation,
                                     self._baseline._frontend_object,
                                     focal=50*sign))
            # Update ray objects.
            for ray in self._rays: ray.update()
            return

        if ray[0]:
            print("Adding a ray")
            self._rays.append(Ray(self.frontend, self, *ray[1:]))
            return
            
        if line[0]:
            print("Adding generic line")
            self.frontend.add_line(stroke[(0,-1),:], kind="generic")
            return

        # Display simplified line
        print ("fallback: display simplified line")
        self.frontend.add_line(s, kind="generic")

## Display loops
##         intersections = SelfIntersection(descriptors)        
##         for loop in intersections.get_loops():
##             self.frontend.add_line(descriptors.extract(*loop), kind="loop")


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
        
    
    def ray_polyline(self, basepoint, unit):
##         print ("unit: ", unit)
##         print ("basepoint: ", basepoint)

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


    def inflection_points(self, descriptors, return_indices=False):
        """Compute the curvilinear coordinates of the inflection points
        of the curve. This function is very sensitive to noise. Use only
        descriptors of a denoised line as input (e.g. a simplified line)"""
        zerocrossings = np.where(
            descriptors._angles[1:] * descriptors._angles[:-1] < 0)[0]

        weighta = np.abs(descriptors._angles[zerocrossings])
        weightb = np.abs(descriptors._angles[zerocrossings+1])
        
        # Stroke lengths at inflection points
        inflection_lengths = descriptors._cumlength[zerocrossings] + \
             weighta/(weighta+weightb)*descriptors._lengths[zerocrossings+1]

        if return_indices:
            return (inflection_lengths, np.hstack(((0,), zerocrossings+1,
                                                   (len(descriptors._angles)-1,))))
        else:
            return(inflection_lengths)
    

    def scratch_detector(self, descriptors):
        """Detect if a stroke can be a scratch.
        Descriptors must be computed on a simplified line. Otherwise, angle
        computations are too noisy.
        
        Criteria:
        - maximum span greater than a threshold.
        - sum of angles minus sum of absolute values of angles greater
          than a threshold (4.5 is a good guess value, independent of scale).
        - At least 2 inflection points.
        - Inflection points are roughly aligned
        """

        print ("-- scratch --")
        size = max(descriptors._span)
        
        # Compute location of inflection points
        inflection_lengths, inflection_indices = \
                            self.inflection_points(descriptors, return_indices=True)
        inflection_points = descriptors.resample(lengths=inflection_lengths)
        if len(inflection_points) < 2: return (False, inflection_points)

        # Compute pca on inflection points
        m = np.dot(np.ones(inflection_points.shape),
                   np.diagflat(inflection_points.mean(0)))
        U,S,V = svd(inflection_points - m, full_matrices=False);

        # Ensure main direction points towards positive value
        if V[0,0] < 0. : V = -V

        # Angle of principal axis relative to horizontal
        inflection_angle = math.atan2(V[0,1], V[0,0])
        # Ratio of singular values
        svalue_ratio = S[1]/S[0]

        abs_angle_sum = np.abs(descriptors._angles).sum()
        angle_sum = abs(descriptors._angles.sum())

        angle_sum_criteria = abs(angle_sum - abs_angle_sum)
        
        # Check if end arcs can be counted in arc number.
        # End lines are counted as arcs if their cumulated angle are greater
        # than the median of the cumulated angles of inner arcs, divided by
        # a constant factor.
        arc_cumangles = abs(descriptors._cumangles[inflection_indices[1:]]
                            - descriptors._cumangles[inflection_indices[:-1]])
        threshold = np.median(arc_cumangles[1:-1])/1.5
        print ("arc_cumangles: ", arc_cumangles)
        print("threshold: %.2f" % threshold)
        arc_number = len(inflection_indices)-3
        if arc_cumangles[0] > threshold:
            arc_number += 1
        if arc_cumangles[-1] > threshold:
            arc_number += 1
        
##        arc_number = len(inflection_lengths)+1

        print ("inflection_indices:", inflection_indices)
        print("inflection_angle: %.2f" % np.rad2deg(inflection_angle))

        print ("* Detecting criteria:")
        print ("angle_sum_criteria: %.2f >= 3.8" % angle_sum_criteria)
        print ("arc_number: %d >= 4" % arc_number)
        print ("svalue_ratio: %.2f <= 0.3 " % svalue_ratio)
        print ("-- end scratch --")

        if size<17 \
           or angle_sum_criteria < 3.8 \
           or arc_number < 4 \
           or svalue_ratio > 0.3:
            return (False, inflection_points)
        
        print ("** scratch detected **")
        return (True, inflection_points)
    
        
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

        
    def set_lens_pos(self, lens, x, y):
        """Move a lens to a new location.
        "lens" is the frontend object.
        x,y : new lens location (lens center)."""

        # Find backend object
        # FIXME: very unefficient. use a dict instead.
        backend=None
        for l in self._lenses:
            if l._frontend_object == lens:
                backend = l
                break
        if backend is None: raise ValueError("No backend object found.")

        backend.xlocation = x
        y = backend.baseline.ylocation
        for ray in self._rays: ray.update()
        
        return (backend.xlocation, y)

    def _find_ray_backend(self, ray_frontend):
        """Find a ray backend from its given frontend"""
        backend=None
        for l in self._rays:
            if l._frontend_object == ray_frontend:
                backend = l
                break
        if backend is None: raise ValueError("No backend object found.")
        return backend

    def set_ray_point(self, ray, x, y):
        """Change the location of a ray base point.
        "ray": frontend ray object.
        x, y: new location"""
        backend = self._find_ray_backend(ray)
        backend.basepoint = np.asarray((x,y))
        backend.update()

    def set_ray_direction(self, ray, dir_vec):
        """Change the ray direction:
        ray: frontend ray object
        dir_vec: direction vector, numpy.array of shape (2,)
        """
        backend = self._find_ray_backend(ray)
        backend.unit = self.scale_to(dir_vec)
        backend.update()
