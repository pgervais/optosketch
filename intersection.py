# This file is part of Optosketch. It is released under the GPL v2 licence.

"""Classes for line intersection computations.
This module handle self-intersection (and intersections between two
different lines in the future).
"""
import numpy as np

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
        #print "Crossings: "
        #print self.crossings
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
                
        #print "\nParts:"
        #print self.parts


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
            #print "\nCandidates: [%d, %d] [%d, %d]" %(n1, p1, n2, p2)

            # Same line only !
            if p1 != n2:
                loc = self._two_segments_crossing(n1, p1, n2, p2)
                if not loc is None:
##                    print "[__cross_intersection] loc:", loc, n1, n2
                    ## loc == (crossing location, alpha, beta)
                    if n1 == 0:
                        l1 = loc[1]
                    else:
                        l1 = self._gea._cumlength[n1-1] + loc[1]

                    if n2 == 0:
                        l1 = loc[2]
                    else:
                        l2 = self._gea._cumlength[n2-1] + loc[2]

                    if l1 <= l2:
                        self.crossings.append((loc[0], l1, l2))
                    else:
                        self.crossings.append((loc[0], l2, l1))
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

        
    def _two_segments_crossing(self, n1, p1, n2, p2):
        """First part : n1, p1, Second part: n2, p2 (indices)
        This function must be called with n1 < p1 < n2 < p2 .
        """

        debug = False

        assert (n1 < p1)
        assert (p1 < n2)
        assert (n2 < p2)
        x1 = self._a[n1,:]
        x2 = self._a[p1,:]
        x3 = self._a[n2,:]
        x4 = self._a[p2,:]

        # Handle a lot of pathological cases
        if debug:
            print "[_two_segments_crossing] Points:"
            print "[_two_segments_crossing]", x1, x2
            print "[_two_segments_crossing] ", x3, x4

            print "[_two_segments_crossing] Vectors:"
            print '[_two_segments_crossing] 1-3:', x1 - x3
            print '[_two_segments_crossing] 3-2:', x3 - x2
            print '[_two_segments_crossing] 2-4:', x2 - x4
            print '[_two_segments_crossing] 4-1:', x4 - x1

        # When one segment is of length zero, consider there is no intersection.
        # Side segments will report a crossing point.
        # Should never happen after line simplification
        if abs(x1-x2).sum() == 0:
            print "[_two_segments_crossing] Zero-length segment"
            return None 
        if abs(x3-x4).sum() == 0:
            print "[_two_segments_crossing] Zero-length segment"  
            return None

        #1-3/3-2/2-4/4-1
        cp1 = np.cross(x1-x3, x3-x2)
        cp2 = np.cross(x3-x2, x2-x4)
        cp3 = np.cross(x2-x4, x4-x1)
        cp4 = np.cross(x4-x1, x1-x3)
        if debug:
            print "[_two_segments_crossing] CP: ", cp1, cp2, cp3, cp4

        # Check if segments are aligned
        cp = np.cross(x2-x1, x4-x3)
        if cp == 0:
            aligned = True
            print "[_two_segments_crossing] segments aligned (warning)"
        else: aligned = False

        if abs(x1-x4).sum() == 0:
            print "[_two_segments_crossing] 1 == 4 : discard"  
            return None
        if abs(x1-x3).sum() == 0:
            print "[_two_segments_crossing] 1 == 3 : discard"  
            return None
        if abs(x2-x4).sum() == 0:
            print "[_two_segments_crossing] 2 == 4 : discard"  
            return None
        if abs(x2-x3).sum() == 0:
            print "[_two_segments_crossing] 1 == 3 : authorized"  
        else:
            # One point may lie on the **direction** of the other segment
            if cp1 == 0 and not aligned: # point 3 on segment 1-2
                print "[_two_segments_crossing] 3 on 1-2 : discard"
                # Intersection will be reported by the other segment
                return None
            if cp4 == 0 and not aligned: # point 1 on segment 3-4
                print "[_two_segments_crossing] 1 on 3-4 : discard" 
                # Intersection will be reported by the other segment
                return None
            if cp2 == 0: print "[_two_segments_crossing] 2 on 3-4"
            if cp3 == 0: print "[_two_segments_crossing] 4 on 1-2"

        if cp1*cp2 < 0: return None
        if cp2*cp3 < 0: return None
        if cp3*cp4 < 0: return None
        if debug: print "*** Crossing found ***"

        # Parallel segments: return any point
        # FIXME: the returned lengths to crossing do not correspond to the same point
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
        if debug:
            print "[_two_segments_crossing] alpha, norm1:", alpha, norm1
            print "[_two_segments_crossing] beta, norm2:", beta, norm2
            print "[_two_segments_crossing] crossing:", alpha*u1 + x1, '==', beta * u2 + x3
        # Return coordinates of crossing, and lengths from x1 and x3 to the crossing.
        return alpha*u1 + x1, alpha, beta
