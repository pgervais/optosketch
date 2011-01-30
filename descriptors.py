
# -*- coding: utf-8 -*-
# This file is part of Optosketch. It is released under the GPL v2 licence.
"""Functions and objects to compute various line descriptors.
StrokeDescriptor is an object that takes a numpy array as input.
It computes several useful descriptors, including :
- line length (_length)
- barycenter, weighted (_gcenter) and unweighted (_center)
- standard deviation (_astd)
- normalized line (standard deviation 1 in both directions : _anorm)
- center of bounding box (_bboxcenter) 
- principal axis computed with Principal Component Analysis (PCA)
- pca-normalized line : principal axis are aligned with horizontal and 
  vertical, standard deviations are set to 1 (_anormacp).
- bounding box sizes along principal axis (_span)
- segment angles (_angles), and cumulated angles (_cumangles). Cumulated 
 angles can be understood as the angle the line has turned since its beginning.
 For a complete circle, 2*pi, for an infinity sign or an 8 it is zero.

Useful methods :
- Extract a sub-part, given lengths since the beginning (extract())
- Bounding box for a sub-part (bbox_indices())
- ad-hoc point detector : point_detector(). 
"""

import math
from math import radians, pi
from array import array

import numpy
from numpy import dot, sin, cos, sqrt, cross
from numpy.linalg import svd, solve, det

from simplify import simplify_dp


class StrokeDescriptors(object):
    """Estimator of various geometric properties. """
    def __init__(self, a):
        self._a = a
        
        self.atan2 = numpy.frompyfunc(math.atan2, 2, 1)

        # Useful quantities 
        # Polyline segments, as vectors.
        self._vectors = self._a[1:, :] - self._a[:-1, :]
        self._dx = self._vectors[:, 0]
        self._dy = self._vectors[:, 1]

        # Polyline segment lengths, and overall length
        self._lengths = numpy.sqrt(self._dx**2 + self._dy**2)
        self._cumlength = self._lengths.cumsum()
        self._length = self._cumlength[-1]
        
        # Centers of segments
        self._segcenters = (self._a[1:,:] + self._a[:-1,:])/2

        # Unweighted barycenter
        self._center = self._a.mean(0)
        # Weighted barycenter
        self.gravity_center()

        # Center of bounding box
        self._bboxcenter = (self._a.max(0) + self._a.min(0)) / 2
        
        if len(self._a) > 2: self.angles_quantities()
        self.normalize()

        # PCA-related computations
        self.acpn() # FIXME: rename acp -> pca (french->english)
        self.span()
        self.normalize_acp()
        # Straight lines occur for a.r. app. greater than 10
        self._ar = self._S[0]/self._S[1]


    def __str__(self):
        s = 'Line length: %d' % self._length
        s += "\nBbox center: (%.2f, %.2f)" % (self._bboxcenter[0], self._bboxcenter[1])
        s += "\nGravity center: (%.2f, %.2f)" % (self._gcenter[0], self._gcenter[1])
        if len(self._a) > 2:
            s += "\nMax rotation: %.2f turn(s)" % (self._maxrotation/(2*math.pi))
            s += "\nAngle rate: %2f deg/(100*pixel)" % (100.*self._angle_rate *180/math.pi)
#            s += "\nMedian angle: %2f deg" % (self._angle_median *180/math.pi) 
        return s
    

    def gravity_center(self):
        """Return center of line. This estimation is consistent with the
        visual impression (not the bounding box center, nor the unweighted
        mean value) """

        # Lengths
        c = self._segcenters.copy()
        c[:, 0] *= self._lengths
        c[:, 1] *= self._lengths
        self._gcenter = c.sum(0) / sum(self._lengths)


    def angles_quantities(self):
        """Compute some quantities related to segments relative angles."""
        # Cosine: scalar product
        c = self._dx[0:-1] * self._dx[1:] + self._dy[0:-1] * self._dy[1:]
        #c /= self._lengths[0:-1]
        #c /= self._lengths[1:]
        
        # Sine: vector product
        s = self._dx[0:-1] * self._dy[1:] - self._dy[0:-1] * self._dx[1:]
        
        # Oriented angles
        self._angles = self.atan2(s,c)
        self._cumangles = self._angles.cumsum()

        # Get the peak-to-peak amplitude of cumulative angles
        self._maxrotation = self._cumangles.max() - self._cumangles.min()

        # Detrend
        P = numpy.polyfit(self._cumlength[1:], self._cumangles, 1)
        self._angle_rate = P[0]
        print 'polynom:', P

        self._cumangles_d = self._cumangles - numpy.polyval(P, self._cumlength[1:])

        # Median angle: useless without a lot of points
#        self._angle_median = numpy.median(self._angles)


    def normalize(self):
        """Scale data so its standard deviations are equal to 10."""

        self._anorm = self._a.copy()

        s = self._anorm.std(0)
        self._astd = s

        if s[0] != 0.: self._anorm[:,0] /= s[0]/10.
        if s[1] != 0.: self._anorm[:,1] /= s[1]/10.
        return self._anorm


    def acpn(self):
        """Make a simple principal component analysis of input data.
        Returns the rotated sample. 
        X must be a matrix containing one sample per row. The number of
        columns is arbitrary.

        Returns V,S,m,U such that :
        X = dot(U, dot(diagflat(S), V)) + m
        m is a matrix with the same shape as X, containing the mean values for
        each component : X-m is the centered samples.

        A unitary vector giving the main direction of the set is V[0,:]. 
        V[0,0] is always positive.

        A rotated sample set can be obtained by : X * V.transpose()
        (* is the matrix product)
        Rotation around the mean value is given by (X-m) * V.transpose() + m

        det(V) can be +1.0 or -1.0
        """

        # Center variables
        m = dot(numpy.ones(self._a.shape), numpy.diagflat(self._center))
        Xm = self._a - m

        U,S,V = svd(Xm, full_matrices=False);

        # Ensure main direction points towards positive value
        if V[0,0] < 0. : V = -V

        self._V = V
        self._S = S
        # Angle of principal axis relative to horizontal
        self._principal_angle = math.atan2(self._V[0,1], self._V[0,0])


    def span(self):
        """Compute data span along principal axis.
        a is the data, V is the first output of acpn()."""
        p = dot(self._a, self._V.transpose())
        self._span = p.max(0) - p.min(0)


    def normalize_acp(self):
        """Rotate and scale data."""

        b = dot(self._a - self._gcenter, self._V.transpose()) / self._S * 100
        self._anormacp = b


    def midpoint(self, l, ind):
        """Return the coordinate of the point along segment
        self._a[ind], self._a[ind+1], at a distance l from istart.
        No check is performed to ensure that the returned point is inside the
        segment (l may be greater than the segment length, or negative)"""

        # Unitary vector
        u = self._vectors[ind]/self._lengths[ind]
        return l*u + self._a[ind]


    # User methods
    def bbox_indices(self, n1, n2):
        """Compute bounding box for line between two indices.
        Order : xmin, ymin, xmax, ymax."""
        bb = numpy.zeros(4)
        assert (n2+1 <= self._a.shape[0])
        bb[0:2] = self._a[n1:n2+1,:].min(0)
        bb[2:4] = self._a[n1:n2+1,:].max(0)    
        return bb

    #def bbox_length(self, l1, l2):
#    """Compute bounding box for line between two lengths."

    def extract(self, l1, l2):
        """Return the part of the polyline between lengths l1 and l2, starting
        from the beginning of the line."""

        # This is intended to be used as a mean to analyse part of polylines,
        # especially with conic fit. The algorithm is still to be established.

        debug = False
        ind = self._cumlength.searchsorted([l1, l2])

        assert (l1 >= 0.)
        if debug:
            print '[extract], l1, l2:', l1, l2
            print '[extract] Extracted:', ind, 'Lengths:', self._cumlength[ind[0]], \
                  self._cumlength[min(ind[1], len(self._cumlength)-1)]
        
        # First point: always exists
        ends = 0
        if ind[0] == 0:
            d = l1
        else:
            d = l1 - self._cumlength[ind[0]-1]
        assert (d>=0)
        first = self.midpoint(d, ind[0])
        ends += 1

        # Second point
        if ind[1] == len(self._cumlength):
            # No extrapolation
            second = None
        else:
            d = l2 - self._cumlength[ind[1]-1]
            assert (d >= 0)
            second = self.midpoint(d, ind[1])
            ends += 1

        n = ind[1]-ind[0]
        c = numpy.zeros((n+ends,2))
        # Add first point
        c[0,:] = first
        c[1:1+n,:] = self._a[ind[0]+1:ind[1]+1,:]

        if not second is None: c[-1,:] = second

        return c


    def point_detector(self):
        """Detects a point. A point is either a very short line, with very
        small spatial extend, or a very long intricated line, not
        necessarily small spatial extend.
        """
        # Values below 4 or 5 are associated with very small drawings.
        # Short lines give larger values very quickly.
        # Detection is not scale-independent !
        # FIXME: normalize by the ratio window size/opengl window size.
        thresh = 5.

        value = self._span.max()*self._span.mean()/self._length
        print "[point] %.2f vs %.2f" % (value, thresh)
        if value <= thresh: # point
            print "** Point detected **"
            return (True, self._center[0],self._center[1])

        return (False, None, None)


    def straight_line_detector(self):
        """Detects a straight line. Use ratio between length and end-to-end
        distance, on simplified line."""

        # Use of the simplified line is required to handle overall line length 
        # instability for very small lines. However, this detector is scale
        # dependent: small lines must be very straight to trigger this
        # detector, long lines trigger too often. 
        # Possible solutions : change threshold on "ratio" depending on line
        # length, or use another ratio (e.g. aspect ratio, computed using
        # pca results).

        d = simplify_dp(self._a[:,0], self._a[:,1])
        s = self._a[d>1.] # Simplified line

        # Length of simplified line
        # TODO: express as a single line.
        _vectors = s[1:, :] - s[:-1, :]
        _dx = _vectors[:, 0]
        _dy = _vectors[:, 1]
        _length = numpy.sqrt(_dx**2 + _dy**2).sum()

        endtoend = numpy.sqrt(((s[0,:]-s[-1,:])**2).sum())
        ratio = _length / endtoend
        print "Straight line: %.2f %.2f / %.2f = %.2f" % \
            (self._length, _length, endtoend, ratio)

        if ratio < 1.03:
            print "** Straight line detected **"
            return (True,)
        else:
            return (False,)

