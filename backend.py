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
import logging

class Baseline(object):
    def __init__(self, frontend, ylocation, span=300):
        self.ylocation = ylocation
        self.polyline = np.asarray([[-span, ylocation],[span,ylocation]])
        self._frontend_object = frontend.add_baseline(ylocation, span)


class Lens(object):
    def __init__(self, frontend, xlocation, baseline, focal=50.,
                 span=70, kind="thin"):
        # kind can be "undefined" or "thin"
        self.xlocation = xlocation
        self.focal = focal
        self.baseline = baseline
        self.span = span
        self.polyline = np.asarray([[xlocation, baseline.ylocation-span],
                                    [xlocation, baseline.ylocation+span]])
        self._frontend_object = frontend.add_lens(xlocation, baseline,
                                                  focal=focal,
                                                  span=span, kind=kind)

    def update(self):
        self.polyline = np.asarray([[self.xlocation, self.baseline.ylocation-self.span],
                                    [self.xlocation, self.baseline.ylocation+self.span]])
        self._frontend_object.update(self.xlocation, self.baseline.ylocation,
                                     self.focal)
        

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

    
    def remove_object(self, objects_list):
        """Delete objects."""
        if not isinstance(objects_list, (list, tuple)):
            objects_list = (objects_list,)

        logging.debug("removing: "+str(objects_list))
        deleted_lenses = 0;
        deleted_baseline = False;

        for obj in objects_list:
            if not isinstance(obj, Baseline):
                self.frontend.remove_object(obj._frontend_object)

            if isinstance(obj, Ray):
                del self._rays[self._rays.index(obj)]
            elif isinstance(obj, Lens):
                del self._lenses[self._lenses.index(obj)]
                deleted_lenses = deleted_lenses + 1
            elif isinstance(obj, Baseline) and len(objects_list) == 1:
                # Baseline can be deleted only if nothing else must be deleted.
                self._baseline = None
                deleted_baseline = True
                self.frontend.remove_object(obj._frontend_object)
##                 del self._baseline[self._baseline.index(obj)]

        # Erase everything if the baseline has been deleted
        if (deleted_baseline):
            for obj in self._rays + self._lenses:
                self.frontend.remove_object(obj._frontend_object)
            self._rays = []
            self._lenses = []            
            return
        
        # Update rays if a lens has been deleted
        if (deleted_lenses > 0):
            for ray in self._rays: ray.update()

                
    def push_stroke(self, stroke):
        """Provides the engine with a new stroke. Interpretation is performed."""
        
        logging.debug("--- Raw line ---")
        logging.debug("number of points: "+str(len(stroke)))
        # print "coordinates: ", stroke

        descriptors = StrokeDescriptors(stroke)
        logging.info("--- Descriptors ---")
        logging.debug(str(descriptors))

        # Call detectors here
        logging.info("--- Detectors ---")

        point = descriptors.point_detector()
        line  = descriptors.straight_line_detector()
        baseline = self.baseline_detector(descriptors)
        lens = self.lens_detector(descriptors)
        ray = self.ray_detector(descriptors)

        threshold = 1.
        d = simplify_dp(stroke[:,0], stroke[:,1])
        s = stroke[d>threshold]
        logging.debug("simplification threshold: "+str(threshold))
        logging.debug("number of points after simplification: "+ str(len(s)))

        simplified_descriptors = StrokeDescriptors(s)
        scratch = self.scratch_detector(simplified_descriptors)

        logging.info("Point detector   : "+str(point))
        logging.info("Line detector    : "+str(line))
        logging.info("Baseline detector: "+str(baseline))
        logging.info("Lens detector    : "+str(lens))
        logging.info("Ray detector     : "+str(ray))
        logging.info("Scratch detector : "+str(scratch))

        logging.info("--- Corners detection ---")
        resamp = descriptors.resample()
        corners1 = descriptors.corners1()

        # Make recognition decision and call frontend here.
        if scratch[0]:
            logging.info("Processing scratch")
            todelete = self.scratch_get_todelete(scratch, descriptors)
            self.remove_object(todelete)
            return
                
        if point[0]:
            logging.info("Adding point")
            self.frontend.add_point(point[1], point[2])
            return 

        if baseline:
            if self._baseline is None:
                logging.info("Adding baseline")
                ylocation = (stroke[0,1] + stroke[-1, 1])/2.
                self._baseline = Baseline(self.frontend, ylocation)
                return
            else:
                logging.error("Already a baseline")

        if lens:
            default_focal_length = 50
            logging.info("Adding a lens")
            xlocation = (stroke[0,0] + stroke[-1, 0])/2.
            if len(self._lenses) % 2 == 0:
                sign = 1
            else:
                sign = -1
            self._lenses.append(Lens(self.frontend, xlocation,
                                     self._baseline._frontend_object,
                                     focal=default_focal_length*sign))
            # Update ray objects.
            for ray in self._rays: ray.update()
            return

        if ray[0]:
            logging.info("Adding a ray")
            self._rays.append(Ray(self.frontend, self, *ray[1:]))
            return
            
        if line[0]:
            logging.info("Adding generic line")
            self.frontend.add_line(stroke[(0,-1),:], kind="generic")
            return

        # Display simplified line
##         logging.info("fallback: adding simplified line")
##         self.frontend.add_line(s, kind="generic")

## Display loops (debug)
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

        logging.debug("-- scratch detector --")
        # If simplified line is perfectly straight, do nothing.
        print descriptors._a.shape
        if descriptors._a.shape[0] <= 2: return (False,)
        
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
        logging.debug("arc_cumangles: "+str(arc_cumangles))
        logging.debug("threshold: %.2f" % threshold)
        arc_number = len(inflection_indices)-3
        if arc_cumangles[0] > threshold:
            arc_number += 1
        if arc_cumangles[-1] > threshold:
            arc_number += 1
        
##        arc_number = len(inflection_lengths)+1

        logging.debug("inflection_indices: " + str(inflection_indices))
        logging.debug("inflection_angle: %.2f" % np.rad2deg(inflection_angle))

        logging.debug("* Detecting criteria:")
        logging.debug("angle_sum_criteria: %.2f >= 3.8" % angle_sum_criteria)
        logging.debug("arc_number: %d >= 4" % arc_number)
#        logging.debug("svalue_ratio: %.2f <= 0.3 " % svalue_ratio)
        logging.debug("-- end scratch --")

        if size<17 \
           or angle_sum_criteria < 3.8 \
           or arc_number < 4 :
#           or svalue_ratio > 0.3 
            return (False, inflection_points)
        
        logging.debug("** scratch detected **")
        # TODO: return a dictionary instead of inflection_points.
        return (True, inflection_points)

    
    def scratch_get_todelete(self, scratch, descriptors):
        """Given a scratch stroke, return the object(s) to be deleted.
        scratch: return value of scratch_detector()
        descriptors: StrokeDescriptors for the scratch stroke
        
        Criteria for deletion of a ray or a lens:
        - the number of intersections between scratch and polyline must
        greater than 2 and the number of scratch inflection points minus 1.

        """
        todelete = []
        
        # If no baseline exists, no other object can exist
        if self._baseline is None: return(todelete)

        for obj in self._rays + self._lenses + [self._baseline]:
            # Compute curvilinear coordinate of intersection points
            # between scratch and object polyline.
            object_descriptors = StrokeDescriptors(obj.polyline)
            intersections = LineIntersection(descriptors, object_descriptors)
            coordinates = np.asarray([l[3] for l in intersections.parts1[:-1]])
#            points = descriptors.resample(lengths=coordinates)

            if len(coordinates) >= len(scratch[1])-1 \
                   and len(coordinates) > 2:
                todelete.append(obj)

        return (todelete)

        
    def baseline_detector(self, descriptors, span=270):
        """Detect if a stroke can be a base line.
        Criteria :
        - horizontal line
        - horizontal coordinate of leftmost point is less than -span
        - horizontal coordinate of rightmost point is greater than span.
        """
        line  = descriptors.straight_line_detector()        
        logging.debug(str(descriptors._a[0,0]))
        logging.debug(str(descriptors._a[-1,0]))

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


    def set_lens_focal(self, lens, focal):
        """Change the focal length of a lens.
        lens: frontend object
        focal: new focal length"""
        logging.debug('backend: set_lens_focal %d' % focal)
        backend=None
        for l in self._lenses:
            if l._frontend_object == lens:
                backend = l
                break
        if backend is None: raise ValueError("No backend object found.")
        backend.focal = focal
        backend.update()
        for ray in self._rays: ray.update()
        
        
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
        backend.update()
        for ray in self._rays: ray.update()


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
