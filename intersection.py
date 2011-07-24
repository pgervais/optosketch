# This file is part of Optosketch. It is released under the GPL v2 licence.

"""Classes for line intersection computations.
This module handle self-intersection (and intersections between two
different lines in the future).
"""
import numpy as np
import logging

class Intersection(object):
    """Base class for line intersection computation. This class contains all
    the methods that can be used for the one-line or the multi-line cases."""

    def _bbox_intersection(self, bb1, bb2):
        """Compute bounding boxes intersection. Returns None if bounding boxes
        do not intersect."""

        # Along x: min of the maximum and max. of the minimum
        xmax = min(bb1[2], bb2[2]) # xmax
        xmin = max(bb1[0], bb2[0]) # xmin
        # Along y: same thing
        ymax = min(bb1[3], bb2[3]) # ymax
        ymin = max(bb1[1], bb2[1]) # ymin

        if xmax < xmin: return None
        if ymax < ymin: return None

        bb = np.asarray((xmin, ymin, xmax, ymax))
        return bb


    def _two_segments_crossing(self, n1, p1, n2, p2, different=False):
        """First part : n1, p1, Second part: n2, p2 (indices)
        This function must be called with n1 < p1 < n2 < p2.
        "different" (boolean): if True, consider two different lines, not the
        same one.
        """

        assert (n1 < p1)
        if different == False: assert (p1 < n2)
        assert (n2 < p2)
        x1 = self._a[n1,:]
        x2 = self._a[p1,:]
        if different:
            x3 = self._b[n2,:]
            x4 = self._b[p2,:]
        else:
            x3 = self._a[n2,:]
            x4 = self._a[p2,:]

        # Handle a lot of pathological cases
        logging.log(5, "[_two_segments_crossing] Points following")
        logging.log(5, "[_two_segments_crossing] "  +str(x1) +' '+str(x2))
        logging.log(5, "[_two_segments_crossing] "  +str(x3) +' '+str(x4))

        logging.log(5, "[_two_segments_crossing] Vectors following")
        logging.log(5, '[_two_segments_crossing] 1-3: ' +str(x1 - x3))
        logging.log(5, '[_two_segments_crossing] 3-2: ' +str(x3 - x2))
        logging.log(5, '[_two_segments_crossing] 2-4: ' +str(x2 - x4))
        logging.log(5, '[_two_segments_crossing] 4-1: ' +str(x4 - x1))

        # When one segment is of length zero, consider there is no intersection.
        # Side segments will report a crossing point.
        # Should never happen after line simplification
        if abs(x1-x2).sum() == 0:
            logging.log(5, "[_two_segments_crossing] Zero-length segment")
            return None 
        if abs(x3-x4).sum() == 0:
            logging.log(5, "[_two_segments_crossing] Zero-length segment")
            return None

        #1-3/3-2/2-4/4-1
        cp1 = np.cross(x1-x3, x3-x2)
        cp2 = np.cross(x3-x2, x2-x4)
        cp3 = np.cross(x2-x4, x4-x1)
        cp4 = np.cross(x4-x1, x1-x3)
        logging.log(5, "[_two_segments_crossing] CP: "+str(cp1)+' '+str(cp2)+' '+str(cp3)+' '+str(cp4))

        # Check if segments are aligned
        cp = np.cross(x2-x1, x4-x3)
        if cp == 0:
            aligned = True
            logging.log(5, "[_two_segments_crossing] segments aligned (warning)")
        else: aligned = False

        # If two points are at the same location, report only one case.
        if abs(x1-x4).sum() == 0:
            logging.log(5, "[_two_segments_crossing] 1 == 4 : discard")
            return None
        if abs(x1-x3).sum() == 0:
            logging.log(5, "[_two_segments_crossing] 1 == 3 : discard")
            return None
        if abs(x2-x4).sum() == 0:
            logging.log(5, "[_two_segments_crossing] 2 == 4 : discard")
            return None
        if abs(x2-x3).sum() == 0:
            logging.log(5, "[_two_segments_crossing] 1 == 3 : ok")
        else:
            # One point may lie on the **direction** of the other segment
            if cp1 == 0 and not aligned: # point 3 on segment 1-2
                # Intersection will be reported by the other segment
                logging.log(5, "[_two_segments_crossing] 3 on 1-2 : discard")
                return None
            if cp4 == 0 and not aligned: # point 1 on segment 3-4
                # Intersection will be reported by the other segment
                logging.log(5, "[_two_segments_crossing] 1 on 3-4 : discard")
                return None

            if cp2 == 0: logging.log(5, "[_two_segments_crossing] 2 on 3-4")
            if cp3 == 0: logging.log(5, "[_two_segments_crossing] 4 on 1-2")

        if cp1*cp2 < 0: return None
        if cp2*cp3 < 0: return None
        if cp3*cp4 < 0: return None
        logging.debug("*** Crossing found ***")

        # Parallel segments: return any point
        # FIXME: the returned lengths to crossing do not correspond to the
        # same point
        if cp == 0: return x1, 0, 0

        norm1 = np.sqrt(((x2-x1)**2).sum())
        norm2 = np.sqrt(((x4-x3)**2).sum())
        u1 = (x2-x1)/norm1 # unitary vectors
        u2 = (x4-x3)/norm2
        alpha = - np.cross(u2, x3-x1)/(cp/(norm1*norm2))
        beta = - np.cross(u1, x3-x1)/(cp/(norm1*norm2))    
        # alpha must be between 0 and norm1
        # beta must be between 0 and norm2
        # And... alpha*u1 + x1 == beta*u2 + x3
        logging.log(5, "[_two_segments_crossing] alpha, norm1: " +str(alpha) + ' '+str(norm1))
        logging.log(5, "[_two_segments_crossing] beta, norm2: " +str(beta) +' '+ str(norm2))
        logging.log(5, "[_two_segments_crossing] crossing: " +str(alpha*u1 + x1) + ' == ' + str(beta * u2 + x3))
        # Return coordinates of crossing, and lengths from x1 and x3 to the crossing.
        return (alpha*u1 + x1, alpha, beta)


class SelfIntersection(Intersection):
    """Object for computation and handling of line self-intersections."""
    def __init__(self, descriptors):
        """Search for line self-intersections.
        The list of intersections founds is in the 'crossings' attribute.
        descriptors: StrokeDescriptors object"""
        self._a = descriptors._a
        self._gea = descriptors
        
        # Get crossings
        self.crossings = []
        self.__intersections(0, self._a.shape[0]-1)
        
        # Set up a list containing for each line part number, the associated
        # crossing numbers and the lengths. 
        self.parts = [[] for k in range(2*len(self.crossings)+1)]

        # Intersection locations in curve length (curvilinear coordinate)
        interlengths = []
        for loc, l1, l2 in self.crossings:
            interlengths.append(l1)            
            interlengths.append(l2)

        interlengths.sort()
        assert(len(interlengths) == len(self.crossings)*2)

        self.parts[0].append(None)
        self.parts[0].append(0.)
        for k in range(len(self.crossings)):
            loc, l1, l2 = self.crossings[k]
            assert(l1 <= l2)

            partnb = interlengths.index(l1)
            self.parts[partnb].append(k)
            self.parts[partnb].append(l1)
            self.parts[partnb+1].append(k)
            self.parts[partnb+1].append(l1)

            partnb = interlengths.index(l2)
            self.parts[partnb].append(k)
            self.parts[partnb].append(l2)
            self.parts[partnb+1].append(k)
            self.parts[partnb+1].append(l2)

        self.parts[-1].append(None)
        self.parts[-1].append(self._gea._length)

        # Reorder line beginning and end
        # First and last points are properly ordered
        for k in range(1,len(self.parts)-1):
            c = self.parts[k]
            if c[1] > c[3]:
                c[1], c[3] = c[3], c[1]
                c[0], c[2] = c[2], c[0]
                

    def __len__(self):
        """Return number of line subparts."""
        return (2*len(self.crossings) + 1)

    def __getitem__(self, key):
        """Return n-th part of line. The number of parts is equal to
        len(self.crossings)*2 + 1."""

        if len(self.crossings) == 0 and key == 0:
            return self._a

        n1, l1, n2, l2 = self.parts[key]
        return self._gea.extract(l1, l2)


    def get_loops(self):
        """Return pairs of curvilinear coordinates that correspond to
        loops. No two intervals overlap."""

        # There may be a better algorithm, this one scale as N^2 in the
        # worst case (N being the number of subparts). N is always 
        # small, this should not be a problem.

        index = 0
        loops = []
        for p, right in enumerate(self.parts):
            if right[0] == right[2]: # simple loop
                loops.append((right[1], right[3]))
                index = p+1
                continue
            
            for n, left in enumerate(self.parts[index:p]):
                if left[0] == right[2] and not right[2] is None: # loop
                    loops.append((left[1], right[3]))
                    index = p+1

        return(loops)


    def __intersections(self, n, p):
        # No possible intersection
        if p - n <= 1:
            return

        # Cut line roughly in the middle
        q = int((n+p)/2)

        # Check sub-lines for self-intersection
        self.__intersections(n, q)
        self.__intersections(q, p)

        # Check for cross-intersection, if any
        if self._bbox_intersecting(n, q, q, p): 
            self.__cross_intersection(n, q, q, p, False, False)


    def __cross_intersection(self, n1, p1, n2, p2, auto1, auto2):
        """Search for intersection between two lines.
        n1, p1: start and stop indices for a1
        n2, p2: start and stop indices for a2
        auto1, auto2: boolean telling if a1 and a2 must be searched
             for self-intersection
        Bounding boxes are supposed to be intersecting
        """

        if p1-n1 == 1 and p2-n2 == 1:
            # Same line only !
            if p1 != n2:
                loc = self._two_segments_crossing(n1, p1, n2, p2,
                                                  different=False)
                if not loc is None:
                    if n1 == 0:  l1 = loc[1]
                    else: l1 = self._gea._cumlength[n1-1] + loc[1]

                    if n2 == 0: l1 = loc[2]
                    else: l2 = self._gea._cumlength[n2-1] + loc[2]

                    if l1 <= l2: self.crossings.append((loc[0], l1, l2))
                    else: self.crossings.append((loc[0], l2, l1))
            return # End of first if

        # Cut longest line in half
        if p1-n1 > p2-n2: # first part
            q = (p1 + n1)/2

            # Auto intersection
            if auto1 and self._bbox_intersecting(n1, q,  q, p1):
                self.__cross_intersection(n1, q, q, p1, True, True)
            # Cross intersection
            if self._bbox_intersecting(n1, q, n2, p2):
                self.__cross_intersection(n1, q, n2, p2, False, auto2)
            if self._bbox_intersecting(q, p1, n2, p2):
                self.__cross_intersection(q, p1, n2, p2, False, auto2)

        else: # second part
            q = (p2 + n2)/2
            # Three cases
            if auto2 and self._bbox_intersecting(n2, q, q, p2):
                self.__cross_intersection(n2, q, q, p2, True, True)
            if self._bbox_intersecting(n1, p1, n2, q):
                self.__cross_intersection(n1, p1, n2, q, auto1, False)
            if self._bbox_intersecting(n1, p1, q, p2):
                self.__cross_intersection(n1, p1, q, p2, auto1, False)


    def _bbox_intersecting(self, n1, p1, n2, p2):
        """Test whether two portions of the same line intersect"""

        b1 = self._gea.bbox_indices(n1, p1)
        b2 = self._gea.bbox_indices(n2, p2)
        bbi = self._bbox_intersection(b1, b2)

        if bbi is None: return False

        # Check if there is a common point on the edges
        common = ((p1 == n2) or (n1 == p2))

        # zero height or zero width
        if common: 
            if bbi[0] == bbi[2] or bbi[1] == bbi[3]: return None

        return True

        


class LineIntersection(Intersection):
    """Object for computation and handling of intersections of two lines."""

    def __init__(self, descriptorsa, descriptorsb):
        """Search for line intersections.
        The list of intersections founds is in the 'crossings' attribute."""
        self._gea = descriptorsa
        self._geb = descriptorsb
        self._a = descriptorsa._a
        self._b = descriptorsb._a
        
        # Get crossings
        self.crossings = []
        self._cross_intersection(0, self._a.shape[0]-1, 0, self._b.shape[0]-1)

        # Set up two lists (one per line) containing for each part number,
        # the associated crossing numbers and the curvilinear coordinate. 

        # Intersection coordinates expressed as curve length, sorted.
        interl1 = []
        interl2 = []
        for loc, l1, l2 in self.crossings:
            interl1.append(l1)
            interl2.append(l2)
        interl1.sort()
        interl2.sort()

        self.parts1 = [[] for k in range(len(self.crossings)+1)]
        self.parts2 = [[] for k in range(len(self.crossings)+1)]

        self.parts1[0].append(None)
        self.parts1[0].append(0.)
        self.parts2[0].append(None)
        self.parts2[0].append(0.)

        # Fill in lists
        for k in range(len(self.crossings)):
            loc, l1, l2 = self.crossings[k]

            partnb = interl1.index(l1)
            self.parts1[partnb].append(k)
            self.parts1[partnb].append(l1)
            self.parts1[partnb+1].append(k)
            self.parts1[partnb+1].append(l1)

            partnb = interl2.index(l2)
            self.parts2[partnb].append(k)
            self.parts2[partnb].append(l2)
            self.parts2[partnb+1].append(k)
            self.parts2[partnb+1].append(l2)

        self.parts1[-1].append(None)
        self.parts1[-1].append(self._gea._length)
        self.parts2[-1].append(None)
        self.parts2[-1].append(self._geb._length)

        # Reorder line beginning and end
        # First and last points are properly ordered
        logging.log(10, "self.parts1: "+str(self.parts1))
        for k in range(1,len(self.parts1)-1):
            c = self.parts1[k]
            if c[1] > c[3]:
                c[1], c[3] = c[3], c[1]
                c[0], c[2] = c[2], c[0]

            c = self.parts2[k]
            if c[1] > c[3]:
                c[1], c[3] = c[3], c[1]
                c[0], c[2] = c[2], c[0]
        

    def get_part(self, lineno, value):
        """Return n-th part of line. The number of parts is equal to
        len(self.crossings) + 1. lineno is 0 or 1, if the part is to be
        extracted on the first or second line respectively."""
        if lineno == 0:
            c = self._a
        elif lineno == 1:
            c = self._b
        else: raise ValueError("Unknown line number.")

        if len(self.crossings) == 0 and value == 0:  return c

        if value < 0 or value >= len(self.crossings) + 1:
            raise IndexError("Unexisting line part") 

        if lineno == 0:
            n1, l1, n2, l2 = self.parts1[value]
            return self._gea.extract(l1, l2)
        else:
            n1, l1, n2, l2 = self.parts2[value]
            return self._geb.extract(l1, l2)


    def _cross_intersection(self, n1, p1, n2, p2):
        """Search for intersections between two lines, in the ranges
        [n1, p1] for the first line, and [n2, p2] for the second.
        Indexing is inconsistent with numpy rules: p1 and p2 are included
        in the search.
        Lines are supposed to be intersecting.
        """
        # FIXME: merge with the method of same name in SelfIntersection
        
        debug = False
        # Lines cannot be cut more
        if p1-n1 == 1 and p2-n2 == 1:
            loc = self._two_segments_crossing(n1, p1, n2, p2, different=True)
            if not loc is None:
                logging.log(5, "[_cross_intersection] loc: " +str(loc) +' '+str(n1)+' '+str(n2))
                ## loc == (crossing location, alpha, beta)
                if n1 == 0: l1 = loc[1]
                else: l1 = self._gea._cumlength[n1-1] + loc[1]

                if n2 == 0: l2 = loc[2]
                else: l2 = self._geb._cumlength[n2-1] + loc[2]

                self.crossings.append((loc[0], l1, l2))
            return # After 'if not loc is None'

        # Cut longest line in half
        if p1-n1 > p2-n2: # first part
            q = (p1 + n1)/2

            if self._bbox_intersecting(n1, q, n2, p2):
                self._cross_intersection(n1, q, n2, p2)
            if self._bbox_intersecting(q, p1, n2, p2):
                self._cross_intersection(q, p1, n2, p2)

        else: # second part
            q = (p2 + n2)/2
            
            if self._bbox_intersecting(n1, p1, n2, q):
                self._cross_intersection(n1, p1, n2, q)
            if self._bbox_intersecting(n1, p1, q, p2):
                self._cross_intersection(n1, p1, q, p2)


    def _bbox_intersecting(self, n1, p1, n2, p2):
        """Test whether two portions of two different lines intersect"""

        b1 = self._gea.bbox_indices(n1, p1)
        b2 = self._geb.bbox_indices(n2, p2)
        bbi = self._bbox_intersection(b1, b2)

        return not bbi is None
